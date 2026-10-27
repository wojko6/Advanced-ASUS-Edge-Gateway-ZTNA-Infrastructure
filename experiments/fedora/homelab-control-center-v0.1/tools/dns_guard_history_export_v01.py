#!/usr/bin/env python3
"""#319: bounded, manually-invoked VM export preflight for ONE DNS Guard series.

Not a background collector, web API, event store, notifier, or live HCC adapter.
No router communication. All exported observations are only sample evidence.
"""
from __future__ import annotations

import argparse
import http.client
import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

METRIC = "asus_edge_dns_guard_mode_bootstrap"
VM_HOST = "127.0.0.1"
VM_PORT = 8428
START = "2026-10-27T14:40:00Z"  # fixed, operator-observed historical window
END = "2026-10-27T16:43:00Z"
MIN_MS = 1793102400000
MAX_MS = 1793109780000
MAX_BYTES = 131072
MAX_SAMPLES = 200
MAX_ADJACENT_GAP_SECONDS = 180
SOURCE = "FEDORA_LOCAL_VICTORIAMETRICS_RAW_EXPORT"
DEPLOYMENT_GATE = "HOLD"


def timestamp(ms: int, tz: str = "UTC") -> str:
    target = timezone.utc if tz == "UTC" else ZoneInfo("Europe/Warsaw")
    return datetime.fromtimestamp(ms / 1000, timezone.utc).astimezone(
        target
    ).isoformat(timespec="milliseconds")


def _mode(v: int) -> str:
    return "BOOTSTRAP" if v == 1 else "LOCAL"


