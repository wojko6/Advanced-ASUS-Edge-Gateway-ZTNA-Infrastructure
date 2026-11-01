#!/usr/bin/env python3
"""Local AI Agent V0.21C.59.1: pinned C57/C58, historical VM+Loki -> Qwen shadow.

Two manual modes: --self-test (offline), --host-preflight (8 fixed loopback reads),
--qwen-shadow (same host reads, then local Ollama tags GET and bounded chat POST).
Model provides only five fixed code strings. It cannot change the trusted host
assessment or run tools, shell commands, executors, containers or dispatch.
Historical 2026-10-27 sampling only, no live DNS health inference.
"""
from __future__ import annotations
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).absolute().parent
C58_NAME = 'local_ai_agent_v021c58_c57_hcc_c54_compatibility_audit_v01.py'
C58_SHA = '90bce75195104f60bf07ed6a96ab017d6035698413343675f2de29d4d94b693c'
EXPECTED_C57_SHA = '557914157204f5b888459efacb4f0e6f13489ad6b21a91042c3be7e76c675b83'
EXPECTED_C54_SHA = '6855974fed1bdd9294893d18b2538b2e7713a78e2efa257e85a2d79cbb61c14d'
MODEL = 'qwen3.5:4b'
OLLAMA_HOST, OLLAMA_PORT = '127.0.0.1', 11435
SCHEMA = 'v0.21c59.dual-source-qwen-shadow.v1'
FIELDS = frozenset(('schema_version','observation_id','incident_code',
                    'log_activity_code','causality_code','dns_health_code','action'))
EXPECTED_CODES = {
    'incident_code': 'FALLBACK_THEN_LOCAL_RESTORED_SAMPLED',
    'log_activity_code': 'NONZERO_OVERLAPPING_MINUTE_BINS',
    'causality_code': 'NOT_ESTABLISHED',
    'dns_health_code': 'NOT_PROVEN',
    'action': 'NONE',
}
SUMMARY_KEYS = frozenset(('window_utc','vm_rows','vm_local','vm_bootstrap','distinct_collections',
                          'loki_minute_bins','loki_log_lines','window_1','window_2',
                          'overlap_full_minute_counts_not_event_counts','source_authentication',
                          'hcc_parity','deployed_hcc','causality','dns_health','deployment_gate'))
MAX_REQUEST, MAX_RESPONSE, MAX_MODEL_CONTENT = 4096, 8192, 1024

class Hold(Exception):
    pass


def no_dupes(pairs):
    o = {}
    for k, v in pairs:
        if k in o:
            raise Hold('DUPLICATE_JSON_KEY')
        o[k] = v
    return o


def strict_json(raw):
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_RESPONSE:
        raise Hold('HTTP_BODY_SIZE_INVALID')
    try:
        return json.loads(raw, object_pairs_hook=no_dupes,
                          parse_constant=lambda _: (_ for _ in ()).throw(Hold('JSON_NONFINITE')))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise Hold('JSON_INVALID') from exc


def pinned_c58(root=HERE):
    p = root / C58_NAME
    try:
        a = p.lstat()
        if (not stat.S_ISREG(a.st_mode) or a.st_uid != os.getuid() or a.st_nlink != 1
            or a.st_mode & 0o022 or not 100 <= a.st_size <= 100000):
            raise Hold('C58_SOURCE_OWNER_MODE_OR_SIZE')
        fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            b = os.fstat(fd)
            identity = lambda s: (s.st_dev, s.st_ino, s.st_uid, s.st_mode, s.st_size, s.st_mtime_ns)
            if identity(a) != identity(b):
                raise Hold('C58_SOURCE_RACE')
            raw = os.read(fd, 100001)
            if len(raw) != b.st_size or identity(b) != identity(os.fstat(fd)):
                raise Hold('C58_SOURCE_CHANGED')
        finally:
            os.close(fd)
    except OSError as exc:
        raise Hold('C58_SOURCE_UNAVAILABLE') from exc
    if hashlib.sha256(raw).hexdigest() != C58_SHA:
        raise Hold('C58_SOURCE_SHA256_MISMATCH')
    m = types.ModuleType('c59_pinned_c58')
    m.__file__ = str(p)
    exec(compile(raw, str(p), 'exec'), m.__dict__)
    return m


