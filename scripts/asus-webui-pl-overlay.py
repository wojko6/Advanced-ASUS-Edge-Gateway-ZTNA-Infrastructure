#!/usr/bin/env python3
"""Audit and build a version-pinned Polish ASUSWRT WebUI dictionary overlay."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

EXPECTED_EN_SHA256 = "6ef410026f3237503d245ce6fd5b4e6c82ee7887deda62f10cb34b6454c12567"
EXPECTED_PL_SHA256 = "cad0a4766bfd2bb7e0faa0fc63638b84ab65ee30bc56b0b5755b7e32f7506719"
EXPECTED_LINE_COUNT = 4686
HEADER_LINES = 26

TAG_RE = re.compile(r"<[^>]+>")
ENTITY_RE = re.compile(r"&(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);")
PRINTF_RE = re.compile(r"%(?:\d+\$)?[@sdifuxX]|%[0-9.]*[a-zA-Z]")
DOLLAR_RE = re.compile(r"\$[A-Za-z0-9_]+\$")
ZV_RE = re.compile(r"\bZV[A-Z0-9_]+VZ\b")
ESCAPED_NEWLINE_RE = re.compile(r"\\n")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")

# Small stop-list used only to rank mixed-language candidates. It never changes
# dictionary content automatically.
ENGLISH_STOPWORDS = {
    "the", "and", "you", "your", "this", "that", "with", "from", "for", "are",
    "will", "can", "please", "click", "select", "network", "router", "enable",
    "disable", "settings", "setting", "internet", "wireless", "connection",
    "server", "client", "mode", "status", "default", "access", "use", "using",
    "when", "then", "if", "to", "of", "is", "in", "on", "or", "be", "as",
}


class OverlayError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_lines(path: Path) -> tuple[list[str], bool]:
    raw = path.read_bytes()
    trailing_newline = raw.endswith(b"\n")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OverlayError(f"{path}: not valid UTF-8: {exc}") from exc
    return text.splitlines(), trailing_newline


def structural_signature(value: str) -> dict[str, list[str]]:
    return {
        "tags": TAG_RE.findall(value),
        "entities": ENTITY_RE.findall(value),
        "printf": PRINTF_RE.findall(value),
        "dollar": DOLLAR_RE.findall(value),
        "zv": ZV_RE.findall(value),
        "escaped_newlines": ESCAPED_NEWLINE_RE.findall(value),
    }


def assert_baseline(en_path: Path, pl_path: Path) -> tuple[list[str], list[str], bool]:
    en_sha = sha256(en_path)
    pl_sha = sha256(pl_path)
    if en_sha != EXPECTED_EN_SHA256:
        raise OverlayError(
            f"EN baseline mismatch: expected {EXPECTED_EN_SHA256}, got {en_sha}"
        )
    if pl_sha != EXPECTED_PL_SHA256:
        raise OverlayError(
            f"PL baseline mismatch: expected {EXPECTED_PL_SHA256}, got {pl_sha}"
        )

    en_lines, en_nl = read_lines(en_path)
    pl_lines, pl_nl = read_lines(pl_path)

    if len(en_lines) != EXPECTED_LINE_COUNT or len(pl_lines) != EXPECTED_LINE_COUNT:
        raise OverlayError(
            f"line-count mismatch: EN={len(en_lines)} PL={len(pl_lines)} "
            f"expected={EXPECTED_LINE_COUNT}"
        )
    if not en_lines[0].startswith("\ufeff"):
        raise OverlayError("EN dictionary lost UTF-8 BOM")
    if not pl_lines[0].startswith("\ufeff"):
        raise OverlayError("PL dictionary lost UTF-8 BOM")
    if en_nl != pl_nl:
        raise OverlayError("EN/PL trailing-newline contract differs")
    return en_lines, pl_lines, pl_nl


def load_manifest(path: Path) -> dict:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OverlayError(f"cannot load manifest {path}: {exc}") from exc

    if manifest.get("schema") != 1:
        raise OverlayError("unsupported manifest schema")

    baseline = manifest.get("baseline", {})
    expected = {
        "en_sha256": EXPECTED_EN_SHA256,
        "pl_sha256": EXPECTED_PL_SHA256,
        "line_count": EXPECTED_LINE_COUNT,
    }
    for key, value in expected.items():
        if baseline.get(key) != value:
            raise OverlayError(f"manifest baseline {key} mismatch")

    overrides = manifest.get("overrides")
    if not isinstance(overrides, dict) or not overrides:
        raise OverlayError("manifest overrides must be a non-empty object")

    return manifest


def validate_override(line_no: int, source: str, replacement: str) -> None:
    if line_no <= HEADER_LINES or line_no > EXPECTED_LINE_COUNT:
        raise OverlayError(f"override line {line_no} is outside the patchable range")
    if "\n" in replacement or "\r" in replacement:
        raise OverlayError(f"override line {line_no} contains a literal newline")
    if structural_signature(source) != structural_signature(replacement):
        raise OverlayError(
            f"override line {line_no} changes markup/entity/placeholder structure\n"
            f"source:      {structural_signature(source)}\n"
            f"replacement: {structural_signature(replacement)}"
        )


def audit(en_path: Path, pl_path: Path) -> int:
    en_lines, pl_lines, _ = assert_baseline(en_path, pl_path)

    identical: list[int] = []
    mixed: list[tuple[int, float, str]] = []
    structure_drift: list[int] = []

    for index, (en_value, pl_value) in enumerate(zip(en_lines, pl_lines), start=1):
        if index <= HEADER_LINES:
            continue
        if en_value == pl_value:
            identical.append(index)
        if structural_signature(en_value) != structural_signature(pl_value):
            structure_drift.append(index)

        en_words = [w.lower() for w in WORD_RE.findall(en_value)]
        pl_words = [w.lower() for w in WORD_RE.findall(pl_value)]
        if en_words and en_value != pl_value:
            en_signal = [w for w in en_words if w in ENGLISH_STOPWORDS]
            if en_signal:
                retained = sum(1 for w in en_signal if w in pl_words)
                ratio = retained / len(en_signal)
                if ratio >= 0.5:
                    mixed.append((index, ratio, pl_value))

    print(f"EN_SHA256={sha256(en_path)}")
    print(f"PL_SHA256={sha256(pl_path)}")
    print(f"LINE_COUNT={len(en_lines)}")
    print(f"IDENTICAL_AFTER_HEADER={len(identical)}")
    print(
        "IDENTICAL_PERCENT="
        f"{(len(identical) / (len(en_lines) - HEADER_LINES)) * 100:.2f}%"
    )
    print(f"MIXED_LANGUAGE_CANDIDATES={len(mixed)}")
    print(f"STRUCTURE_DRIFT_LINES={len(structure_drift)}")

    if structure_drift:
        print("STRUCTURE_DRIFT_LINE_NUMBERS=" + ",".join(map(str, structure_drift)))
    return 0


def build(en_path: Path, pl_path: Path, manifest_path: Path, output: Path) -> int:
    en_lines, pl_lines, trailing_newline = assert_baseline(en_path, pl_path)
    manifest = load_manifest(manifest_path)

    overrides = manifest["overrides"]
    applied = 0

    for key in sorted(overrides, key=lambda item: int(item)):
        try:
            line_no = int(key)
        except ValueError as exc:
            raise OverlayError(f"invalid manifest line number: {key!r}") from exc

        replacement = overrides[key]
        if not isinstance(replacement, str):
            raise OverlayError(f"override line {line_no} must be a string")

        validate_override(line_no, en_lines[line_no - 1], replacement)
        pl_lines[line_no - 1] = replacement
        applied += 1

    if len(pl_lines) != EXPECTED_LINE_COUNT:
        raise OverlayError("output line count changed unexpectedly")

    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(output.name + ".tmp")
    text = "\n".join(pl_lines)
    if trailing_newline:
        text += "\n"
    tmp.write_bytes(text.encode("utf-8"))
    tmp.replace(output)

    out_lines, out_nl = read_lines(output)
    if len(out_lines) != EXPECTED_LINE_COUNT:
        raise OverlayError("generated dictionary line count is invalid")
    if out_nl != trailing_newline:
        raise OverlayError("generated dictionary trailing-newline contract changed")
    if not out_lines[0].startswith("\ufeff"):
        raise OverlayError("generated dictionary lost UTF-8 BOM")

    print(f"APPLIED_OVERRIDES={applied}")
    print(f"OUTPUT={output}")
    print(f"OUTPUT_SHA256={sha256(output)}")
    return 0


def verify(en_path: Path, pl_path: Path, manifest_path: Path, candidate: Path) -> int:
    en_lines, _, trailing_newline = assert_baseline(en_path, pl_path)
    manifest = load_manifest(manifest_path)
    candidate_lines, candidate_nl = read_lines(candidate)

    if len(candidate_lines) != EXPECTED_LINE_COUNT:
        raise OverlayError(
            f"candidate line count {len(candidate_lines)} != {EXPECTED_LINE_COUNT}"
        )
    if candidate_nl != trailing_newline:
        raise OverlayError("candidate trailing-newline contract differs")
    if not candidate_lines[0].startswith("\ufeff"):
        raise OverlayError("candidate lost UTF-8 BOM")

    for key, replacement in manifest["overrides"].items():
        line_no = int(key)
        validate_override(line_no, en_lines[line_no - 1], replacement)
        if candidate_lines[line_no - 1] != replacement:
            raise OverlayError(f"candidate line {line_no} does not match manifest")

    print("VERIFY=PASS")
    print(f"CANDIDATE_SHA256={sha256(candidate)}")
    print(f"APPLIED_OVERRIDES={len(manifest['overrides'])}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Audit/build a version-pinned Polish ASUSWRT dictionary overlay."
    )
    sub = p.add_subparsers(dest="command", required=True)

    audit_p = sub.add_parser("audit", help="Audit the pinned EN/PL baseline")
    audit_p.add_argument("en", type=Path)
    audit_p.add_argument("pl", type=Path)

    build_p = sub.add_parser("build", help="Build a patched PL dictionary")
    build_p.add_argument("en", type=Path)
    build_p.add_argument("pl", type=Path)
    build_p.add_argument("output", type=Path)
    build_p.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "config"
        / "asus-webui-pl-overrides.json",
    )

    verify_p = sub.add_parser("verify", help="Verify a generated PL dictionary")
    verify_p.add_argument("en", type=Path)
    verify_p.add_argument("pl", type=Path)
    verify_p.add_argument("candidate", type=Path)
    verify_p.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "config"
        / "asus-webui-pl-overrides.json",
    )
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "audit":
            return audit(args.en, args.pl)
        if args.command == "build":
            return build(args.en, args.pl, args.manifest, args.output)
        if args.command == "verify":
            return verify(args.en, args.pl, args.manifest, args.candidate)
        raise OverlayError(f"unsupported command: {args.command}")
    except OverlayError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
