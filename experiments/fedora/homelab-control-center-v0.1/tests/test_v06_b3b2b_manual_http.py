"""HCC B3B2B mock-only integration tests; NO real VictoriaMetrics contact."""
from __future__ import annotations

import contextlib
import http.client
import io
import json
from email.message import Message
from types import SimpleNamespace
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import ANY, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import v06_b3b2b_manual_http as http_lab
import v06_b3b_mock_http as b3b1
import v06_b3b2_source_supervisor as guard
import v06_b3b2d_cancel_guard as peer_guard
import v06_coverage_model as coverage
import v06_history_source as b2

END = 1793260800000


def synthetic(window="1h"):
    points = [END-120000, END-60000, END]
    series = {}
    for name in coverage.SUFFIXES:
        if name in ("mode_local", "state_valid"):
            values = [1, 1, 1]
        elif name == "collection_timestamp_seconds":
            values = [n//1000 for n in points]
        else:
            values = [0, 0, 0]
        series[name] = list(zip(points, values))
    data = coverage.analyze(series, window, END)
    data["source_adapter"] = b2.SCHEMA
    return data


def request(port, path="/api/dns-guard-history?window=1h", method="GET", headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        hdr = {"Host": f"127.0.0.1:{port}"}
        if headers:
            hdr.update(headers)
        conn.request(method, path, headers=hdr)
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        conn.close()


class MockHttpIntegrationTests(unittest.TestCase):
    def setUp(self):
        # A missing mock must NEVER spawn the real B2 source child.
        # Fail the test even if the HTTP handler masks that attempt as UNKNOWN.
        self._no_source_process = patch.object(
            peer_guard.subprocess, "Popen",
            side_effect=AssertionError("UNEXPECTED_REAL_SOURCE_PROCESS_IN_MOCK_TEST"))
        self._source_popen = self._no_source_process.start()
        self.addCleanup(self._no_source_process.stop)
        self.addCleanup(self._source_popen.assert_not_called)
        self.server = b3b1.BoundedServer(("127.0.0.1", 0), http_lab.HistoryHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_no_background_read_on_server_start_or_idle(self):
        with patch.object(peer_guard, "read_b2_with_peer",
                          side_effect=AssertionError("unexpected source read")) as read:
            self.assertEqual(http_lab.BIND, "127.0.0.1")
            self.assertEqual(http_lab.PORT, 8791)
            self.assertNotEqual(http_lab.PORT, b3b1.PORT)
            self.assertNotEqual(http_lab.PORT, 8788)
            read.assert_not_called()

    def test_one_explicit_request_returns_bounded_sanitized_evidence(self):
        report = synthetic()
        report["PRIVATE_ROUTER_NAME"] = "DO_NOT_EXPOSE"
        with patch.object(peer_guard, "read_b2_with_peer", return_value=report) as read:
            status, headers, raw = request(self.port)
        self.assertEqual(status, 200)
        self.assertEqual(read.call_count, 1)
        read.assert_called_once_with("1h", ANY)
        data = json.loads(raw)
        self.assertEqual(data["sample_count"], 3)
        self.assertEqual(data["status"], "COVERAGE_OBSERVED_WITH_UNCERTAINTY")
        self.assertEqual(data["gaps"][0]["cause"], "NOT_DETERMINED")
        self.assertNotIn("DO_NOT_EXPOSE", raw.decode())
        self.assertEqual(headers["Cache-Control"], "no-store, max-age=0")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertLessEqual(len(raw), http_lab.MAX_RESPONSE_BYTES)

    def test_unknown_on_worker_failure_without_stale_success(self):
        with patch.object(peer_guard, "read_b2_with_peer",
                          side_effect=[synthetic(), guard.unknown(), RuntimeError("PRIVATE")]):
            first = json.loads(request(self.port)[2])
            second = json.loads(request(self.port)[2])
            third = json.loads(request(self.port)[2])
        self.assertEqual(first["sample_count"], 3)
        for stale in (second, third):
            self.assertEqual(stale["status"], "UNKNOWN")
            self.assertIsNone(stale["sample_count"])
            self.assertEqual(stale["segments"], [])
            self.assertNotIn("PRIVATE", json.dumps(stale))

    def test_malformed_source_extra_fields_or_oversized_is_never_returned(self):
        for bad in (
            {"status": "OK", "private": "SECRET"},
            {"status": "COVERAGE_OBSERVED", "sample_count": 44},
            {**synthetic(), "window": "7d"},
            {**synthetic(), "sample_count": 99999},
            {**synthetic(), "padding": "PRIVATE"*15000},
            False,
        ):
            with self.subTest(bad_type=type(bad).__name__), patch.object(
                    peer_guard, "read_b2_with_peer", return_value=bad) as read:
                status, _, raw = request(self.port)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw), guard.unknown())
            read.assert_called_once_with("1h", ANY)
            self.assertNotIn("SECRET", raw.decode())

    def test_bad_paths_methods_headers_blocked_before_source(self):
        paths = (
            "/api/dns-guard-history?window=7d&window=1h",
            "/api/dns-guard-history?window=24h&match[]=secret",
            "/api/dns-guard-history?window=4h",
            "/api/summary",
        )
        with patch.object(peer_guard, "read_b2_with_peer") as read:
            for path in paths:
                code, _, body = request(self.port, path)
                self.assertEqual((code, body), (403, b""))
            for hdr in ({"Origin": "https://untrusted.example"},
                        {"Sec-Fetch-Site": "cross-site"},
                        {"Host": "other-host.test"}):
                self.assertEqual(request(self.port, headers=hdr)[0], 403)
            self.assertEqual(request(self.port, method="POST")[0], 405)
            self.assertEqual(request(self.port, method="HEAD")[0], 405)
            read.assert_not_called()

    def test_second_read_gets_503_and_unrelated_invalid_get_remains_fast(self):
        started, release = threading.Event(), threading.Event()
        results = []

        def blocked(window, peer):
            started.set()
            release.wait(timeout=2)
            return guard.unknown()

        def first():
            results.append(request(self.port, "/api/dns-guard-history?window=7d"))

        try:
            with patch.object(peer_guard, "read_b2_with_peer", side_effect=blocked):
                thread = threading.Thread(target=first, daemon=True)
                thread.start()
                self.assertTrue(started.wait(timeout=2))
                self.assertEqual(request(self.port)[0], 503)
                self.assertEqual(request(self.port, "/bad")[0], 403)
                release.set()
                thread.join(timeout=3)
                self.assertFalse(thread.is_alive())
                self.assertEqual(results[0][0], 200)
                self.assertEqual(json.loads(results[0][2])["status"], "UNKNOWN")
        finally:
            release.set()

    def test_source_exception_failure_releases_lock(self):
        with patch.object(peer_guard, "read_b2_with_peer", side_effect=RuntimeError("fault")):
            self.assertEqual(json.loads(request(self.port)[2])["status"], "UNKNOWN")
        with patch.object(peer_guard, "read_b2_with_peer", return_value=synthetic()):
            self.assertEqual(json.loads(request(self.port)[2])["sample_count"], 3)

    def test_disconnect_during_headers_or_body_never_retries_response(self):
        # Source completes, but the client goes away during response delivery.
        # We must never attempt to begin a second response on the same socket.
        for failure in ("headers", "body"):
            with self.subTest(failure=failure):
                handler = object.__new__(http_lab.HistoryHandler)
                handler.path = "/api/dns-guard-history?window=1h"
                handler.headers = Message()
                handler.headers.add_header("Host", "127.0.0.1:8791")
                lock = threading.Lock()
                handler.server = SimpleNamespace(
                    server_address=("127.0.0.1", 8791), history_lock=lock)
                handler.connection = MagicMock()
                handler._headers = MagicMock(
                    side_effect=BrokenPipeError if failure == "headers" else None)
                handler.wfile = MagicMock()
                if failure == "body":
                    handler.wfile.write.side_effect = ConnectionResetError
                with patch.object(peer_guard, "read_b2_with_peer",
                                  return_value=synthetic()) as read, \
                     patch.object(http_lab, "disconnected", return_value=False):
                    handler.do_GET()
                read.assert_called_once_with("1h", ANY)
                self.assertEqual(handler._headers.call_count, 1)
                handler.connection.settimeout.assert_called_once_with(
                    http_lab.MAX_WRITE_OPERATION_SECONDS)
                self.assertFalse(lock.locked())

    def test_source_exception_emits_one_neutral_response_not_private_data(self):
        handler = object.__new__(http_lab.HistoryHandler)
        handler.path = "/api/dns-guard-history?window=1h"
        handler.headers = Message()
        handler.headers.add_header("Host", "127.0.0.1:8791")
        lock = threading.Lock()
        handler.server = SimpleNamespace(
            server_address=("127.0.0.1", 8791), history_lock=lock)
        handler.connection = MagicMock()
        handler._headers = MagicMock()
        handler.wfile = MagicMock()
        with patch.object(peer_guard, "read_b2_with_peer",
                          side_effect=RuntimeError("SECRET")) as read, \
             patch.object(http_lab, "disconnected", return_value=False):
            handler.do_GET()
        read.assert_called_once()
        handler._headers.assert_called_once()
        self.assertEqual(json.loads(handler.wfile.write.call_args.args[0]),
                         guard.unknown())
        self.assertFalse(lock.locked())

    def test_no_root_or_listener_without_explicit_two_flags(self):
        with patch.object(sys, "argv", ["script.py", "--inspect"]), \
             patch.object(peer_guard, "read_b2_with_peer", side_effect=AssertionError("read")), \
             patch.object(http_lab.b3b1 if hasattr(http_lab,"b3b1") else b3b1, "BoundedServer",
                          side_effect=AssertionError("listener")), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(http_lab.main(), 0)
            self.assertEqual(json.loads(output.getvalue())["mode"], "INSPECT_ONLY_NO_NETWORK")
        with patch.object(sys, "argv", ["script.py", "--serve-manual-local-history"]), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                http_lab.main()
        self.assertEqual(http_lab.MAX_RESPONSE_BYTES, 65536)


if __name__ == "__main__":
    unittest.main()
