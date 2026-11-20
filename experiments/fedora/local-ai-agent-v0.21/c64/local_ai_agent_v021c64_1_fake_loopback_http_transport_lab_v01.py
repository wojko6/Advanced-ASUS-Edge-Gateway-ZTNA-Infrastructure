#!/usr/bin/env python3
"""C.64.1: OFFLINE simulation of eight bounded local VictoriaMetrics HTTP GETs.

Only an in-memory fake HTTP connection factory is passed to the existing
C.63.8.1 fetch/parse/assess code. This entrypoint has NO live mode, no URL
input, no host clock, no network, no model and no production mutations.
The fictional evaluation clock is fixed to February 2030.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
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

SCHEMA = 'local-ai-agent.v0.21.c64.1.synthetic-http-loopback-transport.v1'
FIXED_EPOCH = int(datetime(2030, 2, 13, 9, 0,
                           tzinfo=timezone(timedelta(hours=1))).timestamp())
MAX_FAKE_CLOCK_SPAN_SECONDS = 24
MAX_SUMMARY_BYTES = 3600
PLAN = tuple((name, kind) for _, name in vm.METRICS
             for kind in ('value', 'sample_time'))
SCENARIOS = (
    'baseline', 'stats', 'missing_local', 'stale_local',
    'future_local', 'stale_collection', 'contradictory_flags', 'invalid_guard',
)
FAULTS = (
    None, 'http_503', 'http_redirect', 'timeout', 'refused',
    'oversized', 'empty', 'bad_json', 'duplicate_json_key',
    'foreign_label', 'nonfinite', 'partial_response', 'evaluation_skew',
)


class Hold(Exception):
    """Always expose only a fixed, non-sensitive hold reason."""


class FakeClock:
    """Operator-clock surrogate: no time.time(), monotonic() or host reads."""

    def __init__(self, readings=(FIXED_EPOCH, FIXED_EPOCH)):
        self._readings = tuple(readings)
        self._idx = 0

    def read(self):
        if self._idx >= len(self._readings):
            raise Hold('FAKE_CLOCK_READ_EXHAUSTED')
        value = self._readings[self._idx]
        self._idx += 1
        if type(value) is not int:
            raise Hold('FAKE_CLOCK_TYPE_INVALID')
        try:
            vm.now_clock(value)
        except vm.Hold as exc:
            raise Hold('FAKE_CLOCK_OUT_OF_RANGE') from exc
        return value


def envelopes(now, scenario='baseline'):
    """Generate exactly eight in-memory VM-shaped responses, no I/O."""
    if type(scenario) is not str or scenario not in SCENARIOS:
        raise Hold('SCENARIO_NOT_WHITELISTED')
    try:
        vm.now_clock(now)
    except vm.Hold as exc:
        raise Hold('EPOCH_INVALID') from exc
    values, times, _ = vm.fixture(now)
    if scenario == 'missing_local':
        values['local'], times['local'] = None, None
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
    for short, name in vm.METRICS:
        for kind in ('value', 'sample_time'):
            v = values[short] if kind == 'value' else times[short]
            data = vm.vector(name, kind, now, v)
            if scenario == 'stats':
                obj = json.loads(data)
                obj['stats'] = {'executionTimeMsec': 1, 'seriesFetched': '1'}
                data = json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('ascii')
            packets[(name, kind)] = data
    if set(packets) != set(PLAN) or len(packets) != 8:
        raise Hold('FIXTURE_PLAN_INVALID')
    return packets


class FakeResponse:
    """Single in-memory HTTP response; records the read cap."""
    def __init__(self, status, data, factory):
        self.status = status
        self._data = data
        self._factory = factory

    def read(self, count):
        if count != vm.MAX_RESPONSE_BYTES + 1:
            raise Hold('READ_CAP_INVALID')
        self._factory.read_limits.append(count)
        return self._data[:count]


class FakeConnection:
    def __init__(self, factory, position):
        self._factory = factory
        self._position = position
        self._requested = False
        self._closed = False

    def request(self, method, path, headers=None):
        if self._requested or self._closed:
            raise Hold('HTTP_REQUEST_SEQUENCE_INVALID')
        key = PLAN[self._position]
        expected = vm.make_path(key[0], key[1], self._factory.now)
        if (method != 'GET' or path != expected
                or headers != {'Accept': 'application/json', 'Connection': 'close'}):
            raise Hold('HTTP_QUERY_POLICY_VIOLATION')
        self._requested = True
        self._factory.calls.append((method, path, dict(headers)))
        if self._factory.fault_at == self._position and self._factory.fault == 'timeout':
            raise TimeoutError('simulated timeout')

    def getresponse(self):
        if not self._requested or self._closed:
            raise Hold('HTTP_RESPONSE_SEQUENCE_INVALID')
        key = PLAN[self._position]
        data = self._factory.packets[key]
        status = 200
        if self._factory.fault_at == self._position:
            fault = self._factory.fault
            if fault == 'http_503':
                status = 503
            elif fault == 'http_redirect':
                status = 302
            elif fault == 'oversized':
                data = b'x' * (vm.MAX_RESPONSE_BYTES + 1)
            elif fault == 'empty':
                data = b''
            elif fault == 'bad_json':
                data = b'{"status":'
            elif fault == 'duplicate_json_key':
                data = b'{"status":"success","status":"success"}'
            elif fault == 'foreign_label':
                obj = json.loads(data)
                obj['data']['result'][0]['metric']['private_label'] = 'fictional'
                data = json.dumps(obj).encode('ascii')
            elif fault == 'nonfinite':
                obj = json.loads(data)
                obj['stats'] = {'executionTimeMsec': float('nan'), 'seriesFetched': '1'}
                data = json.dumps(obj).encode('ascii')
            elif fault == 'partial_response':
                obj = json.loads(data)
                obj['isPartial'] = True
                data = json.dumps(obj).encode('ascii')
            elif fault == 'evaluation_skew':
                name, kind = key
                data = vm.vector(name, kind, self._factory.now,
                                 1, eval_at=self._factory.now - vm.EVAL_TOLERANCE - 1)
        return FakeResponse(status, data, self._factory)

    def close(self):
        if not self._closed:
            self._closed = True
            self._factory.closed += 1


class SyntheticConnectionFactory:
    """Strict fake constructor passed explicitly to vm.fetch.

    It is not a real HTTP transport. It never calls HTTPConnection, socket
    APIs or a host runtime; all bytes come from envelopes() in RAM.
    """
    def __init__(self, scenario='baseline', *, now=FIXED_EPOCH,
                 fault=None, fault_at=0):
        if fault not in FAULTS or type(fault_at) is not int or not 0 <= fault_at < 8:
            raise Hold('FAULT_CONFIGURATION_INVALID')
        self.now = now
        self.packets = envelopes(now, scenario)
        self.fault, self.fault_at = fault, fault_at
        self.opened = 0
        self.closed = 0
        self.calls = []
        self.targets = []
        self.read_limits = []

    def __call__(self, host, port, *, timeout):
        if (host != vm.HOST or host != '127.0.0.1'
                or port != vm.PORT or port != 8428
                or timeout != vm.TIMEOUT_SECONDS or timeout != 3):
            raise Hold('LOOPBACK_TRANSPORT_POLICY_VIOLATION')
        if self.opened >= len(PLAN):
            raise Hold('EXCESS_HTTP_CONNECTIONS')
        position = self.opened
        self.opened += 1
        self.targets.append((host, port, timeout))
        if position == self.fault_at and self.fault == 'refused':
            raise ConnectionRefusedError('simulated refusal')
        return FakeConnection(self, position)


def inspect_transport(factory, clock):
    """Offline transport exercise. Never create an actual connection.

    Caller-provided factories are rejected by exact class type. This is a
    lab test guard, NOT a sandbox/security guarantee against malicious Python.
    """
    if type(factory) is not SyntheticConnectionFactory or type(clock) is not FakeClock:
        raise Hold('NON_SYNTHETIC_DEPENDENCY_REFUSED')
    now = clock.read()
    if factory.now != now:
        raise Hold('FAKE_CLOCK_AND_FIXTURE_MISMATCH')
    values, raw_times = {}, {}
    try:
        for short, name in vm.METRICS:
            for kind in ('value', 'sample_time'):
                blob = vm.fetch(name, kind, now, factory=factory)
                parsed = vm.parse(name, kind, blob, now)
                if kind == 'value':
                    values[short] = parsed
                else:
                    raw_times[short] = parsed
        after = clock.read()
        if after < now or after - now > MAX_FAKE_CLOCK_SPAN_SECONDS:
            raise Hold('FAKE_CLOCK_SPAN_REJECTED')
        if (factory.opened != 8 or factory.closed != 8
                or len(factory.calls) != 8
                or len(factory.read_limits) != 8):
            raise Hold('HTTP_PLAN_NOT_FULLY_OBSERVED')
        report = vm.assess(values, raw_times, now)
    except (vm.Hold, OSError, TimeoutError) as exc:
        raise Hold('VM_RESPONSE_OR_TRANSPORT_REJECTED') from exc
    if (report['schema'] != vm.SCHEMA
            or report['quality_gate_decision'] != 'ABSTAIN_NO_MODEL_INFERENCE'
            or report['dns_health'] != 'NOT_ESTABLISHED'
            or report['root_cause'] != 'UNDETERMINED'
            or report['model_requests'] != 0
            or report['model_action_authority'] != 'NONE'
            or report['remediation_authorized'] is not False
            or report['deployment_gate'] != 'HOLD'):
        raise Hold('SOURCE_ASSESSMENT_ESCALATION')
    result = {
        'schema': SCHEMA,
        'mode': 'IN_MEMORY_SIMULATED_HTTP_ONLY',
        'source_identity': 'FICTIONAL_HTTP_LOOPBACK_SIMULATOR_NOT_REAL_VM',
        'source_authenticity': 'NOT_CRYPTOGRAPHICALLY_ATTESTED',
        'transport_fidelity': 'IN_MEMORY_TEST_DOUBLE_NOT_ACTUAL_NETWORK',
        'clock_basis': 'FAKE_INJECTED_CLOCK',
        'evaluation_epoch_utc': now,
        'simulated_clock_span_seconds': after - now,
        'http_method': 'GET',
        'simulated_target': '127.0.0.1:8428',
        'expected_queries': len(PLAN),
        'performed_fake_queries': len(factory.calls),
        'simulated_read_limit_bytes': vm.MAX_RESPONSE_BYTES + 1,
        'non_atomic_samples': True,
        'observed_mode_claim': report['sampled_mode'],
        'classification': report['classification'],
        'gaps': report['gaps'],
        'dns_health': 'NOT_ESTABLISHED',
        'root_cause': 'UNDETERMINED',
        'quality_gate_decision': 'ABSTAIN_NO_MODEL_INFERENCE',
        'model_requests': 0,
        'model_invoked': False,
        'model_action_authority': 'NONE',
        'remediation_authorized': False,
        'operator_authorized_live_reads': False,
        'real_network_requests': 0,
        'deployment_gate': 'HOLD',
    }
    if len(json.dumps(result, sort_keys=True, separators=(',', ':')).encode('ascii')) > MAX_SUMMARY_BYTES:
        raise Hold('SUMMARY_TOO_LARGE')
    return result


def scenario_report(name='baseline'):
    return inspect_transport(SyntheticConnectionFactory(name), FakeClock())


class Tests(unittest.TestCase):
    def hold(self, fn, code):
        with self.assertRaisesRegex(Hold, '^' + re.escape(code) + '$'):
            fn()

    def test_01_baseline_gets_eight(self):
        self.assertEqual(scenario_report()['performed_fake_queries'], 8)

    def test_02_baseline_only_local_mode_claim(self):
        self.assertEqual(scenario_report()['observed_mode_claim'], 'LOCAL')

    def test_03_baseline_classification(self):
        self.assertEqual(scenario_report()['classification'], 'DNS_GUARD_MODE_SAMPLED_ONLY')

    def test_04_exact_plan(self):
        f = SyntheticConnectionFactory()
        inspect_transport(f, FakeClock())
        self.assertEqual([x[1] for x in f.calls],
                         [vm.make_path(name, kind, FIXED_EPOCH) for name, kind in PLAN])

    def test_05_fixed_get(self):
        f = SyntheticConnectionFactory()
        inspect_transport(f, FakeClock())
        self.assertTrue(all(c[0] == 'GET' for c in f.calls))

    def test_06_fixed_headers(self):
        f = SyntheticConnectionFactory()
        inspect_transport(f, FakeClock())
        self.assertEqual({tuple(sorted(x[2].items())) for x in f.calls},
                         {tuple(sorted({'Accept': 'application/json', 'Connection': 'close'}.items()))})

    def test_07_exact_loopback_target(self):
        f = SyntheticConnectionFactory()
        inspect_transport(f, FakeClock())
        self.assertEqual(f.targets, [('127.0.0.1', 8428, 3)] * 8)

    def test_08_all_connections_closed(self):
        f = SyntheticConnectionFactory()
        inspect_transport(f, FakeClock())
        self.assertEqual((f.opened, f.closed), (8, 8))

    def test_09_read_length_bounded(self):
        f = SyntheticConnectionFactory()
        inspect_transport(f, FakeClock())
        self.assertEqual(f.read_limits, [8193] * 8)

    def test_10_stats_envelope(self):
        self.assertEqual(scenario_report('stats')['observed_mode_claim'], 'LOCAL')

    def test_11_missing_sample(self):
        self.assertEqual(scenario_report('missing_local')['classification'], 'INSUFFICIENT_EVIDENCE')

    def test_12_stale_sample(self):
        self.assertIn('LOCAL_RAW_SAMPLE_STALE', scenario_report('stale_local')['gaps'])

    def test_13_future_sample(self):
        self.assertIn('LOCAL_RAW_SAMPLE_IN_FUTURE', scenario_report('future_local')['gaps'])

    def test_14_stale_collection(self):
        self.assertIn('COLLECTION_VALUE_STALE', scenario_report('stale_collection')['gaps'])

    def test_15_flags_contradict(self):
        self.assertIn('MODE_FLAGS_CONTRADICTORY', scenario_report('contradictory_flags')['gaps'])

    def test_16_invalid_guard_claim(self):
        self.assertEqual(scenario_report('invalid_guard')['classification'],
                         'INVALID_DNS_GUARD_STATE_SAMPLED')

    def test_17_every_case_abstains(self):
        self.assertTrue(all(scenario_report(s)['quality_gate_decision']
                            == 'ABSTAIN_NO_MODEL_INFERENCE' for s in SCENARIOS))

    def test_18_every_case_has_no_authority(self):
        for name in SCENARIOS:
            result = scenario_report(name)
            self.assertEqual(result['model_action_authority'], 'NONE')
            self.assertEqual(result['deployment_gate'], 'HOLD')
            self.assertEqual(result['model_requests'], 0)
            self.assertIs(result['remediation_authorized'], False)

    def test_19_live_read_never_authorized(self):
        self.assertIs(scenario_report()['operator_authorized_live_reads'], False)

    def test_20_not_actual_host_evidence(self):
        x = scenario_report()
        self.assertEqual(x['real_network_requests'], 0)
        self.assertEqual(x['source_identity'], 'FICTIONAL_HTTP_LOOPBACK_SIMULATOR_NOT_REAL_VM')
        self.assertTrue(x['non_atomic_samples'])

    def test_21_healthy_dns_not_proven(self):
        for name in SCENARIOS:
            x = scenario_report(name)
            self.assertEqual(x['dns_health'], 'NOT_ESTABLISHED')
            self.assertEqual(x['root_cause'], 'UNDETERMINED')

    def test_22_clock_normal_window(self):
        self.assertEqual(inspect_transport(SyntheticConnectionFactory(),
                         FakeClock((FIXED_EPOCH, FIXED_EPOCH + 1)))['simulated_clock_span_seconds'], 1)

    def test_23_clock_negative_span_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(),
                  FakeClock((FIXED_EPOCH, FIXED_EPOCH - 1))), 'FAKE_CLOCK_SPAN_REJECTED')

    def test_24_clock_excess_span_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(),
                  FakeClock((FIXED_EPOCH, FIXED_EPOCH + 25))), 'FAKE_CLOCK_SPAN_REJECTED')

    def test_25_clock_boolean_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(),
                  FakeClock((True, FIXED_EPOCH))), 'FAKE_CLOCK_TYPE_INVALID')

    def test_26_clock_epoch_mismatch(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(),
                  FakeClock((FIXED_EPOCH + 1, FIXED_EPOCH + 1))), 'FAKE_CLOCK_AND_FIXTURE_MISMATCH')

    def test_27_clock_short_sequence(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(),
                  FakeClock((FIXED_EPOCH,))), 'FAKE_CLOCK_READ_EXHAUSTED')

    def test_28_scenario_not_whitelisted(self):
        self.hold(lambda: SyntheticConnectionFactory('live'), 'SCENARIO_NOT_WHITELISTED')

    def test_29_refuse_actual_connection_factory(self):
        self.hold(lambda: inspect_transport(object(), FakeClock()),
                  'NON_SYNTHETIC_DEPENDENCY_REFUSED')

    def test_30_refuse_actual_host_clock(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(), object()),
                  'NON_SYNTHETIC_DEPENDENCY_REFUSED')

    def test_31_http_503_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(
                  fault='http_503'), FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')

    def test_32_redirect_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(
                  fault='http_redirect'), FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')

    def test_33_timeout_rejected_and_closed(self):
        factory = SyntheticConnectionFactory(fault='timeout')
        self.hold(lambda: inspect_transport(factory, FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')
        self.assertEqual((factory.opened, factory.closed), (1, 1))

    def test_34_refusal_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(
                  fault='refused'), FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')

    def test_35_oversize_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(
                  fault='oversized'), FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')

    def test_36_empty_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(
                  fault='empty'), FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')

    def test_37_bad_json_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(
                  fault='bad_json'), FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')

    def test_38_duplicate_key_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(
                  fault='duplicate_json_key'), FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')

    def test_39_foreign_labels_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(
                  fault='foreign_label'), FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')

    def test_40_nonfinite_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(
                  fault='nonfinite'), FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')

    def test_41_partial_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(
                  fault='partial_response'), FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')

    def test_42_eval_skew_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(
                  fault='evaluation_skew'), FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')

    def test_43_late_query_failure_closes(self):
        factory = SyntheticConnectionFactory(fault='http_503', fault_at=7)
        self.hold(lambda: inspect_transport(factory, FakeClock()), 'VM_RESPONSE_OR_TRANSPORT_REJECTED')
        self.assertEqual((factory.opened, factory.closed), (8, 8))

    def test_44_all_cases_no_socket_access(self):
        with patch('socket.socket', side_effect=AssertionError('ACTUAL_NETWORK_FORBIDDEN')):
            with patch('socket.create_connection', side_effect=AssertionError('ACTUAL_NETWORK_FORBIDDEN')):
                for name in SCENARIOS:
                    self.assertEqual(scenario_report(name)['real_network_requests'], 0)

    def test_45_no_default_network_getter(self):
        with patch.object(vm, 'observe', side_effect=AssertionError('DEFAULT_FETCH_FORBIDDEN')):
            for name in SCENARIOS:
                self.assertEqual(scenario_report(name)['model_requests'], 0)

    def test_46_no_shell(self):
        with patch('subprocess.Popen', side_effect=AssertionError('SHELL_FORBIDDEN')):
            self.assertEqual(scenario_report()['model_requests'], 0)

    def test_47_bounded_summary(self):
        self.assertLess(len(json.dumps(scenario_report()).encode('ascii')), MAX_SUMMARY_BYTES)

    def test_48_reproducible(self):
        self.assertEqual(scenario_report(), scenario_report())

    def test_49_fault_type_rejected(self):
        self.hold(lambda: SyntheticConnectionFactory(fault='real_http'),
                  'FAULT_CONFIGURATION_INVALID')

    def test_50_nonfinite_clock_rejected(self):
        self.hold(lambda: inspect_transport(SyntheticConnectionFactory(),
                  FakeClock((float('nan'), FIXED_EPOCH))), 'FAKE_CLOCK_TYPE_INVALID')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--self-test', action='store_true')
    group.add_argument('--fixture-matrix', action='store_true')
    group.add_argument('--summary-json', action='store_true')
    parser.add_argument('--scenario', choices=SCENARIOS, default='baseline')
    args = parser.parse_args(argv)
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        print(f'C641_TESTS={result.testsRun} STATUS=' +
              ('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_TEST_FAILURE'))
        return 0 if result.wasSuccessful() else 1
    try:
        if args.fixture_matrix:
            for name in SCENARIOS:
                x = scenario_report(name)
                print('SCENARIO=' + name + ' CLASSIFICATION=' + x['classification']
                      + ' MODEL_REQUESTS=' + str(x['model_requests']))
            print('C641_RESULT=PASS_IN_MEMORY_TRANSPORT_MATRIX_ONLY')
        else:
            print(json.dumps(scenario_report(args.scenario),
                             ensure_ascii=True, indent=2, sort_keys=True))
    except Hold as exc:
        print('C641_RESULT=HOLD_' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
