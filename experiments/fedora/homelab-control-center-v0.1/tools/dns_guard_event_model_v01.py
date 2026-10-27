#!/usr/bin/env python3
"""Issue #319: pure OFFLINE evidence model for sampled DNS Guard transitions.

No runtime collector, PromQL, HTTP, router access, filesystem I/O, notification,
service installation, browser endpoint or alert action. Input is synthetic,
prevalidated-only-like coarse exporter rows with exact allowlisted keys.
A gap or contradiction cannot become a confident transition.
"""
from __future__ import annotations

from datetime import datetime, timezone

SOURCE = "DNS_GUARD_COARSE_FEDORA_EXPORTER"
SCHEMA = "dns-guard-events-offline/0.1"
MAX_ROWS = 256
MAX_GAP_SECONDS = 180  # provisional, not a guaranteed source interval
MIN_EPOCH = 946684800  # 2000-01-01; reject nonsense clocks
MAX_EPOCH = 4102444800  # 2100-01-01
FIELDS = frozenset({
    "collection_epoch", "mode_local", "mode_bootstrap", "state_valid",
    "last_transition_epoch", "fallback_since_epoch", "fallback_transitions_total",
})
BOOT = "DNS_GUARD_BOOTSTRAP_OBSERVED"
LOCAL = "DNS_GUARD_LOCAL_RESTORED"
UNKNOWN = "DNS_GUARD_STATE_UNKNOWN"
STALE = "DNS_GUARD_TELEMETRY_STALE"


