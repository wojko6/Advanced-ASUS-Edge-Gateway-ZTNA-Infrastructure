#!/usr/bin/env python3
"""V0.5 alternative manual localhost server: three V0.4 LIVE tiles + archive.

No autostart, systemd, Caddy changes, router SSH, or notification sender.
Shares 127.0.0.1:8788 with V0.2/V0.3/V0.4, never runs alongside them.
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import ThreadingHTTPServer
from threading import BoundedSemaphore, Lock

import v02_local_server as v02
import v04_local_server as v04
import v05_history_archive as archive

STATIC = {
    "/": ("index-v05.html", "text/html; charset=utf-8"),
    "/dns-history-archive.mjs": ("dns-history-archive.mjs", "text/javascript; charset=utf-8"),
    "/dns-history-archive-model.mjs": ("dns-history-archive-model.mjs", "text/javascript; charset=utf-8"),
    "/dns-history-archive.css": ("dns-history-archive.css", "text/css; charset=utf-8"),
}
MAX_HISTORY_OUTPUT = 8192
MAX_CONCURRENT_HTTP_REQUESTS = 16
_ARCHIVE_IN_FLIGHT = Lock()  # manual history read: at most one VM seven-series batch


class RequestHandler(v04.RequestHandler):
    server_version = "HCC-V0.5-archive-lab"

    def do_GET(self):
        if self.headers.get("Host") != f"{v02.BIND}:{v02.PORT}":
            self.send_headers(403, "text/plain", 0)
            return

        if self.path == "/api/dns-guard-history-archive":
            site = self.headers.get("Sec-Fetch-Site")
            origin = self.headers.get("Origin")
            if site not in (None, "none", "same-origin") or origin not in (
                    None, f"http://{v02.BIND}:{v02.PORT}"):
                self.send_headers(403, "text/plain", 0)
                return
            # A slow historical read must not block unrelated LIVE/static GETs.
            # Never fan out concurrent seven-series VM batches.
            if not _ARCHIVE_IN_FLIGHT.acquire(blocking=False):
                self.send_headers(503, "text/plain", 0)
                return
            try:
                payload = archive.collect()
            finally:
                _ARCHIVE_IN_FLIGHT.release()
            raw = json.dumps(payload, ensure_ascii=True,
                             separators=(",", ":")).encode("ascii")
            if len(raw) > MAX_HISTORY_OUTPUT:
                self.send_headers(503, "text/plain", 0)
                return
            self.send_headers(200, "application/json; charset=utf-8", len(raw))
            self.wfile.write(raw)
            return

        if self.path in STATIC:
            filename, mime = STATIC[self.path]
            raw = (v02.HERE / filename).read_bytes()
            self.send_headers(200, mime, len(raw))
            self.wfile.write(raw)
            return

        super().do_GET()


class BoundedLocalHTTPServer(ThreadingHTTPServer):
    """Manual localhost-only lab with bounded parallel request handlers.

    A slow fixed-history read must not block unrelated source tiles or assets.
    Limit local HTTP concurrency; do not spawn unbounded threads on load.
    """

    daemon_threads = True
    block_on_close = False

    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self._slots = BoundedSemaphore(MAX_CONCURRENT_HTTP_REQUESTS)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            # An overloaded listener reveals no source data or request details.
            try:
                request.sendall(
                    b"HTTP/1.0 503 Service Unavailable\r\n"
                    b"Content-Length: 0\r\n"
                    b"Cache-Control: no-store\r\n"
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
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve-readonly-v05", action="store_true",
                        help="explicit non-root foreground loopback-only lab")
    args = parser.parse_args()
    if not args.serve_readonly_v05:
        parser.error("explicit --serve-readonly-v05 required")
    if os.geteuid() == 0:
        parser.error("root execution refused")
    print("HCC_V05=FEDORA_MANUAL_LOCAL_ONLY", flush=True)
    print("THREE_LIVE_TILES=V04_UNCHANGED ARCHIVE=FIXED_2026_10_27_MANUAL_ONLY", flush=True)
    print("VM_ONLY=127.0.0.1:8428 ROUTER_CONTACT=NO NOTIFICATIONS=NO", flush=True)
    print("CONFIG_WRITES=NO AUTOSTART=NO DEPLOYMENT_GATE=HOLD", flush=True)
    print(f"LOCAL_UI=http://{v02.BIND}:{v02.PORT}/", flush=True)
    print("Ctrl+C to stop", flush=True)
    server = BoundedLocalHTTPServer((v02.BIND, v02.PORT), RequestHandler)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