def deps():
    c58 = pinned_c58()
    c57, c54, c48 = c58.load_all()  # C58 pins each SHA256, owner and mode
    return c58, c57, c54, c48


def host_audit(c58,c57,c54,c48, metrics, counts):
    a = c58.audit(c57,c54,c48,metrics,counts)
    vm = a['vm']
    joint, raw = c57.align(vm,counts)
    if (hashlib.sha256(raw).hexdigest() != a['joint_sha256'] or
        a['joint_sha256'] != EXPECTED_C57_SHA or
        a['evidence_sha256'] != EXPECTED_C54_SHA or
        a['hcc_parity'] != 'FROZEN_MODEL_SAMPLED_WINDOWS_CONCORDANT' or
        a['c54_contract'] != 'INCIDENT_EVIDENCE_V1_VALIDATED_UNVERIFIED_PROVENANCE'):
        raise Hold('HOST_C58_AUDIT_NOT_SATISFIED')
    if (joint.get('deployment_gate')!='HOLD' or
        joint['source']['source_authenticated'] is not False or
        joint['source']['hcc_deployed_instance_contacted'] is not False or
        joint['source']['raw_log_lines_read'] is not False):
        raise Hold('HOST_PROVENANCE_ESCALATED')
    events=joint['transitions']
    if len(events)!=2 or [e['event'] for e in events]!=['BOOTSTRAP_OBSERVED','LOCAL_RESTORED']:
        raise Hold('HOST_EVENT_SEQUENCE_CHANGED')
    if (events[0]['overlapping_full_minute_counts_sum_not_event_count']!=180 or
        events[1]['overlapping_full_minute_counts_sum_not_event_count']!=37 or
        len(counts)!=15 or sum(counts)!=726):
        raise Hold('HOST_AGGREGATE_MISMATCH')
    summary={
        'window_utc':'2026-10-27T15:40:00Z/2026-10-27T16:40:00Z',
        'vm_rows':vm['grid_rows'], 'vm_local':vm['local_rows'],
        'vm_bootstrap':vm['bootstrap_rows'],
        'distinct_collections':vm['distinct_collections'],
        'loki_minute_bins':len(counts), 'loki_log_lines':sum(counts),
        'window_1':'BOOTSTRAP_OBSERVED:17:01:35..17:02:39_CET',
        'window_2':'LOCAL_RESTORED:17:04:48..17:05:55_CET',
        'overlap_full_minute_counts_not_event_counts':[180,37],
        'source_authentication':'NOT_CRYPTOGRAPHICALLY_VERIFIED',
        'hcc_parity':'FROZEN_REPOSITORY_MODEL_ONLY',
        'deployed_hcc':'NOT_TESTED',
        'causality':'NOT_ESTABLISHED',
        'dns_health':'NOT_PROVEN',
        'deployment_gate':'HOLD',
    }
    if summary.keys()!=SUMMARY_KEYS:
        raise Hold('HOST_SUMMARY_SHAPE')
    if any(type(summary[k]) is not int for k in ('vm_rows','vm_local','vm_bootstrap',
                    'distinct_collections','loki_minute_bins','loki_log_lines')):
        raise Hold('HOST_SUMMARY_NUMERIC_TYPE')
    return summary, a


