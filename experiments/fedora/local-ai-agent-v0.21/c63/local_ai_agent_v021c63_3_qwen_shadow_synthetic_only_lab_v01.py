#!/usr/bin/env python3
"""C.63.3 one-shot synthetic-only Qwen SHADOW; no agent actions.

--self-test and --fixture-matrix never use networking. Only the explicit
--ollama-preflight and --qwen-shadow options contact 127.0.0.1:11434.
No CLI input, private file read, telemetry collection, subprocess or writes.
"""
from __future__ import annotations

import argparse
import json
import sys
import unittest
import urllib.error
import urllib.request

import local_ai_agent_v021c63_2_bounded_shadow_contract_offline_lab_v01 as bounded
import local_ai_agent_v021c63_1_c62_cli_offline_bridge_lab_v01 as bridge

sys.dont_write_bytecode = True
MODEL = 'qwen3.5:4b'
BASE = 'http://127.0.0.1:11434'
MAX_TAG_BYTES = 64 * 1024
MAX_ENVELOPE_BYTES = 32 * 1024
MAX_REQUEST_BYTES = 8 * 1024
TIMEOUT_SECONDS = 90

class Hold(Exception):
    pass


def no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise Hold('DUPLICATE_JSON_KEY')
        out[k] = v
    return out


def invalid_constant(_value):
    raise Hold('INVALID_JSON_CONSTANT')


def load_json(raw: bytes):
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=no_dupes,
                          parse_constant=invalid_constant)
    except (ValueError, UnicodeDecodeError) as exc:
        raise Hold('INVALID_JSON') from exc


def packet():
    """Only deterministic synthetic fixture is eligible for a model call."""
    value = bounded.fixture_packet()
    if (value.get('source_type') != bridge.ORIGIN_FIXTURE
        or value.get('model_action_authority') != 'NONE'
        or value.get('deployment_gate') != 'HOLD'
        or value.get('source_provenance_attested') is not False
        or value.get('remediation_authorized') is not False):
        raise Hold('NON_SYNTHETIC_OR_INVALID_PACKET')
    return value


