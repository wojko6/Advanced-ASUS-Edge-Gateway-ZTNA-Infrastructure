#!/usr/bin/env python3
"""Check narrow, evidence-backed *current-state* documentation contracts.

Intentionally excludes dated worklogs, historical research, and undated
production observations not verified by a live test. This is a semantic
tripwire, not proof of router deployment or Grafana notification delivery.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def contents(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def check() -> list[str]:
    failures: list[str] = []
    operations = contents("docs/operations.md")
    monitoring = contents("monitoring/README.md")
    roadmap = contents("docs/roadmap.md")
    runbook = contents("docs/dns-guard-v3.2-live-validation.md")
    alerting = contents("monitoring/grafana/provisioning/alerting/asus-tuf-alerts.yml")
    contacts = contents("monitoring/grafana/provisioning/alerting/asus-email-contact.yml")
    model = contents("docs/documentation-model.md")
    architecture = contents("docs/architecture/dns-enforcement-flow.md")

    if not re.search(r"current validated router-system resolver baseline: DNS Guard v3\.2", operations, re.I):
        failures.append("operations.md must identify v3.2 as the accepted router-system baseline")
    if "PR #197" not in operations or "v3.2 candidate" in operations.lower():
        failures.append("operations.md must cite merged PR #197 and avoid outdated v3.2 candidate language")
    if "COMPLETED / HISTORICAL" not in "\n".join(runbook.splitlines()[:8]):
        failures.append("old v3.2 live-acceptance runbook requires a visible historical notice")
    if "Do not execute the fault-injection" not in runbook:
        failures.append("historical live runbook requires an explicit no-routine-execution gate")
    if "**Issue #178 is CLOSED**" not in monitoring:
        failures.append("monitoring README must show bounded #178 closure")
    if "grouping/anti-flap" not in monitoring.lower() or "unverified follow-ups" not in monitoring.lower():
        failures.append("monitoring README must preserve outstanding notification risks")
    if re.search(r"^\s*-\s*#178\s*[—-]", roadmap, re.M):
        failures.append("roadmap must not list closed #178 as an open bullet")
    if "Closed with bounded acceptance" not in roadmap or "[#178]" not in roadmap:
        failures.append("roadmap must separate #178 closure from residual work")

    # 15 file-based rules alone do not verify live Grafana provisioning.
    uids = re.findall(r"^\s*-\s*uid:\s*([a-zA-Z0-9_]+)\s*$", alerting, re.M)
    if len(uids) != 15 or len(set(uids)) != 15:
        failures.append(f"Grafana source baseline should have 15 unique UIDs, got {len(uids)}")
    receivers = re.findall(r"^\s*receiver:\s*(.+?)\s*$", alerting, re.M)
    if len(receivers) != 15 or set(receivers) != {"ASUS Edge Gateway Email"}:
        failures.append("Grafana YAML must give each of 15 alerts the documented Email receiver")
    if "type: email" not in contacts:
        failures.append("source-controlled Grafana contact must still explicitly have Email")
    if "source-versus-live provisioning parity" not in monitoring:
        failures.append("source/live Email+Telegram drift must not be documented as fixed")

    if "ASUS CORE v1.0" not in model or "`VERSION`" not in model:
        failures.append("documentation model must distinguish milestone from software release")
    if "## Client DNS continuity boundary" not in architecture or "No second" not in architecture:
        failures.append("DNS architecture must preserve the client failover non-deployment boundary")
    return failures


def main() -> int:
    failures = check()
    if failures:
        print("DOCUMENT_CURRENT_STATE=FAIL")
        for item in failures:
            print(" - " + item)
        return 1
    print("DOCUMENT_CURRENT_STATE=PASS")
    print("SCOPE=Source docs/YAML checks only; no production deployment proof")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