def request(summary, nonce):
    if type(summary) is not dict or summary.keys()!=SUMMARY_KEYS:
        raise Hold('MODEL_SUMMARY_SHAPE')
    if (type(nonce) is not str or not re.fullmatch(r'[a-f0-9]{32}', nonce)
        or summary.get('deployment_gate')!='HOLD'
        or summary.get('source_authentication')!='NOT_CRYPTOGRAPHICALLY_VERIFIED'
        or summary.get('deployed_hcc')!='NOT_TESTED'
        or summary.get('causality')!='NOT_ESTABLISHED'
        or summary.get('dns_health')!='NOT_PROVEN'
        or summary.get('overlap_full_minute_counts_not_event_counts')!=[180,37]
        or summary.get('loki_minute_bins')!=15 or summary.get('loki_log_lines')!=726
        or summary.get('vm_rows')!=61 or summary.get('vm_bootstrap')!=3):
        raise Hold('MODEL_SUMMARY_UNTRUSTED_OR_DIFFERENT')
    system=(
        'You are a read-only, historical dual-source incident classifier with NO tools. '
        'Host facts are sampled and already validated; do not claim causality, DNS success, '
        'exact transition instants, verified provenance, or deployed HCC parity. '
        'Pi-hole counts are full-minute log-entry counts, NOT event-specific counts. '
        'Return exactly ONE JSON object (no markdown) with exactly: schema_version, '
        'observation_id, incident_code, log_activity_code, causality_code, dns_health_code, action. '
        'Copy observation_id from input. schema_version=v0.21c59.dual-source-qwen-shadow.v1. '
        'incident_code=FALLBACK_THEN_LOCAL_RESTORED_SAMPLED; '
        'log_activity_code=NONZERO_OVERLAPPING_MINUTE_BINS; '
        'causality_code=NOT_ESTABLISHED; dns_health_code=NOT_PROVEN; action=NONE. '
        'No commands, other text, paths, explanations, extra keys or speculation.'
    )
    obj={'model':MODEL,'stream':False,'format':'json','think':False,'keep_alive':'30s',
         'options':{'temperature':0,'num_ctx':2048,'num_predict':176},
         'messages':[{'role':'system','content':system},
                     {'role':'user','content':json.dumps({'observation_id':nonce,'host_facts':summary},
                                                         ensure_ascii=True,sort_keys=True,separators=(',',':'))}]}
    raw=json.dumps(obj,ensure_ascii=True,separators=(',',':')).encode()
    if not 1 <= len(raw) <= MAX_REQUEST:
        raise Hold('MODEL_REQUEST_SIZE')
    return obj


def assess(reply, nonce):
    if (type(reply) is not dict or reply.get('model')!=MODEL or
        reply.get('done') is not True or reply.get('done_reason','stop')!='stop'):
        return 'HOLD_MODEL_ENVELOPE'
    msg=reply.get('message')
    if (type(msg) is not dict or msg.get('role')!='assistant' or
        'tool_calls' in msg or type(msg.get('content')) is not str or
        (type(msg.get('thinking')) is str and msg['thinking']!='')):
        return 'HOLD_MODEL_ENVELOPE'
    raw=msg['content'].encode()
    if not 1 <= len(raw) <= MAX_MODEL_CONTENT:
        return 'HOLD_MODEL_CONTENT_SIZE'
    try:
        doc=strict_json(raw)
    except Hold:
        return 'HOLD_MODEL_JSON'
    if (type(doc) is not dict or doc.keys()!=FIELDS or
        any(type(v) is not str for v in doc.values()) or
        doc.get('schema_version')!=SCHEMA or doc.get('observation_id')!=nonce or
        any(doc.get(k)!=v for k,v in EXPECTED_CODES.items())):
        return 'HOLD_MODEL_CODES_OR_AUTHORITY'
    return 'VALID_SHADOW_CODES_ONLY'


def fixture_reply(nonce, **changes):
    data={'schema_version':SCHEMA,'observation_id':nonce,**EXPECTED_CODES}
    data.update(changes)
    return {'model':MODEL,'done':True,'done_reason':'stop',
            'message':{'role':'assistant','content':json.dumps(data,separators=(',',':'))}}


