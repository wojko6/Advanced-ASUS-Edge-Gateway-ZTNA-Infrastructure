"""Disposable E source / F ACK / file receiver; no real transport or services."""
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
import v0145f_delivery_ack as delivery
import v0145g_file_receiver as receiver

KEY = identity.SYNTHETIC_KEY


def event(number):
    return identity.envelope(f'synthetic-cursor-{number:04d}')


class PureContract(unittest.TestCase):
    def test_self_test_is_memory_only(self):
        with mock.patch('builtins.open', side_effect=AssertionError('file')), \
             mock.patch.object(os, 'open', side_effect=AssertionError('os.open')), \
             mock.patch.object(socket, 'socket', side_effect=AssertionError('network')), \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('process')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            receiver.self_test()
        self.assertIn('V0145G_SELFTEST=PASS_PURE_SYNTHETIC_ONLY', output.getvalue())

    def test_lab_has_no_network_or_subprocess(self):
        with mock.patch.object(socket, 'socket', side_effect=AssertionError('network')), \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('process')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            receiver.run_lab()
        self.assertIn('V0145G_RESULT=PASS_DISPOSABLE_FILE_RECEIVER_ONLY', output.getvalue())
        self.assertIn('TEMP_STATE_REMOVED=YES', output.getvalue())


