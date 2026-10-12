#!/usr/bin/env python3
"""Reconcile live RouterCloud storage hotfix with PR #224 without touching production.

Reads a LOCAL SSH-exported copy of production index.js. It never contacts the
router, edits active source files, or deploys anything. Fail closed if there is
any unexplained production drift outside setupStorageInfo().
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

BASE_COMMIT = "d68efba6c4e995408b63160893bed63a097e322c"
ASSET = "router/routercloud/webui/metro/index.js"
STORAGE_START = "function setupStorageInfo() {"
STORAGE_END = "\n// ROUTERCLOUD_BACKUP_TILE_V1"
NAV_MARKER = "ROUTERCLOUD_HOME_AJAX_V1"
EXPECTED_LIVE_SHA256 = "d5052ea33917bad9314a49792bc555dd2e7ce2a3f2532aaff3b83c23e4c593b4"
STORAGE_MARKERS = ("wolne", "łącznie", "niedostępne")


class ReconcileRejected(ValueError):
    pass


def parts(code: str) -> tuple[str, str, str]:
    if code.count(STORAGE_START) != 1:
        raise ReconcileRejected("STORAGE_FUNCTION_AMBIGUOUS")
    start = code.index(STORAGE_START)
    end = code.find(STORAGE_END, start)
    if end == -1:
        raise ReconcileRejected("STORAGE_END_MARKER_MISSING")
    return code[:start], code[start:end], code[end:]


def reconcile(base: str, feature: str, live: str) -> str:
    bp, bs, bt = parts(base)
    fp, fs, ft = parts(feature)
    lp, ls, lt = parts(live)

    # Exact matching protects all production-only modifications outside
    # storage, including whitespace and unknown behavioral changes.
    if lp != bp or lt != bt:
        raise ReconcileRejected("LIVE_UNEXPECTED_CHANGES_OUTSIDE_STORAGE")

    if fs != bs:
        raise ReconcileRejected("FEATURE_CHANGED_STORAGE_FUNCTION")

    if ls == bs:
        raise ReconcileRejected("LIVE_STORAGE_HOTFIX_NOT_FOUND")

    if not all(marker in ls for marker in STORAGE_MARKERS):
        raise ReconcileRejected("LIVE_STORAGE_MARKER_MISSING")

    if NAV_MARKER not in feature:
        raise ReconcileRejected("FEATURE_HOME_AJAX_MARKER_MISSING")

    output = fp + ls + ft

    if NAV_MARKER not in output:
        raise ReconcileRejected("CANDIDATE_HOME_AJAX_MARKER_MISSING")

    if any(marker not in parts(output)[1] for marker in STORAGE_MARKERS):
        raise ReconcileRejected("CANDIDATE_STORAGE_MARKER_MISSING")

    return output


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("live", type=Path, help="read-only SSH-exported index.js")
    parser.add_argument("--out", type=Path, required=True, help="NEW local candidate file")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent.parent
    asset = repo / ASSET

    try:
        live_bytes = args.live.read_bytes()
        live = live_bytes.decode("utf-8")
        if digest(live_bytes) != EXPECTED_LIVE_SHA256:
            raise ReconcileRejected("LIVE_SHA256_CHANGED_REAUDIT_REQUIRED")
        feature = asset.read_text(encoding="utf-8")
        base_bytes = subprocess.check_output(
            ["git", "-C", str(repo), "show", f"{BASE_COMMIT}:{ASSET}"],
            stderr=subprocess.DEVNULL,
        )
        base = base_bytes.decode("utf-8")
        output = reconcile(base, feature, live)
        target = args.out.resolve()
        if target in (args.live.resolve(), asset.resolve()):
            raise ReconcileRejected("WOULD_OVERWRITE_SOURCE_OR_LIVE_COPY")
        if target.exists():
            raise ReconcileRejected("CANDIDATE_OUTPUT_ALREADY_EXISTS")
        if not target.parent.is_dir():
            raise ReconcileRejected("CANDIDATE_OUTPUT_PARENT_MISSING")
        output_bytes = output.encode("utf-8")
        target.write_bytes(output_bytes)
        target.chmod(0o600)
    except (ReconcileRejected, UnicodeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"ROUTERCLOUD_RECONCILE=REJECTED reason={exc}")
        return 1

    print(f"BASE_SHA256={digest(base_bytes)}")
    print(f"LIVE_SHA256={digest(live_bytes)}")
    print(f"FEATURE_SHA256={digest(feature.encode('utf-8'))}")
    print("LIVE_OUTSIDE_STORAGE_MATCHES_BASE=PASS")
    print("LIVE_STORAGE_HOTFIX_RETAINED=PASS")
    print("HOME_AJAX_FEATURE_RETAINED=PASS")
    print(f"CANDIDATE_SHA256={digest(output_bytes)}")
    print(f"CANDIDATE_BYTES={len(output_bytes)}")
    print("ROUTERCLOUD_RECONCILE=PASS")
    print("PRODUCTION_CHANGED=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
