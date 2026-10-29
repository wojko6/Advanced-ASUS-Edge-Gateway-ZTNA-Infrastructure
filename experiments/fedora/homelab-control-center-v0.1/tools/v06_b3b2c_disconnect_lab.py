#!/usr/bin/env python3
"""HCC V0.6-B3B2C: isolated synthetic peer-disconnect cancellation laboratory.

NOT wired to the B2 reader or existing B3B2B HTTP endpoint. No CLI listener.
Tests alone create an ephemeral 127.0.0.1 HTTP server and synthetic child.
Import and --inspect perform NO networking or process spawning.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import time

ROUTE = "/__hcc_b3b2c_synthetic_cancel"
POLL_INTERVAL_SECONDS = 0.05
MAX_MOCK_LIFETIME_SECONDS = 6.0
MAX_MOCK_SLEEP_MS = 5000
BIND = "127.0.0.1"
ROOT = Path(__file__).resolve().parent


def disconnected(peer: socket.socket) -> bool:
    """Linux TCP RDHUP/HUP/error; never consume HTTP request or source bytes.

    A remote write-half-close is conservatively treated as a disconnect. This
    does not prove an HTTP end-to-end deadline or arbitrary client cancellation.
    """
    flags = (select.POLLHUP | select.POLLERR | select.POLLNVAL |
             getattr(select, "POLLRDHUP", 0))
    try:
        fd = peer.fileno()
        if fd < 0 or not hasattr(select, "POLLRDHUP"):
            return True  # No reliable platform detector: fail closed.
        poller = select.poll()
        poller.register(fd, flags)
        return any(event & flags for _, event in poller.poll(0))
    except (OSError, ValueError, TypeError):
        return True


def _spawn_synthetic(sleep_ms: int) -> subprocess.Popen:
    """Only fixed Python/synthetic arguments, no shell or real source reader."""
    if type(sleep_ms) is not int or not 1 <= sleep_ms <= MAX_MOCK_SLEEP_MS:
        raise ValueError("INVALID_SYNTHETIC_SLEEP")
    return subprocess.Popen(
        [sys.executable, "-B", str(Path(__file__).resolve()),
         "--internal-mock-worker", "--sleep-ms", str(sleep_ms)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, cwd=str(ROOT), start_new_session=True,
        close_fds=True,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
    )


def _kill_reap(proc: subprocess.Popen) -> None:
    """Always reap a cancelled worker and kill its isolated process group."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=1)
    except (OSError, subprocess.SubprocessError):
        pass


def run_synthetic_with_peer(peer: socket.socket, sleep_ms: int = 3000) -> str:
    """Synchronous, bounded synthetic worker; client loss cancels in-flight work.

    Returns only fixed reason tokens. There is no VM/ASUS source path in here.
    """
    proc = None
    reason = "MOCK_SETUP_ERROR"
    began = time.monotonic()
    try:
        # Fail closed before even spawning a child for an already-lost peer.
        if disconnected(peer):
            return "CLIENT_DISCONNECTED"
        proc = _spawn_synthetic(sleep_ms)
        deadline = began + MAX_MOCK_LIFETIME_SECONDS
        while True:
            if disconnected(peer):
                reason = "CLIENT_DISCONNECTED"
                break
            rc = proc.poll()
            if rc is not None:
                reason = "MOCK_COMPLETED" if rc == 0 else "MOCK_WORKER_FAILED"
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                reason = "LAB_DEADLINE"
                break
            time.sleep(min(POLL_INTERVAL_SECONDS, remaining))
        return reason
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        return "MOCK_SETUP_ERROR"
    finally:
        if proc is not None:
            # Kill the process GROUP when cancelling, even if the direct
            # process exited early; do not leave its descendants behind.
            if reason != "MOCK_COMPLETED":
                _kill_reap(proc)
            else:
                proc.wait(timeout=1)


class SyntheticCancelHandler(BaseHTTPRequestHandler):
    """Used ONLY with ephemeral loopback test servers; never started by CLI."""
    server_version = "HCC-B3B2C-synthetic-only"
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        return

    def _send(self, status: int, payload: bytes = b"") -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.end_headers()
            if payload:
                self.wfile.write(payload)
        except OSError:
            pass
        finally:
            self.close_connection = True

    def do_GET(self) -> None:
        if (self.path != ROUTE or
            self.headers.get_all("Host") !=
                [f"{BIND}:{self.server.server_address[1]}"] or
            self.headers.get_all("Origin") not in
                (None, [f"http://{BIND}:{self.server.server_address[1]}"]) or
            self.headers.get_all("Sec-Fetch-Site") not in
                (None, ["same-origin"], ["none"])):
            self._send(403)
            return
        reason = run_synthetic_with_peer(
            self.connection, getattr(self.server, "mock_sleep_ms", 3000))
        # Test observation only; never log sensitive request/peer data.
        callback = getattr(self.server, "on_mock_result", None)
        if callable(callback):
            callback(reason)
        if reason == "CLIENT_DISCONNECTED":
            self.close_connection = True
            return  # Peer is gone; no attempts to send response headers.
        # The mock lab NEVER returns successful production coverage.
        body = json.dumps({"status": "UNKNOWN", "reason_code": reason,
                           "deployment_gate": "HOLD"}, sort_keys=True).encode()
        self._send(200, body)

    def do_HEAD(self) -> None:
        self._send(405)

    def do_POST(self) -> None:
        self._send(405)

    def do_PUT(self) -> None:
        self._send(405)

    def do_DELETE(self) -> None:
        self._send(405)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect", action="store_true")
    mode.add_argument("--internal-mock-worker", action="store_true",
                      help=argparse.SUPPRESS)
    parser.add_argument("--sleep-ms", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.inspect:
        if args.sleep_ms is not None:
            parser.error("--inspect takes no child arguments")
        print(json.dumps({
            "mode": "INSPECT_ONLY_NO_NETWORK",
            "http_server_cli": False, "source_connected": False,
            "mock_only": True, "bind_for_tests": BIND,
            "port_for_tests": "EPHEMERAL",
            "poll_interval_ms": int(1000 * POLL_INTERVAL_SECONDS),
            "max_mock_lifetime_seconds": MAX_MOCK_LIFETIME_SECONDS,
            "deployment_gate": "HOLD",
        }, sort_keys=True))
        return 0
    if args.sleep_ms is None or not 1 <= args.sleep_ms <= MAX_MOCK_SLEEP_MS:
        parser.error("bounded synthetic sleep is required")
    time.sleep(args.sleep_ms / 1000)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
