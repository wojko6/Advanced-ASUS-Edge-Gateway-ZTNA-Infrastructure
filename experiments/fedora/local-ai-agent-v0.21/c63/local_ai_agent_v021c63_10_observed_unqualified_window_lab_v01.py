#!/usr/bin/env python3
"""C.63.10: synthetic-only temporal boundary after observed unqualified VM reads.

This is NOT outage detection, DNS-health evaluation, provenance attestation,
or an executable repair agent. All evidence is synthetic. No host/network/
service reads, subprocesses, model calls, filesystem writes or privileges.

Requires canonical, bounded C.63.8.1 observation reports. Validating their
SHAPE does not prove they came from VictoriaMetrics. A qualified -> unqualified
-> two distinct qualified progression supports only a sampled observation
resumption BOUNDARY (never full DNS recovery or confirmed outage).
"""
from __future__ import annotations

import argparse
import json
import sys
import unittest
from copy import deepcopy
from decimal import Decimal

import local_ai_agent_v021c63_8_1_vm_stats_envelope_hotfix_lab_v01 as vm
import local_ai_agent_v021c63_9_two_observation_vm_boundary_lab_v01 as pair

sys.dont_write_bytecode = True
SCHEMA='local-ai-agent.c63.10.synthetic-unqualified-window.v1'
MAX_OBSERVATIONS=8
MAX_SPACING_SECONDS=600
REPORT_KEYS=frozenset(vm.assess(*vm.fixture()))

class Hold(Exception):
    pass

def checked_report(r):
    if type(r) is not dict or set(r) != REPORT_KEYS:
        raise Hold('REPORT_FIELDS_NOT_CANONICAL')
    try:
        times=pair.check_report(r)
    except (pair.Hold, vm.Hold, ValueError, TypeError) as e:
        raise Hold('INVALID_PARENT_REPORT') from e
    n=r['evaluation_epoch_utc']
    ages=r['raw_sample_age_seconds']
    if type(ages) is not dict or set(ages)!=set(vm.NAMES):
        raise Hold('RAW_SAMPLE_AGES_INVALID')
    for metric, raw in times.items():
        age=ages[metric]
        if raw is None:
            if age is not None:
                raise Hold('MISSING_SAMPLE_WITH_CLAIMED_AGE')
            continue
        if raw>Decimal(n+vm.FUTURE_SECONDS):
            raise Hold('RAW_TIMESTAMP_TOO_FAR_IN_FUTURE')
        try:
            declared=vm.decimal_string(age)
        except vm.Hold as e:
            raise Hold('RAW_AGE_INVALID') from e
        if declared != max(Decimal(0),Decimal(n)-raw):
            raise Hold('RAW_AGE_MISMATCH')
    spread=r['cross_metric_sample_spread_seconds']
    if all(t is not None for t in times.values()):
        try: actual_spread=vm.decimal_string(spread)
        except vm.Hold as e: raise Hold('RAW_SPREAD_INVALID') from e
        if actual_spread!=max(times.values())-min(times.values()):
            raise Hold('RAW_SPREAD_MISMATCH')
    elif spread is not None:
        raise Hold('MISSING_SAMPLE_WITH_CLAIMED_SPREAD')
    collection_age=r['collection_age_seconds']
    if collection_age is not None and (type(collection_age) is not int or collection_age<0):
        raise Hold('COLLECTION_AGE_INVALID')
    # A report with complete fresh metrics and no error indicators cannot
    # become a gap merely by changing its classification label.
    classification=r['classification']
    if classification not in ('DNS_GUARD_MODE_SAMPLED_ONLY',
                              'INSUFFICIENT_EVIDENCE',
                              'INVALID_DNS_GUARD_STATE_SAMPLED'):
        raise Hold('UNKNOWN_OBSERVATION_CLASSIFICATION')
    gaps=r['gaps']
    if type(gaps) is not list or any(type(g) is not str or not g for g in gaps):
        raise Hold('INVALID_GAP_LIST')
    if classification=='DNS_GUARD_MODE_SAMPLED_ONLY':
        if r['sampled_mode'] not in ('LOCAL','BOOTSTRAP'):
            raise Hold('QUALIFIED_MODE_MISMATCH')
    elif r['sampled_mode']!='UNVERIFIED':
        raise Hold('UNQUALIFIED_MODE_MISMATCH')
    if classification=='INSUFFICIENT_EVIDENCE' and not gaps:
        raise Hold('UNQUALIFIED_WITHOUT_EVIDENCE_GAP')
    if classification=='INVALID_DNS_GUARD_STATE_SAMPLED' and gaps:
        raise Hold('INVALID_STATE_WITH_EVIDENCE_GAPS')
    qualified=classification=='DNS_GUARD_MODE_SAMPLED_ONLY'
    if qualified:
        if any(t is None for t in times.values()) or r['gaps']:
            raise Hold('QUALIFIED_WITH_MISSING_DATA')
        if collection_age is None or collection_age>vm.TTL_COLLECTION:
            raise Hold('QUALIFIED_WITH_STALE_COLLECTION')
        if any(Decimal(n)-t>vm.TTL_RAW for t in times.values()):
            raise Hold('QUALIFIED_WITH_STALE_RAW_SAMPLE')
        if max(times.values())-min(times.values())>vm.MAX_SPREAD:
            raise Hold('QUALIFIED_WITH_RAW_SAMPLE_SKEW')
    return qualified, times

