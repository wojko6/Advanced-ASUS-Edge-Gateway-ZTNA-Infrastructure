"""Mock-only local HTTP tests for the alternative V0.4 manual server."""
import datetime as dt
import http.client
import json
import sys
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT / "tools"))
import v04_local_server as v04

NOW=dt.datetime(2026,10,27,14,0,tzinfo=dt.timezone.utc)
VALID=v04.dnsprobe.project_live({"probe_success":1,"sample_age_seconds":1.5},NOW)


class V04HTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=HTTPServer(("127.0.0.1",0),v04.RequestHandler)
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def fetch(self,method,path,headers=None):
        conn=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=2)
        try:
            h={"Host":"127.0.0.1:8788"}
            h.update(headers or {})
            conn.request(method,path,headers=h)
            resp=conn.getresponse()
            return resp.status,resp.read(),dict(resp.getheaders())
        finally:
            conn.close()

    def test_page_contains_three_real_regions_and_demo_opt_in(self):
        code,body,h=self.fetch("GET","/")
        self.assertEqual(code,200)
        html=body.decode("utf-8")
        for phrase in ('V0.4','id="live-vm"','id="live-dns-guard"',
                       'id="live-router-dns"','data-demo-gate="opt-in"',
                       'id="demo-toggle"','pozostają fikcyjne'):
            self.assertIn(phrase,html)
        self.assertEqual(h["Cache-Control"],"no-store")
        self.assertEqual(h["X-Frame-Options"],"DENY")

    def test_static_allowlist_and_previous_v03_endpoints(self):
        for name in ("router-dns-live.mjs","router-dns-model.mjs",
                     "dns-guard-live.mjs","dns-guard-model.mjs",
                     "app.mjs","live.mjs","styles.css"):
            with self.subTest(name=name):
                self.assertEqual(self.fetch("GET","/"+name)[0],200)
        with patch.object(v04.v03.dns,"collect",return_value={
                "schema_version":"0.3","status":"UNKNOWN"}):
            self.assertEqual(self.fetch("GET","/api/dns-guard")[0],200)
        with patch.object(v04.v02,"get_summary",return_value={"status":"UNKNOWN"}):
            self.assertEqual(self.fetch("GET","/api/summary")[0],200)

    def test_live_dns_api_sanitized_payload_and_headers(self):
        with patch.object(v04.dnsprobe,"collect",return_value=VALID) as collect:
            code,raw,h=self.fetch("GET","/api/router-dns",
                                  {"Sec-Fetch-Site":"same-origin"})
        collect.assert_called_once_with()
        self.assertEqual(code,200)
        self.assertEqual(h["Cache-Control"],"no-store")
        self.assertEqual(h["X-Content-Type-Options"],"nosniff")
        data=json.loads(raw)
        self.assertEqual((data["status"],data["reason_code"]),
                         ("OK","ONE_DNS_PROBE_SUCCEEDED"))
        self.assertNotIn("instance",str(data))
        self.assertNotIn("192.168.",str(data))

    def test_cross_site_and_wrong_host_reject_before_source(self):
        with patch.object(v04.dnsprobe,"collect",
                          side_effect=AssertionError("must not query source")):
            for headers in (
                {"Host":"control.home.arpa"},
                {"Host":"attacker.invalid"},
                {"Sec-Fetch-Site":"cross-site"},
                {"Sec-Fetch-Site":"same-site"},
                {"Origin":"https://control.home.arpa"},
                {"Origin":"https://attacker.invalid"},
            ):
                with self.subTest(headers=headers):
                    self.assertEqual(
                        self.fetch("GET","/api/router-dns",headers)[0],403)

    def test_writes_unauthorized_routes_and_dynamic_queries_blocked(self):
        with patch.object(v04.dnsprobe,"collect",
                          side_effect=AssertionError("must not query source")):
            for method in ("POST","PUT","PATCH","DELETE"):
                self.assertEqual(self.fetch(method,"/api/router-dns")[0],405)
            for path in ("/api/router-dns?query=up","/api/v1/query",
                         "/index-v04.html","/tools/v04_local_server.py",
                         "/%2e%2e/.git/config","/metrics"):
                self.assertEqual(self.fetch("GET",path)[0],404)
            self.assertEqual(
                self.fetch("GET","/router-dns-live.mjs",
                           {"Host":"attacker.invalid"})[0],403)

    def test_api_rejects_payload_oversize(self):
        with patch.object(v04.dnsprobe,"collect",
                          return_value={"message":"x"*10000}):
            code,raw,_=self.fetch("GET","/api/router-dns")
        self.assertEqual(code,503)
        self.assertEqual(raw,b"")


if __name__=="__main__":
    unittest.main()