def parse_export(raw: bytes) -> list[tuple[int, int]]:
    """Parse a single *raw* VM series, with no interpolation or sorting."""
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError("SOURCE_SIZE_INVALID")
    lines = [x for x in raw.splitlines() if x.strip()]
    if len(lines) != 1:
        raise ValueError("UNEXPECTED_SERIES_COUNT")
    try:
        obj = json.loads(lines[0].decode("utf-8"),
                         parse_constant=lambda _x: (_ for _ in ()).throw(
                             ValueError("NON_FINITE_JSON")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("MALFORMED_JSON") from exc
    if not isinstance(obj, dict) or set(obj) != {"metric", "timestamps", "values"}:
        raise ValueError("UNEXPECTED_EXPORT_SCHEMA")
    if obj["metric"] != {"__name__": METRIC}:
        raise ValueError("UNEXPECTED_SERIES_LABELS")
    times, values = obj["timestamps"], obj["values"]
    if not isinstance(times, list) or not isinstance(values, list):
        raise ValueError("INVALID_SAMPLE_ARRAYS")
    if not 1 <= len(times) <= MAX_SAMPLES or len(times) != len(values):
        raise ValueError("INVALID_SAMPLE_COUNT")

    samples = []
    previous = None
    for ms, val in zip(times, values):
        if type(ms) is not int or not MIN_MS <= ms <= MAX_MS:
            raise ValueError("INVALID_OR_OUT_OF_WINDOW_TIMESTAMP")
        if type(val) not in (int, float) or val not in (0, 1):
            raise ValueError("INVALID_SAMPLE_VALUE")
        if previous is not None and ms <= previous:
            raise ValueError("UNSORTED_OR_DUPLICATE_TIMESTAMP")
        samples.append((ms, int(val)))
        previous = ms
    return samples


def summarize(samples: list[tuple[int, int]]) -> dict:
    """Strict sample-mode transitions; unknown on sample gaps, never exact times."""
    if not samples or len(samples) > MAX_SAMPLES:
        raise ValueError("INVALID_SAMPLES")
    events = []
    for (before_ms, before_val), (after_ms, after_val) in zip(samples, samples[1:]):
        gap_seconds = (after_ms - before_ms) / 1000
        if gap_seconds <= 0:
            raise ValueError("NON_MONOTONIC")
        if gap_seconds > MAX_ADJACENT_GAP_SECONDS:
            events.append({
                "event_type": "DNS_GUARD_OBSERVATION_GAP",
                "reason_code": "RAW_SAMPLE_GAP_EXCEEDS_PROVISIONAL_LIMIT",
                "window_start": timestamp(before_ms),
                "window_end": timestamp(after_ms),
                "gap_seconds": gap_seconds,
                "confidence": "UNKNOWN",
            })
        elif before_val != after_val:
            events.append({
                "event_type": ("DNS_GUARD_BOOTSTRAP_OBSERVED" if after_val
                               else "DNS_GUARD_LOCAL_RESTORED"),
                "from": _mode(before_val),
                "to": _mode(after_val),
                "window_start": timestamp(before_ms),
                "window_end": timestamp(after_ms),
                "local_window_start": timestamp(before_ms, "Europe/Warsaw"),
                "local_window_end": timestamp(after_ms, "Europe/Warsaw"),
                "gap_seconds": gap_seconds,
                "reason_code": "ADJACENT_RAW_SAMPLES_DIFFER",
                "confidence": "BOUNDED_OBSERVATION",
                "coverage": "SAMPLED_MODE_ONLY",
            })
    return {
        "schema_version": "dns-guard-raw-export-preflight/0.1",
        "mode": "MANUAL_FIXED_HISTORICAL_WINDOW",
        "source": SOURCE,
        "series_count": 1,
        "samples_count": len(samples),
        "first_sample_at": timestamp(samples[0][0]),
        "last_sample_at": timestamp(samples[-1][0]),
        "initial_sampled_mode": _mode(samples[0][1]),
        "final_sampled_mode": _mode(samples[-1][1]),
        "events": events,
        "observed_change_count": sum(e["event_type"] in (
            "DNS_GUARD_BOOTSTRAP_OBSERVED", "DNS_GUARD_LOCAL_RESTORED"
        ) for e in events),
        "limitation": (
            "Single unlabeled raw mode series. No exact switch time; "
            "unobserved short flaps and causal DNS health remain UNKNOWN. "
            "Other DNS Guard metrics are not cross-validated here."
        ),
        "router_contact": False,
        "production_changes": False,
        "deployment_gate": DEPLOYMENT_GATE,
    }


def fixed_uri() -> str:
    return "/api/v1/export?" + urlencode({
        "match[]": METRIC, "start": START, "end": END,
        "max_rows_per_line": str(MAX_SAMPLES),
    })


def read_local(*, connector=http.client.HTTPConnection) -> dict:
    """Explicit opt-in only: GET fixed VM localhost endpoint, capped response."""
    conn = connector(VM_HOST, VM_PORT, timeout=5)
    try:
        conn.request("GET", fixed_uri())
        response = conn.getresponse()
        raw = response.read(MAX_BYTES + 1)
        if response.status != 200:
            raise ValueError("SOURCE_HTTP_NOT_200")
        if len(raw) > MAX_BYTES:
            raise ValueError("SOURCE_SIZE_LIMIT")
        return summarize(parse_export(raw))
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    flags = parser.add_mutually_exclusive_group(required=True)
    flags.add_argument("--inspect", action="store_true",
                       help="Print fixed source contract; never contact VM")
    flags.add_argument("--read-local", action="store_true",
                       help="Read only 127.0.0.1:8428 fixed October 27 history")
    args = parser.parse_args()
    if args.inspect:
        print(json.dumps({
            "mode": "INSPECT_ONLY_NO_NETWORK",
            "source": SOURCE, "metric": METRIC, "start": START, "end": END,
            "max_bytes": MAX_BYTES, "max_samples": MAX_SAMPLES,
            "deploy_gate": DEPLOYMENT_GATE,
        }, sort_keys=True, ensure_ascii=False))
        return 0
    try:
        result = read_local()
    except (OSError, ValueError, UnicodeError) as exc:
        result = {
            "status": "UNKNOWN",
            "reason_code": type(exc).__name__,
            "source": SOURCE,
            "router_contact": False,
            "production_changes": False,
            "deployment_gate": DEPLOYMENT_GATE,
        }
        print(json.dumps(result, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
