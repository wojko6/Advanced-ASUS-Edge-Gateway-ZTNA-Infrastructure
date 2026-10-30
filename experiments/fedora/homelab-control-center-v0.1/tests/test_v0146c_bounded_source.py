"""Owned Python source/process failures, never real journal or live services."""
import contextlib
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import socket
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
import v0146c_bounded_source as source

REAL_POPEN = subprocess.Popen


class PureContract(unittest.TestCase):
    def test_job_contains_data_not_a_supplied_command(self):
        job = json.loads(source._fixture_job(source.SourceFixture(adapter.fixture_inputs())))
        self.assertEqual(set(job), {'stdout', 'stderr', 'exit_code', 'mode'})
        self.assertEqual((job['exit_code'], job['mode']), (0, 'normal'))

    def test_strict_fixture_shape_rejected_before_process_creation(self):
        valid = source.SourceFixture(b'{}\n')
        bad = [None, {}, replace(valid, stdout=bytearray(b'{}\n')),
               replace(valid, stdout=b'x' * (adapter.MAX_BYTES + 2)),
               replace(valid, stderr='warning'), replace(valid, stderr=b'x' * (source.MAX_STDERR_BYTES + 2)),
               replace(valid, exit_code=True), replace(valid, exit_code=1.0), replace(valid, exit_code=-1),
               replace(valid, exit_code=256), replace(valid, mode='journalctl'), replace(valid, mode=[])]
        with mock.patch.object(source.subprocess, 'Popen', side_effect=AssertionError('SPAWN_FORBIDDEN')):
            for fixture in bad:
                with self.subTest(fixture=type(fixture).__name__), self.assertRaises(spool.Hold):
                    source.capture_fixture(fixture)

    def test_selftest_is_pure_and_fixture_repr_hides_raw_data(self):
        output = io.StringIO()
        denied = AssertionError('IO_FORBIDDEN')
        with mock.patch('builtins.open', side_effect=denied), mock.patch.object(os, 'open', side_effect=denied), \
                mock.patch.object(socket, 'socket', side_effect=denied), \
                mock.patch.object(source.subprocess, 'Popen', side_effect=denied), contextlib.redirect_stdout(output):
            source.self_test()
        self.assertIn('V0146C_SELFTEST=PASS', output.getvalue())
        self.assertNotIn('private-message', repr(source.SourceFixture(b'private-message', b'private-stderr')))
        self.assertNotIn('private-stderr', repr(source.SourceFixture(b'private-message', b'private-stderr')))

    def test_framing_rejects_empty_partial_oversize_and_nonbytes(self):
        for raw in (None, bytearray(b'{}\n'), b'', b'{}', b'{}\n' * 129,
                    b'x' * adapter.MAX_BYTES + b'\n'):
            with self.subTest(kind=type(raw).__name__), self.assertRaises(spool.Hold):
                source._validate_framing(raw)

    def test_cleanup_failure_is_explicit_uncertainty(self):
        proc = mock.Mock()
        proc.poll.return_value = None
        proc.pid = 12345
        proc.wait.side_effect = subprocess.TimeoutExpired('fixed-source', 1)
        with mock.patch.object(source.os, 'killpg'), self.assertRaisesRegex(spool.Hold, '^SOURCE_CLEANUP_UNCERTAIN$'):
            source._kill_and_reap(proc)


class _ProcessLifecycle:
    def setUp(self):
        self.children = []

    def spawn(self, *args, **kwargs):
        proc = REAL_POPEN(*args, **kwargs)
        self.children.append(proc)
        self.addCleanup(self.clean_child, proc)
        return proc

    @staticmethod
    def clean_child(proc):
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=2)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()

    def capture(self, fixture):
        with mock.patch.object(source.subprocess, 'Popen', side_effect=self.spawn):
            return source.capture_fixture(fixture)

    def assert_reaped(self):
        self.assertTrue(self.children)
        for proc in self.children:
            self.assertIsNotNone(proc.returncode)
            self.assertTrue(all(stream.closed for stream in (proc.stdin, proc.stdout, proc.stderr)))
            with self.assertRaises(ChildProcessError):
                os.waitpid(proc.pid, os.WNOHANG)  # Already reaped, not only signalled.


