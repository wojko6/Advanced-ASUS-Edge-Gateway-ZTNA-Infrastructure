#!/usr/bin/env python3
"""C.63.0: offline-only synthetic multi-source incident assessment contract.

Safety: standard library only; no file, network, subprocess or model access.
This stage cannot assess actual Fedora/ASUS/DNS health or authorize an action.

Usage:
    python3 -B local_ai_agent_v021c63_multisource_assessment_offline_lab_v01.py --self-test
    python3 -B local_ai_agent_v021c63_multisource_assessment_offline_lab_v01.py --fixture-matrix
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unittest

sys.dont_write_bytecode = True

SCHEMA_IN = 'local-ai-agent.c63.synthetic-multi-source-input.v1'
SCHEMA_OUT = 'local-ai-agent.c63.synthetic-multi-source-assessment.v1'
ORIGIN = 'SYNTHETIC_OFFLINE_ONLY'
EVENT_LIMIT = 16
MAX_INPUT_BYTES = 12000
MAX_REPORT_BYTES = 8192
MAX_WINDOW_SECONDS = 3600
MAX_EVENT_SKEW_SECONDS = 300
MAX_SAMPLE_AGE_SECONDS = 300
EPOCH_CEILING = 4102444800

CODE_SOURCE = {
    'VM_OBSERVATION_GAP': 'VICTORIAMETRICS',
    'VM_FRESH_SAMPLE': 'VICTORIAMETRICS',
    'JOURNAL_SSH_TIMEOUT': 'FEDORA_JOURNAL',
    'JOURNAL_COLLECTOR_SUCCESS': 'FEDORA_JOURNAL',
    'JOURNAL_WIFI_RECONNECT': 'FEDORA_JOURNAL',
    'HISTORICAL_ACL_POLICY_MATCH': 'DATED_POLICY_RECORD',
}
CODES = frozenset(CODE_SOURCE)
TOP_KEYS = frozenset({'schema', 'origin', 'scenario_id', 'evaluated_at_utc',
                      'window_start_utc', 'window_end_utc', 'observations'})
ROW_KEYS = frozenset({'id', 'source', 'code', 'event_at_utc',
                      'sample_at_utc', 'provenance'})


class Hold(Exception):
    """Invalid, incomplete or contradictory input, not a remediation signal."""


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(',', ':')).encode('ascii')


def check_integer(v, reason):
    if type(v) is not int or not 0 <= v <= EPOCH_CEILING:
        raise Hold(reason)
    return v


def evaluate(report):
    """Accept only caller-constructed synthetic coded evidence, never raw logs."""
    if type(report) is not dict or frozenset(report) != TOP_KEYS:
        raise Hold('INPUT_SCHEMA_KEYS_INVALID')
    if report['schema'] != SCHEMA_IN or report['origin'] != ORIGIN:
        raise Hold('INPUT_ORIGIN_OR_SCHEMA_INVALID')
    scenario = report['scenario_id']
    if type(scenario) is not str or not 1 <= len(scenario) <= 48 or not all(
        c.isascii() and (c.isalnum() or c in '_-') for c in scenario
    ):
        raise Hold('SCENARIO_ID_INVALID')
    now = check_integer(report['evaluated_at_utc'], 'EVALUATION_CLOCK_INVALID')
    start = check_integer(report['window_start_utc'], 'WINDOW_START_INVALID')
    end = check_integer(report['window_end_utc'], 'WINDOW_END_INVALID')
    if not start < end <= now or end - start > MAX_WINDOW_SECONDS:
        raise Hold('WINDOW_INVALID')
    rows = report['observations']
    if type(rows) is not list or len(rows) > EVENT_LIMIT:
        raise Hold('OBSERVATIONS_INVALID')
    if len(canonical(report)) > MAX_INPUT_BYTES:
        raise Hold('INPUT_TOO_LARGE')
    seen_ids = set()
    normalized = []
    for row in rows:
        if type(row) is not dict or frozenset(row) != ROW_KEYS:
            raise Hold('OBSERVATION_KEYS_INVALID')
        ident, source, code = row['id'], row['source'], row['code']
        if type(ident) is not str or not 1 <= len(ident) <= 24 or not all(
            c.isascii() and (c.isalnum() or c in '_-') for c in ident
        ) or ident in seen_ids:
            raise Hold('OBSERVATION_ID_INVALID')
        seen_ids.add(ident)
        if (type(code) is not str or code not in CODES
                or type(source) is not str or CODE_SOURCE[code] != source):
            raise Hold('OBSERVATION_SOURCE_OR_CODE_INVALID')
        if row['provenance'] != ORIGIN:
            raise Hold('OBSERVATION_PROVENANCE_INVALID')
        event = check_integer(row['event_at_utc'], 'EVENT_TIMESTAMP_INVALID')
        if not start <= event <= end:
            raise Hold('EVENT_OUTSIDE_WINDOW')
        sample = row['sample_at_utc']
        if code == 'VM_FRESH_SAMPLE':
            check_integer(sample, 'VM_SAMPLE_TIMESTAMP_INVALID')
            if not start <= sample <= event or event - sample > MAX_SAMPLE_AGE_SECONDS:
                raise Hold('VM_SAMPLE_NOT_FRESH')
        elif sample is not None:
            raise Hold('SAMPLE_TIME_ON_NON_VM_FRESH_EVENT')
        normalized.append({'code': code, 'event_at_utc': event,
                           'sample_at_utc': sample, 'source': source})

    codes = {r['code'] for r in normalized}
    gaps = [r['event_at_utc'] for r in normalized
            if r['code'] == 'VM_OBSERVATION_GAP']
    ssh = [r['event_at_utc'] for r in normalized
           if r['code'] == 'JOURNAL_SSH_TIMEOUT']
    related = bool(gaps and ssh and any(
        abs(g - s) <= MAX_EVENT_SKEW_SECONDS for g in gaps for s in ssh
    ))
    if related:
        status = 'CROSS_SOURCE_TEMPORAL_CORRELATION_ONLY'
    elif gaps:
        status = 'SAMPLED_OBSERVATION_GAP_ONLY'
    else:
        status = 'INSUFFICIENT_EVIDENCE'

    last_gap = max(gaps) if gaps else None
    post_gap_fresh = sorted({r['sample_at_utc'] for r in normalized
                             if r['code'] == 'VM_FRESH_SAMPLE'
                             and last_gap is not None
                             and r['event_at_utc'] > last_gap
                             and r['sample_at_utc'] > last_gap})
    resumed = len(post_gap_fresh) >= 2
    output = {
        'schema': SCHEMA_OUT,
        'scenario_id': scenario,
        'origin': ORIGIN,
        'assessment_status': status,
        'classified_codes': sorted(codes),
        'count_by_source': {source: sum(r['source'] == source for r in normalized)
                            for source in sorted(set(CODE_SOURCE.values()))},
        'post_gap_two_distinct_fresh_samples': resumed,
        'resumption_scope': ('SAMPLED_COLLECTION_RESUMED_NOT_HEALTH_PROOF'
                             if resumed else 'NOT_ESTABLISHED'),
        'historical_acl_is_live_policy_proof': False,
        'journal_and_metrics_are_atomic_snapshot': False,
        'source_provenance_attested': False,
        'dns_query_path_health': 'NOT_ESTABLISHED',
        'root_cause': 'UNDETERMINED',
        'interpretation': 'SYNTHETIC_FIXTURE_NOT_REAL_INCIDENT',
        'model_action_authority': 'NONE',
        'deployment_gate': 'HOLD',
    }
    if len(canonical(output)) > MAX_REPORT_BYTES:
        raise Hold('OUTPUT_TOO_LARGE')
    return output


BASE = 1793433600


def event(ident, code, at, *, sample=None):
    return {'id': ident, 'code': code, 'source': CODE_SOURCE[code],
            'event_at_utc': at, 'sample_at_utc': sample, 'provenance': ORIGIN}


def fixture(name):
    common = {'schema': SCHEMA_IN, 'origin': ORIGIN,
              'scenario_id': name, 'evaluated_at_utc': BASE+2400,
              'window_start_utc': BASE, 'window_end_utc': BASE+2100}
    if name == 'gap_only':
        events = [event('g1', 'VM_OBSERVATION_GAP', BASE+300)]
    elif name == 'cross_source':
        events = [event('g1', 'VM_OBSERVATION_GAP', BASE+300),
                  event('s1', 'JOURNAL_SSH_TIMEOUT', BASE+330),
                  event('w1', 'JOURNAL_WIFI_RECONNECT', BASE+1080),
                  event('f1', 'VM_FRESH_SAMPLE', BASE+1200, sample=BASE+1180),
                  event('f2', 'VM_FRESH_SAMPLE', BASE+1500, sample=BASE+1480),
                  event('p1', 'HISTORICAL_ACL_POLICY_MATCH', BASE+100)]
    elif name == 'one_post_gap_sample':
        events = [event('g1', 'VM_OBSERVATION_GAP', BASE+300),
                  event('f1', 'VM_FRESH_SAMPLE', BASE+1200, sample=BASE+1180)]
    elif name == 'no_machine_evidence':
        events = [event('p1', 'HISTORICAL_ACL_POLICY_MATCH', BASE+100)]
    else:
        raise Hold('UNKNOWN_FIXTURE')
    return {**common, 'observations': events}


class ContractTests(unittest.TestCase):
    def assert_hold(self, obj, reason):
        with self.assertRaises(Hold) as caught:
            evaluate(obj)
        self.assertEqual(str(caught.exception), reason)

    def test_01_gap_only(self):
        self.assertEqual(evaluate(fixture('gap_only'))['assessment_status'],
                         'SAMPLED_OBSERVATION_GAP_ONLY')

    def test_02_cross_source(self):
        self.assertEqual(evaluate(fixture('cross_source'))['assessment_status'],
                         'CROSS_SOURCE_TEMPORAL_CORRELATION_ONLY')

    def test_03_two_distinct_samples(self):
        self.assertTrue(evaluate(fixture('cross_source'))['post_gap_two_distinct_fresh_samples'])

    def test_04_one_sample_not_recovered(self):
        self.assertFalse(evaluate(fixture('one_post_gap_sample'))['post_gap_two_distinct_fresh_samples'])

    def test_05_historical_only_insufficient(self):
        self.assertEqual(evaluate(fixture('no_machine_evidence'))['assessment_status'],
                         'INSUFFICIENT_EVIDENCE')

    def test_06_cause_unproven(self):
        self.assertEqual(evaluate(fixture('cross_source'))['root_cause'], 'UNDETERMINED')

    def test_07_no_action(self):
        r = evaluate(fixture('cross_source'))
        self.assertEqual((r['model_action_authority'], r['deployment_gate']), ('NONE', 'HOLD'))

    def test_08_no_health(self):
        self.assertEqual(evaluate(fixture('cross_source'))['dns_query_path_health'],
                         'NOT_ESTABLISHED')

    def test_09_no_policy_proof(self):
        self.assertFalse(evaluate(fixture('cross_source'))['historical_acl_is_live_policy_proof'])

    def test_10_no_atomic_claim(self):
        self.assertFalse(evaluate(fixture('cross_source'))['journal_and_metrics_are_atomic_snapshot'])

    def test_11_reject_live_origin(self):
        x=fixture('gap_only');x['origin']='LIVE';self.assert_hold(x,'INPUT_ORIGIN_OR_SCHEMA_INVALID')

    def test_12_reject_extra_keys(self):
        x=fixture('gap_only');x['raw_log']='secret';self.assert_hold(x,'INPUT_SCHEMA_KEYS_INVALID')

    def test_13_reject_raw_row(self):
        x=fixture('gap_only');x['observations'][0]['raw_message']='secret';self.assert_hold(x,'OBSERVATION_KEYS_INVALID')

    def test_14_reject_wrong_source(self):
        x=fixture('gap_only');x['observations'][0]['source']='ROUTER';self.assert_hold(x,'OBSERVATION_SOURCE_OR_CODE_INVALID')

    def test_15_reject_duplicate_ids(self):
        x=fixture('gap_only');x['observations'].append(x['observations'][0].copy());self.assert_hold(x,'OBSERVATION_ID_INVALID')

    def test_16_reject_wrong_provenance(self):
        x=fixture('gap_only');x['observations'][0]['provenance']='REAL';self.assert_hold(x,'OBSERVATION_PROVENANCE_INVALID')

    def test_17_reject_outside_window(self):
        x=fixture('gap_only');x['observations'][0]['event_at_utc']=BASE+4000;self.assert_hold(x,'EVENT_OUTSIDE_WINDOW')

    def test_18_reject_sample_on_gap(self):
        x=fixture('gap_only');x['observations'][0]['sample_at_utc']=BASE+100;self.assert_hold(x,'SAMPLE_TIME_ON_NON_VM_FRESH_EVENT')

    def test_19_reject_stale_sample(self):
        x=fixture('cross_source');x['observations'][3]['sample_at_utc']=BASE+400;self.assert_hold(x,'VM_SAMPLE_NOT_FRESH')

    def test_20_reject_bool_clock(self):
        x=fixture('gap_only');x['evaluated_at_utc']=True;self.assert_hold(x,'EVALUATION_CLOCK_INVALID')

    def test_21_reject_large_window(self):
        x=fixture('gap_only');x['window_end_utc']=BASE+3700;x['evaluated_at_utc']=BASE+3900;self.assert_hold(x,'WINDOW_INVALID')

    def test_22_reject_too_many_events(self):
        x=fixture('gap_only');x['observations']=[event('g'+str(i),'VM_OBSERVATION_GAP',BASE+300) for i in range(17)];self.assert_hold(x,'OBSERVATIONS_INVALID')

    def test_23_deterministic_report(self):
        x=fixture('cross_source');self.assertEqual(canonical(evaluate(x)), canonical(evaluate(x)))

    def test_24_duplicate_fresh_timestamp_not_enough(self):
        x=fixture('cross_source');x['observations'][4]['event_at_utc']=BASE+1450
        x['observations'][4]['sample_at_utc']=x['observations'][3]['sample_at_utc']
        self.assertFalse(evaluate(x)['post_gap_two_distinct_fresh_samples'])

    def test_25_unrelated_ssh_not_causal(self):
        x=fixture('cross_source');x['observations'][1]['event_at_utc']=BASE+2050
        self.assertEqual(evaluate(x)['assessment_status'], 'SAMPLED_OBSERVATION_GAP_ONLY')

    def test_26_empty_input_insufficient(self):
        x=fixture('gap_only');x['observations']=[]
        self.assertEqual(evaluate(x)['assessment_status'], 'INSUFFICIENT_EVIDENCE')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--self-test', action='store_true')
    group.add_argument('--fixture-matrix', action='store_true')
    args = parser.parse_args(argv)
    print('=== LOCAL AI AGENT C.63.0 / OFFLINE ASSESSMENT ===')
    print('MODE=SYNTHETIC_ONLY NO_NETWORK=YES NO_HOST_READS=YES NO_SUBPROCESS=YES')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    if args.self_test:
        result=unittest.TextTestRunner(verbosity=0).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests))
        print(f'C630_SELFTESTS={result.testsRun-result.failures.__len__()-result.errors.__len__()}/{result.testsRun}')
        print('C630_RESULT=' + ('PASS_SYNTHETIC_ONLY' if result.wasSuccessful() else 'HOLD'))
        return 0 if result.wasSuccessful() else 1
    for name in ('gap_only','cross_source','one_post_gap_sample','no_machine_evidence'):
        report=evaluate(fixture(name))
        print('SCENARIO=' + name + ' STATUS=' + report['assessment_status']
              + ' RESUMED=' + str(report['post_gap_two_distinct_fresh_samples']))
    print('C630_RESULT=PASS_SYNTHETIC_FIXTURE_MATRIX_ONLY')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