def ollama_call(method,path, payload=None, timeout=8, connector=None):
    if (method,path) not in (('GET','/api/tags'),('POST','/api/chat')) or (payload is None)!=(method=='GET'):
        raise Hold('OLLAMA_ROUTE_NOT_ALLOWED')
    body=None
    if method=='POST':
        if type(payload) is not dict: raise Hold('OLLAMA_REQUEST_TYPE')
        body=json.dumps(payload,ensure_ascii=True,separators=(',',':')).encode()
        if not 1<=len(body)<=MAX_REQUEST:raise Hold('OLLAMA_REQUEST_SIZE')
    # Avoid shadowing the imported `http` package: Python would otherwise
    # raise UnboundLocalError before contacting the local model.
    connection_factory = http.client.HTTPConnection if connector is None else connector
    conn=connection_factory(OLLAMA_HOST,OLLAMA_PORT,timeout=timeout)
    try:
        headers={'Accept':'application/json','Connection':'close'}
        if body is not None:headers['Content-Type']='application/json'
        conn.request(method,path,body=body,headers=headers)
        reply=conn.getresponse()
        data=reply.read(MAX_RESPONSE+1)
        if reply.status!=200 or len(data)>MAX_RESPONSE:
            raise Hold('OLLAMA_HTTP_STATUS_OR_SIZE')
        obj=strict_json(data)
        if type(obj) is not dict:raise Hold('OLLAMA_JSON_NOT_OBJECT')
        return obj
    except (OSError,TimeoutError,http.client.HTTPException) as exc:
        raise Hold('OLLAMA_LOOPBACK_UNAVAILABLE') from exc
    finally:
        conn.close()


def model_is_present(tags):
    if type(tags) is not dict or type(tags.get('models')) is not list or len(tags['models'])>100:
        raise Hold('OLLAMA_TAGS_INVALID')
    return any(type(m) is dict and m.get('name')==MODEL for m in tags['models'])


def perform(mode, *, read_source=None, call=ollama_call, supplied=None):
    if mode not in ('host-preflight','qwen-shadow'):
        raise Hold('MODE_INVALID')
    c58,c57,c54,c48=deps() if supplied is None else supplied
    if read_source is None:
        metrics=c57.vm_read()
        counts=c57.loki_parse(c57.bounded_get(c57.LOKI_PORT,c57.loki_path()))
    else:
        metrics,counts=read_source(c57)
    facts,a=host_audit(c58,c57,c54,c48,metrics,counts)
    print('=== V0.21C.59.1 / VERIFIED VM + LOKI TO QWEN SHADOW ===')
    print('VM=SEVEN_FIXED_LOOPBACK_READS')
    print('LOKI=ONE_FIXED_AGGREGATE_READ')
    print('HOST_JOINT_SHA256='+a['joint_sha256'])
    print('HOST_EVIDENCE_SHA256='+a['evidence_sha256'])
    print('HCC_PARITY='+a['hcc_parity'])
    print('C54_VALIDATION='+a['c54_contract'])
    print('LOKI_MINUTE_BINS=15/15')
    print('LOKI_LOG_ENTRY_SUM=726')
    print('RAW_LOG_LINES_SENT_TO_MODEL=NO')
    print('SOURCE_CRYPTOGRAPHIC_AUTHENTICATION=NO')
    print('DEPLOYED_HCC_CONTACTED=NO')
    if mode=='host-preflight':
        print('OLLAMA_CONTACTED=NO')
        print('FILES_WRITTEN=NO')
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C591_RESULT=PASS_HOST_PREFLIGHT_ONLY')
        return 'HOST_PREFLIGHT_ONLY'
    tags=call('GET','/api/tags',timeout=8)
    if not model_is_present(tags):
        raise Hold('OLLAMA_PINNED_MODEL_NOT_PRESENT')
    nonce=secrets.token_hex(16)
    req=request(facts,nonce)
    result=assess(call('POST','/api/chat',req,timeout=90),nonce)
    print('OLLAMA='+OLLAMA_HOST+':'+str(OLLAMA_PORT))
    print('MODEL='+MODEL)
    print('MODEL_VERDICT='+result)
    print('MODEL_ACTION_AUTHORITY=NONE')
    print('RAW_MODEL_RESPONSE_PRINTED=NO')
    print('EXECUTOR_PODMAN_OPENCODE_CHECKPOINT_CONTACTED=NO')
    print('FILES_WRITTEN=NO')
    print('DEPLOYMENT_GATE=HOLD')
    if result!='VALID_SHADOW_CODES_ONLY':
        raise Hold(result)
    print('V021C591_RESULT=PASS_DUAL_SOURCE_QWEN_SHADOW_ONLY')
    return result