class ProcessContract(_ProcessLifecycle, unittest.TestCase):
    def test_complete_split_output_and_success_are_reaped(self):
        raw = adapter.fixture_inputs()
        self.assertEqual(self.capture(source.SourceFixture(raw, mode='split')), raw)
        self.assert_reaped()

    def test_fixed_argv_isolated_environment_no_shell_and_close_fds(self):
        with mock.patch.object(source.subprocess, 'Popen', side_effect=self.spawn) as spawn:
            source.capture_fixture(source.SourceFixture(b'{}\n'))
        args, options = spawn.call_args
        self.assertEqual(args[0], [sys.executable, '-I', '-B', '-c', source._FIXTURE_PROGRAM])
        self.assertFalse(options['shell'])
        self.assertTrue(options['close_fds'])
        self.assertTrue(options['start_new_session'])
        self.assertEqual(options['env'], {'LC_ALL': 'C', 'LANG': 'C', 'TZ': 'UTC'})
        self.assertEqual(options['bufsize'], 0)
        self.assert_reaped()

    def test_exact_stdout_byte_limit_drains_large_stdin_without_deadlock(self):
        raw = b'x' * (adapter.MAX_BYTES - 1) + b'\n'
        self.assertEqual(self.capture(source.SourceFixture(raw)), raw)
        self.assert_reaped()

    def test_stdout_overflow_kills_reaps_and_returns_only_fixed_reason(self):
        with self.assertRaisesRegex(spool.Hold, '^SOURCE_STDOUT_LIMIT$'):
            self.capture(source.SourceFixture(b'x' * adapter.MAX_BYTES + b'\n'))
        self.assert_reaped()

    def test_exact_row_limit_passes(self):
        raw = b'{}\n' * adapter.MAX_ROWS
        self.assertEqual(self.capture(source.SourceFixture(raw)), raw)
        self.assert_reaped()

    def test_excess_rows_hold_before_import(self):
        with self.assertRaisesRegex(spool.Hold, '^SOURCE_ROW_LIMIT$'):
            self.capture(source.SourceFixture(b'{}\n' * (adapter.MAX_ROWS + 1)))
        self.assert_reaped()

    def test_nonzero_exit_rejects_even_complete_valid_output(self):
        for status in (1, 23, 255):
            with self.subTest(status=status), self.assertRaisesRegex(spool.Hold, '^SOURCE_NONZERO_EXIT$'):
                self.capture(source.SourceFixture(adapter.fixture_inputs(), exit_code=status))
        self.assert_reaped()

    def test_stderr_warning_and_exact_limit_are_not_success(self):
        for err in (b'private-warning', b'x' * source.MAX_STDERR_BYTES):
            with self.subTest(size=len(err)), self.assertRaisesRegex(spool.Hold, '^SOURCE_STDERR_NOT_EMPTY$'):
                self.capture(source.SourceFixture(adapter.fixture_inputs(), stderr=err))
        self.assert_reaped()

    def test_stderr_overflow_does_not_deadlock_behind_stdout(self):
        with self.assertRaisesRegex(spool.Hold, '^SOURCE_STDERR_LIMIT$'):
            self.capture(source.SourceFixture(adapter.fixture_inputs(), stderr=b'x' * (source.MAX_STDERR_BYTES + 1)))
        self.assert_reaped()

    def test_empty_and_truncated_final_row_hold(self):
        for raw in (b'', adapter.fixture_inputs().rstrip(b'\n')):
            with self.subTest(size=len(raw)), self.assertRaises(spool.Hold):
                self.capture(source.SourceFixture(raw))
        self.assert_reaped()

    def test_stall_before_output_is_killed_and_reaped(self):
        with mock.patch.object(source, 'SOURCE_SECONDS', 0.2), \
                self.assertRaisesRegex(spool.Hold, '^SOURCE_DEADLINE$'):
            self.capture(source.SourceFixture(adapter.fixture_inputs(), mode='stall_before_output'))
        self.assert_reaped()

    def test_valid_prefix_then_stall_is_not_complete_success(self):
        with mock.patch.object(source, 'SOURCE_SECONDS', 0.2), \
                self.assertRaisesRegex(spool.Hold, '^SOURCE_DEADLINE$'):
            self.capture(source.SourceFixture(adapter.fixture_inputs(), mode='stall_after_output'))
        self.assert_reaped()

    def test_closed_pipes_do_not_bypass_child_exit_deadline(self):
        with mock.patch.object(source, 'SOURCE_SECONDS', 0.2), \
                self.assertRaisesRegex(spool.Hold, '^SOURCE_DEADLINE$'):
            self.capture(source.SourceFixture(adapter.fixture_inputs(), mode='close_pipes_then_stall'))
        self.assert_reaped()

    def test_keyboard_interrupt_during_select_kills_and_reaps(self):
        with mock.patch.object(source.selectors.DefaultSelector, 'select', side_effect=KeyboardInterrupt), \
                self.assertRaises(KeyboardInterrupt):
            self.capture(source.SourceFixture(adapter.fixture_inputs(), mode='stall_before_output'))
        self.assert_reaped()

    def test_selector_setup_error_kills_and_reaps(self):
        with mock.patch.object(source.selectors.DefaultSelector, 'register', side_effect=OSError('private-error')), \
                self.assertRaisesRegex(spool.Hold, '^SOURCE_PROCESS_IO$'):
            self.capture(source.SourceFixture(adapter.fixture_inputs()))
        self.assert_reaped()

    def test_broken_input_pipe_kills_and_reaps(self):
        with mock.patch.object(source.os, 'write', side_effect=BrokenPipeError('private-error')), \
                self.assertRaisesRegex(spool.Hold, '^SOURCE_PROCESS_IO$'):
            self.capture(source.SourceFixture(adapter.fixture_inputs(), mode='stall_before_output'))
        self.assert_reaped()

    def test_spawn_failure_has_no_success_or_diagnostic_echo(self):
        with mock.patch.object(source.subprocess, 'Popen', side_effect=OSError('private-error')), \
                self.assertRaisesRegex(spool.Hold, '^SOURCE_PROCESS_IO$'):
            source.capture_fixture(source.SourceFixture(adapter.fixture_inputs()))
        self.assertEqual(self.children, [])


