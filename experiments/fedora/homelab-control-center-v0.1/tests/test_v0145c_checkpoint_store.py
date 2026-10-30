"""Disposable checkpoint tests; fixed synthetic input, no production/network."""
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import v0145a_segment_spool as spool
import v0145b_segment_replay as replay
import v0145c_checkpoint_store as store


class CheckpointFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='hcc-v0145c-test-', dir='/tmp')
        self.root = Path(self.tmp.name)
        self.events, self.state = self.root/'events', self.root/'state'
        self.events.mkdir(mode=0o700)
        self.state.mkdir(mode=0o700)
        self.spoolfd = spool.open_private_directory(self.events)
        self.statefd = spool.open_private_directory(self.state)
        for minute in ('00', '01'):
            spool.publish(self.spoolfd, spool.event(f'2026-10-30T09:{minute}:00.000Z', 'SSH_TIMEOUT'))
        self.sink = replay.FakeReceiver()

    def tearDown(self):
        if self.spoolfd is not None:
            os.close(self.spoolfd)
        if self.statefd is not None:
            os.close(self.statefd)
        self.tmp.cleanup()

    def count(self):
        return replay.restore_checkpoint(store.read_checkpoint(self.statefd), replay.snapshot(self.spoolfd))

    def initialize(self):
        plan = replay.snapshot(self.spoolfd)
        raw = replay.checkpoint_bytes(plan.digest, 0)
        store.store_checkpoint(self.statefd, raw, plan, None)
        return plan, raw

    def test_first_ack_is_saved_and_reopen_resumes_next_segment(self):
        store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(self.count(), 1)
        os.close(self.statefd)
        self.statefd = spool.open_private_directory(self.state)
        new_receiver = replay.FakeReceiver()
        store.advance_one(self.spoolfd, self.statefd, new_receiver)
        self.assertNotEqual(new_receiver.received[0], self.sink.received[0])
        self.assertEqual(self.count(), 2)

    def test_complete_does_not_send_rewrite_or_delete_segments(self):
        before = {p.name:p.read_bytes() for p in self.events.iterdir()}
        for _ in range(2):
            store.advance_one(self.spoolfd, self.statefd, self.sink)
        saved = (self.state/store.CHECKPOINT).stat()
        self.assertEqual(store.advance_one(self.spoolfd, self.statefd, self.sink), 'COMPLETE_NO_SEND')
        self.assertEqual(len(self.sink.received), 2)
        self.assertEqual((self.state/store.CHECKPOINT).stat().st_mtime_ns, saved.st_mtime_ns)
        self.assertEqual({p.name:p.read_bytes() for p in self.events.iterdir()}, before)

    def test_receiver_error_saves_zero_and_no_advance(self):
        def unavailable(*_):
            raise OSError('synthetic receiver failure')
        with self.assertRaises(OSError):
            store.advance_one(self.spoolfd, self.statefd, unavailable)
        self.assertEqual(self.count(), 0)
        store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(self.count(), 1)

    def test_wrong_ack_does_not_advance(self):
        with self.assertRaisesRegex(spool.Hold, 'ACK_MISMATCH'):
            store.advance_one(self.spoolfd, self.statefd, lambda *_: 'wrong')
        self.assertEqual(self.count(), 0)

    def test_ack_without_checkpoint_store_repeats_attempt(self):
        with self.assertRaises(spool.SimulatedInterrupt):
            store.advance_one(self.spoolfd, self.statefd, self.sink, failpoint='after_ack_before_store')
        self.assertEqual(self.count(), 0)
        store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(self.sink.received[0], self.sink.received[1])

    def test_before_replace_keeps_previous_checkpoint_and_cleans_temp(self):
        _, raw = self.initialize()
        with self.assertRaises(spool.SimulatedInterrupt):
            store.advance_one(self.spoolfd, self.statefd, self.sink,
                              failpoint='after_file_fsync_before_replace')
        self.assertEqual(store.read_checkpoint(self.statefd), raw)
        self.assertEqual(os.listdir(self.statefd), [store.CHECKPOINT])

    def test_after_replace_exception_leaves_valid_acked_prefix(self):
        self.initialize()
        with self.assertRaises(spool.SimulatedInterrupt):
            store.advance_one(self.spoolfd, self.statefd, self.sink,
                              failpoint='after_replace_before_directory_fsync')
        self.assertEqual(self.count(), 1)
        self.assertEqual(os.listdir(self.statefd), [store.CHECKPOINT])
        # Ordinary exception, not a power-loss durability acknowledgement.
        store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(self.count(), 2)

    def test_corrupt_checkpoint_never_falls_back_to_zero(self):
        self.initialize()
        (self.state/store.CHECKPOINT).write_bytes(b'{}')
        with self.assertRaises(spool.Hold):
            store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(self.sink.received, [])
        self.assertEqual((self.state/store.CHECKPOINT).read_bytes(), b'{}')

    def test_added_segment_invalidates_saved_snapshot_before_send(self):
        self.initialize()
        spool.publish(self.spoolfd, spool.event('2026-10-30T09:02:00.000Z', 'SSH_TIMEOUT'))
        with self.assertRaisesRegex(spool.Hold, 'SNAPSHOT_CHANGED'):
            store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(self.sink.received, [])

    def test_corrupt_segment_prevents_initial_state_and_receive(self):
        first = sorted(self.events.iterdir())[0]
        first.write_bytes(b'corrupt')
        with self.assertRaises(spool.Hold):
            store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(os.listdir(self.statefd), [])
        self.assertEqual(self.sink.received, [])

    def test_orphan_or_unknown_file_blocks_without_deletion(self):
        for name in ('.checkpoint-'+'a'*32+'.tmp', 'unknown.json'):
            with self.subTest(name=name):
                item = self.state/name
                item.write_bytes(b'synthetic residue')
                with self.assertRaises(spool.Hold):
                    store.advance_one(self.spoolfd, self.statefd, self.sink)
                self.assertEqual(item.read_bytes(), b'synthetic residue')
                item.unlink()  # Test-only reset; module never removes orphan state.
        self.assertEqual(self.sink.received, [])

    def test_same_directory_is_rejected_before_any_write(self):
        with self.assertRaisesRegex(spool.Hold, 'SEPARATE_STATE'):
            store.advance_one(self.spoolfd, self.spoolfd, self.sink)
        self.assertEqual(os.listdir(self.statefd), [])

    def test_fifo_checkpoint_open_is_nonblocking(self):
        os.mkfifo(self.state/store.CHECKPOINT, 0o600)
        original = os.open
        def checked_open(path, flags, *args, **kwargs):
            self.assertTrue(flags & os.O_NONBLOCK)
            return original(path, flags, *args, **kwargs)
        with mock.patch.object(store.os, 'open', side_effect=checked_open):
            with self.assertRaisesRegex(spool.Hold, 'UNSAFE_CHECKPOINT'):
                store.read_checkpoint(self.statefd)

    def test_symlink_checkpoint_is_rejected(self):
        (self.state/store.CHECKPOINT).symlink_to(self.root/'missing')
        with self.assertRaises(OSError):
            store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(self.sink.received, [])

    def test_unsafe_modes_hardlink_and_size_reject(self):
        self.initialize()
        saved = self.state/store.CHECKPOINT
        for mode in (0o644, 0o400):
            os.chmod(saved, mode)
            with self.assertRaisesRegex(spool.Hold, 'UNSAFE_CHECKPOINT'):
                store.read_checkpoint(self.statefd)
        os.chmod(saved, 0o600)
        extra = self.root/'extra-link'
        os.link(saved, extra)
        with self.assertRaisesRegex(spool.Hold, 'UNSAFE_CHECKPOINT'):
            store.read_checkpoint(self.statefd)
        extra.unlink()
        for raw in (b'', b'x'*257):
            saved.write_bytes(raw)
            with self.assertRaisesRegex(spool.Hold, 'UNSAFE_CHECKPOINT'):
                store.read_checkpoint(self.statefd)

    def test_private_state_directory_rechecked(self):
        os.chmod(self.state, 0o755)
        with self.assertRaisesRegex(spool.Hold, 'PRIVATE_DIRECTORY'):
            store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(os.listdir(self.statefd), [])

    def test_short_io_and_restrictive_umask_preserve_private_checkpoint(self):
        original_read, original_write = os.read, os.write
        prior_umask = os.umask(0o777)
        try:
            with mock.patch.object(store.os, 'write', side_effect=lambda fd, b:original_write(fd,b[:5])):
                store.advance_one(self.spoolfd, self.statefd, self.sink)
        finally:
            os.umask(prior_umask)
        self.assertEqual(stat.S_IMODE((self.state/store.CHECKPOINT).stat().st_mode), 0o600)
        with mock.patch.object(store.os, 'read', side_effect=lambda fd,n:original_read(fd,min(n,5))):
            self.assertEqual(self.count(), 1)

    def test_file_sync_error_preserves_old_prefix(self):
        _, original = self.initialize()
        fsync = os.fsync
        def fail_file(fd):
            if stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError('synthetic file fsync failure')
            return fsync(fd)
        with mock.patch.object(store.os, 'fsync', side_effect=fail_file):
            with self.assertRaises(OSError):
                store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(store.read_checkpoint(self.statefd), original)
        self.assertEqual(len(self.sink.received), 1)

    def test_directory_sync_error_before_receive_blocks_progress(self):
        self.initialize()
        with mock.patch.object(store.os, 'fsync', side_effect=OSError('synthetic directory fsync')):
            with self.assertRaises(OSError):
                store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(self.count(), 0)
        self.assertEqual(self.sink.received, [])

    def test_replace_failure_keeps_prior_state(self):
        _, original = self.initialize()
        with mock.patch.object(store.os, 'replace', side_effect=OSError('synthetic replace failure')):
            with self.assertRaises(OSError):
                store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(store.read_checkpoint(self.statefd), original)
        self.assertEqual(os.listdir(self.statefd), [store.CHECKPOINT])

    def test_store_refuses_prefix_jumps_rewind_and_stale_expected_bytes(self):
        plan, zero = self.initialize()
        one = replay.checkpoint_bytes(plan.digest, 1)
        two = replay.checkpoint_bytes(plan.digest, 2)
        with self.assertRaisesRegex(spool.Hold, 'PREFIX_STEP'):
            store.store_checkpoint(self.statefd, two, plan, zero)
        store.store_checkpoint(self.statefd, one, plan, zero)
        with self.assertRaisesRegex(spool.Hold, 'PREFIX_STEP'):
            store.store_checkpoint(self.statefd, zero, plan, one)
        with self.assertRaisesRegex(spool.Hold, 'EXPECTATION_CHANGED'):
            store.store_checkpoint(self.statefd, two, plan, zero)

    def test_initial_checkpoint_cannot_claim_an_ack(self):
        plan = replay.snapshot(self.spoolfd)
        with self.assertRaisesRegex(spool.Hold, 'INITIAL_PREFIX'):
            store.store_checkpoint(self.statefd, replay.checkpoint_bytes(plan.digest, 1), plan, None)
        self.assertEqual(os.listdir(self.statefd), [])

    def test_unsupported_failpoint_and_nonbytes_precede_writes(self):
        plan = replay.snapshot(self.spoolfd)
        with self.assertRaisesRegex(spool.Hold, 'UNSUPPORTED_FAILPOINT'):
            store.advance_one(self.spoolfd, self.statefd, self.sink, failpoint='bad')
        with self.assertRaisesRegex(spool.Hold, 'BYTES_REQUIRED'):
            store.store_checkpoint(self.statefd, None, plan, None)
        self.assertEqual(os.listdir(self.statefd), [])

    def test_independent_process_uses_saved_prefix(self):
        store.advance_one(self.spoolfd, self.statefd, self.sink)
        os.close(self.spoolfd)
        os.close(self.statefd)
        self.spoolfd = self.statefd = None
        program = '''
import os,sys
sys.path.insert(0,sys.argv[1])
import v0145a_segment_spool as a
import v0145b_segment_replay as b
import v0145c_checkpoint_store as c
sf,cf=a.open_private_directory(sys.argv[2]),a.open_private_directory(sys.argv[3])
try:
    plan=b.snapshot(sf)
    sink=b.FakeReceiver()
    assert b.restore_checkpoint(c.read_checkpoint(cf),plan)==1
    assert c.advance_one(sf,cf,sink)=='ACKNOWLEDGED_CHECKPOINT_FILE'
    assert sink.received==[(plan.segments[1].name,plan.segments[1].content)]
    assert b.restore_checkpoint(c.read_checkpoint(cf),plan)==2
finally:
    os.close(cf)
    os.close(sf)
'''
        result = subprocess.run([sys.executable,'-B','-c',program,str(Path(store.__file__).parent),
                                 str(self.events),str(self.state)],capture_output=True,timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.spoolfd = spool.open_private_directory(self.events)
        self.statefd = spool.open_private_directory(self.state)
        self.assertEqual(self.count(), 2)

    def test_abrupt_child_exit_before_and_after_replace(self):
        program = '''
import os,sys,stat
sys.path.insert(0,sys.argv[1])
import v0145a_segment_spool as a
import v0145b_segment_replay as b
import v0145c_checkpoint_store as c
sf,cf=a.open_private_directory(sys.argv[2]),a.open_private_directory(sys.argv[3])
if sys.argv[4]=='file_fsync':
    original=os.fsync
    def interrupt(fd):
        original(fd)
        if stat.S_ISREG(os.fstat(fd).st_mode):
            os._exit(23)
    os.fsync=interrupt
else:
    original=os.replace
    def interrupt(*args,**kwargs):
        original(*args,**kwargs)
        os._exit(23)
    os.replace=interrupt
c.advance_one(sf,cf,b.FakeReceiver())
'''
        plan = replay.snapshot(self.spoolfd)
        zero = replay.checkpoint_bytes(plan.digest, 0)
        for phase in ('file_fsync', 'replace'):
            with self.subTest(phase=phase):
                case = self.root/phase
                case.mkdir(mode=0o700)
                casefd = spool.open_private_directory(case)
                try:
                    store.store_checkpoint(casefd, zero, plan, None)
                finally:
                    os.close(casefd)
                os.close(self.spoolfd)
                self.spoolfd = None
                try:
                    result = subprocess.run([sys.executable,'-B','-c',program,
                                             str(Path(store.__file__).parent),str(self.events),
                                             str(case),phase],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode, 23, result.stderr.decode())
                finally:
                    self.spoolfd = spool.open_private_directory(self.events)
                casefd = spool.open_private_directory(case)
                try:
                    if phase == 'file_fsync':
                        self.assertEqual((case/store.CHECKPOINT).read_bytes(), zero)
                        self.assertEqual(len(os.listdir(casefd)), 2)
                        with self.assertRaisesRegex(spool.Hold, 'ORPHAN_CHECKPOINT'):
                            store.advance_one(self.spoolfd, casefd, self.sink)
                    else:
                        self.assertEqual(os.listdir(casefd), [store.CHECKPOINT])
                        self.assertEqual(replay.restore_checkpoint(store.read_checkpoint(casefd), plan), 1)
                        # Current visibility only; this does not prove crash durability.
                        store.advance_one(self.spoolfd, casefd, self.sink)
                        self.assertEqual(replay.restore_checkpoint(store.read_checkpoint(casefd), plan), 2)
                finally:
                    os.close(casefd)

    def test_final_directory_sync_error_is_not_a_success_ack(self):
        self.initialize()
        original = os.fsync
        directory_syncs = 0
        def fail_second_directory(fd):
            nonlocal directory_syncs
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                directory_syncs += 1
                if directory_syncs == 2:
                    raise OSError('synthetic post-replace directory failure')
            return original(fd)
        with mock.patch.object(store.os, 'fsync', side_effect=fail_second_directory):
            with self.assertRaises(OSError):
                store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(self.count(), 1)
        self.assertEqual(len(self.sink.received), 1)
        store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(self.count(), 2)

    def test_cleanup_failure_requires_review(self):
        self.initialize()
        with mock.patch.object(store.os, 'unlink', side_effect=OSError('synthetic unlink failure')):
            with self.assertRaises(OSError):
                store.advance_one(self.spoolfd, self.statefd, self.sink,
                                  failpoint='after_file_fsync_before_replace')
        before = sorted(os.listdir(self.statefd))
        with self.assertRaisesRegex(spool.Hold, 'ORPHAN_CHECKPOINT'):
            store.advance_one(self.spoolfd, self.statefd, self.sink)
        self.assertEqual(sorted(os.listdir(self.statefd)), before)

    def test_second_descriptor_cannot_bypass_state_lock(self):
        other = os.open(self.state, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with self.assertRaisesRegex(spool.Hold, 'DIRECTORY_BUSY'):
                store.advance_one(self.spoolfd, other, self.sink)
        finally:
            os.close(other)
        self.assertEqual(self.sink.received, [])


if __name__ == '__main__':
    unittest.main()
