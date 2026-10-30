#!/usr/bin/env python3
"""HCC V0.14.5F: disposable per-record delivery ACK model for E snapshots.

In-process fake receiver only. No network, real journal/Loki/Alloy, real ACK
protocol, service, production state or event deletion. --lab uses fresh /tmp.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
import re
import stat
import tempfile

import v0145a_segment_spool as spool
import v0145d_event_identity as identity
import v0145e_atomic_handoff as handoff

SCHEMA = 'hcc-v0145f-ack-store/1'
ACK_SCHEMA = 'hcc-v0145f-fake-receiver-ack/1'
NAME = 'delivery-acks.json'
TEMP_RE = re.compile(r'\A\.ack-[0-9a-f]{32}\.tmp\Z', re.ASCII)
MAX_ACKS = 1024
MAX_BYTES = 256 * 1024
STORE_FAILURES = frozenset((None, 'after_ack_file_fsync_before_replace',
                           'after_ack_replace_before_dir_fsync',
                           'after_ack_dir_fsync_before_return'))
FAILPOINTS = STORE_FAILURES | {'after_receiver_ack_before_store'}


@dataclass(frozen=True)
class AckState:
    scope: str
    acknowledged: tuple[tuple[str, str], ...]


def payload_hash(payload):
    return hashlib.sha256(payload).hexdigest()


def encode_state(state):
    body = {'schema': SCHEMA, 'scope': state.scope,
            'acked': [{'event_id': event_id, 'payload_sha256': digest}
                      for event_id, digest in state.acknowledged]}
    raw = identity.canonical(dict(body, digest=payload_hash(identity.canonical(body)))) + b'\n'
    if len(raw) > MAX_BYTES:
        raise spool.Hold('ACK_BYTES_LIMIT')
    return raw


def decode_state(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise spool.Hold('ACK_BYTES_LIMIT')
    try:
        obj = json.loads(raw.decode('ascii'), object_pairs_hook=spool.no_duplicates,
                         parse_constant=lambda _: (_ for _ in ()).throw(spool.Hold('ACK_NONFINITE')))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise spool.Hold('ACK_JSON') from exc
    if type(obj) is not dict or set(obj) != {'schema', 'scope', 'acked', 'digest'}:
        raise spool.Hold('ACK_STATE_SCHEMA')
    if (obj['schema'] != SCHEMA or type(obj['scope']) is not str or
            not handoff.HASH_RE.fullmatch(obj['scope']) or type(obj['digest']) is not str or
            not handoff.HASH_RE.fullmatch(obj['digest']) or type(obj['acked']) is not list or
            len(obj['acked']) > MAX_ACKS):
        raise spool.Hold('ACK_STATE_VALUE')
    pairs, prior = [], None
    for item in obj['acked']:
        if (type(item) is not dict or set(item) != {'event_id', 'payload_sha256'} or
                any(type(value) is not str or not handoff.HASH_RE.fullmatch(value) for value in item.values())):
            raise spool.Hold('ACK_RECORD_SCHEMA')
        if prior is not None and item['event_id'] <= prior:
            raise spool.Hold('ACK_ID_ORDER_OR_DUPLICATE')
        prior = item['event_id']
        pairs.append((item['event_id'], item['payload_sha256']))
    state = AckState(obj['scope'], tuple(pairs))
    if encode_state(state) != raw:
        raise spool.Hold('ACK_DIGEST_OR_CANONICAL_MISMATCH')
    return state


def read_state(dirfd):
    spool.require_private_directory(dirfd)
    found = False
    with os.scandir(dirfd) as entries:
        for entry in entries:
            if TEMP_RE.fullmatch(entry.name):
                raise spool.Hold('ORPHAN_ACK_REQUIRES_REVIEW')
            if entry.name != NAME or found:
                raise spool.Hold('UNEXPECTED_ACK_ENTRY')
            found = True
    if not found:
        return None
    fd = os.open(NAME, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=dirfd)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid() or
                stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1 or
                not 0 < before.st_size <= MAX_BYTES):
            raise spool.Hold('UNSAFE_ACK_METADATA')
        chunks, remaining = [], before.st_size + 1
        while remaining:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b''.join(chunks)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if len(raw) != before.st_size or any(getattr(before, key) != getattr(after, key) for key in fields):
            raise spool.Hold('ACK_CHANGED_DURING_READ')
        return decode_state(raw)
    finally:
        os.close(fd)


def store_state(dirfd, state, expected, *, failpoint=None):
    """Internal trusted-caller writer; not proof that an arbitrary caller got ACK."""
    if (failpoint is not None and type(failpoint) is not str) or failpoint not in STORE_FAILURES:
        raise spool.Hold('UNSUPPORTED_FAILPOINT')
    content = encode_state(state)
    decode_state(content)
    current = read_state(dirfd)
    if current != expected:
        raise spool.Hold('ACK_EXPECTATION_CHANGED')
    new = dict(state.acknowledged)
    if current is None:
        if new:
            raise spool.Hold('ACK_INITIAL_STATE_MUST_BE_EMPTY')
    else:
        old = dict(current.acknowledged)
        if (state.scope != current.scope or len(new) - len(old) not in (0, 1) or
                any(new.get(event_id) != digest for event_id, digest in old.items())):
            raise spool.Hold('ACK_NONMONOTONIC_UPDATE')
    if current == state:
        os.fsync(dirfd)
        return
    temp = '.ack-' + os.urandom(16).hex() + '.tmp'
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
        if failpoint == 'after_ack_file_fsync_before_replace':
            raise spool.SimulatedInterrupt('TEST_ACK_BEFORE_REPLACE')
        os.replace(temp, NAME, src_dir_fd=dirfd, dst_dir_fd=dirfd)
        replaced = True
        if failpoint == 'after_ack_replace_before_dir_fsync':
            raise spool.SimulatedInterrupt('TEST_ACK_REPLACED_SYNC_UNCERTAIN')
        os.fsync(dirfd)
        if failpoint == 'after_ack_dir_fsync_before_return':
            raise spool.SimulatedInterrupt('TEST_ACK_COMMITTED_RETURN_LOST')
    finally:
        if not replaced:
            os.unlink(temp, dir_fd=dirfd)
            os.fsync(dirfd)


def dispatch_one(sourcefd, statefd, receiver, *, failpoint=None):
    """One synthetic receive attempt; save ACK only after exact scope/ID/hash.

    Both directory descriptions stay cooperatively locked through the callback.
    Do not share them between concurrent callers. The receiver is trusted test
    code; its ACK is not evidence of a real/durable remote receiver.
    """
    if (failpoint is not None and type(failpoint) is not str) or failpoint not in FAILPOINTS:
        raise spool.Hold('UNSUPPORTED_FAILPOINT')
    spool.require_private_directory(sourcefd)
    spool.require_private_directory(statefd)
    source_stat, state_stat = os.fstat(sourcefd), os.fstat(statefd)
    if (source_stat.st_dev, source_stat.st_ino) == (state_stat.st_dev, state_stat.st_ino):
        raise spool.Hold('SEPARATE_ACK_DIRECTORY_REQUIRED')
    source = handoff.read_handoff(sourcefd)
    if source is None:
        raise spool.Hold('HANDOFF_REQUIRED')
    payloads = {json.loads(event)['event_id']: event for event in source.events}
    state = read_state(statefd)
    if state is not None:
        if state.scope != source.scope:
            raise spool.Hold('ACK_SOURCE_SCOPE_MISMATCH')
        for event_id, digest in state.acknowledged:
            if event_id not in payloads or payload_hash(payloads[event_id]) != digest:
                raise spool.Hold('ACK_SOURCE_RECORD_MISSING_OR_CHANGED')
    else:
        state = AckState(source.scope, ())
        store_state(statefd, state, None)
    # Retry possible earlier uncertain publication barriers before any receive.
    os.fsync(sourcefd)
    os.fsync(statefd)
    acknowledged = dict(state.acknowledged)
    candidate = next((event_id for event_id in payloads if event_id not in acknowledged), None)
    if candidate is None:
        return 'COMPLETE_NO_SEND'
    payload = payloads[candidate]
    expected_ack = {'schema': ACK_SCHEMA, 'scope': source.scope, 'event_id': candidate,
                    'payload_sha256': payload_hash(payload)}
    try:
        ack = receiver(source.scope, candidate, payload)
    except Exception as exc:
        raise spool.Hold('SYNTHETIC_RECEIVER_FAILURE') from exc
    if type(ack) is not dict or ack != expected_ack or any(type(value) is not str for value in ack.values()):
        raise spool.Hold('RECEIVER_ACK_MISMATCH')
    if failpoint == 'after_receiver_ack_before_store':
        raise spool.SimulatedInterrupt('TEST_RECEIVE_ACK_NOT_STORED')
    acknowledged[candidate] = expected_ack['payload_sha256']
    updated = AckState(source.scope, tuple(sorted(acknowledged.items())))
    store_state(statefd, updated, state, failpoint=failpoint)
    return 'ACKNOWLEDGED_SYNTHETIC_RECORD'


class FakeReceiver:
    """Volatile in-process receiver; counts attempts, does not deduplicate."""
    def __init__(self):
        self.received = []

    def __call__(self, scope, event_id, payload):
        self.received.append((event_id, payload))
        return {'schema': ACK_SCHEMA, 'scope': scope, 'event_id': event_id,
                'payload_sha256': payload_hash(payload)}


def self_test():
    empty = AckState('a' * 64, ())
    assert decode_state(encode_state(empty)) == empty
    one = AckState('a' * 64, (('b' * 64, 'c' * 64),))
    assert decode_state(encode_state(one)) == one
    try:
        decode_state(encode_state(one).replace(b'c' * 64, b'd' * 64))
    except spool.Hold:
        pass
    else:
        raise AssertionError('ACK_CORRUPTION_ACCEPTED')
    print('V0145F_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')
    print('SELFTEST_NO_NETWORK_NO_SUBPROCESS_NO_FILE_WRITES=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    with tempfile.TemporaryDirectory(prefix='hcc-v0145f-synthetic-', dir='/tmp') as folder:
        os.chmod(folder, 0o700)
        source_path, state_path = os.path.join(folder, 'source'), os.path.join(folder, 'acks')
        os.mkdir(source_path, 0o700)
        os.mkdir(state_path, 0o700)
        sourcefd, statefd = spool.open_private_directory(source_path), None
        try:
            statefd = spool.open_private_directory(state_path)
            raw = identity.envelope('synthetic-cursor-001') + identity.envelope('synthetic-cursor-002')
            handoff.publish_handoff(sourcefd, raw, identity.SYNTHETIC_KEY)
            sink = FakeReceiver()
            assert dispatch_one(sourcefd, statefd, sink) == 'ACKNOWLEDGED_SYNTHETIC_RECORD'
            os.close(statefd)
            statefd = None
            os.close(sourcefd)
            sourcefd = None
            sourcefd = spool.open_private_directory(source_path)
            statefd = spool.open_private_directory(state_path)
            assert len(read_state(statefd).acknowledged) == 1
            try:
                dispatch_one(sourcefd, statefd, sink, failpoint='after_receiver_ack_before_store')
            except spool.SimulatedInterrupt:
                pass
            else:
                raise AssertionError('INTERRUPT_NOT_OBSERVED')
            assert dispatch_one(sourcefd, statefd, sink) == 'ACKNOWLEDGED_SYNTHETIC_RECORD'
            assert dispatch_one(sourcefd, statefd, sink) == 'COMPLETE_NO_SEND'
            handoff.publish_handoff(sourcefd, identity.envelope('synthetic-cursor-003'), identity.SYNTHETIC_KEY)
            assert dispatch_one(sourcefd, statefd, sink) == 'ACKNOWLEDGED_SYNTHETIC_RECORD'
            assert dispatch_one(sourcefd, statefd, sink) == 'COMPLETE_NO_SEND'
            assert len(sink.received) == 4 and sink.received[1] == sink.received[2]
            assert len(read_state(statefd).acknowledged) == len(handoff.read_handoff(sourcefd).events) == 3
            print('=== HCC V0.14.5F / SYNTHETIC DELIVERY ACK STORE ===')
            print('ACKS_AFTER_REOPEN=1')
            print('FINAL_STORED_ACKS=3')
            print('SYNTHETIC_RECEIVE_ATTEMPTS=4')
            print('ACK_WITHOUT_STORE=OBSERVED_DUPLICATE_ATTEMPT')
            print('APPENDED_RECORD_AFTER_COMPLETION=ACKNOWLEDGED')
            print('SOURCE_PAYLOADS_RETAINED=3')
            print('ACK_PROTOCOL=IN_PROCESS_FIXTURE_NOT_LOKI')
            print('RECEIVER_DURABILITY=NOT_IMPLEMENTED')
            print('POWER_LOSS_DURABILITY=NOT_TESTED')
            print('RETENTION_ACTION=NO_DELETION')
            print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
            print('NETWORK=NO PRODUCTION_CHANGES=NO')
            print('V0145F_RESULT=PASS_DISPOSABLE_DELIVERY_ACK_ONLY')
        finally:
            if statefd is not None:
                os.close(statefd)
            if sourcefd is not None:
                os.close(sourcefd)
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
        print('V0145F_RESULT=HOLD_DELIVERY_ACK_FAILURE')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
