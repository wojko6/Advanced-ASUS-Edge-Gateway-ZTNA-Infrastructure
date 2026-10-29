#!/usr/bin/env python3
"""HCC V0.6-B1: pure offline, bounded seven-series coverage analysis.

This is NOT a VictoriaMetrics collector, DNS-health signal, router observer,
continuous incident log, notification sender, HCC endpoint or scheduled job.
It only describes where synchronized sampled telemetry exists or is missing.
Inputs come from separately validated local sources; no I/O occurs here.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math

SCHEMA = "hcc-dns-guard-coverage/0.6-b1"
SOURCE = "FEDORA_VM_SEVEN_DNS_GUARD_SERIES"
WINDOWS_MS = {"1h": 3600000, "6h": 21600000,
              "24h": 86400000, "7d": 604800000}
SUFFIXES = (
    "mode_local", "mode_bootstrap", "state_valid",
    "last_transition_timestamp_seconds", "fallback_since_timestamp_seconds",
    "fallback_transitions_runtime_total", "collection_timestamp_seconds",
)
MAX_SAMPLES = 12000   # accommodates observed ~4963/7d, not unlimited exports
MAX_SKEW_MS = 5000
MAX_COLLECTION_DELAY_SECONDS = 30
GAP_THRESHOLD_MS = 180000  # provisional telemetry threshold, NOT DNS availability
MAX_OUTPUT_ITEMS = 128
MIN_MS = 946684800000
MAX_MS = 4102444800000


def utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


def _whole(value: object, maximum: int) -> int:
    if type(value) not in (int, float):
        raise ValueError("INVALID_METRIC_TYPE")
    if not math.isfinite(value) or value < 0 or value > maximum or int(value) != value:
        raise ValueError("INVALID_METRIC_VALUE")
    return int(value)


def unknown(reason: str) -> dict:
    return {
        "schema_version": SCHEMA, "mode": "OFFLINE_EVIDENCE_ONLY",
        "source": SOURCE, "status": "UNKNOWN", "reason_code": reason,
        "sample_count": None, "segments": [], "gaps": [],
        "invalid_sample_count": None, "window_start_utc": None,
        "window_end_utc": None, "deployment_gate": "HOLD",
    }


def analyze(series: object, window: str, window_end_ms: int) -> dict:
    """Analyze seven ordered lists of (timestamp_ms, value) pairs.

    Missing source or conflicting/unaligned samples fail closed. Gap lengths
    describe ABSENCE OF TELEMETRY, never router shutdown or DNS outage.
    No transition is inferred across a gap or an invalid sample.
    """
    if window not in WINDOWS_MS or type(window_end_ms) is not int:
        return unknown("INVALID_WINDOW")
    if not MIN_MS + WINDOWS_MS[window] <= window_end_ms <= MAX_MS:
        return unknown("INVALID_WINDOW_CLOCK")
    if type(series) is not dict or set(series) != set(SUFFIXES):
        return unknown("MISSING_EXTRA_OR_UNEXPECTED_SERIES")
    window_start_ms = window_end_ms - WINDOWS_MS[window]
    try:
        streams = {}
        for name in SUFFIXES:
            samples = series[name]
            if type(samples) not in (list, tuple) or len(samples) > MAX_SAMPLES:
                raise ValueError("SAMPLE_LIMIT_OR_SHAPE")
            parsed = []
            previous = None
            for pair in samples:
                if type(pair) not in (list, tuple) or len(pair) != 2:
                    raise ValueError("INVALID_SAMPLE_PAIR")
                at, value = pair
                if (type(at) is not int or not window_start_ms <= at <= window_end_ms
                        or previous is not None and at <= previous):
                    raise ValueError("OUT_OF_RANGE_OR_UNORDERED_TIMESTAMP")
                maximum = (1 if name in SUFFIXES[:3] else
                           999999999 if name == "fallback_transitions_runtime_total"
                           else 4102444800)
                parsed.append((at, _whole(value, maximum)))
                previous = at
            streams[name] = parsed

        count = len(streams["mode_bootstrap"])
        if count == 0:
            return unknown("NO_TELEMETRY_IN_WINDOW")
        if any(len(s) != count for s in streams.values()):
            raise ValueError("CROSS_SERIES_COUNT_MISMATCH")

        anchor = streams["mode_bootstrap"]
        times = [x[0] for x in anchor]
        valid = []
        for i, (anchor_ms, _) in enumerate(anchor):
            row = {name: streams[name][i][1] for name in SUFFIXES}
            if any(abs(streams[name][i][0] - anchor_ms) > MAX_SKEW_MS
                   for name in SUFFIXES):
                raise ValueError("CROSS_SERIES_TIMESTAMP_MISMATCH")
            if (abs(anchor_ms / 1000 - row["collection_timestamp_seconds"])
                    > MAX_COLLECTION_DELAY_SECONDS):
                raise ValueError("SOURCE_COLLECTION_TIME_MISMATCH")
            if (row["last_transition_timestamp_seconds"] >
                    row["collection_timestamp_seconds"] + 5
                    or row["fallback_since_timestamp_seconds"] >
                    row["collection_timestamp_seconds"] + 5):
                raise ValueError("FUTURE_ROUTER_REPORTED_TIME")
            is_valid = (
                row["state_valid"] == 1
                and row["mode_local"] + row["mode_bootstrap"] == 1
                and (row["mode_bootstrap"] == 1
                     or row["fallback_since_timestamp_seconds"] == 0)
            )
            valid.append(is_valid)

        gaps = []
        def gap(start: int, end: int, position: str) -> None:
            if end - start > GAP_THRESHOLD_MS:
                if len(gaps) >= MAX_OUTPUT_ITEMS:
                    raise ValueError("TOO_MANY_GAPS")
                gaps.append({"kind": "TELEMETRY_GAP",
                             "position": position,
                             "start_utc": utc(start), "end_utc": utc(end),
                             "duration_seconds": round((end - start) / 1000, 3),
                             "cause": "NOT_DETERMINED"})

        gap(window_start_ms, times[0], "LEADING")
        for prior, following in zip(times, times[1:]):
            gap(prior, following, "INTERNAL")
        gap(times[-1], window_end_ms, "TRAILING")

        segments = []
        run_start = None
        def close_run(last_index: int) -> None:
            nonlocal run_start
            if run_start is not None:
                if len(segments) >= MAX_OUTPUT_ITEMS:
                    raise ValueError("TOO_MANY_SEGMENTS")
                segments.append({
                    "kind": "OBSERVED_TELEMETRY_SEGMENT",
                    "start_utc": utc(times[run_start]),
                    "end_utc": utc(times[last_index]),
                    "sample_count": last_index - run_start + 1,
                    "interpretation": "SAMPLED_TELEMETRY_NOT_DNS_UPTIME",
                })
                run_start = None

        for i, ok in enumerate(valid):
            if run_start is not None and (
                not ok or (i > 0 and times[i] - times[i-1] > GAP_THRESHOLD_MS)
            ):
                close_run(i-1)
            if ok and run_start is None:
                run_start = i
        close_run(count-1)

        invalid_count = valid.count(False)
        return {
            "schema_version": SCHEMA, "mode": "OFFLINE_EVIDENCE_ONLY",
            "source": SOURCE,
            "status": ("COVERAGE_OBSERVED_WITH_UNCERTAINTY"
                       if gaps or invalid_count else "COVERAGE_OBSERVED"),
            "reason_code": "SAMPLED_COVERAGE_ONLY",
            "window": window, "window_start_utc": utc(window_start_ms),
            "window_end_utc": utc(window_end_ms),
            "sample_count": count,
            "segments": segments, "gaps": gaps,
            "invalid_sample_count": invalid_count,
            "max_cross_series_skew_ms": max(
                abs(streams[name][i][0] - times[i])
                for name in SUFFIXES for i in range(count)),
            "limitations": (
                "No claim about DNS uptime, reasons for gaps, missed short flaps, "
                "exact transition time or planned shutdown. No event reconstruction."
            ),
            "deployment_gate": "HOLD",
        }
    except (ValueError, TypeError, OverflowError):
        return unknown("SOURCE_OR_COVERAGE_CONTRACT_NOT_VERIFIED")
