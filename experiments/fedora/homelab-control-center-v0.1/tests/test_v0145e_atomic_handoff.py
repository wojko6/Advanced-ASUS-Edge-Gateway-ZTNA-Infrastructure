"""Disposable E handoff tests: synthetic data, private /tmp files, no services."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import stat
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

KEY = identity.SYNTHETIC_KEY


def event(number, kind='SSH_TIMEOUT'):
    return identity.envelope(f'synthetic-cursor-{number:04d}', kind=kind)


def resign(obj):
    """Unkeyed digest is recomputable; tests do not mistake it for provenance."""
    body = {k:v for k,v in obj.items() if k != 'digest'}
    return identity.canonical(dict(body,digest=hashlib.sha256(identity.canonical(body)).hexdigest()))+b'\n'


class SnapshotContract(unittest.TestCase):
    def setUp(self):
        rows = identity.normalized_events(event(1),KEY)
        self.raw = handoff.encode_snapshot(identity.scope_for(KEY),rows)

    def test_valid_round_trip_keeps_id_and_payload_in_same_record(self):
        saved = handoff.decode_snapshot(self.raw)
        self.assertEqual(saved.scope,identity.scope_for(KEY))
        self.assertEqual(saved.events,identity.normalized_events(event(1),KEY))

    def test_digest_detects_validly_shaped_payload_change(self):
        with self.assertRaisesRegex(spool.Hold,'DIGEST_MISMATCH'):
            handoff.decode_snapshot(self.raw.replace(b'SSH_TIMEOUT',b'HTTP_IMPORT_TIMEOUT'))

    def test_reject_type_bytes_limit_json_and_duplicate_keys(self):
        for raw in (None,'data',b'',b'x'*(handoff.MAX_SNAPSHOT_BYTES+1),b'\xff',b'null',b'[]',
                    self.raw.replace(b'"schema":',b'"schema":"other","schema":',1)):
            with self.subTest(type=type(raw).__name__):
                with self.assertRaises(spool.Hold):
                    handoff.decode_snapshot(raw)

    def test_reject_unknown_schema_scope_and_extra_fields(self):
        for field,value in (('schema','other'),('scope','x'*64),('scope',True),('extra','private')):
            obj=json.loads(self.raw)
            obj[field]=value
            with self.assertRaises(spool.Hold):
                handoff.decode_snapshot(resign(obj))

    def test_reject_empty_duplicate_and_out_of_order_event_ids(self):
        for rows in ([],[json.loads(self.raw)['events'][0]]*2):
            obj=json.loads(self.raw)
            obj['events']=rows
            with self.assertRaises(spool.Hold):
                handoff.decode_snapshot(resign(obj))
        rows=identity.normalized_events(event(1)+event(2),KEY)
        rows=sorted(rows,key=lambda r:json.loads(r)['event_id'],reverse=True)
        with self.assertRaisesRegex(spool.Hold,'ORDER_OR_DUPLICATE'):
            handoff.decode_snapshot(handoff.encode_snapshot(identity.scope_for(KEY),rows))

    def test_reject_event_fields_source_scope_kind_and_time(self):
        for field,value in (('source','fedora-user-journal'),('scope','b'*64),('kind','RAW_LOG'),
                            ('event_id','x'*64),('time','2026-02-30T00:00:00.000000Z'),
                            ('time','1999-12-31T23:59:59.999999Z'),('time','2026-10-30T00:00:00.000Z'),
                            ('MESSAGE','private'),('component',False)):
            obj=json.loads(self.raw)
            obj['events'][0][field]=value
            with self.subTest(field=field,value=value):
                with self.assertRaises(spool.Hold):
                    handoff.decode_snapshot(resign(obj))

    def test_noncanonical_file_rejected_even_with_valid_digest(self):
        obj=json.loads(self.raw)
        with self.assertRaisesRegex(spool.Hold,'NONCANONICAL'):
            handoff.decode_snapshot(json.dumps(obj,indent=2).encode())

    def test_digest_is_not_authentication(self):
        obj=json.loads(self.raw)
        obj['events'][0]['kind']='HTTP_IMPORT_TIMEOUT'
        self.assertEqual(json.loads(handoff.decode_snapshot(resign(obj)).events[0])['kind'],
                         'HTTP_IMPORT_TIMEOUT')

    def test_self_test_has_no_file_network_or_subprocess_writes(self):
        output=io.StringIO()
        with mock.patch('builtins.open',side_effect=AssertionError('file')), \
             mock.patch.object(handoff.os,'open',side_effect=AssertionError('os.open')), \
             mock.patch.object(socket,'socket',side_effect=AssertionError('network')), \
             mock.patch.object(subprocess,'Popen',side_effect=AssertionError('subprocess')), \
             contextlib.redirect_stdout(output):
            handoff.self_test()
        self.assertIn('V0145E_SELFTEST=PASS_PURE_SYNTHETIC_ONLY',output.getvalue())


class AtomicHandoff(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='hcc-v0145e-test-',dir='/tmp')
        self.path=Path(self.tmp.name)
        os.chmod(self.path,0o700)
        self.fd=spool.open_private_directory(self.path)

    def tearDown(self):
        if self.fd is not None:
            os.close(self.fd)
        self.tmp.cleanup()

    def snapshot(self):
        return handoff.read_handoff(self.fd)

    def publish(self,raw,**kwargs):
        return handoff.publish_handoff(self.fd,raw,KEY,**kwargs)

    def test_commit_contains_complete_data_without_separate_ledger(self):
        result=self.publish(event(1)+event(2))
        self.assertEqual((result.accepted,result.duplicates,result.retained),(2,0,2))
        self.assertEqual(os.listdir(self.fd),[handoff.NAME])
        self.assertEqual(stat.S_IMODE((self.path/handoff.NAME).stat().st_mode),0o600)
        self.assertEqual(len(self.snapshot().events),2)

    def test_discarded_receipt_reopen_and_exact_replay_keep_payload_readable(self):
        self.publish(event(1)+event(2))
        os.close(self.fd)
        self.fd=spool.open_private_directory(self.path)
        result=self.publish(event(1)+event(2))
        self.assertEqual((result.accepted,result.duplicates),(0,2))
        self.assertEqual(set(self.snapshot().events),set(identity.normalized_events(event(1)+event(2),KEY)))

    def test_overlap_adds_one_and_keeps_every_committed_payload(self):
        self.publish(event(1)+event(2))
        result=self.publish(event(2)+event(3))
        self.assertEqual((result.accepted,result.duplicates,result.retained),(1,1,3))
        self.assertEqual(len(self.snapshot().events),3)

    def test_same_id_changed_payload_rejects_entire_batch(self):
        self.publish(event(1))
        original=(self.path/handoff.NAME).read_bytes()
        with self.assertRaisesRegex(spool.Hold,'SAME_ID_DIFFERENT_PAYLOAD'):
            self.publish(event(2)+event(1,'COLLECTOR_EXIT_255'))
        self.assertEqual((self.path/handoff.NAME).read_bytes(),original)
        self.assertEqual(self.publish(event(2)).accepted,1)

    def test_initial_conflict_leaves_no_state(self):
        with self.assertRaisesRegex(spool.Hold,'SAME_ID_DIFFERENT_PAYLOAD'):
            self.publish(event(1)+event(1,'COLLECTOR_EXIT_255'))
        self.assertEqual(os.listdir(self.fd),[])

    def test_key_scope_change_does_not_change_state(self):
        self.publish(event(1))
        original=(self.path/handoff.NAME).read_bytes()
        with self.assertRaisesRegex(spool.Hold,'HANDOFF_SCOPE_CHANGED'):
            handoff.publish_handoff(self.fd,event(2),b'b'*32)
        self.assertEqual((self.path/handoff.NAME).read_bytes(),original)

    def test_capacity_refusal_retains_data_and_allows_replay(self):
        with mock.patch.object(handoff,'MAX_EVENTS',2):
            self.publish(event(1)+event(2))
            with self.assertRaisesRegex(spool.Hold,'HANDOFF_EVENT_LIMIT'):
                self.publish(event(3))
            self.assertEqual(self.publish(event(1)).duplicates,1)
            self.assertEqual(len(self.snapshot().events),2)

    def test_snapshot_byte_limit_has_no_partial_file(self):
        with mock.patch.object(handoff,'MAX_SNAPSHOT_BYTES',100):
            with self.assertRaisesRegex(spool.Hold,'HANDOFF_BYTES_LIMIT'):
                self.publish(event(1))
        self.assertEqual(os.listdir(self.fd),[])

    def test_replay_does_not_rewrite_but_retries_directory_barrier(self):
        self.publish(event(1))
        before=(self.path/handoff.NAME).stat()
        with mock.patch.object(handoff.os,'fsync',wraps=os.fsync) as barrier:
            self.assertEqual(self.publish(event(1)).status,'DUPLICATE_HANDOFF_NO_WRITE')
        barrier.assert_called_once_with(self.fd)
        after=(self.path/handoff.NAME).stat()
        self.assertEqual((before.st_ino,before.st_mtime_ns),(after.st_ino,after.st_mtime_ns))

    def test_pre_replace_exception_keeps_old_snapshot(self):
        self.publish(event(1))
        original=(self.path/handoff.NAME).read_bytes()
        with self.assertRaises(spool.SimulatedInterrupt):
            self.publish(event(2),failpoint='after_temp_fsync_before_replace')
        self.assertEqual((self.path/handoff.NAME).read_bytes(),original)
        self.assertEqual(os.listdir(self.fd),[handoff.NAME])

    def test_post_replace_exception_has_complete_new_data_not_success_receipt(self):
        self.publish(event(1))
        with self.assertRaises(spool.SimulatedInterrupt):
            self.publish(event(2),failpoint='after_replace_before_dir_fsync')
        self.assertEqual(len(self.snapshot().events),2)
        self.assertEqual(self.publish(event(2)).duplicates,1)

    def test_lost_receipt_after_commit_preserves_id_and_payload(self):
        self.publish(event(1))
        with self.assertRaises(spool.SimulatedInterrupt):
            self.publish(event(2),failpoint='after_dir_fsync_before_return')
        self.assertEqual(len(self.snapshot().events),2)
        self.assertEqual(self.publish(event(2)).duplicates,1)

    def test_file_sync_failure_rolls_back_without_receipt(self):
        self.publish(event(1))
        original=(self.path/handoff.NAME).read_bytes()
        fsync=os.fsync
        def fail_file(fd):
            if stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError('synthetic file sync failure')
            return fsync(fd)
        with mock.patch.object(handoff.os,'fsync',side_effect=fail_file):
            with self.assertRaises(OSError):
                self.publish(event(2))
        self.assertEqual((self.path/handoff.NAME).read_bytes(),original)

    def test_directory_sync_failure_is_uncertain_not_success(self):
        self.publish(event(1))
        fsync=os.fsync
        def fail_dir(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError('synthetic directory sync failure')
            return fsync(fd)
        with mock.patch.object(handoff.os,'fsync',side_effect=fail_dir):
            with self.assertRaises(OSError):
                self.publish(event(2))
        self.assertEqual(len(self.snapshot().events),2)

    def test_replace_and_zero_write_failures_do_not_change_snapshot(self):
        self.publish(event(1))
        original=(self.path/handoff.NAME).read_bytes()
        with mock.patch.object(handoff.os,'replace',side_effect=OSError('synthetic replace failure')):
            with self.assertRaises(OSError):
                self.publish(event(2))
        with mock.patch.object(handoff.os,'write',return_value=0):
            with self.assertRaisesRegex(spool.Hold,'SHORT_WRITE'):
                self.publish(event(2))
        self.assertEqual((self.path/handoff.NAME).read_bytes(),original)

    def test_cleanup_failure_leaves_orphan_and_blocks_progress(self):
        self.publish(event(1))
        with mock.patch.object(handoff.os,'unlink',side_effect=OSError('synthetic cleanup failure')):
            with self.assertRaises(OSError):
                self.publish(event(2),failpoint='after_temp_fsync_before_replace')
        before=sorted(os.listdir(self.fd))
        with self.assertRaisesRegex(spool.Hold,'ORPHAN_HANDOFF'):
            self.publish(event(2))
        self.assertEqual(sorted(os.listdir(self.fd)),before)

    def test_orphan_or_unknown_entry_is_never_ignored(self):
        for name in ('.handoff-'+'a'*32+'.tmp','unexpected.json'):
            with self.subTest(name=name):
                entry=self.path/name
                entry.write_bytes(b'synthetic')
                with self.assertRaises(spool.Hold):
                    self.publish(event(1))
                entry.unlink()  # Test reset only, not implementation recovery.

    def test_corrupt_existing_file_never_resets_to_empty(self):
        self.publish(event(1))
        saved=self.path/handoff.NAME
        saved.write_bytes(b'{}')
        with self.assertRaises(spool.Hold):
            self.publish(event(2))
        self.assertEqual(saved.read_bytes(),b'{}')

    def test_unsafe_mode_hardlink_and_file_size_reject(self):
        self.publish(event(1))
        saved=self.path/handoff.NAME
        os.chmod(saved,0o644)
        with self.assertRaisesRegex(spool.Hold,'UNSAFE_HANDOFF'):
            self.snapshot()
        os.chmod(saved,0o600)
        with tempfile.TemporaryDirectory(prefix='hcc-v0145e-link-',dir='/tmp') as other_folder:
            other=Path(other_folder)/'extra-link'
            os.link(saved,other)
            with self.assertRaisesRegex(spool.Hold,'UNSAFE_HANDOFF'):
                self.snapshot()
        saved.write_bytes(b'')
        with self.assertRaisesRegex(spool.Hold,'UNSAFE_HANDOFF'):
            self.snapshot()

    def test_symlink_and_fifo_are_rejected_without_blocking(self):
        saved=self.path/handoff.NAME
        saved.symlink_to(self.path/'missing')
        with self.assertRaises(OSError):
            self.snapshot()
        saved.unlink()
        os.mkfifo(saved,0o600)
        original=os.open
        def checked_open(path,flags,*args,**kwargs):
            self.assertTrue(flags & os.O_NONBLOCK)
            return original(path,flags,*args,**kwargs)
        with mock.patch.object(handoff.os,'open',side_effect=checked_open):
            with self.assertRaisesRegex(spool.Hold,'UNSAFE_HANDOFF'):
                self.snapshot()

    def test_restrictive_umask_short_reads_and_writes(self):
        read,write=os.read,os.write
        old=os.umask(0o777)
        try:
            with mock.patch.object(handoff.os,'write',side_effect=lambda fd,b:write(fd,b[:13])):
                self.publish(event(1))
        finally:
            os.umask(old)
        with mock.patch.object(handoff.os,'read',side_effect=lambda fd,n:read(fd,min(n,17))):
            self.assertEqual(len(self.snapshot().events),1)
        self.assertEqual(stat.S_IMODE((self.path/handoff.NAME).stat().st_mode),0o600)

    def test_directory_mode_and_second_descriptor_cannot_bypass_lock(self):
        other=os.open(self.path,os.O_RDONLY|os.O_DIRECTORY)
        try:
            with self.assertRaisesRegex(spool.Hold,'DIRECTORY_BUSY'):
                handoff.publish_handoff(other,event(1),KEY)
        finally:
            os.close(other)
        os.chmod(self.path,0o755)
        with self.assertRaisesRegex(spool.Hold,'PRIVATE_DIRECTORY'):
            self.publish(event(1))
        self.assertEqual(os.listdir(self.fd),[])

    def test_invalid_input_and_failpoint_cannot_create_a_file(self):
        for raw,kwargs in ((b'{}',{}),(event(1),{'failpoint':'bad'})):
            with self.assertRaises(spool.Hold):
                self.publish(raw,**kwargs)
        self.assertEqual(os.listdir(self.fd),[])

    def test_raw_boot_cursor_and_fixture_key_not_stored(self):
        self.publish(identity.envelope('private.cursor.SENTINEL.0199',boot='1234567890abcdef'*2))
        raw=(self.path/handoff.NAME).read_bytes()
        for forbidden in (b'private.cursor.SENTINEL.0199',b'1234567890abcdef'*2,KEY,b'"cursor"',b'"boot"'):
            self.assertNotIn(forbidden,raw)

    def test_abrupt_child_exit_at_three_commit_phases(self):
        program='''
import os,sys,stat
sys.path.insert(0,sys.argv[1])
import v0145a_segment_spool as a
import v0145d_event_identity as d
import v0145e_atomic_handoff as e
fd=a.open_private_directory(sys.argv[2])
phase=sys.argv[3]
if phase=='replace':
    original=os.replace
    def interrupt(*args,**kwargs):
        original(*args,**kwargs)
        os._exit(23)
    os.replace=interrupt
else:
    original=os.fsync
    def interrupt(fd):
        original(fd)
        mode=os.fstat(fd).st_mode
        if (phase=='temp_sync' and stat.S_ISREG(mode)) or (phase=='dir_sync' and stat.S_ISDIR(mode)):
            os._exit(23)
    os.fsync=interrupt
e.publish_handoff(fd,d.envelope('synthetic-cursor-0002'),d.SYNTHETIC_KEY)
'''
        for phase in ('temp_sync','replace','dir_sync'):
            with self.subTest(phase=phase):
                case=self.path/phase
                case.mkdir(mode=0o700)
                casefd=spool.open_private_directory(case)
                try:
                    handoff.publish_handoff(casefd,event(1),KEY)
                finally:
                    os.close(casefd)
                result=subprocess.run([sys.executable,'-B','-c',program,str(Path(handoff.__file__).parent),
                                       str(case),phase],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,23,result.stderr.decode())
                casefd=spool.open_private_directory(case)
                try:
                    if phase=='temp_sync':
                        old=handoff.decode_snapshot((case/handoff.NAME).read_bytes())
                        self.assertEqual(len(old.events),1)
                        with self.assertRaisesRegex(spool.Hold,'ORPHAN_HANDOFF'):
                            handoff.read_handoff(casefd)
                    else:
                        self.assertEqual(len(handoff.read_handoff(casefd).events),2)
                        receipt=handoff.publish_handoff(casefd,event(2),KEY)
                        self.assertEqual((receipt.accepted,receipt.duplicates),(0,1))
                        self.assertEqual(len(handoff.read_handoff(casefd).events),2)
                finally:
                    os.close(casefd)


if __name__ == '__main__':
    unittest.main()