def assess_timeline(reports):
    if type(reports) is not list or not 2<=len(reports)<=MAX_OBSERVATIONS:
        raise Hold('TIMELINE_LENGTH_INVALID')
    checked=[checked_report(r) for r in reports]
    evals=[r['evaluation_epoch_utc'] for r in reports]
    if any(not 0<evals[i]-evals[i-1]<=MAX_SPACING_SECONDS for i in range(1,len(evals))):
        raise Hold('EVALUATION_ORDER_OR_SPACING_INVALID')
    valid=[x[0] for x in checked]
    windows=[i for i,v in enumerate(valid) if not v]
    status='NO_OBSERVED_UNQUALIFIED_WINDOW'
    qualifying_pre=0
    gap_count=0
    post_count=0
    if windows:
        first_gap,last_gap=windows[0],windows[-1]
        qualifying_pre=first_gap
        gap_count=last_gap-first_gap+1
        post_count=len(reports)-last_gap-1
        if first_gap==0:
            status='NO_QUALIFIED_PRE_GAP_OBSERVATION'
        elif any(valid[i] for i in range(first_gap,last_gap+1)):
            status='MULTIPLE_SEPARATE_UNQUALIFIED_WINDOWS'
        elif any(reports[i]['classification']=='INVALID_DNS_GUARD_STATE_SAMPLED' for i in windows):
            status='INVALID_GUARD_STATE_NOT_A_TELEMETRY_GAP'
        elif post_count < 2:
            status='POST_WINDOW_QUALIFIED_OBSERVATIONS_INCOMPLETE'
        else:
            pre=checked[first_gap-1][1]
            post_a=checked[last_gap+1][1]
            post_b=checked[last_gap+2][1]
            # All four raw timestamps must advance BOTH across the window and
            # between two post-window observations; an evaluation clock does not
            # count as a new raw sample. Never rely on repeated vector eval time.
            if any(post_a[k] is None or post_b[k] is None for k in vm.NAMES):
                status='POST_WINDOW_RAW_TIMESTAMPS_MISSING'
            elif any(post_b[k]<post_a[k] or post_a[k]<pre[k] for k in vm.NAMES):
                status='POST_WINDOW_RAW_TIMESTAMP_REGRESSION'
            elif any(not(pre[k]<post_a[k]<post_b[k]) for k in vm.NAMES):
                status='POST_WINDOW_RAW_SAMPLES_NOT_DISTINCT'
            else:
                status='SAMPLED_OBSERVATION_RESUMPTION_BOUNDARY_UNATTESTED'
    return {
        'schema':SCHEMA,
        'input_origin':'SYNTHETIC_ONLY',
        'source_identity':'LOCAL_VM_ENDPOINT_127_0_0_1_8428',
        'source_authenticity':'NOT_CRYPTOGRAPHICALLY_ATTESTED',
        'observation_count':len(reports),
        'qualified_observations':sum(valid),
        'unqualified_observations':len(windows),
        'qualified_pre_window_observations':qualifying_pre,
        'candidate_window_size':gap_count,
        'post_window_observations':post_count,
        'first_evaluation_epoch_utc':evals[0],
        'last_evaluation_epoch_utc':evals[-1],
        'classification':status,
        'raw_sample_pair_post_window_advance_observed':status=='SAMPLED_OBSERVATION_RESUMPTION_BOUNDARY_UNATTESTED',
        'telemetry_outage_proven':False,
        'full_collection_recovery_proven':False,
        'dns_health':'NOT_ESTABLISHED',
        'root_cause':'UNDETERMINED',
        'quality_gate_decision':'ABSTAIN_NO_MODEL_INFERENCE',
        'model_requests':0,
        'model_action_authority':'NONE',
        'remediation_authorized':False,
        'deployment_gate':'HOLD',
    }

