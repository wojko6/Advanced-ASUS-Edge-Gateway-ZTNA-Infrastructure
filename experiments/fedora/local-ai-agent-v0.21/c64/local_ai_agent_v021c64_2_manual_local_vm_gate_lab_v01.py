#!/usr/bin/env python3
"""C.64.2: operator-gated, bounded local VM observation (NO MODEL AUTHORITY).

Offline self-tests/fixtures are the default workflows. A LIVE loopback GET is
possible only with the exact --local-vm-readonly option and two explicit
operator acknowledgment flags. Merely importing this file makes no requests.

No sudo, subprocess, files written, router access, Ollama, model, repairs or
service changes. Even a successful observation is NOT DNS health evidence.
Live mode is a draft review candidate and remains DEPLOYMENT_GATE=HOLD.
"""
from __future__ import annotations

import argparse
import http.client
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
C63 = Path(__file__).resolve().parent.parent / 'c63'
sys.path.insert(0, str(C63))
import local_ai_agent_v021c63_8_1_vm_stats_envelope_hotfix_lab_v01 as vm

SCHEMA = 'local-ai-agent.v0.21.c64.2.manual-vm-unattested-observation.v1'
FIXED_EPOCH = 1897200000  # fictional 2030 fixture only for tests
MAX_RUN_SECONDS = 24
MAX_CLOCK_DRIFT_SECONDS = 5
MAX_OUTPUT_BYTES = 3600
SCENARIOS = ('baseline', 'missing_local', 'stale_local', 'future_local',
             'stale_collection', 'invalid_guard', 'contradictory_flags')
NAMES = tuple(vm.METRICS)


class Hold(Exception):
    """Coded fail-closed output; no raw responses in errors."""


def synthetic_getter(case, *, now=FIXED_EPOCH):
    """A fixed test-only getter; no network and no host data access."""
    if type(case) is not str or case not in SCENARIOS or now != FIXED_EPOCH:
        raise Hold('TEST_FIXTURE_NOT_ALLOWED')
    values, samples, _ = vm.fixture(now)
    if case == 'missing_local':
        values['local'] = None
        samples['local'] = None
    elif case == 'stale_local':
        samples['local'] = type(samples['local'])(now - vm.TTL_RAW - 1)
    elif case == 'future_local':
        samples['local'] = type(samples['local'])(now + vm.FUTURE_SECONDS + 1)
    elif case == 'stale_collection':
        values['collection'] = now - vm.TTL_COLLECTION - 1
    elif case == 'invalid_guard':
        values['valid'] = 0
    elif case == 'contradictory_flags':
        values['bootstrap'] = 1

    def get(name, kind, at):
        if at != now or kind not in ('value', 'sample_time'):
            raise Hold('TEST_QUERY_INVALID')
        match = [key for key, metric in NAMES if metric == name]
        if len(match) != 1:
            raise Hold('TEST_QUERY_INVALID')
        key = match[0]
        val = values[key] if kind == 'value' else samples[key]
        return vm.vector(name, kind, now, val)
    return get


