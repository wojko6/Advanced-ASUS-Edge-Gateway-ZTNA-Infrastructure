#!/usr/bin/env python3
"""Offline-only V0.4 router DNS probe status projection.

No I/O, network, imports from the running HCC server, writes, or subprocesses.
Input must already be verified by a future separate fixed-query source adapter:
the one intended job, exactly one series, no untrusted labels, valid timestamps.
This model alone does NOT verify that provenance or query any metric source.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math

TTL_SECONDS = 120  # provisional proposal, NOT measured/approved for deployment
FIELDS = frozenset(("probe_success", "sample_age_seconds"))
LIMITATION = (
    "One Blackbox UDP A-record query for example.com via the configured "
    "router DNS resolver; not Pi-hole/Unbound health, DNSSEC, all clients, "
    "the router's overall uptime, or continuous DNS availability."
)


def _numeric(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (float, int))
        and math.isfinite(value)
    )


def project(values: object, now: datetime) -> dict:
    """Fail closed: OK means only *one fresh successful DNS probe*.

    The caller must authenticate and uniquely identify the input series.
    This deliberately pure function does not fetch/verify Prometheus responses.
    """
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")

    result = {
        "schema_version": "0.4-offline",
        "kind": "router-dns-probe",
        "mode": "offline-fixture-only",
        "source": "candidate VictoriaMetrics / Blackbox job internet_dns",
        "observed_at": now.astimezone(timezone.utc).replace(
            microsecond=0
        ).isoformat().replace("+00:00", "Z"),
        "status": "UNKNOWN",
        "reason_code": "EVIDENCE_NOT_VERIFIED",
        "probe_success": None,
        "sample_age_seconds": None,
        "ttl_seconds": TTL_SECONDS,
        "limitation": LIMITATION,
    }

    if not isinstance(values, dict) or set(values) != FIELDS:
        return result

    probe = values["probe_success"]
    age = values["sample_age_seconds"]
    if not _numeric(probe) or not _numeric(age):
        return result
    if probe not in (0, 1) or not 0 <= age <= 86400:
        return result

    result["sample_age_seconds"] = round(float(age), 1)
    if age > TTL_SECONDS:
        result.update(status="STALE", reason_code="DNS_PROBE_SAMPLE_TOO_OLD")
        return result

    result["probe_success"] = bool(probe)
    if probe == 1:
        result.update(status="OK", reason_code="ONE_DNS_PROBE_SUCCEEDED")
    else:
        # Failure of one specific probe does NOT prove that the router is DOWN.
        result.update(status="DEGRADED", reason_code="ONE_DNS_PROBE_FAILED")
    return result
