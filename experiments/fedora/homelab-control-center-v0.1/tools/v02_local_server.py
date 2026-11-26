#!/usr/bin/env python3
"""Opt-in Fedora loopback-only V0.2 proof, not a production service.

GET /api/summary reads three fixed VictoriaMetrics aggregate instant queries.
All other supported GET paths are read-only static assets, no router/Loki contact.
No credential handling, shell execution, configuration edits or scheduled polling.
"""
from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import math
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import quote

HERE = Path(__file__).resolve().parent.parent
BIND = "127.0.0.1"
PORT = 8788
VM_PORT = 8428
MAX_BODY = 8192
TIMEOUT = 2
TTL_SECONDS = 120  # provisional; do not treat as universal SLO
STATIC = {
    "/": ("index-live.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.mjs": ("app.mjs", "text/javascript; charset=utf-8"),
    "/model.mjs": ("model.mjs", "text/javascript; charset=utf-8"),
    "/data.mjs": ("data.mjs", "text/javascript; charset=utf-8"),
    "/live.mjs": ("live.mjs", "text/javascript; charset=utf-8"),
    "/live-model.mjs": ("live-model.mjs", "text/javascript; charset=utf-8"),
}
QUERIES = (
    ("total", "count(up)"),
    ("healthy", "sum(up)"),
    ("age", "max(time() - timestamp(up))"),
)


def promql_scalar_from_json(raw: bytes, now_epoch: float) -> float:
    """Parse exactly one unlabeled PromQL instant vector; reject malformed/stale API reply."""
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("api document shape")
    if obj.get("status") != "success":
        raise ValueError("api status")
    data = obj.get("data")
    if not isinstance(data, dict) or data.get("resultType") != "vector":
        raise ValueError("data shape")
    rows = data.get("result")
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("not a unique scalar")
    one = rows[0]
    if not isinstance(one, dict) or one.get("metric") != {}:
        raise ValueError("unexpected series labels")
    pair = one.get("value")
    if (not isinstance(pair, list) or len(pair) != 2
            or isinstance(pair[0], bool) or not isinstance(pair[0], (int, float))
            or not isinstance(pair[1], str)):
        raise ValueError("value shape")
    sample_time = float(pair[0])
    if not math.isfinite(sample_time) or abs(sample_time - now_epoch) > 30:
        raise ValueError("stale or future query evaluation")
    value = float(pair[1])
    if not math.isfinite(value):
        raise ValueError("invalid metric")
    return value


def fixed_vm_get(query: str) -> bytes:
    """Single allowlisted HTTP GET to loopback; no redirects, host selection or proxies."""
    if query not in dict(QUERIES).values():
        raise ValueError("query not allowlisted")
    path = "/api/v1/query?query=" + quote(query, safe="")
    conn = http.client.HTTPConnection(BIND, VM_PORT, timeout=TIMEOUT)
    try:
        conn.request("GET", path, headers={"Accept": "application/json", "Connection": "close"})
        resp = conn.getresponse()
        if resp.status != 200:
            raise ValueError("API not ready")
        data = resp.read(MAX_BODY + 1)
        if len(data) > MAX_BODY:
            raise ValueError("API response too large")
        return data
    finally:
        conn.close()


def project_aggregates(values: dict[str, float], now: dt.datetime) -> dict:
    """Fail closed for missing, contradictory and stale aggregate measurements."""
    base = {"schema_version": "0.2", "mode": "live-readonly", "source": "VictoriaMetrics / 127.0.0.1:8428 / fixed PromQL",
            "observed_at": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "status": "UNKNOWN", "reason_code": "METRIC_NOT_VERIFIED", "total": None, "healthy": None,
            "oldest_sample_age_seconds": None, "ttl_seconds": TTL_SECONDS}
    try:
        total, healthy, age = (values[k] for k in ("total", "healthy", "age"))
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in (total, healthy, age)):
            return base
        if not (total.is_integer() if isinstance(total, float) else True) or not (healthy.is_integer() if isinstance(healthy, float) else True):
            return base
        if not (1 <= total <= 10000 and 0 <= healthy <= total and -1 <= age <= 86400):
            return base
        base.update(total=int(total), healthy=int(healthy), oldest_sample_age_seconds=round(max(age, 0), 1))
        if age > TTL_SECONDS:
            base.update(status="STALE", reason_code="SCRAPE_SAMPLES_TOO_OLD")
        elif healthy == total:
            base.update(status="OK", reason_code="ALL_SCRAPE_TARGETS_UP")
        elif healthy == 0:
            base.update(status="DOWN", reason_code="ALL_SCRAPE_TARGETS_DOWN")
        else:
            base.update(status="DEGRADED", reason_code="SOME_SCRAPE_TARGETS_DOWN")
    except (KeyError, ValueError, TypeError, OverflowError):
        return base
    return base


