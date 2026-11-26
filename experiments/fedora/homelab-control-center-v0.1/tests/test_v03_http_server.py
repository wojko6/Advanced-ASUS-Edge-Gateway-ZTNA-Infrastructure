"""Fixture-only V0.3 HTTP routing tests; no real VM or router calls."""
import datetime as dt
import http.client
import json
import sys
from pathlib import Path
from http.server import HTTPServer
from threading import Thread
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT / 'tools'))
import v03_local_server as v03

NOW=dt.datetime(2026,10,26,10,55,33,tzinfo=dt.timezone.utc)
VALID=v03.dns.snapshot({
  'collection':NOW.timestamp()-53,'valid':1,'local':1,
  'bootstrap':0,'breakglass':0,'watchdog':1
},NOW)

class RouteLab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=HTTPServer(('127.0.0.1',0),v03.RequestHandler)
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def fetch(self,method,path,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=2)
        try:
            h={'Host':'127.0.0.1:8788'}
            h.update(headers or {})
            conn.request(method,path,headers=h)
            resp=conn.getresponse()
            return resp.status,resp.read(),dict(resp.getheaders())
        finally:
            conn.close()

    def test_v03_page_contains_two_real_sources_and_demo_disclaimer(self):
        code,body,headers=self.fetch('GET','/')
        self.assertEqual(code,200)
        text=body.decode()
        self.assertIn('V0.3',text)
        self.assertIn('id="live-dns-guard"',text)
        self.assertIn('id="live-vm"',text)
        self.assertIn('pozostają fikcyjne',text)
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertEqual(headers['X-Frame-Options'],'DENY')

    def test_static_assets_and_old_v02_api_remain_available(self):
        for name in ('dns-guard-live.mjs','dns-guard-model.mjs','live.mjs','styles.css'):
            self.assertEqual(self.fetch('GET','/'+name)[0],200)
        with patch.object(v03.v02,'get_summary',return_value=v03.v02.project_aggregates({},NOW)):
            code,raw,_=self.fetch('GET','/api/summary',{'Sec-Fetch-Site':'same-origin'})
        self.assertEqual(code,200)
        self.assertEqual(json.loads(raw)['status'],'UNKNOWN')

    def test_api_contract_with_sanitized_mock(self):
        with patch.object(v03.dns,'collect',return_value=VALID) as collect:
            code,raw,headers=self.fetch('GET','/api/dns-guard',{'Sec-Fetch-Site':'same-origin'})
        collect.assert_called_once_with()
        self.assertEqual(code,200)
        self.assertEqual(headers['Cache-Control'],'no-store')
        data=json.loads(raw)
        self.assertEqual((data['status'],data['dns_mode']),('OK','LOCAL'))
        self.assertNotIn('router',str(data).lower().replace('router-contact',''))  # no endpoint/host fields

    def test_wrong_host_and_cross_site_rejected_before_probe(self):
        with patch.object(v03.dns,'collect',side_effect=AssertionError('unexpected API read')):
            for headers in (
                {'Host':'control.home.arpa'},
                {'Host':'attacker.invalid'},
                {'Sec-Fetch-Site':'cross-site'},
                {'Sec-Fetch-Site':'same-site'},
                {'Origin':'https://control.home.arpa'},
                {'Origin':'https://external.invalid'},
            ):
                with self.subTest(headers=headers):
                    self.assertEqual(self.fetch('GET','/api/dns-guard',headers)[0],403)
            self.assertEqual(self.fetch('GET','/dns-guard-live.mjs',{'Host':'bad.invalid'})[0],403)

    def test_mutations_and_unlisted_routes_blocked(self):
        for verb in ('POST','PUT','DELETE','PATCH'):
            self.assertEqual(self.fetch(verb,'/api/dns-guard')[0],405)
        for path in ('/api/dns-guard?query=up','/api/v1/query','/.git/config',
                     '/tools/v03_local_server.py','/%2e%2e/README.md','/index-v03.html'):
            self.assertEqual(self.fetch('GET',path)[0],404)

if __name__=='__main__':unittest.main()
