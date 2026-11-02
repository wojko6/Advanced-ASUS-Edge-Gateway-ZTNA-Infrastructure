#!/usr/bin/env python3
"""C.64.1: fixed loopback HTTP transport contract, with mock connections only.

NO real HTTP connections are created. All eight GETs are answered by scripted
in-memory connection objects. This is not a live-data reader or model entrypoint.
The existing C.63.8.1 GET client and C.64.0 parser are reused, but the actual
socket/HTTPConnection constructor is never selected by this CLI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_ai_agent_v021c64_0_synthetic_vm_envelope_adapter as c64

vm = c64.vm
SCHEMA = 'local-ai-agent.v0.21.c64.1.mocked-vm-transport.v1'
FIXED_NOW = c64.FIXED_NOW
ORDER = c64.ORDER
GOOD_CASES = c64.CASES
BAD_CASES = (
    'http_503', 'redirect_302', 'read_timeout', 'oversize',
    'invalid_json', 'foreign_label', 'duplicate_json', 'connection_refused',
)
CASES = GOOD_CASES + BAD_CASES
MAX_OUTPUT_BYTES = 4000
EXPECTED_HOLDS = {
    'http_503': 'HTTP_RESPONSE_NOT_200',
    'redirect_302': 'HTTP_RESPONSE_NOT_200',
    'read_timeout': 'VM_LOOPBACK_UNAVAILABLE',
    'oversize': 'RESPONSE_SIZE_INVALID',
    'invalid_json': 'VM_ENVELOPE_REJECTED',
    'foreign_label': 'VM_ENVELOPE_REJECTED',
    'duplicate_json': 'VM_ENVELOPE_REJECTED',
    'connection_refused': 'TRANSPORT_UNAVAILABLE',
}


class Hold(Exception):
    """Fail closed with bounded, literal, non-sensitive refusal codes."""


class MockResponse:
    """Minimal response object returned in RAM, never an HTTP response from host."""
    def __init__(self, payload, status=200, timeout=False):
        self.status = status
        self.payload = payload
        self.timeout = timeout
        self.read_count = 0
        self.requested_bytes = None

    def read(self, limit):
        self.read_count += 1
        self.requested_bytes = limit
        if self.timeout:
            raise TimeoutError('SIMULATED_TIMEOUT')
        if type(limit) is not int or limit != vm.MAX_RESPONSE_BYTES + 1:
            raise AssertionError('READ_BOUND_VIOLATION')
        return self.payload[:limit]


class MockConnection:
    """Check exact GET request semantics and track resource closure."""
    def __init__(self, server, expected, response):
        self.server = server
        self.expected = expected
        self.response = response
        self.requested = False
        self.responded = False
        self.closed = False

    def request(self, method, path, headers=None):
        if self.requested or self.closed:
            raise AssertionError('REPEATED_OR_CLOSED_REQUEST')
        name, kind = self.expected
        if (method != 'GET'
                or path != vm.make_path(name, kind, FIXED_NOW)
                or headers != {'Accept': 'application/json', 'Connection': 'close'}):
            raise AssertionError('REQUEST_NOT_WHITELISTED')
        self.requested = True
        self.server.requests.append((method, path))

    def getresponse(self):
        if not self.requested or self.responded or self.closed:
            raise AssertionError('RESPONSE_STATE_INVALID')
        self.responded = True
        return self.response

    def close(self):
        if not self.closed:
            self.closed = True
            self.server.closed += 1


class ScriptedServer:
    """Eight connections made from fictional payloads and injected into vm.fetch."""
    def __init__(self, scenario='baseline'):
        if type(scenario) is not str or scenario not in CASES:
            raise Hold('SCENARIO_NOT_WHITELISTED')
        self.scenario = scenario
        positive = scenario if scenario in GOOD_CASES else 'baseline'
        self.packets = c64.fixture_responses(positive)
        self.responses = {}
        self.connections = []
        self.requests = []
        self.closed = 0
        for key in ORDER:
            self.responses[key] = MockResponse(self.packets[key])
        first = ORDER[0]
        r = self.responses[first]
        if scenario == 'http_503':
            r.status = 503
        elif scenario == 'redirect_302':
            r.status = 302
        elif scenario == 'read_timeout':
            r.timeout = True
        elif scenario == 'oversize':
            r.payload = b'X' * (vm.MAX_RESPONSE_BYTES + 1)
        elif scenario == 'invalid_json':
            r.payload = b'not valid json'
        elif scenario == 'foreign_label':
            obj = json.loads(r.payload)
            obj['data']['result'][0]['metric']['private_label'] = 'fictional'
            r.payload = json.dumps(obj, sort_keys=True).encode('ascii')
        elif scenario == 'duplicate_json':
            r.payload = b'{"status":"success","status":"success"}'

    def factory(self, host, port, timeout):
        if (host, port, timeout) != (vm.HOST, vm.PORT, vm.TIMEOUT_SECONDS):
            raise AssertionError('DESTINATION_VIOLATION')
        i = len(self.connections)
        if i >= len(ORDER):
            raise AssertionError('EXCESS_REQUEST')
        if self.scenario == 'connection_refused' and i == 0:
            raise ConnectionRefusedError('MOCK_CONNECTION_REFUSED')
        key = ORDER[i]
        conn = MockConnection(self, key, self.responses[key])
        self.connections.append(conn)
        return conn

    def fetch(self, name, kind, now):
        # Mandatory factory injection: never use vm.fetch's default HTTP client.
        if now != FIXED_NOW or (name, kind) not in ORDER:
            raise Hold('UNAPPROVED_QUERY_OR_CLOCK')
        if len(self.requests) != len(self.connections):
            raise Hold('INVALID_MOCK_REQUEST_SEQUENCE')
        if len(self.connections) >= len(ORDER):
            raise Hold('EXCESS_REQUEST')
        if (name, kind) != ORDER[len(self.connections)]:
            raise Hold('REQUEST_ORDER_INVALID')
        try:
            return vm.fetch(name, kind, now, factory=self.factory)
        except vm.Hold as exc:
            code = str(exc)
            if code not in ('HTTP_RESPONSE_NOT_200', 'VM_LOOPBACK_UNAVAILABLE',
                            'RESPONSE_SIZE_INVALID'):
                raise Hold('TRANSPORT_REJECTED') from None
            raise Hold(code) from None
        except (OSError, TimeoutError, AssertionError) as exc:
            raise Hold('TRANSPORT_UNAVAILABLE') from None


def run_mock(scenario='baseline', *, return_server=False):
    """Perform mocked GET round trips, then parse only validated response bytes."""
    server = ScriptedServer(scenario)
    packets = {}
    for name, kind in ORDER:
        packets[(name, kind)] = server.fetch(name, kind, FIXED_NOW)
    if (len(server.connections) != 8 or len(server.requests) != 8
            or server.closed != 8
            or any(not c.closed or not c.requested or not c.responded
                   or c.response.read_count != 1
                   for c in server.connections)):
        raise Hold('INCOMPLETE_MOCK_SESSION')
    try:
        result = c64.assess_packets(packets, evaluated_at=FIXED_NOW)
    except c64.Hold as exc:
        raise Hold('VM_ENVELOPE_REJECTED') from None
    if (result['quality_gate_decision'] != 'ABSTAIN_NO_MODEL_INFERENCE'
            or result['model_requests'] != 0
            or result['model_action_authority'] != 'NONE'
            or result['remediation_authorized'] is not False
            or result['deployment_gate'] != 'HOLD'
            or result['root_cause'] != 'UNDETERMINED'
            or result['dns_health'] != 'NOT_ESTABLISHED'):
        raise Hold('AUTHORITY_BOUNDARY_FAILED')
    result.update({
        'schema': SCHEMA,
        'mode': 'MOCK_HTTP_TRANSPORT_OFFLINE_ONLY',
        'source_identity': 'SCRIPTED_HTTP_CONNECTIONS_IN_MEMORY_NOT_REAL_VM',
        'source_authenticity': 'NOT_CRYPTOGRAPHICALLY_ATTESTED',
        'transport': 'INJECTED_FAKE_HTTP_CONNECTION_OBJECTS',
        'destination_contract': 'FIXED_127_0_0_1_8428_NOT_CONTACTED',
        'transport_requests': len(server.requests),
        'transport_closed_connections': server.closed,
        'transport_method': 'GET_ONLY',
        'response_headers_verified': False,
        'operator_next_step': 'MANUAL_REVIEW_ONLY',
    })
    if len(json.dumps(result, sort_keys=True, separators=(',', ':')).encode('ascii')) > MAX_OUTPUT_BYTES:
        raise Hold('OUTPUT_TOO_LARGE')
    return (result, server) if return_server else result


def matrix():
    output = {}
    for name in CASES:
        expected_hold = EXPECTED_HOLDS.get(name)
        try:
            result = run_mock(name)
        except Hold as exc:
            if expected_hold is None or str(exc) != expected_hold:
                raise Hold('MATRIX_UNEXPECTED_HOLD') from None
            output[name] = ('EXPECTED_HOLD', expected_hold)
        else:
            if expected_hold is not None:
                raise Hold('MATRIX_FAIL_OPEN')
            output[name] = ('PASS_MOCK', result['observation_classification'])
    return output


class Tests(unittest.TestCase):
    def assert_hold(self, f, expected):
        with self.assertRaisesRegex(Hold, '^' + re.escape(expected) + '$'):
            f()

    def test_01_baseline(self):
        self.assertEqual(run_mock()['sampled_mode'], 'LOCAL')

    def test_02_stats(self):
        self.assertEqual(run_mock('stats_envelope')['sampled_mode'], 'LOCAL')

    def test_03_missing(self):
        self.assertEqual(run_mock('missing_local')['observation_classification'], 'INSUFFICIENT_EVIDENCE')

    def test_04_stale(self):
        self.assertIn('LOCAL_RAW_SAMPLE_STALE', run_mock('stale_local')['gaps'])

    def test_05_future(self):
        self.assertIn('LOCAL_RAW_SAMPLE_IN_FUTURE', run_mock('future_local')['gaps'])

    def test_06_stale_collection(self):
        self.assertIn('COLLECTION_VALUE_STALE', run_mock('stale_collection')['gaps'])

    def test_07_contradictory_flags(self):
        self.assertIn('MODE_FLAGS_CONTRADICTORY', run_mock('contradictory_flags')['gaps'])

    def test_08_invalid_guard(self):
        self.assertEqual(run_mock('invalid_guard')['observation_classification'],
                         'INVALID_DNS_GUARD_STATE_SAMPLED')

    def test_09_exact_eight_requests(self):
        result, server = run_mock(return_server=True)
        self.assertEqual((result['transport_requests'], len(server.connections)), (8, 8))

    def test_10_close_all_connections(self):
        result, server = run_mock(return_server=True)
        self.assertEqual((result['transport_closed_connections'], server.closed), (8, 8))

    def test_11_only_get(self):
        _, server = run_mock(return_server=True)
        self.assertTrue(all(method == 'GET' for method, _ in server.requests))

    def test_12_whitelisted_paths(self):
        _, server = run_mock(return_server=True)
        self.assertEqual(server.requests, [
            ('GET', vm.make_path(name, kind, FIXED_NOW)) for name, kind in ORDER])

    def test_13_exact_host_port_timeout(self):
        server = ScriptedServer()
        self.assertRaises(AssertionError, server.factory, '127.0.0.2', vm.PORT,
                          vm.TIMEOUT_SECONDS)
        self.assertRaises(AssertionError, server.factory, vm.HOST, 80,
                          vm.TIMEOUT_SECONDS)
        self.assertRaises(AssertionError, server.factory, vm.HOST, vm.PORT, 300)

    def test_14_method_override_rejected(self):
        server = ScriptedServer()
        conn = server.factory(vm.HOST, vm.PORT, vm.TIMEOUT_SECONDS)
        with self.assertRaises(AssertionError):
            conn.request('POST', vm.make_path(*ORDER[0], FIXED_NOW),
                         headers={'Accept': 'application/json', 'Connection': 'close'})

    def test_15_header_override_rejected(self):
        server = ScriptedServer()
        conn = server.factory(vm.HOST, vm.PORT, vm.TIMEOUT_SECONDS)
        with self.assertRaises(AssertionError):
            conn.request('GET', vm.make_path(*ORDER[0], FIXED_NOW), headers={})

    def test_16_invalid_query_rejected(self):
        server = ScriptedServer()
        self.assert_hold(lambda: server.fetch('up', 'value', FIXED_NOW),
                         'UNAPPROVED_QUERY_OR_CLOCK')

    def test_17_wrong_clock_rejected(self):
        server = ScriptedServer()
        self.assert_hold(lambda: server.fetch(*ORDER[0], now=FIXED_NOW+1),
                         'UNAPPROVED_QUERY_OR_CLOCK')

    def test_18_http_status_hold(self):
        self.assert_hold(lambda: run_mock('http_503'), 'HTTP_RESPONSE_NOT_200')

    def test_19_redirect_hold(self):
        self.assert_hold(lambda: run_mock('redirect_302'), 'HTTP_RESPONSE_NOT_200')

    def test_20_timeout_hold(self):
        self.assert_hold(lambda: run_mock('read_timeout'), 'VM_LOOPBACK_UNAVAILABLE')

    def test_21_overflow_hold(self):
        self.assert_hold(lambda: run_mock('oversize'), 'RESPONSE_SIZE_INVALID')

    def test_22_bad_json_hold(self):
        self.assert_hold(lambda: run_mock('invalid_json'), 'VM_ENVELOPE_REJECTED')

    def test_23_bad_label_hold(self):
        self.assert_hold(lambda: run_mock('foreign_label'), 'VM_ENVELOPE_REJECTED')

    def test_24_duplicate_key_hold(self):
        self.assert_hold(lambda: run_mock('duplicate_json'), 'VM_ENVELOPE_REJECTED')

    def test_25_refused_connection_hold(self):
        self.assert_hold(lambda: run_mock('connection_refused'), 'TRANSPORT_UNAVAILABLE')

    def test_26_unknown_scenario_hold(self):
        self.assert_hold(lambda: run_mock('live'), 'SCENARIO_NOT_WHITELISTED')

    def test_27_all_matrix_expected_results(self):
        self.assertEqual(len(matrix()), len(CASES))
        self.assertTrue(all(status == 'EXPECTED_HOLD' for scenario,(status,_) in
                            matrix().items() if scenario in BAD_CASES))

    def test_28_no_real_sockets(self):
        with patch('socket.create_connection', side_effect=AssertionError('REAL_SOCKET')):
            with patch('socket.socket', side_effect=AssertionError('REAL_SOCKET')):
                self.assertEqual(run_mock()['model_requests'], 0)

    def test_29_no_default_http_connection(self):
        with patch('http.client.HTTPConnection',
                   side_effect=AssertionError('DEFAULT_HTTP_CONNECTION')):
            self.assertEqual(run_mock()['transport_requests'], 8)

    def test_30_no_subprocess(self):
        with patch('subprocess.Popen', side_effect=AssertionError('SUBPROCESS')):
            self.assertEqual(run_mock()['model_requests'], 0)

    def test_31_no_file_io(self):
        with patch('builtins.open', side_effect=AssertionError('FILE_IO')):
            self.assertEqual(run_mock()['model_requests'], 0)

    def test_32_no_model_and_actions(self):
        for case in GOOD_CASES:
            r = run_mock(case)
            self.assertEqual(r['model_requests'], 0)
            self.assertFalse(r['model_invoked'])
            self.assertFalse(r['remediation_authorized'])
            self.assertEqual(r['model_action_authority'], 'NONE')
            self.assertEqual(r['deployment_gate'], 'HOLD')

    def test_33_unauthenticated_and_nonatomic(self):
        r = run_mock()
        self.assertEqual(r['source_authenticity'], 'NOT_CRYPTOGRAPHICALLY_ATTESTED')
        self.assertFalse(r['observations_are_atomic'])
        self.assertFalse(r['source_fingerprint_is_provenance_attestation'])
        self.assertFalse(r['response_headers_verified'])

    def test_34_never_claims_health_or_cause(self):
        for case in GOOD_CASES:
            r = run_mock(case)
            self.assertEqual(r['root_cause'], 'UNDETERMINED')
            self.assertEqual(r['dns_health'], 'NOT_ESTABLISHED')
            self.assertEqual(r['quality_gate_decision'], 'ABSTAIN_NO_MODEL_INFERENCE')

    def test_35_deterministic(self):
        self.assertEqual(run_mock(), run_mock())

    def test_36_output_size(self):
        self.assertLess(len(json.dumps(run_mock()).encode('ascii')), MAX_OUTPUT_BYTES)

    def test_37_no_private_details(self):
        s = json.dumps(run_mock())
        for forbidden in ('192.168.', '10.0.', 'password', 'journal_raw', 'sudo'):
            self.assertNotIn(forbidden, s)

    def test_38_c64_caller_origin_stays_unverified(self):
        r = c64.assess_packets(c64.fixture_responses())
        self.assertEqual(r['source_identity'],
                         'CALLER_PROVIDED_VM_LIKE_BYTES_ORIGIN_UNVERIFIED')

    def test_39_mock_getter_is_always_injected(self):
        original = vm.fetch
        with patch.object(vm, 'fetch', wraps=original) as spy:
            run_mock()
            self.assertEqual(spy.call_count, 8)
            self.assertTrue(all(call.kwargs.get('factory') is not None
                                for call in spy.call_args_list))

    def test_40_no_response_authentication_claim(self):
        r = run_mock()
        self.assertEqual(r['source_identity'],
                         'SCRIPTED_HTTP_CONNECTIONS_IN_MEMORY_NOT_REAL_VM')
        self.assertEqual(r['destination_contract'], 'FIXED_127_0_0_1_8428_NOT_CONTACTED')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_mutually_exclusive_group(required=True)
    commands.add_argument('--self-test', action='store_true')
    commands.add_argument('--mock-matrix', action='store_true')
    commands.add_argument('--summary-json', action='store_true')
    parser.add_argument('--scenario', choices=CASES, default='baseline')
    args = parser.parse_args(argv)
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        print('C641_TESTS=' + str(result.testsRun) + ' STATUS='
              + ('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_TEST_FAILED'))
        return 0 if result.wasSuccessful() else 1
    try:
        if args.mock_matrix:
            data = matrix()
            for case in CASES:
                status, detail = data[case]
                print('SCENARIO=' + case + ' STATUS=' + status
                      + ' RESULT=' + detail)
            print('C641_RESULT=PASS_16_MOCK_CASES_OFFLINE')
            return 0
        print(json.dumps(run_mock(args.scenario), sort_keys=True,
                         indent=2, ensure_ascii=True))
        return 0
    except Hold as exc:
        print('C641_RESULT=HOLD_' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