def _utc(epoch: int | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z")


def _int(value: object, lower: int, upper: int) -> bool:
    return type(value) is int and lower <= value <= upper


def _sample(row: object) -> tuple[dict | None, str]:
    if not isinstance(row, dict) or set(row) != FIELDS:
        return None, "MISSING_EXTRA_OR_NONOBJECT_FIELDS"
    c = row["collection_epoch"]
    if not _int(c, MIN_EPOCH, MAX_EPOCH):
        return None, "INVALID_COLLECTION_CLOCK"
    if not all(_int(row[k], 0, 1) for k in
               ("mode_local", "mode_bootstrap", "state_valid")):
        return None, "INVALID_MODE_FLAGS"
    if row["state_valid"] != 1 or row["mode_local"] + row["mode_bootstrap"] != 1:
        return None, "STATE_INVALID_OR_CONTRADICTORY"
    for k in ("last_transition_epoch", "fallback_since_epoch"):
        if not _int(row[k], 0, MAX_EPOCH):
            return None, "INVALID_REPORTED_TIMESTAMP"
        if row[k] > c + 5:
            return None, "FUTURE_REPORTED_TIMESTAMP"
    if not _int(row["fallback_transitions_total"], 0, 999999999):
        return None, "INVALID_FALLBACK_COUNTER"
    if row["mode_local"] == 1 and row["fallback_since_epoch"] != 0:
        return None, "LOCAL_WITH_ACTIVE_FALLBACK_MARKER"
    return dict(row), ""


def _event(kind: str, at: int | None, code: str, ordinal: int, *,
           lower_window: int | None = None, reported: int | None = None,
           duration_lower: int | None = None, duration_upper: int | None = None,
           confidence: str = "LIMITED") -> dict:
    return {
        "event_type": kind,
        "observed_at": _utc(at),
        "source": SOURCE,
        "status": "OBSERVED" if kind in (BOOT, LOCAL) else "UNVERIFIED",
        "confidence": confidence,
        "coverage": "SAMPLED_ONLY" if kind in (BOOT, LOCAL) else "INCOMPLETE",
        "reason_code": code,
        "effective_time_source": "FEDORA_COLLECTION_INTERVAL",
        "window_start": _utc(lower_window),
        "window_end": _utc(at),
        # Router-maintained timestamps can be reconciled by metrics collection;
        # show as reported, never claim this is an exact wire-level event time.
        "reported_transition_at": _utc(reported),
        "duration_lower_seconds": duration_lower,
        "duration_upper_seconds": duration_upper,
        "dedupe_key": f"{kind}:{at}" if at is not None else f"{kind}:unknown:{ordinal}",
    }


def timeline(rows: object) -> dict:
    """Reconstruct only observed transitions, never complete DNS outage history.

    Input order is source order. Out-of-order rows are not silently sorted:
    this refuses to invent causal order after late or conflicting data.
    """
    if not isinstance(rows, (tuple, list)) or len(rows) > MAX_ROWS:
        raise ValueError("bounded list/tuple required, max 256 samples")
    events = []
    previous = None
    # Bootstrap observed window: (last LOCAL before fallback or None,
    #                            first BOOT observation, last BOOT observation).
    boot_window = None

    for ordinal, row in enumerate(rows):
        current, reason = _sample(row)
        if current is None:
            events.append(_event(UNKNOWN, None, reason, ordinal))
            previous, boot_window = None, None
            continue

        at = current["collection_epoch"]
        mode = "LOCAL" if current["mode_local"] == 1 else "BOOTSTRAP"
        if previous is None:
            previous = current
            boot_window = (None, at, at) if mode == "BOOTSTRAP" else None
            continue

        previous_at = previous["collection_epoch"]
        previous_mode = "LOCAL" if previous["mode_local"] == 1 else "BOOTSTRAP"
        if at == previous_at:
            if current == previous:  # identical scrape/collector replay
                continue
            events.append(_event(UNKNOWN, at, "CONTRADICTORY_SAME_COLLECTION", ordinal))
            previous, boot_window = None, None
            continue

        if at < previous_at:
            events.append(_event(UNKNOWN, at, "OUT_OF_ORDER_SAMPLE", ordinal))
            previous, boot_window = None, None
            continue

        delta = current["fallback_transitions_total"] - previous["fallback_transitions_total"]
        if delta < 0:
            events.append(_event(UNKNOWN, at, "COUNTER_RESET_OR_REBOOT", ordinal))
            previous = current
            boot_window = (None, at, at) if mode == "BOOTSTRAP" else None
            continue

        if at - previous_at > MAX_GAP_SECONDS:
            events.append(_event(STALE, at, "COLLECTION_GAP", ordinal,
                                 lower_window=previous_at))
            previous = current
            boot_window = (None, at, at) if mode == "BOOTSTRAP" else None
            continue

        if delta > 1 or (mode == previous_mode and delta > 0) or (mode == "LOCAL" and delta > 0):
            events.append(_event(UNKNOWN, at, "COUNTER_SUGGESTS_MISSED_TRANSITION",
                                 ordinal, lower_window=previous_at))
            previous = current
            boot_window = (None, at, at) if mode == "BOOTSTRAP" else None
            continue

        if mode != previous_mode:
            reported = current["last_transition_epoch"]
            if not previous_at < reported <= at:
                reported = None
            if mode == "BOOTSTRAP":
                code = "MODE_CHANGE_OBSERVED"
                if delta != 1:
                    code = "MODE_CHANGE_COUNTER_UNCORROBORATED"
                elif current["fallback_since_epoch"] == 0:
                    code = "MODE_CHANGE_FALLBACK_START_UNRECORDED"
                events.append(_event(BOOT, at, code, ordinal,
                                     lower_window=previous_at, reported=reported,
                                     confidence="BOUNDED_OBSERVATION"))
                boot_window = (previous_at, at, at)
            else:
                # Exact fallback duration is impossible at this cadence.
                # min = span of positively observed BOOT samples;
                # max = last pre-fallback LOCAL to first restored LOCAL.
                if boot_window is None:
                    bounds = (None, None)
                else:
                    before, first_boot, last_boot = boot_window
                    bounds = (last_boot - first_boot,
                              at - before if before is not None else None)
                events.append(_event(LOCAL, at, "LOCAL_AFTER_BOOTSTRAP_OBSERVED",
                                     ordinal, lower_window=previous_at,
                                     reported=reported,
                                     duration_lower=bounds[0],
                                     duration_upper=bounds[1],
                                     confidence="BOUNDED_OBSERVATION"))
                boot_window = None
        elif mode == "BOOTSTRAP":
            if boot_window is None:
                boot_window = (None, previous_at, at)
            else:
                boot_window = (boot_window[0], boot_window[1], at)

        previous = current

    return {
        "schema_version": SCHEMA,
        "mode": "OFFLINE_FIXTURES_ONLY",
        "source": SOURCE,
        "event_count": len(events),
        "events": events,
        "input_count": len(rows),
        "limitations": "Sampled transitions only; no proof of every transition or exact outage duration.",
        "deployment_gate": "HOLD",
    }
