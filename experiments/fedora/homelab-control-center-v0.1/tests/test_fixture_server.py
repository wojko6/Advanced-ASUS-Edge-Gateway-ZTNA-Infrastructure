"""Synthetic V0.2 browser/API fault contract: never contacts production VM."""
import datetime as dt
import json
import sys
import http.client
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
from unittest import TestCase
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
import v02_fixture_server as fixtures  # noqa: E402

NOW = dt.datetime(2026, 10, 25, 13, 0, tzinfo=dt.timezone.utc)


class FixtureContract(TestCase):
    def test_six_deterministic_cases_and_no_private_labels(self):
        expected = {
            "ok": "OK", "partial": "DEGRADED", "down": "DOWN",
            "stale": "STALE", "unavailable": "UNKNOWN", "expired": "OK",
        }
        for case, status in expected.items():
            with self.subTest(case=case):
                obj = fixtures.build_fixture(case, NOW)
                self.assertEqual(obj["status"], status)
                self.assertEqual(obj["source"], "SYNTHETIC_FIXTURE_NO_LIVE_MONITORING")
                self.assertNotIn("127.0.0.1:8428", json.dumps(obj))
                self.assertNotIn("metric", json.dumps(obj))

    def test_unknown_case_and_timezone_rejected(self):
        with self.assertRaises(ValueError):
            fixtures.build_fixture("production", NOW)
        with self.assertRaises(ValueError):
            fixtures.build_fixture("ok", NOW.replace(tzinfo=None))

    def test_expired_snapshot_keeps_preexpiry_verdict_only_as_fixture(self):
        fixture = fixtures.build_fixture("expired", NOW)
        when = dt.datetime.fromisoformat(fixture["observed_at"].replace("Z", "+00:00"))
        self.assertEqual((NOW - when).total_seconds(), 240)
        self.assertEqual(fixture["ttl_seconds"], 120)


class FixtureHTTP(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), fixtures.backend.RequestHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, *, host=None):
        port = self.server.server_port
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            conn.request(method, path, headers={"Host": host or f"127.0.0.1:{port}"})
            reply = conn.getresponse()
            return reply.status, reply.read(), dict(reply.getheaders())
        finally:
            conn.close()

    def test_mock_http_routes_no_real_vm_call(self):
        for case in fixtures.CASES:
            with self.subTest(case=case):
                def forbid(*args, **kwargs):
                    raise AssertionError("A fixture called real VictoriaMetrics")
                with patch.object(fixtures.backend, "PORT", self.server.server_port), \
                     patch.object(fixtures.backend, "get_summary", lambda: fixtures.build_fixture(case, NOW)), \
                     patch.object(fixtures.backend, "fixed_vm_get", forbid), \
                     patch.dict(fixtures.backend.STATIC, {"/": ("index-fixture.html", "text/html; charset=utf-8")}):
                    code, payload, headers = self.request("GET", "/api/summary")
                    self.assertEqual(code, 200)
                    self.assertEqual(headers["Cache-Control"], "no-store")
                    self.assertEqual(json.loads(payload)["source"], "SYNTHETIC_FIXTURE_NO_LIVE_MONITORING")
                    code, page, _ = self.request("GET", "/")
                    self.assertEqual(code, 200)
                    self.assertIn(b"data-fixture-mode", page)
                    self.assertEqual(self.request("POST", "/api/summary")[0], 405)
                    self.assertEqual(self.request("GET", "/api/summary?query=evil")[0], 404)
                    self.assertEqual(self.request("GET", "/", host="attacker.invalid")[0], 403)