def make_request(pkt):
    if pkt.get('source_type') != bridge.ORIGIN_FIXTURE:
        raise Hold('HISTORICAL_INPUT_FORBIDDEN_C633')
    if (pkt.get('model_action_authority') != 'NONE'
        or pkt.get('deployment_gate') != 'HOLD'
        or pkt.get('remediation_authorized') is not False
        or pkt.get('source_provenance_attested') is not False):
        raise Hold('PACKET_SAFETY_INVARIANT')
    # Never include raw C.62 CLI logs, host IDs or free-form text.
    schema = {
        'type': 'object', 'additionalProperties': False,
        'required': sorted(bounded.RESPONSE_KEYS),
        'properties': {
            'schema': {'type': 'string', 'enum': [bounded.RESPONSE_SCHEMA]},
            'input_sha256': {'type': 'string', 'enum': [pkt['input_sha256']]},
            'assessment_code': {'type': 'string', 'enum': [pkt['assessment_code']]},
            'next_check_code': {'type': 'string', 'enum': list(bounded.NEXT_CHECKS)},
            'root_cause': {'type': 'string', 'enum': ['UNDETERMINED']},
            'model_action_authority': {'type': 'string', 'enum': ['NONE']},
            'remediation_authorized': {'type': 'boolean', 'enum': [False]},
        },
    }
    prompt = (
        'SYNTHETIC DATA ONLY. Return one ASCII JSON object with exactly 7 keys. '
        'All fields except next_check_code must match the response schema exactly. '
        'Choose only from allowed_next_check_codes; prefer MANUAL_EVIDENCE_REVIEW_ONLY. '
        'No explanation, commands, shell, extra text, markdown or root-cause speculation. '
        'Do not suggest any autonomous remediation. Here is the bounded packet:\n'
        + json.dumps(pkt, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    )
    body = {
        'model': MODEL, 'stream': False, 'think': False,
        'format': schema, 'keep_alive': 0,
        'options': {'temperature': 0, 'num_predict': 180, 'num_ctx': 2048},
        'system': 'Return only strict JSON for a synthetic SHADOW test. You have no tools or action authority.',
        'prompt': prompt,
    }
    data = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    if len(data) > MAX_REQUEST_BYTES:
        raise Hold('REQUEST_TOO_LARGE')
    return data


def validate_ollama(raw: bytes, pkt):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_ENVELOPE_BYTES:
        raise Hold('OLLAMA_ENVELOPE_SIZE_INVALID')
    envelope = load_json(raw)
    if type(envelope) is not dict:
        raise Hold('OLLAMA_ENVELOPE_INVALID')
    if envelope.get('model') != MODEL:
        raise Hold('OLLAMA_MODEL_MISMATCH')
    if envelope.get('done') is not True or envelope.get('done_reason') != 'stop':
        raise Hold('OLLAMA_COMPLETION_NOT_EXPLICIT_STOP')
    response = envelope.get('response')
    if not isinstance(response, str):
        raise Hold('OLLAMA_RESPONSE_MISSING')
    try:
        output = response.encode('ascii')
    except UnicodeEncodeError as exc:
        raise Hold('OLLAMA_NON_ASCII_RESPONSE') from exc
    if not 0 < len(output) <= bounded.MAX_RESPONSE_BYTES:
        raise Hold('MODEL_RESPONSE_SIZE_INVALID')
    # Additional duplicate-key and JSON-constant gate before C.63.2.
    parsed = load_json(output)
    if type(parsed) is not dict:
        raise Hold('MODEL_RESPONSE_NOT_OBJECT')
    try:
        return bounded.validate_response(output, pkt)
    except bounded.Hold as exc:
        raise Hold('C632_GATE_'+str(exc)) from exc


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Hold('HTTP_REDIRECT_FORBIDDEN')


def opener():
    # Ignore HTTP_PROXY/ALL_PROXY/NO_PROXY environment variables.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def bounded_http(op, endpoint, body=None, max_bytes=MAX_ENVELOPE_BYTES):
    if endpoint not in ('/api/tags', '/api/generate'):
        raise Hold('ENDPOINT_NOT_ALLOWED')
    if body is not None and endpoint != '/api/generate':
        raise Hold('INVALID_METHOD')
    request = urllib.request.Request(
        BASE + endpoint, data=body,
        headers={'Content-Type': 'application/json'} if body is not None else {},
        method='POST' if body is not None else 'GET')
    try:
        with op.open(request, timeout=TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise Hold('HTTP_NOT_200')
            result = response.read(max_bytes + 1)
    except Hold:
        raise
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
        raise Hold('LOCAL_OLLAMA_UNAVAILABLE_'+type(exc).__name__) from exc
    if not 0 < len(result) <= max_bytes:
        raise Hold('HTTP_RESPONSE_TOO_LARGE_OR_EMPTY')
    return result


def check_model_installed(op):
    obj = load_json(bounded_http(op, '/api/tags', max_bytes=MAX_TAG_BYTES))
    models = obj.get('models') if type(obj) is dict else None
    if type(models) is not list or len(models) > 1000:
        raise Hold('OLLAMA_TAGS_INVALID')
    names = [entry.get('name') for entry in models if type(entry) is dict]
    if MODEL not in names:
        raise Hold('MODEL_NOT_INSTALLED_NO_DOWNLOAD')
    return 'LOCAL_MODEL_PRESENT'


def run_shadow(op):
    check_model_installed(op)
    pkt = packet()
    request = make_request(pkt)
    raw = bounded_http(op, '/api/generate', body=request)
    return validate_ollama(raw, pkt)


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.pkt = packet()
        self.response = bounded.response_for_fixture(self.pkt)

    def env(self, **update):
        value = {
            'model': MODEL, 'done': True, 'done_reason': 'stop',
            'response': json.dumps(self.response, separators=(',', ':'), ensure_ascii=True),
        }
        value.update(update)
        return json.dumps(value, separators=(',', ':')).encode('ascii')

    def hold(self, raw, expected):
        with self.assertRaisesRegex(Hold, expected):
            validate_ollama(raw, self.pkt)

    def test_01_synthetic(self):
        self.assertEqual(self.pkt['source_type'], bridge.ORIGIN_FIXTURE)
    def test_02_no_action(self):
        self.assertEqual(self.pkt['model_action_authority'], 'NONE')
    def test_03_deployment_hold(self):
        self.assertEqual(self.pkt['deployment_gate'], 'HOLD')
    def test_04_no_model_telemetry(self):
        self.assertEqual(self.pkt['facts']['root_cause'], 'UNDETERMINED')
    def test_05_request_limited(self):
        self.assertLess(len(make_request(self.pkt)), MAX_REQUEST_BYTES)
    def test_06_no_tools_field(self):
        self.assertNotIn('tools', load_json(make_request(self.pkt)))
    def test_07_fixed_model(self):
        self.assertEqual(load_json(make_request(self.pkt))['model'], MODEL)
    def test_08_no_stream(self):
        self.assertIs(load_json(make_request(self.pkt))['stream'], False)
    def test_09_disable_thinking(self):
        self.assertIs(load_json(make_request(self.pkt))['think'], False)
    def test_10_context_bounded(self):
        self.assertEqual(load_json(make_request(self.pkt))['options']['num_ctx'], 2048)
    def test_11_valid_response(self):
        self.assertEqual(validate_ollama(self.env(), self.pkt)['result'], 'PASS_SHADOW_CODES_ONLY')
    def test_12_wrong_model(self):
        self.hold(self.env(model='another:4b'), 'MODEL_MISMATCH')
    def test_13_false_done(self):
        self.hold(self.env(done=False), 'COMPLETION_NOT_EXPLICIT_STOP')
    def test_14_missing_done_reason(self):
        d=load_json(self.env());d.pop('done_reason'); self.hold(json.dumps(d).encode(), 'COMPLETION_NOT_EXPLICIT_STOP')
    def test_15_truncated_done_reason(self):
        self.hold(self.env(done_reason='length'), 'COMPLETION_NOT_EXPLICIT_STOP')
    def test_16_response_missing(self):
        self.hold(self.env(response=None), 'RESPONSE_MISSING')
    def test_17_json_fence(self):
        self.hold(self.env(response='```json\n{}\n```'), 'INVALID_JSON')
    def test_18_model_extra_key(self):
        r=dict(self.response,command='sudo reboot')
        self.hold(self.env(response=json.dumps(r)), 'C632_GATE_RESPONSE_SCHEMA_KEYS')
    def test_19_made_up_cause(self):
        r=dict(self.response, root_cause='ROUTER_DOWN')
        self.hold(self.env(response=json.dumps(r)), 'C632_GATE_RESPONSE_INVARIANT_root_cause')
    def test_20_bad_action(self):
        r=dict(self.response, next_check_code='RESTART_ROUTER')
        self.hold(self.env(response=json.dumps(r)), 'C632_GATE_RESPONSE_NEXT_CHECK_NOT_ALLOWED')
    def test_21_incorrect_sha(self):
        r=dict(self.response, input_sha256='0'*64)
        self.hold(self.env(response=json.dumps(r)), 'C632_GATE_RESPONSE_INVARIANT_input_sha256')
    def test_22_non_ascii(self):
        self.hold(self.env(response='ź'), 'NON_ASCII_RESPONSE')
    def test_23_duplicate_response_key(self):
        self.hold(self.env(response='{"schema":"x","schema":"y"}'), 'DUPLICATE_JSON_KEY')
    def test_24_duplicate_envelope_key(self):
        raw=self.env()[:-1]+b',"model":"bad"}'
        self.hold(raw, 'DUPLICATE_JSON_KEY')
    def test_25_invalid_nan(self):
        self.hold(self.env(response='{"x":NaN}'), 'INVALID_JSON_CONSTANT')
    def test_26_envelope_oversize(self):
        self.hold(b'X'*(MAX_ENVELOPE_BYTES+1), 'ENVELOPE_SIZE_INVALID')
    def test_27_model_response_oversize(self):
        self.hold(self.env(response='X'*(bounded.MAX_RESPONSE_BYTES+1)), 'MODEL_RESPONSE_SIZE_INVALID')
    def test_28_bad_json(self):
        self.hold(b'{', 'INVALID_JSON')
    def test_29_historical_blocked(self):
        p=dict(self.pkt,source_type=bridge.ORIGIN_OPERATOR)
        with self.assertRaisesRegex(Hold,'HISTORICAL_INPUT_FORBIDDEN'):
            make_request(p)
    def test_30_http_endpoint_allowlist(self):
        with self.assertRaisesRegex(Hold,'ENDPOINT_NOT_ALLOWED'):
            bounded_http(None,'/api/pull')
    def test_31_no_redirect(self):
        with self.assertRaisesRegex(Hold,'HTTP_REDIRECT_FORBIDDEN'):
            NoRedirect().redirect_request(None,None,302,'Moved',None,'http://example.com')
    def test_32_second_safe_code(self):
        r=dict(self.response,next_check_code='REQUEST_OPERATOR_APPROVED_ACL_VERIFICATION')
        x=validate_ollama(self.env(response=json.dumps(r)), self.pkt)
        self.assertEqual(x['accepted_next_check_code'],r['next_check_code'])
    def test_33_provenance_unverified(self):
        self.assertIs(self.pkt['source_provenance_attested'],False)
    def test_34_selftest_never_invokes_network(self):
        self.assertFalse('raw_log' in json.dumps(self.pkt))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--self-test', action='store_true')
    modes.add_argument('--fixture-matrix', action='store_true')
    modes.add_argument('--ollama-preflight', action='store_true', help='Explicit local GET /api/tags; no model generation')
    modes.add_argument('--qwen-shadow', action='store_true', help='Explicit synthetic-only local Ollama inference')
    args = parser.parse_args(argv)
    print('=== LOCAL AI AGENT / C.63.3 / QWEN SHADOW ===')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    if args.self_test:
        print('MODE=OFFLINE_SELFTEST NETWORK=NO')
        result = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(OfflineTests))
        good=result.testsRun-len(result.failures)-len(result.errors)
        print(f'C633_SELFTESTS={good}/{result.testsRun}')
        print('C633_RESULT='+('PASS_OFFLINE' if result.wasSuccessful() and result.testsRun==34 else 'HOLD'))
        return 0 if result.wasSuccessful() and result.testsRun==34 else 1
    if args.fixture_matrix:
        print('MODE=SYNTHETIC_FIXTURE NETWORK=NO MODEL_CONTACTED=NO')
        pkt=packet(); valid=bounded.response_for_fixture(pkt)
        try:
            accepted=validate_ollama(json.dumps({'model':MODEL,'done':True,'done_reason':'stop',
                'response':json.dumps(valid)}).encode('ascii'),pkt)
            truncated=False
            try:
                validate_ollama(json.dumps({'model':MODEL,'done':True,'done_reason':'length',
                    'response':json.dumps(valid)}).encode('ascii'),pkt)
            except Hold:
                truncated=True
            print('FIXTURE_ACCEPT='+accepted['result'])
            print('FIXTURE_TRUNCATION_HOLD='+str(truncated).upper())
            print('C633_RESULT='+('PASS_SYNTHETIC_ONLY' if truncated else 'HOLD'))
            return 0 if truncated else 1
        except Hold as exc:
            print('C633_RESULT=HOLD_'+str(exc));return 1
    if args.ollama_preflight:
        print('MODE=MANUAL_LOCAL_OLLAMA_TAGS_READ LOOPBACK_ONLY=YES NO_GENERATION=YES')
        try:
            status=check_model_installed(opener()); print('MODEL='+MODEL)
            print('C633_RESULT=PASS_'+status);return 0
        except Hold as exc:
            print('C633_RESULT=HOLD_'+str(exc));return 1
    print('MODE=MANUAL_LOCAL_QWEN_SHADOW INPUT=SYNTHETIC_ONLY')
    print('NETWORK=LOOPBACK_127.0.0.1_ONLY; MODEL_GENERATION=YES; NO_AGENT_ACTIONS=YES')
    try:
        result=run_shadow(opener())
        print('MODEL='+MODEL)
        print('ACCEPTED_ASSESSMENT='+result['accepted_assessment_code'])
        print('ACCEPTED_NEXT_CHECK='+result['accepted_next_check_code'])
        print('MODEL_ACTION_AUTHORITY=NONE')
        print('C633_RESULT=PASS_QWEN_SHADOW_CODES_ONLY')
        return 0
    except Hold as exc:
        print('C633_RESULT=HOLD_'+str(exc))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
