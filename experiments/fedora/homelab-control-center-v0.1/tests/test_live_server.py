"""Offline, fixture-only V0.2 server contract tests. No real VM, ASUS, or Loki calls."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from http.server import HTTPServer
from threading import Thread
import http.client

P = Path(__file__).resolve().parent.parent / 'tools' / 'v02_local_server.py'
spec = importlib.util.spec_from_file_location('v02_local_server', P)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NOW = dt.datetime(2026, 10, 25, 13, 1, 0, tzinfo=dt.timezone.utc)


def raw(value, timestamp=NOW.timestamp()):
    return json.dumps({'status': 'success', 'data': {'resultType': 'vector', 'result': [
        {'metric': {}, 'value': [timestamp, str(value)]}]}}).encode()


class Aggregates(unittest.TestCase):
    def test_live_good(self):
        data = module.project_aggregates({'total': 7., 'healthy': 7., 'age': 29.7}, NOW)
        self.assertEqual((data['status'], data['healthy'], data['total']), ('OK', 7, 7))

    def test_partial_down_and_full_down(self):
        self.assertEqual(module.project_aggregates({'total': 7, 'healthy': 5, 'age': 20}, NOW)['status'], 'DEGRADED')
        self.assertEqual(module.project_aggregates({'total': 7, 'healthy': 0, 'age': 20}, NOW)['status'], 'DOWN')

    def test_stale_precedes_all_up(self):
        r = module.project_aggregates({'total': 7, 'healthy': 7, 'age': 121}, NOW)
        self.assertEqual(r['status'], 'STALE')

    def test_corrupt_absent_and_conflicting_counts(self):
        for data in ({}, {'total': 7, 'healthy': 8, 'age': 8}, {'total': 0, 'healthy': 0, 'age': 8},
                     {'total': 7, 'healthy': float('nan'), 'age': 8}, {'total': 7, 'healthy': 6.5, 'age': 8},
                     {'total': 7, 'healthy': 7, 'age': float('inf')}, {'total': 7, 'healthy': -1, 'age': 3},
                     {'total': 7, 'healthy': 7, 'age': 90000}):
            self.assertEqual(module.project_aggregates(data, NOW)['status'], 'UNKNOWN')

    def test_scalar_parser_rejects_bad_shapes_labels_and_old_data(self):
        self.assertEqual(module.promql_scalar_from_json(raw(7), NOW.timestamp()), 7.)
        corrupt = [b'{', b'{}', json.dumps({'status': 'success', 'data': {'resultType': 'vector', 'result': []}}).encode(),
                   json.dumps({'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'host': 'secret'}, 'value': [NOW.timestamp(), '7']}]}}).encode(),
                   raw(7, NOW.timestamp()-50), raw('NaN'), raw('Inf'),
                   json.dumps({'status': 'success', 'data': {'resultType': 'vector',
                     'result': [{'metric': {}, 'value': [NOW.timestamp(), True]}]}}).encode(),
                   json.dumps({'status': 'success', 'data': {'resultType': 'vector',
                     'result': [{'metric': {}, 'value': [True, '7']}]}}).encode()]
        for body in corrupt:
            with self.subTest(body=body[:60]):
                with self.assertRaises((ValueError, TypeError, KeyError)):
                    module.promql_scalar_from_json(body, NOW.timestamp())

    def test_top_level_non_object_json_is_rejected_and_server_returns_unknown(self):
        malformed = [b'[]', b'null', b'false', b'0', b'"oops"']
        for raw_body in malformed:
            with self.subTest(raw_body=raw_body):
                with self.assertRaises(ValueError):
                    module.promql_scalar_from_json(raw_body, NOW.timestamp())
                got = module.get_summary(read=lambda _query: raw_body, clock=lambda: NOW)
                self.assertEqual(got['status'], 'UNKNOWN')
                self.assertEqual(got['reason_code'], 'SOURCE_UNAVAILABLE_OR_INVALID')
                self.assertIsNone(got['healthy'])
                self.assertIsNone(got['total'])

    def test_strict_allowlist(self):
        self.assertEqual(len(module.QUERIES), 3)
        with self.assertRaises(ValueError):
            module.fixed_vm_get('something malicious')

    def test_three_fixed_queries_no_network_with_fixture(self):
        calls = []
        responses = {'count(up)': raw(7), 'sum(up)': raw(7), 'max(time() - timestamp(up))': raw(29.7)}
        def read(q):
            calls.append(q)
            return responses[q]
        val = module.get_summary(read=read, clock=lambda: NOW)
        self.assertEqual(val['status'], 'OK')
        self.assertEqual(calls, [x[1] for x in module.QUERIES])
        self.assertEqual(set(val), {'schema_version', 'mode', 'source', 'observed_at', 'status',
                                    'reason_code', 'total', 'healthy', 'oldest_sample_age_seconds', 'ttl_seconds'})
        self.assertEqual(json.dumps(val).find('secret'), -1)

    def test_error_unavailable_is_unknown_and_sanitized(self):
        r = module.get_summary(read=lambda q: (_ for _ in ()).throw(OSError('secret/path/to/token')),
                               clock=lambda: NOW)
        self.assertEqual(r['status'], 'UNKNOWN')
        self.assertNotIn('secret', json.dumps(r))


class HTTPHandler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=HTTPServer(('127.0.0.1', 0), module.RequestHandler)
        cls.thread=Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, host=None, extra_headers=None):
        c=http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        try:
            headers = {'Host': host or '127.0.0.1:8788'}
            headers.update(extra_headers or {})
            c.request(method,path,headers=headers)
            r=c.getresponse()
            return r.status,r.read(),dict(r.getheaders())
        finally:
            c.close()

    def test_fixed_assets_no_dynamic_paths(self):
        for path in ('/', '/styles.css', '/live.mjs', '/live-model.mjs', '/model.mjs'):
            code,_,headers=self.request('GET',path)
            self.assertEqual(code,200)
            self.assertEqual(headers['Cache-Control'],'no-store')
        for path in ('/tools/v02_local_server.py','/README.md','/.git/config','/%2e%2e/README.md', '/api/summary?query=arbitrary'):
            self.assertEqual(self.request('GET',path)[0],404)

    def test_writes_denied_and_wrong_host_rejected(self):
        self.assertEqual(self.request('POST','/api/summary')[0],405)
        self.assertEqual(self.request('GET','/',host='malicious.example')[0],403)

    def test_cross_site_browser_requests_rejected_without_querying_vm(self):
        with patch.object(module, 'get_summary', side_effect=AssertionError('unexpected VM query')):
            for extra_headers in (
                {'Sec-Fetch-Site': 'cross-site'},
                {'Sec-Fetch-Site': 'same-site'},
                {'Origin': 'https://attacker.invalid'},
            ):
                with self.subTest(extra_headers=extra_headers):
                    code,body,_ = self.request('GET','/api/summary',extra_headers=extra_headers)
                    self.assertEqual(code,403)
                    self.assertEqual(body,b'')
        with patch.object(module, 'get_summary', return_value=module.project_aggregates({}, NOW)):
            code,_,_ = self.request('GET','/api/summary',
                                    extra_headers={'Sec-Fetch-Site':'same-origin',
                                                   'Origin':'http://127.0.0.1:8788'})
            self.assertEqual(code,200)
        # A user may click a link to the local dashboard from another site.
        # Static navigation is permitted; only cross-site API queries are denied.
        code,_,_ = self.request('GET','/',extra_headers={'Sec-Fetch-Site':'cross-site'})
        self.assertEqual(code,200)

    def test_api_only_safe_fields_when_dependency_unavailable(self):
        with patch.object(module, 'get_summary', return_value=module.project_aggregates({}, NOW)):
            code,rawbody,headers=self.request('GET','/api/summary')
        self.assertEqual(code,200)
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertEqual(json.loads(rawbody)['status'],'UNKNOWN')

if __name__=='__main__': unittest.main()
