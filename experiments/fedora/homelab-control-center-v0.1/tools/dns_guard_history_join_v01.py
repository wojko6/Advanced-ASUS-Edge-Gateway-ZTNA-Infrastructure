#!/usr/bin/env python3
"""Issue #319: manually gated, seven-series VM historical contract preflight.

Not an HCC API or notification sender. Explicit --read-local makes seven
literal GETs to Fedora 127.0.0.1:8428, for one fixed historical window.
All seven series must align; ambiguity fails closed. No router contact.
"""
from __future__ import annotations

import argparse
import http.client
import json
import math
from datetime import datetime, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from dns_guard_event_model_v01 import timeline

PREFIX = "asus_edge_dns_guard_"
SUFFIXES = (
    "mode_local",
    "mode_bootstrap",
    "state_valid",
    "last_transition_timestamp_seconds",
    "fallback_since_timestamp_seconds",
    "fallback_transitions_runtime_total",
    "collection_timestamp_seconds",
)
METRICS = tuple(PREFIX + x for x in SUFFIXES)
START = "2026-10-27T14:40:00Z"
END = "2026-10-27T16:43:00Z"
MIN_MS = 1793112000000
MAX_MS = 1793119380000
MAX_SAMPLES = 200
MAX_BYTES_PER_SERIES = 131072
MAX_SKEW_MS = 5000
MAX_INGEST_DELAY_SECONDS = 30
SOURCE = "FEDORA_VM_SEVEN_FIXED_DNS_GUARD_RAW_EXPORTS"


