#!/usr/bin/env python3
"""Fail CI when repository-local Markdown links point to missing paths."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
FENCED_CODE = re.compile(r"(^|\n)(?:```|~~~).*?(?:\n```|\n~~~)", re.DOTALL)
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)", re.MULTILINE)


def extract_target(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<"):
        end = value.find(">")
        return value[1:end] if end != -1 else value[1:]
    return value.split(maxsplit=1)[0]


def resolve_local(source: Path, raw: str) -> Path | None:
    target = extract_target(raw)
    if not target or target.startswith("#"):
        return None

    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None

    path_text = unquote(parsed.path)
    if not path_text:
        return None

    candidate = ROOT / path_text.lstrip("/") if path_text.startswith("/") else source.parent / path_text
    return candidate.resolve(strict=False)


def main() -> int:
    root_resolved = ROOT.resolve()
    failures: list[str] = []

    for source in sorted(ROOT.rglob("*.md")):
        if ".git" in source.parts:
            continue

        text = source.read_text(encoding="utf-8")
        text = FENCED_CODE.sub("\n", text)
        targets = [match.group(1) for match in INLINE_LINK.finditer(text)]
        targets.extend(match.group(1) for match in REFERENCE_LINK.finditer(text))

        for raw in targets:
            candidate = resolve_local(source, raw)
            if candidate is None:
                continue

            try:
                candidate.relative_to(root_resolved)
            except ValueError:
                failures.append(f"{source.relative_to(ROOT)}: link escapes repository: {raw}")
                continue

            if not candidate.exists():
                failures.append(
                    f"{source.relative_to(ROOT)}: missing local target {raw} -> "
                    f"{candidate.relative_to(ROOT)}"
                )

    if failures:
        print("FAIL: broken repository-local Markdown links:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    print("PASS: repository-local Markdown links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