def sample(n, kind='fresh', raw_override=None):
    vals,times,_=vm.fixture(n)
    if kind=='gap':
        vals['local']=None
        times['local']=None
    elif kind=='stale':
        vals['collection']=n-150
        times={k:Decimal(n-150) for k in vm.NAMES}
    elif kind=='invalid':
        vals['valid']=0
    elif kind!='fresh':
        raise ValueError('UNKNOWN_SYNTHETIC_KIND')
    if raw_override:
        times.update(raw_override)
        # for synthetic new eval but unchanged source sample timestamp, the
        # associated collection metric value must remain consistent with it.
        if 'collection' in raw_override:
            vals['collection']=int(times['collection'])
    return vm.assess(vals,times,n)

def fixture(kind='baseline'):
    t=1793530000
    x=[sample(t),sample(t+75,'gap'),sample(t+150),sample(t+225)]
    if kind=='baseline': pass
    elif kind=='no_window': x=[sample(t+i*75) for i in range(4)]
    elif kind=='one_post': x.pop()
    elif kind=='same_post':
        x[-1]=sample(t+225,raw_override={k:Decimal(t+125) for k in vm.NAMES})
    elif kind=='partial_post':
        x[-1]=sample(t+225,raw_override={k:(Decimal(t+125) if k=='local' else Decimal(t+135)) for k in vm.NAMES})
    elif kind=='regressed_post':
        x[-1]=sample(t+225,raw_override={k:Decimal(t+120) for k in vm.NAMES})
    elif kind=='first_unqualified': x=[sample(t,'gap'),sample(t+75),sample(t+150)]
    elif kind=='two_windows': x=[sample(t),sample(t+75,'gap'),sample(t+150),sample(t+225,'gap'),sample(t+300),sample(t+375)]
    elif kind=='invalid_middle': x[1]=sample(t+75,'invalid')
    elif kind=='stale_middle': x[1]=sample(t+75,'stale')
    elif kind=='gap_after_two': x=[sample(t),sample(t+75),sample(t+150,'gap'),sample(t+225),sample(t+300)]
    elif kind=='three_post': x.append(sample(t+300))
    elif kind=='duplicate_evaluation': x[2]['evaluation_epoch_utc']=x[1]['evaluation_epoch_utc']
    elif kind=='tamper_auth':x[2]['source_authenticity']='CRYPTO_ATTESTED'
    elif kind=='tamper_dns':x[2]['dns_health']='HEALTHY'
    elif kind=='inject_extra_field':x[2]['execute']='reboot'
    elif kind=='raw_age_forged':x[2]['raw_sample_age_seconds']['local']='1'
    elif kind=='raw_ts_future':x[2]['raw_sample_timestamps_utc']['local']=str(t+999)
    elif kind=='model_authority':x[2]['model_action_authority']='ADMIN'
    elif kind=='outage_claim':x[2]['root_cause']='DNS_OUTAGE'
    elif kind=='recovered_claim':x[2]['sampling_recovered']='PROVEN'
    elif kind=='age_stale_falsified':x[2]['collection_age_seconds']=500
    elif kind=='spoof_provenance':x[2]['source_identity']='TRUSTED'
    elif kind=='wrong_timestamp_order':x[2]['evaluation_epoch_utc']=t+10
    else: raise ValueError('UNKNOWN_FIXTURE')
    return x