def _json_no_duplicates(raw: bytes) -> dict:
    def object_pairs(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("DUPLICATE_JSON_KEY")
            obj[key] = value
        return obj

    def invalid_constant(_):
        raise ValueError("NONFINITE_JSON_VALUE")

    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=object_pairs,
                            parse_constant=invalid_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("INVALID_JSON") from exc
    if not isinstance(result, dict):
        raise ValueError("INVALID_JSON_SHAPE")
    return result


def _whole_number(value: object, upper: int) -> int:
    if type(value) not in (int, float):
        raise ValueError("INVALID_NUMBER_TYPE")
    if not math.isfinite(value) or int(value) != value or not 0 <= value <= upper:
        raise ValueError("INVALID_NUMBER_VALUE")
    return int(value)


def parse_one(metric: str, raw: bytes) -> list[tuple[int, int]]:
    """Exactly one unlabeled original series, no sorting or interpolation."""
    if metric not in METRICS or type(raw) is not bytes or len(raw) > MAX_BYTES_PER_SERIES:
        raise ValueError("METRIC_OR_RESPONSE_BOUNDARY")
    lines = [x for x in raw.splitlines() if x.strip()]
    if len(lines) != 1:
        raise ValueError("NOT_EXACTLY_ONE_SERIES")
    payload = _json_no_duplicates(lines[0])
    if set(payload) != {"metric", "timestamps", "values"}:
        raise ValueError("INVALID_EXPORT_SCHEMA")
    if payload["metric"] != {"__name__": metric}:
        raise ValueError("UNEXPECTED_METRIC_OR_LABELS")
    times, values = payload["timestamps"], payload["values"]
    if not isinstance(times, list) or not isinstance(values, list):
        raise ValueError("INVALID_SERIES_ARRAYS")
    if not 1 <= len(times) <= MAX_SAMPLES or len(times) != len(values):
        raise ValueError("INVALID_SERIES_LENGTH")
    result = []
    prior = None
    for ts, val in zip(times, values):
        if type(ts) is not int or not MIN_MS <= ts <= MAX_MS:
            raise ValueError("BAD_SAMPLE_TIMESTAMP")
        if prior is not None and ts <= prior:
            raise ValueError("DUPLICATE_OR_OUT_OF_ORDER_TIMESTAMP")
        limit = (1 if metric.endswith(("mode_local", "mode_bootstrap", "state_valid"))
                 else 999999999 if metric.endswith("fallback_transitions_runtime_total")
                 else 4102444800)
        result.append((ts, _whole_number(val, limit)))
        prior = ts
    return result


def _utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds")


def _cet(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).astimezone(
        ZoneInfo("Europe/Warsaw")
    ).isoformat(timespec="milliseconds")


def reconcile(raw_by_metric: object) -> dict:
    """Fail closed on absent or misaligned streams; use offline event model."""
    if type(raw_by_metric) is not dict or set(raw_by_metric) != set(METRICS):
        raise ValueError("MISSING_OR_EXTRA_SERIES")
    data = {metric: parse_one(metric, raw_by_metric[metric]) for metric in METRICS}
    anchor = data[PREFIX + "mode_bootstrap"]
    if any(len(stream) != len(anchor) for stream in data.values()):
        raise ValueError("SERIES_LENGTH_MISMATCH")
    rows = []
    observations = []
    for index, (ref_ms, ref_boot) in enumerate(anchor):
        merged = {}
        for suffix, metric in zip(SUFFIXES, METRICS):
            ms, val = data[metric][index]
            if abs(ms - ref_ms) > MAX_SKEW_MS:
                raise ValueError("CROSS_SERIES_TIMESTAMP_MISALIGNMENT")
            merged[suffix] = val
        collection = merged["collection_timestamp_seconds"]
        if not 946684800 <= collection <= 4102444800:
            raise ValueError("COLLECTION_EPOCH_INVALID")
        if abs(ref_ms / 1000 - collection) > MAX_INGEST_DELAY_SECONDS:
            raise ValueError("COLLECTION_TO_IMPORT_CLOCK_MISMATCH")
        if rows and collection <= rows[-1]["collection_epoch"]:
            raise ValueError("NON_INCREASING_COLLECTION_EPOCH")
        if merged["mode_bootstrap"] != ref_boot:
            raise ValueError("ANCHOR_MISMATCH")
        rows.append({
            "collection_epoch": collection,
            "mode_local": merged["mode_local"],
            "mode_bootstrap": merged["mode_bootstrap"],
            "state_valid": merged["state_valid"],
            "last_transition_epoch": merged["last_transition_timestamp_seconds"],
            "fallback_since_epoch": merged["fallback_since_timestamp_seconds"],
            "fallback_transitions_total": merged["fallback_transitions_runtime_total"],
        })
        observations.append((ref_ms, ref_boot))
    model = timeline(rows)
    changes = []
    for (start_ms, start_boot), (end_ms, end_boot) in zip(observations, observations[1:]):
        if start_boot != end_boot:
            changes.append({
                "type": "LOCAL_TO_BOOTSTRAP" if end_boot else "BOOTSTRAP_TO_LOCAL",
                "previous_sample_utc": _utc(start_ms),
                "next_sample_utc": _utc(end_ms),
                "previous_sample_local": _cet(start_ms),
                "next_sample_local": _cet(end_ms),
                "gap_seconds": round((end_ms - start_ms) / 1000, 3),
                "interpretation": "RAW_SAMPLED_MODE_ONLY_NOT_EXACT_EVENT_TIME",
            })
    unknowns = [e for e in model["events"] if e["event_type"] in (
        "DNS_GUARD_STATE_UNKNOWN", "DNS_GUARD_TELEMETRY_STALE")]
    model_changes = [e for e in model["events"] if e["event_type"] in (
        "DNS_GUARD_BOOTSTRAP_OBSERVED", "DNS_GUARD_LOCAL_RESTORED")]
    return {
        "schema_version": "dns-guard-seven-series-preflight/0.1",
        "mode": "MANUAL_FIXED_HISTORICAL_SEVEN_SERIES",
        "source": SOURCE,
        "metric_count": len(METRICS),
        "sample_count": len(rows),
        "sampled_mode_change_count": len(changes),
        "model_observed_change_count": len(model_changes),
        "model_unknown_or_gap_count": len(unknowns),
        "corroborated_sampled_transitions":
            len(unknowns) == 0 and len(changes) == len(model_changes),
        "first_utc": _utc(anchor[0][0]),
        "last_utc": _utc(anchor[-1][0]),
        "transition_windows": changes,
        "model_events": model["events"],
        "limitations": (
            "Seven non-atomic VM raw exports aligned by bounded sample timestamp "
            "and collection epoch; no exact switch time, all short flaps, "
            "or proof of DNS health."
        ),
        "router_contact": False,
        "notification_sent": False,
        "production_changes": False,
        "deployment_gate": "HOLD",
    }


def fixed_uri(metric: str) -> str:
    if metric not in METRICS:
        raise ValueError("METRIC_NOT_ALLOWED")
    return "/api/v1/export?" + urlencode({
        "match[]": metric, "start": START, "end": END,
        "max_rows_per_line": str(MAX_SAMPLES),
    })


def read_local(*, connector=http.client.HTTPConnection) -> dict:
    """Seven fixed historical localhost GETs, only on explicit invocation."""
    source = {}
    for metric in METRICS:
        conn = connector("127.0.0.1", 8428, timeout=5)
        try:
            conn.request("GET", fixed_uri(metric))
            response = conn.getresponse()
            raw = response.read(MAX_BYTES_PER_SERIES + 1)
            if response.status != 200 or len(raw) > MAX_BYTES_PER_SERIES:
                raise ValueError("HTTP_OR_SIZE_GATE")
            parse_one(metric, raw)
            source[metric] = raw
        finally:
            conn.close()
    return reconcile(source)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect", action="store_true", help="no network")
    mode.add_argument("--read-local", action="store_true", help="seven bounded localhost reads")
    args = parser.parse_args()
    if args.inspect:
        print(json.dumps({
            "mode": "INSPECT_ONLY_NO_NETWORK", "source": SOURCE,
            "metric_suffixes": SUFFIXES, "vm_host": "127.0.0.1",
            "start": START, "end": END,
            "max_series": len(METRICS), "max_samples_each": MAX_SAMPLES,
            "max_bytes_each": MAX_BYTES_PER_SERIES, "max_skew_ms": MAX_SKEW_MS,
            "deploy_gate": "HOLD",
        }, ensure_ascii=False, sort_keys=True))
        return 0
    try:
        result = read_local()
    except (OSError, ValueError, UnicodeError, OverflowError):
        print(json.dumps({
            "status": "UNKNOWN", "reason_code": "SOURCE_CONTRACT_NOT_VERIFIED",
            "source": SOURCE, "router_contact": False,
            "notification_sent": False, "production_changes": False,
            "deployment_gate": "HOLD",
        }, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
