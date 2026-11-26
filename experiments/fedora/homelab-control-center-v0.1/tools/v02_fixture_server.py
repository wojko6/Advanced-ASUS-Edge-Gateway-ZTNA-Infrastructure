#!/usr/bin/env python3
"""Deliberate V0.2 fault simulator. Never contacts VictoriaMetrics or ASUS.

Manual demo: python3 -B tools/v02_fixture_server.py --serve-fixture --case partial
Then visit http://127.0.0.1:8789/. Stop with Ctrl+C.
Only fixed synthetic status summaries, no log/source extraction, no disk changes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
from http.server import HTTPServer

import v02_local_server as backend

PORT = 8789
CASES = ("ok", "partial", "down", "stale", "unavailable", "expired")
VALUES = {
    "ok": {"total": 7, "healthy": 7, "age": 26.5},
    "partial": {"total": 7, "healthy": 5, "age": 26.5},
    "down": {"total": 7, "healthy": 0, "age": 26.5},
    "stale": {"total": 7, "healthy": 7, "age": 155},
}


def build_fixture(case: str, now: dt.datetime | None = None) -> dict:
    if case not in CASES:
        raise ValueError("unknown synthetic case")
    if now is None:
        now = dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("timezone-aware clock required")
    if case == "unavailable":
        value = backend.project_aggregates({}, now)
        value["reason_code"] = "SIMULATED_UNAVAILABLE"
    elif case == "expired":
        # A nominal OK snapshot is >TTL old; browser MUST downgrade to STALE.
        value = backend.project_aggregates(VALUES["ok"], now - dt.timedelta(seconds=240))
    else:
        value = backend.project_aggregates(VALUES[case], now)
    value["source"] = "SYNTHETIC_FIXTURE_NO_LIVE_MONITORING"
    return value


def serve(case: str) -> None:
    if os.geteuid() == 0:
        raise SystemExit("Refusing root execution")
    if case not in CASES:
        raise SystemExit("Invalid case")
    # Separate test process: the live provider is replaced, not merely mocked
    # in the browser. This process cannot reach the production VM API by design.
    backend.PORT = PORT
    backend.STATIC = {**backend.STATIC, "/": ("index-fixture.html", "text/html; charset=utf-8")}
    backend.get_summary = lambda: build_fixture(case)

    def no_network(*_args, **_kwargs):
        raise AssertionError("Fixture server MUST NOT request VictoriaMetrics")
    backend.fixed_vm_get = no_network

    print("HCC_V02=FIXTURE_ONLY NO_VM_REQUESTS=YES NO_ASUS=YES", flush=True)
    print("CASE=" + case + " PORT=127.0.0.1:8789", flush=True)
    print("Open http://127.0.0.1:8789/ · Ctrl+C to stop", flush=True)
    server = HTTPServer(("127.0.0.1", PORT), backend.RequestHandler)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def self_test() -> int:
    now = dt.datetime(2026, 10, 25, 13, 0, 0, tzinfo=dt.timezone.utc)
    expected = {
        "ok": "OK", "partial": "DEGRADED", "down": "DOWN",
        "stale": "STALE", "unavailable": "UNKNOWN", "expired": "OK",
    }
    failed = []
    for case, status in expected.items():
        obj = build_fixture(case, now)
        ok = obj["status"] == status and obj["source"] == "SYNTHETIC_FIXTURE_NO_LIVE_MONITORING"
        if case == "expired":
            observed = dt.datetime.fromisoformat(obj["observed_at"].replace("Z", "+00:00"))
            ok = ok and (now - observed).total_seconds() == 240
        if case == "unavailable":
            ok = ok and obj["healthy"] is None
        print("FIXTURE_" + case.upper() + "=" + ("PASS" if ok else "FAIL"))
        if not ok:
            failed.append(case)
    print(f"FIXTURE_RESULT={len(expected)-len(failed)}/{len(expected)}")
    return 0 if not failed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--serve-fixture", action="store_true")
    parser.add_argument("--case", choices=CASES)
    args = parser.parse_args()
    if args.self_test:
        if args.case:
            parser.error("--self-test does not accept --case")
        raise SystemExit(self_test())
    if args.case is None:
        parser.error("--serve-fixture requires --case")
    serve(args.case)


if __name__ == "__main__":
    main()
