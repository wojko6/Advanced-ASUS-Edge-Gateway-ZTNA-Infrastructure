#!/usr/bin/env python3
"""C.64.0: offline in-memory VictoriaMetrics envelope adapter (SYNTHETIC ONLY).

Reuses the pinned C.63.8.1 parser and assessment logic without calling any
network, host, subprocess, model, router or filesystem-write API. Every one of
the eight VM-like responses is fabricated in memory. The future 2030 clock is
fictional, not an incident timestamp. No production data enters this module.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
C63_DIR = Path(__file__).resolve().parent.parent / 'c63'
sys.path.insert(0, str(C63_DIR))
import local_ai_agent_v021c63_8_1_vm_stats_envelope_hotfix_lab_v01 as vm

SCHEMA = 'local-ai-agent.v0.21.c64.0.synthetic-vm-envelope-adapter.v1'
FIXED_NOW = int(datetime(2030, 2, 13, 9, 0, tzinfo=timezone(timedelta(hours=1))).timestamp())
CASES = (
    'baseline', 'stats_envelope', 'missing_local', 'stale_local',
    'future_local', 'stale_collection', 'contradictory_flags', 'invalid_guard',
)
ORDER = tuple((name, kind) for _, name in vm.METRICS
              for kind in ('value', 'sample_time'))
KEYS = frozenset(ORDER)
MAX_BATCH_BYTES = 8 * vm.MAX_RESPONSE_BYTES
MAX_SUMMARY_BYTES = 3600


class Hold(Exception):
    """Only a fixed public hold code is emitted by CLI."""


def fixture_responses(scenario='baseline'):
    """Exactly eight fictional VM JSON envelopes, in canonical order."""
    if type(scenario) is not str or scenario not in CASES:
        raise Hold('SCENARIO_NOT_WHITELISTED')
    values, times, now = vm.fixture(FIXED_NOW)
    if scenario == 'missing_local':
        values['local'] = None
        times['local'] = None
    elif scenario == 'stale_local':
        times['local'] = type(times['local'])(now - vm.TTL_RAW - 1)
    elif scenario == 'future_local':
        times['local'] = type(times['local'])(now + vm.FUTURE_SECONDS + 1)
    elif scenario == 'stale_collection':
        values['collection'] = now - vm.TTL_COLLECTION - 1
    elif scenario == 'contradictory_flags':
        values['bootstrap'] = 1
    elif scenario == 'invalid_guard':
        values['valid'] = 0
    packets = {}
    for key, name in vm.METRICS:
        for kind in ('value', 'sample_time'):
            value = values[key] if kind == 'value' else times[key]
            blob = vm.vector(name, kind, now, value)
            if scenario == 'stats_envelope':
                envelope = json.loads(blob)
                envelope['stats'] = {'executionTimeMsec': 1, 'seriesFetched': '1'}
                blob = json.dumps(envelope, sort_keys=True, separators=(',', ':')).encode('ascii')
            packets[(name, kind)] = blob
    return packets


def fingerprint(packets):
    """Transport-independent byte identity of the ordered synthetic responses."""
    hasher = hashlib.sha256()
    for key in ORDER:
        blob = packets[key]
        hasher.update(len(blob).to_bytes(4, 'big'))
        hasher.update(blob)
    return hasher.hexdigest()


def assess_packets(packets, *, evaluated_at=FIXED_NOW):
    """Convert fixed VM-like envelopes to an unprivileged bounded summary."""
    if type(evaluated_at) is not int or evaluated_at != FIXED_NOW:
        raise Hold('UNAPPROVED_EVALUATION_CLOCK')
    if type(packets) is not dict or len(packets) != len(ORDER) or set(packets) != KEYS:
        raise Hold('RESPONSE_SET_INVALID')
    if any(type(packets[key]) is not bytes
           or not 1 <= len(packets[key]) <= vm.MAX_RESPONSE_BYTES for key in ORDER):
        raise Hold('RESPONSE_BOUNDARY_INVALID')
    if sum(len(packets[key]) for key in ORDER) > MAX_BATCH_BYTES:
        raise Hold('RESPONSE_BATCH_TOO_LARGE')
    values, times = {}, {}
    try:
        for short, name in vm.METRICS:
            values[short] = vm.parse(name, 'value', packets[(name, 'value')], evaluated_at)
            times[short] = vm.parse(name, 'sample_time', packets[(name, 'sample_time')], evaluated_at)
        source = vm.assess(values, times, evaluated_at)
    except (vm.Hold, ValueError, TypeError) as exc:
        raise Hold('VM_ENVELOPE_REJECTED') from exc
    if (source['schema'] != vm.SCHEMA
            or source['quality_gate_decision'] != 'ABSTAIN_NO_MODEL_INFERENCE'
            or source['dns_health'] != 'NOT_ESTABLISHED'
            or source['root_cause'] != 'UNDETERMINED'
            or source['model_requests'] != 0
            or source['model_action_authority'] != 'NONE'
            or source['remediation_authorized'] is not False
            or source['deployment_gate'] != 'HOLD'):
        raise Hold('C63_SAFETY_INVARIANT')
    result = {
        'schema': SCHEMA,
        'mode': 'SYNTHETIC_OFFLINE_IN_MEMORY',
        'evaluation_epoch_utc': evaluated_at,
        'expected_envelopes': len(ORDER),
        'parsed_envelopes': len(ORDER),
        'source_identity': 'SYNTHETIC_VM_LIKE_FIXTURE_NOT_ENDPOINT',
        'source_authenticity': 'NOT_CRYPTOGRAPHICALLY_ATTESTED',
        'source_fingerprint_sha256': fingerprint(packets),
        'source_fingerprint_is_provenance_attestation': False,
        'observations_are_atomic': False,
        'observation_classification': source['classification'],
        'sampled_mode': source['sampled_mode'],
        'gaps': source['gaps'],
        'quality_gate_decision': source['quality_gate_decision'],
        'dns_health': 'NOT_ESTABLISHED',
        'root_cause': 'UNDETERMINED',
        'next_step': 'MANUAL_EVIDENCE_REVIEW_ONLY',
        'model_requests': 0,
        'model_invoked': False,
        'model_action_authority': 'NONE',
        'remediation_authorized': False,
        'deployment_gate': 'HOLD',
    }
    if len(json.dumps(result, sort_keys=True, separators=(',', ':')).encode('ascii')) > MAX_SUMMARY_BYTES:
        raise Hold('SUMMARY_TOO_LARGE')
    return result


def scenario_summary(name='baseline'):
    return assess_packets(fixture_responses(name))


def matrix():
    return {name: scenario_summary(name) for name in CASES}


class Tests(unittest.TestCase):
    def assert_hold(self, action, code):
        with self.assertRaisesRegex(Hold, '^' + re.escape(code) + '$'):
            action()

    def test_01_exact_eight(self):
        self.assertEqual(tuple(fixture_responses()), ORDER)

    def test_02_all_are_bytes(self):
        self.assertTrue(all(type(v) is bytes for v in fixture_responses().values()))

    def test_03_baseline_mode(self):
        self.assertEqual(scenario_summary()['sampled_mode'], 'LOCAL')

    def test_04_baseline_classification(self):
        self.assertEqual(scenario_summary()['observation_classification'],
                         'DNS_GUARD_MODE_SAMPLED_ONLY')

    def test_05_stats_envelope_accepted(self):
        self.assertEqual(scenario_summary('stats_envelope')['sampled_mode'], 'LOCAL')

    def test_06_missing_is_insufficient(self):
        self.assertEqual(scenario_summary('missing_local')['observation_classification'],
                         'INSUFFICIENT_EVIDENCE')

    def test_07_stale_is_insufficient(self):
        self.assertIn('LOCAL_RAW_SAMPLE_STALE', scenario_summary('stale_local')['gaps'])

    def test_08_future_is_insufficient(self):
        self.assertIn('LOCAL_RAW_SAMPLE_IN_FUTURE', scenario_summary('future_local')['gaps'])

    def test_09_collection_stale(self):
        self.assertIn('COLLECTION_VALUE_STALE', scenario_summary('stale_collection')['gaps'])

    def test_10_contradictory_flags(self):
        self.assertIn('MODE_FLAGS_CONTRADICTORY', scenario_summary('contradictory_flags')['gaps'])

    def test_11_invalid_guard_not_health_proof(self):
        self.assertEqual(scenario_summary('invalid_guard')['observation_classification'],
                         'INVALID_DNS_GUARD_STATE_SAMPLED')

    def test_12_all_abstain(self):
        self.assertTrue(all(x['quality_gate_decision'] == 'ABSTAIN_NO_MODEL_INFERENCE'
                            for x in matrix().values()))

    def test_13_no_actions_or_models(self):
        for x in matrix().values():
            self.assertEqual(x['model_requests'], 0)
            self.assertFalse(x['model_invoked'])
            self.assertFalse(x['remediation_authorized'])
            self.assertEqual(x['model_action_authority'], 'NONE')
            self.assertEqual(x['deployment_gate'], 'HOLD')

    def test_14_no_diagnosis_proof(self):
        for x in matrix().values():
            self.assertEqual(x['root_cause'], 'UNDETERMINED')
            self.assertEqual(x['dns_health'], 'NOT_ESTABLISHED')

    def test_15_no_source_provenance_claim(self):
        x = scenario_summary()
        self.assertFalse(x['source_fingerprint_is_provenance_attestation'])
        self.assertEqual(x['source_authenticity'], 'NOT_CRYPTOGRAPHICALLY_ATTESTED')

    def test_16_not_atomic(self):
        self.assertFalse(scenario_summary()['observations_are_atomic'])

    def test_17_reproducible(self):
        self.assertEqual(scenario_summary(), scenario_summary())

    def test_18_bounded_json(self):
        self.assertLess(len(json.dumps(scenario_summary()).encode()), MAX_SUMMARY_BYTES)

    def test_19_unknown_scenario_rejected(self):
        self.assert_hold(lambda: scenario_summary('production'), 'SCENARIO_NOT_WHITELISTED')

    def test_20_missing_response_rejected(self):
        x = fixture_responses()
        del x[ORDER[0]]
        self.assert_hold(lambda: assess_packets(x), 'RESPONSE_SET_INVALID')

    def test_21_extra_response_rejected(self):
        x = fixture_responses()
        x[('arbitrary_query', 'value')] = b'{}'
        self.assert_hold(lambda: assess_packets(x), 'RESPONSE_SET_INVALID')

    def test_22_nonbytes_rejected(self):
        x = fixture_responses()
        x[ORDER[0]] = {'raw': 'fake'}
        self.assert_hold(lambda: assess_packets(x), 'RESPONSE_BOUNDARY_INVALID')

    def test_23_overlarge_rejected(self):
        x = fixture_responses()
        x[ORDER[0]] = b'a' * (vm.MAX_RESPONSE_BYTES + 1)
        self.assert_hold(lambda: assess_packets(x), 'RESPONSE_BOUNDARY_INVALID')

    def test_24_duplicate_json_key_rejected(self):
        x = fixture_responses()
        x[ORDER[0]] = b'{"status":"success","status":"success"}'
        self.assert_hold(lambda: assess_packets(x), 'VM_ENVELOPE_REJECTED')

    def test_25_foreign_series_label_rejected(self):
        x = fixture_responses()
        key = ORDER[0]
        data = json.loads(x[key])
        data['data']['result'][0]['metric']['private_address'] = 'fictional'
        x[key] = json.dumps(data).encode('utf-8')
        self.assert_hold(lambda: assess_packets(x), 'VM_ENVELOPE_REJECTED')

    def test_26_wrong_evaluation_clock_rejected(self):
        self.assert_hold(lambda: assess_packets(fixture_responses(), evaluated_at=FIXED_NOW+60),
                         'UNAPPROVED_EVALUATION_CLOCK')

    def test_27_nonfinite_rejected(self):
        x = fixture_responses()
        key = ORDER[0]
        obj = json.loads(x[key])
        obj['stats'] = {'executionTimeMsec': float('nan'), 'seriesFetched': '1'}
        x[key] = json.dumps(obj, sort_keys=True).encode('ascii')
        self.assertIn(b'NaN', x[key])
        self.assert_hold(lambda: assess_packets(x), 'VM_ENVELOPE_REJECTED')

    def test_28_http_never_used(self):
        with patch('http.client.HTTPConnection', side_effect=AssertionError('NETWORK')):
            self.assertEqual(scenario_summary()['model_requests'], 0)

    def test_29_no_subprocess(self):
        with patch('subprocess.Popen', side_effect=AssertionError('SUBPROCESS')):
            self.assertEqual(scenario_summary()['model_requests'], 0)

    def test_30_no_private_messages_in_summary(self):
        summary = json.dumps(scenario_summary(), sort_keys=True)
        self.assertNotIn('MESSAGE', summary)
        self.assertNotIn('raw_log', summary)
        self.assertNotIn('192.168.', summary)

    def test_31_digest_is_different_for_modified_scenario(self):
        self.assertNotEqual(scenario_summary()['source_fingerprint_sha256'],
                            scenario_summary('stale_local')['source_fingerprint_sha256'])

    def test_32_boolean_clock_rejected(self):
        self.assert_hold(lambda: assess_packets(fixture_responses(), evaluated_at=True),
                         'UNAPPROVED_EVALUATION_CLOCK')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--self-test', action='store_true')
    mode.add_argument('--fixture-matrix', action='store_true')
    mode.add_argument('--summary-json', action='store_true')
    parser.add_argument('--scenario', choices=CASES, default='baseline')
    args = parser.parse_args(argv)
    if args.self_test:
        outcome = unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        print(f'C640_TESTS={outcome.testsRun} STATUS=' +
              ('PASS_OFFLINE' if outcome.wasSuccessful() else 'HOLD_TEST_FAILED'))
        return 0 if outcome.wasSuccessful() else 1
    try:
        if args.fixture_matrix:
            results = matrix()
            for key in CASES:
                print('SCENARIO=' + key + ' CLASSIFICATION=' +
                      results[key]['observation_classification'] +
                      ' MODEL_REQUESTS=' + str(results[key]['model_requests']))
            print('C640_RESULT=PASS_SYNTHETIC_MATRIX_ONLY')
        else:
            print(json.dumps(scenario_summary(args.scenario),
                             sort_keys=True, indent=2, ensure_ascii=True))
        return 0
    except Hold as exc:
        print('C640_RESULT=HOLD_' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
