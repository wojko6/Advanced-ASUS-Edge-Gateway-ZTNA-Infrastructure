#!/usr/bin/env python3
"""V0.21C.61 / offline multi-incident host-only fixture contract.

No imports from the previous pinned lab chain. No VM/Loki/Ollama calls,
no file input/output, no subprocesses, no execution permissions.
This code classifies only synthetic fixed-clock fixtures, not real incidents.

python3 -B THIS.py --self-test
python3 -B THIS.py --fixture-matrix
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True

SCHEMA_IN = 'local-ai-agent.multi-signal.synthetic-fixture.v1'
SCHEMA_OUT = 'local-ai-agent.multi-incident.host-observation.v1'
ORIGIN = 'SYNTHETIC_FIXTURE_ONLY'
NOW = int(datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc).timestamp())
FRESHNESS_SECONDS = 300
MAX_BYTES = 8192
MAX_SIGNALS = 6
MAX_COUNT = 1_000_000
ALLOWED = {
    'dns_guard.mode': ('enum', ('LOCAL', 'BOOTSTRAP', 'UNKNOWN')),
    'dns_guard.state_valid': ('enum', ('VALID', 'INVALID')),
    'pihole.log_entries_1m': ('count', None),
    'unbound.dnssec_probe': ('enum', ('PASS', 'FAIL', 'UNAVAILABLE')),
    'tailscale.peer_probe': ('enum', ('REACHABLE', 'UNREACHABLE', 'UNAVAILABLE')),
    'fedora.collector_state': ('enum', ('RUNNING', 'STOPPED', 'UNKNOWN')),
}
CONDITIONS = {
    ('dns_guard.mode', 'BOOTSTRAP'): 'DNS_GUARD_BOOTSTRAP_SAMPLED',
    ('dns_guard.state_valid', 'INVALID'): 'DNS_GUARD_STATE_INVALID_SAMPLED',
    ('unbound.dnssec_probe', 'FAIL'): 'UNBOUND_DNSSEC_PROBE_FAILURE_SAMPLED',
    ('tailscale.peer_probe', 'UNREACHABLE'): 'TAILSCALE_PEER_PROBE_UNREACHABLE_SAMPLED',
    ('fedora.collector_state', 'STOPPED'): 'FEDORA_COLLECTOR_STOPPED_SAMPLED',
}
IN_KEYS = frozenset(('schema', 'scenario_id', 'origin', 'evaluated_at_utc', 'expected_keys', 'signals'))
SIGNAL_KEYS = frozenset(('key', 'at_utc', 'value'))
OUT_KEYS = frozenset(('schema', 'scenario_id', 'origin', 'evaluated_at_utc', 'status',
                      'observed_conditions', 'data_gaps', 'coverage', 'limits',
                      'model_action_authority', 'deployment_gate'))
LIMITS = (
    'SYNTHETIC_ONLY_NO_REAL_TELEMETRY',
    'SINGLE_SAMPLE_NOT_INCIDENT_DURATION',
    'NO_CRYPTOGRAPHIC_SOURCE_AUTHENTICATION',
    'NO_CAUSALITY_OR_ROOT_CAUSE',
    'NO_DNS_SERVICE_HEALTH_PROOF',
    'NO_HOST_POWER_STATE_PROOF',
    'NO_HCC_DEPLOYED_PARITY',
    'NO_MODEL_OR_EXECUTOR_CONTACT',
)


class Hold(Exception):
    """Fail-closed validation error, never permission to infer missing facts."""


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def exact_keys(obj: object, keys: frozenset[str], reason: str) -> dict:
    if type(obj) is not dict or obj.keys() != keys:
        raise Hold(reason)
    return obj


def validate_fixture(fixture: object) -> tuple[str, list[str], dict[str, tuple[int, object]]]:
    doc = exact_keys(fixture, IN_KEYS, 'FIXTURE_SCHEMA_FIELDS')
    if doc['schema'] != SCHEMA_IN or doc['origin'] != ORIGIN:
        raise Hold('FIXTURE_NOT_SYNTHETIC_CONTRACT')
    ident = doc['scenario_id']
    if type(ident) is not str or not re.fullmatch(r'[a-z][a-z0-9_-]{1,39}', ident):
        raise Hold('SCENARIO_ID_INVALID')
    now = doc['evaluated_at_utc']
    if type(now) is not int or now != NOW:
        raise Hold('CLOCK_NOT_FIXED_SYNTHETIC')
    expected = doc['expected_keys']
    if (type(expected) is not list or not 1 <= len(expected) <= MAX_SIGNALS or
            any(type(k) is not str or k not in ALLOWED for k in expected) or
            len(set(expected)) != len(expected)):
        raise Hold('EXPECTED_SIGNALS_INVALID')
    if expected != sorted(expected):
        raise Hold('EXPECTED_KEYS_NOT_SORTED')
    signals = doc['signals']
    if type(signals) is not list or len(signals) > len(expected):
        raise Hold('SIGNAL_LIST_INVALID')
    parsed = {}
    for entry in signals:
        row = exact_keys(entry, SIGNAL_KEYS, 'SIGNAL_FIELDS_INVALID')
        key, at, val = row['key'], row['at_utc'], row['value']
        if type(key) is not str or key not in expected or key in parsed:
            raise Hold('SIGNAL_UNEXPECTED_OR_DUPLICATE')
        if type(at) is not int or not NOW - 86400 <= at <= NOW:
            raise Hold('SIGNAL_TIMESTAMP_INVALID')
        typ, choices = ALLOWED[key]
        if typ == 'count':
            if type(val) is not int or not 0 <= val <= MAX_COUNT:
                raise Hold('SIGNAL_COUNT_INVALID')
        elif type(val) is not str or val not in choices:
            raise Hold('SIGNAL_ENUM_INVALID')
        parsed[key] = (at, val)
    return ident, expected, parsed


def classify(fixture: object) -> dict:
    ident, expected, observed = validate_fixture(fixture)
    conditions = []
    gaps = []
    fresh = stale = missing = unavailable = 0
    for key in expected:  # sorted, deterministic
        if key not in observed:
            gaps.append({'key': key, 'reason': 'MISSING'})
            missing += 1
            continue
        at, val = observed[key]
        if NOW - at > FRESHNESS_SECONDS:
            gaps.append({'key': key, 'reason': 'STALE'})
            stale += 1
            continue
        if val in ('UNKNOWN', 'UNAVAILABLE'):
            gaps.append({'key': key, 'reason': 'UNAVAILABLE_VALUE'})
            unavailable += 1
            continue
        fresh += 1
        if key == 'pihole.log_entries_1m':
            # Nonzero means log activity; zero does NOT establish a DNS outage.
            if val > 0:
                conditions.append('PIHOLE_LOG_ACTIVITY_SAMPLED_NOT_DNS_SUCCESS')
        elif (key, val) in CONDITIONS:
            conditions.append(CONDITIONS[(key, val)])
    if not fresh:
        status = 'INSUFFICIENT_EVIDENCE'
    elif gaps:
        status = 'PARTIAL_OBSERVATION'
    elif conditions:
        status = 'SAMPLED_CONDITIONS_ONLY'
    else:
        status = 'NO_CLASSIFIED_CONDITION_NOT_HEALTH_PROOF'
    result = {
        'schema': SCHEMA_OUT,
        'scenario_id': ident,
        'origin': ORIGIN,
        'evaluated_at_utc': NOW,
        'status': status,
        'observed_conditions': conditions,
        'data_gaps': gaps,
        'coverage': {'expected': len(expected), 'fresh': fresh,
                     'missing': missing, 'stale': stale, 'unavailable': unavailable},
        'limits': list(LIMITS),
        'model_action_authority': 'NONE',
        'deployment_gate': 'HOLD',
    }
    if result.keys() != OUT_KEYS or len(canonical(result)) > MAX_BYTES:
        raise Hold('OUTPUT_CONTRACT_INVALID')
    return result


def sample(key: str, value: object, age: int = 15) -> dict:
    return {'key': key, 'value': value, 'at_utc': NOW - age}


def fixture(name: str, values: list[dict], expected: list[str] | None = None) -> dict:
    keys = sorted(expected if expected is not None else [s['key'] for s in values])
    return {'schema': SCHEMA_IN, 'scenario_id': name, 'origin': ORIGIN,
            'evaluated_at_utc': NOW, 'expected_keys': keys,
            'signals': values}


def matrix() -> tuple[dict, ...]:
    """Six independent synthetic situations; *not* measured host incidents."""
    return (
        fixture('dns_guard_fallback', [sample('dns_guard.mode', 'BOOTSTRAP'),
                                       sample('dns_guard.state_valid', 'VALID')]),
        fixture('pihole_activity', [sample('pihole.log_entries_1m', 141)]),
        fixture('unbound_probe', [sample('unbound.dnssec_probe', 'FAIL')]),
        fixture('tailscale_peer', [sample('tailscale.peer_probe', 'UNREACHABLE')]),
        fixture('fedora_collector_gap', [sample('fedora.collector_state', 'RUNNING', 3600)],
                ['fedora.collector_state', 'tailscale.peer_probe']),
        fixture('normal_looking_sample', [sample('dns_guard.mode', 'LOCAL'),
                                          sample('unbound.dnssec_probe', 'PASS'),
                                          sample('pihole.log_entries_1m', 0)]),
    )


class ContractTests(unittest.TestCase):
    def base(self):
        return fixture('test_case', [sample('dns_guard.mode', 'BOOTSTRAP')])

    def reject(self, obj, why=None):
        with self.assertRaises(Hold) as ctx:
            classify(obj)
        if why is not None:
            self.assertEqual(str(ctx.exception), why)

    def test_matrix_cases(self):
        expected = (
            ('SAMPLED_CONDITIONS_ONLY', 'DNS_GUARD_BOOTSTRAP_SAMPLED'),
            ('SAMPLED_CONDITIONS_ONLY', 'PIHOLE_LOG_ACTIVITY_SAMPLED_NOT_DNS_SUCCESS'),
            ('SAMPLED_CONDITIONS_ONLY', 'UNBOUND_DNSSEC_PROBE_FAILURE_SAMPLED'),
            ('SAMPLED_CONDITIONS_ONLY', 'TAILSCALE_PEER_PROBE_UNREACHABLE_SAMPLED'),
            ('INSUFFICIENT_EVIDENCE', None),
            ('NO_CLASSIFIED_CONDITION_NOT_HEALTH_PROOF', None),
        )
        for src, (status, condition) in zip(matrix(), expected):
            with self.subTest(src=src['scenario_id']):
                out = classify(src)
                self.assertEqual(out['status'], status)
                if condition is not None:
                    self.assertIn(condition, out['observed_conditions'])
                self.assertEqual(out['model_action_authority'], 'NONE')

    def test_not_synthetic_origin(self):
        f = self.base(); f['origin'] = 'LIVE'; self.reject(f, 'FIXTURE_NOT_SYNTHETIC_CONTRACT')

    def test_nonexistent_schema(self):
        f = self.base(); f['schema'] = 'v2'; self.reject(f)

    def test_extra_input_field(self):
        f = self.base(); f['command'] = 'sudo'; self.reject(f, 'FIXTURE_SCHEMA_FIELDS')

    def test_missing_input_field(self):
        f = self.base(); del f['signals']; self.reject(f)

    def test_non_mapping_input(self):
        self.reject([])

    def test_injected_scenario_id(self):
        f = self.base(); f['scenario_id'] = '../../passwd'; self.reject(f)

    def test_empty_scenario_id(self):
        f = self.base(); f['scenario_id'] = ''; self.reject(f)

    def test_too_long_scenario_id(self):
        f = self.base(); f['scenario_id'] = 'z'*45; self.reject(f)

    def test_non_string_scenario_id(self):
        f = self.base(); f['scenario_id'] = 100; self.reject(f)

    def test_changed_clock(self):
        f = self.base(); f['evaluated_at_utc'] += 1; self.reject(f)

    def test_boolean_clock(self):
        f = self.base(); f['evaluated_at_utc'] = True; self.reject(f)

    def test_empty_expected(self):
        f = self.base(); f['expected_keys'] = []; self.reject(f)

    def test_expected_duplicates(self):
        f = self.base(); f['expected_keys'] *= 2; self.reject(f)

    def test_unknown_expected(self):
        f = self.base(); f['expected_keys'] = ['shell.exec']; self.reject(f)

    def test_expected_unordered(self):
        f = self.base(); f['expected_keys'] = ['pihole.log_entries_1m', 'dns_guard.mode']; self.reject(f)

    def test_expected_too_many(self):
        f = self.base(); f['expected_keys'] = sorted(ALLOWED) + ['bogus']; self.reject(f)

    def test_unexpected_signal(self):
        f = self.base(); f['signals'][0]['key'] = 'pihole.log_entries_1m'; self.reject(f)

    def test_duplicate_signal(self):
        f = self.base(); f['signals'].append(f['signals'][0].copy()); self.reject(f)

    def test_signal_extra_key(self):
        f = self.base(); f['signals'][0]['do'] = 'rm'; self.reject(f)

    def test_signal_missing_key(self):
        f = self.base(); del f['signals'][0]['value']; self.reject(f)

    def test_future_signal(self):
        f = self.base(); f['signals'][0]['at_utc'] = NOW + 1; self.reject(f)

    def test_expired_signal_hard_limit(self):
        f = self.base(); f['signals'][0]['at_utc'] = NOW - 86401; self.reject(f)

    def test_signal_boolean_timestamp(self):
        f = self.base(); f['signals'][0]['at_utc'] = True; self.reject(f)

    def test_signal_float_timestamp(self):
        f = self.base(); f['signals'][0]['at_utc'] = float(NOW); self.reject(f)

    def test_signal_bad_enum(self):
        f = self.base(); f['signals'][0]['value'] = 'UNKNOWN_CMD'; self.reject(f)

    def test_signal_null_enum(self):
        f = self.base(); f['signals'][0]['value'] = None; self.reject(f)

    def test_signal_enum_with_whitespace(self):
        f = self.base(); f['signals'][0]['value'] = 'BOOTSTRAP '; self.reject(f)

    def test_pihole_negative(self):
        f = fixture('case1', [sample('pihole.log_entries_1m', -1)]); self.reject(f)

    def test_pihole_boolean(self):
        f = fixture('case1', [sample('pihole.log_entries_1m', True)]); self.reject(f)

    def test_pihole_string(self):
        f = fixture('case1', [sample('pihole.log_entries_1m', '12')]); self.reject(f)

    def test_pihole_giant(self):
        f = fixture('case1', [sample('pihole.log_entries_1m', MAX_COUNT + 1)]); self.reject(f)

    def test_pihole_nan(self):
        f = fixture('case1', [sample('pihole.log_entries_1m', float('nan'))]); self.reject(f)

    def test_dns_guard_local_not_outage_or_dns_health(self):
        out = classify(fixture('case1', [sample('dns_guard.mode', 'LOCAL')]))
        self.assertEqual(out['status'], 'NO_CLASSIFIED_CONDITION_NOT_HEALTH_PROOF')
        self.assertEqual(out['observed_conditions'], [])
        self.assertIn('NO_DNS_SERVICE_HEALTH_PROOF', out['limits'])

    def test_zero_pihole_not_outage(self):
        out = classify(fixture('case1', [sample('pihole.log_entries_1m', 0)]))
        self.assertEqual(out['status'], 'NO_CLASSIFIED_CONDITION_NOT_HEALTH_PROOF')
        self.assertEqual(out['observed_conditions'], [])

    def test_unbound_unavailable_is_gap(self):
        out = classify(fixture('case1', [sample('unbound.dnssec_probe', 'UNAVAILABLE')]))
        self.assertEqual(out['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(out['data_gaps'], [{'key':'unbound.dnssec_probe','reason':'UNAVAILABLE_VALUE'}])

    def test_dns_guard_unknown_is_gap(self):
        out = classify(fixture('case1', [sample('dns_guard.mode', 'UNKNOWN')]))
        self.assertEqual(out['status'], 'INSUFFICIENT_EVIDENCE')

    def test_unbound_pass_not_incident(self):
        out = classify(fixture('case1', [sample('unbound.dnssec_probe', 'PASS')]))
        self.assertEqual(out['observed_conditions'], [])

    def test_tailscale_unavailable_not_outage(self):
        out = classify(fixture('case1', [sample('tailscale.peer_probe', 'UNAVAILABLE')]))
        self.assertNotIn('TAILSCALE_PEER_PROBE_UNREACHABLE_SAMPLED', out['observed_conditions'])
        self.assertEqual(out['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(out['coverage']['unavailable'], 1)

    def test_fedora_unknown_not_outage(self):
        out = classify(fixture('case1', [sample('fedora.collector_state', 'UNKNOWN')]))
        self.assertNotIn('FEDORA_COLLECTOR_STOPPED_SAMPLED', out['observed_conditions'])
        self.assertEqual(out['status'], 'INSUFFICIENT_EVIDENCE')

    def test_missing_not_outage(self):
        out = classify(fixture('case1', [], ['tailscale.peer_probe']))
        self.assertEqual(out['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(out['data_gaps'], [{'key': 'tailscale.peer_probe', 'reason': 'MISSING'}])

    def test_stale_not_incident(self):
        out = classify(fixture('case1', [sample('unbound.dnssec_probe', 'FAIL', 301)]))
        self.assertEqual(out['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(out['observed_conditions'], [])

    def test_exact_fresh_boundary(self):
        out = classify(fixture('case1', [sample('unbound.dnssec_probe', 'FAIL', 300)]))
        self.assertEqual(out['status'], 'SAMPLED_CONDITIONS_ONLY')

    def test_partial_observation(self):
        out = classify(fixture('case1', [sample('unbound.dnssec_probe', 'FAIL')],
                               ['tailscale.peer_probe','unbound.dnssec_probe']))
        self.assertEqual(out['status'], 'PARTIAL_OBSERVATION')
        self.assertEqual(out['coverage'], {'expected':2,'fresh':1,'stale':0,'missing':1,'unavailable':0})

    def test_two_independent_observations_do_not_cause_each_other(self):
        out = classify(fixture('case1', [sample('unbound.dnssec_probe', 'FAIL'),
                                       sample('tailscale.peer_probe', 'UNREACHABLE')]))
        self.assertEqual(len(out['observed_conditions']), 2)
        self.assertIn('NO_CAUSALITY_OR_ROOT_CAUSE', out['limits'])

    def test_all_coverage_count_matches(self):
        for scenario in matrix():
            out = classify(scenario)
            c = out['coverage']
            self.assertEqual(c['expected'], c['fresh'] + c['missing'] + c['stale'] + c['unavailable'])

    def test_repeatable_canonical_output(self):
        case = matrix()[0]
        self.assertEqual(canonical(classify(case)), canonical(classify(case)))

    def test_sorted_input_order_invariance(self):
        a = fixture('case1', [sample('unbound.dnssec_probe', 'FAIL'),
                              sample('dns_guard.mode', 'BOOTSTRAP')])
        b = fixture('case1', list(reversed(a['signals'])))
        self.assertEqual(canonical(classify(a)), canonical(classify(b)))

    def test_output_fields_exact(self):
        self.assertEqual(classify(self.base()).keys(), OUT_KEYS)

    def test_no_actions_in_output(self):
        for case in matrix():
            data = canonical(classify(case)).decode('ascii')
            self.assertNotIn('subprocess', data)
            self.assertNotIn('shell_command', data)
            self.assertIn('"model_action_authority":"NONE"', data)
            self.assertIn('"deployment_gate":"HOLD"', data)

    def test_output_uses_synthetic_origin(self):
        for case in matrix():
            self.assertEqual(classify(case)['origin'], ORIGIN)

    def test_no_network_during_all_fixtures(self):
        import socket
        with patch.object(socket, 'socket', side_effect=AssertionError('NETWORK_FORBIDDEN')):
            for case in matrix():
                classify(case)

    def test_not_a_time_duration_claim(self):
        for case in matrix():
            self.assertIn('SINGLE_SAMPLE_NOT_INCIDENT_DURATION', classify(case)['limits'])

    def test_nonfinite_json_rejected_in_canonical(self):
        with self.assertRaises(ValueError):
            canonical({'x': float('inf')})

    def test_all_sources_covered(self):
        observed = {key for case in matrix() for key in case['expected_keys']}
        self.assertEqual(observed, set(ALLOWED))


def run_tests() -> bool:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests)
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    print('V021C61_SELFTESTS=%s/%s' % (count - len(result.failures) - len(result.errors), count))
    print('V021C61_NETWORK_DURING_SELFTEST=NO')
    print('V021C61_VM_LOKI_OLLAMA_CONTACTED=NO')
    print('V021C61_ASUS_HCC_EXECUTOR_PODMAN_CONTACTED=NO')
    print('V021C61_FIXTURE_ORIGIN='+ORIGIN)
    print('FILES_WRITTEN=NO')
    print('DEPLOYMENT_GATE=HOLD')
    print('V021C61_SELFTEST_RESULT='+('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_NOT_APPROVED'))
    return result.wasSuccessful()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--self-test', action='store_true')
    mode.add_argument('--fixture-matrix', action='store_true')
    args = ap.parse_args()
    if not run_tests():
        print('V021C61_RESULT=HOLD_NOT_APPROVED')
        return 1
    if args.self_test:
        print('V021C61_RESULT=PASS_OFFLINE_CONTRACT_ONLY')
        return 0
    print('=== V0.21C.61 / SYNTHETIC MULTI-INCIDENT HOST FIXTURE MATRIX ===')
    for case in matrix():
        out = classify(case)
        raw = canonical(out)
        print('SCENARIO=%s STATUS=%s COVERAGE=%s/%s OBSERVED=%s GAPS=%s SHA256=%s' % (
            out['scenario_id'], out['status'], out['coverage']['fresh'],
            out['coverage']['expected'], ','.join(out['observed_conditions']) or 'NONE',
            ','.join(x['reason'] + ':' + x['key'] for x in out['data_gaps']) or 'NONE',
            hashlib.sha256(raw).hexdigest()))
    print('INCIDENT_DETECTION_FROM_REAL_SOURCES=NOT_TESTED')
    print('SOURCE_ATTESTATION=NOT_PROVEN')
    print('CAUSALITY_DNS_HEALTH_HOST_POWER_STATE=NOT_PROVEN')
    print('MODEL_ACTION_AUTHORITY=NONE')
    print('DEPLOYMENT_GATE=HOLD')
    print('V021C61_RESULT=PASS_SYNTHETIC_MULTI_INCIDENT_HOST_FIXTURES_ONLY')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
