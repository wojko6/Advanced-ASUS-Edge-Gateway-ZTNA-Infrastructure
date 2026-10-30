#!/usr/bin/env python3
"""HCC V0.14.5D: synthetic source-envelope identity and replay ledger.

Memory only: no journal reader, stdin/file input, network, subprocess or key
store. Keyed IDs pseudonymize synthetic identity; they do not authenticate a
journal source. The new schema is deliberately not accepted by the A-C spool.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hmac
import json
import re

import v0145a_segment_spool as spool

SCHEMA = 'hcc-v0145d-identity-event/1'
UNIT = 'dns-guard-monitoring.service'
SOURCE = 'synthetic-unit-envelope'
ENVELOPE_KEYS = frozenset(('boot', 'cursor', 'time_us', 'unit', 'kind'))
BOOT_RE = re.compile(r'\A[0-9a-f]{32}\Z', re.ASCII)
CURSOR_RE = re.compile(r'\A[A-Za-z0-9_;=:+./-]{1,512}\Z', re.ASCII)
STAMP_RE = re.compile(r'\A[1-9][0-9]{14,15}\Z', re.ASCII)
MAX_BYTES = 65536
MAX_ROWS = 128
MAX_IDENTITIES = 1024
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
MIN_US = 946684800000000  # 2000-01-01 UTC
MAX_US = 4133980799999999  # 2100-12-31 UTC, inclusive

# Public, deterministic fixture only. Not a secret or a deployable host key.
SYNTHETIC_KEY = bytes(range(32))


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def require_key(key):
    if type(key) is not bytes or len(key) != 32:
        raise spool.Hold('IDENTITY_KEY_SHAPE')


def scope_for(key):
    require_key(key)
    return hmac.digest(key, b'hcc-v0145d/synthetic-scope/1', 'sha256').hex()


def normalized_events(raw, key):
    """Validate all synthetic envelopes, retaining microseconds exactly.

    An opaque cursor's syntax is bounded, not verified against journald. The
    fixed unit field is a declaration, not trusted source provenance. Caller
    knowledge of the key is likewise not proof that input came from that unit.
    """
    scope = scope_for(key)
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise spool.Hold('ENVELOPE_BYTES_LIMIT')
    lines = raw.splitlines()
    if not 1 <= len(lines) <= MAX_ROWS or any(not line for line in lines):
        raise spool.Hold('ENVELOPE_ROW_LIMIT')
    result, total, prior = [], 0, None
    for line in lines:
        try:
            obj = json.loads(line.decode('utf-8'), object_pairs_hook=spool.no_duplicates,
                             parse_constant=lambda _: (_ for _ in ()).throw(spool.Hold('ENVELOPE_NONFINITE')))
        except (UnicodeError, ValueError, RecursionError) as exc:
            raise spool.Hold('ENVELOPE_JSON') from exc
        if type(obj) is not dict or set(obj) != ENVELOPE_KEYS:
            raise spool.Hold('ENVELOPE_SCHEMA')
        if any(type(v) is not str for v in obj.values()):
            raise spool.Hold('ENVELOPE_FIELD_TYPE')
        if (not BOOT_RE.fullmatch(obj['boot']) or not CURSOR_RE.fullmatch(obj['cursor']) or
                not STAMP_RE.fullmatch(obj['time_us']) or obj['unit'] != UNIT or
                obj['kind'] not in spool.ALLOWED_KINDS):
            raise spool.Hold('ENVELOPE_VALUE')
        stamp = int(obj['time_us'])
        if not MIN_US <= stamp <= MAX_US:
            raise spool.Hold('ENVELOPE_TIME_RANGE')
        if prior is not None and stamp < prior:
            raise spool.Hold('ENVELOPE_TIME_ORDER')
        prior = stamp
        identity = canonical({'domain': 'hcc-v0145d/synthetic-identity/1',
                              'unit': UNIT, 'boot': obj['boot'], 'cursor': obj['cursor']})
        event_id = hmac.digest(key, identity, 'sha256').hex()
        timestamp = (EPOCH + timedelta(microseconds=stamp)).isoformat(timespec='microseconds').replace('+00:00', 'Z')
        encoded = canonical({'schema': SCHEMA, 'scope': scope, 'event_id': event_id,
                             'time': timestamp, 'kind': obj['kind'],
                             'component': spool.EXPECTED_COMPONENT, 'source': SOURCE})
        total += len(encoded) + 1
        if total > MAX_BYTES:
            raise spool.Hold('IDENTITY_OUTPUT_BYTES_LIMIT')
        result.append(encoded)
    return tuple(result)


@dataclass(frozen=True)
class BatchResult:
    events: bytes
    accepted: int
    duplicates: int


class IdentityLedger:
    """Bounded in-memory, cooperative single-caller replay/conflict model.

    The same ID with different canonical payload is HOLD, never last-write-wins.
    Validate the whole batch before committing entries. No eviction, persistence,
    source authentication, delivery ACK or cross-ledger deduplication is provided.
    """
    def __init__(self):
        self._scope = None
        self._events = {}

    @property
    def size(self):
        return len(self._events)

    def accept(self, raw, key):
        events = normalized_events(raw, key)
        scope = scope_for(key)
        if self._scope is not None and not hmac.compare_digest(self._scope, scope):
            raise spool.Hold('IDENTITY_SCOPE_CHANGED')
        pending, duplicates = {}, 0
        for encoded in events:
            event_id = json.loads(encoded)['event_id']
            existing = pending.get(event_id, self._events.get(event_id))
            if existing is not None:
                if existing != encoded:
                    raise spool.Hold('SAME_ID_DIFFERENT_PAYLOAD')
                duplicates += 1
            else:
                pending[event_id] = encoded
        if self.size + len(pending) > MAX_IDENTITIES:
            raise spool.Hold('IDENTITY_LEDGER_FULL')
        self._events.update(pending)
        self._scope = scope
        return BatchResult(b''.join(encoded + b'\n' for encoded in pending.values()),
                           len(pending), duplicates)


def envelope(cursor, stamp=1793350800000000, *, boot='a' * 32, kind='SSH_TIMEOUT'):
    """Synthetic fixture factory; no actual cursor/boot is read."""
    return canonical({'boot': boot, 'cursor': cursor, 'time_us': str(stamp),
                      'unit': UNIT, 'kind': kind}) + b'\n'


def self_test():
    ledger = IdentityLedger()
    first = envelope('synthetic-cursor-001', 1793350800000001)
    second = envelope('synthetic-cursor-002', 1793350800000002)
    accepted = ledger.accept(first + second, SYNTHETIC_KEY)
    assert accepted.accepted == 2 and accepted.duplicates == 0
    values = [json.loads(line) for line in accepted.events.splitlines()]
    assert values[0]['time'].endswith('000001Z') and values[1]['time'].endswith('000002Z')
    repeated = ledger.accept(second, SYNTHETIC_KEY)
    assert repeated.accepted == 0 and repeated.duplicates == 1 and not repeated.events
    try:
        ledger.accept(envelope('synthetic-cursor-002', 1793350800000002,
                               kind='COLLECTOR_EXIT_255'), SYNTHETIC_KEY)
    except spool.Hold:
        pass
    else:
        raise AssertionError('IDENTITY_CONFLICT_ACCEPTED')
    assert ledger.size == 2
    for forbidden in (b'synthetic-cursor-', b'a' * 32, SYNTHETIC_KEY):
        assert forbidden not in accepted.events
    print('V0145D_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')
    print('NO_NETWORK_NO_SUBPROCESS_NO_FILES_WRITTEN=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    ledger = IdentityLedger()
    # Distinct cursors can share time/kind; both must survive normalization.
    one, two = envelope('synthetic-cursor-001'), envelope('synthetic-cursor-002')
    first = ledger.accept(one + two, SYNTHETIC_KEY)
    replayed = ledger.accept(two, SYNTHETIC_KEY)
    assert first.accepted == 2 and replayed.accepted == 0 and replayed.duplicates == 1
    try:
        ledger.accept(envelope('synthetic-cursor-002', kind='COLLECTOR_EXIT_255'), SYNTHETIC_KEY)
    except spool.Hold as exc:
        assert str(exc) == 'SAME_ID_DIFFERENT_PAYLOAD'
    else:
        raise AssertionError('IDENTITY_CONFLICT_ACCEPTED')
    assert ledger.size == 2
    # Fail-closed schema boundary; do not drop identity to fit the old spool.
    try:
        spool.normalize_sanitized_jsonl(first.events)
    except spool.Hold:
        pass
    else:
        raise AssertionError('LEGACY_SCHEMA_BOUNDARY_BYPASSED')
    print('=== HCC V0.14.5D / SYNTHETIC EVENT IDENTITY ===')
    print('DISTINCT_SAME_TIME_KIND_EVENTS=2')
    print('OVERLAPPING_BATCH_NEW_EVENTS=0')
    print('OVERLAPPING_BATCH_DUPLICATE_ENVELOPES=1')
    print('SAME_ID_CHANGED_PAYLOAD=HOLD_WITHOUT_LEDGER_CHANGE')
    print('TIME_PRECISION=MICROSECONDS_INTEGER_CONVERSION')
    print('RAW_BOOT_CURSOR_KEY_OUTPUT=NO')
    print('SOURCE_PROVENANCE=DECLARED_SYNTHETIC_NOT_AUTHENTICATED')
    print('KEY_LIFECYCLE=NOT_IMPLEMENTED_PUBLIC_FIXTURE_ONLY')
    print('A_C_SPOOL_SCHEMA_COMPATIBLE=NO')
    print('LEDGER_PERSISTENCE=NOT_IMPLEMENTED')
    print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
    print('NETWORK=NO FILE_WRITES=NO PRODUCTION_CHANGES=NO')
    print('V0145D_RESULT=PASS_SYNTHETIC_IDENTITY_ONLY')
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
        print('V0145D_RESULT=HOLD_SYNTHETIC_IDENTITY_FAILURE')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
