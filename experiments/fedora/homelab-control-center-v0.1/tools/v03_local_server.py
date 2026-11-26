#!/usr/bin/env python3
"""Opt-in V0.3 localhost-only DNS Guard + VictoriaMetrics read-only lab.

A SEPARATE manual alternative to V0.2, never an installed daemon. Shares
the existing 127.0.0.1:8788 listener, so only one HCC version can be running.
No ASUS calls, root privileges, configuration writes, secrets or raw labels.
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import HTTPServer
from pathlib import Path

import v02_local_server as v02
import v03_dns_guard_probe as dns

EXTRA_STATIC = {
    "/": ("index-v03.html", "text/html; charset=utf-8"),
    "/dns-guard-live.mjs": ("dns-guard-live.mjs", "text/javascript; charset=utf-8"),
    "/dns-guard-model.mjs": ("dns-guard-model.mjs", "text/javascript; charset=utf-8"),
}
MAX_OUTPUT = 2048


class RequestHandler(v02.RequestHandler):
    server_version = "HCC-V0.3-lab"

    def do_GET(self):
        # Apply V0.2's strict Host identity before serving *any* V0.3 content.
        if self.headers.get("Host") != f"{v02.BIND}:{v02.PORT}":
            self.send_headers(403, "text/plain", 0)
            return

        if self.path == "/api/dns-guard":
            # Mirror the V0.2 API cross-site gate; NEVER rewrite Origin or Fetch-Site.
            site = self.headers.get("Sec-Fetch-Site")
            origin = self.headers.get("Origin")
            if (site not in (None, "none", "same-origin")
                    or origin not in (None, f"http://{v02.BIND}:{v02.PORT}")):
                self.send_headers(403, "text/plain", 0)
                return
            raw = json.dumps(dns.collect(), ensure_ascii=True, separators=(",", ":")).encode("ascii")
            if len(raw) > MAX_OUTPUT:
                self.send_headers(503, "text/plain", 0)
                return
            self.send_headers(200, "application/json; charset=utf-8", len(raw))
            self.wfile.write(raw)
            return

        if self.path in EXTRA_STATIC:
            rel, mime = EXTRA_STATIC[self.path]
            raw = (v02.HERE / rel).read_bytes()  # explicit allowed assets, no request paths
            self.send_headers(200, mime, len(raw))
            self.wfile.write(raw)
            return

        # Existing V0.2 /api/summary, static allowlist and 405 write denial.
        super().do_GET()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve-readonly-v03", action="store_true",
                        help="foreground, non-root, loopback-only opt-in")
    args = parser.parse_args()
    if not args.serve_readonly_v03:
        parser.error("explicit --serve-readonly-v03 required")
    if os.geteuid() == 0:
        parser.error("root execution refused")
    print("HCC_V03=FEDORA_LOCAL_MANUAL_READ_ONLY", flush=True)
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
