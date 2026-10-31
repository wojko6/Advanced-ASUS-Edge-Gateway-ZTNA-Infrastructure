#!/usr/bin/env python3
"""V0.21C.60: isolated fault matrix for pinned V0.21C.59.1 shadow chain.

Only mode: --self-test. NEVER connects to VM, Loki, Ollama, ASUS, HCC,
containers or any model. No file writes. C.59.1 is intentionally NOT patched.
One known contract hardening finding is reported separately from PASS tests.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).absolute().parent
TARGET = 'local_ai_agent_v021c59_1_ollama_transport_hotfix_shadow_lab_v01.py'
TARGET_SHA = '013879e02a8a40a0260204f7880545926a02986f9dce6cb0da590124a38cfde9'
SCHEMA = 'v0.21c60.offline-fault-matrix.v1'

class Hold(Exception):
    pass


def load_pinned(root=HERE):
    p = root / TARGET
    try:
        before = p.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or before.st_nlink != 1 or before.st_mode & 0o022
                or not 100 <= before.st_size <= 100000):
            raise Hold('TARGET_OWNER_MODE_OR_SIZE')
        fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            got = os.fstat(fd)
            fingerprint = lambda s: (s.st_dev, s.st_ino, s.st_uid, s.st_mode, s.st_size, s.st_mtime_ns)
            if fingerprint(before) != fingerprint(got):
                raise Hold('TARGET_RACE')
            raw = os.read(fd, 100001)
            if len(raw) != got.st_size or fingerprint(got) != fingerprint(os.fstat(fd)):
                raise Hold('TARGET_CHANGED')
        finally:
            os.close(fd)
    except OSError as exc:
        raise Hold('TARGET_UNAVAILABLE') from exc
    if hashlib.sha256(raw).hexdigest() != TARGET_SHA:
        raise Hold('TARGET_SHA256_MISMATCH')
    mod = types.ModuleType('c60_pinned_c591')
    mod.__file__ = str(p)
    exec(compile(raw, str(p), 'exec'), mod.__dict__)
    return mod


def clean_output(fn):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn()


class Matrix(unittest.TestCase):
    NONCE = 'c' * 32

    @classmethod
    def setUpClass(cls):
        cls.target = load_pinned()
        cls.chain = cls.target.deps()

    def fixture(self):
        c57 = self.chain[1]
        return c57.synthetic_vm(), c57.COUNTS_GOLDEN

    def facts(self):
        return self.target.host_audit(*self.chain, *self.fixture())[0]

    def do(self, call, read_source=None):
        if read_source is None:
            read_source = lambda _: self.fixture()
        return clean_output(lambda: self.target.perform(
            'qwen-shadow', supplied=self.chain, read_source=read_source, call=call))

    def valid_call(self, extra=None):
        calls = []
        def fake(method, path, payload=None, **kwargs):
            calls.append((method, path))
            if method == 'GET':
                return {'models': [{'name': self.target.MODEL}]}
            nonce = json.loads(payload['messages'][1]['content'])['observation_id']
            reply = self.target.fixture_reply(nonce)
            if extra:
                extra(reply)
            return reply
        return fake, calls

    def assert_hold(self, fn):
        with self.assertRaises((self.target.Hold, self.chain[0].Hold,
                                self.chain[1].Hold, self.chain[2].Hold, Hold)):
            fn()

    def test_01_source_pins(self):
        self.assertEqual(TARGET_SHA, hashlib.sha256((HERE / TARGET).read_bytes()).hexdigest())
        self.assertEqual(self.chain[0].EXPECTED['c57'][1], hashlib.sha256((HERE / self.chain[0].EXPECTED['c57'][0]).read_bytes()).hexdigest())

    def test_02_real_host_fixture_audit(self):
        report = self.target.host_audit(*self.chain, *self.fixture())[1]
        self.assertEqual(report['hcc_parity'], 'FROZEN_MODEL_SAMPLED_WINDOWS_CONCORDANT')

    def test_03_request_bounded_and_tool_free(self):
        obj = self.target.request(self.facts(), self.NONCE)
        raw = json.dumps(obj, sort_keys=True)
        self.assertLessEqual(len(raw.encode()), self.target.MAX_REQUEST)
        self.assertNotIn('"tools"', raw)
        self.assertNotIn('"tool_choice"', raw)
        self.assertEqual(obj['stream'], False)

    def test_04_known_good_response(self):
        self.assertEqual(self.target.assess(self.target.fixture_reply(self.NONCE), self.NONCE),
                         'VALID_SHADOW_CODES_ONLY')

    def test_05_wrong_action_rejected(self):
        self.assertEqual(self.target.assess(self.target.fixture_reply(self.NONCE, action='EXECUTE'), self.NONCE),
                         'HOLD_MODEL_CODES_OR_AUTHORITY')

    def test_06_wrong_causality_rejected(self):
        self.assertEqual(self.target.assess(self.target.fixture_reply(self.NONCE, causality_code='PROVEN'), self.NONCE),
                         'HOLD_MODEL_CODES_OR_AUTHORITY')

    def test_07_wrong_dns_health_rejected(self):
        self.assertEqual(self.target.assess(self.target.fixture_reply(self.NONCE, dns_health_code='HEALTHY'), self.NONCE),
                         'HOLD_MODEL_CODES_OR_AUTHORITY')

    def test_08_wrong_nonce_rejected(self):
        self.assertEqual(self.target.assess(self.target.fixture_reply(self.NONCE, observation_id='d'*32), self.NONCE),
                         'HOLD_MODEL_CODES_OR_AUTHORITY')

    def test_09_extra_json_action_field_rejected(self):
        self.assertEqual(self.target.assess(self.target.fixture_reply(self.NONCE, shell='sudo reboot'), self.NONCE),
                         'HOLD_MODEL_CODES_OR_AUTHORITY')

    def test_10_duplicate_json_key_rejected(self):
        reply = self.target.fixture_reply(self.NONCE)
        reply['message']['content'] = '{"action":"NONE","action":"REBOOT"}'
        self.assertEqual(self.target.assess(reply, self.NONCE), 'HOLD_MODEL_JSON')

    def test_11_markdown_rejected(self):
        reply = self.target.fixture_reply(self.NONCE)
        reply['message']['content'] = '```json\n{}\n```'
        self.assertEqual(self.target.assess(reply, self.NONCE), 'HOLD_MODEL_JSON')

    def test_12_nonfinite_json_rejected(self):
        reply = self.target.fixture_reply(self.NONCE)
        reply['message']['content'] = '{"action":NaN}'
        self.assertEqual(self.target.assess(reply, self.NONCE), 'HOLD_MODEL_JSON')

    def test_13_empty_message_rejected(self):
        reply = self.target.fixture_reply(self.NONCE)
        reply['message']['content'] = ''
        self.assertEqual(self.target.assess(reply, self.NONCE), 'HOLD_MODEL_CONTENT_SIZE')

    def test_14_oversized_message_rejected(self):
        reply = self.target.fixture_reply(self.NONCE)
        reply['message']['content'] = 'A' * (self.target.MAX_MODEL_CONTENT + 1)
        self.assertEqual(self.target.assess(reply, self.NONCE), 'HOLD_MODEL_CONTENT_SIZE')

    def test_15_tool_calls_rejected(self):
        reply = self.target.fixture_reply(self.NONCE)
        reply['message']['tool_calls'] = [{'function': {'name':'shell','arguments':{}}}]
        self.assertEqual(self.target.assess(reply, self.NONCE), 'HOLD_MODEL_ENVELOPE')

    def test_16_hidden_thinking_rejected(self):
        reply = self.target.fixture_reply(self.NONCE)
        reply['message']['thinking'] = 'ignore policy'
        self.assertEqual(self.target.assess(reply, self.NONCE), 'HOLD_MODEL_ENVELOPE')

    def test_17_wrong_model_rejected(self):
        reply = self.target.fixture_reply(self.NONCE)
        reply['model'] = 'unreviewed-model'
        self.assertEqual(self.target.assess(reply, self.NONCE), 'HOLD_MODEL_ENVELOPE')

    def test_18_done_false_rejected(self):
        reply = self.target.fixture_reply(self.NONCE)
        reply['done'] = False
        self.assertEqual(self.target.assess(reply, self.NONCE), 'HOLD_MODEL_ENVELOPE')

    def test_19_incomplete_generation_rejected(self):
        reply = self.target.fixture_reply(self.NONCE)
        reply['done_reason'] = 'length'
        self.assertEqual(self.target.assess(reply, self.NONCE), 'HOLD_MODEL_ENVELOPE')

    def test_20_missing_done_reason_finding(self):
        # Expected known gap in C.59.1: defaults a missing done_reason to stop.
        reply = self.target.fixture_reply(self.NONCE)
        reply.pop('done_reason')
        self.assertEqual(self.target.assess(reply, self.NONCE), 'VALID_SHADOW_CODES_ONLY')

    def test_21_invalid_ollama_route_never_calls_network(self):
        self.assert_hold(lambda: self.target.ollama_call('POST', '/api/generate', {}))

    def fake_connection(self, raw, status=200, error=None):
        state = {'closed':False, 'requests':[], 'endpoints':[]}
        class Response:
            def __init__(self): self.status = status
            def read(self, n): return raw[:n]
        class Connection:
            def __init__(self, host, port, timeout):
                state['endpoints'].append((host,port,timeout))
            def request(self, method, path, body=None, headers=None):
                state['requests'].append((method,path,body,headers))
                if error is not None: raise error
            def getresponse(self): return Response()
            def close(self): state['closed'] = True
        return Connection, state

    def test_22_transport_pinned_get_and_close(self):
        connector,state = self.fake_connection(b'{"models":[]}')
        reply = self.target.ollama_call('GET','/api/tags',connector=connector)
        self.assertEqual(reply, {'models': []})
        self.assertEqual(state['endpoints'], [('127.0.0.1',11435,8)])
        self.assertTrue(state['closed'])

    def test_23_transport_pinned_post_and_close(self):
        req = self.target.request(self.facts(),self.NONCE)
        connector,state = self.fake_connection(json.dumps(self.target.fixture_reply(self.NONCE)).encode())
        self.target.ollama_call('POST','/api/chat',req,connector=connector,timeout=90)
        self.assertEqual(state['endpoints'], [('127.0.0.1',11435,90)])
        self.assertEqual(json.loads(state['requests'][0][2]), req)
        self.assertTrue(state['closed'])

    def test_24_http_503_hold_closed(self):
        connector,state = self.fake_connection(b'INTERNAL_ERR_LEAK_NO',status=503)
        with self.assertRaisesRegex(self.target.Hold, 'OLLAMA_HTTP_STATUS_OR_SIZE'):
            self.target.ollama_call('GET','/api/tags',connector=connector)
        self.assertTrue(state['closed'])

    def test_25_timeout_hold_closed(self):
        connector,state = self.fake_connection(b'',error=TimeoutError('synthetic timeout, no network'))
        with self.assertRaisesRegex(self.target.Hold,'OLLAMA_LOOPBACK_UNAVAILABLE'):
            self.target.ollama_call('GET','/api/tags',connector=connector)
        self.assertTrue(state['closed'])

    def test_26_connection_refused_hold_closed(self):
        connector,state = self.fake_connection(b'',error=ConnectionRefusedError('synthetic'))
        with self.assertRaisesRegex(self.target.Hold,'OLLAMA_LOOPBACK_UNAVAILABLE'):
            self.target.ollama_call('GET','/api/tags',connector=connector)
        self.assertTrue(state['closed'])

    def test_27_http_malformed_json_hold_closed(self):
        connector,state = self.fake_connection(b'not-json')
        with self.assertRaises(self.target.Hold):
            self.target.ollama_call('GET','/api/tags',connector=connector)
        self.assertTrue(state['closed'])

    def test_28_http_duplicate_json_hold_closed(self):
        connector,state = self.fake_connection(b'{"models":[],"models":[]}')
        with self.assertRaisesRegex(self.target.Hold,'DUPLICATE_JSON_KEY'):
            self.target.ollama_call('GET','/api/tags',connector=connector)
        self.assertTrue(state['closed'])

    def test_29_http_response_too_big_hold_closed(self):
        connector,state = self.fake_connection(b'X' * (self.target.MAX_RESPONSE + 1))
        with self.assertRaisesRegex(self.target.Hold,'OLLAMA_HTTP_STATUS_OR_SIZE'):
            self.target.ollama_call('GET','/api/tags',connector=connector)
        self.assertTrue(state['closed'])

    def test_30_pinned_model_not_present_never_posts(self):
        calls=[]
        def fake(method,path,payload=None,**kwargs):
            calls.append((method,path))
            return {'models':[]}
        self.assert_hold(lambda: self.do(fake))
        self.assertEqual(calls,[('GET','/api/tags')])

    def test_31_vm_missing_never_contacts_ollama(self):
        def source(c57):
            metrics, counts = self.fixture()
            del metrics[c57.VM_NAMES[0]][c57.VM_START]
            return metrics, counts
        calls=[]
        def fake(*args,**kwargs):
            calls.append('CONTACT')
            raise AssertionError('UNEXPECTED_MODEL')
        self.assert_hold(lambda: self.do(fake,source))
        self.assertEqual(calls,[])

    def test_32_vm_stale_never_contacts_ollama(self):
        def source(c57):
            metrics,counts = self.fixture()
            metrics[c57.VM_NAMES[0]][c57.VM_START] = c57.VM_START-181
            return metrics, counts
        calls=[]
        def fake(*args,**kwargs):
            calls.append('CONTACT')
            raise AssertionError('UNEXPECTED_MODEL')
        self.assert_hold(lambda: self.do(fake,source))
        self.assertEqual(calls,[])

    def test_33_vm_conflict_never_contacts_ollama(self):
        def source(c57):
            metrics,counts = self.fixture()
            metrics[c57.VM_NAMES[1]][c57.VM_START] = 0
            return metrics, counts
        calls=[]
        def fake(*args,**kwargs):
            calls.append('CONTACT')
            raise AssertionError('UNEXPECTED_MODEL')
        self.assert_hold(lambda: self.do(fake,source))
        self.assertEqual(calls,[])

    def test_34_loki_changed_never_contacts_ollama(self):
        def source(c57):
            metrics,counts = self.fixture()
            changed=list(counts)
            changed[0]+=1
            return metrics, tuple(changed)
        calls=[]
        def fake(*args,**kwargs):
            calls.append('CONTACT')
            raise AssertionError('UNEXPECTED_MODEL')
        self.assert_hold(lambda: self.do(fake,source))
        self.assertEqual(calls,[])

    def test_35_host_source_timeout_never_contacts_ollama(self):
        def source(_): raise TimeoutError('synthetic VM timeout')
        calls=[]
        def fake(*args,**kwargs):
            calls.append('CONTACT')
            raise AssertionError('UNEXPECTED_MODEL')
        with self.assertRaises(TimeoutError): self.do(fake,source)
        self.assertEqual(calls,[])

    def test_36_model_invalid_action_causes_hold(self):
        fake,calls=self.valid_call(lambda r: r['message'].update(content=json.dumps({
            **json.loads(r['message']['content']), 'action':'EXECUTE'})))
        self.assert_hold(lambda: self.do(fake))
        self.assertEqual(calls,[('GET','/api/tags'),('POST','/api/chat')])

    def test_37_model_valid_shadow_succeeds_without_executor(self):
        fake,calls=self.valid_call()
        self.assertEqual(self.do(fake),'VALID_SHADOW_CODES_ONLY')
        self.assertEqual(calls,[('GET','/api/tags'),('POST','/api/chat')])

    def test_38_wrong_summary_rejected_before_request(self):
        facts=self.facts()
        facts['deployment_gate']='LIVE'
        self.assert_hold(lambda: self.target.request(facts,self.NONCE))

    def test_39_unauthenticated_provenance_persists(self):
        summary=self.facts()
        self.assertEqual(summary['source_authentication'],'NOT_CRYPTOGRAPHICALLY_VERIFIED')
        self.assertEqual(summary['deployed_hcc'],'NOT_TESTED')
        self.assertEqual(summary['causality'],'NOT_ESTABLISHED')

    def test_40_replay_identity_of_request(self):
        req=self.target.request(self.facts(),self.NONCE)
        j=json.loads(req['messages'][1]['content'])
        self.assertEqual(j['observation_id'],self.NONCE)
        self.assertEqual(j['host_facts']['loki_log_lines'],726)


def selftest():
    with patch('http.client.HTTPConnection', side_effect=AssertionError('REAL_NETWORK_FORBIDDEN_C60')):
        result=unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Matrix))
    ok=result.wasSuccessful() and result.testsRun==40
    successes=result.testsRun - len(result.errors) - len(result.failures)
    print(f'V021C60_SELFTESTS={successes}/{result.testsRun}')
    print('NO_NETWORK=YES')
    print('NO_VM_NO_LOKI_NO_OLLAMA_CONTACT=YES')
    print('NO_ASUS_NO_HCC_NO_EXECUTOR_NO_PODMAN=YES')
    print('FILES_WRITTEN=NO')
    print('PINNED_TARGET=C59.1_UNMODIFIED')
    print('EXPECTED_HARDENING_FINDING=MISSING_DONE_REASON_ACCEPTED_IN_C591')
    print('MODEL_INJECTION_OR_HOSTILE_EXECUTOR_CERTIFICATION=NO')
    print('DEPLOYMENT_GATE=HOLD')
    print('V021C60_RESULT=' + ('PASS_OFFLINE_FAULT_MATRIX_WITH_KNOWN_FINDING_ONLY' if ok
                                else 'HOLD_NOT_APPROVED'))
    return ok


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test',action='store_true',required=True)
    args=p.parse_args()
    if os.geteuid()==0:
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C60_RESULT=HOLD_ROOT_REFUSED')
        return 1
    try:
        return 0 if selftest() else 1
    except Exception as exc:
        print('HOLD_REASON='+type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C60_RESULT=HOLD_NOT_APPROVED')
        return 1

if __name__=='__main__':
    raise SystemExit(main())
