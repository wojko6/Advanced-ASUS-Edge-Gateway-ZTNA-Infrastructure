"""HCC B3B2E exact merged manual handler cancellation tests; SYNTHETIC ONLY.

All possible history GET sources use a patched B3B2A fixed argv, or a mocked
peer-aware guard. No VictoriaMetrics 8428 or ASUS, no persistent service.
"""
from __future__ import annotations

import contextlib
import http.client
import io
import json
import socket
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import v06_b3b2b_manual_http as http_lab
import v06_b3b2d_cancel_guard as peer_guard
import v06_b3b2_source_supervisor as supervisor
import v06_b3b_mock_http as b3b1
import v06_coverage_model as coverage
import v06_history_source as source

PATH = "/api/dns-guard-history?window=1h"
END = 1793260800000


def synthetic():
    points = [END-120000, END-60000, END]
    series = {}
    for name in coverage.SUFFIXES:
        if name in ("mode_local", "state_valid"):
            values = [1, 1, 1]
        elif name == "collection_timestamp_seconds":
            values = [t//1000 for t in points]
        else:
            values = [0, 0, 0]
        series[name] = list(zip(points, values))
    report = coverage.analyze(series, "1h", END)
    assert report["status"] == "COVERAGE_OBSERVED_WITH_UNCERTAINTY"
    report["source_adapter"] = source.SCHEMA
    return report


def argv(script):
    return [sys.executable, "-B", "-c", script]


@contextlib.contextmanager
def ephemeral_handler():
    server = b3b1.BoundedServer(("127.0.0.1", 0), http_lab.HistoryHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request(port, path=PATH, *, method="GET", headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    hdr = {"Host": f"127.0.0.1:{port}"}
    hdr.update(headers or {})
    try:
        conn.request(method, path, headers=hdr)
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        conn.close()


class RealHandlerSyntheticTests(unittest.TestCase):
    def test_no_vm_on_handler_start_or_inspect(self):
        code = Path(http_lab.__file__).read_text(encoding="utf-8")
        self.assertIn("peer_guard", code.replace("cancel_guard", "peer_guard"))
        self.assertNotIn("supervised.read_b2_supervised(", code)
        self.assertEqual(http_lab.BIND, "127.0.0.1")
        self.assertEqual(http_lab.PORT, 8791)
        with patch.object(sys, "argv", ["hcc.py", "--inspect"]), \
             patch.object(peer_guard, "read_b2_with_peer",
                          side_effect=AssertionError("real read")), \
             patch.object(b3b1, "BoundedServer",
                          side_effect=AssertionError("server started")), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(http_lab.main(), 0)
        details = json.loads(out.getvalue())
        self.assertEqual(details["mode"], "INSPECT_ONLY_NO_NETWORK")
        self.assertEqual(details["peer_poll_interval_ms"], 50)
        self.assertEqual(details["deployment_gate"], "HOLD")
        self.assertFalse(details["autostart"])
        self.assertTrue(details["requires_two_explicit_flags"])

    def test_real_handler_synthetic_positive_response_is_sanitized(self):
        report = synthetic()
        report["SENSITIVE"] = "PRIVATE"
        child = argv("import sys;sys.stdout.write("+repr(json.dumps(report))+")")
        with ephemeral_handler() as server, \
             patch.object(supervisor, "_fixed_argv", return_value=child):
            status, hdr, raw = request(server.server_address[1])
        self.assertEqual(status, 200)
        data = json.loads(raw)
        self.assertEqual(data["sample_count"], 3)
        self.assertEqual(data["gaps"][0]["cause"], "NOT_DETERMINED")
        self.assertNotIn("PRIVATE", raw.decode())
        self.assertEqual(hdr["Cache-Control"], "no-store, max-age=0")
        self.assertLessEqual(len(raw), http_lab.MAX_RESPONSE_BYTES)

    def test_disconnect_of_actual_http_client_cancels_guarded_child_and_releases_lock(self):
        spawned, started = [], threading.Event()
        original = subprocess.Popen

        def capture(*args, **kwargs):
            proc = original(*args, **kwargs)
            spawned.append(proc)
            started.set()
            return proc

        with ephemeral_handler() as server:
            port = server.server_address[1]
            sock = socket.create_connection(("127.0.0.1", port), timeout=2)
            try:
                with patch.object(supervisor, "_fixed_argv",
                                  return_value=argv("import time;time.sleep(5)")), \
                     patch.object(peer_guard.subprocess, "Popen", side_effect=capture):
                    sock.sendall((f"GET {PATH} HTTP/1.1\r\n"
                                  f"Host: 127.0.0.1:{port}\r\n"
                                  "Connection: close\r\n\r\n").encode())
                    self.assertTrue(started.wait(timeout=2))
                    stamp = time.monotonic()
                    sock.close()
                    deadline = stamp + 1.8
                    # Wait until source lock is released, never infer success
                    # from a connection closing without checking the child.
                    while server.history_lock.locked() and time.monotonic() < deadline:
                        time.sleep(.02)
                    self.assertFalse(server.history_lock.locked())
                    self.assertLess(time.monotonic()-stamp, 1.8)
                    self.assertEqual(len(spawned), 1)
                    self.assertIsNotNone(spawned[0].poll())
            finally:
                sock.close()

    def test_close_before_valid_read_does_not_start_child(self):
        with ephemeral_handler() as server:
            port = server.server_address[1]
            sock = socket.create_connection(("127.0.0.1", port), timeout=2)
            with patch.object(supervisor, "_fixed_argv",
                              side_effect=AssertionError("real source argv")) as fixed, \
                 patch.object(peer_guard.subprocess, "Popen",
                              side_effect=AssertionError("source spawn")) as spawned:
                try:
                    sock.sendall((f"GET {PATH} HTTP/1.1\r\n"
                                  f"Host: 127.0.0.1:{port}\r\n\r\n").encode())
                    sock.close()
                    # Race intentionally not asserted as deterministic:
                    # check this contract with an already disconnected socket
                    # in B3B2D tests instead, only verify no repeated calls.
                    time.sleep(.1)
                finally:
                    sock.close()
            self.assertLessEqual(fixed.call_count, 1)
            self.assertEqual(spawned.call_count, 0)

    def test_bad_headers_and_queries_never_invoke_cancel_guard(self):
        with ephemeral_handler() as server, \
             patch.object(peer_guard, "read_b2_with_peer",
                          side_effect=AssertionError("unexpected source")) as called:
            port = server.server_address[1]
            for path in ("/api/dns-guard-history?window=1h&window=7d",
                         "/api/dns-guard-history?window=%31h",
                         "/api/dns-guard-history?window=24h&metric=private",
                         "/api/summary"):
                self.assertEqual(request(port, path)[0], 403)
            self.assertEqual(request(port, method="POST")[0], 405)
            for headers in ({"Host": "bad.example"},
                            {"Origin": "https://evil.example"},
                            {"Sec-Fetch-Site": "cross-site"}):
                self.assertEqual(request(port, headers=headers)[0], 403)
            called.assert_not_called()

    def test_timeout_and_oversize_are_unknown_and_release_lock(self):
        with ephemeral_handler() as server:
            port = server.server_address[1]
            with patch.object(supervisor, "_fixed_argv",
                              return_value=argv("import time;time.sleep(4)")), \
                 patch.object(peer_guard, "MAX_CHILD_SECONDS", .15):
                status, _, raw = request(port)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(raw)["status"], "UNKNOWN")
            self.assertFalse(server.history_lock.locked())
            with patch.object(supervisor, "_fixed_argv",
                              return_value=argv("import sys;sys.stdout.write('X'*70000)")):
                status, _, raw = request(port)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(raw)["status"], "UNKNOWN")
            self.assertFalse(server.history_lock.locked())

    def test_disconnect_or_failure_does_not_retain_last_success(self):
        payload = json.dumps(synthetic())
        with ephemeral_handler() as server:
            port = server.server_address[1]
            with patch.object(supervisor, "_fixed_argv",
                              return_value=argv("import sys;sys.stdout.write(" +
                                                repr(payload) + ")")):
                first = json.loads(request(port)[2])
            with patch.object(supervisor, "_fixed_argv",
                              return_value=argv("import sys;sys.exit(12)")):
                second = json.loads(request(port)[2])
            self.assertEqual(first["sample_count"], 3)
            self.assertEqual(second["status"], "UNKNOWN")
            self.assertIsNone(second["sample_count"])
            self.assertEqual(second["segments"], [])

    def test_inflight_second_read_is_503_invalid_unrelated_route_is_403(self):
        started, release = threading.Event(), threading.Event()
        results = []

        def slow(window, peer):
            started.set()
            release.wait(timeout=2)
            return supervisor.unknown()

        with ephemeral_handler() as server, \
             patch.object(peer_guard, "read_b2_with_peer", side_effect=slow):
            port = server.server_address[1]
            t = threading.Thread(target=lambda: results.append(request(port)), daemon=True)
            try:
                t.start()
                self.assertTrue(started.wait(timeout=2))
                self.assertEqual(request(port)[0], 503)
                self.assertEqual(request(port, "/bad")[0], 403)
            finally:
                release.set()
                t.join(timeout=3)
            self.assertFalse(t.is_alive())
            self.assertEqual(len(results), 1)
            self.assertEqual(json.loads(results[0][2])["status"], "UNKNOWN")
            self.assertFalse(server.history_lock.locked())


if __name__ == "__main__":
    unittest.main()
