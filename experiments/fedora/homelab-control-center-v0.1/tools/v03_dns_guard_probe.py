#!/usr/bin/env python3
"""V0.3 experimental DNS Guard telemetry probe: local VictoriaMetrics only.

This module is NOT wired to the running V0.2 app and is NOT a service.
Explicit --probe-local-vm performs exactly six fixed local GETs (no SSH/router).
No command execution, writes, credentials, environment-based URLs or arbitrary PromQL.
"""
from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import math
import os
import re
from urllib.parse import quote

LOOPBACK = "127.0.0.1"
VM_PORT = 8428
HTTP_TIMEOUT = 2
MAX_REPLY_BYTES = 8192
MAX_COLLECTION_AGE_SECONDS = 180  # provisional; operator must confirm cadence
EVALUATION_SKEW_SECONDS = 30
MAX_CLOCK_LEAD_SECONDS = 5

METRICS = (
    ("collection", "asus_edge_dns_guard_collection_timestamp_seconds"),
    ("valid", "asus_edge_dns_guard_state_valid"),
    ("local", "asus_edge_dns_guard_mode_local"),
    ("bootstrap", "asus_edge_dns_guard_mode_bootstrap"),
    ("breakglass", "asus_edge_dns_guard_breakglass_active"),
    ("watchdog", "asus_edge_dns_guard_watchdog_present"),
)
ALLOWLIST = frozenset(metric for _, metric in METRICS)
METRIC_NAME_RE = re.compile(r"^asus_edge_dns_guard_[a-z0-9_]+$")
NUMBER_RE = re.compile(r"^(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,9})?$")


def fetch_metric(metric: str) -> bytes:
    """Fixed single metric selector against operator-local VM; no redirect/proxy."""
    if metric not in ALLOWLIST:
        raise ValueError("metric is not allowlisted")
    path = "/api/v1/query?query=" + quote(metric, safe="")
    conn = http.client.HTTPConnection(LOOPBACK, VM_PORT, timeout=HTTP_TIMEOUT)
    try:
        conn.request("GET", path, headers={"Accept": "application/json", "Connection": "close"})
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError("VM non-200")
        body = response.read(MAX_REPLY_BYTES + 1)
        if len(body) > MAX_REPLY_BYTES:
            raise ValueError("VM reply oversize")
        return body
    finally:
        conn.close()


def parse_metric(raw: bytes, expected: str, now_epoch: float) -> float:
    """Require exactly one unlabelled exporter series with the exact metric name."""
    if expected not in ALLOWLIST or not METRIC_NAME_RE.fullmatch(expected):
        raise ValueError("metric not in contract")
    if len(raw) > MAX_REPLY_BYTES:
        raise ValueError("oversize")
    document = json.loads(raw)
    if not isinstance(document, dict) or document.get("status") != "success":
        raise ValueError("API status")
    data = document.get("data")
    if not isinstance(data, dict) or data.get("resultType") != "vector":
        raise ValueError("not an instant vector")
    items = data.get("result")
    if not isinstance(items, list) or len(items) != 1:
        raise ValueError("missing/duplicate metric")
    item = items[0]
    if not isinstance(item, dict) or item.get("metric") != {"__name__": expected}:
        raise ValueError("unexpected label set")
    pair = item.get("value")
    if not isinstance(pair, list) or len(pair) != 2:
        raise ValueError("bad sample")
    when, value = pair
    if isinstance(when, bool) or not isinstance(when, (int, float)):
        raise ValueError("bad sample time")
    if not math.isfinite(when) or abs(float(when) - now_epoch) > EVALUATION_SKEW_SECONDS:
        raise ValueError("sample timestamp outside window")
    if not isinstance(value, str) or not NUMBER_RE.fullmatch(value):
        raise ValueError("bad metric value")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite")
    return number


