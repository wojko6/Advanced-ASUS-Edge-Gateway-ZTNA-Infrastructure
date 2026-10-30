"""Offline snapshot replay: no journal, network, Alloy or production services."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import v0145a_segment_spool as spool
import v0145b_segment_replay as replay


def event(minute, kind='SSH_TIMEOUT'):
    return spool.event(f'2026-10-30T09:{minute:02d}:00.000Z', kind)


class SnapshotReplay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='hcc-v0145b-test-', dir='/tmp')
        self.path = Path(self.tmp.name)
        os.chmod(self.path, 0o700)
        self.fd = spool.open_private_directory(self.path)
        self.sink = replay.FakeReceiver()

    def tearDown(self):
        os.close(self.fd)
        self.tmp.cleanup()

    def publish(self, raw):
        return spool.publish(self.fd, raw)[1]

    def test_empty_snapshot_completes_without_receiver_call(self):
        result, cp = replay.replay_one(self.fd, None, self.sink)
        self.assertEqual(result, 'COMPLETE_NO_SEND')
        self.assertEqual(replay.restore_checkpoint(cp, replay.snapshot(self.fd)), 0)
        self.assertEqual(self.sink.received, [])

    def test_out_of_publication_order_is_replayed_chronologically(self):
        late, early = self.publish(event(2)), self.publish(event(1))
        _, cp = replay.replay_one(self.fd, None, self.sink)
        _, cp = replay.replay_one(self.fd, cp, self.sink)
        self.assertEqual([name for name, _ in self.sink.received], [early, late])
        self.assertEqual(replay.replay_one(self.fd, cp, self.sink)[0], 'COMPLETE_NO_SEND')
        self.assertEqual(len(self.sink.received), 2)

    def test_restored_checkpoint_skips_only_acknowledged_prefix(self):
        self.publish(event(1))
        second = self.publish(event(2))
        _, cp = replay.replay_one(self.fd, None, self.sink)
        fresh_receiver = replay.FakeReceiver()
        replay.replay_one(self.fd, bytes(cp), fresh_receiver)
        self.assertEqual([name for name, _ in fresh_receiver.received], [second])

    def test_receiver_exception_does_not_return_checkpoint(self):
        self.publish(event(1))
        def reject(*_):
            raise OSError('synthetic receiver unavailable')
        with self.assertRaises(OSError):
            replay.replay_one(self.fd, None, reject)
        replay.replay_one(self.fd, None, self.sink)
        self.assertEqual(len(self.sink.received), 1)

    def test_wrong_ack_does_not_advance(self):
        self.publish(event(1))
        with self.assertRaisesRegex(spool.Hold, 'ACK_MISMATCH'):
            replay.replay_one(self.fd, None, lambda *_: 'wrong-segment')
        replay.replay_one(self.fd, None, self.sink)
        self.assertEqual(len(self.sink.received), 1)

    def test_ack_lost_before_checkpoint_replays_duplicate_attempt(self):
        self.publish(event(1))
        with self.assertRaises(spool.SimulatedInterrupt):
            replay.replay_one(self.fd, None, self.sink, failpoint='after_ack_before_checkpoint')
        _, cp = replay.replay_one(self.fd, None, self.sink)
        self.assertEqual(self.sink.received[0], self.sink.received[1])
        self.assertEqual(replay.replay_one(self.fd, cp, self.sink)[0], 'COMPLETE_NO_SEND')

    def test_added_segment_invalidates_checkpoint_before_send(self):
        self.publish(event(1))
        _, cp = replay.replay_one(self.fd, None, self.sink)
        self.publish(event(2))
        with self.assertRaisesRegex(spool.Hold, 'SNAPSHOT_CHANGED'):
            replay.replay_one(self.fd, cp, self.sink)
        self.assertEqual(len(self.sink.received), 1)

    def test_removed_segment_invalidates_checkpoint_before_send(self):
        first = self.publish(event(1))
        self.publish(event(2))
        _, cp = replay.replay_one(self.fd, None, self.sink)
        os.unlink(self.path/first)  # Test-only mutation; implementation has no GC.
        with self.assertRaisesRegex(spool.Hold, 'SNAPSHOT_CHANGED'):
            replay.replay_one(self.fd, cp, self.sink)
        self.assertEqual(len(self.sink.received), 1)

    def test_corrupt_later_segment_blocks_even_first_send(self):
        self.publish(event(1))
        later = self.publish(event(2))
        (self.path/later).write_bytes(b'corrupt\n')
        with self.assertRaises(spool.Hold):
            replay.replay_one(self.fd, None, self.sink)
        self.assertEqual(self.sink.received, [])

    def test_orphan_temp_blocks_send(self):
        self.publish(event(1))
        (self.path/('.tmp-'+'a'*32)).write_bytes(b'test orphan')
        with self.assertRaisesRegex(spool.Hold, 'ORPHAN'):
            replay.replay_one(self.fd, None, self.sink)
        self.assertEqual(self.sink.received, [])

    def test_cross_batch_collision_is_hold_not_silent_dedup(self):
        self.publish(event(1) + event(2))
        self.publish(event(2))
        before = sorted(os.listdir(self.fd))
        with self.assertRaisesRegex(spool.Hold, 'AMBIGUOUS_CROSS_BATCH_EVENT'):
            replay.replay_one(self.fd, None, self.sink)
        self.assertEqual(self.sink.received, [])
        self.assertEqual(sorted(os.listdir(self.fd)), before)

    def test_interleaved_ranges_need_separate_merge_contract(self):
        self.publish(event(1) + event(3))
        self.publish(event(2))
        with self.assertRaisesRegex(spool.Hold, 'INTERLEAVED_SEGMENT_TIMES'):
            replay.replay_one(self.fd, None, self.sink)
        self.assertEqual(self.sink.received, [])

    def test_same_time_different_kind_is_allowed(self):
        self.publish(event(1))
        self.publish(event(1, 'COLLECTOR_EXIT_255'))
        self.assertEqual(len(replay.snapshot(self.fd).segments), 2)

    def test_exact_batch_replay_does_not_change_snapshot(self):
        self.publish(event(1))
        initial = replay.snapshot(self.fd)
        self.publish(event(1))
        self.assertEqual(replay.snapshot(self.fd), initial)

    def test_replay_leaves_directory_and_files_unchanged(self):
        name = self.publish(event(1))
        before = (self.path/name).stat()
        directory_mtime = self.path.stat().st_mtime_ns
        replay.replay_one(self.fd, None, self.sink)
        after = (self.path/name).stat()
        self.assertEqual((before.st_size, before.st_mtime_ns, before.st_nlink),
                         (after.st_size, after.st_mtime_ns, after.st_nlink))
        self.assertEqual(self.path.stat().st_mtime_ns, directory_mtime)
        self.assertEqual(os.listdir(self.fd), [name])

    def test_illegal_failpoint_precedes_send(self):
        self.publish(event(1))
        with self.assertRaisesRegex(spool.Hold, 'UNSUPPORTED_FAILPOINT'):
            replay.replay_one(self.fd, None, self.sink, failpoint='unknown')
        self.assertEqual(self.sink.received, [])


class CheckpointContract(unittest.TestCase):
    def setUp(self):
        self.plan = replay.Snapshot('a'*64, ())
        self.valid = {'schema': replay.SCHEMA, 'snapshot': self.plan.digest, 'acknowledged': 0}

    def reject(self, raw):
        with self.assertRaises(spool.Hold):
            replay.restore_checkpoint(raw, self.plan)

    def test_type_size_json_and_nonfinite(self):
        for raw in ('text', b'', b'x'*257, b'null', b'[]', b'\xff', b'{', b'NaN'):
            with self.subTest(raw=repr(raw)[:40]):
                self.reject(raw)

    def test_boolean_negative_and_overshoot_count(self):
        for count in (True, False, -1, 1, 0.0, '0', None):
            self.reject(json.dumps(dict(self.valid, acknowledged=count)).encode())

    def test_extra_missing_and_duplicate_keys(self):
        self.reject(json.dumps(dict(self.valid, extra='private')).encode())
        self.reject(b'{}')
        raw = json.dumps(self.valid).encode()
        self.reject(raw.replace(b'"acknowledged":', b'"acknowledged":0,"acknowledged":'))

    def test_wrong_schema_and_hash(self):
        for key, value in (('schema', 'unknown'), ('snapshot', 'b'*64), ('snapshot', 1)):
            self.reject(json.dumps(dict(self.valid, **{key:value})).encode())

    def test_no_checkpoint_and_round_trip(self):
        self.assertEqual(replay.restore_checkpoint(None, self.plan), 0)
        self.assertEqual(replay.restore_checkpoint(replay.checkpoint_bytes('a'*64, 0), self.plan), 0)


if __name__ == '__main__':
    unittest.main()
