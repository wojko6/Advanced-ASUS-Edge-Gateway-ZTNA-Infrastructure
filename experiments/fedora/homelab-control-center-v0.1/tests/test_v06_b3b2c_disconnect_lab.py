"""B3B2C synthetic-only HTTP client-disconnect cancellation tests.

No actual VictoriaMetrics source, production listener, or router contact.
"""
from __future__ import annotations

import contextlib
import http.client
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
import queue
import socket
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import v06_b3b2c_disconnect_lab as lab


class DisconnectLabTests(unittest.TestCase):
    def test_inspect_is_no_network_no_worker_no_listener(self):
        with patch.object(sys, "argv", ["script.py", "--inspect"]), \
             patch.object(lab, "_spawn_synthetic", side_effect=AssertionError("spawn")), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(lab.main(), 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "INSPECT_ONLY_NO_NETWORK")
        self.assertEqual(result["port_for_tests"], "EPHEMERAL")
        self.assertFalse(result["http_server_cli"])
        self.assertFalse(result["source_connected"])
        self.assertTrue(result["mock_only"])
        self.assertEqual(result["deployment_gate"], "HOLD")

    def test_open_peer_remains_live_and_close_is_detected(self):
        left, right = socket.socketpair()
        try:
            self.assertFalse(lab.disconnected(left))
            right.sendall(b"GET /synthetic HTTP/1.1\r\n")
            self.assertFalse(lab.disconnected(left))  # no socket consumption
            self.assertEqual(left.recv(256), b"GET /synthetic HTTP/1.1\r\n")
            right.close()
            self.assertTrue(lab.disconnected(left))
        finally:
            left.close()
            right.close()

    def test_normal_mock_child_finishes_with_open_peer(self):
        left, right = socket.socketpair()
        try:
            with patch.object(lab, "MAX_MOCK_LIFETIME_SECONDS", 2.0):
                self.assertEqual(lab.run_synthetic_with_peer(left, 60), "MOCK_COMPLETED")
        finally:
            left.close()
            right.close()

    def test_disconnect_kills_and_reaps_inflight_mock_worker(self):
        left, right = socket.socketpair()
        started = threading.Event()
        spawned = []
        outcome = []
        real_spawn = lab._spawn_synthetic

        def capture(duration):
            proc = real_spawn(duration)
            spawned.append(proc)
            started.set()
            return proc

        try:
            with patch.object(lab, "_spawn_synthetic", side_effect=capture):
                thread = threading.Thread(target=lambda:
                    outcome.append(lab.run_synthetic_with_peer(left, 4000)), daemon=True)
                thread.start()
                self.assertTrue(started.wait(timeout=2))
                began = time.monotonic()
                right.close()
                thread.join(timeout=2)
                elapsed = time.monotonic() - began
            self.assertFalse(thread.is_alive())
            self.assertEqual(outcome, ["CLIENT_DISCONNECTED"])
            self.assertLess(elapsed, 1.5)
            self.assertIsNotNone(spawned[0].poll())  # reaped, not orphaned
        finally:
            right.close()
            left.close()

    def test_total_mock_deadline_reaps_worker(self):
        left, right = socket.socketpair()
        captured = []
        original = lab._spawn_synthetic

        def capture(duration):
            p = original(duration)
            captured.append(p)
            return p

        try:
            with patch.object(lab, "MAX_MOCK_LIFETIME_SECONDS", 0.15), \
                 patch.object(lab, "_spawn_synthetic", side_effect=capture):
                result = lab.run_synthetic_with_peer(left, 4000)
            self.assertEqual(result, "LAB_DEADLINE")
            self.assertIsNotNone(captured[0].poll())
        finally:
            left.close()
            right.close()

    def test_unexpected_worker_failure_is_unknown(self):
        left, right = socket.socketpair()
        try:
            def failed(_duration):
                return subprocess.Popen([sys.executable, "-B", "-c", "import sys;sys.exit(7)"],
                                        stdin=subprocess.DEVNULL,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL,
                                        start_new_session=True)
            with patch.object(lab, "_spawn_synthetic", side_effect=failed):
                self.assertEqual(lab.run_synthetic_with_peer(left, 200),
                                 "MOCK_WORKER_FAILED")
        finally:
            left.close()
            right.close()

    def test_invalid_duration_does_not_start_worker(self):
        left, right = socket.socketpair()
        try:
            for duration in (-1, 0, 6000, True, "3000"):
                self.assertEqual(lab.run_synthetic_with_peer(left, duration),
                                 "MOCK_SETUP_ERROR")
        finally:
            left.close()
            right.close()

    def test_closed_peer_does_not_spawn_worker(self):
        left, right = socket.socketpair()
        right.close()
        try:
            with patch.object(lab, "_spawn_synthetic",
                              side_effect=AssertionError("should not spawn")) as spawn:
                self.assertEqual(lab.run_synthetic_with_peer(left, 3000),
                                 "CLIENT_DISCONNECTED")
                spawn.assert_not_called()
        finally:
            left.close()

    def test_ephemeral_http_invalid_path_is_not_a_worker_trigger(self):
        with _ephemeral_server() as (server, _):
            port = server.server_address[1]
            with patch.object(lab, "_spawn_synthetic") as spawn:
                status, _, body = _request(port, "/api/dns-guard-history?window=24h")
                self.assertEqual((status, body), (403, b""))
                self.assertEqual(_request(port, lab.ROUTE, method="POST")[0], 405)
                self.assertEqual(_request(port, lab.ROUTE, headers={
                    "Origin": "https://untrusted.example"})[0], 403)
                spawn.assert_not_called()

    def test_ephemeral_http_returns_only_unknown_on_normal_completion(self):
        with _ephemeral_server(sleep_ms=70) as (server, results):
            status, headers, body = _request(server.server_address[1], lab.ROUTE)
            self.assertEqual(status, 200)
            self.assertEqual(headers["Cache-Control"], "no-store")
            data = json.loads(body)
            self.assertEqual(data["status"], "UNKNOWN")
            self.assertEqual(data["reason_code"], "MOCK_COMPLETED")
            self.assertEqual(data["deployment_gate"], "HOLD")
            self.assertEqual(results.get(timeout=1), "MOCK_COMPLETED")
            self.assertNotIn("sample_count", data)

    def test_real_http_disconnection_cancels_worker_without_reply(self):
        with _ephemeral_server(sleep_ms=4000) as (server, results):
            port = server.server_address[1]
            sock = socket.create_connection(("127.0.0.1", port), timeout=2)
            spawned = []
            begin_event = threading.Event()
            original = lab._spawn_synthetic

            def capture(duration):
                proc = original(duration)
                spawned.append(proc)
                begin_event.set()
                return proc

            try:
                with patch.object(lab, "_spawn_synthetic", side_effect=capture):
                    sock.sendall((
                        f"GET {lab.ROUTE} HTTP/1.1\r\n"
                        f"Host: 127.0.0.1:{port}\r\n"
                        "Connection: close\r\n\r\n").encode())
                    self.assertTrue(begin_event.wait(timeout=2))
                    mark = time.monotonic()
                    sock.close()
                    self.assertEqual(results.get(timeout=2), "CLIENT_DISCONNECTED")
                    self.assertLess(time.monotonic()-mark, 1.5)
                    self.assertIsNotNone(spawned[0].poll())
            finally:
                sock.close()

    def test_bounded_source_isolation(self):
        source = Path(lab.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import v06_history_source", source)
        self.assertNotIn("read_b2_supervised", source)
        self.assertNotIn("127.0.0.1:8428", source)
        self.assertNotIn("serve_forever(", source)
        self.assertEqual(lab.BIND, "127.0.0.1")
        self.assertEqual(lab.MAX_MOCK_SLEEP_MS, 5000)


@contextlib.contextmanager
def _ephemeral_server(sleep_ms=150):
    # Only tests start an ephemeral loopback HTTP listener. No source.
    server = ThreadingHTTPServer(("127.0.0.1", 0), lab.SyntheticCancelHandler)
    server.daemon_threads = True
    server.mock_sleep_ms = sleep_ms
    outcomes = queue.Queue()
    server.on_mock_result = outcomes.put
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, outcomes
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request(port, path, method="GET", headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    hdr = {"Host": f"127.0.0.1:{port}"}
    hdr.update(headers or {})
    try:
        conn.request(method, path, headers=hdr)
        result = conn.getresponse()
        return result.status, dict(result.getheaders()), result.read()
    finally:
        conn.close()


if __name__ == "__main__":
    unittest.main()
