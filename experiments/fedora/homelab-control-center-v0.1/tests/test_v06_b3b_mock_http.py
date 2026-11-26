"""HCC V0.6-B3B1: mock-only loopback HTTP boundary and cancellation tests."""
from __future__ import annotations

import http.client
import json
from email.message import Message
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import v06_b3b_mock_http as b3b


def headers(*pairs):
    message = Message()
    for k, v in pairs:
        message.add_header(k, v)
    return message


def http_request(port, path, *, method="GET", custom=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    opts = custom or {}
    try:
        conn.request(method, path, headers={"Host": f"127.0.0.1:{port}", **opts})
        result = conn.getresponse()
        return result.status, dict(result.getheaders()), result.read()
    finally:
        conn.close()


class BoundaryTests(unittest.TestCase):
    def test_one_literal_fixed_window_and_reject_bad_or_ambiguous_query(self):
        for token in b3b.WINDOWS:
            got = b3b.validate_request(
                f"/api/dns-guard-history?window={token}",
                headers(("Host", "127.0.0.1:8790")), 8790,
            )
            self.assertEqual(got, token)
        bad = [
            "/api/dns-guard-history", "/api/dns-guard-history?window=30d",
            "/api/dns-guard-history?window=24h&window=7d",
            "/api/dns-guard-history?window=24h&query=up",
            "/api/dns-guard-history?window=%32%34h",
            "/api/dns-guard-history?window=24h#fragment",
            "/api/dns-guard-history?window=24h/",
            "http://evil.test/api/dns-guard-history?window=24h",
        ]
        for path in bad:
            with self.subTest(path=path), self.assertRaises(ValueError):
                b3b.validate_request(path, headers(
                    ("Host", "127.0.0.1:8790")), 8790)

    def test_reject_cross_site_host_origin_body_and_duplicate_headers(self):
        good = "/api/dns-guard-history?window=24h"
        for bag in [
            headers(("Host", "localhost:8790")),
            headers(("Host", "127.0.0.1:8790"), ("Host", "evil.test")),
            headers(("Host", "127.0.0.1:8790"), ("Origin", "http://evil.test")),
            headers(("Host", "127.0.0.1:8790"), ("Origin", "http://127.0.0.1:8790"),
                    ("Origin", "http://evil.test")),
            headers(("Host", "127.0.0.1:8790"), ("Sec-Fetch-Site", "cross-site")),
            headers(("Host", "127.0.0.1:8790"), ("Sec-Fetch-Site", "same-site")),
            headers(("Host", "127.0.0.1:8790"), ("Content-Length", "1")),
            headers(("Host", "127.0.0.1:8790"), ("Transfer-Encoding", "chunked")),
        ]:
            with self.subTest(fields=list(bag.items())), self.assertRaises(ValueError):
                b3b.validate_request(good, bag, 8790)
        for bag in [
            headers(("Host", "127.0.0.1:8790")),
            headers(("Host", "127.0.0.1:8790"), ("Sec-Fetch-Site", "none")),
            headers(("Host", "127.0.0.1:8790"), ("Origin", "http://127.0.0.1:8790"),
                    ("Sec-Fetch-Site", "same-origin")),
        ]:
            self.assertEqual(b3b.validate_request(good, bag, 8790), "24h")

    def test_internal_worker_never_returns_sampled_or_live_status(self):
        for window in b3b.WINDOWS:
            expected = b3b.unknown(window)
            self.assertEqual(expected["status"], "UNKNOWN")
            self.assertEqual(expected["mode"], "MOCK_ONLY")
            self.assertEqual(expected["deployment_gate"], "HOLD")
            self.assertEqual(expected["segments"], [])
            self.assertEqual(expected["gaps"], [])
            self.assertEqual(b3b.run_mock_worker(window), expected)
        self.assertEqual(b3b.run_mock_worker("30d")["status"], "UNKNOWN")

    def test_worker_timeout_or_malformed_result_fails_to_unknown(self):
        with patch.object(b3b.subprocess, "run", side_effect=subprocess.TimeoutExpired(
                cmd=["mock"], timeout=0.01)):
            self.assertEqual(b3b.run_mock_worker("24h"), b3b.unknown("24h"))
        fake = subprocess.CompletedProcess(args=["mock"], returncode=0, stdout=b'{"status":"OK"}')
        with patch.object(b3b.subprocess, "run", return_value=fake):
            self.assertEqual(b3b.run_mock_worker("24h"), b3b.unknown("24h"))
        with patch.object(b3b.subprocess, "run", return_value=subprocess.CompletedProcess(
                args=["mock"], returncode=0, stdout=b"x"*(b3b.MAX_BODY+1))):
            self.assertEqual(b3b.run_mock_worker("7d"), b3b.unknown("7d"))
        with patch.object(b3b.subprocess, "run", return_value=subprocess.CompletedProcess(
                args=["mock"], returncode=1, stdout=b"PRIVATE")):
            self.assertNotIn("PRIVATE", str(b3b.run_mock_worker("1h")))

    def test_actual_ephemeral_http_is_mock_only_and_no_store(self):
        server = b3b.BoundedServer(("127.0.0.1", 0), b3b.RequestHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            port = server.server_address[1]
            status, fields, body = http_request(port, "/api/dns-guard-history?window=24h")
            self.assertEqual(status, 200)
            payload = json.loads(body)
            self.assertEqual(payload, b3b.unknown("24h"))
            self.assertEqual(fields["Cache-Control"], "no-store, max-age=0")
            self.assertEqual(fields["X-Content-Type-Options"], "nosniff")
            self.assertLessEqual(len(body), b3b.MAX_BODY)
            for path in [
                "/api/dns-guard-history?window=24h&window=7d",
                "/api/dns-guard-history?window=24h&match[]=private",
                "/api/summary",
            ]:
                code, _, raw = http_request(port, path)
                self.assertEqual(code, 403)
                self.assertEqual(raw, b"")
            self.assertEqual(http_request(port, "/api/dns-guard-history?window=24h",
                           method="POST")[0], 405)
            self.assertEqual(http_request(port, "/api/dns-guard-history?window=24h",
                           custom={"Origin": "https://evil.test"})[0], 403)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)

    def test_one_inflight_mock_read_and_nonblocking_unrelated_denial(self):
        server = b3b.BoundedServer(("127.0.0.1", 0), b3b.RequestHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        started, release = threading.Event(), threading.Event()
        outcome = []
        def blocked(window):
            started.set()
            release.wait(timeout=2)
            return b3b.unknown(window)
        try:
            port = server.server_address[1]
            with patch.object(b3b, "run_mock_worker", side_effect=blocked):
                t = threading.Thread(target=lambda: outcome.append(
                    http_request(port, "/api/dns-guard-history?window=7d")), daemon=True)
                t.start()
                self.assertTrue(started.wait(timeout=2))
                self.assertEqual(http_request(port, "/api/dns-guard-history?window=24h")[0], 503)
                self.assertEqual(http_request(port, "/forbidden")[0], 403)
                release.set()
                t.join(timeout=2)
                self.assertFalse(t.is_alive())
                self.assertEqual(len(outcome), 1)
                self.assertEqual(outcome[0][0], 200)
        finally:
            release.set()
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)

    def test_never_trust_mock_backend_if_it_returns_healthy_payload(self):
        server = b3b.BoundedServer(("127.0.0.1", 0), b3b.RequestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.object(b3b, "run_mock_worker", return_value={
                    "status": "COVERAGE_OBSERVED", "sample_count": 9999}):
                port = server.server_address[1]
                _, _, body = http_request(port, "/api/dns-guard-history?window=7d")
                self.assertEqual(json.loads(body), b3b.unknown("7d"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_source_file_has_no_vm_import_or_auto_launch(self):
        source = Path(b3b.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import v06_history_source", source)
        self.assertNotIn("127.0.0.1:8428", source)
        self.assertNotIn("systemctl", source)
        self.assertNotIn("setInterval", source)
        self.assertEqual(b3b.BIND, "127.0.0.1")
        self.assertNotEqual(b3b.PORT, 8788)


if __name__ == "__main__":
    unittest.main()
