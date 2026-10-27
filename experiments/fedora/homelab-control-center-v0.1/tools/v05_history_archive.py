#!/usr/bin/env python3
"""V0.5: sanitized, bounded view of a verified fixed 2026-10-27 archive.

The upstream #322 seven-series join stays unchanged. This projection NEVER
claims rolling LIVE history, full DNS availability, or exact switch times.
No network access in this module; manual server opt-in is separate.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import dns_guard_history_join_v01 as join

KIND = "dns-guard-history-archive"
SCHEMA = "0.5"
MODE = "manual-fixed-archive-readonly"
SOURCE = join.SOURCE
START = join.START
END = join.END
MAX_EVENTS = 8
EXPECTED_EVENT_TYPES = {
    "LOCAL_TO_BOOTSTRAP": "DNS_GUARD_BOOTSTRAP_OBSERVED",
    "BOOTSTRAP_TO_LOCAL": "DNS_GUARD_LOCAL_RESTORED",
}
MIN_TS = datetime.fromisoformat(START.replace("Z", "+00:00"))
MAX_TS = datetime.fromisoformat(END.replace("Z", "+00:00"))


def unknown() -> dict:
    return {
        "schema_version": SCHEMA, "kind": KIND, "mode": MODE,
        "status": "UNKNOWN", "reason_code": "ARCHIVE_EVIDENCE_NOT_VERIFIED",
        "source": SOURCE, "archive_start": START, "archive_end": END,
        "sample_count": None, "event_count": 0, "events": [],
        "limitation": "Stałe archiwum 27.10.2026, nie historia na żywo. Brak zweryfikowanych danych.",
    }


def _date(value: object) -> datetime:
    if type(value) is not str:
        raise ValueError("INVALID_TIMESTAMP")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or not MIN_TS <= parsed <= MAX_TS:
        raise ValueError("OUT_OF_WINDOW_TIMESTAMP")
    return parsed


def _local(value: datetime) -> str:
    return value.astimezone(ZoneInfo("Europe/Warsaw")).isoformat(timespec="milliseconds")


def project(report: object) -> dict:
    """Fail closed if observed windows and offline model disagree."""
    if type(report) is not dict:
        return unknown()
    try:
        if (report.get("schema_version") != "dns-guard-seven-series-preflight/0.1"
                or report.get("mode") != "MANUAL_FIXED_HISTORICAL_SEVEN_SERIES"
                or report.get("source") != SOURCE
                or report.get("corroborated_sampled_transitions") is not True
                or report.get("metric_count") != 7
                or type(report.get("sample_count")) is not int
                or not 2 <= report["sample_count"] <= 200
                or type(report.get("sampled_mode_change_count")) is not int
                or type(report.get("model_observed_change_count")) is not int
                or report.get("model_unknown_or_gap_count") != 0):
            return unknown()
        windows = report.get("transition_windows")
        model = report.get("model_events")
        if not isinstance(windows, list) or not isinstance(model, list):
            return unknown()
        if not (len(windows) == len(model) == report["sampled_mode_change_count"]
                == report["model_observed_change_count"] <= MAX_EVENTS):
            return unknown()
        first = _date(report.get("first_utc"))
        last = _date(report.get("last_utc"))
        if first >= last:
            return unknown()

        events = []
        prior_end = None
        for window, evidence in zip(windows, model):
            if type(window) is not dict or type(evidence) is not dict:
                return unknown()
            transition = window.get("type")
            if transition not in EXPECTED_EVENT_TYPES:
                return unknown()
            if (evidence.get("event_type") != EXPECTED_EVENT_TYPES[transition]
                    or evidence.get("status") != "OBSERVED"
                    or evidence.get("confidence") != "BOUNDED_OBSERVATION"
                    or evidence.get("coverage") != "SAMPLED_ONLY"
                    or evidence.get("effective_time_source") != "FEDORA_COLLECTION_INTERVAL"
                    or evidence.get("source") != "DNS_GUARD_COARSE_FEDORA_EXPORTER"
                    or window.get("interpretation") != "RAW_SAMPLED_MODE_ONLY_NOT_EXACT_EVENT_TIME"
                    or type(window.get("gap_seconds")) not in (int, float)):
                return unknown()
            start = _date(window.get("previous_sample_utc"))
            end = _date(window.get("next_sample_utc"))
            if (not first <= start < end <= last
                    or prior_end is not None and start < prior_end):
                return unknown()
            gap = (end - start).total_seconds()
            if not 0 < gap <= 180 or abs(gap - window["gap_seconds"]) > 0.005:
                return unknown()
            from_mode, to_mode = ("LOCAL", "BOOTSTRAP") if transition == "LOCAL_TO_BOOTSTRAP" else ("BOOTSTRAP", "LOCAL")
            if window.get("type") != transition:
                return unknown()
            # The source model timestamps are integer collection epochs, whereas
            # raw VM sample timestamps preserve milliseconds; tolerate <2s skew.
            model_start = _date(evidence.get("window_start"))
            model_end = _date(evidence.get("window_end"))
            if (abs((model_start - start).total_seconds()) > 2
                    or abs((model_end - end).total_seconds()) > 2):
                return unknown()
            reported = evidence.get("reported_transition_at")
            reported_local = None
            if reported is not None:
                moment = _date(reported)
                if not start <= moment <= end:
                    return unknown()
                reported_local = _local(moment)
            events.append({
                "type": transition,
                "from": from_mode,
                "to": to_mode,
                "window_start_local": _local(start),
                "window_end_local": _local(end),
                "reported_at_local": reported_local,
                "gap_seconds": round(gap, 3),
                "confidence": "BOUNDED_OBSERVATION",
            })
            prior_end = end

        return {
            "schema_version": SCHEMA, "kind": KIND, "mode": MODE,
            "status": "ARCHIVE_VERIFIED",
            "reason_code": "SAMPLED_TRANSITIONS_CORROBORATED",
            "source": SOURCE, "archive_start": START, "archive_end": END,
            "sample_count": report["sample_count"],
            "event_count": len(events), "events": events,
            "limitation": (
                "Archiwum 27.10.2026. Czasy są przedziałami obserwacji; "
                "znaczniki DNS Guard są zgłoszone, nie niezależnie potwierdzone. "
                "Nie dowodzi to ciągłości ani zdrowia całego DNS."
            ),
        }
    except (ValueError, KeyError, TypeError, OverflowError):
        return unknown()


def collect() -> dict:
    try:
        return project(join.read_local())
    except (OSError, ValueError, TypeError, UnicodeError, OverflowError):
        return unknown()
