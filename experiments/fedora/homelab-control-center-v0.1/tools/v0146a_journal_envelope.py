#!/usr/bin/env python3
"""V0.14.6A: supplied journal-like JSON -> D identity / E snapshot, memory only.

Metadata in supplied bytes is UNVERIFIED. No journal reader, actual provenance,
file/key input, subprocess, network, state mutation, ACK or deployment.
CLI accepts only --self-test / --lab with public synthetic fixtures.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import re

import v0145a_segment_spool as spool
import v0145d_event_identity as identity
import v0145e_atomic_handoff as handoff

MAX_BYTES = 1024 * 1024
MAX_ROWS = 128
MAX_ROW_BYTES = 16 * 1024
MAX_FIELDS = 64
MAX_MESSAGE_BYTES = 4096
MAX_UID = 2**32 - 2
FIELD_RE = re.compile(r'\A[A-Z_][A-Z0-9_]{0,63}\Z', re.ASCII)
REQUIRED = frozenset(('__CURSOR', '__REALTIME_TIMESTAMP', '_BOOT_ID',
                      '_SYSTEMD_USER_UNIT', '_UID', '_SYSTEMD_OWNER_UID',
                      '_TRANSPORT', 'MESSAGE'))


@dataclass(frozen=True)
class AdaptedSnapshot:
    input_records: int
    classified_records: int
    ignored_records: int
    accepted_events: int
    duplicate_events: int
    snapshot: bytes | None


def classify_message(message):
    """Narrow legacy-style text hints, not a diagnosis or trusted metadata.

    Manager exit-255 messages require separate attribution and are excluded.
    """
    low = message.lower()
    if low.startswith('ssh:'):
        if 'timed out' in low or 'timeout' in low:
            return 'SSH_TIMEOUT'
        if 'permission denied' in low:
            return 'SSH_AUTH_FAILURE'
    if low.startswith('curl:') and ('timed out' in low or 'timeout' in low):
        return 'HTTP_IMPORT_TIMEOUT'
    return None


def _record(line, expected_uid):
    if len(line) > MAX_ROW_BYTES:
        raise spool.Hold('JOURNAL_ROW_BYTES_LIMIT')
    try:
        obj = json.loads(line.decode('utf-8'), object_pairs_hook=spool.no_duplicates,
                         parse_constant=lambda _: (_ for _ in ()).throw(spool.Hold('JOURNAL_NONFINITE')))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise spool.Hold('JOURNAL_JSON') from exc
    if (type(obj) is not dict or not REQUIRED <= obj.keys() or len(obj) > MAX_FIELDS or
            any(not FIELD_RE.fullmatch(key) for key in obj)):
        raise spool.Hold('JOURNAL_FIELDS')
    if any(type(obj[key]) is not str for key in REQUIRED):
        raise spool.Hold('JOURNAL_REQUIRED_FIELD_TYPE')
    if (obj['_SYSTEMD_USER_UNIT'] != identity.UNIT or
            obj['_UID'] != str(expected_uid) or obj['_SYSTEMD_OWNER_UID'] != str(expected_uid) or
            obj['_TRANSPORT'] != 'stdout' or '_LINE_BREAK' in obj):
        raise spool.Hold('JOURNAL_DECLARED_ORIGIN_OR_LINE_BOUNDARY')
    if (not identity.BOOT_RE.fullmatch(obj['_BOOT_ID']) or
            not identity.CURSOR_RE.fullmatch(obj['__CURSOR']) or
            not identity.STAMP_RE.fullmatch(obj['__REALTIME_TIMESTAMP'])):
        raise spool.Hold('JOURNAL_ADDRESS_OR_TIME_SHAPE')
    stamp = int(obj['__REALTIME_TIMESTAMP'])
    if not identity.MIN_US <= stamp <= identity.MAX_US:
        raise spool.Hold('JOURNAL_TIME_RANGE')
    message = obj['MESSAGE']
    try:
        message_bytes = message.encode('utf-8')
    except UnicodeError as exc:
        raise spool.Hold('JOURNAL_MESSAGE_ENCODING') from exc
    if (not message or any(ord(char) < 32 or ord(char) == 127 for char in message) or
            len(message_bytes) > MAX_MESSAGE_BYTES):
        raise spool.Hold('JOURNAL_MESSAGE_SHAPE_OR_BYTES')
    return obj['_BOOT_ID'], obj['__CURSOR'], stamp, classify_message(message), message_bytes


def adapt_snapshot(raw, *, expected_uid, key):
    """Whole supplied batch -> one canonical E snapshot, or no matched events.

    Every row, including unclassified messages, must meet the declared origin
    contract. Fields in bytes can be forged; this is NOT trusted journal input.
    No persistent ledger, source cursor/checkpoint or receiver state exists.
    """
    if type(expected_uid) is not int or not 1 <= expected_uid <= MAX_UID:
        raise spool.Hold('JOURNAL_EXPECTED_UID')
    identity.require_key(key)
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise spool.Hold('JOURNAL_BYTES_LIMIT')
    lines = raw.splitlines()
    if not 1 <= len(lines) <= MAX_ROWS or any(not line for line in lines):
        raise spool.Hold('JOURNAL_ROW_LIMIT')
    envelopes, seen, prior, ignored = [], {}, None, 0
    for line in lines:
        boot, cursor, stamp, kind, message_bytes = _record(line, expected_uid)
        if prior is not None and stamp < prior:
            raise spool.Hold('JOURNAL_TIME_ORDER')
        prior = stamp
        # Private message bytes are compared only inside this call, never
        # emitted or stored in the E snapshot. Equal hints need not mean an
        # equal source record, including when both messages are unclassified.
        address, signature = (boot, cursor), (stamp, kind, message_bytes)
        if address in seen and seen[address] != signature:
            raise spool.Hold('JOURNAL_SAME_ADDRESS_CHANGED_EVENT')
        seen[address] = signature
        if kind is None:
            ignored += 1
        else:
            envelopes.append(identity.envelope(cursor, stamp, boot=boot, kind=kind))
    if not envelopes:
        return AdaptedSnapshot(len(lines), 0, ignored, 0, 0, None)
    # A fresh bounded D ledger deduplicates only within this supplied batch.
    batch = identity.IdentityLedger().accept(b''.join(envelopes), key)
    events = sorted(batch.events.splitlines(), key=lambda payload: json.loads(payload)['event_id'])
    snapshot = handoff.encode_snapshot(identity.scope_for(key), events)
    handoff.decode_snapshot(snapshot)
    return AdaptedSnapshot(len(lines), len(envelopes), ignored,
                           batch.accepted, batch.duplicates, snapshot)


def fixture_record(cursor='synthetic-cursor-001', stamp=1793350800000001,
                   message='ssh: private.example: Connection timed out'):
    return {'__CURSOR': cursor, '__REALTIME_TIMESTAMP': str(stamp), '_BOOT_ID': 'a' * 32,
            '_SYSTEMD_USER_UNIT': identity.UNIT, '_UID': '1000', '_SYSTEMD_OWNER_UID': '1000',
            '_TRANSPORT': 'stdout', 'MESSAGE': message, '_HOSTNAME': 'private.example'}


def fixture_inputs():
    one = fixture_record()
    two = fixture_record('synthetic-cursor-002')
    unknown = fixture_record('synthetic-cursor-003', 1793350800000002, 'collector finished')
    curl = fixture_record('synthetic-cursor-004', 1793350800000003, 'curl: (28) Operation timed out')
    return b''.join(identity.canonical(row) + b'\n' for row in (one, two, two, unknown, curl))


def self_test():
    result = adapt_snapshot(fixture_inputs(), expected_uid=1000, key=identity.SYNTHETIC_KEY)
    assert (result.input_records, result.classified_records, result.ignored_records,
            result.accepted_events, result.duplicate_events) == (5, 4, 1, 3, 1)
    events = handoff.decode_snapshot(result.snapshot).events
    assert len(events) == 3
    assert sum(json.loads(event)['time'].endswith('000001Z') for event in events) == 2
    for raw_private in (b'private.example', b'synthetic-cursor-', b'"_UID"', b'"MESSAGE"', b'a' * 32):
        assert raw_private not in result.snapshot
    print('V0146A_SELFTEST=PASS_SUPPLIED_METADATA_MODEL_ONLY')
    print('NO_NETWORK_NO_SUBPROCESS_NO_FILE_WRITES=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    self_test()
    print('=== HCC V0.14.6A / SUPPLIED JOURNAL ENVELOPE ADAPTER ===')
    print('INPUT_RECORDS=5 CLASSIFIED_RECORDS=4 IGNORED_RECORDS=1')
    print('UNIQUE_IDENTITY_EVENTS=3 DUPLICATE_EVENTS=1')
    print('OUTPUT=CANONICAL_E_SNAPSHOT_IN_MEMORY')
    print('TIME_PRECISION=EXACT_INTEGER_MICROSECONDS')
    print('SOURCE_PROVENANCE=UNVERIFIED_SUPPLIED_BYTES')
    print('TRUSTED_JOURNAL_READER=NOT_IMPLEMENTED')
    print('MANAGER_EXIT_255_ATTRIBUTION=NOT_SUPPORTED')
    print('PERSISTENCE_ACK_CHECKPOINT_RETENTION=NO')
    print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
    print('NETWORK=NO SUBPROCESS=NO FILE_WRITES=NO PRODUCTION_CHANGES=NO')
    print('V0146A_RESULT=PASS_SUPPLIED_METADATA_MODEL_ONLY')
    print('DEPLOYMENT_GATE=HOLD')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--self-test', action='store_true')
    mode.add_argument('--lab', action='store_true')
    args = parser.parse_args()
    try:
        self_test() if args.self_test else run_lab()
    except (spool.Hold, AssertionError) as exc:
        print('V0146A_RESULT=HOLD_SUPPLIED_METADATA_MODEL')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