class Tests(unittest.TestCase):
    NONCE='f'*32
    @classmethod
    def setUpClass(cls):
        cls.s=deps()
    def fixture(self):
        c58,c57,c54,c48=self.s
        return c57.synthetic_vm(), c57.COUNTS_GOLDEN
    def verified(self):
        return host_audit(*self.s, *self.fixture())
    def test_01_sources_pin(self):self.assertEqual(C58_SHA,hashlib.sha256((HERE/C58_NAME).read_bytes()).hexdigest())
    def test_02_c58_hcc(self):self.assertEqual(self.verified()[1]['hcc_parity'],'FROZEN_MODEL_SAMPLED_WINDOWS_CONCORDANT')
    def test_03_c54(self):self.assertEqual(self.verified()[1]['evidence_sha256'],EXPECTED_C54_SHA)
    def test_04_c57(self):self.assertEqual(self.verified()[1]['joint_sha256'],EXPECTED_C57_SHA)
    def test_05_facts_keys(self):self.assertEqual(self.verified()[0].keys(),SUMMARY_KEYS)
    def test_06_facts_counts(self):self.assertEqual(self.verified()[0]['loki_log_lines'],726)
    def test_07_request_model(self):self.assertEqual(request(self.verified()[0],self.NONCE)['model'],MODEL)
    def test_08_request_roles(self):self.assertEqual([m['role'] for m in request(self.verified()[0],self.NONCE)['messages']],['system','user'])
    def test_09_no_raw_series(self):
        data=json.dumps(request(self.verified()[0],self.NONCE))
        self.assertNotIn('asus_edge_dns_guard_',data)
        self.assertNotIn('raw_log',data.lower())
    def test_10_bad_nonce(self):
        with self.assertRaises(Hold):request(self.verified()[0],'invalid')
    def test_11_summary_extra(self):
        x=self.verified()[0];x['sudo']='true'
        with self.assertRaises(Hold):request(x,self.NONCE)
    def test_12_summary_causality(self):
        x=self.verified()[0];x['causality']='PROVEN'
        with self.assertRaises(Hold):request(x,self.NONCE)
    def test_13_valid_model(self):self.assertEqual(assess(fixture_reply(self.NONCE),self.NONCE),'VALID_SHADOW_CODES_ONLY')
    def test_14_injection_code(self):self.assertNotEqual(assess(fixture_reply(self.NONCE,action='EXECUTE'),self.NONCE),'VALID_SHADOW_CODES_ONLY')
    def test_15_model_wrong_cause(self):self.assertNotEqual(assess(fixture_reply(self.NONCE,causality_code='PROVEN'),self.NONCE),'VALID_SHADOW_CODES_ONLY')
    def test_16_model_wrong_dns_health(self):self.assertNotEqual(assess(fixture_reply(self.NONCE,dns_health_code='HEALTHY'),self.NONCE),'VALID_SHADOW_CODES_ONLY')
    def test_17_model_nonce(self):self.assertNotEqual(assess(fixture_reply(self.NONCE,observation_id='a'*32),self.NONCE),'VALID_SHADOW_CODES_ONLY')
    def test_18_model_extra(self):self.assertNotEqual(assess(fixture_reply(self.NONCE,command='sudo'),self.NONCE),'VALID_SHADOW_CODES_ONLY')
    def test_19_model_tool_calls(self):
        x=fixture_reply(self.NONCE);x['message']['tool_calls']=[]
        self.assertEqual(assess(x,self.NONCE),'HOLD_MODEL_ENVELOPE')
    def test_20_model_duplicate_json(self):
        x=fixture_reply(self.NONCE);x['message']['content']='{"action":"NONE","action":"EXECUTE"}'
        self.assertEqual(assess(x,self.NONCE),'HOLD_MODEL_JSON')
    def test_21_model_oversize(self):
        x=fixture_reply(self.NONCE);x['message']['content']='X'*(MAX_MODEL_CONTENT+1)
        self.assertEqual(assess(x,self.NONCE),'HOLD_MODEL_CONTENT_SIZE')
    def test_22_model_thinking(self):
        x=fixture_reply(self.NONCE);x['message']['thinking']='run commands'
        self.assertEqual(assess(x,self.NONCE),'HOLD_MODEL_ENVELOPE')
    def test_23_extra_loki_count_hold(self):
        x,y=self.fixture();bad=list(y);bad[1]+=1
        with self.assertRaises((Hold,self.s[1].Hold,self.s[0].Hold)):host_audit(*self.s,x,tuple(bad))
    def test_24_missing_vm_hold(self):
        x,y=self.fixture();del x[self.s[1].VM_NAMES[0]][self.s[1].VM_START]
        with self.assertRaises((Hold,self.s[1].Hold,self.s[0].Hold)):host_audit(*self.s,x,y)
    def test_25_unknown_route(self):
        with self.assertRaises(Hold):ollama_call('POST','/api/generate',{})
    def test_26_tags(self):self.assertTrue(model_is_present({'models':[{'name':MODEL}]}))
    def test_27_host_only_no_ollama(self):
        import io,contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            outcome=perform('host-preflight',supplied=self.s,read_source=lambda _: self.fixture(),
                            call=lambda *a,**k: (_ for _ in ()).throw(AssertionError('OLLAMA_CONTACT')))
        self.assertEqual(outcome,'HOST_PREFLIGHT_ONLY')
    def test_28_model_offline_fake(self):
        import io,contextlib
        paths=[]
        def fake(method,path,payload=None,**kw):
            paths.append((method,path))
            if method=='GET':return {'models':[{'name':MODEL}]}
            nonce=json.loads(payload['messages'][1]['content'])['observation_id']
            return fixture_reply(nonce)
        with contextlib.redirect_stdout(io.StringIO()):
            verdict=perform('qwen-shadow', supplied=self.s,read_source=lambda _:self.fixture(),call=fake)
        self.assertEqual(verdict,'VALID_SHADOW_CODES_ONLY')
        self.assertEqual(paths,[('GET','/api/tags'),('POST','/api/chat')])
    def test_29_model_bad_fails_closed(self):
        import io,contextlib
        def fake(method,path,payload=None,**kw):
            if method=='GET':return {'models':[{'name':MODEL}]}
            nonce=json.loads(payload['messages'][1]['content'])['observation_id']
            return fixture_reply(nonce,action='EXECUTE')
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(Hold):perform('qwen-shadow',supplied=self.s,read_source=lambda _:self.fixture(),call=fake)
    def test_30_no_untrusted_metrics(self):
        x,y=self.fixture();x[self.s[1].VM_NAMES[2]][self.s[1].VM_START]=0
        with self.assertRaises((Hold,self.s[1].Hold,self.s[0].Hold)):host_audit(*self.s,x,y)


    # C59.1 regression coverage: use the actual ollama_call(), not a fake `call`.
    # All transports below are in-memory stand-ins. No real network IO occurs.
    def fake_transport(self, raw, status=200, request_error=None):
        state={'connect':[], 'requests':[], 'closed':False}
        class FakeResponse:
            def __init__(self): self.status=status
            def read(self, max_size): return raw[:max_size]
        class FakeConnection:
            def __init__(self, host, port, timeout):
                state['connect'].append((host, port, timeout))
            def request(self, method, path, body=None, headers=None):
                state['requests'].append((method, path, body, headers))
                if request_error is not None:
                    raise request_error
            def getresponse(self): return FakeResponse()
            def close(self): state['closed']=True
        return FakeConnection, state

    def test_31_real_http_adapter_get_tags_without_network(self):
        raw=json.dumps({'models':[{'name':MODEL}]}).encode()
        factory, state=self.fake_transport(raw)
        with patch('http.client.HTTPConnection', side_effect=factory):
            reply=ollama_call('GET','/api/tags',timeout=8)
        self.assertTrue(model_is_present(reply))
        self.assertEqual(state['connect'], [(OLLAMA_HOST,OLLAMA_PORT,8)])
        self.assertEqual([(m,p) for m,p,_,_ in state['requests']], [('GET','/api/tags')])
        self.assertIsNone(state['requests'][0][2])
        self.assertTrue(state['closed'])

    def test_32_real_http_adapter_post_chat_without_network(self):
        facts,_=self.verified()
        req=request(facts,self.NONCE)
        raw=json.dumps(fixture_reply(self.NONCE)).encode()
        factory, state=self.fake_transport(raw)
        with patch('http.client.HTTPConnection',side_effect=factory):
            reply=ollama_call('POST','/api/chat',req,timeout=90)
        self.assertEqual(assess(reply,self.NONCE),'VALID_SHADOW_CODES_ONLY')
        self.assertEqual(state['connect'],[(OLLAMA_HOST,OLLAMA_PORT,90)])
        method,path,body,headers=state['requests'][0]
        self.assertEqual((method,path),('POST','/api/chat'))
        self.assertEqual(json.loads(body),req)
        self.assertEqual(headers['Content-Type'],'application/json')
        self.assertTrue(state['closed'])

    def test_33_http_non_200_fails_closed(self):
        factory,state=self.fake_transport(b'not-a-success',status=503)
        with patch('http.client.HTTPConnection',side_effect=factory):
            with self.assertRaisesRegex(Hold,'OLLAMA_HTTP_STATUS_OR_SIZE'):
                ollama_call('GET','/api/tags')
        self.assertTrue(state['closed'])

    def test_34_http_connection_error_fails_closed(self):
        factory,state=self.fake_transport(b'',request_error=OSError('synthetic'))
        with patch('http.client.HTTPConnection',side_effect=factory):
            with self.assertRaisesRegex(Hold,'OLLAMA_LOOPBACK_UNAVAILABLE'):
                ollama_call('GET','/api/tags')
        self.assertTrue(state['closed'])

    def test_35_http_oversize_fails_closed(self):
        factory,state=self.fake_transport(b'a'*(MAX_RESPONSE+1))
        with patch('http.client.HTTPConnection',side_effect=factory):
            with self.assertRaisesRegex(Hold,'OLLAMA_HTTP_STATUS_OR_SIZE'):
                ollama_call('GET','/api/tags')
        self.assertTrue(state['closed'])

    def test_36_http_duplicate_json_fails_closed(self):
        factory,state=self.fake_transport(b'{"models":[],"models":[]}')
        with patch('http.client.HTTPConnection',side_effect=factory):
            with self.assertRaisesRegex(Hold,'DUPLICATE_JSON_KEY'):
                ollama_call('GET','/api/tags')
        self.assertTrue(state['closed'])

