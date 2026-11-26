"""B3B2D: HTTP + peer-aware subprocess integration, synthetic-only.

Tests run ephemeral 127.0.0.1 listeners. Every source read uses patched
fixed argv pointing ONLY to harmless synthetic Python commands. No actual
B2/VM subprocess runs. No ASUS, router, HCC service or production changes.
"""
from __future__ import annotations

import contextlib
import http.client
import json
import queue
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import v06_b3b_mock_http as b3b1
import v06_b3b2_source_supervisor as b3b2a
import v06_b3b2b_manual_http as b3b2b
import v06_b3b2c_disconnect_lab as b3b2c
import v06_b3b2d_cancel_guard as guard
import v06_b3b2d_cancel_http_proof as proof
import v06_coverage_model as coverage
import v06_history_source as source

END = 1793260800000
PATH = "/api/dns-guard-history?window=1h"


def fixture():
    stamps = [END - 120000, END - 60000, END]
    series = {}
    for name in coverage.SUFFIXES:
        if name in ("mode_local", "state_valid"):
            vals = [1, 1, 1]
        elif name == "collection_timestamp_seconds":
            vals = [t // 1000 for t in stamps]
        else:
            vals = [0, 0, 0]
        series[name] = list(zip(stamps, vals))
    record = coverage.analyze(series, "1h", END)
    assert record["status"] == "COVERAGE_OBSERVED_WITH_UNCERTAINTY"
    record["source_adapter"] = source.SCHEMA
    return record


def fake_command(script):
    return [sys.executable, "-B", "-c", script]


@contextlib.contextmanager
def server_lab():
    server = b3b1.BoundedServer(("127.0.0.1", 0), proof.CancelProofHandler)
    server.daemon_threads = True
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
    opts = {"Host": f"127.0.0.1:{port}"}
    opts.update(headers or {})
    try:
        conn.request(method, path, headers=opts)
        resp = conn.getresponse()
        return resp.status, dict(resp.getheaders()), resp.read()
    finally:
        conn.close()


class CancelProofTests(unittest.TestCase):
    def test_no_listener_or_source_on_module_import_or_inspect(self):
        source_text = Path(proof.__file__).read_text()
        self.assertNotIn("serve_forever(", source_text)
        self.assertNotIn("read_b2_supervised(", source_text)
        self.assertFalse(hasattr(proof, "main"))
        data = guard.inspect_contract()
        self.assertEqual(data["mode"], "INSPECT_ONLY_NO_NETWORK")
        self.assertFalse(data["autostart"])
        self.assertFalse(data["http_endpoint"])
        self.assertEqual(data["deployment_gate"], "HOLD")
        self.assertEqual(data["max_stdout_bytes"], 65536)

    def test_supervised_synthetic_stdout_with_open_peer_is_validated(self):
        left, right = socket.socketpair()
        payload = json.dumps(fixture())
        try:
            with patch.object(b3b2a, "_fixed_argv", return_value=fake_command(
                    "import sys;sys.stdout.write(" + repr(payload) + ")")):
                result = guard.read_b2_with_peer("1h", left)
            self.assertEqual(result["sample_count"], 3)
            self.assertEqual(result["window"], "1h")
            self.assertEqual(result["status"], "COVERAGE_OBSERVED_WITH_UNCERTAINTY")
        finally:
            left.close()
            right.close()

    def test_bad_window_and_preclosed_peer_do_not_spawn_any_process(self):
        left, right = socket.socketpair()
        try:
            with patch.object(guard.subprocess, "Popen",
                              side_effect=AssertionError("process started")) as p:
                self.assertEqual(guard.read_b2_with_peer("30d", left)["status"], "UNKNOWN")
                right.close()
                self.assertEqual(guard.read_b2_with_peer("1h", left)["status"], "UNKNOWN")
                p.assert_not_called()
        finally:
            left.close()
            right.close()

    def test_child_timeout_is_neutral_and_kills_worker(self):
        left, right = socket.socketpair()
        spawned = []
        original = subprocess.Popen
        def capture(*args, **kwargs):
            child = original(*args, **kwargs)
            spawned.append(child)
            return child
        try:
            with patch.object(b3b2a, "_fixed_argv",
                              return_value=fake_command("import time;time.sleep(5)")), \
                 patch.object(guard, "MAX_CHILD_SECONDS", .2), \
                 patch.object(guard.subprocess, "Popen", side_effect=capture):
                start = time.monotonic()
                result = guard.read_b2_with_peer("1h", left)
                elapsed = time.monotonic() - start
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertLess(elapsed, 2.0)
            self.assertEqual(len(spawned), 1)
            self.assertIsNotNone(spawned[0].poll())
        finally:
            left.close()
            right.close()

    def test_oversize_or_malformed_child_output_returns_unknown(self):
        left, right = socket.socketpair()
        try:
            for code in ("import sys;sys.stdout.write('x'*70000)",
                         "print('not JSON')",
                         "import sys;sys.exit(9)"):
                with self.subTest(code=code), patch.object(
                        b3b2a, "_fixed_argv", return_value=fake_command(code)):
                    answer = guard.read_b2_with_peer("1h", left)
                self.assertEqual(answer["status"], "UNKNOWN")
                self.assertIsNone(answer["sample_count"])
        finally:
            left.close()
            right.close()

    def test_manual_http_get_returns_sanitized_synthetic_data_only(self):
        report = fixture()
        report["PRIVATE_LABEL"] = "DO_NOT_EXPOSE"
        payload = json.dumps(report)
        with server_lab() as srv, patch.object(
            b3b2a, "_fixed_argv", return_value=fake_command(
                "import sys;sys.stdout.write(" + repr(payload) + ")")):
            status, headers, body = request(srv.server_address[1])
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store, max-age=0")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        data = json.loads(body)
        self.assertEqual(data["sample_count"], 3)
        self.assertEqual(data["gaps"][0]["cause"], "NOT_DETERMINED")
        self.assertNotIn("DO_NOT_EXPOSE", body.decode())
        self.assertLessEqual(len(body), b3b2b.MAX_RESPONSE_BYTES)

    def test_rejected_query_method_origin_never_start_source(self):
        with server_lab() as srv, patch.object(
                guard, "read_b2_with_peer",
                side_effect=AssertionError("unexpected source")) as read:
            port = srv.server_address[1]
            for path in ("/api/dns-guard-history?window=1h&x=1",
                         "/api/dns-guard-history?window=7d&window=1h",
                         "/api/summary"):
                self.assertEqual(request(port, path)[0], 403)
            self.assertEqual(request(port, method="POST")[0], 405)
            self.assertEqual(request(port, headers={"Origin": "https://evil.test"})[0], 403)
            self.assertEqual(request(port, headers={"Sec-Fetch-Site": "cross-site"})[0], 403)
            read.assert_not_called()

    def test_concurrent_second_get_503_and_invalid_route_403(self):
        started, release = threading.Event(), threading.Event()
        first = []
        def slow(window, peer):
            started.set()
            release.wait(timeout=2)
            return b3b2a.unknown()
        with server_lab() as srv:
            port = srv.server_address[1]
            with patch.object(guard, "read_b2_with_peer", side_effect=slow):
                thread = threading.Thread(target=lambda: first.append(request(port)), daemon=True)
                try:
                    thread.start()
                    self.assertTrue(started.wait(timeout=2))
                    self.assertEqual(request(port)[0], 503)
                    self.assertEqual(request(port, "/nope")[0], 403)
                finally:
                    release.set()
                    thread.join(timeout=3)
                self.assertFalse(thread.is_alive())
                self.assertEqual(first[0][0], 200)
                self.assertEqual(json.loads(first[0][2])["status"], "UNKNOWN")

    def test_actual_http_disconnect_cancels_child_and_releases_history_lock(self):
        # Actual client closes its socket while a synthetic 4s child is alive.
        started = threading.Event()
        spawned = []
        original = subprocess.Popen
        def capture(*args, **kwargs):
            child = original(*args, **kwargs)
            spawned.append(child)
            started.set()
            return child
        with server_lab() as srv:
            port = srv.server_address[1]
            client = socket.create_connection(("127.0.0.1", port), timeout=2)
            try:
                with patch.object(b3b2a, "_fixed_argv",
                                  return_value=fake_command("import time;time.sleep(4)")), \
                     patch.object(guard.subprocess, "Popen", side_effect=capture):
                    client.sendall((
                        f"GET {PATH} HTTP/1.1\r\n"
                        f"Host: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n").encode())
                    self.assertTrue(started.wait(timeout=2))
                    stamp = time.monotonic()
                    client.close()
                    deadline = stamp + 1.8
                    while srv.history_lock.locked() and time.monotonic() < deadline:
                        time.sleep(.02)
                    self.assertFalse(srv.history_lock.locked())
                    self.assertLess(time.monotonic()-stamp, 1.8)
                    self.assertEqual(len(spawned), 1)
                    self.assertIsNotNone(spawned[0].poll())
            finally:
                client.close()

    def test_no_stale_success_after_source_failure(self):
        payload = json.dumps(fixture())
        with server_lab() as srv:
            port = srv.server_address[1]
            with patch.object(b3b2a, "_fixed_argv", return_value=fake_command(
                    "import sys;sys.stdout.write(" + repr(payload) + ")")):
                ok = json.loads(request(port)[2])
            with patch.object(b3b2a, "_fixed_argv", return_value=fake_command(
                    "import sys;sys.exit(7)")):
                fail = json.loads(request(port)[2])
        self.assertEqual(ok["sample_count"], 3)
        self.assertEqual(fail["status"], "UNKNOWN")
        self.assertIsNone(fail["sample_count"])
        self.assertEqual(fail["segments"], [])


if __name__ == "__main__":
    unittest.main()
