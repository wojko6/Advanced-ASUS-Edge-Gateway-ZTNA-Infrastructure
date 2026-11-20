#!/usr/bin/env python3
"""C.63.6 pre-model gate: never contact Qwen for invalid synthetic evidence.

Offline modes never contact network, files, subprocess or host services.
The explicit --qwen-gated mode contacts only local Ollama at 127.0.0.1:11435
for ONE hardcoded synthetic baseline after the C.63.5 gate accepts it.
No real telemetry, arbitrary inputs, actions, tools or config writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unittest

import local_ai_agent_v021c63_5_evidence_quality_abstention_offline_lab_v01 as evidence
import local_ai_agent_v021c63_3_1_qwen_shadow_port_11435_synthetic_lab_v01 as shadow
import local_ai_agent_v021c63_2_bounded_shadow_contract_offline_lab_v01 as bounded
import local_ai_agent_v021c63_multisource_assessment_offline_lab_v01 as parent

sys.dont_write_bytecode = True
SCHEMA = 'local-ai-agent.c63.6.pre-model-evidence-gate.v1'
GATE_KEYS = frozenset((
    'schema', 'evidence_origin', 'decision', 'reason_code', 'parent_assessment',
    'collection_resumption_observed_in_synthetic_grid', 'source_provenance_attested',
    'source_fingerprint_sha256', 'actual_dns_health', 'root_cause',
    'model_invoked', 'model_action_authority', 'remediation_authorized',
    'deployment_gate',
))
READY_RESULT = 'PASS_ONE_SYNTHETIC_QWEN_AND_13_ABSTENTIONS'
NO_MODEL_RESULT = 'PASS_ONE_SYNTHETIC_READY_13_ABSTENTIONS_NO_MODEL'

class Hold(Exception):
    """Fail-closed if any contract assertion is violated."""


def strict_gate(case):
    """Reject invalid evidence before the network callback is even available."""
    if type(case) is not str or case not in evidence.CASES:
        raise Hold('CASE_NOT_WHITELISTED')
    source = evidence.synthetic_case(case)
    assessment = evidence.assess(source)
    if type(assessment) is not dict or set(assessment) != GATE_KEYS:
        raise Hold('GATE_SCHEMA_MISMATCH')
    if (assessment['schema'] != evidence.SCHEMA
            or assessment['evidence_origin'] != 'SYNTHETIC_OFFLINE_ONLY'
            or assessment['source_provenance_attested'] is not False
            or assessment['actual_dns_health'] != 'NOT_ESTABLISHED'
            or assessment['root_cause'] != 'UNDETERMINED'
            or assessment['model_invoked'] is not False
            or assessment['model_action_authority'] != 'NONE'
            or assessment['remediation_authorized'] is not False
            or assessment['deployment_gate'] != 'HOLD'):
        raise Hold('GATE_SAFETY_INVARIANT')
    if case == 'baseline':
        expected = parent.evaluate(parent.fixture('cross_source'))
        digest = hashlib.sha256(parent.canonical(source)).hexdigest()
        if (assessment['decision'] != evidence.READY
                or assessment['reason_code'] != 'NONE'
                or assessment['parent_assessment'] != expected['assessment_status']
                or assessment['parent_assessment'] != 'CROSS_SOURCE_TEMPORAL_CORRELATION_ONLY'
                or assessment['collection_resumption_observed_in_synthetic_grid'] is not True
                or assessment['source_fingerprint_sha256'] != digest):
            raise Hold('BASELINE_GATE_INCONSISTENT')
    else:
        if (assessment['decision'] != evidence.ABSTAIN
                or assessment['reason_code'] == 'NONE'
                or assessment['source_fingerprint_sha256'] != 'NOT_ISSUED'):
            raise Hold('INVALID_CASE_UNEXPECTEDLY_READY')
    return assessment


def strict_packet():
    """C.63.2 fixed, bounded, synthetic packet; not a reserialized log."""
    pkt = shadow.packet()
    if (pkt != bounded.fixture_packet()
            or pkt.get('assessment_code') != 'TEMPORAL_CORRELATION_ONLY'
            or pkt.get('source_provenance_attested') is not False
            or pkt.get('model_action_authority') != 'NONE'
            or pkt.get('remediation_authorized') is not False
            or pkt.get('deployment_gate') != 'HOLD'):
        raise Hold('SYNTHETIC_PACKET_INVARIANT')
    return pkt


def process_case(case, send=None):
    """Call `send(pkt)` at most once, and ONLY for the whitelist baseline.

    `send` is a test callback in offline modes. The only real sender is
    fixed_ollama_sender, used only in the explicit --qwen-gated mode.
    """
    gate = strict_gate(case)
    if gate['decision'] == evidence.ABSTAIN:
        return {
            'schema': SCHEMA,
            'scenario': case,
            'gate_decision': evidence.ABSTAIN,
            'reason_code': gate['reason_code'],
            'model_requests': 0,
            'model_invoked': False,
            'response_gate': 'NOT_APPLICABLE_NO_MODEL',
            'assessment_code': 'NOT_ISSUED',
            'next_check_code': 'NOT_ISSUED',
            'root_cause': 'UNDETERMINED',
            'deployment_gate': 'HOLD',
            'model_action_authority': 'NONE',
        }
    if case != 'baseline' or gate['decision'] != evidence.READY:
        raise Hold('UNEXPECTED_SHADOW_ELIGIBILITY')
    pkt = strict_packet()
    if send is None:
        return {
            'schema': SCHEMA, 'scenario': case,
            'gate_decision': evidence.READY, 'reason_code': 'NONE',
            'model_requests': 0, 'model_invoked': False,
            'response_gate': 'NOT_INVOKED_OFFLINE',
            'assessment_code': 'TEMPORAL_CORRELATION_ONLY',
            'next_check_code': 'NOT_ISSUED', 'root_cause': 'UNDETERMINED',
            'deployment_gate': 'HOLD', 'model_action_authority': 'NONE',
        }
    accepted = send(pkt)
    if (type(accepted) is not dict
            or accepted.get('result') != 'PASS_SHADOW_CODES_ONLY'
            or accepted.get('input_sha256') != pkt['input_sha256']
            or accepted.get('accepted_assessment_code') != pkt['assessment_code']
            or accepted.get('accepted_next_check_code') not in bounded.NEXT_CHECKS
            or accepted.get('model_action_authority') != 'NONE'
            or accepted.get('deployment_gate') != 'HOLD'):
        raise Hold('MODEL_VALIDATION_NOT_ACCEPTED')
    return {
        'schema': SCHEMA, 'scenario': case, 'gate_decision': evidence.READY,
        'reason_code': 'NONE', 'model_requests': 1, 'model_invoked': True,
        'response_gate': 'ACCEPTED_CODES_ONLY',
        'assessment_code': pkt['assessment_code'],
        'next_check_code': accepted['accepted_next_check_code'],
        'root_cause': 'UNDETERMINED', 'deployment_gate': 'HOLD',
        'model_action_authority': 'NONE',
    }


def fixed_ollama_sender(pkt):
    """One fixed POST to localhost. No user-defined URL, file, tool or input."""
    req = shadow.make_request(pkt)
    op = shadow.opener() # proxy disabled; redirects forbidden by parent
    shadow.check_model_installed(op) # bounded GET /api/tags
    raw = shadow.bounded_http(op, '/api/generate', body=req) # single generation
    return shadow.validate_ollama(raw, pkt)


def all_offline():
    """Return classified cases without even constructing an HTTP client."""
    results = [process_case(name) for name in evidence.CASES]
    if (len(results) != 14
            or [r['scenario'] for r in results if r['gate_decision'] == evidence.READY] != ['baseline']
            or sum(r['model_requests'] for r in results) != 0):
        raise Hold('OFFLINE_MATRIX_MISMATCH')
    return results


def mock_valid_sender(pkt):
    return bounded.validate_response(
        json.dumps(bounded.response_for_fixture(pkt), sort_keys=True).encode('ascii'), pkt)


class Tests(unittest.TestCase):
    def test_01_exact_cases(self): self.assertEqual(len(evidence.CASES), 14)
    def test_02_fixed_endpoint(self): self.assertEqual(shadow.BASE, 'http://127.0.0.1:11435')
    def test_03_fixed_model(self): self.assertEqual(shadow.MODEL, 'qwen3.5:4b')
    def test_04_baseline_ready(self): self.assertEqual(strict_gate('baseline')['decision'], evidence.READY)
    def test_05_fingerprint(self): self.assertRegex(strict_gate('baseline')['source_fingerprint_sha256'], r'^[0-9a-f]{64}$')
    def test_06_origin(self): self.assertEqual(strict_gate('baseline')['evidence_origin'], 'SYNTHETIC_OFFLINE_ONLY')
    def test_07_no_attestation(self): self.assertFalse(strict_gate('baseline')['source_provenance_attested'])
    def test_08_no_dns_health(self): self.assertEqual(strict_gate('baseline')['actual_dns_health'], 'NOT_ESTABLISHED')
    def test_09_no_cause(self): self.assertEqual(strict_gate('baseline')['root_cause'], 'UNDETERMINED')
    def test_10_no_authority(self): self.assertEqual(strict_gate('baseline')['model_action_authority'], 'NONE')
    def test_11_hold(self): self.assertEqual(strict_gate('baseline')['deployment_gate'], 'HOLD')
    def test_12_packet(self): self.assertEqual(strict_packet(), bounded.fixture_packet())
    def test_13_packet_no_log(self): self.assertNotIn('raw_log',json.dumps(strict_packet()))
    def test_14_no_model_baseline(self): self.assertEqual(process_case('baseline')['model_requests'], 0)
    def test_15_offline_matrix(self): self.assertEqual(len(all_offline()), 14)
    def test_16_only_baseline(self): self.assertEqual([r['scenario'] for r in all_offline() if r['gate_decision'] == evidence.READY], ['baseline'])
    def test_17_no_network_offline(self): self.assertEqual(sum(r['model_requests'] for r in all_offline()),0)
    def test_18_unknown_blocked(self):
        with self.assertRaisesRegex(Hold,'CASE_NOT_WHITELISTED'): process_case('host')
    def test_19_noarbitrary_none(self):
        with self.assertRaisesRegex(Hold,'CASE_NOT_WHITELISTED'): process_case(None)
    def test_20_noarbitrary_dict(self):
        with self.assertRaisesRegex(Hold,'CASE_NOT_WHITELISTED'): process_case({})
    def test_21_baseline_mock_accepted(self): self.assertEqual(process_case('baseline',mock_valid_sender)['response_gate'],'ACCEPTED_CODES_ONLY')
    def test_22_baseline_mock_one_call(self):
        seen=[]
        def sender(pkt): seen.append(pkt);return mock_valid_sender(pkt)
        self.assertEqual(process_case('baseline',sender)['model_requests'],1)
        self.assertEqual(len(seen),1)
    def test_23_baseline_model_not_root(self): self.assertEqual(process_case('baseline',mock_valid_sender)['root_cause'],'UNDETERMINED')
    def test_24_baseline_next_check(self): self.assertEqual(process_case('baseline',mock_valid_sender)['next_check_code'],'MANUAL_EVIDENCE_REVIEW_ONLY')
    def test_25_abstention_never_calls_sender(self):
        def forbidden(_): raise AssertionError('model invocation on abstention')
        for name in evidence.CASES:
            if name!='baseline': self.assertEqual(process_case(name,forbidden)['model_requests'],0)
    def test_26_abstention_model_invoked_false(self):
        for name in evidence.CASES[1:]: self.assertFalse(process_case(name,mock_valid_sender)['model_invoked'])
    def test_27_abstentions_no_hash(self):
        for name in evidence.CASES[1:]: self.assertEqual(strict_gate(name)['source_fingerprint_sha256'],'NOT_ISSUED')
    def test_28_response_missing(self):
        with self.assertRaisesRegex(Hold,'MODEL_VALIDATION_NOT_ACCEPTED'): process_case('baseline',lambda _: {})
    def test_29_response_none(self):
        with self.assertRaisesRegex(Hold,'MODEL_VALIDATION_NOT_ACCEPTED'): process_case('baseline',lambda _: None)
    def test_30_response_forged(self):
        fake=dict(mock_valid_sender(strict_packet()), input_sha256='0'*64)
        with self.assertRaisesRegex(Hold,'MODEL_VALIDATION_NOT_ACCEPTED'): process_case('baseline',lambda _: fake)
    def test_31_response_action(self):
        fake=dict(mock_valid_sender(strict_packet()), accepted_next_check_code='RESTART_ROUTER')
        with self.assertRaisesRegex(Hold,'MODEL_VALIDATION_NOT_ACCEPTED'): process_case('baseline',lambda _: fake)
    def test_32_response_authority(self):
        fake=dict(mock_valid_sender(strict_packet()), model_action_authority='ROOT')
        with self.assertRaisesRegex(Hold,'MODEL_VALIDATION_NOT_ACCEPTED'): process_case('baseline',lambda _: fake)
    def test_33_response_gate(self):
        fake=dict(mock_valid_sender(strict_packet()), deployment_gate='OPEN')
        with self.assertRaisesRegex(Hold,'MODEL_VALIDATION_NOT_ACCEPTED'): process_case('baseline',lambda _: fake)
    def test_34_sender_throws(self):
        def broken(_): raise shadow.Hold('SIMULATED_TRANSPORT_FAILED')
        with self.assertRaisesRegex(shadow.Hold,'SIMULATED_TRANSPORT_FAILED'): process_case('baseline',broken)
    def test_35_parent_outcome(self): self.assertEqual(strict_gate('baseline')['parent_assessment'],'CROSS_SOURCE_TEMPORAL_CORRELATION_ONLY')
    def test_36_no_injected_log(self): self.assertEqual(process_case('injected_log_field')['gate_decision'],evidence.ABSTAIN)
    def test_37_no_injected_cause(self): self.assertEqual(process_case('injected_root_cause')['gate_decision'],evidence.ABSTAIN)
    def test_38_no_spoof(self): self.assertEqual(process_case('spoofed_provenance')['gate_decision'],evidence.ABSTAIN)
    def test_39_no_stale(self): self.assertEqual(process_case('stale_raw_sample')['gate_decision'],evidence.ABSTAIN)
    def test_40_no_conflict(self): self.assertEqual(process_case('conflicting_vm_labels')['gate_decision'],evidence.ABSTAIN)
    def test_41_no_dup_sample(self): self.assertEqual(process_case('duplicate_raw_sample')['gate_decision'],evidence.ABSTAIN)
    def test_42_no_future(self): self.assertEqual(process_case('future_event')['gate_decision'],evidence.ABSTAIN)
    def test_43_only_model_on_ready(self):
        count=[]
        def s(pkt): count.append(pkt);return mock_valid_sender(pkt)
        rows=[process_case(n,s) for n in evidence.CASES]
        self.assertEqual(len(count),1)
        self.assertEqual(sum(r['model_requests'] for r in rows),1)
    def test_44_safety_everycase(self):
        for n in evidence.CASES:
            r=process_case(n)
            self.assertEqual(r['model_action_authority'],'NONE')
            self.assertEqual(r['deployment_gate'],'HOLD')
            self.assertEqual(r['root_cause'],'UNDETERMINED')
    def test_45_offline_never_invokes_model(self): self.assertTrue(all(not x['model_invoked'] for x in all_offline()))
    def test_46_no_host_paths(self):
        for n in evidence.CASES:
            self.assertNotIn('192.168.',json.dumps(process_case(n)))
            self.assertNotIn('SSID=',json.dumps(process_case(n)))
    def test_47_no_extra_fields(self):
        expected=set(process_case('baseline'))
        self.assertTrue(all(set(r)==expected for r in all_offline()))
    def test_48_mock_output_schema(self): self.assertEqual(process_case('baseline',mock_valid_sender)['schema'],SCHEMA)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    opts=p.add_mutually_exclusive_group(required=True)
    opts.add_argument('--self-test',action='store_true',help='48 offline tests; no network')
    opts.add_argument('--fixture-matrix',action='store_true',help='14 offline cases; no network')
    opts.add_argument('--qwen-gated',action='store_true',help='Explicit localhost model call for ONE synthetic qualified baseline only')
    args=p.parse_args(argv)
    print('=== LOCAL AI AGENT / C.63.6 / PRE-MODEL EVIDENCE GATE ===')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    if args.self_test:
        print('MODE=OFFLINE_SELFTEST NETWORK=NO MODEL=NO HOST_READS=NO')
        result=unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        passed=result.testsRun-len(result.failures)-len(result.errors)
        print(f'C636_SELFTESTS={passed}/{result.testsRun}')
        print('C636_RESULT='+('PASS_OFFLINE' if result.wasSuccessful() and result.testsRun==48 else 'HOLD'))
        return 0 if result.wasSuccessful() and result.testsRun==48 else 1
    if args.fixture_matrix:
        print('MODE=OFFLINE_MATRIX NO_NETWORK=YES NO_MODEL=YES')
        try:
            results=all_offline()
            for r in results:
                print('SCENARIO='+r['scenario']+' DECISION='+r['gate_decision']+' MODEL_REQUESTS='+str(r['model_requests']))
            print('C636_RESULT='+NO_MODEL_RESULT)
            return 0
        except (Hold,evidence.Hold,parent.Hold,shadow.Hold,bounded.Hold) as exc:
            print('C636_RESULT=HOLD_'+str(exc))
            return 1
    print('MODE=MANUAL_LOCAL_QWEN_GATED SYNTHETIC_ONLY=YES LOOPBACK_ONLY=YES')
    print('MAX_GENERATIONS=1 NO_ROUTER=YES NO_REAL_LOGS=YES NO_TOOLS=YES')
    try:
        # Always check blocked cases BEFORE constructing the network opener.
        blocked=[process_case(n) for n in evidence.CASES if n!='baseline']
        if len(blocked)!=13 or any(x['model_requests'] or x['gate_decision']!=evidence.ABSTAIN for x in blocked):
            raise Hold('PREMODEL_ABSTENTION_BROKEN')
        baseline=process_case('baseline',fixed_ollama_sender)
        if baseline['model_requests']!=1 or baseline['response_gate']!='ACCEPTED_CODES_ONLY':
            raise Hold('BASELINE_NOT_ACCEPTED')
        for result in blocked:
            print('SCENARIO='+result['scenario']+' DECISION=ABSTAIN_NO_MODEL_INFERENCE MODEL_REQUESTS=0')
        print('SCENARIO=baseline DECISION='+baseline['gate_decision']+' MODEL_REQUESTS=1')
        print('ACCEPTED_ASSESSMENT='+baseline['assessment_code'])
        print('ACCEPTED_NEXT_CHECK='+baseline['next_check_code'])
        print('ABSTAINED_CASES=13 MODEL_GENERATIONS=1')
        print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
        print('C636_RESULT='+READY_RESULT)
        return 0
    except (Hold,evidence.Hold,parent.Hold,shadow.Hold,bounded.Hold,ValueError,TypeError) as exc:
        print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
        print('C636_RESULT=HOLD_'+str(exc))
        return 1

if __name__=='__main__':
    sys.exit(main())