def selftest():
    with patch('http.client.HTTPConnection',side_effect=AssertionError('NETWORK_IN_SELFTEST')):
        out=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    valid=out.wasSuccessful() and out.testsRun==36
    success=out.testsRun-len(out.failures)-len(out.errors)
    print(f'V021C591_SELFTESTS={success}/{out.testsRun}')
    print('NO_NETWORK_DURING_SELFTEST=YES')
    print('V021C591_SELFTEST_RESULT='+('PASS_OFFLINE' if valid else 'HOLD'))
    return valid


def main():
    p=argparse.ArgumentParser(description=__doc__)
    opt=p.add_mutually_exclusive_group(required=True)
    opt.add_argument('--self-test',action='store_true')
    opt.add_argument('--host-preflight',action='store_true')
    opt.add_argument('--qwen-shadow',action='store_true')
    args=p.parse_args()
    if os.geteuid()==0:
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C591_RESULT=HOLD_ROOT_REFUSED')
        return 1
    if not selftest():
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C591_RESULT=HOLD_NOT_APPROVED')
        return 1
    if args.self_test:
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C591_RESULT=PASS_OFFLINE_ONLY')
        return 0
    try:
        perform('host-preflight' if args.host_preflight else 'qwen-shadow')
        return 0
    except Exception as exc:
        # Modules C57/C58 have separate pinned Hold classes. Any unexpected
        # ordinary exception also fails CLOSED without a traceback or payload.
        # Do not echo raw HTTP payload, untrusted model text or source lines.
        print('HOLD_REASON='+str(exc) if type(exc) is Hold else 'HOLD_REASON='+type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C591_RESULT=HOLD_NOT_APPROVED')
        return 1

if __name__=='__main__':
    sys.exit(main())
