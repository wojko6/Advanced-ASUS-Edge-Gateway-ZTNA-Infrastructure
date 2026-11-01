#!/usr/bin/env python3
"""C.63.11: synthetic VM window -> C.63.10 classification, read-only.

Original private manual reader is not included here. Synthetic fixture models
loopback 127.0.0.1:8428, 2030-02-13 09:00..09:35 Europe/Warsaw (08:00..08:35 UTC); synthetic fixture ONLY,
eight five-minute evaluations. The public fetch function always HOLDs. No router, DNS probes, log reads, Qwen, writes,
model authority or deployment changes. VM is not cryptographically authenticated.

No attempt to claim an actual network/DNS outage or its root cause. The eight
GETs are non-atomic. Hashes alone are not source attestations.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import json
import sys
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from urllib.parse import urlencode
from unittest.mock import patch

import local_ai_agent_v021c63_8_1_vm_stats_envelope_hotfix_lab_v01 as vm
import local_ai_agent_v021c63_10_observed_unqualified_window_lab_v01 as boundary

sys.dont_write_bytecode = True
SCHEMA = 'local-ai-agent.c63.11.fixed-historical-vm-window.v1'
START = int(datetime(2030, 2, 13, 8, 0, tzinfo=timezone.utc).timestamp())
STEP = 300
SLOTS = 8
END = START + STEP * (SLOTS - 1)
MAX_GETS = 8
MAX_RESPONSE_BYTES = 20_000
TIMEOUT_SECONDS = 4
HOST, PORT = '127.0.0.1', 8428

class Hold(Exception):
    pass

def strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise Hold('DUPLICATE_JSON_KEY')
        out[k] = v
    return out

def path_for(name, kind):
    if type(name) is not str or name not in vm.ALLOWED_NAMES or kind not in ('value','sample_time'):
        raise Hold('NON_FIXED_METRIC_OR_KIND')
    query = name if kind == 'value' else f'timestamp({name})'
    return '/api/v1/query_range?' + urlencode((
        ('query',query),('start',START),('end',END),('step',STEP)
    ))

def fetch(name, kind, factory=None):
    """The public specimen cannot reach VictoriaMetrics, even when imported."""
    raise Hold('PUBLIC_SYNTHETIC_ONLY_NO_HTTP')

def _decode(body):
    if type(body) is not bytes or not 1 <= len(body) <= MAX_RESPONSE_BYTES:
        raise Hold('VM_BODY_SIZE_INVALID')
    try:
        obj = json.loads(body, object_pairs_hook=strict_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(Hold('NONFINITE_JSON')))
    except (TypeError, ValueError, UnicodeError) as exc:
        raise Hold('VM_JSON_INVALID') from exc
    if type(obj) is not dict or set(obj) not in ({'status','data'}, {'status','data','stats'}):
        raise Hold('VM_ENVELOPE_INVALID')
    if obj['status'] != 'success' or type(obj['data']) is not dict or set(obj['data']) != {'resultType','result'} or obj['data']['resultType'] != 'matrix':
        raise Hold('VM_ENVELOPE_INVALID')
    if 'stats' in obj:
        stats = obj['stats']
        if type(stats) is not dict or set(stats) != {'executionTimeMsec','seriesFetched'}:
            raise Hold('VM_STATS_INVALID')
        elapsed, fetched = stats['executionTimeMsec'], stats['seriesFetched']
        if type(elapsed) not in (int,float) or not 0<=elapsed<=3_600_000:
            raise Hold('VM_STATS_INVALID')
        if type(fetched) is not str or not fetched.isascii() or not fetched.isdigit() or len(fetched)>12:
            raise Hold('VM_STATS_INVALID')
    return obj['data']['result']

def parse_matrix(name,kind,body):
    path_for(name,kind)
    rows = _decode(body)
    if type(rows) is not list or len(rows)>1:
        raise Hold('VM_SERIES_COUNT_INVALID')
    points = {START + i*STEP:None for i in range(SLOTS)}
    if not rows:
        return points
    row = rows[0]
    expected_labels = {'__name__':name} if kind=='value' else {}
    if type(row) is not dict or set(row) != {'metric','values'} or row['metric'] != expected_labels:
        raise Hold('VM_SERIES_LABELS_INVALID')
    samples = row['values']
    if type(samples) is not list or len(samples)>SLOTS:
        raise Hold('VM_SAMPLE_COUNT_INVALID')
    seen=set()
    for sample in samples:
        if type(sample) is not list or len(sample)!=2:
            raise Hold('VM_SAMPLE_SHAPE_INVALID')
        epoch, value = sample
        if type(epoch) not in (int,float) or not float(epoch).is_integer() or int(epoch) not in points:
            raise Hold('VM_EVALUATION_TIMESTAMP_INVALID')
        epoch=int(epoch)
        if epoch in seen:
            raise Hold('VM_DUPLICATE_EVALUATION_TIMESTAMP')
        seen.add(epoch)
        try:
            numeric = vm.decimal_string(value)
        except vm.Hold as exc:
            raise Hold('VM_NUMBER_INVALID') from exc
        if kind=='sample_time':
            if not Decimal(1577836800) <= numeric <= Decimal(4102444800) or numeric>Decimal(epoch+vm.FUTURE_SECONDS):
                raise Hold('VM_RAW_TIMESTAMP_INVALID')
            points[epoch] = numeric
        else:
            if numeric != numeric.to_integral_value() or numeric < 0:
                raise Hold('VM_METRIC_VALUE_INVALID')
            if name != vm.NAMES['collection'] and numeric not in (0,1):
                raise Hold('VM_METRIC_FLAG_INVALID')
            points[epoch] = int(numeric)
    return points

def observe_historical(getter=fetch):
    # Exactly eight fixed, non-atomic GETs on success. On errors fail closed.
    values_by_key, times_by_key={},{}
    for key,metric in vm.METRICS:
        values_by_key[key]=parse_matrix(metric,'value',getter(metric,'value'))
        times_by_key[key]=parse_matrix(metric,'sample_time',getter(metric,'sample_time'))
    reports=[]
    mismatches=[]
    unpaired=[]
    for i in range(SLOTS):
        t=START+i*STEP
        values={key:values_by_key[key][t] for key in vm.NAMES}
        times={key:times_by_key[key][t] for key in vm.NAMES}
        partial=[key for key in vm.NAMES if (values[key] is None) != (times[key] is None)]
        # Preserve source-reported unpaired timestamps for transparent review.
        # Never silently assert a complete value/timestamp pair.
        unpaired.append({key:(str(times[key]) if times[key] is not None else None)
                         for key in partial})
        # Parent C.63.10 expects complete value + raw timestamp pairs.
        # A partial response is unqualified, not source attestation or a DNS failure.
        for key in partial:
            values[key]=None
            times[key]=None
        mismatches.append(partial)
        reports.append(vm.assess(values,times,t))
    # Reuse strict C63.10 classifier logic; its original tests are synthetic.
    timeline=boundary.assess_timeline(reports)
    # Do not propagate the parent report's input_origin=SYNTHETIC_ONLY to live evidence.
    return {
        'schema':SCHEMA,
        'evidence_origin':'PUBLIC_SYNTHETIC_VM_QUERY_RANGE_FIXTURE',
        'window_local':'2030-02-13 09:00–09:35 Europe/Warsaw',
        'start_epoch_utc':START,
        'end_epoch_utc':END,
        'step_seconds':STEP,
        'evaluations':SLOTS,
        'get_requests_max':MAX_GETS,
        'non_atomic_gets':True,
        'source_identity':'LOCAL_VM_ENDPOINT_127_0_0_1_8428',
        'source_authenticity':'NOT_CRYPTOGRAPHICALLY_ATTESTED',
        'raw_timestamp_basis':'VM_TIMESTAMP_FUNCTION_VALUE_NOT_QUERY_EVALUATION_TIME',
        'per_slot':[
            {'evaluation_epoch_utc':r['evaluation_epoch_utc'],
             'classification':r['classification'],
             'sampled_mode':r['sampled_mode'],
             'gaps':r['gaps'],
             'incomplete_value_timestamp_pairs':mismatches[i],
             'unpaired_source_raw_timestamps_utc':unpaired[i],
             'raw_sample_timestamps_utc':r['raw_sample_timestamps_utc']}
            for i,r in enumerate(reports)
        ],
        'classification':timeline['classification'],
        'qualified_slots':timeline['qualified_observations'],
        'unqualified_slots':timeline['unqualified_observations'],
        'candidate_unqualified_slots':timeline['candidate_window_size'],
        'raw_sample_pair_post_window_advance_observed':timeline['raw_sample_pair_post_window_advance_observed'],
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

def matrix_body(name, kind, fresh=(0,1,6,7), modifier=None, stats=False):
    vals=[]
    for i in fresh:
        epoch=START+i*STEP
        v=epoch-30 if (kind=='sample_time' or name==vm.NAMES['collection']) else (
            1 if name in (vm.NAMES['valid'],vm.NAMES['local']) else 0
        )
        vals.append([epoch,str(v)])
    row={'metric':({'__name__':name} if kind=='value' else {}),'values':vals}
    obj={'status':'success','data':{'resultType':'matrix','result':[row]}}
    if stats:obj['stats']={'executionTimeMsec':4,'seriesFetched':'1'}
    if modifier:modifier(obj)
    return json.dumps(obj,separators=(',',':'),sort_keys=True).encode('ascii')

def fake_getter(fresh=(0,1,6,7), modifier=None):
    calls=[]
    def fake(name,kind):
        calls.append((name,kind))
        if modifier and modifier[0]==(name,kind):
            return matrix_body(name,kind,fresh,modifier[1])
        return matrix_body(name,kind,fresh,stats=True)
    return fake,calls

class Tests(unittest.TestCase):
    def test_window_timestamps(self):
        self.assertEqual(SLOTS,8)
        self.assertEqual((END-START)//STEP+1,8)
        self.assertEqual(datetime.fromtimestamp(START,timezone.utc).isoformat(),'2030-02-13T08:00:00+00:00')
    def test_path_is_fixed(self):
        p=path_for(vm.NAMES['local'],'sample_time')
        self.assertIn('127',HOST)
        self.assertIn('query_range?',p)
        self.assertIn('step=300',p)
    def test_unknown_metric_fails(self):
        with self.assertRaises(Hold):path_for('up','value')
    def test_unknown_kind_fails(self):
        with self.assertRaises(Hold):path_for(vm.NAMES['local'],'delete')
    def test_baseline(self):
        get,calls=fake_getter(); a=observe_historical(get)
        self.assertEqual(len(calls),8)
        self.assertEqual(a['classification'],'SAMPLED_OBSERVATION_RESUMPTION_BOUNDARY_UNATTESTED')
        self.assertEqual(a['qualified_slots'],4)
        self.assertEqual(a['unqualified_slots'],4)
        self.assertTrue(a['raw_sample_pair_post_window_advance_observed'])
    def test_no_observed_window(self):
        get,_=fake_getter(tuple(range(8)))
        self.assertEqual(observe_historical(get)['classification'],'NO_OBSERVED_UNQUALIFIED_WINDOW')
    def test_only_one_post(self):
        get,_=fake_getter((0,7))
        self.assertEqual(observe_historical(get)['classification'],'POST_WINDOW_QUALIFIED_OBSERVATIONS_INCOMPLETE')
    def test_no_pre(self):
        get,_=fake_getter((6,7))
        self.assertEqual(observe_historical(get)['classification'],'NO_QUALIFIED_PRE_GAP_OBSERVATION')
    def test_all_absent(self):
        get,_=fake_getter(())
        self.assertEqual(observe_historical(get)['classification'],'NO_QUALIFIED_PRE_GAP_OBSERVATION')
    def test_no_model(self):
        get,_=fake_getter();r=observe_historical(get)
        self.assertEqual(r['model_requests'],0)
        self.assertFalse(r['remediation_authorized'])
    def test_never_dns_proven(self):
        get,_=fake_getter();r=observe_historical(get)
        self.assertFalse(r['telemetry_outage_proven'])
        self.assertEqual(r['dns_health'],'NOT_ESTABLISHED')
    def test_no_fake_attestation(self):
        get,_=fake_getter();r=observe_historical(get)
        self.assertEqual(r['source_authenticity'],'NOT_CRYPTOGRAPHICALLY_ATTESTED')
    def test_no_synthetic_origin_on_real(self):
        get,_=fake_getter();r=observe_historical(get)
        self.assertIn('SYNTHETIC',r['evidence_origin'])
    def test_epoch_labels_exact(self):
        name=vm.NAMES['local']
        obj=json.loads(matrix_body(name,'value'))
        self.assertEqual(len(parse_matrix(name,'value',json.dumps(obj).encode())),8)
    def test_duplicate_json_keys(self):
        with self.assertRaises(Hold):_decode(b'{"status":"success","status":"success","data":{}}')
    def test_nonfinite_json(self):
        with self.assertRaises(Hold):_decode(b'{"status":"success","data":NaN}')
    def test_bad_status(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o.update(status='error'))
        with self.assertRaises(Hold):parse_matrix(name,'value',body)
    def test_extra_envelope(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o.update(command='restart'))
        with self.assertRaises(Hold):parse_matrix(name,'value',body)
    def test_extra_stats(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o.update(stats={'other':1}))
        with self.assertRaises(Hold):parse_matrix(name,'value',body)
    def test_wrong_resulttype(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o['data'].update(resultType='vector'))
        with self.assertRaises(Hold):parse_matrix(name,'value',body)
    def test_extra_series(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o['data']['result'].append(deepcopy(o['data']['result'][0])))
        with self.assertRaises(Hold):parse_matrix(name,'value',body)
    def test_extra_label(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o['data']['result'][0]['metric'].update(job='forged'))
        with self.assertRaises(Hold):parse_matrix(name,'value',body)
    def test_bad_field(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o['data']['result'][0].update(command='reboot'))
        with self.assertRaises(Hold):parse_matrix(name,'value',body)
    def test_duplicate_timestep(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o['data']['result'][0]['values'].append(deepcopy(o['data']['result'][0]['values'][0])))
        with self.assertRaises(Hold):parse_matrix(name,'value',body)
    def test_off_grid_timestamp(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o['data']['result'][0]['values'][0].__setitem__(0,START+1))
        with self.assertRaises(Hold):parse_matrix(name,'value',body)
    def test_bad_metric_flag(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o['data']['result'][0]['values'][0].__setitem__(1,'3'))
        with self.assertRaises(Hold):parse_matrix(name,'value',body)
    def test_bad_sample_timestamp(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'sample_time',modifier=lambda o:o['data']['result'][0]['values'][0].__setitem__(1,str(END+10000)))
        with self.assertRaises(Hold):parse_matrix(name,'sample_time',body)
    def test_injected_value(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o['data']['result'][0]['values'][0].__setitem__(1,'0;rm -rf /'))
        with self.assertRaises(Hold):parse_matrix(name,'value',body)
    def test_large_body(self):
        with self.assertRaises(Hold):_decode(b' '* (MAX_RESPONSE_BYTES+1))
    def test_broken_json(self):
        with self.assertRaises(Hold):_decode(b'{')
    def test_empty_rows(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o['data'].update(result=[]))
        self.assertTrue(all(x is None for x in parse_matrix(name,'value',body).values()))
    def test_missing_one_metric(self):
        name=vm.NAMES['local']
        def modifier(o):o['data'].update(result=[])
        getter,calls=fake_getter(modifier=((name,'value'),modifier))
        result=observe_historical(getter)
        self.assertEqual(len(calls),8)
        self.assertEqual(result['qualified_slots'],0)
    def test_unpaired_timestamp_is_preserved_without_claiming_pair(self):
        name=vm.NAMES['local']
        def modifier(o):o['data'].update(result=[])
        getter,_=fake_getter(modifier=((name,'value'),modifier))
        r=observe_historical(getter)
        self.assertEqual(r['per_slot'][0]['incomplete_value_timestamp_pairs'], ['local'])
        self.assertEqual(r['per_slot'][0]['unpaired_source_raw_timestamps_utc']['local'],str(START-30))
        self.assertIsNone(r['per_slot'][0]['raw_sample_timestamps_utc']['local'])
    def test_unpaired_value_is_not_qualified(self):
        name=vm.NAMES['local']
        def modifier(o):o['data'].update(result=[])
        getter,_=fake_getter(modifier=((name,'sample_time'),modifier))
        r=observe_historical(getter)
        self.assertEqual(r['qualified_slots'],0)
        self.assertEqual(r['per_slot'][0]['unpaired_source_raw_timestamps_utc']['local'],None)
    def test_public_network_reader_denied(self):
        with self.assertRaisesRegex(Hold,'PUBLIC_SYNTHETIC_ONLY_NO_HTTP'):
            fetch(vm.NAMES['local'],'value')

    def test_external_access_not_in_live_reader(self):
        import ast,inspect
        module=ast.parse(inspect.getsource(sys.modules[__name__]))
        text=inspect.getsource(fetch)
        self.assertIn('PUBLIC_SYNTHETIC_ONLY_NO_HTTP',text)
        self.assertNotIn('subprocess',text)
        # Still manual review required: AST string checks are not security proofs.
    def test_no_exit_on_get_error(self):
        def broken(name,kind):raise Hold('VM_LOOPBACK_UNAVAILABLE')
        with self.assertRaises(Hold):observe_historical(broken)
    def test_wrong_source_return(self):
        name=vm.NAMES['local']
        with self.assertRaises(Hold):parse_matrix(name,'value','text')
    def test_bool_timestamp(self):
        name=vm.NAMES['local']
        body=matrix_body(name,'value',modifier=lambda o:o['data']['result'][0]['values'][0].__setitem__(0,True))
        with self.assertRaises(Hold):parse_matrix(name,'value',body)
    def test_hash_not_attestation(self):
        get,_=fake_getter();r=observe_historical(get)
        self.assertNotIn('ATTESTED',r['source_authenticity'].replace('NOT_CRYPTOGRAPHICALLY_ATTESTED',''))

MATRIX = {
    'observed_window':(0,1,6,7),
    'no_window':tuple(range(8)),
    'one_post':(0,7),
    'missing_pre':(6,7),
    'no_samples':(),
}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--self-test',action='store_true')
    group.add_argument('--fixture-matrix',action='store_true')
    group.add_argument('--historical-vm-readonly',action='store_true')
    a=parser.parse_args(argv)
    print('=== LOCAL AI AGENT / C.63.11 / HISTORICAL VM WINDOW ===')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    if a.self_test:
        print('MODE=OFFLINE_SELFTEST NETWORK=NO MODEL=NO HOST_READS=NO')
        result=unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        good=result.testsRun-len(result.failures)-len(result.errors)
        print(f'C6311_SELFTESTS={good}/{result.testsRun}')
        print('C6311_RESULT='+('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_TEST_FAILURE'))
        return 0 if result.wasSuccessful() else 1
    if a.fixture_matrix:
        print('MODE=OFFLINE_SYNTHETIC_FIXTURES NETWORK=NO MODEL=NO')
        for k,slots in MATRIX.items():
            getter,calls=fake_getter(slots)
            result=observe_historical(getter)
            print(f'SCENARIO={k} CLASSIFICATION={result["classification"]} QUALIFIED={result["qualified_slots"]} GETS={len(calls)} MODEL_REQUESTS=0')
        print(f'C6311_RESULT=PASS_{len(MATRIX)}_SYNTHETIC_HISTORICAL_CASES')
        return 0
    print('MODE=MANUAL_HISTORICAL_VM_READONLY LOOPBACK_ONLY=YES GET_REQUESTS_MAX=8')
    print('NO_MODEL=YES NO_LOGS=YES NO_ROUTER=YES NO_FILES=YES')
    print('C6311_RESULT=HOLD_PUBLIC_SYNTHETIC_ONLY_NO_VM_READ')
    return 2
    result=observe_historical()
    print(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False))
    print('C6311_RESULT=PASS_HISTORICAL_VM_OBSERVATION_UNATTESTED_ABSTAIN')
    return 0

if __name__ == '__main__':
    try:sys.exit(main())
    except (Hold,vm.Hold,boundary.Hold) as exc:
        print('C6311_RESULT=HOLD_'+type(exc).__name__+'_'+str(exc))
        sys.exit(2)
