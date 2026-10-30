#!/usr/bin/env python3
"""V0.21C.57 — self-contained, manual, READ-ONLY historical VM + Loki lab.

Replaces the runtime *chain* C49..C56.5 for one strictly fixed historical
incident with 7 VM matrix GETs + 1 Loki aggregate GET. No import of old
laboratory files, no subprocess, file writes, model, executor or HCC endpoint.
The HCC frozen event model is NOT executed here: compares a separately
implemented sampled event-window derivation to known operator-observed C56.2
windows. This is NOT deployed-HCC parity nor cryptographic source attestation.

Usage: python3 -B THIS.py --self-test | --historical-preflight
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import http.client
import json
import os
import re
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True
VM_HOST, VM_PORT = '127.0.0.1', 8428
LOKI_HOST, LOKI_PORT = '127.0.0.1', 3100
UTC = timezone.utc
WARSAW = ZoneInfo('Europe/Warsaw')
VM_START = int(datetime(2026,10,27,15,40,tzinfo=UTC).timestamp())
VM_END = VM_START + 3600
LOKI_START = int(datetime(2026,10,27,15,56,tzinfo=UTC).timestamp())
LOKI_END = int(datetime(2026,10,27,16,10,tzinfo=UTC).timestamp())
STEP = 60
NAME_PREFIX = 'asus_edge_dns_guard_'
VM_NAMES = tuple(NAME_PREFIX + key for key in (
    'collection_timestamp_seconds', 'state_valid', 'mode_local', 'mode_bootstrap',
    'last_transition_timestamp_seconds', 'fallback_since_timestamp_seconds',
    'fallback_transitions_runtime_total'))
LOKI_QUERY = 'sum(count_over_time({job="dns-activity",dataset="dns-activity",source="pihole"}[1m]))'
COUNTS_GOLDEN = (82,24,54,56,57,76,141,39,26,20,17,17,90,21,6)
WINDOWS_GOLDEN = (
    ('BOOTSTRAP_OBSERVED','2026-10-27T17:01:35+01:00','2026-10-27T17:02:39+01:00'),
    ('LOCAL_RESTORED','2026-10-27T17:04:48+01:00','2026-10-27T17:05:55+01:00'),
)
VM_COUNTS_GOLDEN = (58,3,56,5)  # LOCAL, BOOT, distinct collections, repeats
MAX_RESPONSE = 65536
MAX_REPORT = 12000
SCHEMA = 'dns-guard-pihole-consolidated-readonly.v1'
NUMBER_RE = re.compile(r'(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,9})?\Z')

class Hold(Exception):
    pass

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,
                      separators=(',', ':'),allow_nan=False).encode('utf-8')

def no_duplicate_keys(pairs):
    d = {}
    for key, value in pairs:
        if key in d: raise Hold('JSON_DUPLICATE_KEY')
        d[key] = value
    return d

def read_json(raw):
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_RESPONSE:
        raise Hold('RESPONSE_INVALID_SIZE')
    try:
        return json.loads(raw, object_pairs_hook=no_duplicate_keys,
                          parse_constant=lambda _: (_ for _ in ()).throw(Hold('JSON_NONFINITE')))
    except (ValueError, UnicodeError, TypeError) as exc:
        raise Hold('JSON_PARSE_FAILED') from exc

def bounded_get(port, path, *, connection_factory=None):
    if port not in (VM_PORT,LOKI_PORT) or not path.startswith('/') or '\n' in path or '\r' in path:
        raise Hold('HTTP_NOT_ALLOWLISTED')
    conn = (http.client.HTTPConnection if connection_factory is None else connection_factory)(
        '127.0.0.1',port,timeout=8)
    try:
        conn.request('GET',path,headers={'Accept':'application/json','Connection':'close'})
        reply = conn.getresponse()
        raw = reply.read(MAX_RESPONSE+1)
        if reply.status != 200 or len(raw)>MAX_RESPONSE:
            raise Hold('HTTP_NON200_OR_LIMIT')
        return raw
    except (OSError,TimeoutError,http.client.HTTPException) as exc:
        raise Hold('HTTP_UNAVAILABLE') from exc
    finally:
        conn.close()

def vm_path(metric):
    if metric not in VM_NAMES:
        raise Hold('VM_SELECTOR_UNEXPECTED')
    return '/api/v1/query_range?' + urlencode((
        ('query',metric),('start',VM_START),('end',VM_END),('step',STEP)))

def vm_parse(metric, raw):
    if metric not in VM_NAMES: raise Hold('VM_SELECTOR_UNEXPECTED')
    obj = read_json(raw)
    if (type(obj) is not dict or obj.get('status') != 'success' or
        type(obj.get('data')) is not dict or obj['data'].get('resultType')!='matrix'):
        raise Hold('VM_MATRIX_INVALID')
    series = obj['data'].get('result')
    if (type(series) is not list or len(series)!=1 or type(series[0]) is not dict or
        series[0].get('metric') != {'__name__': metric}):
        raise Hold('VM_SERIES_IDENTITY')
    values = series[0].get('values')
    if type(values) is not list or len(values)>61:
        raise Hold('VM_SERIES_ROWS')
    result = {}
    for pair in values:
        if type(pair) is not list or len(pair)!=2:raise Hold('VM_PAIR_SHAPE')
        ts, val = pair
        if (type(ts) not in (int,float) or not (VM_START <= ts <= VM_END) or
                ts!=int(ts) or (int(ts)-VM_START)%60 or int(ts) in result):
            raise Hold('VM_SAMPLE_CLOCK')
        if type(val) is not str or not NUMBER_RE.fullmatch(val):
            raise Hold('VM_VALUE_FORMAT')
        try: num = Decimal(val)
        except InvalidOperation as exc: raise Hold('VM_VALUE_DECIMAL') from exc
        if not num.is_finite() or num!=int(num) or num>10**12:
            raise Hold('VM_VALUE_NOT_BOUNDED_INT')
        number = int(num)
        if metric in (VM_NAMES[1],VM_NAMES[2],VM_NAMES[3]) and number not in (0,1):
            raise Hold('VM_BOOLEAN_FLAG_INVALID')
        result[int(ts)] = number
    return result

def vm_read(get=bounded_get):
    return {metric:vm_parse(metric,get(VM_PORT,vm_path(metric))) for metric in VM_NAMES}

def utc_to_local(epoch):
    return datetime.fromtimestamp(epoch,UTC).astimezone(WARSAW).isoformat(timespec='seconds')

def derive_vm(metrics):
    if type(metrics) is not dict or set(metrics)!=set(VM_NAMES):
        raise Hold('VM_METRIC_SET_INVALID')
    if any(type(x) is not dict for x in metrics.values()):
        raise Hold('VM_METRIC_MAP_INVALID')
    rows=[]
    unique=[]
    duplicates=0
    nlocal=nboot=0
    for t in range(VM_START,VM_END+1,STEP):
        if any(t not in metrics[m] for m in VM_NAMES):
            raise Hold('VM_GRID_INCOMPLETE')
        col,valid,local,boot,transition,fb,counter = (metrics[m][t] for m in VM_NAMES)
        if any(type(x) is not int for x in (col,valid,local,boot,transition,fb,counter)):
            raise Hold('VM_SAMPLE_TYPE')
        if not (t-180 <= col <= t+5 and col>0 and valid==1 and local+boot==1
                and local in (0,1) and boot in (0,1)):
            raise Hold('VM_STALE_OR_CONFLICT')
        if transition > col+5 or fb > col+5 or counter>10**12:
            raise Hold('VM_TIMELINE_INCONSISTENT')
        row=(col,valid,local,boot,transition,fb,counter)
        rows.append(row)
        if local: nlocal+=1
        else: nboot+=1
        if unique and col==unique[-1][0]:
            if row!=unique[-1]:raise Hold('VM_CONTRADICTORY_REPLAY')
            duplicates+=1
            continue
        if unique and col<unique[-1][0]:raise Hold('VM_COLLECTION_OUT_OF_ORDER')
        unique.append(row)
    windows=[]
    for a,b in zip(unique,unique[1:]):
        delta=b[0]-a[0]
        if not 0<delta<=180:raise Hold('VM_COLLECTION_GAP')
        counter_delta=b[6]-a[6]
        if counter_delta<0 or counter_delta>1:raise Hold('VM_COUNTER_RESET_OR_GAP')
        if a[2]==b[2]:
            if counter_delta!=0: raise Hold('VM_COUNTER_CHANGED_WITHOUT_MODE')
            continue
        if b[3]==1:
            if counter_delta!=1 or not b[5]:raise Hold('VM_BOOTSTRAP_UNCORROBORATED')
            kind='BOOTSTRAP_OBSERVED'
        else:
            if counter_delta!=0:raise Hold('VM_RESTORE_COUNTER_CONFLICT')
            kind='LOCAL_RESTORED'
        windows.append((kind,utc_to_local(a[0]),utc_to_local(b[0])))
    return {
        'grid_rows':len(rows),'local_rows':nlocal,'bootstrap_rows':nboot,
        'distinct_collections':len(unique),'repeated_collections':duplicates,
        'windows':tuple(windows),
    }

def loki_path():
    return '/loki/api/v1/query_range?' + urlencode({
        'query':LOKI_QUERY,'start':str(LOKI_START*10**9),
        'end':str(LOKI_END*10**9),'step':'60'})

def loki_parse(raw):
    obj=read_json(raw)
    if type(obj) is not dict or obj.get('status')!='success':raise Hold('LOKI_STATUS_INVALID')
    data=obj.get('data')
    if type(data) is not dict or data.get('resultType')!='matrix':raise Hold('LOKI_RESULT_TYPE')
    items=data.get('result')
    if (type(items) is not list or len(items)!=1 or type(items[0]) is not dict or
        items[0].get('metric')!={}):raise Hold('LOKI_SERIES_INVALID')
    values=items[0].get('values')
    if type(values) is not list or len(values)!=15:raise Hold('LOKI_COVERAGE')
    result={}
    for pair in values:
        if type(pair) is not list or len(pair)!=2:raise Hold('LOKI_PAIR_SHAPE')
        t,val=pair
        if (type(t) not in (int,float) or t!=int(t) or
            not LOKI_START <= t <= LOKI_END or
            (int(t)-LOKI_START)%60 or int(t) in result):
            raise Hold('LOKI_TIMESTAMP_INVALID')
        if type(val) is not str or not re.fullmatch(r'(?:0|[1-9][0-9]{0,6})',val):
            raise Hold('LOKI_COUNT_INVALID')
        result[int(t)]=int(val)
    if set(result)!=set(range(LOKI_START,LOKI_END+1,60)):
        raise Hold('LOKI_MINUTES_NOT_CONTIGUOUS')
    return tuple(result[t] for t in range(LOKI_START,LOKI_END+1,60))

def align(vm,counts):
    if (vm['grid_rows'],vm['local_rows'],vm['bootstrap_rows'],
        vm['distinct_collections'],vm['repeated_collections']) != (61,*VM_COUNTS_GOLDEN):
        raise Hold('VM_OPERATOR_BASELINE_DIFFERENT')
    if vm['windows'] != WINDOWS_GOLDEN:raise Hold('VM_OBSERVED_WINDOWS_DIFFERENT')
    if counts != COUNTS_GOLDEN:raise Hold('LOKI_OPERATOR_BASELINE_DIFFERENT')
    overlaps=[]
    for kind,first,last in vm['windows']:
        begin=datetime.fromisoformat(first)
        end=datetime.fromisoformat(last)
        if begin>=end: raise Hold('EVENT_UNCERTAINTY_WINDOW_INVALID')
        values=[]
        for i,number in enumerate(counts):
            bin_end=datetime.fromtimestamp(LOKI_START+i*60,UTC).astimezone(WARSAW)
            bin_start=bin_end-timedelta(minutes=1)
            sec=int((min(bin_end,end)-max(bin_start,begin)).total_seconds())
            if sec>0:
                values.append({'minute_end_cet':bin_end.strftime('%H:%M'),
                               'count_for_full_minute':number,'overlap_seconds':sec})
        if len(values)!=2:raise Hold('INCIDENT_OVERLAP_BINS_UNEXPECTED')
        overlaps.append({'event':kind,'uncertainty_window_start_cet':first,
                         'uncertainty_window_end_cet':last,
                         'overlapping_full_minute_counts_sum_not_event_count':sum(v['count_for_full_minute'] for v in values),
                         'overlapping_bins':values})
    if [x['overlapping_full_minute_counts_sum_not_event_count'] for x in overlaps]!=[180,37]:
        raise Hold('INCIDENT_COUNT_PARITY_CHANGED')
    out={
        'schema':SCHEMA,'deployment_gate':'HOLD',
        'source':{'vm':'SEVEN_FIXED_LOOPBACK_MATRIX_GETS',
                  'loki':'ONE_FIXED_LOOPBACK_AGGREGATE_GET',
                  'source_authenticated':False,'hcc_event_model_executed':False,
                  'hcc_deployed_instance_contacted':False,
                  'operator_baseline_exact_match':True,
                  'raw_log_lines_read':False,'model_or_executor_contacted':False},
        'vm':{'window_utc':'2026-10-27T15:40:00Z/2026-10-27T16:40:00Z',
              'seven_series_rows':vm['grid_rows'],
              'local_rows':vm['local_rows'],'bootstrap_rows':vm['bootstrap_rows'],
              'distinct_collections':vm['distinct_collections'],
              'repeated_collections':vm['repeated_collections'],
              'classification':'FALLBACK_THEN_LOCAL_RESTORED_SAMPLED',
              'observed_transition_windows':len(vm['windows'])},
        'loki':{'series':'job="dns-activity",dataset="dns-activity",source="pihole"',
                'minute_bins':len(counts),'minute_counts_sum':sum(counts),
                'minute_counts':list(counts)},
        'transitions':overlaps,
        'limitations':['SAMPLED_ONLY','EXACT_SWITCH_TIMES_UNPROVEN',
                       'WHOLE_MINUTE_COUNTS_NOT_EVENT_COUNTS',
                       'DNS_SUCCESS_OR_PATH_HEALTH_UNPROVEN',
                       'TEMPORAL_OVERLAP_NOT_CAUSALITY',
                       'NO_ATOMIC_VM_LOKI_SNAPSHOT',
                       'NO_CRYPTOGRAPHIC_SOURCE_ATTESTATION',
                       'HCC_FROZEN_MODEL_AND_DEPLOYED_PARITY_NOT_TESTED',
                       'NOT_VALIDATED_AGAINST_C54_SCHEMA'],
    }
    raw=canonical(out)
    if len(raw)>MAX_REPORT:raise Hold('REPORT_TOO_LARGE')
    return out,raw

def report_text(obj):
    event1,event2=obj['transitions']
    return ('# DNS Guard + Pi-hole — raport historyczny C.57 (roboczy)\n\n'
            'Okno VictoriaMetrics: 27.10.2026, 16:40–17:40 CET.\n'
            'Agregaty Loki: 15 minut, 16:56–17:10 CET (czas końca przedziału).\n'
            'Odczyt: siedem ustalonych metryk VM i jeden licznikowy agregat Loki, tylko loopback.\n\n'
            '## Przejścia DNS Guard — zakres niepewności próbkowania\n'
            f'- BOOTSTRAP: {event1["uncertainty_window_start_cet"][11:19]}–{event1["uncertainty_window_end_cet"][11:19]} CET; całe pokrywające minuty: {event1["overlapping_full_minute_counts_sum_not_event_count"]} wpisów.\n'
            f'- LOCAL: {event2["uncertainty_window_start_cet"][11:19]}–{event2["uncertainty_window_end_cet"][11:19]} CET; całe pokrywające minuty: {event2["overlapping_full_minute_counts_sum_not_event_count"]} wpisów.\n\n'
            f'Pełna próba Loki: {obj["loki"]["minute_bins"]}/15 minut, {obj["loki"]["minute_counts_sum"]} wpisów.\n'
            'Zliczenia minut obejmują też czas poza niepewnymi oknami przełączeń.\n'
            'Nie potwierdzono dokładnej chwili zmiany, przyczynowości, poprawności odpowiedzi DNS ani deployed HCC parity.\n'
            'Wyniki porównano z wcześniejszymi obserwacjami operatora, a nie z kryptograficznie poświadczonym źródłem.\n'
            'W tym uproszczonym module nie uruchomiono zamrożonego modelu HCC ani walidatora C54.\n'
            'DEPLOYMENT_GATE=HOLD. Raport roboczy, wyłącznie do ręcznej oceny.\n')

def synthetic_vm():
    """Valid synthetic sample: same windows as historical operator observation."""
    result={n:{} for n in VM_NAMES}
    prev=None
    repeats={3,8,13,30,40}
    for i,t in enumerate(range(VM_START,VM_END+1,STEP)):
        if i in repeats:
            row=prev
        else:
            c=t-25
            if i==23:c=t-21
            if i==25:c=t-12
            if i==26:c=t-5
            boot=int(23<=i<=25)
            row=(c,1,1-boot,boot,VM_START+23*60-45 if 23<=i<=25 else (VM_START+26*60-40 if i>=26 else 0),
                 VM_START+23*60-45 if boot else 0,int(i>=23))
        for name,value in zip(VM_NAMES,row):result[name][t]=value
        prev=row
    return result

def vm_payload(name,mapping):
    return canonical({'status':'success','data':{'resultType':'matrix','result':[
        {'metric':{'__name__':name},'values':[[t,str(v)] for t,v in mapping.items()]}]}})

def loki_payload(counts=COUNTS_GOLDEN):
    return canonical({'status':'success','data':{'resultType':'matrix','result':[
        {'metric':{},'values':[[LOKI_START+i*60,str(v)] for i,v in enumerate(counts)]}]}})

class Tests(unittest.TestCase):
    def fixture(self):return synthetic_vm()
    def test_01_vm_fixture(self):
        d=derive_vm(self.fixture());self.assertEqual((d['local_rows'],d['bootstrap_rows'],d['distinct_collections'],d['repeated_collections']),VM_COUNTS_GOLDEN)
    def test_02_event_windows(self):self.assertEqual(derive_vm(self.fixture())['windows'],WINDOWS_GOLDEN)
    def test_03_vm_parse(self):
        d=self.fixture();self.assertEqual(vm_parse(VM_NAMES[0],vm_payload(VM_NAMES[0],d[VM_NAMES[0]])),d[VM_NAMES[0]])
    def test_04_vm_missing(self):
        d=self.fixture();del d[VM_NAMES[0]][VM_START]
        with self.assertRaises(Hold):derive_vm(d)
    def test_05_vm_conflict(self):
        d=self.fixture();d[VM_NAMES[1]][VM_START]=0
        with self.assertRaises(Hold):derive_vm(d)
    def test_06_vm_extra_series(self):
        p=read_json(vm_payload(VM_NAMES[1],self.fixture()[VM_NAMES[1]]));p['data']['result'].append(p['data']['result'][0])
        with self.assertRaises(Hold):vm_parse(VM_NAMES[1],canonical(p))
    def test_07_vm_duplicate_sample(self):
        p=read_json(vm_payload(VM_NAMES[0],self.fixture()[VM_NAMES[0]]));p['data']['result'][0]['values'].append(p['data']['result'][0]['values'][0])
        with self.assertRaises(Hold):vm_parse(VM_NAMES[0],canonical(p))
    def test_08_duplicate_json_key(self):
        with self.assertRaises(Hold):read_json(b'{"x":1,"x":2}')
    def test_09_nonfinite_json(self):
        with self.assertRaises(Hold):read_json(b'{"value":NaN}')
    def test_10_wrong_metric(self):
        with self.assertRaises(Hold):vm_parse(VM_NAMES[0],vm_payload(VM_NAMES[1],self.fixture()[VM_NAMES[1]]))
    def test_11_loki_parse(self):self.assertEqual(loki_parse(loki_payload()),COUNTS_GOLDEN)
    def test_12_loki_gap(self):
        p=read_json(loki_payload());p['data']['result'][0]['values'].pop()
        with self.assertRaises(Hold):loki_parse(canonical(p))
    def test_13_loki_duplicate(self):
        p=read_json(loki_payload());p['data']['result'][0]['values'][1][0]=LOKI_START
        with self.assertRaises(Hold):loki_parse(canonical(p))
    def test_14_loki_other_type(self):
        p=read_json(loki_payload());p['data']['resultType']='streams'
        with self.assertRaises(Hold):loki_parse(canonical(p))
    def test_15_join(self):
        j,raw=align(derive_vm(self.fixture()),COUNTS_GOLDEN)
        self.assertEqual(j['loki']['minute_counts_sum'],726);self.assertEqual(raw,canonical(j))
    def test_16_event_sums(self):
        j,_=align(derive_vm(self.fixture()),COUNTS_GOLDEN)
        self.assertEqual([w['overlapping_full_minute_counts_sum_not_event_count'] for w in j['transitions']],[180,37])
    def test_17_baseline_loki_diff_hold(self):
        x=list(COUNTS_GOLDEN);x[0]+=1
        with self.assertRaises(Hold):align(derive_vm(self.fixture()),tuple(x))
    def test_18_baseline_vm_diff_hold(self):
        d=self.fixture();d[VM_NAMES[0]][VM_START]=VM_START-181
        with self.assertRaises(Hold):align(derive_vm(d),COUNTS_GOLDEN)
    def test_19_event_window_diff_hold(self):
        d=self.fixture();t=VM_START+23*60;d[VM_NAMES[0]][t]-=1
        with self.assertRaises(Hold):align(derive_vm(d),COUNTS_GOLDEN)
    def test_20_report_gate(self):
        j,_=align(derive_vm(self.fixture()),COUNTS_GOLDEN)
        self.assertIn('DEPLOYMENT_GATE=HOLD',report_text(j))
    def test_21_report_no_authority(self):
        j,_=align(derive_vm(self.fixture()),COUNTS_GOLDEN)
        self.assertFalse(j['source']['source_authenticated']);self.assertFalse(j['source']['hcc_event_model_executed'])
    def test_22_canonical_deterministic(self):
        j,_=align(derive_vm(self.fixture()),COUNTS_GOLDEN)
        self.assertEqual(canonical(j),canonical(j))
    def test_23_paths_are_fixed(self):
        self.assertEqual(len(VM_NAMES),7);self.assertIn('query_range',loki_path())
    def test_24_unknown_metric_hold(self):
        with self.assertRaises(Hold):vm_path('malicious')
    def test_25_empty_oversize_hold(self):
        with self.assertRaises(Hold):read_json(b'')
        with self.assertRaises(Hold):read_json(b'X'*(MAX_RESPONSE+1))
    def test_26_vm_counter_decrease_hold(self):
        d=self.fixture();d[VM_NAMES[6]][VM_START+30*60]=-1
        with self.assertRaises(Hold):derive_vm(d)
    def test_27_vm_bad_replay_hold(self):
        d=self.fixture();t=VM_START+3*60;d[VM_NAMES[6]][t]=1
        with self.assertRaises(Hold):derive_vm(d)
    def test_28_loki_negative_hold(self):
        p=read_json(loki_payload());p['data']['result'][0]['values'][0][1]='-1'
        with self.assertRaises(Hold):loki_parse(canonical(p))
    def test_29_loki_labels_hold(self):
        p=read_json(loki_payload());p['data']['result'][0]['metric']={'foo':'bar'}
        with self.assertRaises(Hold):loki_parse(canonical(p))
    def test_30_exact_requests_offline(self):
        d=self.fixture();calls=[]
        def fake(port,path):
            calls.append((port,path))
            for n in VM_NAMES:
                if path==vm_path(n):return vm_payload(n,d[n])
            if path==loki_path():return loki_payload()
            raise AssertionError('NONALLOWLISTED')
        metrics=vm_read(fake); counts=loki_parse(fake(LOKI_PORT,loki_path()))
        align(derive_vm(metrics),counts)
        self.assertEqual(len(calls),8)
        self.assertEqual([p for p,_ in calls],[VM_PORT]*7+[LOKI_PORT])


def selftest():
    with patch('http.client.HTTPConnection',side_effect=AssertionError('NETWORK_DURING_OFFLINE_SELFTEST')):
        result=unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    successes=result.testsRun-len(result.failures)-len(result.errors)
    ok=result.wasSuccessful() and result.testsRun==30
    print(f'V021C57_SELFTESTS={successes}/{result.testsRun}')
    print('SELFTEST_NETWORK=NO')
    print('V021C57_SELFTEST_RESULT=' + ('PASS_OFFLINE' if ok else 'HOLD'))
    return ok

def run_live():
    metrics=vm_read()
    vm=derive_vm(metrics)
    counts=loki_parse(bounded_get(LOKI_PORT,loki_path()))
    joint,raw=align(vm,counts)
    report=report_text(joint)
    print('=== V0.21C.57 / CONSOLIDATED INDEPENDENT READ-ONLY HOST LAB ===')
    print('VM=SEVEN_FIXED_LOOPBACK_GETS')
    print('LOKI=ONE_FIXED_AGGREGATE_LOOPBACK_GET')
    print('VM_GRID_ROWS='+str(vm['grid_rows']))
    print('VM_LOCAL_ROWS='+str(vm['local_rows']))
    print('VM_BOOTSTRAP_ROWS='+str(vm['bootstrap_rows']))
    print('VM_DISTINCT_COLLECTIONS='+str(vm['distinct_collections']))
    print('VM_REPEATS='+str(vm['repeated_collections']))
    print('LOKI_BINS='+str(len(counts))+'/15')
    print('LOKI_TOTAL='+str(sum(counts)))
    print('HISTORICAL_OPERATOR_BASELINE=EXACT_MATCH')
    print('HCC_MODEL_PARITY=NOT_TESTED_IN_THIS_MODULE')
    print('C54_SCHEMA_VALIDATION=NOT_PERFORMED')
    print('JOINT_SCHEMA='+SCHEMA)
    print('JOINT_SHA256='+hashlib.sha256(raw).hexdigest())
    print('JOINT_BYTES='+str(len(raw)))
    print('=== HOST_REPORT_BEGIN ===')
    print(report,end='')
    print('=== HOST_REPORT_END ===')
    print('RAW_LOG_LINES_READ=NO')
    print('OLLAMA_EXECUTOR_ASUS_HCC_CONTACTED=NO')
    print('FILES_WRITTEN=NO')
    print('DEPLOYMENT_GATE=HOLD')
    print('V021C57_RESULT=PASS_INDEPENDENT_DUAL_SOURCE_HOST_BASELINE_ONLY')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--self-test',action='store_true')
    group.add_argument('--historical-preflight',action='store_true')
    args=p.parse_args()
    if os.geteuid()==0:
        print('V021C57_RESULT=HOLD_ROOT_REFUSED')
        return 1
    if not selftest():
        print('DEPLOYMENT_GATE=HOLD');return 1
    if args.self_test:
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C57_RESULT=PASS_OFFLINE_SELFTEST_ONLY')
        return 0
    try:
        run_live()
        return 0
    except (Hold,OSError,ValueError,TypeError,KeyError,OverflowError) as exc:
        print('REASON='+type(exc).__name__)
        if isinstance(exc,Hold):print('HOLD_CODE='+str(exc))
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C57_RESULT=HOLD_NOT_APPROVED')
        return 1

if __name__=='__main__':
    sys.exit(main())
