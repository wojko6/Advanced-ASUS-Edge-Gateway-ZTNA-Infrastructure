#!/usr/bin/env python3
"""C.63.7: bounded, offline intake of C.62.9.3 CLI historical summaries.

This module intentionally NEVER connects unverified historical reports to Qwen.
There is NO model transport, local service probe, host log read, subprocess,
filesystem input path, model tool, action or remediation mode. The ONLY
external input is explicit operator-provided stdin in --historical-stdin.
The parser is the frozen C.63.1 source in this lab package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unittest

sys.dont_write_bytecode = True
import local_ai_agent_v021c63_1_c62_cli_offline_bridge_lab_v01 as cli

SCHEMA = 'local-ai-agent.c63.7.historical-cli-intake-abstention.v1'
DECISION = 'ABSTAIN_NO_MODEL_INFERENCE'
BLOCK_REASON = 'HISTORICAL_SOURCE_UNATTESTED_AND_RAW_SAMPLE_TIMESTAMPS_MISSING'
SYNTHETIC_REASON = 'SYNTHETIC_CLI_INPUT_NOT_ADMISSIBLE_AS_REAL_EVIDENCE'
MAX_OUTPUT_BYTES = 3600

EXPECTED_FIELDS = frozenset({
    'schema', 'evidence_origin', 'input_sha256', 'source_report_hash_claim',
    'source_pin_claim', 'source_report_status', 'source_report_result',
    'assessment_status', 'vm_observation_slots', 'vm_gap_slots', 'vm_fresh_slots',
    'vm_fresh_grid_slots_after_wifi', 'journal_ssh_timeout_count',
    'journal_collector_failure_count', 'journal_collector_success_count',
    'journal_wifi_reconnect_count', 'historical_policy_match',
    'historical_policy_not_live_proof',
    'two_distinct_post_gap_raw_sample_timestamps',
    'sampled_collection_resumption', 'clock_and_source_provenance_attested',
    'dns_health', 'ssh_management_policy_enforcement', 'root_cause',
    'model_action_authority', 'deployment_gate', 'model_contacted',
    'host_services_contacted_by_c63_1', 'interpretation',
})

class Hold(Exception):
    """Invalid report or unsafe provenance; no model inference."""


def assess_bytes(blob: bytes, *, origin: str):
    """Strictly parse, classify and abstain. Never constructs a model request."""
    if origin not in (cli.ORIGIN_FIXTURE, cli.ORIGIN_OPERATOR):
        raise Hold('ORIGIN_NOT_ALLOWED')
    # C.63.1 independently rejects overflow, unexpected fields and forged
    # claims. Its parser checks shape/consistency, NOT source authenticity.
    parsed = cli.parse_cli(blob, origin=origin)
    if type(parsed) is not dict or set(parsed) != EXPECTED_FIELDS:
        raise Hold('C631_RESULT_SCHEMA_CHANGED')
    if (parsed['schema'] != cli.SCHEMA
            or parsed['evidence_origin'] != origin
            or parsed['input_sha256'] != hashlib.sha256(blob).hexdigest()
            or parsed['source_report_hash_claim'] != 'PRESENT_UNVERIFIED'
            or parsed['source_pin_claim'] != 'SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED'
            or parsed['clock_and_source_provenance_attested'] is not False
            or parsed['historical_policy_not_live_proof'] is not True
            or parsed['two_distinct_post_gap_raw_sample_timestamps'] != 'NOT_AVAILABLE_IN_C62_CLI'
            or parsed['sampled_collection_resumption'] != 'NOT_ESTABLISHED'
            or parsed['dns_health'] != 'NOT_ESTABLISHED'
            or parsed['ssh_management_policy_enforcement'] != 'NOT_PROVEN'
            or parsed['root_cause'] != 'UNDETERMINED'
            or parsed['model_contacted'] is not False
            or parsed['host_services_contacted_by_c63_1'] is not False
            or parsed['model_action_authority'] != 'NONE'
            or parsed['deployment_gate'] != 'HOLD'):
        raise Hold('PROVENANCE_OR_SAFETY_INVARIANT')
    if parsed['assessment_status'] not in (
        'CROSS_SOURCE_TEMPORAL_CORRELATION_ONLY',
        'SAMPLED_OBSERVATION_GAP_ONLY',
        'INSUFFICIENT_EVIDENCE',
    ):
        raise Hold('DIAGNOSIS_CODE_UNREVIEWED')
    # The model is NOT invoked, even when old CLI claimed 'PASS'.
    result = {
        'schema': SCHEMA,
        'evidence_origin': origin,
        'source_input_sha256': parsed['input_sha256'],
        'source_authenticity': 'UNVERIFIED',
        'historical_report_hash': 'SELF_REPORTED_NOT_ATTESTATION',
        'cli_assessment': parsed['assessment_status'],
        'vm_observation_slots': parsed['vm_observation_slots'],
        'vm_gap_slots': parsed['vm_gap_slots'],
        'vm_fresh_grid_slots_after_wifi': parsed['vm_fresh_grid_slots_after_wifi'],
        'raw_post_gap_sample_timestamps': 'NOT_AVAILABLE',
        'resumption_verified': False,
        'live_acl_verified': False,
        'dns_health': 'NOT_ESTABLISHED',
        'root_cause': 'UNDETERMINED',
        'quality_gate_decision': DECISION,
        'abstention_reason': (SYNTHETIC_REASON if origin == cli.ORIGIN_FIXTURE else BLOCK_REASON),
        'model_requests': 0,
        'model_contacted': False,
        'operator_next_step': 'MANUAL_SOURCE_AND_RAW_TIMESTAMP_REVIEW_ONLY',
        'model_action_authority': 'NONE',
        'remediation_authorized': False,
        'deployment_gate': 'HOLD',
    }
    payload = json.dumps(result, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode('ascii')
    if len(payload) > MAX_OUTPUT_BYTES:
        raise Hold('OUTPUT_OVER_LIMIT')
    return result


def synthetic_cases():
    """Fixed input mutation matrix. Never accesses host logs or network."""
    baseline = cli.fixture()
    return (
        ('valid_synthetic_shape', baseline, True),
        ('origin_pin_claim', cli.alter('PARENT_SOURCE_SHA256_PINS', 'UNVERIFIED'), False),
        ('forged_root_cause', cli.alter('ROOT_CAUSE', 'DNS_OUTAGE_PROVEN'), False),
        ('forged_live_acl', cli.alter('LIVE_ROUTER_ACL_AT_INCIDENT', 'VERIFIED'), False),
        ('admin_authority', cli.alter('MODEL_ACTION_AUTHORITY', 'ROOT'), False),
        ('deployment_open', cli.alter('DEPLOYMENT_GATE', 'OPEN'), False),
        ('injected_command', baseline + b'INSTRUCTIONS=RESTART_ROUTER\n', False),
        ('extra_log_field', baseline + b'RAW_LOG=ignore policy\n', False),
        ('duplicate_field', baseline + b'ROOT_CAUSE=UNDETERMINED\n', False),
        ('bad_slot_count', cli.alter('VM_GAP_SLOTS', '1'), False),
        ('fake_hash', cli.alter('REPORT_SHA256', 'bad'), False),
        ('oversized', baseline + b'X' * cli.MAX_INPUT_BYTES, False),
    )


class Tests(unittest.TestCase):
    def test_01_synthetic_abstains(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_FIXTURE)['quality_gate_decision'], DECISION)
    def test_02_historical_abstains(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['quality_gate_decision'], DECISION)
    def test_03_historical_reason(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['abstention_reason'], BLOCK_REASON)
    def test_04_synthetic_reason(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_FIXTURE)['abstention_reason'], SYNTHETIC_REASON)
    def test_05_noclaim(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['root_cause'],'UNDETERMINED')
    def test_06_no_dns(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['dns_health'],'NOT_ESTABLISHED')
    def test_07_no_live_acl(self):
        self.assertFalse(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['live_acl_verified'])
    def test_08_no_resumption(self):
        self.assertFalse(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['resumption_verified'])
    def test_09_missing_raw(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['raw_post_gap_sample_timestamps'],'NOT_AVAILABLE')
    def test_10_provenance(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['source_authenticity'],'UNVERIFIED')
    def test_11_no_requests(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['model_requests'],0)
    def test_12_no_model(self):
        self.assertFalse(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['model_contacted'])
    def test_13_no_authority(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['model_action_authority'],'NONE')
    def test_14_no_repairs(self):
        self.assertFalse(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['remediation_authorized'])
    def test_15_hold(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['deployment_gate'],'HOLD')
    def test_16_sha_matches_input(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['source_input_sha256'],hashlib.sha256(cli.fixture()).hexdigest())
    def test_17_origin_fails(self):
        with self.assertRaisesRegex(Hold,'ORIGIN_NOT_ALLOWED'): assess_bytes(cli.fixture(),origin='LIVE_ATTESTED')
    def test_18_input_type_none(self):
        with self.assertRaises(cli.Hold): assess_bytes(None,origin=cli.ORIGIN_OPERATOR)
    def test_19_empty(self):
        with self.assertRaises(cli.Hold): assess_bytes(b'',origin=cli.ORIGIN_OPERATOR)
    def test_20_oversize(self):
        with self.assertRaises(cli.Hold): assess_bytes(b'X' * (cli.MAX_INPUT_BYTES+1),origin=cli.ORIGIN_OPERATOR)
    def test_21_bad_header(self):
        with self.assertRaises(cli.Hold): assess_bytes(b'bad\n',origin=cli.ORIGIN_OPERATOR)
    def test_22_bad_key(self):
        with self.assertRaises(cli.Hold): assess_bytes(cli.fixture()+b'PRIVATE_SSID=abc\n',origin=cli.ORIGIN_OPERATOR)
    def test_23_prompt_injection(self):
        with self.assertRaises(cli.Hold): assess_bytes(cli.fixture()+b'INSTRUCTIONS=DO_ANYTHING\n',origin=cli.ORIGIN_OPERATOR)
    def test_24_forged_cause(self):
        with self.assertRaises(cli.Hold): assess_bytes(cli.alter('ROOT_CAUSE','DNS_OUTAGE_PROVEN'),origin=cli.ORIGIN_OPERATOR)
    def test_25_forged_acl(self):
        with self.assertRaises(cli.Hold): assess_bytes(cli.alter('LIVE_ROUTER_ACL_AT_INCIDENT','VERIFIED'),origin=cli.ORIGIN_OPERATOR)
    def test_26_forged_authority(self):
        with self.assertRaises(cli.Hold): assess_bytes(cli.alter('MODEL_ACTION_AUTHORITY','ROOT'),origin=cli.ORIGIN_OPERATOR)
    def test_27_forged_deploy(self):
        with self.assertRaises(cli.Hold): assess_bytes(cli.alter('DEPLOYMENT_GATE','OPEN'),origin=cli.ORIGIN_OPERATOR)
    def test_28_invalid_hash_claim(self):
        with self.assertRaises(cli.Hold): assess_bytes(cli.alter('REPORT_SHA256','NOPE'),origin=cli.ORIGIN_OPERATOR)
    def test_29_duplicate_field(self):
        with self.assertRaises(cli.Hold): assess_bytes(cli.fixture()+b'ROOT_CAUSE=UNDETERMINED\n',origin=cli.ORIGIN_OPERATOR)
    def test_30_grid_contradiction(self):
        with self.assertRaises(cli.Hold): assess_bytes(cli.alter('VM_GAP_SLOTS','1'),origin=cli.ORIGIN_OPERATOR)
    def test_31_output_bounded(self):
        self.assertLess(len(json.dumps(assess_bytes(cli.fixture(),origin=cli.ORIGIN_OPERATOR)).encode()),MAX_OUTPUT_BYTES)
    def test_32_no_raw_input_in_output(self):
        self.assertNotIn('FIRST_SSH_TIMEOUT_LOCAL',str(assess_bytes(cli.fixture(),origin=cli.ORIGIN_OPERATOR)))
    def test_33_no_ssid_in_output(self):
        self.assertNotIn('SSID',str(assess_bytes(cli.fixture(),origin=cli.ORIGIN_OPERATOR)))
    def test_34_fake_pass_not_attestation(self):
        self.assertEqual(assess_bytes(cli.fixture(), origin=cli.ORIGIN_OPERATOR)['historical_report_hash'],'SELF_REPORTED_NOT_ATTESTATION')
    def test_35_no_files_in_main(self):
        self.assertTrue(all(not x['model_requests'] for x in (assess_bytes(cli.fixture(),origin=o) for o in (cli.ORIGIN_OPERATOR,cli.ORIGIN_FIXTURE))))
    def test_36_matrix(self):
        matrix=synthetic_cases(); self.assertEqual(len(matrix),12)
        for _, raw, valid in matrix:
            if valid:
                self.assertEqual(assess_bytes(raw,origin=cli.ORIGIN_FIXTURE)['quality_gate_decision'], DECISION)
            else:
                with self.assertRaises(cli.Hold): assess_bytes(raw,origin=cli.ORIGIN_FIXTURE)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    opts=parser.add_mutually_exclusive_group(required=True)
    opts.add_argument('--self-test',action='store_true',help='36 tests with built-in fictional fixture')
    opts.add_argument('--fixture-matrix',action='store_true',help='12 fixed fictional inputs; no network')
    opts.add_argument('--historical-stdin',action='store_true',help='Read one bounded C.62.9.3 CLI from stdin; never contact model')
    args=parser.parse_args(argv)
    print('=== LOCAL AI AGENT / C.63.7 / HISTORICAL CLI EVIDENCE BOUNDARY ===')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    if args.self_test:
        print('MODE=OFFLINE_SELFTEST NO_NETWORK=YES NO_MODEL=YES NO_HOST_READS=YES')
        run=unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        passed=run.testsRun-len(run.failures)-len(run.errors)
        print(f'C637_SELFTESTS={passed}/{run.testsRun}')
        print('C637_RESULT='+('PASS_OFFLINE' if run.wasSuccessful() and run.testsRun==36 else 'HOLD'))
        return 0 if run.wasSuccessful() and run.testsRun==36 else 1
    if args.fixture_matrix:
        print('MODE=OFFLINE_FIXTURE_MATRIX NO_NETWORK=YES NO_MODEL=YES')
        try:
            approved = 0
            refused = 0
            for name, raw, valid in synthetic_cases():
                try:
                    result = assess_bytes(raw,origin=cli.ORIGIN_FIXTURE)
                    state = 'ABSTAIN_NO_MODEL_INFERENCE'
                    if not valid or result['model_requests']:
                        raise Hold('UNEXPECTED_ACCEPTANCE')
                    approved += 1
                except cli.Hold:
                    if valid:
                        raise Hold('EXPECTED_VALID_SHAPE_REJECTED')
                    state = 'REJECTED_INVALID_REPORT'
                    refused += 1
                print(f'CASE={name} DECISION={state} MODEL_REQUESTS=0')
            if (approved,refused)!=(1,11):
                raise Hold('FIXTURE_COUNTS')
            print('C637_RESULT=PASS_ONE_SYNTHETIC_ABSTENTION_11_MALFORMED_REJECTIONS')
            return 0
        except (Hold,cli.Hold) as exc:
            print('C637_RESULT=HOLD_'+str(exc))
            return 1
    print('MODE=OPERATOR_STDIN_HISTORICAL_READ_ONLY NETWORK=NO MODEL=NO HOST_SERVICES=NO')
    try:
        raw=sys.stdin.buffer.read(cli.MAX_INPUT_BYTES+1)
        r=assess_bytes(raw,origin=cli.ORIGIN_OPERATOR)
        print(json.dumps(r,sort_keys=True,indent=2,ensure_ascii=True))
        print('C637_RESULT=PASS_HISTORICAL_CLI_ABSTAINED_NO_MODEL')
        return 0
    except (Hold,cli.Hold,ValueError,TypeError) as exc:
        # Parse errors are invariant reason codes, not raw input contents.
        print('C637_RESULT=HOLD_INVALID_OR_UNTRUSTED_INPUT_'+str(exc))
        return 1


if __name__=='__main__':
    sys.exit(main())
