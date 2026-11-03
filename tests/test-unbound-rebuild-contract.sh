#!/bin/sh
# Fast, offline regression: no Podman, network access or router changes.
set -eu
ROOT="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
RECIPE="$ROOT/scripts/unbound"
FAIL=0

bad() { echo "FAIL: $1" >&2; FAIL=1; }
sh -n "$ROOT/scripts/build-unbound-entware-armv7.sh" || bad 'orchestrator syntax'
sh -n "$RECIPE/build-in-container.sh" || bad 'inner build syntax'
python3 - "$RECIPE/verify-artifacts.py" <<'PY_CHECK'
import ast, sys
from pathlib import Path
ast.parse(Path(sys.argv[1]).read_text())
print('UNBOUND_IPK_VERIFIER_SYNTAX=PASS')
PY_CHECK
sh "$ROOT/scripts/build-unbound-entware-armv7.sh" --check || bad 'recipe static preflight'

grep -Fq 'b62c0e7937551d0cc02b8fd5cb0f544f9405bafc9a54d3808ed4594812edef43' "$RECIPE/Dockerfile" || bad 'Python2 source pin'
grep -Fq '35a6dc0e425a9282c3426d9a3043144011bf0534aed4b73ab62c52aee0af1503' "$RECIPE/build-in-container.sh" || bad 'Unbound upstream source pin'
grep -Fq 'git -C feeds/packages checkout --detach "$PACKAGES_COMMIT"' "$RECIPE/build-in-container.sh" || bad 'pinned feed checkout'
grep -Fq 'make package/feeds/packages/unbound/compile' "$RECIPE/build-in-container.sh" || bad 'build target'
grep -Fq 'UNBOUND_HISTORICAL_BYTE_PARITY=NOT_PROVEN' "$RECIPE/build-in-container.sh" || bad 'parity claim boundary'
grep -Fq 'ROUTER_DEPLOYMENT=NOT_PERFORMED' "$RECIPE/build-in-container.sh" || bad 'deployment separation'

python3 - "$RECIPE/HISTORICAL-SHA256SUMS.txt" <<'PY'
import re
import sys
from pathlib import Path
source = Path(sys.argv[1])
rows = source.read_text().splitlines()
expected = {
    f"{name}_1.26.1-1_armv7-3.2.ipk"
    for name in (
        "libunbound", "unbound-daemon", "unbound-anchor",
        "unbound-checkconf", "unbound-control", "unbound-control-setup",
        "unbound-host",
    )
}
assert len(rows) == 7, "exactly seven historical packages required"
names = set()
for row in rows:
    match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9._-]+\.ipk)", row)
    assert match, f"invalid SHA256SUMS row: {row!r}"
    assert match.group(2) not in names, "duplicate package"
    names.add(match.group(2))
assert names == expected, f"wrong artifact set: {expected ^ names}"
print("UNBOUND_HISTORICAL_MANIFEST=PASS")
PY

[ "$FAIL" -eq 0 ] || exit 1
echo 'UNBOUND_REBUILD_STATIC_TEST=PASS'