class ImportContract(_ProcessLifecycle, unittest.TestCase):
    def setUp(self):
        super().setUp()
        temp = tempfile.TemporaryDirectory(prefix='hcc-v0146c-test-', dir='/tmp')
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name)
        self.fd = spool.open_private_directory(self.path)
        self.addCleanup(os.close, self.fd)

    def run_import(self, fixture=None, **options):
        with mock.patch.object(source.subprocess, 'Popen', side_effect=self.spawn):
            return source.import_fixture(self.fd, fixture or source.SourceFixture(adapter.fixture_inputs()),
                                         expected_uid=options.pop('expected_uid', 1000),
                                         key=options.pop('key', identity.SYNTHETIC_KEY), **options)

    def saved(self):
        return (self.path / handoff.NAME).read_bytes()

    def test_whole_source_import_and_replay_match_direct_b(self):
        first = self.run_import()
        self.assertEqual((first.source_rows, first.imported.accepted_events, first.imported.duplicate_events), (5, 3, 1))
        before = (self.path / handoff.NAME).stat()
        again = self.run_import()
        after = (self.path / handoff.NAME).stat()
        self.assertEqual((again.imported.accepted_events, again.imported.duplicate_events), (0, 4))
        self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))
        self.assert_reaped()

    def test_no_import_call_until_successful_child_exit_and_cleanup(self):
        import_batch = importer.import_batch
        def observe(*args, **options):
            self.assert_reaped()
            self.assertEqual(self.children[-1].returncode, 0)
            return import_batch(*args, **options)
        with mock.patch.object(importer, 'import_batch', side_effect=observe):
            self.run_import()

    def test_source_errors_do_not_call_importer_or_change_existing_file(self):
        self.run_import()
        before = self.saved()
        fixtures = (source.SourceFixture(adapter.fixture_inputs(), exit_code=23),
                    source.SourceFixture(adapter.fixture_inputs(), stderr=b'private-warning'),
                    source.SourceFixture(adapter.fixture_inputs().rstrip(b'\n')),
                    source.SourceFixture(adapter.fixture_inputs(), mode='stall_after_output'))
        with mock.patch.object(source, 'SOURCE_SECONDS', 0.2), \
                mock.patch.object(importer, 'import_batch', side_effect=AssertionError('IMPORT_FORBIDDEN')):
            for fixture in fixtures:
                with self.subTest(mode=fixture.mode), self.assertRaises(spool.Hold):
                    self.run_import(fixture)
                self.assertEqual(self.saved(), before)
                self.assertEqual([p.name for p in self.path.iterdir()], [handoff.NAME])
        self.assert_reaped()

    def test_late_bad_metadata_does_not_partially_import_valid_prefix(self):
        invalid = adapter.fixture_record('synthetic-late-bad', 1793350800000010)
        invalid['_UID'] = '1001'
        raw = adapter.fixture_inputs() + identity.canonical(invalid) + b'\n'
        with self.assertRaises(spool.Hold):
            self.run_import(source.SourceFixture(raw))
        self.assertEqual(list(self.path.iterdir()), [])
        self.assert_reaped()

    def test_blank_row_invalid_json_and_binary_are_rejected_by_a(self):
        for raw in (adapter.fixture_inputs() + b'\n', b'{}\n', b'\xff\n'):
            with self.subTest(size=len(raw)), self.assertRaises(spool.Hold):
                self.run_import(source.SourceFixture(raw))
            self.assertEqual(list(self.path.iterdir()), [])
        self.assert_reaped()

    def test_invalid_uid_and_key_rejected_without_spawning(self):
        for options in ({'expected_uid': True}, {'expected_uid': 0}, {'key': b'x'}):
            with mock.patch.object(source.subprocess, 'Popen', side_effect=AssertionError('SPAWN_FORBIDDEN')), \
                    self.assertRaises(spool.Hold):
                source.import_fixture(self.fd, source.SourceFixture(adapter.fixture_inputs()),
                                      expected_uid=options.get('expected_uid', 1000),
                                      key=options.get('key', identity.SYNTHETIC_KEY))
        self.assertEqual(list(self.path.iterdir()), [])

    def test_no_match_still_checks_existing_corrupt_store(self):
        (self.path / handoff.NAME).write_bytes(b'corrupt')
        os.chmod(self.path / handoff.NAME, 0o600)
        row = adapter.fixture_record(message='collector finished')
        with self.assertRaises(spool.Hold):
            self.run_import(source.SourceFixture(identity.canonical(row) + b'\n'))
        self.assertEqual(self.saved(), b'corrupt')
        self.assert_reaped()

    def test_same_declared_metadata_from_fixed_child_is_still_not_provenance(self):
        # All bytes originated in this test, never kernel journal credentials.
        first = self.run_import()
        self.assertEqual(first.imported.accepted_events, 3)
        for secret in (b'private.example', b'synthetic-cursor-', b'"MESSAGE"', b'"_UID"'):
            self.assertNotIn(secret, self.saved())
        self.assert_reaped()