def assess_once(getter, wall_clock, monotonic_clock):
    """Eight strictly validated, non-atomic observations; identity UNVERIFIED.

    The caller-supplied transport is only used from an explicit CLI live gate
    or synthetic tests. It is NOT a sandbox, and any caller of Python methods
    bypasses CLI prompts. Operator review must precede live execution.
    """
    if not callable(getter) or not callable(wall_clock) or not callable(monotonic_clock):
        raise Hold('DEPENDENCY_INVALID')
    try:
        wall_before = wall_clock()
        mono_before = monotonic_clock()
        if type(wall_before) is not int:
            raise Hold('WALL_CLOCK_TYPE_INVALID')
        vm.now_clock(wall_before)
        if type(mono_before) not in (int, float) or not 0 <= mono_before < 1e15:
            raise Hold('MONOTONIC_CLOCK_INVALID')
        vals, samples = {}, {}
        for short, name in NAMES:
            for kind in ('value', 'sample_time'):
                blob = getter(name, kind, wall_before)
                sample = vm.parse(name, kind, blob, wall_before)
                if kind == 'value':
                    vals[short] = sample
                else:
                    samples[short] = sample
        mono_after = monotonic_clock()
        wall_after = wall_clock()
        if type(wall_after) is not int or type(mono_after) not in (int, float):
            raise Hold('FINISH_CLOCK_TYPE_INVALID')
        vm.now_clock(wall_after)
        elapsed = mono_after - mono_before
        wall_elapsed = wall_after - wall_before
        if not 0 <= elapsed <= MAX_RUN_SECONDS or not 0 <= wall_elapsed <= MAX_RUN_SECONDS:
            raise Hold('RUN_DURATION_OR_CLOCK_JUMP_INVALID')
        if abs(wall_elapsed - elapsed) > MAX_CLOCK_DRIFT_SECONDS:
            raise Hold('CLOCK_DIVERGENCE_INVALID')
        report = vm.assess(vals, samples, wall_before)
    except (vm.Hold, OSError, TimeoutError, http.client.HTTPException,
            ValueError, TypeError) as exc:
        raise Hold('LOCAL_VM_READ_OR_SAMPLE_REJECTED') from exc
    if not (report['schema'] == vm.SCHEMA
            and report['quality_gate_decision'] == 'ABSTAIN_NO_MODEL_INFERENCE'
            and report['root_cause'] == 'UNDETERMINED'
            and report['dns_health'] == 'NOT_ESTABLISHED'
            and report['model_requests'] == 0
            and report['model_action_authority'] == 'NONE'
            and report['remediation_authorized'] is False
            and report['deployment_gate'] == 'HOLD'):
        raise Hold('ASSESSMENT_ESCALATION')
    result = {
        'schema': SCHEMA,
        'mode': 'BOUNDED_READ_ONLY_OBSERVATION_UNATTESTED',
        'source_identity': 'CLAIMED_LOCAL_VM_127_0_0_1_8428_NOT_ATTESTED',
        'source_authenticity': 'NOT_CRYPTOGRAPHICALLY_ATTESTED',
        'source_owner_verified_by_this_program': False,
        'sample_atomicity': 'EIGHT_SEPARATE_GETS_NOT_ATOMIC',
        'evaluation_epoch_utc': wall_before,
        'duration_seconds': round(elapsed, 3),
        'clock_divergence_seconds': round(abs(wall_elapsed-elapsed), 3),
        'queries': 8,
        'classification': report['classification'],
        'sampled_mode_claim': report['sampled_mode'],
        'gaps': report['gaps'],
        'source_freshness_proven': False,
        'dns_health': 'NOT_ESTABLISHED',
        'root_cause': 'UNDETERMINED',
        'quality_gate_decision': 'ABSTAIN_NO_MODEL_INFERENCE',
        'model_requests': 0,
        'model_invoked': False,
        'model_action_authority': 'NONE',
        'remediation_authorized': False,
        'deployment_gate': 'HOLD',
        'next_step': 'MANUAL_REVIEW_ONLY',
    }
    if len(json.dumps(result, sort_keys=True, separators=(',', ':')).encode('ascii')) > MAX_OUTPUT_BYTES:
        raise Hold('OUTPUT_BOUNDARY_EXCEEDED')
    return result


def offline_scenario(name='baseline'):
    times = iter((FIXED_EPOCH, FIXED_EPOCH))
    monotonic = iter((100.0, 100.0))
    result = assess_once(synthetic_getter(name), lambda: next(times),
                         lambda: next(monotonic))
    result['mode'] = 'SYNTHETIC_OFFLINE_NO_NETWORK'
    result['source_identity'] = 'FICTIONAL_VM_IN_MEMORY_NOT_A_LIVE_SOURCE'
    return result