MATRIX={
 'baseline':'SAMPLED_OBSERVATION_RESUMPTION_BOUNDARY_UNATTESTED',
 'no_window':'NO_OBSERVED_UNQUALIFIED_WINDOW',
 'one_post':'POST_WINDOW_QUALIFIED_OBSERVATIONS_INCOMPLETE',
 'same_post':'POST_WINDOW_RAW_SAMPLES_NOT_DISTINCT',
 'partial_post':'POST_WINDOW_RAW_SAMPLES_NOT_DISTINCT',
 'regressed_post':'POST_WINDOW_RAW_TIMESTAMP_REGRESSION',
 'first_unqualified':'NO_QUALIFIED_PRE_GAP_OBSERVATION',
 'two_windows':'MULTIPLE_SEPARATE_UNQUALIFIED_WINDOWS',
 'invalid_middle':'INVALID_GUARD_STATE_NOT_A_TELEMETRY_GAP',
 'stale_middle':'SAMPLED_OBSERVATION_RESUMPTION_BOUNDARY_UNATTESTED',
 'gap_after_two':'SAMPLED_OBSERVATION_RESUMPTION_BOUNDARY_UNATTESTED',
 'three_post':'SAMPLED_OBSERVATION_RESUMPTION_BOUNDARY_UNATTESTED',
}
MALFORMED=('duplicate_evaluation','tamper_auth','tamper_dns','inject_extra_field',
           'raw_age_forged','raw_ts_future','model_authority','outage_claim',
           'recovered_claim','age_stale_falsified','spoof_provenance','wrong_timestamp_order')

