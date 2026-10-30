#!/usr/bin/env python3
"""HCC V0.14.5G: disposable file-backed synthetic receiver, no transport.

E source, F ACK file and a separate E-format receiver snapshot stay in /tmp.
No real journal/Loki/Alloy, network, production store, service or deletion.
Process reopen and retained-ID deduplication are not exactly-once delivery or
physical power-loss durability. CLI accepts only --self-test or --lab.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile

import v0145a_segment_spool as spool
import v0145d_event_identity as identity
import v0145e_atomic_handoff as handoff
import v0145f_delivery_ack as delivery

MAX_RECORD_BYTES = 4096
FAILPOINTS = handoff.FAILPOINTS


def require_failpoint(value, allowed):
    if (value is not None and type(value) is not str) or value not in allowed:
        raise spool.Hold('UNSUPPORTED_FAILPOINT')


def validate_record(scope, event_id, payload):
    """One exact canonical D-format event; no envelope reconstruction or key."""
    if (type(scope) is not str or not handoff.HASH_RE.fullmatch(scope) or
            type(event_id) is not str or not handoff.HASH_RE.fullmatch(event_id) or
            type(payload) is not bytes or not 0 < len(payload) <= MAX_RECORD_BYTES):
        raise spool.Hold('RECEIVER_RECORD_SHAPE')
    try:
        snapshot = handoff.decode_snapshot(handoff.encode_snapshot(scope, (payload,)))
    except (ValueError, UnicodeError, RecursionError, TypeError) as exc:
        raise spool.Hold('RECEIVER_RECORD_JSON') from exc
    if snapshot.events != (payload,) or json.loads(payload)['event_id'] != event_id:
        raise spool.Hold('RECEIVER_RECORD_BINDING_OR_CANONICAL')


def fixture_ack(scope, event_id, payload):
    return {'schema': delivery.ACK_SCHEMA, 'scope': scope, 'event_id': event_id,
            'payload_sha256': delivery.payload_hash(payload)}


def receive_one(dirfd, scope, event_id, payload, *, failpoint=None):
    """Persist full payload before fixture ACK; same retained ID is idempotent.

    Reuses E's snapshot schema, reader, bounds and orphan rules in an independent
    directory. Trusted caller and cooperative lock; no authenticated receiver.
    """
    require_failpoint(failpoint, FAILPOINTS)
    validate_record(scope, event_id, payload)
    current = handoff.read_handoff(dirfd)
    if current is not None and current.scope != scope:
        raise spool.Hold('RECEIVER_SCOPE_CHANGED')
    records = {} if current is None else {json.loads(e)['event_id']: e for e in current.events}
    if event_id in records:
        if records[event_id] != payload:
            raise spool.Hold('RECEIVER_SAME_ID_DIFFERENT_PAYLOAD')
        # The file was synced before replacement. Retry a possibly uncertain
        # directory barrier before returning ACK; do not rewrite duplicate data.
        os.fsync(dirfd)
        return fixture_ack(scope, event_id, payload)
    records[event_id] = payload
    content = handoff.encode_snapshot(scope, [records[k] for k in sorted(records)])
    handoff.decode_snapshot(content)  # Whole prospective state before any write.
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
            raise spool.SimulatedInterrupt('TEST_RECEIVER_BEFORE_REPLACE')
        os.replace(temp, handoff.NAME, src_dir_fd=dirfd, dst_dir_fd=dirfd)
        replaced = True
        if failpoint == 'after_replace_before_dir_fsync':
            raise spool.SimulatedInterrupt('TEST_RECEIVER_REPLACED_SYNC_UNCERTAIN')
        os.fsync(dirfd)
        if failpoint == 'after_dir_fsync_before_return':
            raise spool.SimulatedInterrupt('TEST_RECEIVER_STORED_ACK_LOST')
        return fixture_ack(scope, event_id, payload)
    finally:
        if not replaced:
            os.unlink(temp, dir_fd=dirfd)
            os.fsync(dirfd)


def dispatch_one(sourcefd, ackfd, receiverfd, *, receiver_failpoint=None, ack_failpoint=None):
    """Cross-check all three retained stores before using F's dispatcher.

    Keep three distinct private directory descriptions locked until close. Do
    not share descriptions between concurrent callers. No cross-store atomic
    transaction, rollback protection, automatic retries or retention exists.
    """
    require_failpoint(receiver_failpoint, FAILPOINTS)
    require_failpoint(ack_failpoint, delivery.FAILPOINTS)
    inodes = set()
    for fd in (sourcefd, ackfd, receiverfd):
        spool.require_private_directory(fd)
        info = os.fstat(fd)
        inodes.add((info.st_dev, info.st_ino))
    if len(inodes) != 3:
        raise spool.Hold('THREE_SEPARATE_DIRECTORIES_REQUIRED')
    source = handoff.read_handoff(sourcefd)
    if source is None:
        raise spool.Hold('HANDOFF_REQUIRED')
    state = delivery.read_state(ackfd)
    received = handoff.read_handoff(receiverfd)
    payloads = {json.loads(e)['event_id']: e for e in source.events}
    stored = {} if received is None else {json.loads(e)['event_id']: e for e in received.events}
    if received is not None:
        if received.scope != source.scope:
            raise spool.Hold('RECEIVER_SOURCE_SCOPE_MISMATCH')
        if any(payloads.get(event_id) != payload for event_id, payload in stored.items()):
            raise spool.Hold('RECEIVER_SOURCE_RECORD_MISSING_OR_CHANGED')
    if state is not None:
        if state.scope != source.scope:
            raise spool.Hold('ACK_SOURCE_SCOPE_MISMATCH')
        for event_id, digest in state.acknowledged:
            if event_id not in stored or delivery.payload_hash(stored[event_id]) != digest:
                raise spool.Hold('ACK_WITHOUT_MATCHING_RECEIVER_RECORD')

    def receive(scope, event_id, payload):
        return receive_one(receiverfd, scope, event_id, payload, failpoint=receiver_failpoint)

    return delivery.dispatch_one(sourcefd, ackfd, receive, failpoint=ack_failpoint)


def self_test():
    scope = identity.scope_for(identity.SYNTHETIC_KEY)
    payload = identity.normalized_events(identity.envelope('synthetic-cursor-001'),
                                         identity.SYNTHETIC_KEY)[0]
    event_id = json.loads(payload)['event_id']
    validate_record(scope, event_id, payload)
    assert fixture_ack(scope, event_id, payload)['payload_sha256'] == delivery.payload_hash(payload)
    try:
        validate_record(scope, 'a' * 64, payload)
    except spool.Hold:
        pass
    else:
        raise AssertionError('WRONG_RECORD_BINDING_ACCEPTED')
    print('V0145G_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')
    print('SELFTEST_NO_NETWORK_NO_SUBPROCESS_NO_FILE_WRITES=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    with tempfile.TemporaryDirectory(prefix='hcc-v0145g-synthetic-', dir='/tmp') as folder:
        os.chmod(folder, 0o700)
        paths = [os.path.join(folder, name) for name in ('source', 'acks', 'receiver')]
        fds = []
        try:
            for path in paths:
                os.mkdir(path, 0o700)
                fds.append(spool.open_private_directory(path))
            sourcefd, ackfd, receiverfd = fds
            handoff.publish_handoff(sourcefd, identity.envelope('synthetic-cursor-001') +
                                    identity.envelope('synthetic-cursor-002'), identity.SYNTHETIC_KEY)
            try:
                dispatch_one(*fds, ack_failpoint='after_receiver_ack_before_store')
            except spool.SimulatedInterrupt:
                pass
            else:
                raise AssertionError('INTERRUPT_NOT_OBSERVED')
            assert len(handoff.read_handoff(receiverfd).events) == 1
            assert len(delivery.read_state(ackfd).acknowledged) == 0
            while fds:
                os.close(fds.pop())
            for path in paths:
                fds.append(spool.open_private_directory(path))
            sourcefd, ackfd, receiverfd = fds
            before = os.stat(handoff.NAME, dir_fd=receiverfd)
            assert dispatch_one(*fds) == 'ACKNOWLEDGED_SYNTHETIC_RECORD'
            after = os.stat(handoff.NAME, dir_fd=receiverfd)
            assert (before.st_ino, before.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)
            assert len(handoff.read_handoff(receiverfd).events) == 1
            assert dispatch_one(*fds) == 'ACKNOWLEDGED_SYNTHETIC_RECORD'
            assert dispatch_one(*fds) == 'COMPLETE_NO_SEND'
            handoff.publish_handoff(sourcefd, identity.envelope('synthetic-cursor-003'), identity.SYNTHETIC_KEY)
            assert dispatch_one(*fds) == 'ACKNOWLEDGED_SYNTHETIC_RECORD'
            assert dispatch_one(*fds) == 'COMPLETE_NO_SEND'
            assert handoff.read_handoff(sourcefd) == handoff.read_handoff(receiverfd)
            assert len(delivery.read_state(ackfd).acknowledged) == 3
            print('=== HCC V0.14.5G / DISPOSABLE FILE RECEIVER ===')
            print('RECEIVER_RECORDS_AFTER_REOPEN=1 ACKS_AFTER_REOPEN=0')
            print('REPLAY_RECEIVER_SNAPSHOT_UNCHANGED=YES')
            print('FINAL_RECEIVER_RECORDS=3 FINAL_STORED_ACKS=3')
            print('SOURCE_PAYLOADS_RETAINED=3')
            print('RECEIVER_STORAGE=DISPOSABLE_FSYNC_SNAPSHOT')
            print('ACK_PROTOCOL=IN_PROCESS_FIXTURE_NOT_LOKI')
            print('EXACTLY_ONCE=NOT_CLAIMED POWER_LOSS_DURABILITY=NOT_TESTED')
            print('RETENTION_ACTION=NO_DELETION')
            print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
            print('NETWORK=NO PRODUCTION_CHANGES=NO')
            print('V0145G_RESULT=PASS_DISPOSABLE_FILE_RECEIVER_ONLY')
        finally:
            while fds:
                os.close(fds.pop())
    print('TEMP_STATE_REMOVED=YES')
    print('DEPLOYMENT_GATE=HOLD')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--self-test', action='store_true')
    modes.add_argument('--lab', action='store_true')
    args = parser.parse_args()
    try:
        self_test() if args.self_test else run_lab()
    except (spool.Hold, OSError, AssertionError) as exc:
        print('V0145G_RESULT=HOLD_FILE_RECEIVER_FAILURE')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
