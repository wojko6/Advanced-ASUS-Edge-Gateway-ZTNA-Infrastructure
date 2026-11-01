#!/usr/bin/env python3
"""C.63.12 read-only comparison of C.63.11 VM history to an synthetic reference grid.

The reference grid comes from the manually supplied C.62.9.3 summary, NOT an
independent read or authenticated source. No raw logs, no model, no commands,
no router and no writes. Manual --historical-vm-parity-readonly makes exactly the
same eight bounded VM GETs as C.63.11; --fixture-matrix and --self-test offline.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import sys
import unittest

import local_ai_agent_v021c63_11_historical_vm_window_readonly_lab_v01 as source

sys.dont_write_bytecode = True
SCHEMA = 'local-ai-agent.c63.12.vm-synthetic reference-grid-parity.v1'
REF_GRID = ('DNS_GUARD_MODE_SAMPLED_ONLY',) * 2 + ('INSUFFICIENT_EVIDENCE',) * 4 + ('DNS_GUARD_MODE_SAMPLED_ONLY',) * 2
REF_MODES = ('LOCAL',) * 2 + ('UNVERIFIED',) * 4 + ('LOCAL',) * 2
SOURCE_KEYS = frozenset(('schema','evidence_origin','window_local','start_epoch_utc','end_epoch_utc',
    'step_seconds','evaluations','get_requests_max','non_atomic_gets','source_identity',
    'source_authenticity','raw_timestamp_basis','per_slot','classification','qualified_slots',
    'unqualified_slots','candidate_unqualified_slots','raw_sample_pair_post_window_advance_observed',
    'sampling_recovered','telemetry_outage_proven','dns_health','root_cause',
    'quality_gate_decision','model_requests','model_action_authority','remediation_authorized',
    'deployment_gate'))
SLOT_KEYS=frozenset(('evaluation_epoch_utc','classification','sampled_mode','gaps',
    'incomplete_value_timestamp_pairs','unpaired_source_raw_timestamps_utc','raw_sample_timestamps_utc'))
KEYS=frozenset(('local','bootstrap','valid','collection'))
ALLOWED_CLASSES=frozenset(('DNS_GUARD_MODE_SAMPLED_ONLY','INSUFFICIENT_EVIDENCE','INVALID_DNS_GUARD_STATE_SAMPLED'))
ALLOWED_MODES=frozenset(('LOCAL','BOOTSTRAP','UNVERIFIED','INVALID'))

class Hold(Exception):
    pass

def _finite_decimal(s):
    if type(s) is not str or not 1 <= len(s) <= 32 or not s.isascii():
        raise Hold('RAW_TIMESTAMP_INVALID')
    try:
        d=Decimal(s)
    except InvalidOperation as exc:
        raise Hold('RAW_TIMESTAMP_INVALID') from exc
    if not d.is_finite() or not Decimal('1577836800') <= d <= Decimal('4102444800'):
        raise Hold('RAW_TIMESTAMP_INVALID')
    return d

def validate_report(r):
    if type(r) is not dict or frozenset(r) != SOURCE_KEYS:
        raise Hold('SOURCE_SCHEMA_INVALID')
    invariants = {
        'schema':source.SCHEMA,
        'evidence_origin':'PUBLIC_SYNTHETIC_VM_QUERY_RANGE_FIXTURE',
        'window_local':'2030-02-13 09:00–09:35 Europe/Warsaw',
        'start_epoch_utc':source.START,
        'end_epoch_utc':source.END,
        'step_seconds':300,
        'evaluations':8,
        'get_requests_max':8,
        'non_atomic_gets':True,
        'source_identity':'LOCAL_VM_ENDPOINT_127_0_0_1_8428',
        'source_authenticity':'NOT_CRYPTOGRAPHICALLY_ATTESTED',
        'raw_timestamp_basis':'VM_TIMESTAMP_FUNCTION_VALUE_NOT_QUERY_EVALUATION_TIME',
        'sampling_recovered':'NOT_ESTABLISHED',
        'telemetry_outage_proven':False,
        'dns_health':'NOT_ESTABLISHED',
        'root_cause':'UNDETERMINED',
        'quality_gate_decision':'ABSTAIN_NO_MODEL_INFERENCE',
        'model_requests':0,
        'model_action_authority':'NONE',
        'remediation_authorized':False,
        'deployment_gate':'HOLD',
    }
    if any(type(r[k]) is not type(v) or r[k] != v for k,v in invariants.items()):
        raise Hold('SOURCE_SECURITY_INVARIANT_INVALID')
    slots=r['per_slot']
    if type(slots) is not list or len(slots) != 8:
        raise Hold('SOURCE_SLOTS_INVALID')
    classes, modes=[],[]
    qualified=0
    for i,slot in enumerate(slots):
        if type(slot) is not dict or frozenset(slot) != SLOT_KEYS:
            raise Hold('SLOT_SCHEMA_INVALID')
        t=source.START+source.STEP*i
        if type(slot['evaluation_epoch_utc']) is not int or slot['evaluation_epoch_utc'] != t:
            raise Hold('EVALUATION_EPOCH_INVALID')
        c,m=slot['classification'],slot['sampled_mode']
        if type(c) is not str or c not in ALLOWED_CLASSES or type(m) is not str or m not in ALLOWED_MODES:
            raise Hold('SLOT_CLASSIFICATION_INVALID')
        is_qualified=c=='DNS_GUARD_MODE_SAMPLED_ONLY'
        if is_qualified != (m in ('LOCAL','BOOTSTRAP')):
            raise Hold('SLOT_CLASS_MODE_CONTRADICTION')
        if type(slot['gaps']) is not list or len(slot['gaps'])>12 or any(type(x) is not str or len(x)>80 or not x.isascii() for x in slot['gaps']):
            raise Hold('GAP_CODES_INVALID')
        if is_qualified and slot['gaps']:
            raise Hold('QUALIFIED_WITH_GAP')
        if type(slot['incomplete_value_timestamp_pairs']) is not list or any(k not in KEYS for k in slot['incomplete_value_timestamp_pairs']):
            raise Hold('PAIR_DIAGNOSTICS_INVALID')
        if len(set(slot['incomplete_value_timestamp_pairs']))!=len(slot['incomplete_value_timestamp_pairs']):
            raise Hold('PAIR_DIAGNOSTICS_INVALID')
        times=slot['raw_sample_timestamps_utc']; extra=slot['unpaired_source_raw_timestamps_utc']
        if type(times) is not dict or frozenset(times)!=KEYS or type(extra) is not dict or frozenset(extra)!=frozenset(slot['incomplete_value_timestamp_pairs']):
            raise Hold('TIMESTAMP_SHAPE_INVALID')
        for key, value in times.items():
            if value is not None:
                raw=_finite_decimal(value)
                if raw > Decimal(t+5): raise Hold('RAW_TIMESTAMP_IN_FUTURE')
            if is_qualified and value is None:
                raise Hold('QUALIFIED_MISSING_RAW_TIMESTAMP')
        for value in extra.values():
            if value is not None: _finite_decimal(value)
        qualified+=int(is_qualified)
        classes.append(c); modes.append(m)
    if any(type(r[k]) is not int for k in ('qualified_slots','unqualified_slots','candidate_unqualified_slots')):
        raise Hold('SOURCE_COUNTS_INVALID')
    if r['qualified_slots'] != qualified or r['unqualified_slots'] != len(slots)-qualified:
        raise Hold('SOURCE_COUNTS_MISMATCH')
    if type(r['classification']) is not str or len(r['classification'])>100:
        raise Hold('SOURCE_SUMMARY_INVALID')
    if type(r['raw_sample_pair_post_window_advance_observed']) is not bool:
        raise Hold('SOURCE_SUMMARY_INVALID')
    return classes,modes

def compare_report(report):
    classes,modes=validate_report(report)
    matched=(tuple(classes)==REF_GRID and tuple(modes)==REF_MODES)
    distinct_after_window = False
    if matched:
        first=report['per_slot'][6]['raw_sample_timestamps_utc']
        second=report['per_slot'][7]['raw_sample_timestamps_utc']
        distinct_after_window=all(_finite_decimal(first[key]) < _finite_decimal(second[key]) for key in KEYS)
        if report['raw_sample_pair_post_window_advance_observed'] is not distinct_after_window:
            raise Hold('RAW_ADVANCE_CLAIM_CONTRADICTS_REPORTED_TIMESTAMPS')
    # No endorsement of either source's provenance, DNS availability or causality.
    return {
        'schema':SCHEMA,
        'reference_type':'SYNTHETIC_REFERENCE_GRID_NOT_AN_OPERATOR_OBSERVATION',
        'reference_synthetic_date':'2030-02-13',
        'vm_source_type':'MANUAL_HISTORICAL_LOCAL_VM_READ_UNATTESTED',
        'evaluated_slots':len(classes),
        'qualified_slots':report['qualified_slots'],
        'unqualified_slots':report['unqualified_slots'],
        'comparison':'PATTERN_MATCH_WITH_SYNTHETIC_REFERENCE_ONLY' if matched else 'PATTERN_DIFFERS_FROM_SYNTHETIC_REFERENCE',
        'mismatched_slots_local':[f'09:{i*5:02d}' for i in range(8) if (classes[i]!=REF_GRID[i] or modes[i]!=REF_MODES[i])],
        'boundary_status':report['classification'],
        'post_window_raw_advance_in_report': distinct_after_window if matched else 'NOT_ASSESSED_PATTERN_MISMATCH',
        'sampling_recovered':'NOT_ESTABLISHED',
        'telemetry_outage_proven':False,
        'dns_health':'NOT_ESTABLISHED',
        'root_cause':'UNDETERMINED',
        'provenance_verified':False,
        'model_requests':0,
        'quality_gate_decision':'ABSTAIN_NO_MODEL_INFERENCE',
        'remediation_authorized':False,
        'model_action_authority':'NONE',
        'deployment_gate':'HOLD',
    }

def fixture_report(qualified=(0,1,6,7)):
    getter,_=source.fake_getter(tuple(qualified))
    return source.observe_historical(getter)

class Tests(unittest.TestCase):
    def test_public_parent_network_reader_denied(self):
        with self.assertRaisesRegex(source.Hold,'PUBLIC_SYNTHETIC_ONLY_NO_HTTP'):
            source.fetch(source.vm.NAMES['local'],'value')

    def test_baseline(self):
        r=compare_report(fixture_report())
        self.assertEqual(r['comparison'],'PATTERN_MATCH_WITH_SYNTHETIC_REFERENCE_ONLY')
        self.assertEqual(r['mismatched_slots_local'],[])
        self.assertEqual(r['quality_gate_decision'],'ABSTAIN_NO_MODEL_INFERENCE')
    def test_other_grid(self):
        r=compare_report(fixture_report(tuple(range(8))))
        self.assertEqual(r['comparison'],'PATTERN_DIFFERS_FROM_SYNTHETIC_REFERENCE')
        self.assertEqual(len(r['mismatched_slots_local']),4)
    def test_no_pre(self):
        self.assertEqual(compare_report(fixture_report((6,7)))['comparison'],'PATTERN_DIFFERS_FROM_SYNTHETIC_REFERENCE')
    def test_single_post(self):
        self.assertEqual(compare_report(fixture_report((0,7)))['comparison'],'PATTERN_DIFFERS_FROM_SYNTHETIC_REFERENCE')
    def test_empty(self):
        self.assertEqual(compare_report(fixture_report(()))['qualified_slots'],0)
    def test_no_model(self):
        self.assertEqual(compare_report(fixture_report())['model_requests'],0)
    def test_no_root_cause(self):
        self.assertEqual(compare_report(fixture_report())['root_cause'],'UNDETERMINED')
    def test_no_attestation(self):
        self.assertFalse(compare_report(fixture_report())['provenance_verified'])
    def test_not_dns_health(self):
        self.assertEqual(compare_report(fixture_report())['dns_health'],'NOT_ESTABLISHED')
    def test_no_repair(self):
        self.assertFalse(compare_report(fixture_report())['remediation_authorized'])
    def test_baseline_two_post(self):
        self.assertTrue(compare_report(fixture_report())['post_window_raw_advance_in_report'])
    def test_forged_raw_advance_claim(self):
        r=fixture_report();r['raw_sample_pair_post_window_advance_observed']=False;self.assertRaises(Hold,compare_report,r)
    def test_equal_post_raw_timestamps(self):
        r=fixture_report();r['per_slot'][7]['raw_sample_timestamps_utc']=deepcopy(r['per_slot'][6]['raw_sample_timestamps_utc']);self.assertRaises(Hold,compare_report,r)
    def test_duplicate_slots(self):
        r=fixture_report();r['per_slot'][1]=deepcopy(r['per_slot'][0]);self.assertRaises(Hold,compare_report,r)
    def test_forged_origin(self):
        r=fixture_report();r['evidence_origin']='CRYPTO_ATTESTED';self.assertRaises(Hold,compare_report,r)
    def test_forged_root(self):
        r=fixture_report();r['root_cause']='DNS_FAILURE';self.assertRaises(Hold,compare_report,r)
    def test_forged_dns(self):
        r=fixture_report();r['dns_health']='HEALTHY';self.assertRaises(Hold,compare_report,r)
    def test_extra_key(self):
        r=fixture_report();r['command']='sudo reboot';self.assertRaises(Hold,compare_report,r)
    def test_extra_slot_key(self):
        r=fixture_report();r['per_slot'][0]['command']='sudo reboot';self.assertRaises(Hold,compare_report,r)
    def test_forged_model(self):
        r=fixture_report();r['model_requests']=1;self.assertRaises(Hold,compare_report,r)
    def test_forged_gate(self):
        r=fixture_report();r['deployment_gate']='OPEN';self.assertRaises(Hold,compare_report,r)
    def test_claimed_recovery(self):
        r=fixture_report();r['sampling_recovered']='YES';self.assertRaises(Hold,compare_report,r)
    def test_claimed_outage(self):
        r=fixture_report();r['telemetry_outage_proven']=True;self.assertRaises(Hold,compare_report,r)
    def test_forged_count(self):
        r=fixture_report();r['qualified_slots']=8;self.assertRaises(Hold,compare_report,r)
    def test_forged_raw_time(self):
        r=fixture_report();r['per_slot'][6]['raw_sample_timestamps_utc']['local']='9999999999';self.assertRaises(Hold,compare_report,r)
    def test_missing_timestamp(self):
        r=fixture_report();r['per_slot'][6]['raw_sample_timestamps_utc']['local']=None;self.assertRaises(Hold,compare_report,r)
    def test_unexpected_gap(self):
        r=fixture_report();r['per_slot'][0]['gaps']=['FAKE'];self.assertRaises(Hold,compare_report,r)
    def test_bad_mode(self):
        r=fixture_report();r['per_slot'][6]['sampled_mode']='BOOTSTRAP';self.assertEqual(compare_report(r)['comparison'],'PATTERN_DIFFERS_FROM_SYNTHETIC_REFERENCE')
    def test_bad_mode_status(self):
        r=fixture_report();r['per_slot'][6]['sampled_mode']='UNVERIFIED';self.assertRaises(Hold,compare_report,r)
    def test_nonatomic_remains(self):
        r=fixture_report();r['non_atomic_gets']=False;self.assertRaises(Hold,compare_report,r)
    def test_forged_attestation(self):
        r=fixture_report();r['source_authenticity']='ATTESTED';self.assertRaises(Hold,compare_report,r)
    def test_input_list_invalid(self):
        self.assertRaises(Hold,compare_report,[])
    def test_missing_slot(self):
        r=fixture_report();r['per_slot'].pop();self.assertRaises(Hold,compare_report,r)
    def test_corrupt_extra_pair(self):
        r=fixture_report();r['per_slot'][1]['unpaired_source_raw_timestamps_utc']['valid']='1793380500';self.assertRaises(Hold,compare_report,r)

FIXTURES=(('baseline',(0,1,6,7)),('all_fresh',tuple(range(8))),('missing_pre',(6,7)),('one_post',(0,7)),('none',()))

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--self-test',action='store_true')
    group.add_argument('--fixture-matrix',action='store_true')
    group.add_argument('--historical-vm-parity-readonly',action='store_true')
    args=parser.parse_args(argv)
    print('=== LOCAL AI AGENT / C.63.12 / HISTORICAL VM VS OPERATOR GRID ===')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    if args.self_test:
        print('MODE=OFFLINE_SELFTEST NETWORK=NO MODEL=NO HOST_READS=NO')
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        result=unittest.TextTestRunner().run(suite)
        print(f'C6312_SELFTESTS={result.testsRun}/{result.testsRun}')
        print('C6312_RESULT='+('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_OFFLINE'))
        return 0 if result.wasSuccessful() else 1
    if args.fixture_matrix:
        print('MODE=OFFLINE_FIXTURES NETWORK=NO MODEL=NO HOST_READS=NO')
        for name,qualified in FIXTURES:
            r=compare_report(fixture_report(qualified))
            print(f'SCENARIO={name} PARITY={r["comparison"]} MODEL_REQUESTS=0')
        print('C6312_RESULT=PASS_FIVE_SYNTHETIC_PARITY_CASES')
        return 0
    print('MODE=MANUAL_HISTORICAL_VM_READONLY LOOPBACK_ONLY=YES GET_REQUESTS_MAX=8')
    print('NO_MODEL=YES NO_LOGS=YES NO_ROUTER=YES NO_FILES=YES')
    print('C6312_RESULT=HOLD_PUBLIC_SYNTHETIC_ONLY_NO_VM_READ')
    return 2
    try:
        result=compare_report(source.observe_historical())
    except (Hold,source.Hold,source.vm.Hold) as exc:
        print(f'C6312_RESULT=HOLD_{exc}')
        return 2
    print(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=True))
    print('C6312_RESULT=PASS_SYNTHETIC_REFERENCE_ONLY_UNATTESTED_ABSTAIN')
    return 0

if __name__ == '__main__':
    sys.exit(main())