class Tests(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(vm.PORT,8428)
        self.assertEqual(len(vm.NAMES),4)
        self.assertEqual(pair.EXPECTED_FIELDS['deployment_gate'],'HOLD')
    def test_all_matrix(self):
        for name,expected in MATRIX.items():
            with self.subTest(name=name):
                got=assess_timeline(fixture(name))
                self.assertEqual(got['classification'],expected)
    def test_all_malformed(self):
        for name in MALFORMED:
            with self.subTest(name=name):
                with self.assertRaises(Hold):assess_timeline(fixture(name))
    def test_no_model(self):
        for name in MATRIX:
            r=assess_timeline(fixture(name));self.assertEqual(r['model_requests'],0)
            self.assertEqual(r['model_action_authority'],'NONE')
    def test_no_dns_claim(self):
        for name in MATRIX:self.assertEqual(assess_timeline(fixture(name))['dns_health'],'NOT_ESTABLISHED')
    def test_no_outage_claim(self):
        for name in MATRIX:self.assertFalse(assess_timeline(fixture(name))['telemetry_outage_proven'])
    def test_no_full_recovery_claim(self):
        for name in MATRIX:self.assertFalse(assess_timeline(fixture(name))['full_collection_recovery_proven'])
    def test_no_root_cause(self):
        for name in MATRIX:self.assertEqual(assess_timeline(fixture(name))['root_cause'],'UNDETERMINED')
    def test_no_action(self):
        for name in MATRIX:self.assertFalse(assess_timeline(fixture(name))['remediation_authorized'])
    def test_gate(self):
        for name in MATRIX:self.assertEqual(assess_timeline(fixture(name))['deployment_gate'],'HOLD')
    def test_abstain(self):
        for name in MATRIX:self.assertEqual(assess_timeline(fixture(name))['quality_gate_decision'],'ABSTAIN_NO_MODEL_INFERENCE')
    def test_has_pre_boundary(self):self.assertEqual(assess_timeline(fixture())['qualified_pre_window_observations'],1)
    def test_has_gap_boundary(self):self.assertEqual(assess_timeline(fixture())['candidate_window_size'],1)
    def test_has_two_post(self):self.assertEqual(assess_timeline(fixture())['post_window_observations'],2)
    def test_baseline_input_unattested(self):self.assertEqual(assess_timeline(fixture())['source_authenticity'],'NOT_CRYPTOGRAPHICALLY_ATTESTED')
    def test_no_pre_gap_overclaim(self):self.assertFalse(assess_timeline(fixture('no_window'))['raw_sample_pair_post_window_advance_observed'])
    def test_repeated_raw_no_claim(self):self.assertFalse(assess_timeline(fixture('same_post'))['raw_sample_pair_post_window_advance_observed'])
    def test_stale_gap_not_dns_outage(self):self.assertFalse(assess_timeline(fixture('stale_middle'))['telemetry_outage_proven'])
    def test_input_empty(self):
        with self.assertRaises(Hold):assess_timeline([])
    def test_input_not_list(self):
        with self.assertRaises(Hold):assess_timeline('not a list')
    def test_input_one(self):
        with self.assertRaises(Hold):assess_timeline([sample(1793530000)])
    def test_input_too_many(self):
        with self.assertRaises(Hold):assess_timeline([sample(1793530000+i*75) for i in range(9)])
    def test_unknown_report(self):
        with self.assertRaises(Hold):assess_timeline([{},{}])
    def test_gap_after_end(self):
        f=fixture();f[-1]=sample(1793530225,'gap')
        self.assertEqual(assess_timeline(f)['classification'],'MULTIPLE_SEPARATE_UNQUALIFIED_WINDOWS')
    def test_time_spacing(self):
        f=fixture();f[2]=sample(1793531000)
        with self.assertRaises(Hold):assess_timeline(f)
    def test_time_regression(self):
        f=fixture();f[2]['evaluation_epoch_utc']=f[0]['evaluation_epoch_utc']
        with self.assertRaises(Hold):assess_timeline(f)
    def test_duplicate_snapshot_clock_not_new_sample(self):
        with self.assertRaises(Hold):assess_timeline(fixture('duplicate_evaluation'))
    def test_reject_forged_unqualified_label(self):
        f=fixture()
        f[1]=sample(f[1]['evaluation_epoch_utc'],'fresh')
        f[1]['classification']='INSUFFICIENT_EVIDENCE'
        f[1]['sampled_mode']='UNVERIFIED'
        with self.assertRaisesRegex(Hold,'UNQUALIFIED_WITHOUT_EVIDENCE_GAP'):
            assess_timeline(f)

    def test_reject_forged_qualified_label(self):
        f=fixture()
        f[1]['classification']='DNS_GUARD_MODE_SAMPLED_ONLY'
        f[1]['sampled_mode']='LOCAL'
        with self.assertRaises(Hold):
            assess_timeline(f)

    def test_no_file_io_or_external_calls(self):
        import ast,inspect
        tree=ast.parse(inspect.getsource(sys.modules[__name__]))
        banned={'open','urlopen','Popen','run','system','exec','eval'}
        direct_calls={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
        self.assertFalse(direct_calls & banned)

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    options=ap.add_mutually_exclusive_group(required=True)
    options.add_argument('--self-test',action='store_true')
    options.add_argument('--fixture-matrix',action='store_true')
    opt=ap.parse_args(argv)
    print('=== LOCAL AI AGENT / C.63.10 / OBSERVED UNQUALIFIED WINDOW ===')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    print('MODE=OFFLINE_SYNTHETIC_ONLY NETWORK=NO HOST_TELEMETRY_READS=NO MODEL=NO')
    if opt.self_test:
        result=unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        count=result.testsRun-len(result.failures)-len(result.errors)
        print(f'C6310_SELFTESTS={count}/{result.testsRun}')
        print('C6310_RESULT='+('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_TEST_FAILURE'))
        return 0 if result.wasSuccessful() else 1
    for name,expected in MATRIX.items():
        a=assess_timeline(fixture(name))
        if a['classification']!=expected:raise Hold('FIXTURE_MISMATCH')
        print(f'SCENARIO={name} CLASSIFICATION={expected} MODEL_REQUESTS={a["model_requests"]}')
    for name in MALFORMED:
        try:assess_timeline(fixture(name))
        except Hold:
            print(f'SCENARIO={name} CLASSIFICATION=REJECTED_FAIL_CLOSED MODEL_REQUESTS=0')
        else:raise Hold('MALFORMED_ACCEPTED_'+name)
    print(f'C6310_RESULT=PASS_{len(MATRIX)}_CLASSIFICATIONS_{len(MALFORMED)}_MALFORMED_REJECTIONS')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Hold as err:
        print('C6310_RESULT=HOLD_'+str(err));sys.exit(2)
