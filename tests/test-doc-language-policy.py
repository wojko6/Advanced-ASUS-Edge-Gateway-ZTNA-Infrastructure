#!/usr/bin/env python3
"""Fail when the EN/PL documentation entry points drift out of their contract.

This is intentionally an index/path policy check, not automated translation
or operational-safety validation. The normal Markdown link checker runs too.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "docs/pl/README.md"

# Existing, stable public Polish guide paths. Do not rename them implicitly.
POLISH_GUIDES = (
    "docs/deployment-pl.md",
    "docs/printer-setup-lan-pl.md",
    "docs/printer-setup-tailscale-pl.md",
)

RELATED_ENGLISH = (
    "docs/operations.md",
    "docs/PRINTER-HARDENING.md",
    "docs/firewall-policy.md",
    "docs/router-disaster-recovery.md",
)

POLICY_REFERENCES = {
    "README.md": ("docs/pl/README.md", "docs/language-policy.md"),
    "CONTRIBUTING.md": ("docs/pl/README.md", "docs/language-policy.md"),
    "docs/documentation-model.md": ("docs/pl/README.md", "docs/language-policy.md"),
    "docs/language-policy.md": ("docs/pl/README.md", "docs/documentation-model.md"),
}

PENDING_DR_PR = (
    "https://github.com/wojko6/"
    "Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/205"
)


def check() -> list[str]:
    failures: list[str] = []

    def read(path: str) -> str:
        target = ROOT / path
        if not target.is_file():
            failures.append(f"Missing required file: {path}")
            return ""
        return target.read_text(encoding="utf-8")

    index = read("docs/pl/README.md")
    policy = read("docs/language-policy.md")

    for path in POLISH_GUIDES + RELATED_ENGLISH:
        target = ROOT / path
        if not target.is_file():
            failures.append(f"Referenced guide missing: {path}")
            continue
        relative = Path(os.path.relpath(target, INDEX_PATH.parent)).as_posix()
        if f"({relative})" not in index:
            failures.append(f"Polish index missing reference to {path} ({relative})")

    if PENDING_DR_PR not in index:
        failures.append("Polish index must disclose in-review PR #205")

    if "not a" not in policy.lower() or "operator adaptation" not in policy.lower():
        failures.append("Language policy must distinguish translated/adapted operational scope")

    for source, targets in POLICY_REFERENCES.items():
        text = read(source)
        for target in targets:
            relative = Path(os.path.relpath(ROOT / target, (ROOT / source).parent)).as_posix()
            if f"({relative})" not in text:
                failures.append(f"{source} must reference {target} via ({relative})")

    return failures


def main() -> int:
    failures = check()
    if failures:
        print("EN_PL_DOCUMENTATION_POLICY=FAIL")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("EN_PL_DOCUMENTATION_POLICY=PASS")
    print("NOTE=Index/source checks only; semantic PL/EN parity requires human review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