def snapshot(values: dict[str, float], now: dt.datetime) -> dict:
    """Report *telemetry*, never assert DNS query-path health from a mode flag."""
    if now.tzinfo is None:
        raise ValueError("timezone-aware clock required")
    result = {
        "schema_version": "0.3",
        "kind": "dns-guard-telemetry",
        "mode": "manual-local-vm-readonly",
        "source": "VictoriaMetrics local fixed DNS Guard metrics",
        "observed_at": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "UNKNOWN",
        "reason_code": "TELEMETRY_NOT_VERIFIED",
        "dns_mode": "UNVERIFIED",
        "collection_age_seconds": None,
        "ttl_seconds": MAX_COLLECTION_AGE_SECONDS,
        "breakglass_active": None,
        "watchdog_present": None,
    }
    if set(values) != {key for key, _ in METRICS}:
        return result
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in values.values()):
        return result
    if any(values[key] not in (0, 1) for key in ("valid", "local", "bootstrap", "breakglass", "watchdog")):
        return result
    collection = values["collection"]
    if not collection.is_integer() if isinstance(collection, float) else False:
        return result
    if collection <= 0 or collection > now.timestamp() + MAX_CLOCK_LEAD_SECONDS:
        return result
    age = round(max(0., now.timestamp() - collection), 1)
    result["collection_age_seconds"] = age
    if age > MAX_COLLECTION_AGE_SECONDS:
        result.update(status="STALE", reason_code="COLLECTION_TOO_OLD")
        return result

    if values["valid"] != 1:
        result["reason_code"] = "STATE_NOT_VALID"
        return result
    if values["local"] + values["bootstrap"] != 1:
        result["reason_code"] = "MODE_FLAGS_INVALID"
        return result
    result["dns_mode"] = "LOCAL" if values["local"] == 1 else "BOOTSTRAP"
    result["breakglass_active"] = values["breakglass"] == 1
    result["watchdog_present"] = values["watchdog"] == 1
    if result["breakglass_active"]:
        result.update(status="DEGRADED", reason_code="BREAKGLASS_ACTIVE")
    elif not result["watchdog_present"]:
        result.update(status="DEGRADED", reason_code="WATCHDOG_NOT_PRESENT")
    elif result["dns_mode"] == "BOOTSTRAP":
        result.update(status="DEGRADED", reason_code="BOOTSTRAP_MODE")
    else:
        result.update(status="OK", reason_code="LOCAL_MODE_REPORTED")
    return result


def collect(fetch=fetch_metric, clock=None) -> dict:
    """Collapse missing, malformed and unauthorized data to bounded UNKNOWN."""
    if clock is None:
        clock = lambda: dt.datetime.now(dt.timezone.utc)
    now = clock()
    if now.tzinfo is None:
        raise ValueError("timezone-aware clock required")
    result = snapshot({}, now)
    try:
        readings = {}
        for key, metric in METRICS:
            readings[key] = parse_metric(fetch(metric), metric, clock().timestamp())
        return snapshot(readings, clock())
    except (OSError, ValueError, TypeError, KeyError, OverflowError, AttributeError,
            http.client.HTTPException, TimeoutError, json.JSONDecodeError):
        result["reason_code"] = "SOURCE_UNAVAILABLE_OR_INVALID"
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--show-contract", action="store_true", help="print fixed metric names; never connect")
    options.add_argument("--probe-local-vm", action="store_true",
                         help="explicit local VictoriaMetrics GETs; no router contact")
    arguments = parser.parse_args()
    if arguments.show_contract:
        print("V03=FEDORA_ONLY DNS_GUARD_TELEMETRY=FIXED_METRICS")
        print("MODE=NO_NETWORK")
        for _, name in METRICS:
            print(name)
        print("DEPLOYMENT_GATE=HOLD")
        return 0
    if os.geteuid() == 0:
        parser.error("root execution refused")
    print("V03=MANUAL_READ_ONLY VM=127.0.0.1:8428 NO_ASUS_CONTACT=YES NO_CONFIG_WRITES=YES")
    print(json.dumps(collect(), separators=(",", ":"), sort_keys=True))
    print("DEPLOYMENT_GATE=HOLD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
