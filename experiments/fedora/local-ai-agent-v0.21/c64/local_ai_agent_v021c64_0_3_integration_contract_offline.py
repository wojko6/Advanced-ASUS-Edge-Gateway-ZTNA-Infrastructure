#!/usr/bin/env python3
"""C.64.0–C.64.3 integration contract: synthetic-only, no host access.

This is an additional test harness for the existing stacked Draft PR #359,
NOT a new agent capability, transport or live-data opt-in.

C.64.0 responses and C.64.1 HTTP connections are both fabricated in memory.
C.64.2's process/socket metadata is fabricated in memory through evaluate().
C.64.3 joins those two unrelated simulations while preserving uncertainty.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_ai_agent_v021c64_0_synthetic_vm_envelope_adapter as c640
import local_ai_agent_v021c64_1_mocked_vm_transport_contract as c641
import local_ai_agent_v021c64_2_listener_identity_preflight as c642
import local_ai_agent_v021c64_3_independent_source_operator_gate as c643

SCHEMA = 'local-ai-agent.v0.21.c64.0-3.offline-integration-contract.v1'
EXPECTED_CASES = 11
MAX_SUMMARY_BYTES = 2400


class IntegrationTests(unittest.TestCase):
    def test_01_c640_and_c641_parser_parity(self):
        for case in c640.CASES:
            direct, mock = c640.scenario_summary(case), c641.run_mock(case)
            for key in ('observation_classification', 'sampled_mode', 'gaps',
                        'quality_gate_decision', 'root_cause', 'dns_health',
                        'source_fingerprint_sha256'):
                with self.subTest(case=case, key=key):
                    self.assertEqual(direct[key], mock[key])

    def test_02_identical_fixture_digest_not_attestation(self):
        direct = c640.scenario_summary('baseline')
        mocked = c641.run_mock('baseline')
        self.assertEqual(direct['source_fingerprint_sha256'],
                         mocked['source_fingerprint_sha256'])
        self.assertNotEqual(direct['source_identity'], mocked['source_identity'])
        self.assertFalse(direct['source_fingerprint_is_provenance_attestation'])
        self.assertFalse(mocked['source_fingerprint_is_provenance_attestation'])

    def test_03_c642_producer_schema_matches_gate(self):
        listener, _ = c643.synthetic_pair()
        self.assertEqual(set(listener), c643.LISTENER_FIELDS)
        self.assertEqual(listener['schema'], c642.SCHEMA)

    def test_04_c641_producer_schema_matches_gate(self):
        _, vm = c643.synthetic_pair()
        self.assertEqual(set(vm), c643.VM_FIELDS)
        self.assertEqual(vm['schema'], c641.SCHEMA)

    def test_05_c643_accepts_exact_producer_outputs(self):
        listener, vm = c643.synthetic_pair('fd_denied')
        result = c643.evaluate_inputs(listener, vm)
        self.assertEqual(result['decision'], 'HOLD_FD_ACCESS_DENIED')
        self.assertEqual(result['listener_result'], 'HOLD_LISTENER_FD_ACCESS_DENIED')

    def test_06_fd_denied_remains_hold_with_valid_vm_fixture(self):
        listener, vm = c643.synthetic_pair('fd_denied')
        self.assertEqual(vm['observation_classification'],
                         'DNS_GUARD_MODE_SAMPLED_ONLY')
        self.assertEqual(listener['mainpid_socket_inode_match'],
                         'PERMISSION_DENIED')
        self.assertFalse(c643.evaluate_inputs(listener, vm)['live_http_authorized'])

    def test_07_positive_mock_socket_match_not_authority(self):
        r = c643.scenario_summary('loopback_match')
        self.assertEqual(r['decision'], 'HOLD_SOURCE_NOT_ATTESTED')
        self.assertFalse(r['source_identity_cryptographically_attested'])
        self.assertFalse(r['independent_inputs_prove_same_process'])

    def test_08_all_11_scenarios_are_still_hold(self):
        matrix = c643.matrix()
        self.assertEqual(set(matrix), set(c643.SCENARIOS))
        self.assertEqual(len(matrix), EXPECTED_CASES)
        self.assertTrue(all(x['decision'].startswith('HOLD_')
                            for x in matrix.values()))

    def test_09_all_review_codes_are_non_authorizing(self):
        for case in c643.SCENARIOS:
            listener, vm = c643.synthetic_pair(case)
            for review in c643.REVIEWS:
                with self.subTest(case=case, review=review):
                    out = c643.evaluate_inputs(listener, vm, review)
                    self.assertTrue(out['decision'].startswith('HOLD_'))
                    self.assertFalse(out['live_http_authorized'])
                    self.assertFalse(out['review_code_authenticated'])
                    self.assertFalse(out['review_acknowledgement_grants_access'])

    def test_10_bad_review_is_fail_closed(self):
        listener, vm = c643.synthetic_pair('loopback_match')
        with self.assertRaisesRegex(c643.Hold, '^REVIEW_CODE_NOT_ALLOWED$'):
            c643.evaluate_inputs(listener, vm, 'ENABLE_LIVE')

    def test_11_missing_listener_field_is_rejected(self):
        listener, vm = c643.synthetic_pair()
        del listener['model_requests']
        with self.assertRaisesRegex(c643.Hold, '^LISTENER_SCHEMA_REJECTED$'):
            c643.evaluate_inputs(listener, vm)

    def test_12_missing_vm_field_is_rejected(self):
        listener, vm = c643.synthetic_pair()
        del vm['deployment_gate']
        with self.assertRaisesRegex(c643.Hold, '^VM_SCHEMA_REJECTED$'):
            c643.evaluate_inputs(listener, vm)

    def test_13_false_vm_attestation_is_rejected(self):
        listener, vm = c643.synthetic_pair('loopback_match')
        vm['source_authenticity'] = 'AUTHENTICATED'
        with self.assertRaisesRegex(c643.Hold, '^VM_AUTHORITY_REJECTED$'):
            c643.evaluate_inputs(listener, vm)

    def test_14_false_listener_attestation_is_rejected(self):
        listener, vm = c643.synthetic_pair('loopback_match')
        listener['process_identity_cryptographically_attested'] = True
        with self.assertRaisesRegex(c643.Hold, '^LISTENER_AUTHORITY_REJECTED$'):
            c643.evaluate_inputs(listener, vm)

    def test_15_digest_replacement_does_not_grant_provenance(self):
        listener, vm = c643.synthetic_pair('loopback_match')
        vm['source_fingerprint_sha256'] = '0' * 64
        out = c643.evaluate_inputs(listener, vm)
        self.assertEqual(out['decision'], 'HOLD_SOURCE_NOT_ATTESTED')
        self.assertFalse(out['source_identity_cryptographically_attested'])

    def test_16_tampered_fictional_clock_is_rejected(self):
        listener, vm = c643.synthetic_pair()
        vm['evaluation_epoch_utc'] += 1
        with self.assertRaisesRegex(c643.Hold, '^VM_AUTHORITY_REJECTED$'):
            c643.evaluate_inputs(listener, vm)

    def test_17_no_real_host_socket_or_service_access(self):
        with patch.object(c642, 'inspect_local',
                          side_effect=AssertionError('REAL_HOST')), \
             patch.object(c642, 'read_table',
                          side_effect=AssertionError('REAL_PROC')), \
             patch.object(c642, 'query_unit',
                          side_effect=AssertionError('REAL_SYSTEMD')), \
             patch('socket.socket', side_effect=AssertionError('REAL_SOCKET')), \
             patch('socket.create_connection',
                   side_effect=AssertionError('REAL_SOCKET')), \
             patch('subprocess.Popen',
                   side_effect=AssertionError('REAL_SUBPROCESS')):
            for case in c643.SCENARIOS:
                self.assertEqual(c643.scenario_summary(case)['http_requests'], 0)

    def test_18_no_original_vm_default_network_factory(self):
        # C.63 binds its real HTTPConnection factory at definition time.
        # All eight calls in C.64.1 must explicitly inject a mock factory.
        original = c640.vm.fetch
        with patch.object(c640.vm, 'fetch', wraps=original) as spy, \
             patch('http.client.HTTPConnection',
                   side_effect=AssertionError('DEFAULT_HTTP')):
            c643.synthetic_pair('loopback_match')
            self.assertEqual(spy.call_count, 8)
            self.assertTrue(all(call.kwargs.get('factory') is not None
                                for call in spy.call_args_list))

    def test_19_no_file_reads_or_writes_from_synthetic_join(self):
        with patch('builtins.open', side_effect=AssertionError('FILE_ACCESS')):
            result = c643.scenario_summary('fd_denied')
            self.assertEqual(result['http_requests'], 0)

    def test_20_cross_source_non_atomicity_and_privileges(self):
        for scenario in c643.SCENARIOS:
            out = c643.scenario_summary(scenario)
            for key in ('input_objects_are_authenticated',
                        'source_identity_cryptographically_attested',
                        'independent_inputs_prove_same_process',
                        'sources_are_same_evidence',
                        'cross_source_causality_established',
                        'live_http_authorized', 'remediation_authorized'):
                self.assertIs(out[key], False)
            self.assertEqual(out['quality_gate_decision'],
                             'ABSTAIN_NO_MODEL_INFERENCE')
            self.assertEqual(out['dns_health'], 'NOT_ESTABLISHED')
            self.assertEqual(out['root_cause'], 'UNDETERMINED')
            self.assertEqual(out['model_action_authority'], 'NONE')
            self.assertEqual(out['model_requests'], 0)
            self.assertEqual(out['http_requests'], 0)
            self.assertEqual(out['deployment_gate'], 'HOLD')


def summary():
    result = {
        'schema': SCHEMA,
        'scope': 'FOUR_MODULES_SYNTHETIC_ONLY',
        'integration_cases': EXPECTED_CASES,
        'c640_fixture_scenarios': len(c640.CASES),
        'c641_mock_scenarios': len(c641.CASES),
        'c642_host_inspection_invoked': False,
        'c643_source_decisions': len(c643.SCENARIOS),
        'status': 'OFFLINE_INTEGRATION_CONTRACT_CHECK_ONLY',
        'http_requests': 0,
        'model_requests': 0,
        'model_action_authority': 'NONE',
        'live_http_authorized': False,
        'remediation_authorized': False,
        'deployment_gate': 'HOLD',
        'operator_security_approval': 'NOT_ESTABLISHED',
        'real_source_identity': 'UNVERIFIED',
        'merge_authorized': False,
    }
    if len(json.dumps(result, sort_keys=True).encode('ascii')) > MAX_SUMMARY_BYTES:
        raise AssertionError('UNEXPECTED_OUTPUT_SIZE')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--self-test', action='store_true')
    actions.add_argument('--summary-json', action='store_true')
    args = parser.parse_args(argv)
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(IntegrationTests))
        print('C64_INTEGRATION_TESTS=' + str(result.testsRun) + ' STATUS=' +
              ('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_TEST_FAILURE'))
        return 0 if result.wasSuccessful() else 1
    print(json.dumps(summary(), sort_keys=True, indent=2, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