class Tests(unittest.TestCase):
    def holds(self, fn, expected):
        with self.assertRaisesRegex(Hold, '^' + expected + '$'):
            fn()

    def test_01_baseline(self):
        self.assertEqual(offline_scenario()['classification'], 'DNS_GUARD_MODE_SAMPLED_ONLY')

    def test_02_baseline_mode(self):
        self.assertEqual(offline_scenario()['sampled_mode_claim'], 'LOCAL')

    def test_03_eight_samples(self):
        self.assertEqual(offline_scenario()['queries'], 8)

    def test_04_offline_identity(self):
        self.assertEqual(offline_scenario()['source_identity'],
                         'FICTIONAL_VM_IN_MEMORY_NOT_A_LIVE_SOURCE')

    def test_05_unverified_by_default(self):
        self.assertIs(offline_scenario()['source_owner_verified_by_this_program'], False)

    def test_06_not_atomic(self):
        self.assertEqual(offline_scenario()['sample_atomicity'],
                         'EIGHT_SEPARATE_GETS_NOT_ATOMIC')

    def test_07_missing(self):
        self.assertEqual(offline_scenario('missing_local')['classification'],
                         'INSUFFICIENT_EVIDENCE')

    def test_08_stale(self):
        self.assertIn('LOCAL_RAW_SAMPLE_STALE', offline_scenario('stale_local')['gaps'])

    def test_09_future(self):
        self.assertIn('LOCAL_RAW_SAMPLE_IN_FUTURE', offline_scenario('future_local')['gaps'])

    def test_10_stale_collector(self):
        self.assertIn('COLLECTION_VALUE_STALE', offline_scenario('stale_collection')['gaps'])

    def test_11_invalid_state(self):
        self.assertEqual(offline_scenario('invalid_guard')['classification'],
                         'INVALID_DNS_GUARD_STATE_SAMPLED')

    def test_12_mode_contradiction(self):
        self.assertIn('MODE_FLAGS_CONTRADICTORY',
                      offline_scenario('contradictory_flags')['gaps'])

    def test_13_all_abstain(self):
        self.assertTrue(all(offline_scenario(c)['quality_gate_decision']
                            == 'ABSTAIN_NO_MODEL_INFERENCE' for c in SCENARIOS))

    def test_14_all_hold(self):
        self.assertTrue(all(offline_scenario(c)['deployment_gate'] == 'HOLD'
                            for c in SCENARIOS))

    def test_15_no_model(self):
        self.assertTrue(all(offline_scenario(c)['model_requests'] == 0
                            for c in SCENARIOS))

    def test_16_no_remediation(self):
        self.assertTrue(all(offline_scenario(c)['remediation_authorized'] is False
                            for c in SCENARIOS))

    def test_17_no_dns_health(self):
        self.assertTrue(all(offline_scenario(c)['dns_health'] == 'NOT_ESTABLISHED'
                            for c in SCENARIOS))

    def test_18_no_root_cause(self):
        self.assertTrue(all(offline_scenario(c)['root_cause'] == 'UNDETERMINED'
                            for c in SCENARIOS))

    def test_19_wrong_scenario(self):
        self.holds(lambda: offline_scenario('real'), 'TEST_FIXTURE_NOT_ALLOWED')

    def test_20_default_requires_mutual_exclusion(self):
        with self.assertRaises(SystemExit):
            main([])

    def test_21_live_without_ack_refused(self):
        self.assertEqual(main(['--local-vm-readonly']), 2)

    def test_22_live_with_only_one_ack_refused(self):
        self.assertEqual(main(['--local-vm-readonly', '--ack-operator-read-only']), 2)

    def test_23_ack_not_accepted_in_offline_mode(self):
        self.assertEqual(main(['--summary-json', '--ack-operator-read-only']), 2)

    def test_24_no_network_in_offline(self):
        with patch.object(vm, 'fetch', side_effect=AssertionError('LIVE_FETCH')):
            with patch('socket.create_connection', side_effect=AssertionError('NETWORK')):
                for c in SCENARIOS:
                    self.assertEqual(offline_scenario(c)['model_requests'], 0)

    def test_25_no_shell_in_offline(self):
        with patch('subprocess.Popen', side_effect=AssertionError('SHELL')):
            self.assertEqual(offline_scenario()['model_requests'], 0)

    def test_26_normal_short_run(self):
        result = assess_once(synthetic_getter('baseline'),
                             iter((FIXED_EPOCH,FIXED_EPOCH+1)).__next__,
                             iter((1.0,2.0)).__next__)
        self.assertEqual(result['duration_seconds'], 1)

    def test_27_reverse_clock_rejected(self):
        self.holds(lambda: assess_once(synthetic_getter('baseline'),
                   iter((FIXED_EPOCH,FIXED_EPOCH-1)).__next__,
                   iter((1.0,2.0)).__next__),
                   'RUN_DURATION_OR_CLOCK_JUMP_INVALID')

    def test_28_long_run_rejected(self):
        self.holds(lambda: assess_once(synthetic_getter('baseline'),
                   iter((FIXED_EPOCH,FIXED_EPOCH+25)).__next__,
                   iter((1.0,26.0)).__next__),
                   'RUN_DURATION_OR_CLOCK_JUMP_INVALID')

    def test_29_clock_divergence_rejected(self):
        self.holds(lambda: assess_once(synthetic_getter('baseline'),
                   iter((FIXED_EPOCH,FIXED_EPOCH+20)).__next__,
                   iter((1.0,2.0)).__next__),
                   'CLOCK_DIVERGENCE_INVALID')

    def test_30_boolean_clock_rejected(self):
        self.holds(lambda: assess_once(synthetic_getter('baseline'),
                   iter((True,FIXED_EPOCH)).__next__,
                   iter((1.0,2.0)).__next__),
                   'WALL_CLOCK_TYPE_INVALID')

    def test_31_missing_metric_response_rejected(self):
        self.holds(lambda: assess_once(lambda *_: b'', 
                   iter((FIXED_EPOCH,FIXED_EPOCH)).__next__,
                   iter((1.0,2.0)).__next__),
                   'LOCAL_VM_READ_OR_SAMPLE_REJECTED')

    def test_32_nonfinite_response_rejected(self):
        self.holds(lambda: assess_once(lambda *_: b'{"status":NaN}',
                   iter((FIXED_EPOCH,FIXED_EPOCH)).__next__,
                   iter((1.0,2.0)).__next__),
                   'LOCAL_VM_READ_OR_SAMPLE_REJECTED')

    def test_33_exception_redacted(self):
        def bad_get(*_):
            raise ConnectionRefusedError('internal-private-token')
        self.holds(lambda: assess_once(bad_get,
                   iter((FIXED_EPOCH,FIXED_EPOCH)).__next__,
                   iter((1.0,2.0)).__next__),
                   'LOCAL_VM_READ_OR_SAMPLE_REJECTED')

    def test_34_direct_assessor_does_not_know_source(self):
        result = assess_once(synthetic_getter('baseline'),
                             iter((FIXED_EPOCH,FIXED_EPOCH)).__next__,
                             iter((1.0,1.0)).__next__)
        self.assertEqual(result['source_identity'],
                         'CLAIMED_LOCAL_VM_127_0_0_1_8428_NOT_ATTESTED')

    def test_35_whitelist_only_summary(self):
        txt = json.dumps(offline_scenario(), sort_keys=True)
        for forbidden in ('password', '192.168.', 'ssh_authorized_keys', 'PRIVATE KEY'):
            self.assertNotIn(forbidden, txt)

    def test_36_bounded_summary(self):
        self.assertLess(len(json.dumps(offline_scenario()).encode('ascii')),
                        MAX_OUTPUT_BYTES)

    def test_37_reproducible(self):
        self.assertEqual(offline_scenario(), offline_scenario())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--self-test', action='store_true')
    group.add_argument('--fixture-matrix', action='store_true')
    group.add_argument('--summary-json', action='store_true')
    group.add_argument('--local-vm-readonly', action='store_true',
                       help='EXPLICIT operator-only live loopback query; not production-authorized')
    parser.add_argument('--scenario', choices=SCENARIOS, default='baseline')
    parser.add_argument('--ack-operator-read-only', action='store_true')
    parser.add_argument('--ack-unverified-source', action='store_true')
    args = parser.parse_args(argv)
    if args.self_test:
        out = unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        print(f'C642_TESTS={out.testsRun} STATUS=' +
              ('PASS_OFFLINE' if out.wasSuccessful() else 'HOLD_TEST_FAILURE'))
        return 0 if out.wasSuccessful() else 1
    if args.local_vm_readonly:
        if (not args.ack_operator_read_only or not args.ack_unverified_source
                or args.scenario != 'baseline'):
            print('C642_RESULT=HOLD_EXPLICIT_OPERATOR_ACK_REQUIRED', file=sys.stderr)
            return 2
        try:
            # This is the ONLY CLI path permitted to invoke actual VM GETs.
            # The source remains unverified and no model/executor is reachable.
            report = assess_once(vm.fetch, lambda: int(time.time()), time.monotonic)
        except Hold as exc:
            print('C642_RESULT=HOLD_' + str(exc), file=sys.stderr)
            return 2
        except Exception:
            print('C642_RESULT=HOLD_UNEXPECTED_FAILURE', file=sys.stderr)
            return 2
    else:
        if args.ack_operator_read_only or args.ack_unverified_source:
            print('C642_RESULT=HOLD_ACK_ONLY_ALLOWED_FOR_LIVE_MODE', file=sys.stderr)
            return 2
        if args.fixture_matrix:
            for scenario in SCENARIOS:
                report = offline_scenario(scenario)
                print('SCENARIO=' + scenario + ' CLASSIFICATION=' +
                      report['classification'] + ' MODEL_REQUESTS=' +
                      str(report['model_requests']))
            print('C642_RESULT=PASS_OFFLINE_MATRIX')
            return 0
        report = offline_scenario(args.scenario)
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
