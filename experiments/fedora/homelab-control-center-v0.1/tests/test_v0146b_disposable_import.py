"""Disposable A->E import: synthetic JSON, private /tmp state, no live services."""
import contextlib
import io
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import v0145a_segment_spool as spool
import v0145d_event_identity as identity
import v0145e_atomic_handoff as handoff
import v0146a_journal_envelope as adapter
import v0146b_disposable_import as importer


def record(number=1, **changes):
    row = adapter.fixture_record(f'synthetic-import-{number:04d}', 1793350800000000 + number)
    row.update(changes)
    return identity.canonical(row) + b'\n'


class ImportContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hcc-v0146b-test-', dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        os.chmod(self.path, 0o700)
        self.fd = spool.open_private_directory(self.path)
        self.addCleanup(lambda: os.close(self.fd) if self.fd is not None else None)

    def run_import(self, data=None, **options):
        return importer.import_batch(self.fd, record() if data is None else data,
                                     expected_uid=options.pop('expected_uid', 1000),
                                     key=options.pop('key', identity.SYNTHETIC_KEY), **options)

    def saved(self):
        return (self.path / handoff.NAME).read_bytes()

    def reopen(self):
        os.close(self.fd)
        self.fd = None
        self.fd = spool.open_private_directory(self.path)

    def test_initial_fixture_import_retains_three_complete_events(self):
        result = self.run_import(adapter.fixture_inputs())
        self.assertEqual((result.input_records, result.accepted_events, result.duplicate_events,
                          result.ignored_records, result.retained_events), (5, 3, 1, 1, 3))
        self.assertEqual(result.status, 'PUBLISHED_DISPOSABLE_IMPORT')
        self.assertEqual(len(handoff.read_handoff(self.fd).events), 3)

    def test_reopen_repeat_deduplicates_without_replacing_file(self):
        self.run_import(adapter.fixture_inputs())
        self.reopen()
        before = (self.path / handoff.NAME).stat()
        result = self.run_import(adapter.fixture_inputs())
        after = (self.path / handoff.NAME).stat()
        self.assertEqual((result.accepted_events, result.duplicate_events, result.retained_events), (0, 4, 3))
        self.assertEqual(result.status, 'DUPLICATE_IMPORT_NO_WRITE')
        self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))

    def test_overlap_and_internal_duplicates_have_exact_counts(self):
        self.run_import(record(1))
        result = self.run_import(record(1) + record(2) + record(2))
        self.assertEqual((result.accepted_events, result.duplicate_events, result.retained_events), (1, 2, 2))

    def test_new_lower_id_is_merged_instead_of_skipped(self):
        key = importer.policy_key(1000, identity.SYNTHETIC_KEY)
        pairs = []
        for number in range(1, 12):
            result = adapter.adapt_snapshot(record(number), expected_uid=1000, key=key)
            event_id = json.loads(handoff.decode_snapshot(result.snapshot).events[0])['event_id']
            pairs.append((event_id, number))
        pairs.sort()
        self.run_import(record(pairs[-1][1]))
        self.assertEqual(self.run_import(record(pairs[0][1])).accepted_events, 1)
        ids = [json.loads(event)['event_id'] for event in handoff.read_handoff(self.fd).events]
        self.assertEqual(ids, [pairs[0][0], pairs[-1][0]])

    def test_changed_payload_for_retained_id_preserves_previous_file(self):
        self.run_import()
        before = self.saved()
        for update in ({'MESSAGE': 'ssh: Permission denied'},
                       {'__REALTIME_TIMESTAMP': '1793350800000002'}):
            with self.subTest(update=update), self.assertRaisesRegex(spool.Hold, 'SAME_ID_CHANGED'):
                self.run_import(record(**update))
            self.assertEqual(self.saved(), before)

    def test_new_record_before_later_retained_conflict_is_not_partially_committed(self):
        self.run_import(record(2))
        before = self.saved()
        with self.assertRaises(spool.Hold):
            self.run_import(record(1) + record(2, MESSAGE='ssh: Permission denied'))
        self.assertEqual(self.saved(), before)

    def test_cross_call_private_message_change_same_sanitized_payload_is_not_detected(self):
        self.run_import(record(MESSAGE='ssh: timeout host-a'))
        before = self.saved()
        self.reopen()
        result = self.run_import(record(MESSAGE='ssh: timeout host-b'))
        self.assertEqual(result.duplicate_events, 1)
        self.assertEqual(self.saved(), before)  # No persistent raw-message fingerprint.

    def test_policy_uid_change_is_rejected_even_for_no_match(self):
        self.run_import()
        before = self.saved()
        for message in ('ssh: timeout', 'collector finished'):
            with self.subTest(message=message), self.assertRaisesRegex(spool.Hold, 'POLICY_OR_KEY_SCOPE'):
                self.run_import(record(2, _UID='1001', _SYSTEMD_OWNER_UID='1001', MESSAGE=message),
                                expected_uid=1001)
            self.assertEqual(self.saved(), before)

    def test_key_change_and_standalone_a_scope_are_not_silently_migrated(self):
        self.run_import()
        before = self.saved()
        with self.assertRaisesRegex(spool.Hold, 'POLICY_OR_KEY_SCOPE'):
            self.run_import(key=b'k' * 32)
        self.assertEqual(self.saved(), before)
        original = adapter.adapt_snapshot(record(), expected_uid=1000, key=identity.SYNTHETIC_KEY)
        (self.path / handoff.NAME).write_bytes(original.snapshot)
        with self.assertRaisesRegex(spool.Hold, 'POLICY_OR_KEY_SCOPE'):
            self.run_import()

    def test_no_match_checks_store_without_creating_or_rewriting_snapshot(self):
        no_match = record(MESSAGE='collector finished')
        result = self.run_import(no_match)
        self.assertEqual(result.status, 'NO_MATCH_NO_WRITE')
        self.assertEqual(list(self.path.iterdir()), [])
        self.run_import()
        before = self.saved()
        self.assertEqual(self.run_import(no_match).retained_events, 1)
        self.assertEqual(self.saved(), before)

    def test_no_match_does_not_anchor_policy_in_an_empty_store(self):
        self.run_import(record(MESSAGE='collector finished'))
        result = self.run_import(record(_UID='1001', _SYSTEMD_OWNER_UID='1001'), expected_uid=1001)
        self.assertEqual(result.accepted_events, 1)

    def test_total_store_loss_is_indistinguishable_from_fresh_import(self):
        self.run_import()
        (self.path / handoff.NAME).unlink()  # Test-induced loss, never implementation retention.
        self.reopen()
        self.assertEqual(self.run_import().accepted_events, 1)

    def test_atomic_visibility_modes_and_private_payload(self):
        self.run_import()
        before = self.saved()
        replace = os.replace
        observed = []
        def inspect(source, target, **kwargs):
            self.assertEqual(self.saved(), before)
            content = (self.path / source).read_bytes()
            self.assertEqual(len(handoff.decode_snapshot(content).events), 2)
            self.assertEqual(stat.S_IMODE((self.path / source).stat().st_mode), 0o600)
            observed.append(True)
            return replace(source, target, **kwargs)
        with mock.patch.object(importer.os, 'replace', side_effect=inspect):
            self.run_import(record(2))
        self.assertEqual(observed, [True])
        self.assertEqual(stat.S_IMODE((self.path / handoff.NAME).stat().st_mode), 0o600)
        for token in (b'private.example', b'synthetic-import-', b'"MESSAGE"', b'"_UID"', b'a' * 32):
            self.assertNotIn(token, self.saved())

    def test_strict_options_and_invalid_late_row_create_no_file(self):
        cases = [(record(), {'failpoint': value}) for value in ('bad', False, 1, [])]
        cases += [(record(), {'expected_uid': uid}) for uid in (True, 0, '1000')]
        cases += [(record(), {'key': b'x'}), (b'{}', {}),
                  (record(1) + record(2, _UID='1001'), {})]
        for data, options in cases:
            with self.subTest(options=options), self.assertRaises(spool.Hold):
                self.run_import(data, **options)
            self.assertEqual(list(self.path.iterdir()), [])

    def test_capacity_limit_has_no_partial_update(self):
        for start in range(1, handoff.MAX_EVENTS + 1, adapter.MAX_ROWS):
            self.run_import(b''.join(record(number) for number in
                                    range(start, min(start + adapter.MAX_ROWS, handoff.MAX_EVENTS + 1))))
        self.assertEqual(len(handoff.read_handoff(self.fd).events), handoff.MAX_EVENTS)
        before = self.saved()
        with self.assertRaisesRegex(spool.Hold, 'IMPORT_EVENT_LIMIT'):
            self.run_import(record(handoff.MAX_EVENTS + 1))
        self.assertEqual(self.saved(), before)

    def test_snapshot_bytes_limit_has_no_partial_update(self):
        self.run_import(record(1))
        before = self.saved()
        # Each incoming/current single record fits; their prospective merge does not.
        with mock.patch.object(handoff, 'MAX_SNAPSHOT_BYTES', len(before)), self.assertRaises(spool.Hold):
            self.run_import(record(2))
        self.assertEqual(self.saved(), before)

    def test_unknown_or_orphan_entry_blocks_even_no_match(self):
        for name in ('unexpected.json', '.handoff-' + 'a' * 32 + '.tmp'):
            path = self.path / name
            path.write_bytes(b'synthetic')
            for data in (record(), record(MESSAGE='collector finished')):
                with self.subTest(name=name), self.assertRaises(spool.Hold):
                    self.run_import(data)
            path.unlink()  # Fixture reset only.

    def test_corrupt_snapshot_is_not_reset_even_on_no_match(self):
        self.run_import()
        (self.path / handoff.NAME).write_bytes(b'{}')
        for data in (record(), record(MESSAGE='collector finished')):
            with self.assertRaises(spool.Hold):
                self.run_import(data)
            self.assertEqual(self.saved(), b'{}')

    def test_directory_and_file_modes_are_rechecked(self):
        os.fchmod(self.fd, 0o755)
        with self.assertRaises(spool.Hold):
            self.run_import()
        os.fchmod(self.fd, 0o700)
        self.run_import()
        (self.path / handoff.NAME).chmod(0o644)
        with self.assertRaises(spool.Hold):
            self.run_import()

    def test_symlink_fifo_and_extra_hardlink_are_refused(self):
        path = self.path / handoff.NAME
        path.symlink_to(self.path / 'missing')
        with self.assertRaises(OSError):
            self.run_import()
        path.unlink()
        os.mkfifo(path, 0o600)
        with self.assertRaises(spool.Hold):
            self.run_import()
        path.unlink()
        self.run_import()
        with tempfile.TemporaryDirectory(prefix='hcc-v0146b-link-', dir='/tmp') as other:
            os.link(path, Path(other) / 'other-link')
            with self.assertRaisesRegex(spool.Hold, 'UNSAFE_HANDOFF'):
                self.run_import()

    def test_separate_directory_description_cannot_bypass_writer_lock(self):
        other = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            with self.assertRaisesRegex(spool.Hold, 'DIRECTORY_BUSY'):
                importer.import_batch(other, record(), expected_uid=1000, key=identity.SYNTHETIC_KEY)
        finally:
            os.close(other)

    def test_pre_replace_failure_preserves_old_snapshot_and_cleans_temp(self):
        self.run_import()
        before = self.saved()
        with self.assertRaises(spool.SimulatedInterrupt):
            self.run_import(record(2), failpoint='after_temp_fsync_before_replace')
        self.assertEqual(self.saved(), before)
        self.assertEqual(os.listdir(self.fd), [handoff.NAME])

    def test_post_replace_uncertainty_and_lost_receipt_reopen_as_duplicates(self):
        for phase in ('after_replace_before_dir_fsync', 'after_dir_fsync_before_return'):
            number = len(handoff.read_handoff(self.fd).events) + 1 if (self.path / handoff.NAME).exists() else 1
            with self.subTest(phase=phase), self.assertRaises(spool.SimulatedInterrupt):
                self.run_import(record(number), failpoint=phase)
            self.reopen()
            self.assertEqual(self.run_import(record(number)).duplicate_events, 1)

    def test_file_and_directory_sync_failures_do_not_return_success(self):
        self.run_import()
        before = self.saved()
        fsync = os.fsync
        def fail_file(fd):
            if stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError('synthetic file sync')
            return fsync(fd)
        with mock.patch.object(importer.os, 'fsync', side_effect=fail_file), self.assertRaises(OSError):
            self.run_import(record(2))
        self.assertEqual(self.saved(), before)
        def fail_dir(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError('synthetic directory sync')
            return fsync(fd)
        with mock.patch.object(importer.os, 'fsync', side_effect=fail_dir), self.assertRaises(OSError):
            self.run_import(record(2))
        self.assertEqual(len(handoff.read_handoff(self.fd).events), 2)

    def test_duplicate_and_no_match_require_directory_barrier(self):
        self.run_import()
        before = self.saved()
        for data in (record(), record(MESSAGE='collector finished')):
            with mock.patch.object(importer.os, 'fsync', side_effect=OSError('synthetic barrier')), \
                 self.assertRaises(OSError):
                self.run_import(data)
        self.assertEqual(self.saved(), before)

    def test_zero_write_and_replace_failure_preserve_previous_data(self):
        self.run_import()
        before = self.saved()
        for operation, value in (('write', 0), ('replace', OSError('synthetic replace'))):
            options = {'side_effect': value} if isinstance(value, Exception) else {'return_value': value}
            with mock.patch.object(importer.os, operation, **options), self.assertRaises((spool.Hold, OSError)):
                self.run_import(record(2))
            self.assertEqual(self.saved(), before)
            self.assertEqual(os.listdir(self.fd), [handoff.NAME])

    def test_cleanup_failure_leaves_orphan_for_explicit_hold(self):
        self.run_import()
        with mock.patch.object(importer.os, 'unlink', side_effect=OSError('synthetic cleanup')), \
             self.assertRaises(OSError):
            self.run_import(record(2), failpoint='after_temp_fsync_before_replace')
        with self.assertRaisesRegex(spool.Hold, 'ORPHAN_HANDOFF'):
            self.run_import(record(2))

    def test_interrupt_before_replace_propagates_after_temp_cleanup(self):
        self.run_import()
        before = self.saved()
        with mock.patch.object(importer.os, 'write', side_effect=KeyboardInterrupt()), \
             self.assertRaises(KeyboardInterrupt):
            self.run_import(record(2))
        self.assertEqual(self.saved(), before)
        self.assertEqual(os.listdir(self.fd), [handoff.NAME])

    def test_abrupt_child_exit_three_commit_phases(self):
        program = r'''
import os,stat,sys
sys.path.insert(0,sys.argv[1])
import v0145a_segment_spool as s
import v0145d_event_identity as d
import v0146a_journal_envelope as a
import v0146b_disposable_import as b
phase=sys.argv[3]
replace,fsync=os.replace,os.fsync
def interrupt_replace(*args,**kwargs):
    if phase=='temp': os._exit(23)
    result=replace(*args,**kwargs)
    if phase=='replace': os._exit(23)
    return result
def interrupt_sync(fd):
    fsync(fd)
    if phase=='directory' and stat.S_ISDIR(os.fstat(fd).st_mode): os._exit(23)
os.replace,os.fsync=interrupt_replace,interrupt_sync
fd=s.open_private_directory(sys.argv[2])
row=a.fixture_record('synthetic-child-002',1793350800000002)
b.import_batch(fd,d.canonical(row)+b'\n',expected_uid=1000,key=d.SYNTHETIC_KEY)
os._exit(99)
'''
        for phase in ('temp', 'replace', 'directory'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory(prefix='hcc-v0146b-exit-', dir='/tmp') as folder:
                os.chmod(folder, 0o700)
                fd = spool.open_private_directory(folder)
                importer.import_batch(fd, record(), expected_uid=1000, key=identity.SYNTHETIC_KEY)
                os.close(fd)
                child = subprocess.run([sys.executable, '-B', '-c', program, str(Path(importer.__file__).parent),
                                        folder, phase], capture_output=True, timeout=10)
                self.assertEqual((child.returncode, child.stdout, child.stderr), (23, b'', b''))
                fd = spool.open_private_directory(folder)
                try:
                    if phase == 'temp':
                        with self.assertRaisesRegex(spool.Hold, 'ORPHAN_HANDOFF'):
                            handoff.read_handoff(fd)
                        self.assertEqual(len(handoff.decode_snapshot((Path(folder) / handoff.NAME).read_bytes()).events), 1)
                    else:
                        self.assertEqual(len(handoff.read_handoff(fd).events), 2)
                        extra = identity.canonical(adapter.fixture_record('synthetic-child-002', 1793350800000002)) + b'\n'
                        self.assertEqual(importer.import_batch(fd, extra, expected_uid=1000,
                                                              key=identity.SYNTHETIC_KEY).duplicate_events, 1)
                finally:
                    os.close(fd)


class ImportCli(unittest.TestCase):
    def test_policy_key_and_selftest_are_pure(self):
        with mock.patch('builtins.open', side_effect=AssertionError('file')), \
             mock.patch.object(os, 'open', side_effect=AssertionError('os.open')), \
             mock.patch.object(socket, 'socket', side_effect=AssertionError('network')), \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('subprocess')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            importer.self_test()
        self.assertIn('V0146B_SELFTEST=PASS_PURE_SYNTHETIC_ONLY', output.getvalue())

    def test_lab_cleans_temp_and_reports_no_raw_data_or_keys(self):
        folders = []
        original = tempfile.TemporaryDirectory
        def capture(*args, **kwargs):
            folder = original(*args, **kwargs)
            folders.append(folder.name)
            return folder
        with mock.patch.object(tempfile, 'TemporaryDirectory', side_effect=capture), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            importer.run_lab()
        self.assertTrue(folders and all(not Path(folder).exists() for folder in folders))
        self.assertIn('V0146B_RESULT=PASS_DISPOSABLE_IMPORT_ONLY', output.getvalue())
        self.assertIn('FINAL_RETAINED_EVENTS=4', output.getvalue())
        for token in ('private.example', 'synthetic-cursor-', identity.scope_for(identity.SYNTHETIC_KEY),
                      importer.policy_key(1000, identity.SYNTHETIC_KEY).hex(), *folders):
            self.assertNotIn(token, output.getvalue())

    def test_cli_rejects_paths_stdin_key_uid_and_ambiguous_modes(self):
        for args in ([], ['--lab', '--self-test'], ['--stdin'], ['--path', '/tmp/synthetic'],
                     ['--key', 'synthetic'], ['--uid', '1000'], ['--url', 'http://invalid.test/']):
            with mock.patch.object(sys, 'argv', ['v0146b.py', *args]), \
                 contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    importer.main()
            self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
