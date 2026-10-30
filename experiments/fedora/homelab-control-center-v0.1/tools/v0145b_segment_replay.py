#!/usr/bin/env python3
"""HCC V0.14.5B immutable-snapshot replay contract, synthetic offline only.

No journal reader, network transport, Alloy adapter, persistent checkpoint,
garbage collection or HCC HTTP endpoint. The only receiver shipped here keeps
synthetic data in memory. --lab uses a disposable /tmp directory.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
import re
import tempfile

import v0145a_segment_spool as spool

SCHEMA = 'hcc-v0145b-snapshot-checkpoint/1'
MAX_CHECKPOINT_BYTES = 256
HASH_RE = re.compile(r'\A[0-9a-f]{64}\Z', re.ASCII)


@dataclass(frozen=True)
class Segment:
    name: str
    content: bytes
    first: str
    last: str


@dataclass(frozen=True)
class Snapshot:
    digest: str
    segments: tuple[Segment, ...]


def snapshot(dirfd):
    """Freeze a completely verified bounded backlog, with explicit ambiguity HOLD.

    Canonical row equality is not journal event identity. A collision across
    batches is refused rather than silently discarded. Interleaved time ranges
    need a merge/event-identity contract and are also refused in this substage.
    """
    segments, seen = [], set()
    for name in spool.inspect_entries(dirfd):
        content = spool.verified_segment(dirfd, name)
        lines = content.splitlines()
        for line in lines:
            if line in seen:
                raise spool.Hold('AMBIGUOUS_CROSS_BATCH_EVENT')
            seen.add(line)
        segments.append(Segment(name, content, json.loads(lines[0])['time'],
                                json.loads(lines[-1])['time']))
    segments.sort(key=lambda item: (item.first, item.last, item.name))
    for prior, current in zip(segments, segments[1:]):
        if current.first < prior.last:
            raise spool.Hold('INTERLEAVED_SEGMENT_TIMES')
    manifest = json.dumps({'schema': SCHEMA, 'segments': [s.name for s in segments]},
                          sort_keys=True, separators=(',', ':')).encode('ascii')
    return Snapshot(hashlib.sha256(manifest).hexdigest(), tuple(segments))


def checkpoint_bytes(digest, acknowledged):
    """Internal checkpoint encoding; shape and prefix bounds checked on restore."""
    return json.dumps({'schema': SCHEMA, 'snapshot': digest,
                       'acknowledged': acknowledged}, sort_keys=True,
                      separators=(',', ':')).encode('ascii')


def restore_checkpoint(raw, plan):
    if raw is None:
        return 0
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_CHECKPOINT_BYTES:
        raise spool.Hold('CHECKPOINT_LENGTH')
    try:
        obj = json.loads(raw.decode('ascii'), object_pairs_hook=spool.no_duplicates,
                         parse_constant=lambda _: (_ for _ in ()).throw(spool.Hold('CHECKPOINT_NONFINITE')))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise spool.Hold('CHECKPOINT_JSON') from exc
    if type(obj) is not dict or set(obj) != {'schema', 'snapshot', 'acknowledged'}:
        raise spool.Hold('CHECKPOINT_SCHEMA')
    if (obj['schema'] != SCHEMA or type(obj['snapshot']) is not str or
            not HASH_RE.fullmatch(obj['snapshot']) or
            type(obj['acknowledged']) is not int or
            not 0 <= obj['acknowledged'] <= len(plan.segments)):
        raise spool.Hold('CHECKPOINT_VALUE')
    if obj['snapshot'] != plan.digest:
        raise spool.Hold('SNAPSHOT_CHANGED_REQUIRES_REVIEW')
    return obj['acknowledged']


def replay_one(dirfd, raw_checkpoint, receiver, *, failpoint=None):
    """Deliver at most one verified segment, advancing only after exact ACK.

    Rebuild/validate the full snapshot before every simulated send, including
    completion. Added/removed/modified segments cannot silently change a saved
    checkpoint. An ACK lost before checkpoint persistence can cause a replay;
    this models at-least-once attempts, NOT exactly-once or real Loki delivery.
    """
    if failpoint not in (None, 'after_ack_before_checkpoint'):
        raise spool.Hold('UNSUPPORTED_FAILPOINT')
    plan = snapshot(dirfd)
    acknowledged = restore_checkpoint(raw_checkpoint, plan)
    if acknowledged == len(plan.segments):
        return 'COMPLETE_NO_SEND', checkpoint_bytes(plan.digest, acknowledged)
    item = plan.segments[acknowledged]
    # The receiver is trusted test code. No URL, socket or HTTP client exists.
    if receiver(item.name, item.content) != item.name:
        raise spool.Hold('RECEIVER_ACK_MISMATCH')
    if failpoint is not None:
        raise spool.SimulatedInterrupt('TEST_ACK_WITHOUT_CHECKPOINT')
    return 'ACKNOWLEDGED_SYNTHETIC_SEGMENT', checkpoint_bytes(plan.digest, acknowledged + 1)


class FakeReceiver:
    """In-process synthetic sink; counts repeat attempts without deduplicating."""
    def __init__(self):
        self.received = []

    def __call__(self, name, content):
        self.received.append((name, content))
        return name


def self_test():
    plan = Snapshot('a' * 64, ())
    raw = checkpoint_bytes(plan.digest, 0)
    assert restore_checkpoint(raw, plan) == 0
    for bad in (b'', b'{}', raw.replace(b':0', b':true'),
                raw.replace(b'"snapshot":', b'"extra":0,"snapshot":'),
                raw.replace(b'a' * 64, b'b' * 64)):
        try:
            restore_checkpoint(bad, plan)
        except spool.Hold:
            pass
        else:
            raise AssertionError('BAD_CHECKPOINT_ACCEPTED')
    print('V0145B_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')
    print('SELFTEST_NO_NETWORK_NO_SUBPROCESS_NO_FILE_WRITES=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    with tempfile.TemporaryDirectory(prefix='hcc-v0145b-synthetic-', dir='/tmp') as folder:
        os.chmod(folder, 0o700)
        fd = spool.open_private_directory(folder)
        try:
            for minute in ('01', '00'):
                spool.publish(fd, spool.event('2026-10-30T09:' + minute + ':00.000Z', 'SSH_TIMEOUT'))
            sink = FakeReceiver()
            _, checkpoint = replay_one(fd, None, sink)
            try:
                replay_one(fd, checkpoint, sink, failpoint='after_ack_before_checkpoint')
            except spool.SimulatedInterrupt:
                pass
            else:
                raise AssertionError('INTERRUPT_NOT_OBSERVED')
            _, checkpoint = replay_one(fd, checkpoint, sink)
            complete, _ = replay_one(fd, checkpoint, sink)
            assert complete == 'COMPLETE_NO_SEND'
            assert len(sink.received) == 3
            assert sink.received[1] == sink.received[2]
            print('=== HCC V0.14.5B / OFFLINE SNAPSHOT REPLAY ===')
            print('VERIFIED_SNAPSHOT_SEGMENTS=2')
            print('SYNTHETIC_RECEIVE_ATTEMPTS=3')
            print('ACK_WITHOUT_CHECKPOINT_REPLAY=OBSERVED_DUPLICATE_ATTEMPT')
            print('CHECKPOINT_AFTER_ACK=PASS_IN_MEMORY_ONLY')
            print('DELIVERY_CONTRACT=AT_LEAST_ONCE_MODEL_NOT_EXACTLY_ONCE')
            print('CHECKPOINT_PERSISTENCE=NOT_IMPLEMENTED')
            print('RETENTION_ACTION=NO_DELETION')
            print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
            print('NETWORK=NO PRODUCTION_CHANGES=NO')
            print('V0145B_RESULT=PASS_SYNTHETIC_REPLAY_MODEL_ONLY')
        finally:
            os.close(fd)
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
        print('V0145B_RESULT=HOLD_LAB_FAILURE')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
