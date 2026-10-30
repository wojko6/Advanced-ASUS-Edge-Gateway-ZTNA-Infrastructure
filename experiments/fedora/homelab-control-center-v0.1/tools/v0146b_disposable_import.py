#!/usr/bin/env python3
"""V0.14.6B: A-supplied metadata to a disposable private E-format store.

No trusted journal, production path/key, transport, ACK or source cursor.
--self-test is memory-only; --lab creates and removes its own /tmp store.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hmac
import json
import os
import tempfile

import v0145a_segment_spool as spool
import v0145d_event_identity as identity
import v0145e_atomic_handoff as handoff
import v0146a_journal_envelope as adapter

FAILPOINTS = handoff.FAILPOINTS


@dataclass(frozen=True)
class ImportReceipt:
    status: str
    input_records: int
    accepted_events: int
    duplicate_events: int
    ignored_records: int
    retained_events: int


def policy_key(expected_uid, key):
    """Separate UID/unit/transport namespaces; not source authentication.

    The derived key is never written to the store. This scope is intentionally
    different from standalone A/E fixtures; no implicit migration is offered.
    """
    if type(expected_uid) is not int or not 1 <= expected_uid <= adapter.MAX_UID:
        raise spool.Hold('IMPORT_EXPECTED_UID')
    identity.require_key(key)
    policy = identity.canonical({'domain': 'hcc-v0146b/synthetic-policy-key/1',
                                 'uid': expected_uid, 'unit': identity.UNIT, 'transport': 'stdout'})
    return hmac.digest(key, policy, 'sha256')


def _merge(current, incoming, scope):
    if current is not None and current.scope != scope:
        raise spool.Hold('IMPORT_POLICY_OR_KEY_SCOPE_CHANGED')
    previous = {} if current is None else {json.loads(event)['event_id']: event for event in current.events}
    if incoming.snapshot is None:
        return None, ImportReceipt('NO_MATCH_NO_WRITE', incoming.input_records, 0, 0,
                                   incoming.ignored_records, len(previous))
    addition = handoff.decode_snapshot(incoming.snapshot)
    if addition.scope != scope:
        raise spool.Hold('IMPORT_INCOMING_SCOPE_CHANGED')
    combined, accepted, duplicates = dict(previous), 0, incoming.duplicate_events
    for event in addition.events:
        event_id = json.loads(event)['event_id']
        if event_id in combined:
            if combined[event_id] != event:
                raise spool.Hold('IMPORT_SAME_ID_CHANGED_PAYLOAD')
            duplicates += 1
        else:
            combined[event_id] = event
            accepted += 1
    if len(combined) > handoff.MAX_EVENTS:
        raise spool.Hold('IMPORT_EVENT_LIMIT')
    content = None
    if accepted:
        content = handoff.encode_snapshot(scope, [combined[k] for k in sorted(combined)])
        handoff.decode_snapshot(content)  # Complete prospective state before any write.
    status = 'PUBLISHED_DISPOSABLE_IMPORT' if accepted else 'DUPLICATE_IMPORT_NO_WRITE'
    return content, ImportReceipt(status, incoming.input_records, accepted, duplicates,
                                  incoming.ignored_records, len(combined))


def import_batch(dirfd, raw, *, expected_uid, key, failpoint=None):
    """Validate whole batch/store, merge, sync and replace one complete E file.

    Caller owns a distinct private directory description, cooperatively locked
    until close. No cross-call raw-message fingerprint or delivery state exists.
    Ordinary pre-replace failures clean temp; abrupt exits may leave HOLD residue.
    """
    if (failpoint is not None and type(failpoint) is not str) or failpoint not in FAILPOINTS:
        raise spool.Hold('UNSUPPORTED_FAILPOINT')
    scoped_key = policy_key(expected_uid, key)
    incoming = adapter.adapt_snapshot(raw, expected_uid=expected_uid, key=scoped_key)
    current = handoff.read_handoff(dirfd)  # Full reader/metadata/orphan rules, even for no-match.
    content, receipt = _merge(current, incoming, identity.scope_for(scoped_key))
    if content is None:
        os.fsync(dirfd)  # Retry an earlier uncertain directory barrier without rewriting data.
        return receipt
    temp = '.handoff-' + os.urandom(16).hex() + '.tmp'
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=dirfd)
    replaced = False
    try:
        try:
            os.fchmod(fd, 0o600)
            spool.write_all(fd, content)
            os.fsync(fd)
        finally:
            os.close(fd)
        if failpoint == 'after_temp_fsync_before_replace':
            raise spool.SimulatedInterrupt('TEST_IMPORT_BEFORE_REPLACE')
        os.replace(temp, handoff.NAME, src_dir_fd=dirfd, dst_dir_fd=dirfd)
        replaced = True
        if failpoint == 'after_replace_before_dir_fsync':
            raise spool.SimulatedInterrupt('TEST_IMPORT_REPLACED_SYNC_UNCERTAIN')
        os.fsync(dirfd)
        if failpoint == 'after_dir_fsync_before_return':
            raise spool.SimulatedInterrupt('TEST_IMPORT_COMMITTED_RECEIPT_LOST')
        return receipt
    finally:
        if not replaced:
            os.unlink(temp, dir_fd=dirfd)
            os.fsync(dirfd)


def self_test():
    scoped_key = policy_key(1000, identity.SYNTHETIC_KEY)
    incoming = adapter.adapt_snapshot(adapter.fixture_inputs(), expected_uid=1000, key=scoped_key)
    scope = identity.scope_for(scoped_key)
    content, first = _merge(None, incoming, scope)
    assert (first.accepted_events, first.duplicate_events, first.retained_events) == (3, 1, 3)
    content_again, repeated = _merge(handoff.decode_snapshot(content), incoming, scope)
    assert content_again is None and repeated.accepted_events == 0 and repeated.duplicate_events == 4
    assert policy_key(1001, identity.SYNTHETIC_KEY) != scoped_key
    print('V0146B_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')
    print('NO_NETWORK_NO_SUBPROCESS_NO_FILES_WRITTEN=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    with tempfile.TemporaryDirectory(prefix='hcc-v0146b-synthetic-', dir='/tmp') as folder:
        os.chmod(folder, 0o700)
        fd = spool.open_private_directory(folder)
        try:
            options = {'expected_uid': 1000, 'key': identity.SYNTHETIC_KEY}
            first = import_batch(fd, adapter.fixture_inputs(), **options)
            assert first.accepted_events == 3
            os.close(fd)
            fd = None
            fd = spool.open_private_directory(folder)
            before = os.stat(handoff.NAME, dir_fd=fd)
            repeated = import_batch(fd, adapter.fixture_inputs(), **options)
            after = os.stat(handoff.NAME, dir_fd=fd)
            assert repeated.accepted_events == 0 and repeated.duplicate_events == 4
            assert (before.st_ino, before.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)
            extra = identity.canonical(adapter.fixture_record('synthetic-cursor-005', 1793350800000004)) + b'\n'
            try:
                import_batch(fd, extra, failpoint='after_dir_fsync_before_return', **options)
            except spool.SimulatedInterrupt:
                pass
            else:
                raise AssertionError('LOST_RECEIPT_NOT_OBSERVED')
            os.close(fd)
            fd = None
            fd = spool.open_private_directory(folder)
            assert import_batch(fd, extra, **options).duplicate_events == 1
            assert len(handoff.read_handoff(fd).events) == 4
        finally:
            if fd is not None:
                os.close(fd)
    # Report success only after the disposable directory's cleanup succeeds.
    print('=== HCC V0.14.6B / DISPOSABLE ATOMIC IMPORT ===')
    print('INITIAL_RETAINED_EVENTS=3 REOPEN_REPLAY_DUPLICATES=4')
    print('DUPLICATE_REWRITE=NO LOST_RECEIPT_REPLAY=RETAINED_EVENT')
    print('FINAL_RETAINED_EVENTS=4')
    print('POLICY_SCOPE=UID_UNIT_TRANSPORT_BOUND KEY_STORED=NO')
    print('STORE=PRIVATE_E_SNAPSHOT_ATOMIC_REPLACE_WITH_FSYNC')
    print('FILES_WRITTEN=DISPOSABLE_E_STORE_ONLY')
    print('SOURCE_PROVENANCE=UNVERIFIED_SUPPLIED_BYTES')
    print('TRUSTED_JOURNAL_READER=NOT_IMPLEMENTED')
    print('RAW_MESSAGE_CONFLICT_CHECK=WITHIN_BATCH_ONLY')
    print('ACK_OR_SOURCE_CURSOR=NOT_IMPLEMENTED RETENTION_ACTION=NO_DELETION')
    print('POWER_LOSS_DURABILITY=NOT_TESTED')
    print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
    print('NETWORK=NO SUBPROCESS=NO PRODUCTION_CHANGES=NO')
    print('TEMP_STATE_REMOVED=YES')
    print('V0146B_RESULT=PASS_DISPOSABLE_IMPORT_ONLY')
    print('DEPLOYMENT_GATE=HOLD')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--self-test', action='store_true')
    mode.add_argument('--lab', action='store_true')
    args = parser.parse_args()
    try:
        self_test() if args.self_test else run_lab()
    except (spool.Hold, spool.SimulatedInterrupt, OSError, AssertionError) as exc:
        print('V0146B_RESULT=HOLD_DISPOSABLE_IMPORT')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
