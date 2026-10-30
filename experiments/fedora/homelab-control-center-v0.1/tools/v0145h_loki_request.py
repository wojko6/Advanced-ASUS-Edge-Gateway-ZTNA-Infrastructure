#!/usr/bin/env python3
"""HCC V0.14.5H: memory-only JSON request encoding for synthetic E snapshots.

No HTTP/client/receiver/ACK, file input/output, network, subprocess, journal,
service, retention or deployment. CLI accepts only --self-test or --lab.
Documented JSON shape is not proof of actual Loki acceptance or delivery.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json

import v0145a_segment_spool as spool
import v0145d_event_identity as identity
import v0145e_atomic_handoff as handoff

PATH = '/loki/api/v1/push'
CONTENT_TYPE = 'application/json'
LABELS = (('component', spool.EXPECTED_COMPONENT), ('source', identity.SOURCE))
MAX_EVENTS = 16
MAX_BODY_BYTES = 64 * 1024


@dataclass(frozen=True)
class PushRequest:
    body: bytes
    scope: str
    event_ids: tuple[str, ...]
    sha256: str


def nanoseconds(timestamp):
    """Exact six-fraction UTC source time -> integer nanoseconds as a string."""
    if type(timestamp) is not str or not handoff.TIME_RE.fullmatch(timestamp):
        raise spool.Hold('REQUEST_TIME_SHAPE')
    try:
        stamp = datetime.fromisoformat(timestamp[:-1] + '+00:00')
    except ValueError as exc:
        raise spool.Hold('REQUEST_TIME_VALUE') from exc
    if not 2000 <= stamp.year <= 2100:
        raise spool.Hold('REQUEST_TIME_RANGE')
    delta = stamp - identity.EPOCH
    return str((delta.days * 86400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000)


def build_request(raw_snapshot):
    """Validate the WHOLE E snapshot, then encode one bounded request in memory.

    No truncation, pagination, pending-record selection or checkpoint change.
    Limits here are laboratory choices, not discovered Loki server limits.
    """
    snapshot = handoff.decode_snapshot(raw_snapshot)
    if len(snapshot.events) > MAX_EVENTS:
        raise spool.Hold('REQUEST_EVENT_LIMIT')
    rows = []
    for payload in snapshot.events:
        event = json.loads(payload)
        stamp = nanoseconds(event['time'])
        rows.append((int(stamp), event['event_id'], stamp, payload.decode('ascii')))
    # E validates canonical ID order on input. Only this request is reordered;
    # F/G's ID-based delivery/progress contracts remain untouched.
    rows.sort(key=lambda row: (row[0], row[1]))
    values = [[row[2], row[3]] for row in rows]
    body = identity.canonical({'streams': [{'stream': dict(LABELS), 'values': values}]})
    if len(body) > MAX_BODY_BYTES:
        raise spool.Hold('REQUEST_BYTES_LIMIT')
    return PushRequest(body, snapshot.scope, tuple(row[1] for row in rows), hashlib.sha256(body).hexdigest())


def fixture_snapshot():
    raw = (identity.envelope('synthetic-cursor-001', 1793350800123456) +
           identity.envelope('synthetic-cursor-002', 1793350800123456) +
           identity.envelope('synthetic-cursor-003', 1793350800123457))
    events = identity.normalized_events(raw, identity.SYNTHETIC_KEY)
    ordered = sorted(events, key=lambda payload: json.loads(payload)['event_id'])
    return handoff.encode_snapshot(identity.scope_for(identity.SYNTHETIC_KEY), ordered)


def self_test():
    request = build_request(fixture_snapshot())
    stream = json.loads(request.body)['streams'][0]
    assert stream['stream'] == dict(LABELS)
    assert [row[0] for row in stream['values']] == ['1793350800123456000',
                                                  '1793350800123456000', '1793350800123457000']
    assert len(request.event_ids) == len(set(request.event_ids)) == 3
    assert hashlib.sha256(request.body).hexdigest() == request.sha256
    print('V0145H_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')
    print('SELFTEST_NO_NETWORK_NO_SUBPROCESS_NO_FILE_WRITES=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    request = build_request(fixture_snapshot())
    stream = json.loads(request.body)['streams'][0]
    values = stream['values']
    assert len(values) == len(request.event_ids) == 3
    assert [json.loads(row[1])['event_id'] for row in values] == list(request.event_ids)
    assert [row[0] for row in values] == ['1793350800123456000',
                                        '1793350800123456000', '1793350800123457000']
    assert set(stream['stream']) == {'component', 'source'}
    print('=== HCC V0.14.5H / OFFLINE LOKI JSON REQUEST ===')
    print('SYNTHETIC_RECORDS=3 STREAMS=1')
    print('TIMESTAMP_ENCODING=INTEGER_NANOSECONDS_AS_STRINGS')
    print('MICROSECOND_PRECISION=EXACT_NO_FLOAT')
    print('ORDER=TIMESTAMP_THEN_EVENT_ID')
    print('EVENT_IDENTITIES=JSON_LINES_NOT_STREAM_LABELS')
    print('REQUEST_BODY_BYTES=' + str(len(request.body)))
    print('REQUEST_CONTRACT=DOCUMENTED_JSON_SHAPE_NOT_LOKI_ACCEPTANCE')
    print('DELIVERY_OR_ACK=NOT_IMPLEMENTED')
    print('RETENTION_ACTION=NO_DELETION')
    print('FILES_WRITTEN=NO SUBPROCESS=NO')
    print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
    print('NETWORK=NO PRODUCTION_CHANGES=NO')
    print('V0145H_RESULT=PASS_OFFLINE_REQUEST_ENCODING_ONLY')
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
        print('V0145H_RESULT=HOLD_REQUEST_ENCODING_FAILURE')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
