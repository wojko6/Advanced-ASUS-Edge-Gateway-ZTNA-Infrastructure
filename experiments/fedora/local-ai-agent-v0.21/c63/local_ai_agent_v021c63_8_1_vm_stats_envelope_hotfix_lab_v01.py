#!/usr/bin/env python3
"""C.63.8.1: bounded local VM source observation; still NOT attested or model-ready.

Modes: offline self-tests/fixtures, and explicit --live-vm-readonly only.
Exactly eight non-atomic GETs on fixed 127.0.0.1:8428 VictoriaMetrics endpoint.
No model, router, journal, Loki, shell, agent actions, files written or autostart.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import http.client
import json
import re
import sys
import time
import unittest
from urllib.parse import urlencode

sys.dont_write_bytecode = True
SCHEMA = 'local-ai-agent.c63.8.1.vm-local-readonly-source-boundary.v1'
HOST, PORT = '127.0.0.1', 8428
TIMEOUT_SECONDS, MAX_RESPONSE_BYTES = 3, 8192
MAX_OUTPUT_BYTES = 3600
TTL_COLLECTION, TTL_RAW, MAX_SPREAD, FUTURE_SECONDS = 120, 300, 15, 5
EVAL_TOLERANCE = 5
METRICS = (
    ('collection', 'asus_edge_dns_guard_collection_timestamp_seconds'),
    ('valid', 'asus_edge_dns_guard_state_valid'),
    ('local', 'asus_edge_dns_guard_mode_local'),
    ('bootstrap', 'asus_edge_dns_guard_mode_bootstrap'),
)
NAMES = dict(METRICS)
ALLOWED_NAMES = frozenset(NAMES.values())
NUMERIC = re.compile(r'(?:0|[1-9][0-9]{0,14})(?:\.[0-9]{1,9})?(?:[eE][+-]?[0-9]{1,3})?\Z')

class Hold(Exception):
    pass

def strict_pairs(pairs):
    data = {}
    for k, v in pairs:
        if k in data:
            raise Hold('DUPLICATE_JSON_KEY')
        data[k] = v
    return data

def now_clock(now):
    if type(now) is not int or not 1577836800 <= now <= 4102444800:
        raise Hold('INVALID_EVALUATION_CLOCK')
    return now

def make_path(name, kind, now):
    if type(name) is not str or name not in ALLOWED_NAMES or kind not in ('value', 'sample_time'):
        raise Hold('UNAPPROVED_QUERY')
    q = name if kind == 'value' else 'timestamp(' + name + ')'
    return '/api/v1/query?' + urlencode((('query', q), ('time', now_clock(now))))

def fetch(name, kind, now, factory=http.client.HTTPConnection):
    path = make_path(name, kind, now)
    conn = factory(HOST, PORT, timeout=TIMEOUT_SECONDS)
    try:
        conn.request('GET', path, headers={'Accept': 'application/json', 'Connection': 'close'})
        response = conn.getresponse()
        if response.status != 200:
            raise Hold('HTTP_RESPONSE_NOT_200')
        blob = response.read(MAX_RESPONSE_BYTES + 1)
        if not 1 <= len(blob) <= MAX_RESPONSE_BYTES:
            raise Hold('RESPONSE_SIZE_INVALID')
        return blob
    except (OSError, TimeoutError, http.client.HTTPException) as exc:
        raise Hold('VM_LOOPBACK_UNAVAILABLE') from exc
    finally:
        conn.close()

def decimal_string(v):
    if type(v) is not str or len(v) > 32 or not NUMERIC.fullmatch(v):
        raise Hold('METRIC_NUMBER_NOT_ALLOWED')
    try:
        d = Decimal(v)
    except InvalidOperation as exc:
        raise Hold('METRIC_DECIMAL_INVALID') from exc
    if not d.is_finite():
        raise Hold('METRIC_NONFINITE')
    return d

def parse(name, kind, blob, now):
    make_path(name, kind, now)
    if type(blob) is not bytes or not 1 <= len(blob) <= MAX_RESPONSE_BYTES:
        raise Hold('RESPONSE_SIZE_INVALID')
    try:
        obj = json.loads(blob, object_pairs_hook=strict_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(Hold('JSON_NONFINITE')))
    except (ValueError, UnicodeError, TypeError) as exc:
        raise Hold('INVALID_VM_JSON') from exc
    if (type(obj) is not dict or set(obj) not in ({'status','data'}, {'status','data','stats'})
        or obj['status'] != 'success'
        or type(obj['data']) is not dict or set(obj['data']) != {'resultType','result'}
        or obj['data']['resultType'] != 'vector'):
        raise Hold('VM_ENVELOPE_INVALID')
    # VictoriaMetrics adds documented query statistics. These are transport
    # metadata, NOT evidence or authentication; never promote into assessment.
    # Unknown envelope fields, duplicate JSON keys and unexpected stats fail closed.
    if 'stats' in obj:
        st = obj['stats']
        if type(st) is not dict or set(st) != {'executionTimeMsec','seriesFetched'}:
            raise Hold('VM_STATS_INVALID')
        elapsed = st['executionTimeMsec']
        fetched = st['seriesFetched']
        if (type(elapsed) not in (int,float)
            or not (0 <= elapsed <= 3600000)
            or not (isinstance(fetched,str) and re.fullmatch(r'(?:0|[1-9][0-9]{0,11})',fetched))):
            raise Hold('VM_STATS_INVALID')
    rows = obj['data']['result']
    if type(rows) is not list or len(rows) > 1:
        raise Hold('VM_SERIES_COUNT_INVALID')
    if not rows:
        return None
    row = rows[0]
    exp = {'__name__':name} if kind == 'value' else {}
    if type(row) is not dict or set(row) != {'metric','value'} or row['metric'] != exp:
        raise Hold('SERIES_LABELS_OR_SHAPE_INVALID')
    pair = row['value']
    if type(pair) is not list or len(pair) != 2:
        raise Hold('VECTOR_VALUE_INVALID')
    t, value = pair
    if type(t) not in (float,int) or not (now - EVAL_TOLERANCE <= t <= now + EVAL_TOLERANCE):
        raise Hold('QUERY_EVALUATION_TIME_INVALID')
    n = decimal_string(value)
    if kind == 'sample_time':
        if not Decimal(1577836800) <= n <= Decimal(4102444800):
            raise Hold('RAW_SAMPLE_TIME_INVALID')
        return n
    if n != n.to_integral_value() or n < 0:
        raise Hold('METRIC_VALUE_NOT_POSITIVE_INTEGER')
    if name != NAMES['collection'] and n not in (0,1):
        raise Hold('METRIC_FLAG_INVALID')
    return int(n)

def assess(values, raw_times, now):
    now_clock(now)
    if type(values) is not dict or type(raw_times) is not dict or set(values) != set(NAMES) or set(raw_times) != set(NAMES):
        raise Hold('METRIC_KEYS_INVALID')
    if any(v is not None and (type(v) is not int or v < 0) for v in values.values()):
        raise Hold('METRIC_VALUES_INVALID')
    if any(t is not None and (type(t) is not Decimal or not t.is_finite()) for t in raw_times.values()):
        raise Hold('RAW_SAMPLE_TYPES_INVALID')
    # Only trusted as locally queried *claims*; the selected VM metric samples
    # are not cryptographically attested and separate GETs are not atomic.
    gaps = []
    ages = {}
    for k in NAMES:
        v, ts = values[k], raw_times[k]
        if v is None or ts is None:
            gaps.append(k.upper()+'_VALUE_OR_TIMESTAMP_MISSING')
            ages[k] = None
            continue
        age = Decimal(now) - ts
        ages[k] = str(max(Decimal(0),age))
        if age < -FUTURE_SECONDS: gaps.append(k.upper()+'_RAW_SAMPLE_IN_FUTURE')
        if age > TTL_RAW: gaps.append(k.upper()+'_RAW_SAMPLE_STALE')
    collected = values['collection']
    collection_age = None
    if collected is None or collected == 0 or collected > now+FUTURE_SECONDS:
        gaps.append('COLLECTION_VALUE_INVALID_OR_MISSING')
    else:
        collection_age = now-collected
        if collection_age > TTL_COLLECTION: gaps.append('COLLECTION_VALUE_STALE')
        if raw_times['collection'] is not None and abs(Decimal(collected)-raw_times['collection']) > TTL_COLLECTION:
            gaps.append('COLLECTION_VALUE_SAMPLE_TIME_MISALIGNED')
    complete = all(raw_times[k] is not None for k in NAMES)
    spread = None
    if complete:
        spread = max(raw_times.values()) - min(raw_times.values())
        if spread > MAX_SPREAD: gaps.append('CROSS_METRIC_RAW_SAMPLE_SKEW')
    if not gaps and values['valid']==1 and values['local']+values['bootstrap'] != 1:
        gaps.append('MODE_FLAGS_CONTRADICTORY')
    classification = 'INSUFFICIENT_EVIDENCE'
    observed_mode = 'UNVERIFIED'
    if not gaps:
        if values['valid'] != 1:
            classification = 'INVALID_DNS_GUARD_STATE_SAMPLED'
        else:
            observed_mode = 'LOCAL' if values['local']==1 else 'BOOTSTRAP'
            classification = 'DNS_GUARD_MODE_SAMPLED_ONLY'
    report = {
        'schema': SCHEMA,
        'source_identity': 'LOCAL_VM_ENDPOINT_127_0_0_1_8428',
        'source_authenticity': 'NOT_CRYPTOGRAPHICALLY_ATTESTED',
        'source_transport': 'HTTP_LOOPBACK_FIXED_EIGHT_NONATOMIC_GETS',
        'timestamp_basis': 'VM_TIMESTAMP_FUNCTION_VALUE_NOT_VECTOR_EVALUATION_TIME',
        'evaluation_epoch_utc': now,
        'raw_sample_timestamps_utc': {k:(str(raw_times[k]) if raw_times[k] is not None else None) for k in NAMES},
        'raw_sample_age_seconds': ages,
        'collection_age_seconds': collection_age,
        'cross_metric_sample_spread_seconds': str(spread) if spread is not None else None,
        'classification': classification,
        'sampled_mode': observed_mode,
        'gaps': sorted(set(gaps)),
        'samples_per_metric': 1,
        'two_distinct_post_gap_samples': False,
        'sampling_recovered': 'NOT_ESTABLISHED',
        'dns_health': 'NOT_ESTABLISHED',
        'root_cause': 'UNDETERMINED',
        'quality_gate_decision': 'ABSTAIN_NO_MODEL_INFERENCE',
        'model_requests': 0,
        'model_action_authority': 'NONE',
        'remediation_authorized': False,
        'deployment_gate': 'HOLD',
    }
    if len(json.dumps(report,sort_keys=True,separators=(',',':')).encode('ascii'))>MAX_OUTPUT_BYTES:
        raise Hold('REPORT_TOO_LARGE')
    return report

def observe(now, getter=fetch):
    values, times = {}, {}
    for k,name in METRICS:
        values[k] = parse(name,'value',getter(name,'value',now),now)
        times[k] = parse(name,'sample_time',getter(name,'sample_time',now),now)
    return assess(values,times,now)

def vector(name,kind,now,val=None,eval_at=None,labels=None):
    return json.dumps({'status':'success','data':{'resultType':'vector','result':([] if val is None else [{
        'metric': ({'__name__':name} if kind=='value' else {}) if labels is None else labels,
        'value':[now if eval_at is None else eval_at,str(val)]}])}},sort_keys=True,separators=(',',':')).encode('ascii')

def fixture(now=1793530000):
    val = {'collection':now-25,'valid':1,'local':1,'bootstrap':0}
    times = {k:Decimal(now-25) for k in NAMES}
    return val,times,now

class Tests(unittest.TestCase):
    def baseline(self):
        return fixture()
    def holds(self,fn):
        with self.assertRaises(Hold): fn()
    def test_baseline(self):
        v,t,n=self.baseline(); r=assess(v,t,n)
        self.assertEqual(r['classification'],'DNS_GUARD_MODE_SAMPLED_ONLY')
        self.assertEqual(r['sampled_mode'],'LOCAL')
    def test_bootstrap(self):
        v,t,n=self.baseline(); v.update(local=0,bootstrap=1)
        self.assertEqual(assess(v,t,n)['sampled_mode'],'BOOTSTRAP')
    def test_invalid_guard(self):
        v,t,n=self.baseline(); v['valid']=0
        self.assertEqual(assess(v,t,n)['classification'],'INVALID_DNS_GUARD_STATE_SAMPLED')
    def test_stale_raw(self):
        v,t,n=self.baseline(); t['local']=Decimal(n-301)
        self.assertIn('LOCAL_RAW_SAMPLE_STALE', assess(v,t,n)['gaps'])
    def test_stale_collection(self):
        v,t,n=self.baseline(); v['collection']=n-121
        self.assertIn('COLLECTION_VALUE_STALE', assess(v,t,n)['gaps'])
    def test_missing_collection(self):
        v,t,n=self.baseline(); v['collection']=None
        self.assertIn('COLLECTION_VALUE_INVALID_OR_MISSING',assess(v,t,n)['gaps'])
    def test_future_raw(self):
        v,t,n=self.baseline(); t['local']=Decimal(n+6)
        self.assertIn('LOCAL_RAW_SAMPLE_IN_FUTURE',assess(v,t,n)['gaps'])
    def test_cross_metric_skew(self):
        v,t,n=self.baseline(); t['local']=Decimal(n-5)
        self.assertIn('CROSS_METRIC_RAW_SAMPLE_SKEW',assess(v,t,n)['gaps'])
    def test_two_flags(self):
        v,t,n=self.baseline(); v.update(local=1,bootstrap=1)
        self.assertIn('MODE_FLAGS_CONTRADICTORY',assess(v,t,n)['gaps'])
    def test_unobserved_recovery(self):
        v,t,n=self.baseline(); r=assess(v,t,n)
        self.assertIs(r['two_distinct_post_gap_samples'],False)
    def test_no_model(self):
        v,t,n=self.baseline(); r=assess(v,t,n)
        self.assertEqual(r['model_requests'],0)
    def test_no_health_proof(self):
        v,t,n=self.baseline(); self.assertEqual(assess(v,t,n)['dns_health'],'NOT_ESTABLISHED')
    def test_not_attested(self):
        v,t,n=self.baseline(); self.assertEqual(assess(v,t,n)['source_authenticity'],'NOT_CRYPTOGRAPHICALLY_ATTESTED')
    def test_query_whitelist(self):
        self.holds(lambda:make_path('up','value',1793530000))
    def test_query_fixed_host(self):
        self.assertTrue(make_path(NAMES['valid'],'sample_time',1793530000).startswith('/api/v1/query?'))
    def test_no_wrong_time(self):
        self.holds(lambda:make_path(NAMES['valid'],'value',0))
    def test_parse_valid(self):
        v,t,n=self.baseline(); self.assertEqual(parse(NAMES['local'],'value',vector(NAMES['local'],'value',n,1),n),1)
    def test_parse_time(self):
        v,t,n=self.baseline(); self.assertEqual(parse(NAMES['local'],'sample_time',vector(NAMES['local'],'sample_time',n,str(t['local'])),n),t['local'])
    def test_parse_empty(self):
        v,t,n=self.baseline(); self.assertIsNone(parse(NAMES['local'],'value',vector(NAMES['local'],'value',n),n))
    def test_parse_duplicate(self):
        v,t,n=self.baseline(); self.holds(lambda:parse(NAMES['local'],'value',b'{"status":"success","status":"error"}',n))
    def test_parse_invalid_json(self):
        v,t,n=self.baseline(); self.holds(lambda:parse(NAMES['local'],'value',b'not json',n))
    def test_parse_label_injection(self):
        v,t,n=self.baseline(); self.holds(lambda:parse(NAMES['local'],'value',vector(NAMES['local'],'value',n,1,labels={'__name__':NAMES['local'],'machine':'private'}),n))
    def test_parse_not200_shape(self):
        v,t,n=self.baseline(); self.holds(lambda:parse(NAMES['local'],'value',b'{}',n))
    def test_parse_noninteger(self):
        v,t,n=self.baseline(); self.holds(lambda:parse(NAMES['local'],'value',vector(NAMES['local'],'value',n,'1.1'),n))
    def test_parse_nan(self):
        v,t,n=self.baseline(); self.holds(lambda:parse(NAMES['local'],'value',vector(NAMES['local'],'value',n,'NaN'),n))
    def test_parse_eval_skew(self):
        v,t,n=self.baseline(); self.holds(lambda:parse(NAMES['local'],'value',vector(NAMES['local'],'value',n,1,eval_at=n-6),n))
    def test_parse_sample_time_range(self):
        v,t,n=self.baseline(); self.holds(lambda:parse(NAMES['local'],'sample_time',vector(NAMES['local'],'sample_time',n,1),n))
    def test_parse_multi_series(self):
        v,t,n=self.baseline(); obj=json.loads(vector(NAMES['local'],'value',n,1)); obj['data']['result']*=2
        self.holds(lambda:parse(NAMES['local'],'value',json.dumps(obj).encode(),n))
    def test_parse_overflow(self):
        v,t,n=self.baseline(); self.holds(lambda:parse(NAMES['local'],'value',b'A'*(MAX_RESPONSE_BYTES+1),n))
    def test_observe_calls_exact_eight(self):
        v,t,n=self.baseline(); calls=[]
        def get(name,kind,now):
            calls.append((name,kind,now))
            k=next(k for k,x in METRICS if x==name)
            return vector(name,kind,now,v[k] if kind=='value' else str(t[k]))
        r=observe(n,get)
        self.assertEqual(len(calls),8)
        self.assertEqual(r['classification'],'DNS_GUARD_MODE_SAMPLED_ONLY')
    def test_missing_is_abstain(self):
        v,t,n=self.baseline(); t['valid']=None
        r=assess(v,t,n);self.assertEqual(r['quality_gate_decision'],'ABSTAIN_NO_MODEL_INFERENCE')
    def test_value_wrong_keys(self):
        v,t,n=self.baseline();v['foo']=1;self.holds(lambda:assess(v,t,n))
    def test_raw_wrong_type(self):
        v,t,n=self.baseline();t['local']=n;self.holds(lambda:assess(v,t,n))
    def test_empty_vector_is_gap(self):
        v,t,n=self.baseline();v['local']=None;self.assertIn('LOCAL_VALUE_OR_TIMESTAMP_MISSING',assess(v,t,n)['gaps'])
    def test_report_size(self):
        v,t,n=self.baseline();self.assertLess(len(json.dumps(assess(v,t,n)).encode()),MAX_OUTPUT_BYTES)
    def test_matrix_missing_case(self):
        self.assertEqual(dict(matrix())["missing_local"]["classification"], "INSUFFICIENT_EVIDENCE")
    def test_matrix_all_abstain(self):
        self.assertTrue(all(r["model_requests"]==0 for _,r in matrix()))
    def test_no_actions(self):
        v,t,n=self.baseline();self.assertFalse(assess(v,t,n)['remediation_authorized'])

    def test_real_vm_stats_accepted_on_value(self):
        v,t,n=self.baseline(); obj=json.loads(vector(NAMES['local'],'value',n,1))
        obj['stats']={'executionTimeMsec':2,'seriesFetched':'1'}
        self.assertEqual(parse(NAMES['local'],'value',json.dumps(obj).encode(),n),1)
    def test_real_vm_stats_accepted_on_timestamp(self):
        v,t,n=self.baseline(); obj=json.loads(vector(NAMES['local'],'sample_time',n,n-25))
        obj['stats']={'executionTimeMsec':0,'seriesFetched':'2'}
        self.assertEqual(parse(NAMES['local'],'sample_time',json.dumps(obj).encode(),n),Decimal(n-25))
    def test_stats_missing_field_rejected(self):
        v,t,n=self.baseline(); obj=json.loads(vector(NAMES['local'],'value',n,1))
        obj['stats']={'seriesFetched':'1'}
        self.holds(lambda:parse(NAMES['local'],'value',json.dumps(obj).encode(),n))
    def test_stats_unexpected_field_rejected(self):
        v,t,n=self.baseline(); obj=json.loads(vector(NAMES['local'],'value',n,1))
        obj['stats']={'executionTimeMsec':1,'seriesFetched':'1','unexpected':'x'}
        self.holds(lambda:parse(NAMES['local'],'value',json.dumps(obj).encode(),n))
    def test_stats_bad_series_count_rejected(self):
        v,t,n=self.baseline(); obj=json.loads(vector(NAMES['local'],'value',n,1))
        obj['stats']={'executionTimeMsec':1,'seriesFetched':'bad'}
        self.holds(lambda:parse(NAMES['local'],'value',json.dumps(obj).encode(),n))
    def test_stats_bad_elapsed_rejected(self):
        v,t,n=self.baseline(); obj=json.loads(vector(NAMES['local'],'value',n,1))
        obj['stats']={'executionTimeMsec':-1,'seriesFetched':'1'}
        self.holds(lambda:parse(NAMES['local'],'value',json.dumps(obj).encode(),n))
    def test_stats_bool_elapsed_rejected(self):
        v,t,n=self.baseline(); obj=json.loads(vector(NAMES['local'],'value',n,1))
        obj['stats']={'executionTimeMsec':True,'seriesFetched':'1'}
        self.holds(lambda:parse(NAMES['local'],'value',json.dumps(obj).encode(),n))
    def test_stats_duplicate_key_rejected(self):
        v,t,n=self.baseline()
        blob=vector(NAMES['local'],'value',n,1)
        blob=blob[:-1]+b',"stats":{"executionTimeMsec":1,"seriesFetched":"1","seriesFetched":"2"}}'
        self.holds(lambda:parse(NAMES['local'],'value',blob,n))
    def test_partial_status_rejected(self):
        v,t,n=self.baseline(); obj=json.loads(vector(NAMES['local'],'value',n,1))
        obj['stats']={'executionTimeMsec':1,'seriesFetched':'1'}
        obj['isPartial']=True
        self.holds(lambda:parse(NAMES['local'],'value',json.dumps(obj).encode(),n))
    def test_unexpected_top_key_rejected(self):
        v,t,n=self.baseline(); obj=json.loads(vector(NAMES['local'],'value',n,1))
        obj['warnings']=['unexpected']
        self.holds(lambda:parse(NAMES['local'],'value',json.dumps(obj).encode(),n))
    def test_stats_not_used_for_evidence(self):
        v,t,n=self.baseline(); calls=[]
        def get(name,kind,now):
            calls.append((name,kind))
            key=next(k for k,s in METRICS if s==name)
            obj=json.loads(vector(name,kind,now,v[key] if kind=='value' else str(t[key])))
            obj['stats']={'executionTimeMsec':2,'seriesFetched':'1'}
            return json.dumps(obj).encode()
        report=observe(n,get)
        self.assertEqual(len(calls),8)
        self.assertEqual(report['model_requests'],0)
        self.assertEqual(report['source_authenticity'],'NOT_CRYPTOGRAPHICALLY_ATTESTED')
        self.assertEqual(report['quality_gate_decision'],'ABSTAIN_NO_MODEL_INFERENCE')


def matrix():
    v,t,n=fixture()
    data=[('baseline',v,t)]
    for label,change in (
        ('missing_local', {'value':('local',None)}),
        ('stale_local', {'time':('local',Decimal(n-301))}),
        ('future_local', {'time':('local',Decimal(n+6))}),
        ('stale_collection', {'value':('collection',n-121)}),
        ('invalid_guard', {'value':('valid',0)}),
        ('raw_sample_skew', {'time':('local',Decimal(n-5))}),
    ):
        va,ra,nn=fixture()
        if 'value' in change:
            key,new=change['value'];va[key]=new
        if 'time' in change:
            key,new=change['time'];ra[key]=new
        data.append((label,va,ra))
    return [(name,assess(va,ra,n)) for name,va,ra in data]

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--self-test',action='store_true')
    mode.add_argument('--fixture-matrix',action='store_true')
    mode.add_argument('--live-vm-readonly',action='store_true',help='EXPLICIT local loopback VM 8 GETs; no model')
    args=parser.parse_args(argv)
    print('=== LOCAL AI AGENT / C.63.8.1 / VM STATS ENVELOPE HOTFIX ===')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    try:
        if args.self_test:
            print('MODE=OFFLINE_SELF_TEST NETWORK=NO MODEL=NO HOST_READS=NO')
            result=unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
            print(f'C6381_SELFTESTS={result.testsRun-len(result.failures)-len(result.errors)}/{result.testsRun}')
            print('C6381_RESULT='+('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_TEST_FAILURE'))
            return 0 if result.wasSuccessful() else 1
        if args.fixture_matrix:
            print('MODE=OFFLINE_FIXTURE_MATRIX NETWORK=NO MODEL=NO HOST_READS=NO')
            cases=matrix()
            for name,report in cases:
                print(f'SCENARIO={name} CLASSIFICATION={report["classification"]} MODEL_REQUESTS={report["model_requests"]}')
            print(f'C6381_RESULT=PASS_{len(cases)}_SYNTHETIC_SOURCE_CASES')
            return 0
        print('MODE=MANUAL_LOCAL_VM_READONLY REQUESTS=8 LOCALHOST_ONLY=YES NO_MODEL=YES NO_FILES=YES')
        now=now_clock(int(time.time()))
        report=observe(now)
        print(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=True))
        print('C6381_RESULT=PASS_READONLY_OBSERVATION_WITH_UNATTESTED_SOURCE_ABSTAIN')
        return 0
    except Hold as exc:
        print('C6381_RESULT=HOLD_'+str(exc))
        print('MODEL_REQUESTS=0 DEPLOYMENT_GATE=HOLD')
        return 2

if __name__ == '__main__':
    sys.exit(main())
