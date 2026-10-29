#!/usr/bin/env python3
"""HCC B3B1: explicit Fedora-only MOCK HTTP boundary, no VictoriaMetrics reads.

Not an installed service or a connection from HCC to a live reader.
It returns sanitized UNKNOWN for every accepted request. B3B2 must independently
review real-source wiring, cancellation, deadline and browser constraints.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import BoundedSemaphore, Lock

BIND = "127.0.0.1"
PORT = 8790  # separate from V0.5's 8788; operator must verify availability
WINDOWS = ("1h", "6h", "24h", "7d")
ROUTE = re.compile(r"^/api/dns-guard-history\?window=(1h|6h|24h|7d)$")
SCHEMA = "hcc-dns-guard-b3b1-mock/0.6"
MAX_BODY = 4096
MAX_HANDLERS = 8
MOCK_WORKER_DEADLINE_S = 2.0  # one mock subprocess only, not a live-source SLO


def unknown(window=None):
    return {
        "schema_version": SCHEMA, "status": "UNKNOWN",
        "reason_code": "MOCK_ONLY_SOURCE_NOT_CONNECTED",
        "mode": "MOCK_ONLY", "window": window if window in WINDOWS else None,
        "sample_count": None, "segments": [], "gaps": [],
        "deployment_gate": "HOLD",
    }


def _one(headers, key):
    values = headers.get_all(key)
    return None if values is None else values


def validate_request(path, headers, port):
    """Require one literal fixed URL and unambiguous same-origin GET headers."""
    if type(path) is not str or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("INVALID_REQUEST")
    match = ROUTE.fullmatch(path)
    if match is None:
        raise ValueError("UNKNOWN_ROUTE_OR_QUERY")
    host = _one(headers, "Host")
    if host != [f"{BIND}:{port}"]:
        raise ValueError("INVALID_HOST")
    origin = _one(headers, "Origin")
    if origin not in (None, [f"http://{BIND}:{port}"]):
        raise ValueError("INVALID_ORIGIN")
    site = _one(headers, "Sec-Fetch-Site")
    if site not in (None, ["none"], ["same-origin"]):
        raise ValueError("INVALID_FETCH_SITE")
    if _one(headers, "Content-Length") is not None or _one(headers, "Transfer-Encoding") is not None:
        raise ValueError("REQUEST_BODY_NOT_ALLOWED")
    return match.group(1)


def run_mock_worker(window):
    """The only child command is our fixed MOCK UNKNOWN generator.

    subprocess.run timeout kills/reaps this controlled child if it stalls.
    No arbitrary command, shell, VM address or user-controlled script path.
    """
    if window not in WINDOWS:
        return unknown()
    cmd = (sys.executable, "-B", str(Path(__file__).resolve()),
           "--mock-worker", "--window", window)
    try:
        result = subprocess.run(
            cmd, stdin=subprocess.DEVNULL, capture_output=True, check=False,
            timeout=MOCK_WORKER_DEADLINE_S,
            cwd=str(Path(__file__).resolve().parent.parent),
            env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
        )
        if result.returncode != 0 or len(result.stdout) > MAX_BODY:
            return unknown(window)
        doc = json.loads(result.stdout)
        return doc if type(doc) is dict and doc == unknown(window) else unknown(window)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        return unknown(window)


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "HCC-B3B1-mock-lab"
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        # No request-path or client metadata in logs.
        return

    def _headers(self, status, mime, count):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(count))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

    def _empty(self, status):
        self._headers(status, "text/plain; charset=utf-8", 0)

    def do_GET(self):
        try:
            window = validate_request(self.path, self.headers, self.server.server_address[1])
        except ValueError:
            self._empty(403)
            return
        if not self.server.history_lock.acquire(blocking=False):
            self._empty(503)
            return
        try:
            # B3B1 is source-disconnected by construction.
            doc = run_mock_worker(window)
            if doc != unknown(window):
                doc = unknown(window)
            body = json.dumps(doc, separators=(",", ":"), sort_keys=True).encode("ascii")
            if len(body) > MAX_BODY:
                self._empty(503)
                return
            self._headers(200, "application/json; charset=utf-8", len(body))
            self.wfile.write(body)
        except (OSError, ValueError, TypeError):
            self._empty(503)
        finally:
            self.server.history_lock.release()

    def do_HEAD(self):
        self._empty(405)

    def do_POST(self):
        self._empty(405)

    def do_PUT(self):
        self._empty(405)

    def do_DELETE(self):
        self._empty(405)


class BoundedServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False

    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.history_lock = Lock()
        self.request_slots = BoundedSemaphore(MAX_HANDLERS)

    def process_request(self, request, client_address):
        if not self.request_slots.acquire(blocking=False):
            try:
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Content-Length: 0\r\nCache-Control: no-store\r\n"
                    b"Connection: close\r\n\r\n"
                )
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.request_slots.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inspect", action="store_true")
    group.add_argument("--serve-mock-b3b1", action="store_true")
    group.add_argument("--mock-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--window", choices=WINDOWS)
    args = parser.parse_args()
    if args.mock_worker:
        if args.window is None:
            parser.error("--window required for mock worker")
        print(json.dumps(unknown(args.window), separators=(",", ":"), sort_keys=True))
        return 0
    if args.window is not None:
        parser.error("--window is only for the internal mock worker")
    if args.inspect:
        print(json.dumps({
            "mode": "INSPECT_ONLY_NO_NETWORK", "schema": SCHEMA,
            "bind": BIND, "port": PORT, "windows": WINDOWS,
            "source": "DISCONNECTED_MOCK_UNKNOWN_ONLY",
            "worker_deadline_seconds": MOCK_WORKER_DEADLINE_S,
            "max_body_bytes": MAX_BODY, "max_handlers": MAX_HANDLERS,
            "deployment_gate": "HOLD",
        }, sort_keys=True))
        return 0
    if os.geteuid() == 0:
        parser.error("root execution refused")
    print("HCC_B3B1=EXPLICIT_MOCK_ONLY VM_CONTACT=NO ASUS_CONTACT=NO", flush=True)
    print(f"LOCAL_ONLY=http://{BIND}:{PORT}", flush=True)
    print("AUTOSTART=NO DEPLOYMENT_GATE=HOLD", flush=True)
    server = BoundedServer((BIND, PORT), RequestHandler)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
