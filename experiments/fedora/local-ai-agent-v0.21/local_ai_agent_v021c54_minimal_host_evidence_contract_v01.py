#!/usr/bin/env python3
"""Local AI Agent V0.21C.54: minimal host-only incident-evidence.v1 contract.

Offline and standalone. No imports of previous lab scripts, no subprocess,
network, Ollama, filesystem reads/writes, executor or HCC contact.

--fixture emits a deterministic demonstration ONLY, based on previously
operator-reported C.49 results; NOT a fresh or independently certified read.
--validate-stdin validates a caller-supplied summary, which is never promoted
to trusted telemetry merely because it matches the schema.

This is an API *boundary prototype*, not a live collector, approval or audit
of a deployed HCC. Deployment stays HOLD.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import sys
import unittest

SCHEMA = 'incident-evidence.v1'
INPUT_SCHEMA = 'host-summary-input.v1'
WINDOW_START = '2026-10-27T15:40:00Z'
WINDOW_END = '2026-10-27T16:40:00Z'
METRICS = (
    'asus_edge_dns_guard_mode_local',
    'asus_edge_dns_guard_mode_bootstrap',
    'asus_edge_dns_guard_state_valid',
    'asus_edge_dns_guard_last_transition_timestamp_seconds',
    'asus_edge_dns_guard_fallback_since_timestamp_seconds',
    'asus_edge_dns_guard_fallback_transitions_runtime_total',
    'asus_edge_dns_guard_collection_timestamp_seconds',
)
EVENTS = ('BOOTSTRAP_OBSERVED', 'LOCAL_RESTORED')
LIMITATIONS = (
    'SAMPLED_OBSERVATIONS_ONLY',
    'HIDDEN_TRANSITIONS_NOT_EXCLUDED',
    'EXACT_SWITCH_TIMES_NOT_PROVEN',
    'DNS_QUERY_PATH_HEALTH_NOT_PROVEN',
    'DEPLOYED_HCC_PARITY_NOT_TESTED',
    'INCIDENT_CAUSE_NOT_ESTABLISHED',
)
MAX_INPUT_BYTES = 8192
MAX_OUTPUT_BYTES = 8192
MAX_ROWS = 256
MAX_EVENTS = 16
REQUIRED = frozenset({
    'schema', 'window_start_utc', 'window_end_utc', 'grid_step_seconds',
    'grid_rows', 'seven_metric_names', 'seven_series_present_rows',
    'distinct_collections', 'repeated_collections', 'valid_local',
    'valid_bootstrap', 'invalid', 'stale', 'missing', 'observed_adjacent_changes',
    'hcc_observed_events', 'hcc_unknown_events', 'hcc_stale_events',
    'observed_event_order',
})
COUNTS = (
    'grid_rows', 'seven_series_present_rows', 'distinct_collections',
    'repeated_collections', 'valid_local', 'valid_bootstrap',
    'invalid', 'stale', 'missing', 'observed_adjacent_changes',
    'hcc_observed_events', 'hcc_unknown_events', 'hcc_stale_events',
)


class Hold(Exception):
    """Fail closed on input that cannot support bounded evidence."""


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _no_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict:
    output = {}
    for key, value in pairs:
        if key in output:
            raise Hold('DUPLICATE_JSON_KEY')
        output[key] = value
    return output


def parse_input(raw: bytes) -> dict:
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_INPUT_BYTES:
        raise Hold('INPUT_SIZE_OR_TYPE')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_no_duplicate_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(Hold('NONFINITE_JSON')))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Hold('INVALID_JSON') from exc
    if type(value) is not dict:
        raise Hold('INPUT_NOT_OBJECT')
    return value


def _timestamp(value: object) -> int:
    if type(value) is not str or len(value) != 20 or not value.endswith('Z'):
        raise Hold('WINDOW_TIMESTAMP_FORMAT')
    try:
        parsed = datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        if parsed.strftime('%Y-%m-%dT%H:%M:%SZ') != value:
            raise ValueError('non-canonical time')
        return int(parsed.timestamp())
    except (ValueError, OverflowError) as exc:
        raise Hold('WINDOW_TIMESTAMP_INVALID') from exc


def normalize(summary: dict, *, provenance_kind: str) -> dict:
    """Strict schema/consistency check, NOT source authentication.

    Caller must authenticate data source upstream. This function cannot know
    whether numbers actually came from VictoriaMetrics or C.49.
    """
    if type(summary) is not dict or set(summary) != REQUIRED:
        raise Hold('MISSING_OR_EXTRA_FIELDS')
    if summary['schema'] != INPUT_SCHEMA:
        raise Hold('INPUT_SCHEMA_INVALID')
    if provenance_kind not in ('OPERATOR_REPORTED_C49_FIXTURE', 'CALLER_SUPPLIED_UNVERIFIED'):
        raise Hold('PROVENANCE_KIND_INVALID')
    step = summary['grid_step_seconds']
    if type(step) is not int or step != 60:
        raise Hold('GRID_STEP_NOT_FIXED')
    start = _timestamp(summary['window_start_utc'])
    end = _timestamp(summary['window_end_utc'])
    if not start < end or (end - start) > 86400 or start % step or end % step:
        raise Hold('WINDOW_INVALID_OR_UNBOUNDED')
    rows = (end - start) // step + 1
    if rows > MAX_ROWS or rows < 2 or rows != summary['grid_rows']:
        raise Hold('GRID_ROWS_INVALID')
    if type(summary['seven_metric_names']) is not list or tuple(summary['seven_metric_names']) != METRICS:
        raise Hold('SEVEN_METRIC_ALLOWLIST_MISMATCH')
    for key in COUNTS:
        value = summary[key]
        if type(value) is not int or not 0 <= value <= MAX_ROWS:
            raise Hold('COUNT_INVALID_'+key.upper())
    if summary['seven_series_present_rows'] != rows:
        raise Hold('SEVEN_SERIES_INCOMPLETE')
    if summary['missing'] or summary['stale'] or summary['invalid'] or summary['hcc_unknown_events'] or summary['hcc_stale_events']:
        raise Hold('INCOMPLETE_OR_UNCERTAIN_SOURCE')
    if summary['valid_local'] + summary['valid_bootstrap'] != rows:
        raise Hold('MODE_ROW_ACCOUNTING_INVALID')
    if summary['distinct_collections'] + summary['repeated_collections'] != rows:
        raise Hold('COLLECTION_ROW_ACCOUNTING_INVALID')
    if summary['distinct_collections'] < 1:
        raise Hold('NO_DISTINCT_COLLECTIONS')
    events = summary['observed_event_order']
    if type(events) is not list or len(events) > MAX_EVENTS or any(type(x) is not str for x in events):
        raise Hold('EVENT_LIST_INVALID')
    if any(x not in EVENTS for x in events):
        raise Hold('EVENT_TYPE_NOT_ALLOWED')
    if summary['observed_adjacent_changes'] != len(events) or summary['hcc_observed_events'] != len(events):
        raise Hold('EVENT_COUNT_INCONSISTENT')
    if len(events) and (summary['valid_local'] == 0 or summary['valid_bootstrap'] == 0):
        raise Hold('EVENT_CONTRADICTS_MODES')
    if any(a == b for a, b in zip(events, events[1:])):
        raise Hold('NONALTERNATING_EVENTS')
    if events == list(EVENTS):
        incident_code = 'FALLBACK_THEN_LOCAL_RESTORED_SAMPLED'
    elif not events and summary['valid_local'] == rows:
        incident_code = 'LOCAL_GRID_ONLY'
    else:
        incident_code = 'BOUNDED_OTHER_OBSERVED_SEQUENCE'
    result = {
        'schema': SCHEMA,
        'source': {
            'family': 'FEDORA_VM_DNS_GUARD_SEVEN_SERIES',
            'metric_count': 7,
            'read_only': True,
            'source_authenticated_by_this_module': False,
        },
        'window': {
            'start_utc': summary['window_start_utc'],
            'end_utc': summary['window_end_utc'],
            'step_seconds': step,
        },
        'observed_events': [
            {'ordinal': index + 1, 'kind': kind, 'exact_event_time': None}
            for index, kind in enumerate(events)
        ],
        'coverage': {
            'grid_rows': rows,
            'distinct_collections': summary['distinct_collections'],
            'repeated_collections': summary['repeated_collections'],
            'valid_local': summary['valid_local'],
            'valid_bootstrap': summary['valid_bootstrap'],
            'missing': summary['missing'],
            'stale': summary['stale'],
            'invalid': summary['invalid'],
            'complete_seven_series_rows': summary['seven_series_present_rows'],
        },
        'classification': incident_code,
        'confidence_limitations': list(LIMITATIONS),
        'provenance': {
            'kind': provenance_kind,
            'data_verification': 'NOT_VERIFIED_BY_C54',
            'previous_operator_result': 'C49_SAMPLED_EVENT_SEQUENCE_CONCORDANT'
            if provenance_kind == 'OPERATOR_REPORTED_C49_FIXTURE' else 'NONE',
            'hcc_event_model': 'FROZEN_REPOSITORY_NOT_DEPLOYED',
            'model_output_authority': 'NONE',
        },
        'deployment_gate': 'HOLD',
    }
    if len(canonical(result)) > MAX_OUTPUT_BYTES:
        raise Hold('OUTPUT_OVER_LIMIT')
    return result


def fixture() -> dict:
    """User-observed historical C49 COUNTS; frozen demo, not a live read."""
    return {
        'schema': INPUT_SCHEMA,
        'window_start_utc': WINDOW_START,
        'window_end_utc': WINDOW_END,
        'grid_step_seconds': 60,
        'grid_rows': 61,
        'seven_metric_names': list(METRICS),
        'seven_series_present_rows': 61,
        'distinct_collections': 56,
        'repeated_collections': 5,
        'valid_local': 58,
        'valid_bootstrap': 3,
        'invalid': 0,
        'stale': 0,
        'missing': 0,
        'observed_adjacent_changes': 2,
        'hcc_observed_events': 2,
        'hcc_unknown_events': 0,
        'hcc_stale_events': 0,
        'observed_event_order': list(EVENTS),
    }


class Tests(unittest.TestCase):
    def valid(self, **changes):
        d = fixture()
        d.update(changes)
        return d

    def assertHold(self, expected, **changes):
        with self.assertRaisesRegex(Hold, expected):
            normalize(self.valid(**changes), provenance_kind='CALLER_SUPPLIED_UNVERIFIED')

    def test_01_fixture_classification(self):
        self.assertEqual(normalize(fixture(), provenance_kind='OPERATOR_REPORTED_C49_FIXTURE')['classification'],
                         'FALLBACK_THEN_LOCAL_RESTORED_SAMPLED')

    def test_02_event_order(self):
        self.assertEqual([x['kind'] for x in normalize(fixture(), provenance_kind='OPERATOR_REPORTED_C49_FIXTURE')['observed_events']], list(EVENTS))

    def test_03_coverage(self):
        self.assertEqual(normalize(fixture(), provenance_kind='OPERATOR_REPORTED_C49_FIXTURE')['coverage']['distinct_collections'], 56)

    def test_04_no_authority(self):
        x = normalize(fixture(), provenance_kind='CALLER_SUPPLIED_UNVERIFIED')
        self.assertFalse(x['source']['source_authenticated_by_this_module'])
        self.assertEqual(x['provenance']['data_verification'], 'NOT_VERIFIED_BY_C54')

    def test_05_reproducible_sha(self):
        self.assertEqual(hashlib.sha256(canonical(normalize(fixture(), provenance_kind='OPERATOR_REPORTED_C49_FIXTURE'))).digest(),
                         hashlib.sha256(canonical(normalize(fixture(), provenance_kind='OPERATOR_REPORTED_C49_FIXTURE'))).digest())

    def test_06_extra_field(self): self.assertHold('MISSING_OR_EXTRA', extra='bad')
    def test_07_missing_metric(self): self.assertHold('SEVEN_METRIC', seven_metric_names=list(METRICS[:-1]))
    def test_08_spoofed_metric(self): self.assertHold('SEVEN_METRIC', seven_metric_names=list(METRICS[:-1])+['evil'])
    def test_09_not_all_series(self): self.assertHold('SEVEN_SERIES_INCOMPLETE', seven_series_present_rows=60)
    def test_10_missing(self): self.assertHold('INCOMPLETE', missing=1)
    def test_11_stale(self): self.assertHold('INCOMPLETE', stale=1)
    def test_12_invalid(self): self.assertHold('INCOMPLETE', invalid=1)
    def test_13_unknown_hcc(self): self.assertHold('INCOMPLETE', hcc_unknown_events=1)
    def test_14_stale_hcc(self): self.assertHold('INCOMPLETE', hcc_stale_events=1)
    def test_15_bool_count(self): self.assertHold('COUNT_INVALID', valid_local=True)
    def test_16_negative_count(self): self.assertHold('COUNT_INVALID', valid_local=-1)
    def test_17_grid_overshoot(self): self.assertHold('GRID_ROWS', grid_rows=62)
    def test_18_wrong_step(self): self.assertHold('GRID_STEP', grid_step_seconds=30)
    def test_19_wrong_window(self): self.assertHold('WINDOW_', window_end_utc=WINDOW_START)
    def test_20_bad_timestamp(self): self.assertHold('WINDOW_TIMESTAMP', window_end_utc='tomorrow')
    def test_21_bad_local_sum(self): self.assertHold('MODE_ROW', valid_local=57)
    def test_22_bad_collection_sum(self): self.assertHold('COLLECTION_ROW', distinct_collections=55)
    def test_23_bad_event_count(self): self.assertHold('EVENT_COUNT', observed_adjacent_changes=1)
    def test_24_bad_hcc_event_count(self): self.assertHold('EVENT_COUNT', hcc_observed_events=1)
    def test_25_unknown_kind(self): self.assertHold('EVENT_TYPE', observed_event_order=['ROOT_EXECUTE','LOCAL_RESTORED'])
    def test_26_duplicate_event(self): self.assertHold('NONALTERNATING', observed_event_order=['BOOTSTRAP_OBSERVED','BOOTSTRAP_OBSERVED'])
    def test_27_bad_schema(self): self.assertHold('INPUT_SCHEMA', schema='wrong')
    def test_28_bad_provenance(self):
        with self.assertRaisesRegex(Hold, 'PROVENANCE_KIND'):
            normalize(fixture(), provenance_kind='LIVE_TRUSTED')

    def test_29_json_duplicate_keys(self):
        with self.assertRaisesRegex(Hold, 'DUPLICATE_JSON_KEY'):
            parse_input(b'{"a":1,"a":2}')

    def test_30_json_nonfinite(self):
        with self.assertRaisesRegex(Hold, 'NONFINITE_JSON'):
            parse_input(b'{"a":NaN}')

    def test_31_oversize_input(self):
        with self.assertRaisesRegex(Hold, 'INPUT_SIZE'):
            parse_input(b' ' * (MAX_INPUT_BYTES + 1))

    def test_32_wrong_input_type(self):
        with self.assertRaisesRegex(Hold, 'INPUT_SIZE'):
            parse_input('text')

    def test_33_zero_transition_local(self):
        d = self.valid(valid_local=61,valid_bootstrap=0,observed_adjacent_changes=0,
                       hcc_observed_events=0,observed_event_order=[])
        self.assertEqual(normalize(d, provenance_kind='CALLER_SUPPLIED_UNVERIFIED')['classification'], 'LOCAL_GRID_ONLY')

    def test_34_no_claim_of_exact_time(self):
        d = normalize(fixture(), provenance_kind='OPERATOR_REPORTED_C49_FIXTURE')
        self.assertTrue(all(x['exact_event_time'] is None for x in d['observed_events']))

    def test_35_explicit_limitations(self):
        d = normalize(fixture(), provenance_kind='OPERATOR_REPORTED_C49_FIXTURE')
        self.assertEqual(tuple(d['confidence_limitations']), LIMITATIONS)

    def test_36_deployment_gate(self):
        self.assertEqual(normalize(fixture(), provenance_kind='OPERATOR_REPORTED_C49_FIXTURE')['deployment_gate'], 'HOLD')

    def test_37_report_no_raw_payload(self):
        d = normalize(fixture(), provenance_kind='OPERATOR_REPORTED_C49_FIXTURE')
        self.assertNotIn('raw_series', canonical(d).decode())

    def test_38_json_shape(self):
        self.assertEqual(parse_input(canonical(fixture())), fixture())


def run_tests():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    print('V021C54_SELFTESTS=%s/%s' % (result.testsRun-result.failures.__len__()-result.errors.__len__(), result.testsRun))
    print('V021C54_NO_IMPORT_OF_PREVIOUS_LABS=YES')
    print('V021C54_SOURCE_AUTHENTICATION=NOT_IMPLEMENTED')
    print('V021C54_NO_NETWORK_NO_MODEL_NO_SUBPROCESS_NO_WRITES=YES')
    print('DEPLOYMENT_GATE=HOLD')
    print('V021C54_SELFTEST_RESULT=' + ('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD'))
    return result.wasSuccessful()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--self-test', action='store_true')
    modes.add_argument('--fixture', action='store_true', help='print bounded evidence from fixed C49 transcript fixture; no live VM')
    modes.add_argument('--validate-stdin', action='store_true', help='read up to 8 KiB of untrusted JSON from stdin and validate only')
    args = parser.parse_args()
    if not run_tests():
        print('V021C54_RESULT=HOLD_TEST_FAILURE')
        return 1
    if args.self_test:
        print('V021C54_RESULT=PASS_HOST_ONLY_EVIDENCE_SCHEMA_TESTS')
        return 0
    try:
        if args.fixture:
            summary = fixture()
            provenance = 'OPERATOR_REPORTED_C49_FIXTURE'
        else:
            summary = parse_input(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
            provenance = 'CALLER_SUPPLIED_UNVERIFIED'
        evidence = normalize(summary, provenance_kind=provenance)
        payload = canonical(evidence)
    except (Hold, TypeError, ValueError, OverflowError) as exc:
        # Never include untrusted original input in error output.
        print('V021C54_RESULT=HOLD_' + (str(exc) if isinstance(exc, Hold) else 'INVALID_INPUT'))
        print('DEPLOYMENT_GATE=HOLD')
        return 1
    print('=== V0.21C.54 / MINIMAL HOST-ONLY EVIDENCE CONTRACT ===')
    print('EVIDENCE_SCHEMA=' + SCHEMA)
    print('EVIDENCE_PROVENANCE=' + provenance)
    print('EVIDENCE_CLASSIFICATION=' + evidence['classification'])
    print('EVIDENCE_SHA256=' + hashlib.sha256(payload).hexdigest())
    print('EVIDENCE_BYTES=' + str(len(payload)))
    print('EVIDENCE_SOURCE_AUTHENTICATED=NO')
    print('VM_HCC_OLLAMA_ROUTER_CONTACTED=NO')
    print('FILES_WRITTEN=NO')
    print('=== EVIDENCE_JSON_BEGIN ===')
    print(payload.decode('utf-8'))
    print('=== EVIDENCE_JSON_END ===')
    print('DEPLOYMENT_GATE=HOLD')
    print('V021C54_RESULT=PASS_BOUNDED_EVIDENCE_SCHEMA_OFFLINE_ONLY')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