class FileReceiver(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='hcc-v0145g-test-', dir='/tmp')
        self.root = Path(self.tmp.name)
        self.paths = [self.root / name for name in ('source', 'acks', 'receiver')]
        for path in self.paths:
            path.mkdir(mode=0o700)
        self.fds = [spool.open_private_directory(path) for path in self.paths]
        handoff.publish_handoff(self.fds[0], event(1) + event(2) + event(3), KEY)
        self.scope = identity.scope_for(KEY)
        self.payloads = handoff.read_handoff(self.fds[0]).events
        self.ids = [json.loads(payload)['event_id'] for payload in self.payloads]

    def tearDown(self):
        self.close_all()
        self.tmp.cleanup()

    def close_all(self):
        while self.fds:
            os.close(self.fds.pop())

    def reopen(self):
        self.close_all()
        self.fds = [spool.open_private_directory(path) for path in self.paths]

    def advance(self, **kwargs):
        return receiver.dispatch_one(*self.fds, **kwargs)

    def received(self):
        return handoff.read_handoff(self.fds[2])

    def ack_count(self):
        state = delivery.read_state(self.fds[1])
        return 0 if state is None else len(state.acknowledged)

    def initialize_ack(self):
        delivery.store_state(self.fds[1], delivery.AckState(self.scope, ()), None)

    def put(self, index=0, **kwargs):
        return receiver.receive_one(self.fds[2], self.scope, self.ids[index], self.payloads[index], **kwargs)

    def receiver_file(self):
        return self.paths[2] / handoff.NAME

    def file_identity(self):
        info = self.receiver_file().stat()
        return info.st_ino, info.st_mtime_ns, self.receiver_file().read_bytes()

    def write_receiver(self, payloads):
        self.receiver_file().write_bytes(handoff.encode_snapshot(self.scope, payloads))
        self.receiver_file().chmod(0o600)

    def test_full_payload_exists_when_fixture_ack_returns(self):
        ack = self.put()
        self.assertEqual(ack, {'schema': delivery.ACK_SCHEMA, 'scope': self.scope,
                              'event_id': self.ids[0],
                              'payload_sha256': delivery.payload_hash(self.payloads[0])})
        self.assertEqual(self.received().events, (self.payloads[0],))
        self.assertEqual(os.listdir(self.fds[1]), [])
        self.assertEqual(stat.S_IMODE(self.receiver_file().stat().st_mode), 0o600)

    def test_strict_record_schema_binding_and_canonical_bytes_before_write(self):
        obj = json.loads(self.payloads[0])
        extra = dict(obj, MESSAGE='synthetic-private-field')
        wrong_time = dict(obj, time='2026-02-30T01:00:00.000000Z')
        bad = [(self.scope, self.ids[0], raw) for raw in
               (None, b'', b'\xff', b'null', b'NaN', b'{' + b'x' * 4096,
                self.payloads[0] + b'\n', json.dumps(obj, indent=2).encode(),
                identity.canonical(extra), identity.canonical(wrong_time),
                self.payloads[0].replace(b'"kind":', b'"kind":"SSH_TIMEOUT","kind":', 1))]
        bad += [(self.scope, 'a' * 64, self.payloads[0]), ('a' * 64, self.ids[0], self.payloads[0]),
                (True, self.ids[0], self.payloads[0]), (self.scope, 42, self.payloads[0])]
        for scope, event_id, payload in bad:
            with self.subTest(scope=type(scope).__name__, length=len(payload) if type(payload) is bytes else None):
                with self.assertRaises(spool.Hold):
                    receiver.receive_one(self.fds[2], scope, event_id, payload)
                self.assertEqual(os.listdir(self.fds[2]), [])

    def test_duplicate_keeps_same_file_and_requires_directory_sync(self):
        self.put()
        before = self.file_identity()
        self.assertEqual(self.put(), receiver.fixture_ack(self.scope, self.ids[0], self.payloads[0]))
        self.assertEqual(self.file_identity(), before)
        with mock.patch.object(os, 'fsync', side_effect=OSError('synthetic sync failure')):
            with self.assertRaises(OSError):
                self.put()
        self.assertEqual(self.file_identity(), before)

    def test_same_id_changed_payload_holds_without_replacing_any_record(self):
        self.put()
        before = self.file_identity()
        changed = identity.canonical(dict(json.loads(self.payloads[0]), kind='HTTP_IMPORT_TIMEOUT'))
        with self.assertRaisesRegex(spool.Hold, 'SAME_ID_DIFFERENT_PAYLOAD'):
            receiver.receive_one(self.fds[2], self.scope, self.ids[0], changed)
        self.assertEqual(self.file_identity(), before)

    def test_receiver_scope_change_rejects_atomically(self):
        self.put()
        before = self.file_identity()
        other_key = bytes(reversed(KEY))
        payload = identity.normalized_events(event(4), other_key)[0]
        with self.assertRaisesRegex(spool.Hold, 'RECEIVER_SCOPE_CHANGED'):
            receiver.receive_one(self.fds[2], identity.scope_for(other_key), json.loads(payload)['event_id'], payload)
        self.assertEqual(self.file_identity(), before)

    def test_reopen_all_stores_resumes_and_completion_does_not_write(self):
        self.advance()
        self.reopen()
        self.assertEqual(len(self.received().events), 1)
        self.assertEqual(self.ack_count(), 1)
        self.advance()
        self.advance()
        before = self.file_identity()
        self.assertEqual(self.advance(), 'COMPLETE_NO_SEND')
        self.assertEqual(self.file_identity(), before)
        self.assertEqual(self.received(), handoff.read_handoff(self.fds[0]))
        self.assertEqual(self.ack_count(), 3)

    def test_verified_ack_before_store_reopens_and_deduplicates_receiver(self):
        with self.assertRaises(spool.SimulatedInterrupt):
            self.advance(ack_failpoint='after_receiver_ack_before_store')
        self.assertEqual(self.ack_count(), 0)
        before = self.file_identity()
        self.reopen()
        self.advance()
        self.assertEqual(self.file_identity(), before)
        self.assertEqual(self.ack_count(), 1)

    def test_receiver_committed_before_return_error_retries_without_duplicate_write(self):
        with self.assertRaises(spool.Hold) as caught:
            self.advance(receiver_failpoint='after_dir_fsync_before_return')
        self.assertIsInstance(caught.exception.__cause__, spool.SimulatedInterrupt)
        self.assertEqual(self.ack_count(), 0)
        before = self.file_identity()
        self.reopen()
        self.advance()
        self.assertEqual(self.file_identity(), before)
        self.assertEqual(self.ack_count(), 1)

    def test_receiver_pre_replace_failure_keeps_old_state_and_ack(self):
        self.advance()
        before = self.file_identity()
        with self.assertRaises(spool.Hold):
            self.advance(receiver_failpoint='after_temp_fsync_before_replace')
        self.assertEqual(self.file_identity(), before)
        self.assertEqual(self.ack_count(), 1)
        self.assertEqual(os.listdir(self.fds[2]), [handoff.NAME])

    def test_receiver_post_replace_failure_does_not_advance_ack(self):
        self.advance()
        with self.assertRaises(spool.Hold):
            self.advance(receiver_failpoint='after_replace_before_dir_fsync')
        self.assertEqual(len(self.received().events), 2)
        self.assertEqual(self.ack_count(), 1)
        before = self.file_identity()
        self.advance()
        self.assertEqual(self.file_identity(), before)
        self.assertEqual(self.ack_count(), 2)

    def test_ack_replace_error_retains_receiver_for_idempotent_retry(self):
        self.initialize_ack()
        original = os.replace
        def fail_ack(*args, **kwargs):
            if kwargs.get('dst_dir_fd') == self.fds[1]:
                raise OSError('synthetic ack replace')
            return original(*args, **kwargs)
        with mock.patch.object(os, 'replace', side_effect=fail_ack):
            with self.assertRaises(OSError):
                self.advance()
        self.assertEqual(self.ack_count(), 0)
        before = self.file_identity()
        self.advance()
        self.assertEqual(self.file_identity(), before)
        self.assertEqual(self.ack_count(), 1)

    def test_receiver_file_sync_replace_and_zero_write_errors_do_not_ack(self):
        self.initialize_ack()
        sync, replace = os.fsync, os.replace
        def fail_file(fd):
            if stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError('synthetic receiver file sync')
            return sync(fd)
        def fail_receiver(*args, **kwargs):
            if kwargs.get('dst_dir_fd') == self.fds[2]:
                raise OSError('synthetic receiver replace')
            return replace(*args, **kwargs)
        patches = [mock.patch.object(os, 'fsync', side_effect=fail_file),
                   mock.patch.object(os, 'replace', side_effect=fail_receiver),
                   mock.patch.object(os, 'write', return_value=0)]
        for patch in patches:
            with patch:
                with self.assertRaises(spool.Hold):
                    self.advance()
            self.assertIsNone(self.received())
            self.assertEqual(self.ack_count(), 0)

    def test_receiver_directory_sync_failure_withholds_ack_until_retry_barrier(self):
        self.initialize_ack()
        sync = os.fsync
        def fail_receiver(fd):
            if fd == self.fds[2]:
                raise OSError('synthetic receiver directory sync')
            return sync(fd)
        with mock.patch.object(os, 'fsync', side_effect=fail_receiver):
            for _ in range(2):
                with self.assertRaises(spool.Hold):
                    self.advance()
                self.assertEqual(self.ack_count(), 0)
        before = self.file_identity()
        self.advance()
        self.assertEqual(self.file_identity(), before)
        self.assertEqual(self.ack_count(), 1)

    def test_corrupt_receiver_blocks_before_initializing_ack(self):
        self.put()
        self.receiver_file().write_bytes(b'corrupt synthetic receiver')
        with self.assertRaises(spool.Hold):
            self.advance()
        self.assertEqual(os.listdir(self.fds[1]), [])

    def test_missing_receiver_is_hold_even_after_all_acks_complete(self):
        for _ in range(3):
            self.advance()
        self.receiver_file().unlink()
        with self.assertRaisesRegex(spool.Hold, 'ACK_WITHOUT_MATCHING_RECEIVER'):
            self.advance()
        self.assertEqual(self.ack_count(), 3)
        self.assertEqual(len(handoff.read_handoff(self.fds[0]).events), 3)

    def test_removed_received_record_with_new_valid_digest_cannot_keep_ack(self):
        self.advance()
        self.advance()
        self.write_receiver(self.received().events[1:])
        with self.assertRaisesRegex(spool.Hold, 'ACK_WITHOUT_MATCHING_RECEIVER'):
            self.advance()
        self.assertEqual(self.ack_count(), 2)

    def test_changed_received_payload_with_valid_digest_holds(self):
        self.advance()
        changed = identity.canonical(dict(json.loads(self.received().events[0]), kind='HTTP_IMPORT_TIMEOUT'))
        self.write_receiver((changed,))
        with self.assertRaisesRegex(spool.Hold, 'RECEIVER_SOURCE_RECORD_MISSING_OR_CHANGED'):
            self.advance()
        self.assertEqual(self.ack_count(), 1)

    def test_unrelated_receiver_record_prevents_ack_initialization(self):
        payload = identity.normalized_events(event(4), KEY)[0]
        receiver.receive_one(self.fds[2], self.scope, json.loads(payload)['event_id'], payload)
        with self.assertRaisesRegex(spool.Hold, 'RECEIVER_SOURCE_RECORD_MISSING_OR_CHANGED'):
            self.advance()
        self.assertEqual(os.listdir(self.fds[1]), [])

    def test_receiver_source_scope_mismatch_is_hold_before_ack_initialization(self):
        key = bytes(reversed(KEY))
        payload = identity.normalized_events(event(4), key)[0]
        receiver.receive_one(self.fds[2], identity.scope_for(key), json.loads(payload)['event_id'], payload)
        with self.assertRaisesRegex(spool.Hold, 'RECEIVER_SOURCE_SCOPE_MISMATCH'):
            self.advance()
        self.assertEqual(os.listdir(self.fds[1]), [])

    def test_valid_looking_ack_with_wrong_receiver_hash_holds(self):
        self.advance()
        forged = delivery.AckState(self.scope, ((self.ids[0], 'a' * 64),))
        (self.paths[1] / delivery.NAME).write_bytes(delivery.encode_state(forged))
        with self.assertRaisesRegex(spool.Hold, 'ACK_WITHOUT_MATCHING_RECEIVER'):
            self.advance()
        self.assertEqual(len(self.received().events), 1)

    def test_source_missing_removed_or_changed_cannot_skip_received_record(self):
        self.advance()
        path = self.paths[0] / handoff.NAME
        original = path.read_bytes()
        changes = [handoff.encode_snapshot(self.scope, self.payloads[1:]),
                   handoff.encode_snapshot(self.scope, (identity.canonical(dict(json.loads(self.payloads[0]),
                                                        kind='HTTP_IMPORT_TIMEOUT')), *self.payloads[1:]))]
        for content in changes:
            path.write_bytes(content)
            with self.assertRaisesRegex(spool.Hold, 'RECEIVER_SOURCE_RECORD_MISSING_OR_CHANGED'):
                self.advance()
            path.write_bytes(original)
        path.unlink()
        with self.assertRaisesRegex(spool.Hold, 'HANDOFF_REQUIRED'):
            self.advance()
        self.assertEqual(self.ack_count(), 1)

    def test_new_lower_id_after_completion_is_delivered(self):
        for _ in range(3):
            self.advance()
        number = next(n for n in range(4, 256)
                      if json.loads(identity.normalized_events(event(n), KEY)[0])['event_id'] < self.ids[0])
        handoff.publish_handoff(self.fds[0], event(number), KEY)
        self.advance()
        self.assertEqual(self.ack_count(), 4)
        self.assertEqual(self.received(), handoff.read_handoff(self.fds[0]))
        self.assertEqual(self.advance(), 'COMPLETE_NO_SEND')

    def test_deleted_ack_replays_without_rewriting_retained_receiver(self):
        for _ in range(3):
            self.advance()
        before = self.file_identity()
        (self.paths[1] / delivery.NAME).unlink()  # Explicit negative fixture.
        for _ in range(3):
            self.advance()
        self.assertEqual(self.file_identity(), before)
        self.assertEqual(self.ack_count(), 3)

    def test_paired_state_loss_is_not_authenticated_or_detected(self):
        for _ in range(3):
            self.advance()
        (self.paths[1] / delivery.NAME).unlink()
        self.receiver_file().unlink()  # Negative fixture, never automatic recovery.
        self.advance()
        self.assertEqual(self.ack_count(), 1)
        self.assertEqual(len(self.received().events), 1)
        self.assertEqual(len(handoff.read_handoff(self.fds[0]).events), 3)

    def test_corrupt_ack_or_source_never_changes_receiver(self):
        self.advance()
        before = self.file_identity()
        for path in (self.paths[0] / handoff.NAME, self.paths[1] / delivery.NAME):
            content = path.read_bytes()
            path.write_bytes(b'invalid synthetic state')
            with self.assertRaises(spool.Hold):
                self.advance()
            self.assertEqual(self.file_identity(), before)
            path.write_bytes(content)

    def test_unknown_and_orphan_receiver_files_hold_without_deletion(self):
        for name in ('unknown', '.handoff-' + 'b' * 32 + '.tmp'):
            path = self.paths[2] / name
            path.write_bytes(b'synthetic')
            with self.assertRaises(spool.Hold):
                self.advance()
            self.assertEqual(os.listdir(self.fds[2]), [name])
            self.assertEqual(os.listdir(self.fds[1]), [])
            path.unlink()

    def test_receiver_metadata_symlink_fifo_and_weak_directory_hold(self):
        self.put()
        path = self.receiver_file()
        path.chmod(0o644)
        with self.assertRaises(spool.Hold):
            self.advance()
        path.chmod(0o600)
        link = self.root / 'synthetic-hardlink'
        os.link(path, link)
        with self.assertRaises(spool.Hold):
            self.advance()
        link.unlink()
        path.unlink()
        path.symlink_to(self.root / 'missing')
        with self.assertRaises(OSError):
            self.advance()
        path.unlink()
        os.mkfifo(path, 0o600)
        original = os.open
        def bounded_open(name, flags, *args, **kwargs):
            if name == handoff.NAME and kwargs.get('dir_fd') == self.fds[2]:
                self.assertTrue(flags & os.O_NONBLOCK)
            return original(name, flags, *args, **kwargs)
        with mock.patch.object(os, 'open', side_effect=bounded_open):
            with self.assertRaises(spool.Hold):
                self.advance()
        path.unlink()
        self.paths[2].chmod(0o755)
        with self.assertRaises(spool.Hold):
            self.advance()
        self.assertEqual(os.listdir(self.fds[1]), [])

    def test_directory_aliases_and_competing_descriptor_hold(self):
        for fds in ((self.fds[0], self.fds[1], self.fds[0]),
                    (self.fds[0], self.fds[1], self.fds[1]),
                    (self.fds[0], self.fds[0], self.fds[2])):
            with self.assertRaisesRegex(spool.Hold, 'THREE_SEPARATE'):
                receiver.dispatch_one(*fds)
        other = os.open(self.paths[2], os.O_RDONLY | os.O_DIRECTORY)
        try:
            with self.assertRaisesRegex(spool.Hold, 'DIRECTORY_BUSY'):
                receiver.dispatch_one(self.fds[0], self.fds[1], other)
        finally:
            os.close(other)
        self.assertEqual(os.listdir(self.fds[1]), [])

    def test_short_io_and_restrictive_umask_keep_both_stores_private(self):
        read, write = os.read, os.write
        old_umask = os.umask(0o777)
        try:
            with mock.patch.object(os, 'write', side_effect=lambda fd, data: write(fd, data[:7])), \
                 mock.patch.object(os, 'read', side_effect=lambda fd, count: read(fd, min(count, 13))):
                self.advance()
        finally:
            os.umask(old_umask)
        for path in (self.receiver_file(), self.paths[1] / delivery.NAME):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(self.ack_count(), 1)
        self.assertEqual(len(self.received().events), 1)

    def test_record_count_and_snapshot_byte_limits_preserve_receiver(self):
        self.put()
        before = self.file_identity()
        for patch in (mock.patch.object(handoff, 'MAX_EVENTS', 1),
                      mock.patch.object(handoff, 'MAX_SNAPSHOT_BYTES', len(before[2])),
                      mock.patch.object(receiver, 'MAX_RECORD_BYTES', len(self.payloads[1]) - 1)):
            with patch:
                with self.assertRaises(spool.Hold):
                    self.put(1)
            self.assertEqual(self.file_identity(), before)

    def test_cleanup_error_preserves_orphan_and_prevents_ack(self):
        self.initialize_ack()
        with mock.patch.object(os, 'unlink', side_effect=OSError('synthetic cleanup')):
            with self.assertRaises(spool.Hold):
                self.advance(receiver_failpoint='after_temp_fsync_before_replace')
        names = os.listdir(self.fds[2])
        self.assertEqual(len(names), 1)
        self.assertTrue(handoff.TEMP_RE.fullmatch(names[0]))
        with self.assertRaisesRegex(spool.Hold, 'ORPHAN_HANDOFF'):
            self.advance()
        self.assertEqual(os.listdir(self.fds[2]), names)
        self.assertEqual(self.ack_count(), 0)

    def test_bad_failpoints_precede_all_state_writes(self):
        for bad in ('unknown', {}, [], True, 42):
            for key in ('receiver_failpoint', 'ack_failpoint'):
                with self.assertRaisesRegex(spool.Hold, 'UNSUPPORTED_FAILPOINT'):
                    self.advance(**{key: bad})
            with self.assertRaisesRegex(spool.Hold, 'UNSUPPORTED_FAILPOINT'):
                self.put(failpoint=bad)
        self.assertEqual(os.listdir(self.fds[1]), [])
        self.assertEqual(os.listdir(self.fds[2]), [])

    def test_new_process_resumes_all_three_stores_after_lost_ack(self):
        with self.assertRaises(spool.SimulatedInterrupt):
            self.advance(ack_failpoint='after_receiver_ack_before_store')
        self.close_all()
        program = '''
import os,sys
sys.path.insert(0,sys.argv[1])
import v0145a_segment_spool as a
import v0145e_atomic_handoff as e
import v0145f_delivery_ack as f
import v0145g_file_receiver as g
fds=[a.open_private_directory(path) for path in sys.argv[2:]]
try:
    before=os.stat(e.NAME,dir_fd=fds[2]).st_ino
    assert len(e.read_handoff(fds[2]).events)==1
    assert len(f.read_state(fds[1]).acknowledged)==0
    g.dispatch_one(*fds)
    assert os.stat(e.NAME,dir_fd=fds[2]).st_ino==before
    g.dispatch_one(*fds)
    g.dispatch_one(*fds)
    assert g.dispatch_one(*fds)=='COMPLETE_NO_SEND'
    assert len(f.read_state(fds[1]).acknowledged)==3
    assert e.read_handoff(fds[0])==e.read_handoff(fds[2])
finally:
    for fd in fds: os.close(fd)
'''
        result = subprocess.run([sys.executable, '-B', '-c', program, str(Path(receiver.__file__).parent),
                                 *map(str, self.paths)], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.reopen()
        self.assertEqual(self.ack_count(), 3)

    def test_child_exit_receiver_and_ack_commit_phases(self):
        program = '''
import os,stat,sys
sys.path.insert(0,sys.argv[1])
import v0145a_segment_spool as a
import v0145f_delivery_ack as f
import v0145g_file_receiver as g
fds=[a.open_private_directory(path) for path in sys.argv[2:5]]
sf,af,rf=fds
phase=sys.argv[5]
if phase=='verified_ack':
    def interrupt(*args,**kwargs): os._exit(23)
    f.store_state=interrupt
elif phase in ('receiver_replace','ack_replace'):
    original=os.replace
    def interrupt(*args,**kwargs):
        original(*args,**kwargs)
        if kwargs.get('dst_dir_fd')==(rf if phase=='receiver_replace' else af): os._exit(23)
    os.replace=interrupt
else:
    original=os.fsync
    file_syncs=0
    def interrupt(fd):
        global file_syncs
        original(fd)
        if stat.S_ISREG(os.fstat(fd).st_mode):
            file_syncs+=1
            if (phase=='receiver_temp' and file_syncs==1) or (phase=='ack_temp' and file_syncs==2):
                os._exit(23)
        if phase=='receiver_dir' and fd==rf: os._exit(23)
    os.fsync=interrupt
g.dispatch_one(*fds)
'''
        for phase in ('receiver_temp', 'receiver_replace', 'receiver_dir', 'verified_ack', 'ack_temp', 'ack_replace'):
            with self.subTest(phase=phase):
                case = self.root / phase
                case.mkdir(mode=0o700)
                ack, received = case / 'acks', case / 'receiver'
                ack.mkdir(mode=0o700)
                received.mkdir(mode=0o700)
                fd = spool.open_private_directory(ack)
                try:
                    delivery.store_state(fd, delivery.AckState(self.scope, ()), None)
                finally:
                    os.close(fd)
                os.close(self.fds[0])
                self.fds[0] = None
                try:
                    result = subprocess.run([sys.executable, '-B', '-c', program,
                                             str(Path(receiver.__file__).parent), str(self.paths[0]),
                                             str(ack), str(received), phase], capture_output=True, timeout=5)
                    self.assertEqual(result.returncode, 23, result.stderr.decode())
                finally:
                    self.fds[0] = spool.open_private_directory(self.paths[0])
                af, rf = spool.open_private_directory(ack), spool.open_private_directory(received)
                try:
                    if phase in ('receiver_temp', 'ack_temp'):
                        with self.assertRaisesRegex(spool.Hold, 'ORPHAN'):
                            receiver.dispatch_one(self.fds[0], af, rf)
                    else:
                        self.assertEqual(handoff.read_handoff(rf).events, (self.payloads[0],))
                        self.assertEqual(len(delivery.read_state(af).acknowledged), 1 if phase == 'ack_replace' else 0)
                        before = os.stat(handoff.NAME, dir_fd=rf).st_ino
                        receiver.dispatch_one(self.fds[0], af, rf)
                        expected = 2 if phase == 'ack_replace' else 1
                        self.assertEqual(len(delivery.read_state(af).acknowledged), expected)
                        self.assertEqual(len(handoff.read_handoff(rf).events), expected)
                        if phase != 'ack_replace':
                            self.assertEqual(os.stat(handoff.NAME, dir_fd=rf).st_ino, before)
                    self.assertEqual(handoff.read_handoff(self.fds[0]).events, self.payloads)
                finally:
                    os.close(rf)
                    os.close(af)


if __name__ == '__main__':
    unittest.main()
