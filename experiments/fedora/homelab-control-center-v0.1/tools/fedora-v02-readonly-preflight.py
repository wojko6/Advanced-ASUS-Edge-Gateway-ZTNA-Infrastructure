#!/usr/bin/env python3
"""Fedora-only V0.2 read-only preflight. No root, writes, or router contact.

Usage:
  python3 -B tools/fedora-v02-readonly-preflight.py --self-test
  python3 -B tools/fedora-v02-readonly-preflight.py --inspect
  python3 -B tools/fedora-v02-readonly-preflight.py --run

--run performs only three bounded HTTP GETs over IPv4 127.0.0.1:
  VictoriaMetrics /health and /api/v1/query?query=count(up)
  Loki /ready
No query labels, log lines, credentials, hostnames, addresses or metric values
other than the aggregated count of UP-series are printed.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import subprocess
import sys
from urllib.parse import quote

sys.dont_write_bytecode = True

SERVICES = {"victoriametrics": 8428, "loki": 3100}
MAX_BYTES = 16_384
TIMEOUT = 2
ALLOWED = {
    (8428, "/health"),
    (8428, "/api/v1/query?query=" + quote("count(up)", safe="")),
    (3100, "/ready"),
}


def classify_listeners(output: str, port: int) -> str:
    found = []
    for line in output.splitlines():
        bits = line.split()
        if len(bits) < 4 or bits[0] != "LISTEN":
            continue
        local = bits[3]
        host, sep, port_text = local.rpartition(":")
        if not sep or port_text != str(port):
            continue
        found.append(host)
    if not found:
        return "NOT_LISTENING"
    if all(host in ("127.0.0.1", "[::1]", "::1") for host in found):
        return "LOOPBACK_ONLY"
    return "NON_LOOPBACK_LISTENER"


def listeners() -> dict[str, str]:
    try:
        proc = subprocess.run(
            ["ss", "-H", "-lnt"], capture_output=True, text=True, timeout=3,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError("ss unavailable")
        return {
            name: classify_listeners(proc.stdout, port)
            for name, port in SERVICES.items()
        }
    except (OSError, subprocess.TimeoutExpired, RuntimeError):
        return {name: "UNKNOWN" for name in SERVICES}


def get_state(name: str) -> str:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name + ".service"],
            text=True, capture_output=True, check=False, timeout=3,
        )
        value = result.stdout.strip()
        return value if value in (
            "active", "inactive", "failed", "activating", "deactivating"
        ) else "UNKNOWN"
    except (OSError, subprocess.TimeoutExpired):
        return "UNKNOWN"


def local_get(port: int, path: str) -> tuple[int, bytes]:
    if (port, path) not in ALLOWED:
        raise ValueError("endpoint not allowlisted")
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT)
    try:
        conn.request("GET", path, headers={
            "Accept": "application/json, text/plain",
            "Connection": "close",
        })
        response = conn.getresponse()
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("response too large")
        return response.status, raw
    finally:
        conn.close()


def safe_http_check(port: int, path: str) -> tuple[str, bytes]:
    try:
        status, body = local_get(port, path)
        if status == 200:
            return "HTTP_200", body
        if status in (401, 403):
            return "ACCESS_DENIED", b""
        if 300 <= status < 400:
            return "REDIRECT_NOT_FOLLOWED", b""
        return "HTTP_" + str(status), b""
    except (OSError, ValueError, http.client.HTTPException, TimeoutError):
        return "UNAVAILABLE_OR_INVALID", b""


def parse_up_count(raw: bytes) -> str:
    """Return only aggregate target count; never source labels."""
    try:
        obj = json.loads(raw)
        if obj.get("status") != "success":
            return "UNKNOWN"
        res = obj.get("data", {}).get("result", [])
        if not isinstance(res, list) or len(res) != 1:
            return "UNKNOWN"
        value = res[0].get("value")
        if not isinstance(value, list) or len(value) != 2:
            return "UNKNOWN"
        number = float(value[1])
        if not number.is_integer() or number < 0 or number > 1_000_000:
            return "UNKNOWN"
        return str(int(number))
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
        return "UNKNOWN"


def inspect() -> dict[str, str]:
    state = listeners()
    print("LAB=HCC_V02_FEDORA_READ_ONLY")
    print("MODE=INSPECT")
    print("FEDORA_ONLY=YES ROOT_REQUIRED=NO ASUS_CONTACTED=NO")
    print("CONFIG_WRITES=NO PACKAGES=NO SYSTEMD_CHANGES=NO")
    for name in SERVICES:
        print(name.upper() + "_SYSTEMD=" + get_state(name))
        print(name.upper() + "_LISTEN=" + state[name])
    print("DEPLOYMENT_GATE=HOLD")
    return state


def run() -> int:
    if os.geteuid() == 0:
        print("RUN=HOLD_ROOT_NOT_ALLOWED")
        return 2
    state = inspect()
    if any(v == "NON_LOOPBACK_LISTENER" for v in state.values()):
        print("RUN=HOLD_UNEXPECTED_LISTENER_EXPOSURE")
        return 2
    print("MODE=RUN_READ_ONLY_LOOPBACK")
    print("LOCAL_GET_TARGETS=3 (127.0.0.1 ONLY)")
    vm_status, _ = safe_http_check(8428, "/health")
    loki_status, _ = safe_http_check(3100, "/ready")
    query_path = "/api/v1/query?query=" + quote("count(up)", safe="")
    count_status, count_body = safe_http_check(8428, query_path)
    print("VICTORIAMETRICS_HEALTH=" + vm_status)
    print("LOKI_READY=" + loki_status)
    print("VM_AGGREGATE_QUERY=" + count_status)
    count = parse_up_count(count_body) if count_status == "HTTP_200" else "UNKNOWN"
    print("VM_AGGREGATE_UP_SERIES_COUNT=" + count)
    print("NO_RAW_LABELS_OR_LOGS_PRINTED=YES")
    print("NO_MUTATING_ENDPOINTS=YES")
    print("DEPLOYMENT_GATE=HOLD")
    return 0 if vm_status == loki_status == count_status == "HTTP_200" and count != "UNKNOWN" else 1


def self_test() -> int:
    positive = 'LISTEN 0 1024 127.0.0.1:8428 0.0.0.0:*'
    negative = 'LISTEN 0 1024 0.0.0.0:8428 0.0.0.0:*'
    example = b'{"status":"success","data":{"resultType":"vector","result":[{"metric":{},"value":[1,"7"]}]}}'
    checks = [
        classify_listeners(positive, 8428) == "LOOPBACK_ONLY",
        classify_listeners(negative, 8428) == "NON_LOOPBACK_LISTENER",
        classify_listeners("", 8428) == "NOT_LISTENING",
        classify_listeners("LISTEN 0 5 [::1]:3100 [::]:*", 3100) == "LOOPBACK_ONLY",
        classify_listeners("LISTEN 0 5 [::]:3100 [::]:*", 3100) == "NON_LOOPBACK_LISTENER",
        parse_up_count(example) == "7",
        parse_up_count(b'{"status":"success","data":{"result":[]}}') == "UNKNOWN",
        parse_up_count(b'{"status":"error"}') == "UNKNOWN",
        parse_up_count(b'not-json') == "UNKNOWN",
        all(port in SERVICES.values() and path.startswith("/")
            for port, path in ALLOWED),
    ]
    for n, ok in enumerate(checks, 1):
        print("SELFTEST_%02d=%s" % (n, "PASS" if ok else "FAIL"))
    print("SELFTEST_RESULT=%d/%d" % (sum(checks), len(checks)))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--inspect", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        sys.exit(self_test())
    if args.inspect:
        if os.geteuid() == 0:
            sys.exit("Root execution is not permitted")
        inspect()
    elif args.run:
        sys.exit(run())
