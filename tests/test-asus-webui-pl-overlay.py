#!/usr/bin/env python3
"""Unit tests for the ASUS WebUI Polish overlay helper without firmware dictionaries."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "asus-webui-pl-overlay.py"
MANIFEST = REPO / "config" / "asus-webui-pl-overrides.json"

spec = importlib.util.spec_from_file_location("asus_webui_pl_overlay", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["schema"] == 1
    assert manifest["baseline"]["line_count"] == module.EXPECTED_LINE_COUNT
    assert manifest["baseline"]["en_sha256"] == module.EXPECTED_EN_SHA256
    assert manifest["baseline"]["pl_sha256"] == module.EXPECTED_PL_SHA256

    overrides = manifest["overrides"]
    assert len(overrides) >= 100
    assert len(overrides) == len(set(overrides))

    for key, value in overrides.items():
        line_no = int(key)
        assert module.HEADER_LINES < line_no <= module.EXPECTED_LINE_COUNT
        assert isinstance(value, str)
        assert value
        assert "\n" not in value
        assert "\r" not in value

    source = 'Check <a id="faq" href="$feature$">FAQ</a> for %3$@.\\n'
    good = 'Sprawdź <a id="faq" href="$feature$">FAQ</a> dla %3$@.\\n'
    bad = 'Sprawdź FAQ dla %3$@.'

    assert module.structural_signature(source) == module.structural_signature(good)
    assert module.structural_signature(source) != module.structural_signature(bad)

    try:
        module.validate_override(100, source, bad)
    except module.OverlayError:
        pass
    else:
        raise AssertionError("unsafe structural change was accepted")

    module.validate_override(100, source, good)

    print(f"ASUS_WEBUI_PL_OVERLAY_TEST=PASS overrides={len(overrides)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
