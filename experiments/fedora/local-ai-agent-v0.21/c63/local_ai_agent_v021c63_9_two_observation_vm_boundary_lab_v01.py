#!/usr/bin/env python3
"""C.63.9: compare two bounded, non-atomic, untrusted VM observation batches.

Offline tests/matrix by default. Explicit --live-vm-pair-readonly performs two
fixed eight-GET localhost batches, separated by one fixed 75-second interval.
Neither repeated samples nor increasing timestamps prove collection recovery,
source authenticity, DNS health, or any failure root cause. No model/commands.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import unittest
from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

import local_ai_agent_v021c63_8_1_vm_stats_envelope_hotfix_lab_v01 as vm

sys.dont_write_bytecode = True
SCHEMA='local-ai-agent.c63.9.two-vm-observations-readonly.v1'
INTERVAL_SECONDS=75
MAX_OBSERVATION_SPAN_SECONDS=360
EXPECTED_FIELDS={
    'schema':vm.SCHEMA,
    'source_identity':'LOCAL_VM_ENDPOINT_127_0_0_1_8428',
    'source_authenticity':'NOT_CRYPTOGRAPHICALLY_ATTESTED',
    'source_transport':'HTTP_LOOPBACK_FIXED_EIGHT_NONATOMIC_GETS',
    'timestamp_basis':'VM_TIMESTAMP_FUNCTION_VALUE_NOT_VECTOR_EVALUATION_TIME',
    'model_action_authority':'NONE',
    'deployment_gate':'HOLD',
    'quality_gate_decision':'ABSTAIN_NO_MODEL_INFERENCE',
    'dns_health':'NOT_ESTABLISHED',
    'root_cause':'UNDETERMINED',
    'sampling_recovered':'NOT_ESTABLISHED',
}
class Hold(Exception):
    pass

def parse_raw_times(report):
    d=report.get('raw_sample_timestamps_utc')
    if type(d) is not dict or set(d)!=set(vm.NAMES):
        raise Hold('RAW_TIMESTAMP_KEYS_INVALID')
    out={}
    for key,value in d.items():
        if value is None:
            out[key]=None
            continue
        if type(value) is not str or len(value)>30:
            raise Hold('RAW_TIMESTAMP_TYPE_INVALID')
        try: number=vm.decimal_string(value)
        except vm.Hold as exc: raise Hold('RAW_TIMESTAMP_FORMAT_INVALID') from exc
        if not Decimal(1577836800)<=number<=Decimal(4102444800):
            raise Hold('RAW_TIMESTAMP_RANGE_INVALID')
        out[key]=number
    return out

def check_report(report):
    if type(report) is not dict or len(json.dumps(report,default=str))>vm.MAX_OUTPUT_BYTES*2:
        raise Hold('REPORT_INVALID_OR_TOO_LARGE')
    for field,required in EXPECTED_FIELDS.items():
        if report.get(field)!=required or type(report.get(field)) is not type(required):
            raise Hold('REPORT_INVARIANT_INVALID_'+field.upper())
    if type(report.get('evaluation_epoch_utc')) is not int:
        raise Hold('EVALUATION_TIMESTAMP_TYPE_INVALID')
    try: vm.now_clock(report['evaluation_epoch_utc'])
    except vm.Hold as exc: raise Hold('EVALUATION_CLOCK_INVALID') from exc
    if report.get('model_requests') != 0 or type(report.get('model_requests')) is not int:
        raise Hold('MODEL_REQUESTS_INVARIANT_INVALID')
    if report.get('remediation_authorized') is not False:
        raise Hold('REMEDIATION_INVARIANT_INVALID')
    if report.get('two_distinct_post_gap_samples') is not False:
        raise Hold('RECOVERY_CLAIM_NOT_ALLOWED')
    if type(report.get('gaps')) is not list or len(report['gaps'])>20 or any(type(x) is not str or len(x)>100 for x in report['gaps']):
        raise Hold('GAP_REPORT_INVALID')
    if report.get('classification') not in ('DNS_GUARD_MODE_SAMPLED_ONLY','INSUFFICIENT_EVIDENCE','INVALID_DNS_GUARD_STATE_SAMPLED'):
        raise Hold('CLASSIFICATION_INVALID')
    if report.get('sampled_mode') not in ('LOCAL','BOOTSTRAP','UNVERIFIED'):
        raise Hold('MODE_INVALID')
    if report.get('samples_per_metric') != 1 or type(report.get('samples_per_metric')) is not int:
        raise Hold('SAMPLE_COUNT_INVALID')
    if report['classification']=='DNS_GUARD_MODE_SAMPLED_ONLY' and (report['gaps'] or report['sampled_mode']=='UNVERIFIED'):
        raise Hold('CONTRADICTORY_QUALIFIED_REPORT')
    return parse_raw_times(report)

def compare(first, second):
    a=check_report(first)
    b=check_report(second)
    t1=first['evaluation_epoch_utc']; t2=second['evaluation_epoch_utc']
    if not (t1<t2 and t2-t1<=MAX_OBSERVATION_SPAN_SECONDS):
        raise Hold('OBSERVATION_CLOCK_ORDER_INVALID')
    advanced=[]; same=[]; regression=[]; unavailable=[]
    for k in vm.NAMES:
        if a[k] is None or b[k] is None:
            unavailable.append(k)
        elif b[k]>a[k]:
            advanced.append(k)
        elif b[k]==a[k]:
            same.append(k)
        else:
            regression.append(k)
    a_fresh=first['classification']=='DNS_GUARD_MODE_SAMPLED_ONLY'
    b_fresh=second['classification']=='DNS_GUARD_MODE_SAMPLED_ONLY'
    if regression:
        status='RAW_SAMPLE_TIMESTAMP_REGRESSION_REVIEW_REQUIRED'
    elif not b_fresh:
        status='SECOND_OBSERVATION_NOT_QUALIFIED'
    elif not a_fresh:
        status='UNQUALIFIED_THEN_ONE_FRESH_OBSERVATION_ONLY'
    elif len(advanced)==len(vm.NAMES):
        status='TWO_DISTINCT_FRESH_VM_OBSERVATIONS_UNATTESTED'
    elif len(same)==len(vm.NAMES):
        status='SAME_RAW_VM_SAMPLES_REOBSERVED'
    else:
        status='PARTIAL_OR_MISSING_SAMPLE_ADVANCE'
    # A state *transition* is not an outage or recovery. Two fresh reads
    # alone cannot establish that any preceding observation gap occurred.
    return {
        'schema':SCHEMA,
        'mode':'TWO_LOCAL_VM_OBSERVATIONS_ONLY',
        'observation_count':2,
        'requests_total':16,
        'non_atomic_gets':True,
        'source_identity':EXPECTED_FIELDS['source_identity'],
        'source_authenticity':'NOT_CRYPTOGRAPHICALLY_ATTESTED',
        'first_evaluation_epoch_utc':t1,
        'second_evaluation_epoch_utc':t2,
        'elapsed_evaluation_seconds':t2-t1,
        'first_classification':first['classification'],
        'second_classification':second['classification'],
        'first_sampled_mode':first['sampled_mode'],
        'second_sampled_mode':second['sampled_mode'],
        'raw_timestamp_advanced_metrics':sorted(advanced),
        'raw_timestamp_unchanged_metrics':sorted(same),
        'raw_timestamp_regressed_metrics':sorted(regression),
        'raw_timestamp_unavailable_metrics':sorted(unavailable),
        'classification':status,
        'two_distinct_fresh_sample_sets_observed':bool(a_fresh and b_fresh and len(advanced)==len(vm.NAMES)),
        'pre_gap_boundary_observed':False,
        'two_distinct_post_gap_samples':False,
        'sampling_recovered':'NOT_ESTABLISHED',
        'dns_health':'NOT_ESTABLISHED',
        'root_cause':'UNDETERMINED',
        'quality_gate_decision':'ABSTAIN_NO_MODEL_INFERENCE',
        'model_requests':0,
        'model_action_authority':'NONE',
        'remediation_authorized':False,
        'deployment_gate':'HOLD',
    }

def fixture_pair(kind='advanced'):
    # Build both reports through the verified C.63.8.1 host logic, not
    # by inventing a permissive report format or changing its invariants.
    v1,raw1,n1=vm.fixture(1793530000)
    n2=n1+75
    v2,raw2,_=vm.fixture(n2)
    if kind=='same':
        v2=deepcopy(v1);raw2=deepcopy(raw1)
    elif kind=='partial':
        n2=n1+10
        v2=deepcopy(v1);raw2=deepcopy(raw1)
        v2['collection']=n2-25;raw2['collection']=Decimal(n2-25)
    elif kind=='regression':
        v2=deepcopy(v1);raw2={k:Decimal(n1-40) for k in vm.NAMES}
        v2['collection']=n2-25
    elif kind=='first_gap':
        v1['local']=None;raw1['local']=None
    elif kind=='second_gap':
        v2['local']=None;raw2['local']=None
    elif kind=='first_invalid':
        v1['valid']=0
    elif kind=='mode_switch':
        v2.update(local=0,bootstrap=1)
    elif kind=='stale_second':
        v2['collection']=n2-121
    elif kind not in ('advanced',):
        raise ValueError('UNKNOWN_SYNTHETIC_FIXTURE')
    return vm.assess(v1,raw1,n1),vm.assess(v2,raw2,n2)

class Tests(unittest.TestCase):
    def result(self,kind='advanced'):
        a,b=fixture_pair(kind);return compare(a,b)
    def holds(self,a,b):
        with self.assertRaises(Hold):compare(a,b)
    def test_advancement(self):self.assertEqual(self.result()['classification'],'TWO_DISTINCT_FRESH_VM_OBSERVATIONS_UNATTESTED')
    def test_advancement_flag(self):self.assertTrue(self.result()['two_distinct_fresh_sample_sets_observed'])
    def test_same(self):self.assertEqual(self.result('same')['classification'],'SAME_RAW_VM_SAMPLES_REOBSERVED')
    def test_same_no_flag(self):self.assertFalse(self.result('same')['two_distinct_fresh_sample_sets_observed'])
    def test_partial(self):self.assertEqual(self.result('partial')['classification'],'PARTIAL_OR_MISSING_SAMPLE_ADVANCE')
    def test_regression(self):self.assertEqual(self.result('regression')['classification'],'RAW_SAMPLE_TIMESTAMP_REGRESSION_REVIEW_REQUIRED')
    def test_first_gap(self):self.assertEqual(self.result('first_gap')['classification'],'UNQUALIFIED_THEN_ONE_FRESH_OBSERVATION_ONLY')
    def test_second_gap(self):self.assertEqual(self.result('second_gap')['classification'],'SECOND_OBSERVATION_NOT_QUALIFIED')
    def test_first_invalid(self):self.assertEqual(self.result('first_invalid')['classification'],'UNQUALIFIED_THEN_ONE_FRESH_OBSERVATION_ONLY')
    def test_stale_second(self):self.assertEqual(self.result('stale_second')['classification'],'SECOND_OBSERVATION_NOT_QUALIFIED')
    def test_mode_switch(self):self.assertEqual(self.result('mode_switch')['second_sampled_mode'],'BOOTSTRAP')
    def test_no_recovery_from_two_fresh(self):self.assertFalse(self.result()['two_distinct_post_gap_samples'])
    def test_no_recovery_from_first_gap(self):self.assertEqual(self.result('first_gap')['sampling_recovered'],'NOT_ESTABLISHED')
    def test_no_dns_health(self):self.assertEqual(self.result()['dns_health'],'NOT_ESTABLISHED')
    def test_no_root_cause(self):self.assertEqual(self.result()['root_cause'],'UNDETERMINED')
    def test_no_model_requests(self):self.assertEqual(self.result()['model_requests'],0)
    def test_no_actions(self):self.assertFalse(self.result()['remediation_authorized'])
    def test_hold(self):self.assertEqual(self.result()['deployment_gate'],'HOLD')
    def test_not_attested(self):self.assertEqual(self.result()['source_authenticity'],'NOT_CRYPTOGRAPHICALLY_ATTESTED')
    def test_fixed_requests(self):self.assertEqual(self.result()['requests_total'],16)
    def test_pair_time_diff(self):self.assertEqual(self.result()['elapsed_evaluation_seconds'],75)
    def test_gap_list_no_proof(self):self.assertFalse(self.result('first_gap')['pre_gap_boundary_observed'])
    def test_negative_time_order(self):
        a,b=fixture_pair();b['evaluation_epoch_utc']=a['evaluation_epoch_utc'];self.holds(a,b)
    def test_long_interval(self):
        a,b=fixture_pair();b['evaluation_epoch_utc']=a['evaluation_epoch_utc']+361;self.holds(a,b)
    def test_wrong_schema(self):
        a,b=fixture_pair();b['schema']='untrusted';self.holds(a,b)
    def test_wrong_source(self):
        a,b=fixture_pair();b['source_identity']='OTHER';self.holds(a,b)
    def test_forged_attestation(self):
        a,b=fixture_pair();b['source_authenticity']='ATTESTED';self.holds(a,b)
    def test_model_requests_injected(self):
        a,b=fixture_pair();b['model_requests']=1;self.holds(a,b)
    def test_wrong_gate(self):
        a,b=fixture_pair();b['deployment_gate']='OPEN';self.holds(a,b)
    def test_remediation_injected(self):
        a,b=fixture_pair();b['remediation_authorized']=True;self.holds(a,b)
    def test_malicious_root_cause(self):
        a,b=fixture_pair();b['root_cause']='DNS_OUTAGE';self.holds(a,b)
    def test_recovery_injected(self):
        a,b=fixture_pair();b['two_distinct_post_gap_samples']=True;self.holds(a,b)
    def test_second_unknown_metric(self):
        a,b=fixture_pair();b['raw_sample_timestamps_utc']['other']='1793530000';self.holds(a,b)
    def test_raw_timestamp_nonstring(self):
        a,b=fixture_pair();b['raw_sample_timestamps_utc']['local']=1793530000;self.holds(a,b)
    def test_raw_timestamp_invalid(self):
        a,b=fixture_pair();b['raw_sample_timestamps_utc']['local']='nan';self.holds(a,b)
    def test_raw_future_out_of_range(self):
        a,b=fixture_pair();b['raw_sample_timestamps_utc']['local']='9999999999';self.holds(a,b)
    def test_wrong_classification(self):
        a,b=fixture_pair();b['classification']='DNS_HEALTH_PROVEN';self.holds(a,b)
    def test_wrong_mode(self):
        a,b=fixture_pair();b['sampled_mode']='ADMIN';self.holds(a,b)
    def test_duplicate_model_authority(self):
        a,b=fixture_pair();b['model_action_authority']='ADMIN';self.holds(a,b)
    def test_wrong_request_count(self):
        a,b=fixture_pair();b['samples_per_metric']=2;self.holds(a,b)
    def test_json_output_under_limit(self):self.assertLess(len(json.dumps(self.result()).encode('utf-8')),3000)
    def test_parent_fixture(self):self.assertEqual(vm.SCHEMA,EXPECTED_FIELDS['schema'])
    def test_parent_parser(self):
        a,b=fixture_pair();self.assertEqual(len(parse_raw_times(a)),4)
    def test_malformed_report(self):
        a,b=fixture_pair();self.holds([],b)
    def test_untrusted_ts_clock(self):
        a,b=fixture_pair();a['evaluation_epoch_utc']=0;self.holds(a,b)
    def test_invalid_mode_label_consistency(self):
        a,b=fixture_pair();a['sampled_mode']='UNVERIFIED';self.holds(a,b)
    def test_wrong_decision(self):
        a,b=fixture_pair();a['quality_gate_decision']='READY';self.holds(a,b)
    def test_out_of_order_raw(self):
        r=self.result('regression');self.assertTrue(r['raw_timestamp_regressed_metrics'])
    def test_mode_switch_not_causality(self):self.assertEqual(self.result('mode_switch')['root_cause'],'UNDETERMINED')
    def test_live_exactly_two_observations_fixed_interval(self):
        first,second=fixture_pair()
        with patch.object(vm,'observe',side_effect=[first,second]) as reads, \
             patch.object(time,'sleep') as sleep, \
             patch.object(time,'time',side_effect=[first['evaluation_epoch_utc'],second['evaluation_epoch_utc']]):
            with patch('builtins.print'):
                report=live_pair()
        self.assertEqual(reads.call_count,2)
        sleep.assert_called_once_with(INTERVAL_SECONDS)
        self.assertEqual(report['requests_total'],16)
    def test_live_fail_closed_before_second_read(self):
        with patch.object(vm,'observe',side_effect=vm.Hold('VM_LOOPBACK_UNAVAILABLE')) as reads, \
             patch.object(time,'sleep') as sleep, \
             patch.object(time,'time',return_value=1793530000):
            with self.assertRaises(vm.Hold):live_pair()
        self.assertEqual(reads.call_count,1)
        sleep.assert_not_called()


def matrix():
    for kind in ('advanced','same','partial','regression','first_gap','second_gap','first_invalid','mode_switch','stale_second'):
        a,b=fixture_pair(kind)
        yield kind,compare(a,b)


def live_pair():
    # Manual opt-in only. Two separate observations on the same locally
    # configured VM endpoint, with no file writes, model, or subprocesses.
    # A fixed gap does not guarantee a new VM sample; no auto-retry.
    first=vm.observe(vm.now_clock(int(time.time())))
    print('FIRST_OBSERVATION='+first['classification'],flush=True)
    print('INTERVAL_FIXED_SECONDS='+str(INTERVAL_SECONDS),flush=True)
    time.sleep(INTERVAL_SECONDS)
    second=vm.observe(vm.now_clock(int(time.time())))
    return compare(first,second)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--self-test',action='store_true')
    g.add_argument('--fixture-matrix',action='store_true')
    g.add_argument('--live-vm-pair-readonly',action='store_true')
    opt=ap.parse_args(argv)
    print('=== LOCAL AI AGENT / C.63.9 / TWO VM OBSERVATIONS ===')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    try:
        if opt.self_test:
            print('MODE=OFFLINE SELFTEST NETWORK=NO MODEL=NO HOST_READS=NO')
            result=unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
            good=result.testsRun-len(result.failures)-len(result.errors)
            print(f'C639_SELFTESTS={good}/{result.testsRun}')
            print('C639_RESULT='+('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_TEST_FAILURE'))
            return 0 if result.wasSuccessful() else 1
        if opt.fixture_matrix:
            print('MODE=OFFLINE_FIXTURES NETWORK=NO MODEL=NO HOST_READS=NO')
            rows=list(matrix())
            for name,r in rows:
                print(f'SCENARIO={name} CLASSIFICATION={r["classification"]} MODEL_REQUESTS={r["model_requests"]}')
            print(f'C639_RESULT=PASS_{len(rows)}_SYNTHETIC_PAIR_CASES')
            return 0
        print('MODE=MANUAL_VM_PAIR_READONLY GET_REQUESTS_MAX=16 LOOPBACK_ONLY=YES',flush=True)
        print('NO_MODEL=YES NO_FILES=YES NO_ROUTER=YES',flush=True)
        report=live_pair()
        print(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=True))
        print('C639_RESULT=PASS_TWO_OBSERVATION_COMPARISON_WITH_UNATTESTED_SOURCE_ABSTAIN')
        return 0
    except (Hold,vm.Hold) as exc:
        print('C639_RESULT=HOLD_'+str(exc))
        print('MODEL_REQUESTS=0 DEPLOYMENT_GATE=HOLD')
        return 2
    except KeyboardInterrupt:
        print('\nC639_RESULT=HOLD_OPERATOR_INTERRUPTED')
        return 130

if __name__=='__main__':sys.exit(main())
