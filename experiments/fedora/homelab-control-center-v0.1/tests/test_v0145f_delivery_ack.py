"""F uses disposable source/ACK directories and a volatile fake receiver only."""
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

KEY = identity.SYNTHETIC_KEY


def event(number):
    return identity.envelope(f'synthetic-cursor-{number:04d}')


class AckEncoding(unittest.TestCase):
    def setUp(self):
        self.empty = delivery.AckState('a'*64, ())
        self.one = delivery.AckState('a'*64, (('b'*64, 'c'*64),))

    def test_round_trip_empty_and_single_ack(self):
        for state in (self.empty,self.one):
            self.assertEqual(delivery.decode_state(delivery.encode_state(state)),state)

    def test_invalid_json_types_size_duplicate_and_extra_keys_reject(self):
        valid=delivery.encode_state(self.one)
        for raw in (None,b'',b'\xff',b'null',b'[]',b'NaN',b'x'*(delivery.MAX_BYTES+1),
                    valid.replace(b'"schema":',b'"schema":"other","schema":',1),
                    valid.replace(b'"scope":',b'"MESSAGE":"private","scope":',1)):
            with self.assertRaises(spool.Hold):
                delivery.decode_state(raw)

    def test_corruption_and_noncanonical_state_reject(self):
        valid=delivery.encode_state(self.one)
        for raw in (valid.replace(b'c'*64,b'd'*64),json.dumps(json.loads(valid),indent=2).encode()):
            with self.assertRaises(spool.Hold):
                delivery.decode_state(raw)

    def test_order_duplicates_invalid_hash_and_count_reject(self):
        states=(delivery.AckState('a'*64,(('b'*64,'c'*64),)*2),
                delivery.AckState('a'*64,(('d'*64,'c'*64),('b'*64,'c'*64))),
                delivery.AckState('a'*64,(('x'*64,'c'*64),)),
                delivery.AckState('wrong',()))
        for state in states:
            with self.assertRaises(spool.Hold):
                delivery.decode_state(delivery.encode_state(state))
        with mock.patch.object(delivery,'MAX_ACKS',0):
            with self.assertRaises(spool.Hold):
                delivery.decode_state(delivery.encode_state(self.one))

    def test_unkeyed_state_digest_is_not_ack_authentication(self):
        invented=delivery.AckState('a'*64,(('b'*64,'d'*64),))
        self.assertEqual(delivery.decode_state(delivery.encode_state(invented)),invented)

    def test_self_test_is_memory_only(self):
        output=io.StringIO()
        with mock.patch('builtins.open',side_effect=AssertionError('file')), \
             mock.patch.object(delivery.os,'open',side_effect=AssertionError('os.open')), \
             mock.patch.object(socket,'socket',side_effect=AssertionError('network')), \
             mock.patch.object(subprocess,'Popen',side_effect=AssertionError('subprocess')), \
             contextlib.redirect_stdout(output):
            delivery.self_test()
        self.assertIn('V0145F_SELFTEST=PASS_PURE_SYNTHETIC_ONLY',output.getvalue())


