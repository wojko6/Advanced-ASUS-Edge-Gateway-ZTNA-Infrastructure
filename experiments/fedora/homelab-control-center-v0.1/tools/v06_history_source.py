#!/usr/bin/env python3
"""HCC V0.6-B2 manual-only, fixed-allowlist local VictoriaMetrics history adapter.

No HCC HTTP endpoint, service, timer, auto-read, storage, alerts, SSH or router
contact. Only explicit --read-local performs seven GETs to 127.0.0.1:8428.
No user-provided URLs, hostnames, PromQL, metric selectors or arbitrary dates.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import http.client
import json
import math
from urllib.parse import urlencode

import v06_coverage_model as coverage

HOST = "127.0.0.1"
PORT = 8428
TIMEOUT_SECONDS = 5  # per socket operation, NOT a global deadline
ROWS_PER_LINE = 200
MAX_EXPORT_CHUNKS = 64
MAX_BYTES_PER_METRIC = 524288
MAX_TOTAL_SAMPLES = coverage.MAX_SAMPLES
METRIC_PREFIX = "asus_edge_dns_guard_"
METRICS = tuple(METRIC_PREFIX + name for name in coverage.SUFFIXES)
SCHEMA = "hcc-dns-guard-history-source/0.6-b2"
MAX_LINE_BYTES = 32768


def _object_no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _invalid_constant(_):
    raise ValueError("NONFINITE_JSON_CONSTANT")


def _datetime(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


def fixed_path(metric: str, window: str, window_end_ms: int) -> str:
    """Exact fixed-series VictoriaMetrics raw export, never user-selected PromQL."""
    if (metric not in METRICS or type(window) is not str
            or window not in coverage.WINDOWS_MS
            or type(window_end_ms) is not int
            or not coverage.MIN_MS + coverage.WINDOWS_MS[window]
            <= window_end_ms <= coverage.MAX_MS):
        raise ValueError("INVALID_FIXED_QUERY")
    start_ms = window_end_ms - coverage.WINDOWS_MS[window]
    return "/api/v1/export?" + urlencode({
        "match[]": metric,
        "start": _datetime(start_ms),
        "end": _datetime(window_end_ms),
        "max_rows_per_line": str(ROWS_PER_LINE),
    })


def parse_chunks(metric: str, raw: bytes, start_ms: int, end_ms: int) -> list[tuple[int, int]]:
    """Fail closed on extra labels, malformed NDJSON, duplicates, ordering, limits."""
    if (metric not in METRICS or type(start_ms) is not int or type(end_ms) is not int
            or not coverage.MIN_MS <= start_ms < end_ms <= coverage.MAX_MS
            or type(raw) is not bytes or len(raw) > MAX_BYTES_PER_METRIC):
        raise ValueError("INVALID_EXPORT_BOUNDARY")
    lines = [line for line in raw.splitlines() if line.strip()]
    if not 1 <= len(lines) <= MAX_EXPORT_CHUNKS:
        raise ValueError("EXPORT_CHUNK_LIMIT")
    name = metric.removeprefix(METRIC_PREFIX)
    limit = (1 if name in coverage.SUFFIXES[:3]
             else 999999999 if name == "fallback_transitions_runtime_total"
             else 4102444800)
    parsed = []
    prior = None
    for line in lines:
        if len(line) > MAX_LINE_BYTES:
            raise ValueError("EXPORT_LINE_LIMIT")
        record = json.loads(line.decode("utf-8"),
                            object_pairs_hook=_object_no_duplicates,
                            parse_constant=_invalid_constant)
        if type(record) is not dict or set(record) != {"metric", "timestamps", "values"}:
            raise ValueError("EXPORT_SCHEMA")
        if record["metric"] != {"__name__": metric}:
            raise ValueError("UNEXPECTED_SOURCE_LABELS")
        stamps, values = record["timestamps"], record["values"]
        if (type(stamps) is not list or type(values) is not list
                or not 1 <= len(stamps) <= ROWS_PER_LINE
                or len(stamps) != len(values)):
            raise ValueError("EXPORT_ARRAYS")
        if len(parsed) + len(stamps) > MAX_TOTAL_SAMPLES:
            raise ValueError("TOO_MANY_SAMPLES")
        for at, value in zip(stamps, values):
            if (type(at) is not int or not start_ms <= at <= end_ms
                    or prior is not None and at <= prior):
                raise ValueError("TIMESTAMP_NOT_STRICTLY_INCREASING")
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or not 0 <= value <= limit or int(value) != value):
                raise ValueError("INVALID_EXPORTED_VALUE")
            parsed.append((at, int(value)))
            prior = at
    return parsed


def unknown() -> dict:
    data = coverage.unknown("SOURCE_UNAVAILABLE_OR_INVALID")
    data["source_adapter"] = SCHEMA
    return data


def _read_one(metric: str, window: str, end_ms: int, connector) -> list[tuple[int, int]]:
    # Always loopback; never redirects, proxies, caller-selected URL or Host.
    conn = connector(HOST, PORT, timeout=TIMEOUT_SECONDS)
    try:
        conn.request("GET", fixed_path(metric, window, end_ms),
                     headers={"Accept": "application/json",
                              "Connection": "close"})
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError("HTTP_NOT_200")
        raw = response.read(MAX_BYTES_PER_METRIC + 1)
        if len(raw) > MAX_BYTES_PER_METRIC:
            raise ValueError("EXPORT_RESPONSE_TOO_LARGE")
    finally:
        conn.close()
    return parse_chunks(metric, raw, end_ms-coverage.WINDOWS_MS[window], end_ms)


def read_local(window: str, *, clock=None, connector=http.client.HTTPConnection) -> dict:
    """Only called by explicit operator action; no async collectors or caching."""
    if type(window) is not str or window not in coverage.WINDOWS_MS:
        return unknown()
    if clock is None:
        clock = lambda: datetime.now(timezone.utc)
    try:
        moment = clock()
        if not isinstance(moment, datetime) or moment.tzinfo is None:
            raise ValueError("CLOCK_UNVERIFIED")
        end_ms = int(moment.timestamp()*1000)
        if not coverage.MIN_MS + coverage.WINDOWS_MS[window] <= end_ms <= coverage.MAX_MS:
            raise ValueError("CLOCK_OUTSIDE_WINDOW")
        series = {
            name: _read_one(METRIC_PREFIX + name, window, end_ms, connector)
            for name in coverage.SUFFIXES
        }
        result = coverage.analyze(series, window, end_ms)
        result["source_adapter"] = SCHEMA
        return result
    except (OSError, ValueError, TypeError, KeyError, OverflowError,
            UnicodeError, http.client.HTTPException):
        return unknown()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inspect", action="store_true", help="no network")
    group.add_argument("--read-local", action="store_true",
                       help="manual seven local fixed-series GETs")
    parser.add_argument("--window", choices=tuple(coverage.WINDOWS_MS),
                        help="exact allowlisted window, required for --read-local")
    args = parser.parse_args()
    if args.inspect:
        print(json.dumps({
            "mode": "INSPECT_ONLY_NO_NETWORK",
            "source_adapter": SCHEMA,
            "metric_count": len(METRICS),
            "windows": list(coverage.WINDOWS_MS),
            "vm_host": HOST, "vm_port": PORT,
            "max_samples_per_metric": MAX_TOTAL_SAMPLES,
            "max_bytes_per_metric": MAX_BYTES_PER_METRIC,
            "max_chunks_per_metric": MAX_EXPORT_CHUNKS,
            "deployment_gate": "HOLD",
        }, sort_keys=True))
        return 0
    if args.window is None:
        parser.error("--window required with --read-local")
    result = read_local(args.window)
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0 if result["status"] != "UNKNOWN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
