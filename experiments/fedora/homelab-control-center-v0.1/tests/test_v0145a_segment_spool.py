"""HCC V0.14.5A pure synthetic offline tests: tempfile and no network/services."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import v0145a_segment_spool as lab


def sample(time='2026-10-29T09:00:00.000Z', kind='COLLECTOR_EXIT_255'):
    return lab.event(time, kind)


class InputContract(unittest.TestCase):
    def reject(self, raw):
        with self.assertRaises(lab.Hold):
            lab.normalize_sanitized_jsonl(raw)

    def test_canonical_whitelist(self):
        b = sample()
        self.assertEqual(b, lab.normalize_sanitized_jsonl(b))
        self.assertEqual(len(lab.normalize_sanitized_jsonl(b).splitlines()), 1)

    def test_duplicate_json_keys_rejected(self):
        obj = sample().decode().strip()
        self.reject(obj.replace('"kind":', '"kind":"SSH_TIMEOUT","kind":').encode())

    def test_raw_log_or_extra_field_rejected(self):
        self.reject(sample().replace(b'COLLECTOR_EXIT_255', b'private.example'))
        self.reject(sample().replace(b'"source":', b'"client_ip":"192.0.2.1","source":'))
        self.reject(sample().replace(b'"source":"fedora-user-journal"', b'"source":"raw-journal"'))

    def test_type_boolean_nonfinite_empty_and_limits(self):
        self.reject(b'')
        self.reject(b'\n')
        self.reject(b'null\n')
        self.reject(sample().replace(b'"kind":"COLLECTOR_EXIT_255"', b'"kind":true'))
        self.reject(sample().replace(b'"kind":"COLLECTOR_EXIT_255"', b'"kind":NaN'))
        self.reject(sample() + b' ' * lab.MAX_BYTES)

    def test_reject_bad_time(self):
        for s in ('2026-02-29T09:00:00.000Z','2026-10-29T09:00:00Z',
                  '2026-10-29T09:00:00.000+00:00','1999-10-29T09:00:00.000Z'):
            with self.subTest(s=s):
                self.reject(sample().replace(b'2026-10-29T09:00:00.000Z',s.encode()))

    def test_order_and_duplicate_in_batch(self):
        self.reject(sample()+sample())
        self.reject(sample('2026-10-29T09:00:01.000Z')+sample())
        self.assertEqual(len(lab.normalize_sanitized_jsonl(
            sample()+sample('2026-10-29T09:00:00.000Z','SSH_TIMEOUT')).splitlines()), 2)

    def test_excessive_rows(self):
        many = b''.join(sample(f'2026-10-29T09:{i//60:02}:{i%60:02}.000Z') for i in range(lab.MAX_ROWS+1))
        self.reject(many)


class SyntheticStorage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hcc-v0145a-test-')
        self.addCleanup(self.temp.cleanup)
        self.p = Path(self.temp.name)
        os.chmod(self.p, 0o700)
        self.fd = lab.open_private_directory(self.p)
        self.addCleanup(os.close, self.fd)

    def test_publish_exact_batch_dedup_and_integrity(self):
        state, name = lab.publish(self.fd, sample())
        self.assertEqual(state, 'PUBLISHED_ATOMIC_SEGMENT')
        self.assertEqual(lab.publish(self.fd, sample()), ('DUPLICATE_BATCH_NO_WRITE',name))
        self.assertEqual(lab.inspect_entries(self.fd), [name])
        self.assertEqual(lab.verified_segment(self.fd,name), sample())
        self.assertEqual(stat.S_IMODE((self.p/name).stat().st_mode),0o600)

    def test_interruption_before_publish_no_visible_segment(self):
        with self.assertRaises(lab.SimulatedInterrupt):
            lab.publish(self.fd,sample(),failpoint='after_fsync_before_publish')
        self.assertEqual(lab.inspect_entries(self.fd), [])

    def test_private_directory_mandatory(self):
        other=self.p/'weak'
        other.mkdir(mode=0o755)
        with self.assertRaises(lab.Hold):
            lab.open_private_directory(other)

    def test_symlink_private_directory_refused(self):
        outside = self.p/'real'
        outside.mkdir(mode=0o700)
        link = self.p/'link'
        link.symlink_to(outside,target_is_directory=True)
        with self.assertRaises(OSError):
            lab.open_private_directory(link)

    def test_orphan_temp_causes_hold(self):
        (self.p/('.tmp-'+'a'*32)).write_text('orphan')
        with self.assertRaisesRegex(lab.Hold, 'ORPHAN'):
            lab.publish(self.fd,sample())

    def test_unexpected_entry_causes_hold(self):
        (self.p/'secret.txt').write_text('data')
        with self.assertRaisesRegex(lab.Hold, 'UNEXPECTED'):
            lab.publish(self.fd,sample())

    def test_symlink_existing_segment_is_not_trusted(self):
        content=sample()
        name=lab.digest_name(content)
        (self.p/name).symlink_to(self.p/'missing-target')
        with self.assertRaises(OSError):
            lab.publish(self.fd, content)

    def test_modified_segment_fails_closed(self):
        _,name=lab.publish(self.fd,sample())
        (self.p/name).write_bytes(b'not a valid sanitized event\n')
        with self.assertRaises(lab.Hold):
            lab.publish(self.fd,sample())

    def test_world_readable_segment_rejected(self):
        _,name=lab.publish(self.fd,sample())
        os.chmod(self.p/name,0o644)
        with self.assertRaisesRegex(lab.Hold,'UNSAFE_SEGMENT'):
            lab.verified_segment(self.fd,name)

    def test_hardlinked_segment_rejected(self):
        _,name=lab.publish(self.fd,sample())
        os.link(self.p/name,self.p/'another-link')
        with self.assertRaisesRegex(lab.Hold,'UNSAFE_SEGMENT'):
            lab.verified_segment(self.fd,name)

    def test_retention_preview_does_not_delete(self):
        lab.publish(self.fd,sample())
        lab.publish(self.fd,sample('2026-10-29T09:01:00.000Z', 'SSH_TIMEOUT'))
        candidate=lab.retention_preview(self.fd,keep=1)
        self.assertEqual(len(candidate),1)
        self.assertEqual(len(lab.inspect_entries(self.fd)),2)

    def test_overlapping_batches_not_implicitly_deduplicated(self):
        event1=sample()
        event2=sample('2026-10-29T09:01:00.000Z','SSH_TIMEOUT')
        lab.publish(self.fd,event1+event2)
        lab.publish(self.fd,event2)
        self.assertEqual(len(lab.inspect_entries(self.fd)),2)
        # A future streaming architecture MUST address cross-batch overlap explicitly.

    def test_unrelated_corrupt_segment_blocks_new_publication(self):
        _, name = lab.publish(self.fd, sample())
        (self.p/name).write_bytes(b'corrupted\n')
        before = sorted(os.listdir(self.fd))
        with self.assertRaises(lab.Hold):
            lab.publish(self.fd, sample('2026-10-29T09:01:00.000Z'))
        self.assertEqual(sorted(os.listdir(self.fd)), before)

    def test_duplicate_batch_also_checks_unrelated_segment(self):
        lab.publish(self.fd, sample())
        _, name = lab.publish(self.fd, sample('2026-10-29T09:01:00.000Z'))
        (self.p/name).write_bytes(b'corrupted\n')
        with self.assertRaises(lab.Hold):
            lab.publish(self.fd, sample())

    def test_fifo_is_opened_nonblocking_and_rejected_before_read(self):
        name = lab.digest_name(sample())
        os.mkfifo(self.p/name, 0o600)
        # Mock open to verify the nonblocking flag; no test can hang if regressed.
        real_open = os.open
        def bounded_open(path, flags, *args, **kwargs):
            self.assertTrue(flags & os.O_NONBLOCK)
            return real_open(path, flags, *args, **kwargs)
        with mock.patch.object(lab.os, 'open', side_effect=bounded_open):
            with self.assertRaisesRegex(lab.Hold, 'UNSAFE_SEGMENT_METADATA'):
                lab.publish(self.fd, sample('2026-10-29T09:01:00.000Z'))
        self.assertEqual(os.listdir(self.fd), [name])

    def test_unrelated_world_readable_segment_blocks_new_publication(self):
        _, name = lab.publish(self.fd, sample())
        os.chmod(self.p/name, 0o644)
        with self.assertRaisesRegex(lab.Hold, 'UNSAFE_SEGMENT_METADATA'):
            lab.publish(self.fd, sample('2026-10-29T09:01:00.000Z'))

    def test_directory_mode_change_is_rechecked(self):
        os.chmod(self.p, 0o755)
        with self.assertRaisesRegex(lab.Hold, 'PRIVATE_DIRECTORY_REQUIRED'):
            lab.publish(self.fd, sample())
        self.assertEqual(os.listdir(self.fd), [])

    def test_second_open_fails_without_creating_lock_file(self):
        with self.assertRaisesRegex(lab.Hold, 'DIRECTORY_BUSY'):
            lab.open_private_directory(self.p)
        self.assertEqual(os.listdir(self.fd), [])

    def test_raw_second_descriptor_cannot_bypass_writer_lock(self):
        other = os.open(self.p, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with self.assertRaisesRegex(lab.Hold, 'DIRECTORY_BUSY'):
                lab.publish(other, sample())
        finally:
            os.close(other)
        self.assertEqual(os.listdir(self.fd), [])

    def test_closing_holder_releases_lock(self):
        os.close(self.fd)
        self.fd = lab.open_private_directory(self.p)
        self.assertEqual(lab.publish(self.fd, sample())[0], 'PUBLISHED_ATOMIC_SEGMENT')

    def test_file_fsync_failure_has_no_published_segment(self):
        real_fsync = os.fsync
        def fail_file(fd):
            if stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError('synthetic fsync failure')
            return real_fsync(fd)
        with mock.patch.object(lab.os, 'fsync', side_effect=fail_file):
            with self.assertRaises(OSError):
                lab.publish(self.fd, sample())
        self.assertEqual(os.listdir(self.fd), [])

    def test_directory_fsync_failure_is_not_success(self):
        real_fsync = os.fsync
        def fail_directory(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError('synthetic directory fsync failure')
            return real_fsync(fd)
        with mock.patch.object(lab.os, 'fsync', side_effect=fail_directory):
            with self.assertRaises(OSError):
                lab.publish(self.fd, sample())
        # Visibility is not a successful durability ACK; retry verifies the file.
        self.assertEqual(lab.publish(self.fd, sample())[0], 'DUPLICATE_BATCH_NO_WRITE')

    def test_short_writes_and_short_reads_preserve_content(self):
        real_write, real_read = os.write, os.read
        with mock.patch.object(lab.os, 'write', side_effect=lambda fd, b: real_write(fd, b[:7])):
            _, name = lab.publish(self.fd, sample())
        with mock.patch.object(lab.os, 'read', side_effect=lambda fd, n: real_read(fd, min(n, 7))):
            self.assertEqual(lab.verified_segment(self.fd, name), sample())

    def test_zero_write_fails_with_no_segment(self):
        with mock.patch.object(lab.os, 'write', return_value=0):
            with self.assertRaisesRegex(lab.Hold, 'SHORT_WRITE'):
                lab.publish(self.fd, sample())
        self.assertEqual(os.listdir(self.fd), [])

    def test_link_failure_does_not_publish_or_leave_temp(self):
        with mock.patch.object(lab.os, 'link', side_effect=OSError('synthetic link failure')):
            with self.assertRaises(OSError):
                lab.publish(self.fd, sample())
        self.assertEqual(os.listdir(self.fd), [])

    def test_cleanup_failure_leaves_orphan_for_review(self):
        with mock.patch.object(lab.os, 'unlink', side_effect=OSError('synthetic unlink failure')):
            with self.assertRaises(OSError):
                lab.publish(self.fd, sample())
        with self.assertRaisesRegex(lab.Hold, 'ORPHAN'):
            lab.publish(self.fd, sample())

    def test_count_limit_refuses_new_but_permits_verified_duplicate(self):
        with mock.patch.object(lab, 'MAX_SEGMENTS_REVIEWED', 1):
            lab.publish(self.fd, sample())
            self.assertEqual(lab.publish(self.fd, sample())[0], 'DUPLICATE_BATCH_NO_WRITE')
            with self.assertRaisesRegex(lab.Hold, 'SEGMENT_COUNT_LIMIT'):
                lab.publish(self.fd, sample('2026-10-29T09:01:00.000Z'))

    def test_directory_enumeration_stops_at_limit(self):
        lab.publish(self.fd, sample())
        lab.publish(self.fd, sample('2026-10-29T09:01:00.000Z'))
        with mock.patch.object(lab, 'MAX_SEGMENTS_REVIEWED', 1):
            with self.assertRaisesRegex(lab.Hold, 'TOO_MANY_SEGMENTS'):
                lab.inspect_entries(self.fd)

    def test_abrupt_process_exit_preserves_residue_and_releases_lock(self):
        # Real child exits without Python finally blocks. This is not power loss.
        program = '''
import os, sys, stat
sys.path.insert(0, sys.argv[1])
import v0145a_segment_spool as lab
fd = lab.open_private_directory(sys.argv[2])
phase = sys.argv[3]
if phase == 'file_sync':
    original = os.fsync
    def interrupt(fd):
        original(fd)
        if stat.S_ISREG(os.fstat(fd).st_mode):
            os._exit(23)
    os.fsync = interrupt
else:
    original = os.link
    def interrupt(*args, **kwargs):
        original(*args, **kwargs)
        os._exit(23)
    os.link = interrupt
lab.publish(fd, lab.event('2026-10-30T09:00:00.000Z', 'SSH_TIMEOUT'))
'''
        for phase in ('file_sync', 'link'):
            with self.subTest(phase=phase):
                child_path = self.p / phase
                child_path.mkdir(mode=0o700)
                child = subprocess.run([sys.executable, '-B', '-c', program,
                                        str(Path(lab.__file__).parent), str(child_path), phase],
                                       capture_output=True, timeout=5, check=False)
                self.assertEqual(child.returncode, 23, child.stderr.decode())
                reopened = lab.open_private_directory(child_path)
                try:
                    names = os.listdir(reopened)
                    self.assertEqual(sum(bool(lab.TEMP_RE.fullmatch(n)) for n in names), 1)
                    self.assertEqual(sum(bool(lab.FINAL_RE.fullmatch(n)) for n in names),
                                     int(phase == 'link'))
                    with self.assertRaisesRegex(lab.Hold, 'ORPHAN'):
                        lab.publish(reopened, sample())
                    self.assertEqual(sorted(os.listdir(reopened)), sorted(names))
                finally:
                    os.close(reopened)

    def test_duplicate_retries_directory_fsync(self):
        lab.publish(self.fd, sample())
        with mock.patch.object(lab.os, 'fsync', wraps=os.fsync) as barrier:
            self.assertEqual(lab.publish(self.fd, sample())[0], 'DUPLICATE_BATCH_NO_WRITE')
        barrier.assert_called_once_with(self.fd)

    def test_restrictive_umask_still_publishes_exact_private_mode(self):
        prior_umask = os.umask(0o777)
        try:
            _, name = lab.publish(self.fd, sample())
        finally:
            os.umask(prior_umask)
        self.assertEqual(stat.S_IMODE((self.p/name).stat().st_mode), 0o600)
        self.assertEqual(lab.verified_segment(self.fd, name), sample())


if __name__ == '__main__':
    unittest.main()
