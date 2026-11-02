#!/usr/bin/env python3
"""C.64.3: synthetic-only independent-source and operator-decision HOLD gate.

Combines unrelated, IN-MEMORY C.64.2 metadata fixtures and C.64.1 fake
HTTP response fixtures. Their coincidence is not provenance, authentication,
DNS health, a cause, or approval to contact any live service.

CLI modes NEVER call inspect_local(), actual HTTP, router, model or executor.
The direct evaluate_inputs() API treats both incoming objects as unverified.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_ai_agent_v021c64_0_synthetic_vm_envelope_adapter as c640
import local_ai_agent_v021c64_1_mocked_vm_transport_contract as c641
import local_ai_agent_v021c64_2_listener_identity_preflight as c642

SCHEMA = 'local-ai-agent.v0.21.c64.3.independent-source-operator-gate.v1'
REVIEWS = (
    'UNREVIEWED', 'ACKNOWLEDGE_OFFLINE_FINDINGS', 'DECLINE_FURTHER_REVIEW',
)
SCENARIOS = (
    'fd_denied', 'loopback_match', 'owner_mismatch', 'wildcard_bind',
    'nonlocal_bind', 'no_listener', 'inactive_service', 'stale_metric',
    'missing_metric', 'invalid_guard', 'ipv6_loopback',
)
MAX_OUTPUT_BYTES = 3000

LISTENER_FIELDS = frozenset('''
schema mode service_name target_port tcp_listeners_count
loopback_ipv4_count loopback_ipv6_count wildcard_count nonloopback_count
systemd_active systemd_main_pid_present mainpid_socket_inode_match
preflight_result process_identity_cryptographically_attested
localhost_service_authentication_established socket_was_opened_by_agent
http_requests model_requests remediation_authorized model_action_authority
deployment_gate next_step
'''.split())

VM_FIELDS = frozenset('''
schema mode destination_contract dns_health evaluation_epoch_utc
expected_envelopes gaps model_action_authority model_invoked model_requests
next_step observation_classification observations_are_atomic
operator_next_step parsed_envelopes quality_gate_decision
remediation_authorized response_headers_verified root_cause sampled_mode
source_authenticity source_fingerprint_is_provenance_attestation
source_fingerprint_sha256 source_identity transport
transport_closed_connections transport_method transport_requests deployment_gate
'''.split())

LISTENER_RESULTS = frozenset((
    'OBSERVED_LOOPBACK_MAINPID_SOCKET_MANUAL_REVIEW_ONLY',
    'HOLD_LISTENER_FD_ACCESS_DENIED',
    'HOLD_LISTENER_OWNERSHIP_UNCONFIRMED',
    'HOLD_NONLOCAL_BIND_PRESENT',
    'HOLD_NO_LISTENER', 'HOLD_SERVICE_NOT_ACTIVE',
))
OWNER_STATES = frozenset(('YES', 'NO', 'UNAVAILABLE', 'PERMISSION_DENIED'))
VM_CLASSIFICATIONS = frozenset((
    'INSUFFICIENT_EVIDENCE',
    'DNS_GUARD_MODE_SAMPLED_ONLY',
    'INVALID_DNS_GUARD_STATE_SAMPLED',
))
GAP_CODE = re.compile(r'[A-Z][A-Z0-9_]{0,63}\Z')
HASH = re.compile(r'[0-9a-f]{64}\Z')


class Hold(Exception):
    """Opaque, fixed safety code; never echo untrusted input."""


def checked(condition, code):
    if not condition:
        raise Hold(code)


def validate_listener(x):
    checked(type(x) is dict and set(x) == LISTENER_FIELDS,
            'LISTENER_SCHEMA_REJECTED')
    fixed = {
        'schema': c642.SCHEMA,
        'mode': 'EXPLICIT_LOCAL_PROCESS_METADATA_INSPECTION_NO_HTTP',
        'service_name': c642.SERVICE, 'target_port': 8428,
        'process_identity_cryptographically_attested': False,
        'localhost_service_authentication_established': False,
        'socket_was_opened_by_agent': False,
        'http_requests': 0, 'model_requests': 0,
        'remediation_authorized': False, 'model_action_authority': 'NONE',
        'deployment_gate': 'HOLD',
        'next_step': 'MANUAL_REVIEW_ONLY_NO_LIVE_QUERY_AUTHORIZED',
    }
    checked(all(type(x[key]) is type(expected) and x[key] == expected
                for key, expected in fixed.items()), 'LISTENER_AUTHORITY_REJECTED')
    numbers = ('tcp_listeners_count', 'loopback_ipv4_count',
               'loopback_ipv6_count', 'wildcard_count', 'nonloopback_count')
    checked(all(type(x[k]) is int and 0 <= x[k] <= 32 for k in numbers),
            'LISTENER_COUNTS_REJECTED')
    checked(sum(x[k] for k in numbers[1:]) == x['tcp_listeners_count'],
            'LISTENER_COUNTS_REJECTED')
    checked(type(x['systemd_active']) is bool and
            type(x['systemd_main_pid_present']) is bool,
            'LISTENER_STATUS_REJECTED')
    owner = x['mainpid_socket_inode_match']
    checked(type(owner) is str and owner in OWNER_STATES,
            'LISTENER_OWNER_REJECTED')
    if x['wildcard_count'] or x['nonloopback_count']:
        expected = 'HOLD_NONLOCAL_BIND_PRESENT'
    elif not x['tcp_listeners_count']:
        expected = 'HOLD_NO_LISTENER'
    elif not x['systemd_active'] or not x['systemd_main_pid_present']:
        expected = 'HOLD_SERVICE_NOT_ACTIVE'
    elif owner == 'YES':
        expected = 'OBSERVED_LOOPBACK_MAINPID_SOCKET_MANUAL_REVIEW_ONLY'
    elif owner == 'PERMISSION_DENIED':
        expected = 'HOLD_LISTENER_FD_ACCESS_DENIED'
    else:
        expected = 'HOLD_LISTENER_OWNERSHIP_UNCONFIRMED'
    checked(x['preflight_result'] in LISTENER_RESULTS and
            x['preflight_result'] == expected, 'LISTENER_CONTRADICTION_REJECTED')


def validate_vm(x):
    checked(type(x) is dict and set(x) == VM_FIELDS, 'VM_SCHEMA_REJECTED')
    fixed = {
        'schema': c641.SCHEMA, 'mode': 'MOCK_HTTP_TRANSPORT_OFFLINE_ONLY',
        'destination_contract': 'FIXED_127_0_0_1_8428_NOT_CONTACTED',
        'dns_health': 'NOT_ESTABLISHED',
        'evaluation_epoch_utc': c640.FIXED_NOW,
        'expected_envelopes': 8, 'parsed_envelopes': 8,
        'model_action_authority': 'NONE',
        'model_invoked': False, 'model_requests': 0,
        'next_step': 'MANUAL_EVIDENCE_REVIEW_ONLY',
        'operator_next_step': 'MANUAL_REVIEW_ONLY',
        'observations_are_atomic': False,
        'quality_gate_decision': 'ABSTAIN_NO_MODEL_INFERENCE',
        'remediation_authorized': False,
        'response_headers_verified': False,
        'root_cause': 'UNDETERMINED',
        'source_authenticity': 'NOT_CRYPTOGRAPHICALLY_ATTESTED',
        'source_fingerprint_is_provenance_attestation': False,
        'source_identity': 'SCRIPTED_HTTP_CONNECTIONS_IN_MEMORY_NOT_REAL_VM',
        'transport': 'INJECTED_FAKE_HTTP_CONNECTION_OBJECTS',
        'transport_closed_connections': 8, 'transport_method': 'GET_ONLY',
        'transport_requests': 8, 'deployment_gate': 'HOLD',
    }
    checked(all(type(x[k]) is type(expected) and x[k] == expected
                for k, expected in fixed.items()), 'VM_AUTHORITY_REJECTED')
    checked(type(x['observation_classification']) is str and
            x['observation_classification'] in VM_CLASSIFICATIONS,
            'VM_CLASSIFICATION_REJECTED')
    checked(type(x['sampled_mode']) is str and
            x['sampled_mode'] in ('LOCAL', 'BOOTSTRAP', 'UNVERIFIED'),
            'VM_MODE_REJECTED')
    checked(type(x['gaps']) is list and len(x['gaps']) <= 16
            and all(type(k) is str and GAP_CODE.fullmatch(k) for k in x['gaps'])
            and len(set(x['gaps'])) == len(x['gaps']),
            'VM_GAPS_REJECTED')
    checked(type(x['source_fingerprint_sha256']) is str and
            HASH.fullmatch(x['source_fingerprint_sha256']) is not None,
            'VM_FINGERPRINT_REJECTED')
    if x['observation_classification'] == 'DNS_GUARD_MODE_SAMPLED_ONLY':
        checked(not x['gaps'] and x['sampled_mode'] in ('LOCAL', 'BOOTSTRAP'),
                'VM_CLASSIFICATION_CONTRADICTION')
    if x['observation_classification'] == 'INSUFFICIENT_EVIDENCE':
        checked(bool(x['gaps']) and x['sampled_mode'] == 'UNVERIFIED',
                'VM_CLASSIFICATION_CONTRADICTION')
    if x['observation_classification'] == 'INVALID_DNS_GUARD_STATE_SAMPLED':
        checked(not x['gaps'] and x['sampled_mode'] == 'UNVERIFIED',
                'VM_CLASSIFICATION_CONTRADICTION')


def evaluate_inputs(listener, vm, review='UNREVIEWED'):
    """Pure bounded assessment of two separately unverified input objects.

    This function can accept outside data as Python dictionaries; parsing
    shape and field values NEVER proves their origin or relationship.
    """
    checked(type(review) is str and review in REVIEWS,
            'REVIEW_CODE_NOT_ALLOWED')
    validate_listener(listener)
    validate_vm(vm)
    observed = listener['preflight_result']
    if review == 'DECLINE_FURTHER_REVIEW':
        decision = 'HOLD_OPERATOR_DECLINED'
    elif observed == 'HOLD_LISTENER_FD_ACCESS_DENIED':
        decision = 'HOLD_FD_ACCESS_DENIED'
    elif observed == 'HOLD_NONLOCAL_BIND_PRESENT':
        decision = 'HOLD_NONLOCAL_BIND'
    elif observed == 'HOLD_NO_LISTENER':
        decision = 'HOLD_NO_LISTENER'
    elif observed == 'HOLD_SERVICE_NOT_ACTIVE':
        decision = 'HOLD_SERVICE_NOT_ACTIVE'
    elif observed != 'OBSERVED_LOOPBACK_MAINPID_SOCKET_MANUAL_REVIEW_ONLY':
        decision = 'HOLD_OWNER_NOT_ESTABLISHED'
    elif vm['observation_classification'] != 'DNS_GUARD_MODE_SAMPLED_ONLY':
        decision = 'HOLD_UNQUALIFIED_SYNTHETIC_SAMPLES'
    else:
        decision = 'HOLD_SOURCE_NOT_ATTESTED'
    output = {
        'schema': SCHEMA,
        'mode': 'SYNTHETIC_ONLY_INDEPENDENT_SOURCE_REVIEW',
        'listener_metadata_input_schema': c642.SCHEMA,
        'vm_mock_input_schema': c641.SCHEMA,
        'input_objects_are_authenticated': False,
        'source_identity_cryptographically_attested': False,
        'independent_inputs_prove_same_process': False,
        'sources_are_same_evidence': False,
        'cross_source_causality_established': False,
        'listener_result': observed,
        'vm_classification': vm['observation_classification'],
        'vm_gap_count': len(vm['gaps']),
        'review_code': review,
        'review_code_authenticated': False,
        'review_acknowledgement_grants_access': False,
        'decision': decision,
        'next_step': 'MANUAL_REVIEW_ONLY',
        'live_http_authorized': False,
        'http_requests': 0,
        'model_requests': 0,
        'model_invoked': False,
        'quality_gate_decision': 'ABSTAIN_NO_MODEL_INFERENCE',
        'root_cause': 'UNDETERMINED',
        'dns_health': 'NOT_ESTABLISHED',
        'model_action_authority': 'NONE',
        'remediation_authorized': False,
        'deployment_gate': 'HOLD',
    }
    checked(len(json.dumps(output, sort_keys=True,
                           separators=(',', ':')).encode('ascii')) <= MAX_OUTPUT_BYTES,
            'OUTPUT_BOUNDARY_EXCEEDED')
    return output


def synthetic_pair(scenario='fd_denied'):
    checked(type(scenario) is str and scenario in SCENARIOS,
            'SCENARIO_NOT_ALLOWED')
    addr = c642.table([c642.mock_row('0100007F')])
    ipv6 = c642.table()
    state, pid, owner = 'active', 123, 'PERMISSION_DENIED'
    vm_case = 'baseline'
    if scenario == 'loopback_match':
        owner = 'YES'
    elif scenario == 'owner_mismatch':
        owner = 'NO'
    elif scenario == 'wildcard_bind':
        addr = c642.table([c642.mock_row('00000000')])
    elif scenario == 'nonlocal_bind':
        addr = c642.table([c642.mock_row('0200A8C0')])
    elif scenario == 'no_listener':
        addr = c642.table()
    elif scenario == 'inactive_service':
        state = 'inactive'
    elif scenario == 'stale_metric':
        owner, vm_case = 'YES', 'stale_local'
    elif scenario == 'missing_metric':
        owner, vm_case = 'YES', 'missing_local'
    elif scenario == 'invalid_guard':
        owner, vm_case = 'YES', 'invalid_guard'
    elif scenario == 'ipv6_loopback':
        addr, ipv6 = c642.table(), c642.table([
            c642.mock_row('00000000000000000000000001000000')])
    listener = c642.evaluate(addr, ipv6, state, pid, lambda *_: owner)
    vm = c641.run_mock(vm_case)
    return listener, vm


def scenario_summary(scenario='fd_denied', review='UNREVIEWED'):
    # Only this wrapper constructs its own entirely fictional sources.
    listener, vm = synthetic_pair(scenario)
    return evaluate_inputs(listener, vm, review)


def matrix():
    return {name: scenario_summary(name) for name in SCENARIOS}


class Tests(unittest.TestCase):
    def hold(self, action, code):
        with self.assertRaisesRegex(Hold, '^' + re.escape(code) + '$'):
            action()

    def test_01_baseline_fd_denied(self):
        self.assertEqual(scenario_summary()['decision'], 'HOLD_FD_ACCESS_DENIED')

    def test_02_positive_synthetic_match_still_hold(self):
        self.assertEqual(scenario_summary('loopback_match')['decision'],
                         'HOLD_SOURCE_NOT_ATTESTED')

    def test_03_owner_mismatch(self):
        self.assertEqual(scenario_summary('owner_mismatch')['decision'],
                         'HOLD_OWNER_NOT_ESTABLISHED')

    def test_04_wildcard_bind(self):
        self.assertEqual(scenario_summary('wildcard_bind')['decision'],
                         'HOLD_NONLOCAL_BIND')

    def test_05_nonlocal_bind(self):
        self.assertEqual(scenario_summary('nonlocal_bind')['decision'],
                         'HOLD_NONLOCAL_BIND')

    def test_06_no_listener(self):
        self.assertEqual(scenario_summary('no_listener')['decision'],
                         'HOLD_NO_LISTENER')

    def test_07_inactive_service(self):
        self.assertEqual(scenario_summary('inactive_service')['decision'],
                         'HOLD_SERVICE_NOT_ACTIVE')

    def test_08_stale_metric(self):
        self.assertEqual(scenario_summary('stale_metric')['decision'],
                         'HOLD_UNQUALIFIED_SYNTHETIC_SAMPLES')

    def test_09_missing_metric(self):
        self.assertEqual(scenario_summary('missing_metric')['decision'],
                         'HOLD_UNQUALIFIED_SYNTHETIC_SAMPLES')

    def test_10_invalid_guard(self):
        self.assertEqual(scenario_summary('invalid_guard')['decision'],
                         'HOLD_UNQUALIFIED_SYNTHETIC_SAMPLES')

    def test_11_ipv6_loopback_not_attestation(self):
        self.assertEqual(scenario_summary('ipv6_loopback')['decision'],
                         'HOLD_FD_ACCESS_DENIED')

    def test_12_all_scenarios_hold(self):
        self.assertTrue(all(v['decision'].startswith('HOLD_')
                            for v in matrix().values()))

    def test_13_all_scenarios_abstain(self):
        self.assertTrue(all(v['quality_gate_decision'] == 'ABSTAIN_NO_MODEL_INFERENCE'
                            for v in matrix().values()))

    def test_14_all_scenarios_no_permissions(self):
        for v in matrix().values():
            self.assertFalse(v['live_http_authorized'])
            self.assertFalse(v['remediation_authorized'])
            self.assertEqual(v['model_action_authority'], 'NONE')
            self.assertEqual(v['deployment_gate'], 'HOLD')

    def test_15_all_scenarios_no_health(self):
        for v in matrix().values():
            self.assertEqual(v['dns_health'], 'NOT_ESTABLISHED')
            self.assertEqual(v['root_cause'], 'UNDETERMINED')

    def test_16_all_scenarios_no_http(self):
        for v in matrix().values():
            self.assertEqual(v['http_requests'], 0)
            self.assertEqual(v['model_requests'], 0)

    def test_17_operator_ack_is_not_permission(self):
        x = scenario_summary('loopback_match', 'ACKNOWLEDGE_OFFLINE_FINDINGS')
        self.assertFalse(x['review_acknowledgement_grants_access'])
        self.assertFalse(x['review_code_authenticated'])
        self.assertEqual(x['decision'], 'HOLD_SOURCE_NOT_ATTESTED')

    def test_18_operator_decline_holds(self):
        self.assertEqual(scenario_summary('loopback_match', 'DECLINE_FURTHER_REVIEW')['decision'],
                         'HOLD_OPERATOR_DECLINED')

    def test_19_live_request_refused(self):
        self.hold(lambda: scenario_summary('loopback_match', 'REQUEST_LIVE_ACCESS'),
                  'REVIEW_CODE_NOT_ALLOWED')

    def test_20_bad_scenario_refused(self):
        self.hold(lambda: scenario_summary('live'), 'SCENARIO_NOT_ALLOWED')

    def test_21_bad_type_review(self):
        self.hold(lambda: scenario_summary(review=True), 'REVIEW_CODE_NOT_ALLOWED')

    def test_22_source_dict_not_accepted_with_extra_key(self):
        a, b = synthetic_pair()
        a['raw_fd'] = 'sensitive'
        self.hold(lambda: evaluate_inputs(a, b), 'LISTENER_SCHEMA_REJECTED')

    def test_23_vm_dict_not_accepted_with_extra_key(self):
        a, b = synthetic_pair()
        b['raw_http_body'] = 'secret'
        self.hold(lambda: evaluate_inputs(a, b), 'VM_SCHEMA_REJECTED')

    def test_24_listener_attestation_spoof(self):
        a, b = synthetic_pair()
        a['process_identity_cryptographically_attested'] = True
        self.hold(lambda: evaluate_inputs(a, b), 'LISTENER_AUTHORITY_REJECTED')

    def test_25_vm_auth_spoof(self):
        a, b = synthetic_pair()
        b['source_authenticity'] = 'TRUSTED'
        self.hold(lambda: evaluate_inputs(a, b), 'VM_AUTHORITY_REJECTED')

    def test_26_listener_http_spoof(self):
        a, b = synthetic_pair()
        a['http_requests'] = 1
        self.hold(lambda: evaluate_inputs(a, b), 'LISTENER_AUTHORITY_REJECTED')

    def test_27_vm_model_spoof(self):
        a, b = synthetic_pair()
        b['model_requests'] = 1
        self.hold(lambda: evaluate_inputs(a, b), 'VM_AUTHORITY_REJECTED')

    def test_28_vm_remediation_spoof(self):
        a, b = synthetic_pair()
        b['remediation_authorized'] = True
        self.hold(lambda: evaluate_inputs(a, b), 'VM_AUTHORITY_REJECTED')

    def test_29_listener_remediation_spoof(self):
        a, b = synthetic_pair()
        a['remediation_authorized'] = True
        self.hold(lambda: evaluate_inputs(a, b), 'LISTENER_AUTHORITY_REJECTED')

    def test_30_vm_diagnosis_spoof(self):
        a, b = synthetic_pair()
        b['root_cause'] = 'ROUTER'
        self.hold(lambda: evaluate_inputs(a, b), 'VM_AUTHORITY_REJECTED')

    def test_31_vm_clock_mismatch(self):
        a, b = synthetic_pair()
        b['evaluation_epoch_utc'] += 1
        self.hold(lambda: evaluate_inputs(a, b), 'VM_AUTHORITY_REJECTED')

    def test_32_listener_count_mismatch(self):
        a, b = synthetic_pair()
        a['tcp_listeners_count'] = 2
        self.hold(lambda: evaluate_inputs(a, b), 'LISTENER_COUNTS_REJECTED')

    def test_33_listener_boolean_not_int(self):
        a, b = synthetic_pair()
        a['loopback_ipv4_count'] = True
        self.hold(lambda: evaluate_inputs(a, b), 'LISTENER_COUNTS_REJECTED')

    def test_34_listener_owner_contradiction(self):
        a, b = synthetic_pair()
        a['mainpid_socket_inode_match'] = 'YES'
        self.hold(lambda: evaluate_inputs(a, b), 'LISTENER_CONTRADICTION_REJECTED')

    def test_35_listener_result_spoof(self):
        a, b = synthetic_pair()
        a['preflight_result'] = 'OBSERVED_LOOPBACK_MAINPID_SOCKET_MANUAL_REVIEW_ONLY'
        self.hold(lambda: evaluate_inputs(a, b), 'LISTENER_CONTRADICTION_REJECTED')

    def test_36_vm_invalid_classification(self):
        a, b = synthetic_pair()
        b['observation_classification'] = 'DNS_HEALTHY'
        self.hold(lambda: evaluate_inputs(a, b), 'VM_CLASSIFICATION_REJECTED')

    def test_37_vm_samples_contradiction(self):
        a, b = synthetic_pair()
        b['gaps'] = ['LOCAL_RAW_SAMPLE_STALE']
        self.hold(lambda: evaluate_inputs(a, b), 'VM_CLASSIFICATION_CONTRADICTION')

    def test_38_vm_gap_content_rejected(self):
        a, b = synthetic_pair()
        b['gaps'] = ['password=abc']
        self.hold(lambda: evaluate_inputs(a, b), 'VM_GAPS_REJECTED')

    def test_39_vm_bad_digest(self):
        a, b = synthetic_pair()
        b['source_fingerprint_sha256'] = 'not a digest'
        self.hold(lambda: evaluate_inputs(a, b), 'VM_FINGERPRINT_REJECTED')

    def test_40_nonatomic_sources_never_join(self):
        x = scenario_summary('loopback_match')
        self.assertFalse(x['independent_inputs_prove_same_process'])
        self.assertFalse(x['sources_are_same_evidence'])
        self.assertFalse(x['cross_source_causality_established'])

    def test_41_reproducible(self):
        self.assertEqual(scenario_summary(), scenario_summary())

    def test_42_bounded_and_redacted(self):
        blob = json.dumps(scenario_summary(), sort_keys=True)
        self.assertLess(len(blob.encode('ascii')), MAX_OUTPUT_BYTES)
        for item in ('12345', '192.168.', 'password', 'MainPID=', 'raw_http_body'):
            self.assertNotIn(item, blob)

    def test_43_never_uses_real_host_or_network(self):
        with patch.object(c642, 'inspect_local', side_effect=AssertionError('HOST')), \
             patch.object(c642, 'query_unit', side_effect=AssertionError('SYSTEMD')), \
             patch.object(c642, 'read_table', side_effect=AssertionError('PROC')), \
             patch('socket.create_connection', side_effect=AssertionError('TCP')), \
             patch('socket.socket', side_effect=AssertionError('TCP')):
            self.assertEqual(scenario_summary()['http_requests'], 0)

    def test_44_never_uses_model_or_subprocess(self):
        with patch('subprocess.Popen', side_effect=AssertionError('SUBPROCESS')):
            self.assertEqual(scenario_summary()['model_requests'], 0)

    def test_45_no_filesystem_writes(self):
        with patch('builtins.open', side_effect=AssertionError('FILES')):
            self.assertEqual(scenario_summary()['model_requests'], 0)

    def test_46_c642_fd_permission_is_not_source_identity(self):
        x = scenario_summary()
        self.assertEqual(x['listener_result'], 'HOLD_LISTENER_FD_ACCESS_DENIED')
        self.assertFalse(x['source_identity_cryptographically_attested'])

    def test_47_no_real_user_approval(self):
        x = scenario_summary('loopback_match', 'ACKNOWLEDGE_OFFLINE_FINDINGS')
        self.assertFalse(x['input_objects_are_authenticated'])
        self.assertFalse(x['review_code_authenticated'])
        self.assertFalse(x['live_http_authorized'])

    def test_48_strict_shape_type(self):
        a, b = synthetic_pair()
        self.hold(lambda: evaluate_inputs([], b), 'LISTENER_SCHEMA_REJECTED')
        self.hold(lambda: evaluate_inputs(a, []), 'VM_SCHEMA_REJECTED')

    def test_49_contract_keys_match_actual_c642_c641_producers(self):
        a, b = synthetic_pair('fd_denied')
        self.assertEqual(set(a), LISTENER_FIELDS)
        self.assertEqual(set(b), VM_FIELDS)
        self.assertEqual(b['deployment_gate'], 'HOLD')

    def test_50_no_external_authority_from_direct_input(self):
        a, b = synthetic_pair('loopback_match')
        result = evaluate_inputs(a, b, 'ACKNOWLEDGE_OFFLINE_FINDINGS')
        self.assertEqual(result['decision'], 'HOLD_SOURCE_NOT_ATTESTED')
        self.assertFalse(result['review_code_authenticated'])
        self.assertFalse(result['live_http_authorized'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--self-test', action='store_true')
    mode.add_argument('--synthetic-matrix', action='store_true')
    mode.add_argument('--summary-json', action='store_true')
    parser.add_argument('--scenario', choices=SCENARIOS, default='fd_denied')
    parser.add_argument('--review-code', choices=REVIEWS, default='UNREVIEWED')
    args = parser.parse_args(argv)
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        print('C643_TESTS=' + str(result.testsRun) + ' STATUS='
              + ('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_TEST_FAILURE'))
        return 0 if result.wasSuccessful() else 1
    try:
        if args.synthetic_matrix:
            for key, value in matrix().items():
                print('SCENARIO=' + key + ' DECISION=' + value['decision']
                      + ' HTTP_REQUESTS=' + str(value['http_requests'])
                      + ' MODEL_REQUESTS=' + str(value['model_requests']))
            print('C643_RESULT=PASS_SYNTHETIC_HOLD_MATRIX')
        else:
            print(json.dumps(scenario_summary(args.scenario, args.review_code),
                             sort_keys=True, indent=2, ensure_ascii=True))
    except Hold as exc:
        print('C643_RESULT=HOLD_' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
