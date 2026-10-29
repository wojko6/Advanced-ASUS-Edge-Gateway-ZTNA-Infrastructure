#!/usr/bin/env python3
"""B3B2B: separately approved, manual-only, loopback source HTTP laboratory.

Import and --inspect do not open sockets or contact VictoriaMetrics. The two
explicit CLI flags are required for the optional real-source lab listener.
All tests patch the source read and contact neither VM nor the ASUS gateway.
This is NOT a deployed HCC service, public API, or B3C browser UI.
"""
from __future__ import annotations

import argparse
import json
import os

import v06_b3b_mock_http as mock
import v06_b3b2_source_supervisor as supervised

BIND = mock.BIND
PORT = 8791  # V0.5 8788 and B3B1 8790 must remain untouched.
MAX_RESPONSE_BYTES = 65536
MAX_WRITE_OPERATION_SECONDS = 2.0  # socket operation; NOT a total HTTP deadline
SCHEMA = "hcc-dns-guard-history-http/0.6-b3b2b"


def sanitize_result(raw, window):
    """Do not trust a worker result, even if it came from a local module."""
    missing = supervised.unknown()
    if type(window) is not str or window not in mock.WINDOWS:
        return missing
    if type(raw) is dict and raw == missing:
        return missing
    try:
        if type(raw) is not dict:
            return missing
        wire = json.dumps(raw, separators=(",", ":"), sort_keys=True,
                          ensure_ascii=True, allow_nan=False).encode("ascii")
        if len(wire) > MAX_RESPONSE_BYTES:
            return missing
        return supervised._project(wire, window)
    except (ValueError, TypeError, UnicodeError, OverflowError):
        return missing


class HistoryHandler(mock.RequestHandler):
    server_version = "HCC-B3B2B-local-source-lab"

    def do_GET(self):
        try:
            window = mock.validate_request(
                self.path, self.headers, self.server.server_address[1])
        except ValueError:
            self._empty(403)
            return
        if not self.server.history_lock.acquire(blocking=False):
            self._empty(503)
            return
        try:
            # Compute the whole response BEFORE any status/header bytes are sent.
            # Worker failure cannot cause a second HTTP response on one socket.
            try:
                result = supervised.read_b2_supervised(window)
                doc = sanitize_result(result, window)
                body = json.dumps(doc, separators=(",", ":"), sort_keys=True,
                                  ensure_ascii=True, allow_nan=False).encode("ascii")
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ValueError("bounded response exceeded")
            except Exception:
                # Never leak raw child data, errors or a previous success.
                body = json.dumps(supervised.unknown(), separators=(",", ":"),
                                  sort_keys=True).encode("ascii")
            try:
                # Operation timeout guards blocked writes, but does not
                # interrupt the already-running source worker on disconnect.
                self.connection.settimeout(MAX_WRITE_OPERATION_SECONDS)
                self._headers(200, "application/json; charset=utf-8", len(body))
                self.wfile.write(body)
            except OSError:
                # A client disconnect / broken pipe does not retry headers
                # or trigger another source read. Lock is always released.
                pass
        finally:
            self.server.history_lock.release()

    # HEAD/POST/PUT/DELETE are denied by the unchanged B3B1 handler.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inspect", action="store_true")
    group.add_argument("--serve-manual-local-history", action="store_true")
    parser.add_argument("--ack-local-vm-read", action="store_true",
                        help="second explicit opt-in for manually initiated localhost VictoriaMetrics reads")
    args = parser.parse_args()
    if args.inspect:
        if args.ack_local_vm_read:
            parser.error("acknowledgement only allowed for explicit manual server")
        print(json.dumps({
            "mode": "INSPECT_ONLY_NO_NETWORK",
            "bind": BIND, "port": PORT, "windows": mock.WINDOWS,
            "source": "FIXED_B2_VIA_SUPERVISOR_NOT_INVOKED",
            "max_response_bytes": MAX_RESPONSE_BYTES,
            "write_operation_timeout_seconds": MAX_WRITE_OPERATION_SECONDS,
            "max_child_seconds": supervised.MAX_CHILD_SECONDS,
            "max_child_stdout_bytes": supervised.MAX_STDOUT_BYTES,
            "max_handlers": mock.MAX_HANDLERS,
            "one_source_read_at_a_time": True,
            "requires_two_explicit_flags": True,
            "autostart": False, "production_deployment": False,
            "deployment_gate": "HOLD",
        }, sort_keys=True))
        return 0
    if not args.ack_local_vm_read:
        parser.error("--ack-local-vm-read required to start source-connected lab")
    if os.geteuid() == 0:
        parser.error("root execution refused")
    server = mock.BoundedServer((BIND, PORT), HistoryHandler)
    print("B3B2B=MANUAL_LOOPBACK_ONLY HOST=127.0.0.1", flush=True)
    print("SOURCE=FIXED_B2_VIA_B3B2A_NO_AUTO_REQUEST", flush=True)
    print("DEPLOYMENT_GATE=HOLD AUTOSTART=NO", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
