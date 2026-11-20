#!/usr/bin/env python3
"""C.63.2: deterministic offline bounded SHADOW packet + strict response gate.

All CLI modes are offline. Never contacts Qwen, localhost, router, journal,
VictoriaMetrics or any external service. No host actions or autonomous repairs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unittest

import local_ai_agent_v021c63_1_c62_cli_offline_bridge_lab_v01 as bridge

sys.dont_write_bytecode = True
PACKET_SCHEMA = 'local-ai-agent.c63.2.bounded-shadow-packet.v1'
RESPONSE_SCHEMA = 'local-ai-agent.c63.2.bounded-shadow-response.v1'
MAX_PACKET_BYTES = 4096
MAX_RESPONSE_BYTES = 1024
HASH_RE = re.compile(r'[0-9a-f]{64}\Z')
ASSESSMENTS = {
    'CROSS_SOURCE_TEMPORAL_CORRELATION_ONLY': 'TEMPORAL_CORRELATION_ONLY',
    'SAMPLED_OBSERVATION_GAP_ONLY': 'OBSERVATION_GAP_ONLY',
    'INSUFFICIENT_EVIDENCE': 'INSUFFICIENT_EVIDENCE',
}
NEXT_CHECKS = ('MANUAL_EVIDENCE_REVIEW_ONLY', 'REQUEST_OPERATOR_APPROVED_ACL_VERIFICATION')
RESPONSE_KEYS = frozenset({
    'schema', 'input_sha256', 'assessment_code', 'next_check_code',
    'root_cause', 'model_action_authority', 'remediation_authorized',
})

class Hold(Exception):
    """Fail closed on a packet or model response outside the declared contract."""


def packet_for_report(report):
    """Bounded facts from C.63.1; no raw log lines, IPs or host identifiers."""
    if not isinstance(report, dict):
        raise Hold('INVALID_REPORT')
    status = report.get('assessment_status')
    if status not in ASSESSMENTS:
        raise Hold('INVALID_ASSESSMENT')
    if (report.get('model_action_authority') != 'NONE'
        or report.get('deployment_gate') != 'HOLD'
        or report.get('root_cause') != 'UNDETERMINED'
        or report.get('dns_health') != 'NOT_ESTABLISHED'
        or report.get('sampled_collection_resumption') != 'NOT_ESTABLISHED'
        or report.get('clock_and_source_provenance_attested') is not False
        or report.get('ssh_management_policy_enforcement') != 'NOT_PROVEN'
        or report.get('two_distinct_post_gap_raw_sample_timestamps') != 'NOT_AVAILABLE_IN_C62_CLI'
        or report.get('model_contacted') is not False
        or report.get('host_services_contacted_by_c63_1') is not False
        or report.get('source_pin_claim') != 'SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED'):
        raise Hold('C631_SAFETY_INVARIANT')
    origin=report.get('evidence_origin')
    if origin not in (bridge.ORIGIN_FIXTURE,bridge.ORIGIN_OPERATOR):
        raise Hold('INVALID_EVIDENCE_ORIGIN')
    digest=report.get('input_sha256')
    if not isinstance(digest,str) or not HASH_RE.fullmatch(digest):
        raise Hold('INVALID_EVIDENCE_FINGERPRINT')
    # Only explicitly selected, typed, bounded counters are eligible.
    counters={}
    for k in ('vm_fresh_slots','vm_gap_slots','journal_ssh_timeout_count',
              'journal_collector_failure_count','journal_wifi_reconnect_count'):
        value=report.get(k)
        if type(value) is not int or not 0 <= value <= 100000:
            raise Hold('INVALID_COUNTER_'+k)
        counters[k]=value
    fields={
        'schema':PACKET_SCHEMA,
        'source_type':origin,
        'input_sha256':digest,
        'assessment_code':ASSESSMENTS[status],
        'facts':{
            **counters,
            'dns_health':'NOT_ESTABLISHED',
            'root_cause':'UNDETERMINED',
            'sampled_collection_resumption':'NOT_ESTABLISHED',
            'live_acl':'NOT_VERIFIED',
            'historical_policy_is_current_proof':False,
        },
        'allowed_next_check_codes':list(NEXT_CHECKS),
        'response_schema':RESPONSE_SCHEMA,
        'model_action_authority':'NONE',
        'remediation_authorized':False,
        'deployment_gate':'HOLD',
        'source_provenance_attested':False,
    }
    encoded=json.dumps(fields,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode('ascii')
    if len(encoded)>MAX_PACKET_BYTES:
        raise Hold('PACKET_TOO_LARGE')
    return fields


def response_for_fixture(packet):
    """Valid response for synthetic tests only; never a real model output."""
    return {
        'schema':RESPONSE_SCHEMA,
        'input_sha256':packet['input_sha256'],
        'assessment_code':packet['assessment_code'],
        'next_check_code':'MANUAL_EVIDENCE_REVIEW_ONLY',
        'root_cause':'UNDETERMINED',
        'model_action_authority':'NONE',
        'remediation_authorized':False,
    }


def reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('DUPLICATE_JSON_PROPERTY')
        result[key] = value
    return result


def reject_nonstandard_json_constant(value):
    raise ValueError('NONSTANDARD_JSON_CONSTANT')


def validate_response(raw, packet):
    """Validate hypothetical SHADOW response, never execute its text."""
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_RESPONSE_BYTES:
        raise Hold('RESPONSE_SIZE_INVALID')
    try:
        txt=raw.decode('ascii')
        response=json.loads(txt, object_pairs_hook=reject_duplicate_pairs, parse_constant=reject_nonstandard_json_constant)
    except (UnicodeDecodeError,ValueError) as exc:
        raise Hold('RESPONSE_NOT_ASCII_JSON') from exc
    if type(response) is not dict or set(response)!=RESPONSE_KEYS:
        raise Hold('RESPONSE_SCHEMA_KEYS')
    for key,value in {
        'schema':RESPONSE_SCHEMA,
        'input_sha256':packet['input_sha256'],
        'assessment_code':packet['assessment_code'],
        'root_cause':'UNDETERMINED',
        'model_action_authority':'NONE',
        'remediation_authorized':False,
    }.items():
        if type(response[key]) is not type(value) or response[key]!=value:
            raise Hold('RESPONSE_INVARIANT_'+key)
    if response['next_check_code'] not in NEXT_CHECKS:
        raise Hold('RESPONSE_NEXT_CHECK_NOT_ALLOWED')
    return {
        'schema':RESPONSE_SCHEMA,
        'input_sha256':packet['input_sha256'],
        'accepted_assessment_code':packet['assessment_code'],
        'accepted_next_check_code':response['next_check_code'],
        'result':'PASS_SHADOW_CODES_ONLY',
        'model_action_authority':'NONE',
        'deployment_gate':'HOLD',
    }


def fixture_packet():
    return packet_for_report(bridge.parse_cli(bridge.fixture(),origin=bridge.ORIGIN_FIXTURE))


class Tests(unittest.TestCase):
    def setUp(self):
        self.packet=fixture_packet()
        self.response=response_for_fixture(self.packet)
    def encoded(self, obj=None):
        return json.dumps(self.response if obj is None else obj,separators=(',',':')).encode('ascii')
    def expect_hold(self, obj, code):
        with self.assertRaisesRegex(Hold,code):
            validate_response(self.encoded(obj),self.packet)

    def test_01_valid_packet(self):
        self.assertEqual(self.packet['assessment_code'],'TEMPORAL_CORRELATION_ONLY')
    def test_02_no_authority(self):
        self.assertEqual(self.packet['model_action_authority'],'NONE')
    def test_03_holds_deployment(self):
        self.assertEqual(self.packet['deployment_gate'],'HOLD')
    def test_04_no_private_raw_fields(self):
        s=json.dumps(self.packet)
        for x in ('SSID','MAC','hostname','raw_log','192.168','ssh_command'):
            self.assertNotIn(x,s)
    def test_05_no_pretend_provenance(self):
        self.assertFalse(self.packet['source_provenance_attested'])
    def test_06_allows_safe_response(self):
        self.assertEqual(validate_response(self.encoded(),self.packet)['result'],'PASS_SHADOW_CODES_ONLY')
    def test_reject_duplicate_json_key(self):
        raw=self.encoded().decode('ascii')
        raw=raw.replace('"root_cause":"UNDETERMINED"', '"root_cause":"UNDETERMINED","root_cause":"UNDETERMINED"')
        with self.assertRaises(Hold):
            validate_response(raw.encode('ascii'),self.packet)

    def test_reject_nonstandard_json_constant(self):
        raw=self.encoded().decode('ascii').replace('"root_cause":"UNDETERMINED"','"root_cause":NaN')
        with self.assertRaises(Hold):
            validate_response(raw.encode('ascii'),self.packet)

    def test_07_secondary_manual_choice(self):
        r=dict(self.response,next_check_code='REQUEST_OPERATOR_APPROVED_ACL_VERIFICATION')
        self.assertEqual(validate_response(self.encoded(r),self.packet)['result'],'PASS_SHADOW_CODES_ONLY')
    def test_08_unrecognized_next_action(self):
        self.expect_hold(dict(self.response,next_check_code='RESTART_ROUTER'),'RESPONSE_NEXT_CHECK_NOT_ALLOWED')
    def test_09_dangerous_extra_key(self):
        self.expect_hold(dict(self.response, shell='sudo reboot'),'RESPONSE_SCHEMA_KEYS')
    def test_10_false_diagnosis(self):
        self.expect_hold(dict(self.response,root_cause='DNS_OUTAGE_PROVEN'),'RESPONSE_INVARIANT_root_cause')
    def test_11_remediation_true(self):
        self.expect_hold(dict(self.response,remediation_authorized=True),'RESPONSE_INVARIANT_remediation_authorized')
    def test_12_remediation_string(self):
        self.expect_hold(dict(self.response,remediation_authorized='false'),'RESPONSE_INVARIANT_remediation_authorized')
    def test_13_wrong_fingerprint(self):
        self.expect_hold(dict(self.response,input_sha256='0'*64),'RESPONSE_INVARIANT_input_sha256')
    def test_14_change_assessment(self):
        self.expect_hold(dict(self.response,assessment_code='DNS_OUTAGE_PROVEN'),'RESPONSE_INVARIANT_assessment_code')
    def test_15_wrong_schema(self):
        self.expect_hold(dict(self.response,schema='evil'),'RESPONSE_INVARIANT_schema')
    def test_16_missing_field(self):
        d=dict(self.response);d.pop('model_action_authority');self.expect_hold(d,'RESPONSE_SCHEMA_KEYS')
    def test_17_code_instead_of_json(self):
        with self.assertRaisesRegex(Hold,'RESPONSE_NOT_ASCII_JSON'):
            validate_response(b'```json\n{}\n```',self.packet)
    def test_18_non_ascii(self):
        with self.assertRaisesRegex(Hold,'RESPONSE_NOT_ASCII_JSON'):
            validate_response(b'\xff',self.packet)
    def test_19_oversized(self):
        with self.assertRaisesRegex(Hold,'RESPONSE_SIZE_INVALID'):
            validate_response(b'X'*1025,self.packet)
    def test_20_empty(self):
        with self.assertRaisesRegex(Hold,'RESPONSE_SIZE_INVALID'):
            validate_response(b'',self.packet)
    def test_21_no_model_input_calls(self):
        self.assertEqual(self.packet['facts']['live_acl'],'NOT_VERIFIED')
    def test_22_status_spoof(self):
        p=bridge.parse_cli(bridge.fixture(),origin=bridge.ORIGIN_FIXTURE)
        p['root_cause']='KNOWN'
        with self.assertRaisesRegex(Hold,'C631_SAFETY_INVARIANT'):
            packet_for_report(p)
    def test_23_old_provenance_spoof(self):
        p=bridge.parse_cli(bridge.fixture(),origin=bridge.ORIGIN_FIXTURE)
        p['source_pin_claim']='INDEPENDENTLY_VERIFIED'
        with self.assertRaisesRegex(Hold,'C631_SAFETY_INVARIANT'):
            packet_for_report(p)
    def test_24_invalid_origin(self):
        p=bridge.parse_cli(bridge.fixture(),origin=bridge.ORIGIN_FIXTURE)
        p['evidence_origin']='LIVE_TRUSTED'
        with self.assertRaisesRegex(Hold,'INVALID_EVIDENCE_ORIGIN'):
            packet_for_report(p)
    def test_25_malformed_fingerprint(self):
        p=bridge.parse_cli(bridge.fixture(),origin=bridge.ORIGIN_FIXTURE)
        p['input_sha256']='aaa'
        with self.assertRaisesRegex(Hold,'INVALID_EVIDENCE_FINGERPRINT'):
            packet_for_report(p)
    def test_26_counter_string(self):
        p=bridge.parse_cli(bridge.fixture(),origin=bridge.ORIGIN_FIXTURE)
        p['journal_ssh_timeout_count']='23'
        with self.assertRaisesRegex(Hold,'INVALID_COUNTER'):
            packet_for_report(p)
    def test_27_counter_boolean(self):
        p=bridge.parse_cli(bridge.fixture(),origin=bridge.ORIGIN_FIXTURE)
        p['journal_ssh_timeout_count']=True
        with self.assertRaisesRegex(Hold,'INVALID_COUNTER'):
            packet_for_report(p)
    def test_28_stdin_fixture_evidence(self):
        self.assertEqual(self.packet['source_type'],bridge.ORIGIN_FIXTURE)
    def test_29_fingerprint_is_input_bytes(self):
        self.assertEqual(self.packet['input_sha256'],hashlib.sha256(bridge.fixture()).hexdigest())
    def test_30_no_auto_grant(self):
        self.assertFalse(self.packet['remediation_authorized'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    x=p.add_mutually_exclusive_group(required=True)
    x.add_argument('--self-test',action='store_true')
    x.add_argument('--fixture-matrix',action='store_true')
    x.add_argument('--packet-stdin',action='store_true',help='Historical C62.9.3 CLI text from operator; offline')
    args=p.parse_args(argv)
    print('=== LOCAL AI AGENT C.63.2 / BOUNDED SHADOW CONTRACT ===')
    print('MODE=OFFLINE NO_NETWORK=YES NO_MODEL=YES NO_HOST_READS=YES')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    if args.self_test:
        result=unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        good=result.testsRun-len(result.failures)-len(result.errors)
        print(f'C632_SELFTESTS={good}/{result.testsRun}')
        print('C632_RESULT='+('PASS_SYNTHETIC_ONLY' if result.wasSuccessful() and result.testsRun==32 else 'HOLD'))
        return 0 if result.wasSuccessful() and result.testsRun==32 else 1
    try:
        if args.fixture_matrix:
            pkt=fixture_packet()
            print('INPUT_ORIGIN=SYNTHETIC_ONLY')
        else:
            raw=sys.stdin.buffer.read(bridge.MAX_INPUT_BYTES+1)
            parsed=bridge.parse_cli(raw,origin=bridge.ORIGIN_OPERATOR)
            pkt=packet_for_report(parsed)
            print('INPUT_ORIGIN=OPERATOR_RECONSTRUCTED_OR_STORED_UNVERIFIED_HISTORICAL_ONLY')
        print(json.dumps(pkt,sort_keys=True,ensure_ascii=True,indent=2))
        print('C632_RESULT=PASS_BOUNDED_PACKET_ONLY_NO_MODEL')
        return 0
    except (Hold,bridge.Hold) as e:
        print('C632_RESULT=HOLD_'+str(e))
        return 1

if __name__=='__main__':
    raise SystemExit(main())
