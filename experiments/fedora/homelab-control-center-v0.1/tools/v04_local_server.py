#!/usr/bin/env python3
"""Opt-in V0.4 Fedora localhost-only alternative to the manual V0.3 server.

No service install, no router/SSH/direct Pi-hole connection, config mutation,
scheduled scrape or externally bound listener. Shares port 8788 with V0.2/V0.3
and therefore cannot run at the same time.
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import HTTPServer

import v02_local_server as v02
import v03_local_server as v03
import v04_router_dns_probe as dnsprobe

EXTRA_STATIC = {
    "/": ("index-v04.html", "text/html; charset=utf-8"),
    "/router-dns-model.mjs": ("router-dns-model.mjs", "text/javascript; charset=utf-8"),
    "/router-dns-live.mjs": ("router-dns-live.mjs", "text/javascript; charset=utf-8"),
}
MAX_OUTPUT = 2048


class RequestHandler(v03.RequestHandler):
    server_version = "HCC-V0.4-lab"

    def do_GET(self):
        # Must validate identity before source adapter access or serving assets.
        if self.headers.get("Host") != f"{v02.BIND}:{v02.PORT}":
            self.send_headers(403, "text/plain", 0)
            return

        if self.path == "/api/router-dns":
            site = self.headers.get("Sec-Fetch-Site")
            origin = self.headers.get("Origin")
            if (site not in (None, "none", "same-origin")
                    or origin not in (None, f"http://{v02.BIND}:{v02.PORT}")):
                self.send_headers(403, "text/plain", 0)
                return
            raw = json.dumps(dnsprobe.collect(), ensure_ascii=True, separators=(",", ":")).encode("ascii")
            if len(raw) > MAX_OUTPUT:
                self.send_headers(503, "text/plain", 0)
                return
            self.send_headers(200, "application/json; charset=utf-8", len(raw))
            self.wfile.write(raw)
            return

        if self.path in EXTRA_STATIC:
            rel, mime = EXTRA_STATIC[self.path]
            raw = (v02.HERE / rel).read_bytes()  # static path allowlist, no request-derived files
            self.send_headers(200, mime, len(raw))
            self.wfile.write(raw)
            return

        # Preserve existing V0.3 DNS Guard/V0.2 summary and denial rules.
        super().do_GET()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve-readonly-v04", action="store_true",
                        help="manual foreground loopback-only alternative")
    args = parser.parse_args()
    if not args.serve_readonly_v04:
        parser.error("explicit --serve-readonly-v04 required")
    if os.geteuid() == 0:
        parser.error("root execution refused")
    print("HCC_V04=FEDORA_LOCAL_MANUAL_READ_ONLY", flush=True)
    print("VM_ONLY=127.0.0.1:8428 ROUTER_CONTACT=NO CONFIG_WRITES=NO", flush=True)
    print(f"LOCAL_UI=http://{v02.BIND}:{v02.PORT}/", flush=True)
    print("TLS_ALIAS=EXISTING_CADDY_LOCAL_ONLY NOT_MODIFIED", flush=True)
    print("BACKEND_AUTOSTART=NO DEPLOYMENT_GATE=HOLD", flush=True)
    print("Ctrl+C to stop", flush=True)
    server = HTTPServer((v02.BIND, v02.PORT), RequestHandler)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
