#!/usr/bin/env python3
"""Validate semantic invariants in read-only iptables/routing snapshots.

This is an offline evidence helper. It does not modify firewall state and does
not turn fixture/mock results into live validation.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def rules_for(snapshot: str, chain: str) -> list[str]:
    prefix = f"-A {chain} "
    return [line.strip() for line in snapshot.splitlines() if line.startswith(prefix)]


def check(snapshot_filter: str, snapshot_nat: str, routes: str, ip_forward: str,
          ts_if: str, wan_if: str) -> list[str]:
    errors: list[str] = []

    for parent, managed in (("INPUT", "EDGE_TS_INPUT"), ("FORWARD", "EDGE_TS_FORWARD")):
        parent_rules = rules_for(snapshot_filter, parent)
        expected = f"-A {parent} -i {ts_if} -j {managed}"
        matches = [r for r in parent_rules if r == expected]
        if len(matches) != 1:
            errors.append(f"{parent}: expected exactly one managed jump, found {len(matches)}")
        if not parent_rules or parent_rules[0] != expected:
            errors.append(f"{parent}: managed jump is not first")
        managed_rules = rules_for(snapshot_filter, managed)
        if not managed_rules or managed_rules[-1] != f"-A {managed} -j DROP":
            errors.append(f"{managed}: missing terminal DROP")

    forward_rules = rules_for(snapshot_filter, "EDGE_TS_FORWARD")
    if not any("--ctstate RELATED,ESTABLISHED" in r and "-j ACCEPT" in r for r in forward_rules):
        errors.append("EDGE_TS_FORWARD: missing conntrack return-path ACCEPT")
    if not any(f"-o {wan_if} " in r and "-j ACCEPT" in r for r in forward_rules):
        errors.append(f"EDGE_TS_FORWARD: missing exit rule for WAN {wan_if}")

    prerouting = rules_for(snapshot_nat, "PREROUTING")
    expected_nat_jump = f"-A PREROUTING -i {ts_if} -j EDGE_TS_PREROUTING"
    nat_matches = [r for r in prerouting if r == expected_nat_jump]
    if len(nat_matches) != 1:
        errors.append(f"PREROUTING: expected one EDGE_TS_PREROUTING jump, found {len(nat_matches)}")

    if "ts-postrouting" in snapshot_nat:
        errors.append("NAT: competing Tailscale ts-postrouting chain present")

    if not any(line.startswith("-A POSTROUTING ") and f"-o {wan_if} " in line
               and "-j MASQUERADE" in line for line in snapshot_nat.splitlines()):
        errors.append(f"POSTROUTING: no observed MASQUERADE on effective WAN {wan_if}")

    if ip_forward.strip() != "1":
        errors.append("sysctl: net.ipv4.ip_forward is not 1")

    default_lines = [line for line in routes.splitlines() if line.startswith("default ")]
    if not any(re.search(rf"(?:^| )dev {re.escape(wan_if)}(?: |$)", line)
               for line in default_lines):
        errors.append(f"routing: default route does not use {wan_if}")

    stale = re.findall(r"(?m)^:(EDGE_TS[^ ]*) ", snapshot_filter + "\n" + snapshot_nat)
    allowed = {"EDGE_TS_INPUT", "EDGE_TS_FORWARD", "EDGE_TS_PREROUTING"}
    unexpected = sorted(set(stale) - allowed)
    if unexpected:
        errors.append("stale/unexpected EDGE_TS chains: " + ", ".join(unexpected))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--filter", required=True)
    parser.add_argument("--nat", required=True)
    parser.add_argument("--routes", required=True)
    parser.add_argument("--ip-forward", required=True)
    parser.add_argument("--ts-if", default="tailscale0")
    parser.add_argument("--wan-if", required=True)
    args = parser.parse_args()

    errors = check(
        read(args.filter), read(args.nat), read(args.routes),
        read(args.ip_forward), args.ts_if, args.wan_if
    )
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: firewall snapshot semantic invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