class DeliveryModel(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='hcc-v0145f-test-',dir='/tmp')
        self.root=Path(self.tmp.name)
        self.source,self.acks=self.root/'source',self.root/'acks'
        self.source.mkdir(mode=0o700)
        self.acks.mkdir(mode=0o700)
        self.sourcefd=spool.open_private_directory(self.source)
        self.ackfd=spool.open_private_directory(self.acks)
        handoff.publish_handoff(self.sourcefd,event(1)+event(2)+event(3),KEY)
        self.sink=delivery.FakeReceiver()

    def tearDown(self):
        if self.ackfd is not None:
            os.close(self.ackfd)
        if self.sourcefd is not None:
            os.close(self.sourcefd)
        self.tmp.cleanup()

    def advance(self,receiver=None,**kwargs):
        return delivery.dispatch_one(self.sourcefd,self.ackfd,self.sink if receiver is None else receiver,**kwargs)

    def count(self):
        state=delivery.read_state(self.ackfd)
        return 0 if state is None else len(state.acknowledged)

    def initialize(self):
        state=delivery.AckState(handoff.read_handoff(self.sourcefd).scope,())
        delivery.store_state(self.ackfd,state,None)
        return state

    def test_one_record_ack_is_bound_to_id_and_payload(self):
        self.assertEqual(self.advance(),'ACKNOWLEDGED_SYNTHETIC_RECORD')
        state=delivery.read_state(self.ackfd)
        self.assertEqual(state.acknowledged,((self.sink.received[0][0],
                                            delivery.payload_hash(self.sink.received[0][1])),))
        self.assertEqual(stat.S_IMODE((self.acks/delivery.NAME).stat().st_mode),0o600)

    def test_reopen_resumes_unacknowledged_records(self):
        self.advance()
        old_id=self.sink.received[0][0]
        os.close(self.ackfd)
        self.ackfd=spool.open_private_directory(self.acks)
        fresh=delivery.FakeReceiver()
        self.advance(fresh)
        self.assertNotEqual(fresh.received[0][0],old_id)
        self.assertEqual(self.count(),2)

    def test_complete_does_not_send_rewrite_or_delete_source(self):
        source_before=(self.source/handoff.NAME).read_bytes()
        for _ in range(3):
            self.advance()
        before=(self.acks/delivery.NAME).stat().st_mtime_ns
        self.assertEqual(self.advance(),'COMPLETE_NO_SEND')
        self.assertEqual(len(self.sink.received),3)
        self.assertEqual((self.source/handoff.NAME).read_bytes(),source_before)
        self.assertEqual((self.acks/delivery.NAME).stat().st_mtime_ns,before)

    def test_appended_record_is_delivered_after_completion(self):
        for _ in range(3):
            self.advance()
        self.assertEqual(self.advance(),'COMPLETE_NO_SEND')
        handoff.publish_handoff(self.sourcefd,event(4),KEY)
        self.assertEqual(self.advance(),'ACKNOWLEDGED_SYNTHETIC_RECORD')
        self.assertEqual(self.count(),4)
        self.assertEqual(len(handoff.read_handoff(self.sourcefd).events),4)

    def test_new_lower_id_is_not_skipped_by_a_watermark(self):
        rows=identity.normalized_events(b''.join(event(n) for n in range(10,20)),KEY)
        ordered=sorted(rows,key=lambda raw:json.loads(raw)['event_id'])
        scope=identity.scope_for(KEY)
        (self.source/handoff.NAME).write_bytes(handoff.encode_snapshot(scope,[ordered[-1]]))
        self.advance()
        (self.source/handoff.NAME).write_bytes(handoff.encode_snapshot(scope,[ordered[0],ordered[-1]]))
        self.advance()
        self.assertEqual(self.sink.received[1][0],json.loads(ordered[0])['event_id'])
        self.assertEqual(self.count(),2)

    def test_wrong_ack_schema_scope_id_hash_or_extra_field_never_advances(self):
        for field,value in (('schema','wrong'),('scope','b'*64),('event_id','c'*64),
                            ('payload_sha256','d'*64),('extra','private')):
            def receiver(scope,event_id,payload):
                ack=self.sink(scope,event_id,payload)
                ack[field]=value
                return ack
            with self.subTest(field=field):
                with self.assertRaisesRegex(spool.Hold,'RECEIVER_ACK_MISMATCH'):
                    self.advance(receiver)
                self.assertEqual(self.count(),0)
        with self.assertRaisesRegex(spool.Hold,'RECEIVER_ACK_MISMATCH'):
            self.advance(lambda *_:None)

    def test_receiver_exception_leaves_initialized_empty_state(self):
        def broken(*_):
            raise RuntimeError('synthetic private receiver error')
        with self.assertRaisesRegex(spool.Hold,'SYNTHETIC_RECEIVER_FAILURE'):
            self.advance(broken)
        self.assertIsNotNone(delivery.read_state(self.ackfd))
        self.assertEqual(self.count(),0)

    def test_ack_received_but_not_stored_repeats_same_record(self):
        with self.assertRaises(spool.SimulatedInterrupt):
            self.advance(failpoint='after_receiver_ack_before_store')
        self.assertEqual(self.count(),0)
        self.advance()
        self.assertEqual(self.sink.received[0],self.sink.received[1])

    def test_before_replace_keeps_old_state_and_cleans_own_temp(self):
        state=self.initialize()
        with self.assertRaises(spool.SimulatedInterrupt):
            self.advance(failpoint='after_ack_file_fsync_before_replace')
        self.assertEqual(delivery.read_state(self.ackfd),state)
        self.assertEqual(os.listdir(self.ackfd),[delivery.NAME])

    def test_after_replace_error_may_expose_valid_ack_but_not_success(self):
        self.initialize()
        with self.assertRaises(spool.SimulatedInterrupt):
            self.advance(failpoint='after_ack_replace_before_dir_fsync')
        self.assertEqual(self.count(),1)
        self.advance()
        self.assertEqual(self.count(),2)
        self.assertNotEqual(self.sink.received[0][0],self.sink.received[1][0])

    def test_lost_return_after_ack_commit_does_not_resend_that_id(self):
        with self.assertRaises(spool.SimulatedInterrupt):
            self.advance(failpoint='after_ack_dir_fsync_before_return')
        self.assertEqual(self.count(),1)
        self.advance()
        self.assertNotEqual(self.sink.received[0][0],self.sink.received[1][0])

    def test_missing_or_corrupt_source_never_initializes_ack_or_receives(self):
        source_file=self.source/handoff.NAME
        before=source_file.read_bytes()
        source_file.unlink()  # Negative fixture mutation, no implementation GC.
        with self.assertRaisesRegex(spool.Hold,'HANDOFF_REQUIRED'):
            self.advance()
        self.assertEqual(os.listdir(self.ackfd),[])
        source_file.write_bytes(before)
        os.chmod(source_file,0o600)
        source_file.write_bytes(b'{}')
        with self.assertRaises(spool.Hold):
            self.advance()
        self.assertEqual(self.sink.received,[])

    def test_corrupt_ack_never_resets_to_empty(self):
        self.initialize()
        saved=self.acks/delivery.NAME
        saved.write_bytes(b'{}')
        with self.assertRaises(spool.Hold):
            self.advance()
        self.assertEqual(saved.read_bytes(),b'{}')
        self.assertEqual(self.sink.received,[])

    def test_acknowledged_source_record_cannot_disappear(self):
        self.advance()
        acknowledged=self.sink.received[0][0]
        source=handoff.read_handoff(self.sourcefd)
        remaining=[e for e in source.events if json.loads(e)['event_id']!=acknowledged]
        (self.source/handoff.NAME).write_bytes(handoff.encode_snapshot(source.scope,remaining))
        with self.assertRaisesRegex(spool.Hold,'ACK_SOURCE_RECORD_MISSING_OR_CHANGED'):
            self.advance()
        self.assertEqual(len(self.sink.received),1)

    def test_changed_acknowledged_payload_is_rejected_even_with_new_source_digest(self):
        self.advance()
        acknowledged=self.sink.received[0][0]
        source=handoff.read_handoff(self.sourcefd)
        events=[]
        for raw in source.events:
            obj=json.loads(raw)
            if obj['event_id']==acknowledged:
                obj['kind']='HTTP_IMPORT_TIMEOUT'
            events.append(identity.canonical(obj))
        (self.source/handoff.NAME).write_bytes(handoff.encode_snapshot(source.scope,events))
        with self.assertRaisesRegex(spool.Hold,'ACK_SOURCE_RECORD_MISSING_OR_CHANGED'):
            self.advance()
        self.assertEqual(len(self.sink.received),1)

    def test_source_scope_change_is_not_silently_rebased(self):
        self.initialize()
        rows=identity.normalized_events(event(1),b'b'*32)
        (self.source/handoff.NAME).write_bytes(handoff.encode_snapshot(identity.scope_for(b'b'*32),rows))
        with self.assertRaisesRegex(spool.Hold,'ACK_SOURCE_SCOPE_MISMATCH'):
            self.advance()
        self.assertEqual(self.sink.received,[])

    def test_state_cannot_start_nonempty_rewind_jump_or_overwrite(self):
        scope=handoff.read_handoff(self.sourcefd).scope
        empty=delivery.AckState(scope,())
        one=delivery.AckState(scope,(('a'*64,'b'*64),))
        two=delivery.AckState(scope,(('a'*64,'b'*64),('c'*64,'d'*64)))
        with self.assertRaisesRegex(spool.Hold,'INITIAL_STATE_MUST_BE_EMPTY'):
            delivery.store_state(self.ackfd,one,None)
        delivery.store_state(self.ackfd,empty,None)
        with self.assertRaisesRegex(spool.Hold,'NONMONOTONIC'):
            delivery.store_state(self.ackfd,two,empty)
        delivery.store_state(self.ackfd,one,empty)
        with self.assertRaisesRegex(spool.Hold,'NONMONOTONIC'):
            delivery.store_state(self.ackfd,empty,one)
        with self.assertRaisesRegex(spool.Hold,'EXPECTATION_CHANGED'):
            delivery.store_state(self.ackfd,two,empty)

    def test_orphan_and_unknown_ack_entries_block_without_deletion(self):
        for name in ('.ack-'+'a'*32+'.tmp','unknown'):
            saved=self.acks/name
            saved.write_bytes(b'synthetic')
            with self.assertRaises(spool.Hold):
                self.advance()
            self.assertTrue(saved.exists())
            saved.unlink()
        self.assertEqual(self.sink.received,[])

    def test_state_modes_hardlinks_and_empty_files_reject(self):
        self.initialize()
        saved=self.acks/delivery.NAME
        os.chmod(saved,0o644)
        with self.assertRaisesRegex(spool.Hold,'UNSAFE_ACK_METADATA'):
            self.advance()
        os.chmod(saved,0o600)
        other=self.root/'extra-link'
        os.link(saved,other)
        with self.assertRaisesRegex(spool.Hold,'UNSAFE_ACK_METADATA'):
            self.advance()
        other.unlink()
        saved.write_bytes(b'')
        with self.assertRaisesRegex(spool.Hold,'UNSAFE_ACK_METADATA'):
            self.advance()

    def test_symlink_and_fifo_checkpoint_never_follow_or_block(self):
        saved=self.acks/delivery.NAME
        saved.symlink_to(self.root/'missing')
        with self.assertRaises(OSError):
            delivery.read_state(self.ackfd)
        saved.unlink()
        os.mkfifo(saved,0o600)
        original=os.open
        def bounded_open(path,flags,*args,**kwargs):
            self.assertTrue(flags & os.O_NONBLOCK)
            return original(path,flags,*args,**kwargs)
        with mock.patch.object(delivery.os,'open',side_effect=bounded_open):
            with self.assertRaisesRegex(spool.Hold,'UNSAFE_ACK_METADATA'):
                delivery.read_state(self.ackfd)

    def test_same_directory_weak_mode_and_second_descriptor_reject(self):
        with self.assertRaisesRegex(spool.Hold,'SEPARATE_ACK_DIRECTORY'):
            delivery.dispatch_one(self.sourcefd,self.sourcefd,self.sink)
        other=os.open(self.acks,os.O_RDONLY|os.O_DIRECTORY)
        try:
            with self.assertRaisesRegex(spool.Hold,'DIRECTORY_BUSY'):
                delivery.dispatch_one(self.sourcefd,other,self.sink)
        finally:
            os.close(other)
        os.chmod(self.acks,0o755)
        with self.assertRaisesRegex(spool.Hold,'PRIVATE_DIRECTORY'):
            self.advance()
        self.assertEqual(self.sink.received,[])

    def test_ack_count_and_byte_limits_do_not_partially_advance(self):
        self.initialize()
        with mock.patch.object(delivery,'MAX_ACKS',0):
            with self.assertRaises(spool.Hold):
                self.advance()
        self.assertEqual(self.count(),0)
        with mock.patch.object(delivery,'MAX_BYTES',1):
            with self.assertRaises(spool.Hold):
                self.advance()
        self.assertEqual(self.count(),0)

    def test_short_io_and_restrictive_umask_preserve_private_state(self):
        original_read,original_write=os.read,os.write
        old_umask=os.umask(0o777)
        try:
            with mock.patch.object(delivery.os,'write',side_effect=lambda fd,b:original_write(fd,b[:9])):
                self.advance()
        finally:
            os.umask(old_umask)
        with mock.patch.object(delivery.os,'read',side_effect=lambda fd,n:original_read(fd,min(n,11))):
            self.assertEqual(self.count(),1)
        self.assertEqual(stat.S_IMODE((self.acks/delivery.NAME).stat().st_mode),0o600)

    def test_source_and_state_directory_barrier_errors_prevent_receive(self):
        self.initialize()
        for target in (self.sourcefd,self.ackfd):
            original=os.fsync
            def fail_selected(fd):
                if fd==target:
                    raise OSError('synthetic pre-receive barrier error')
                return original(fd)
            with mock.patch.object(delivery.os,'fsync',side_effect=fail_selected):
                with self.assertRaises(OSError):
                    self.advance()
        self.assertEqual(self.sink.received,[])
        self.assertEqual(self.count(),0)

    def test_ack_file_sync_replace_and_zero_write_errors_keep_old_state(self):
        self.initialize()
        before=(self.acks/delivery.NAME).read_bytes()
        fsync=os.fsync
        def fail_file(fd):
            if stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError('synthetic ack file fsync')
            return fsync(fd)
        with mock.patch.object(delivery.os,'fsync',side_effect=fail_file):
            with self.assertRaises(OSError):
                self.advance()
        with mock.patch.object(delivery.os,'replace',side_effect=OSError('synthetic replace')):
            with self.assertRaises(OSError):
                self.advance()
        with mock.patch.object(delivery.os,'write',return_value=0):
            with self.assertRaisesRegex(spool.Hold,'SHORT_WRITE'):
                self.advance()
        self.assertEqual((self.acks/delivery.NAME).read_bytes(),before)

    def test_post_replace_directory_sync_error_does_not_return_success(self):
        self.initialize()
        original=os.fsync
        ack_dir_syncs=0
        def fail_second_ack_dir(fd):
            nonlocal ack_dir_syncs
            if fd==self.ackfd:
                ack_dir_syncs+=1
                if ack_dir_syncs==2:
                    raise OSError('synthetic final ack barrier failure')
            return original(fd)
        with mock.patch.object(delivery.os,'fsync',side_effect=fail_second_ack_dir):
            with self.assertRaises(OSError):
                self.advance()
        self.assertEqual(self.count(),1)

    def test_cleanup_error_preserves_orphan_for_review(self):
        self.initialize()
        with mock.patch.object(delivery.os,'unlink',side_effect=OSError('synthetic cleanup')):
            with self.assertRaises(OSError):
                self.advance(failpoint='after_ack_file_fsync_before_replace')
        before=sorted(os.listdir(self.ackfd))
        with self.assertRaisesRegex(spool.Hold,'ORPHAN_ACK'):
            self.advance()
        self.assertEqual(sorted(os.listdir(self.ackfd)),before)

    def test_deleted_ack_state_replays_and_source_payload_is_retained(self):
        self.advance()
        first=self.sink.received[0]
        (self.acks/delivery.NAME).unlink()  # Explicit negative fixture mutation.
        self.advance()
        self.assertEqual(self.sink.received[1],first)
        self.assertEqual(len(handoff.read_handoff(self.sourcefd).events),3)

    def test_unsupported_failpoint_precedes_any_state_write(self):
        for bad in ('unknown',{},[],True,42):
            with self.assertRaisesRegex(spool.Hold,'UNSUPPORTED_FAILPOINT'):
                self.advance(failpoint=bad)
        self.assertEqual(os.listdir(self.ackfd),[])
        self.assertEqual(self.sink.received,[])

    def test_independent_process_resumes_stored_ack_set(self):
        self.advance()
        already=self.sink.received[0][0]
        os.close(self.sourcefd)
        os.close(self.ackfd)
        self.sourcefd=self.ackfd=None
        program='''
import os,sys
sys.path.insert(0,sys.argv[1])
import v0145a_segment_spool as a
import v0145f_delivery_ack as f
sf,af=a.open_private_directory(sys.argv[2]),a.open_private_directory(sys.argv[3])
sink=f.FakeReceiver()
try:
    assert len(f.read_state(af).acknowledged)==1
    assert f.dispatch_one(sf,af,sink)=='ACKNOWLEDGED_SYNTHETIC_RECORD'
    assert sink.received[0][0]!=sys.argv[4]
    assert len(f.read_state(af).acknowledged)==2
finally:
    os.close(af)
    os.close(sf)
'''
        result=subprocess.run([sys.executable,'-B','-c',program,str(Path(delivery.__file__).parent),
                               str(self.source),str(self.acks),already],capture_output=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.sourcefd=spool.open_private_directory(self.source)
        self.ackfd=spool.open_private_directory(self.acks)
        self.assertEqual(self.count(),2)

    def test_actual_child_exit_in_four_receive_store_phases(self):
        program='''
import os,sys,stat
sys.path.insert(0,sys.argv[1])
import v0145a_segment_spool as a
import v0145f_delivery_ack as f
sf,af=a.open_private_directory(sys.argv[2]),a.open_private_directory(sys.argv[3])
phase=sys.argv[4]
if phase=='receive':
    def interrupt(*args,**kwargs):
        os._exit(23)
    # Empty state was initialized by the parent, so this is reached only
    # after dispatch has verified the receiver's exact ACK.
    f.store_state=interrupt
elif phase=='replace':
    original=os.replace
    def interrupt(*args,**kwargs):
        original(*args,**kwargs)
        os._exit(23)
    os.replace=interrupt
elif phase in ('file_sync','dir_sync'):
    original=os.fsync
    dir_calls=0
    def interrupt(fd):
        global dir_calls
        original(fd)
        if phase=='file_sync' and stat.S_ISREG(os.fstat(fd).st_mode):
            os._exit(23)
        if fd==af:
            dir_calls+=1
            if phase=='dir_sync' and dir_calls==2:
                os._exit(23)
    os.fsync=interrupt
def receive(scope,event_id,payload):
    print(event_id,flush=True)
    return f.FakeReceiver()(scope,event_id,payload)
f.dispatch_one(sf,af,receive)
'''
        scope=handoff.read_handoff(self.sourcefd).scope
        for phase in ('receive','file_sync','replace','dir_sync'):
            with self.subTest(phase=phase):
                case=self.root/phase
                case.mkdir(mode=0o700)
                casefd=spool.open_private_directory(case)
                try:
                    delivery.store_state(casefd,delivery.AckState(scope,()),None)
                finally:
                    os.close(casefd)
                os.close(self.sourcefd)
                self.sourcefd=None
                try:
                    result=subprocess.run([sys.executable,'-B','-c',program,
                                           str(Path(delivery.__file__).parent),str(self.source),str(case),phase],
                                          capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,23,result.stderr.decode())
                finally:
                    self.sourcefd=spool.open_private_directory(self.source)
                received_id=result.stdout.decode().strip()
                self.assertTrue(handoff.HASH_RE.fullmatch(received_id))
                casefd=spool.open_private_directory(case)
                try:
                    sink=delivery.FakeReceiver()
                    if phase=='file_sync':
                        with self.assertRaisesRegex(spool.Hold,'ORPHAN_ACK'):
                            delivery.dispatch_one(self.sourcefd,casefd,sink)
                    else:
                        state=delivery.read_state(casefd)
                        self.assertEqual(len(state.acknowledged),0 if phase=='receive' else 1)
                        delivery.dispatch_one(self.sourcefd,casefd,sink)
                        if phase=='receive':
                            self.assertEqual(sink.received[0][0],received_id)
                        else:
                            self.assertNotEqual(sink.received[0][0],received_id)
                    self.assertEqual(len(handoff.read_handoff(self.sourcefd).events),3)
                finally:
                    os.close(casefd)


if __name__ == '__main__':
    unittest.main()