def get_summary(read=fixed_vm_get, clock=None) -> dict:
    """No error details, labels or private data cross the browser boundary."""
    if clock is None:
        clock = lambda: dt.datetime.now(dt.timezone.utc)
    now = clock()
    if now.tzinfo is None:
        raise ValueError("clock needs tz")
    unavailable = project_aggregates({}, now)
    try:
        data = {}
        # Queries are not atomic; status is a bounded near-time snapshot.
        for key, promql in QUERIES:
            raw = read(promql)
            data[key] = promql_scalar_from_json(raw, clock().timestamp())
        return project_aggregates(data, clock())
    except (OSError, ValueError, TypeError, KeyError, OverflowError,
            http.client.HTTPException, json.JSONDecodeError, TimeoutError):
        unavailable["reason_code"] = "SOURCE_UNAVAILABLE_OR_INVALID"
        return unavailable


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "HCC-V0.2-lab"
    sys_version = ""

    def send_headers(self, code: int, mime: str, length: int):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()

    def do_GET(self):
        # Host check avoids accidental loopback DNS rebinding. Path must match exactly.
        if self.headers.get("Host") != f"{BIND}:{PORT}":
            self.send_headers(403, "text/plain", 0)
            return
        if self.path == "/api/summary":
            # Reject cross-site API triggers, but allow top-level navigation to
            # static pages even when opened from a link in another website.
            # This is NOT authentication; local programs can forge headers.
            site = self.headers.get("Sec-Fetch-Site")
            origin = self.headers.get("Origin")
            if (site not in (None, "none", "same-origin")
                    or origin not in (None, f"http://{BIND}:{PORT}")):
                self.send_headers(403, "text/plain", 0)
                return
            raw = json.dumps(get_summary(), separators=(",", ":"), ensure_ascii=True).encode("ascii")
            self.send_headers(200, "application/json; charset=utf-8", len(raw))
            self.wfile.write(raw)
            return
        if self.path not in STATIC:
            self.send_headers(404, "text/plain", 0)
            return
        rel, mime = STATIC[self.path]
        raw = (HERE / rel).read_bytes()  # hardcoded allowlisted paths only
        self.send_headers(200, mime, len(raw))
        self.wfile.write(raw)

    def do_POST(self):
        self.send_headers(405, "text/plain", 0)

    do_PUT = do_DELETE = do_PATCH = do_POST

    def log_message(self, fmt, *args):
        # Avoid raw request paths, Host fields and client IPs in logs.
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve-readonly", action="store_true", help="explicit loopback-only opt-in")
    args = parser.parse_args()
    if not args.serve_readonly:
        parser.error("explicit --serve-readonly required")
    if os.geteuid() == 0:
        parser.error("root execution refused")
    print("HCC_V02=LOCAL_MANUAL_READ_ONLY")
    print("NO_ASUS=YES NO_CONFIG_WRITES=YES NO_BACKGROUND_JOB=YES")
    print(f"LOCAL_UI=http://{BIND}:{PORT}/")
    print("VM_QUERY_SOURCE=127.0.0.1:8428 FIXED_AGGREGATES_ONLY")
    print("DEPLOYMENT_GATE=HOLD")
    print("Ctrl+C to stop", flush=True)
    server = HTTPServer((BIND, PORT), RequestHandler)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