class CliContract(unittest.TestCase):
    def test_lab_cleanup_and_no_socket_usage(self):
        made = []
        temporary_directory = tempfile.TemporaryDirectory
        def own_temp(*args, **kwargs):
            temp = temporary_directory(*args, **kwargs)
            made.append(temp.name)
            return temp
        output = io.StringIO()
        with mock.patch.object(source.tempfile, 'TemporaryDirectory', side_effect=own_temp), \
                mock.patch.object(socket, 'socket', side_effect=AssertionError('NETWORK_FORBIDDEN')), \
                contextlib.redirect_stdout(output):
            source.run_lab()
        self.assertTrue(made)
        self.assertTrue(all(not Path(folder).exists() for folder in made))
        self.assertIn('TEMP_STATE_REMOVED=YES', output.getvalue())
        self.assertIn('V0146C_RESULT=PASS_BOUNDED_FIXTURE_IMPORT_ONLY', output.getvalue())
        for private in ('private.example', 'synthetic-cursor-', 'private-warning'):
            self.assertNotIn(private, output.getvalue())

    def test_cli_rejects_command_path_uid_key_and_live_options(self):
        for args in (['--command', 'journalctl'], ['--journal'], ['--path', '/var/log/journal'],
                     ['--uid', '1000'], ['--key', 'private-key'], ['--source-worker']):
            with mock.patch.object(sys, 'argv', ['v0146c', '--lab', *args]), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                source.main()
            self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
