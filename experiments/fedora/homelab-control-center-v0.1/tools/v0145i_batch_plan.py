#!/usr/bin/env python3
"""HCC V0.14.5I: memory-only frozen batch plan for synthetic E/F bytes.

Declared F fixture ACKs are not actual Loki receipts. No network, file I/O,
subprocess, receiver, checkpoint advance, service, journal or deletion.
CLI accepts only --self-test or --lab; all inputs are synthetic memory.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json

import v0145a_segment_spool as spool
import v0145d_event_identity as identity
import v0145e_atomic_handoff as handoff
import v0145f_delivery_ack as delivery
import v0145h_loki_request as encoding

MAX_REQUESTS = 64
MAX_TOTAL_BODY_BYTES = 1024 * 1024


@dataclass(frozen=True)
class RequestPlan:
    scope: str
    source_sha256: str
    ack_sha256: str | None
    source_events: int
    declared_acks: int
    requests: tuple[encoding.PushRequest, ...]

    @property
    def pending_ids(self):
        return tuple(event_id for request in self.requests for event_id in request.event_ids)

    @property
    def body_bytes(self):
        return sum(len(request.body) for request in self.requests)


def build_plan(raw_source, raw_ack=None):
    """Validate whole source and declared ACK state before building any batch.

    None explicitly declares no ACK basis; corrupt bytes never become None.
    This is content consistency, not proof of receipt or authenticated state.
    """
    source = handoff.decode_snapshot(raw_source)
    state = None if raw_ack is None else delivery.decode_state(raw_ack)
    payloads = {json.loads(payload)['event_id']: payload for payload in source.events}
    acknowledged = {} if state is None else dict(state.acknowledged)
    if state is not None:
        if state.scope != source.scope:
            raise spool.Hold('PLAN_ACK_SCOPE_MISMATCH')
        for event_id, digest in acknowledged.items():
            if event_id not in payloads or delivery.payload_hash(payloads[event_id]) != digest:
                raise spool.Hold('PLAN_ACK_RECORD_MISSING_OR_CHANGED')
    pending = []
    for event_id, payload in payloads.items():
        if event_id not in acknowledged:
            stamp = encoding.nanoseconds(json.loads(payload)['time'])
            pending.append((int(stamp), event_id, payload))
    pending.sort(key=lambda row: (row[0], row[1]))
    expected_requests = (len(pending) + encoding.MAX_EVENTS - 1) // encoding.MAX_EVENTS
    if expected_requests > MAX_REQUESTS:
        raise spool.Hold('PLAN_REQUEST_COUNT_LIMIT')
    requests, total_bytes = [], 0
    for start in range(0, len(pending), encoding.MAX_EVENTS):
        # H requires an E-format input with canonical ID order, and restores
        # time/ID order inside the request. Chunk boundaries use global time/ID.
        chunk = sorted(pending[start:start + encoding.MAX_EVENTS], key=lambda row: row[1])
        request = encoding.build_request(handoff.encode_snapshot(source.scope, [row[2] for row in chunk]))
        total_bytes += len(request.body)
        if total_bytes > MAX_TOTAL_BODY_BYTES:
            raise spool.Hold('PLAN_TOTAL_BYTES_LIMIT')
        requests.append(request)
    return RequestPlan(source.scope, hashlib.sha256(raw_source).hexdigest(),
                       None if raw_ack is None else hashlib.sha256(raw_ack).hexdigest(),
                       len(source.events), len(acknowledged), tuple(requests))


def require_current(plan, raw_source, raw_ack=None):
    """Recompute all requests/bindings before a future caller reuses a plan.

    Caller must supply freshly obtained bytes; this does not read files or
    lock live state, and cannot prevent changes after this pure check returns.
    """
    if type(plan) is not RequestPlan:
        raise spool.Hold('PLAN_VALUE_TYPES')
    if (any(type(value) is not str for value in (plan.scope, plan.source_sha256)) or
            (plan.ack_sha256 is not None and type(plan.ack_sha256) is not str) or
            any(type(value) is not int for value in (plan.source_events, plan.declared_acks)) or
            type(plan.requests) is not tuple or len(plan.requests) > MAX_REQUESTS):
        raise spool.Hold('PLAN_VALUE_TYPES')
    for request in plan.requests:
        if (type(request) is not encoding.PushRequest or type(request.body) is not bytes or
                not 0 < len(request.body) <= encoding.MAX_BODY_BYTES or
                any(type(value) is not str for value in (request.scope, request.sha256)) or
                type(request.event_ids) is not tuple or not 1 <= len(request.event_ids) <= encoding.MAX_EVENTS or
                any(type(event_id) is not str for event_id in request.event_ids)):
            raise spool.Hold('PLAN_VALUE_TYPES')
    # Reject coercions such as True == 1 and bytearray(data) == data before
    # equality can accept a plan with mutable bodies or changed field types.
    if plan != build_plan(raw_source, raw_ack):
        raise spool.Hold('PLAN_OR_INPUT_CHANGED')


def fixture_inputs():
    events = [identity.normalized_events(identity.envelope(f'synthetic-plan-{n:04d}',
                                                          1793350800123456 + n),
                                         identity.SYNTHETIC_KEY)[0] for n in range(35)]
    events.sort(key=lambda payload: json.loads(payload)['event_id'])
    scope = identity.scope_for(identity.SYNTHETIC_KEY)
    # Declared in-memory fixture only, not a file-store or real receipt.
    pairs = tuple((json.loads(payload)['event_id'], delivery.payload_hash(payload))
                  for payload in (events[0], events[-1]))
    return handoff.encode_snapshot(scope, events), delivery.encode_state(delivery.AckState(scope, pairs))


def self_test():
    raw = encoding.fixture_snapshot()
    plan = build_plan(raw)
    assert len(plan.requests) == 1 and len(plan.pending_ids) == 3
    assert plan.requests[0] == encoding.build_request(raw)
    require_current(plan, raw)
    print('V0145I_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')
    print('SELFTEST_NO_NETWORK_NO_SUBPROCESS_NO_FILE_WRITES=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    raw_source, raw_ack = fixture_inputs()
    plan = build_plan(raw_source, raw_ack)
    assert plan.source_events == 35 and plan.declared_acks == 2
    assert [len(request.event_ids) for request in plan.requests] == [16, 16, 1]
    assert len(plan.pending_ids) == len(set(plan.pending_ids)) == 33
    require_current(plan, raw_source, raw_ack)
    try:
        require_current(plan, raw_source, None)
    except spool.Hold:
        pass
    else:
        raise AssertionError('CHANGED_ACK_BASIS_ACCEPTED')
    print('=== HCC V0.14.5I / OFFLINE FROZEN BATCH PLAN ===')
    print('SYNTHETIC_SOURCE_RECORDS=35 DECLARED_SYNTHETIC_ACKS=2')
    print('PLANNED_REQUESTS=3 PENDING_SYNTHETIC_RECORDS=33')
    print('BATCH_RECORD_COUNTS=16,16,1')
    print('ORDER=GLOBAL_TIMESTAMP_THEN_EVENT_ID')
    print('PLAN_REUSE_ON_CHANGED_INPUT=HOLD')
    print('ACK_BASIS=DECLARED_F_FIXTURE_NOT_LOKI_RECEIPT')
    print('ACK_OR_CHECKPOINT_ADVANCE=NO')
    print('RETENTION_ACTION=NO_DELETION')
    print('NETWORK=NO FILES_WRITTEN=NO SUBPROCESS=NO')
    print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
    print('PRODUCTION_CHANGES=NO')
    print('V0145I_RESULT=PASS_OFFLINE_BATCH_PLAN_ONLY')
    print('DEPLOYMENT_GATE=HOLD')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--self-test', action='store_true')
    modes.add_argument('--lab', action='store_true')
    args = parser.parse_args()
    try:
        self_test() if args.self_test else run_lab()
    except (spool.Hold, AssertionError) as exc:
        print('V0145I_RESULT=HOLD_BATCH_PLAN_FAILURE')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
