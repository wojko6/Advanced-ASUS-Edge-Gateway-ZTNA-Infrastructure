#!/usr/bin/env python3
"""V0.4 opt-in, local VictoriaMetrics-only router DNS Blackbox evidence reader.

Exactly three source-owned queries. No router contact, shell, file writing,
credential handling, environment-configured URLs, proxy or raw label exposure.
This collector proves only one timestamped DNS Blackbox result, not service health.
"""
from __future__ import annotations

import datetime as dt
import http.client
import json
import math
from urllib.parse import quote

import v02_local_server as v02
import v04_router_dns_model as model

VM = "127.0.0.1"
PORT = 8428
TIMEOUT = 2
MAX_REPLY_BYTES = 8192
QUERIES = (
    ("count", 'count(probe_success{job="internet_dns"})'),
    ("success", 'sum(probe_success{job="internet_dns"})'),
    ("age", 'max(time()-timestamp(probe_success{job="internet_dns"}))'),
)
ALLOWED = frozenset(query for _, query in QUERIES)


def get_fixed(query: str) -> bytes:
    if query not in ALLOWED:
        raise ValueError("metric query not allowlisted")
    conn = http.client.HTTPConnection(VM, PORT, timeout=TIMEOUT)
    try:
        path = "/api/v1/query?query=" + quote(query, safe="")
        conn.request("GET", path, headers={
            "Accept": "application/json", "Connection": "close",
        })
        resp = conn.getresponse()
        if resp.status != 200:
            raise ValueError("source unavailable")
        data = resp.read(MAX_REPLY_BYTES + 1)
        if len(data) > MAX_REPLY_BYTES:
            raise ValueError("oversized source")
        return data
    finally:
        conn.close()


def project_live(values: object, now: dt.datetime) -> dict:
    """Use the separately tested pure model, mark only this adapter as LIVE."""
    projected = model.project(values, now)
    projected["schema_version"] = "0.4"
    projected["mode"] = "manual-local-vm-readonly"
    projected["source"] = "VictoriaMetrics / Blackbox internet_dns / fixed aggregates"
    return projected


def collect(read=get_fixed, clock=None) -> dict:
    if clock is None:
        clock = lambda: dt.datetime.now(dt.timezone.utc)
    current = clock()
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("timezone-aware clock required")
    try:
        parsed = {}
        for key, query in QUERIES:
            # Original V0.2 parser requires a unique label-free scalar, finite
            # number and sample evaluation time matching the local request clock.
            raw = read(query)
            parsed[key] = v02.promql_scalar_from_json(raw, clock().timestamp())
        # count==1 proves the one-series aggregate cardinality for this instant;
        # other reads are near-time, not an atomic snapshot.
        if parsed["count"] != 1 or parsed["success"] not in (0, 1):
            return project_live({}, clock())
        return project_live({
            "probe_success": parsed["success"],
            "sample_age_seconds": parsed["age"],
        }, clock())
    except (OSError, ValueError, TypeError, KeyError, OverflowError,
            http.client.HTTPException, TimeoutError, json.JSONDecodeError):
        return project_live({}, clock())
