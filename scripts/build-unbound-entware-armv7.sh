#!/bin/sh
# Workstation-only reproduction of the September 2026 Entware Unbound build.
# Does not install, restart or contact the reference ASUS router.
set -eu

ROOT="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
RECIPE_DIR="$ROOT/scripts/unbound"
MODE="${1:---check}"
ENGINE="${EDGE_UNBOUND_CONTAINER_ENGINE:-}"
OUT="${EDGE_UNBOUND_BUILD_DIR:-$HOME/.cache/asus-edge-unbound-armv7}"
JOBS="${EDGE_UNBOUND_BUILD_JOBS:-2}"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

case "$MODE" in --check|--build) ;; *) fail 'Usage: sh scripts/build-unbound-entware-armv7.sh [--check|--build]' ;; esac

# No secret, router mount or production daemon is accessed by this script.
for file in Dockerfile build-in-container.sh verify-artifacts.py HISTORICAL-SHA256SUMS.txt; do
    [ -s "$RECIPE_DIR/$file" ] || fail "missing recipe: $file"
done
sh -n "$RECIPE_DIR/build-in-container.sh" || fail 'invalid inner build script'
[ "$(wc -l < "$RECIPE_DIR/HISTORICAL-SHA256SUMS.txt" | tr -d ' ')" = 7 ] ||
    fail 'historical manifest must list exactly seven IPKs'
grep -Fq 'ENTWARE_COMMIT=969c703e6fd8b2ad84d82affaeb14b48d1fcb105' "$RECIPE_DIR/build-in-container.sh" ||
    fail 'Entware snapshot pin missing'
grep -Fq 'PACKAGES_COMMIT=b6a6f2962f62882b76dfe45f9f9e1238cd9b74fd' "$RECIPE_DIR/build-in-container.sh" ||
    fail 'package-feed snapshot pin missing'
grep -Fq 'PKG_RELEASE:=1' "$RECIPE_DIR/build-in-container.sh" ||
    fail 'historic package release pin missing'
if [ "$MODE" = --check ]; then
    echo 'UNBOUND_RECIPE_PREFLIGHT=PASS (static only; no build executed)'
    exit 0
fi

case "$OUT" in
    /*) ;;
    *) fail 'EDGE_UNBOUND_BUILD_DIR must be an absolute path' ;;
esac
case "$OUT" in
    *' '*) fail 'build path must not contain spaces (Entware requirement)' ;;
esac
case "$JOBS" in ''|*[!0-9]*|0) fail 'EDGE_UNBOUND_BUILD_JOBS must be a positive integer' ;; esac
[ "$OUT" != / ] || fail 'unsafe build root'
[ ! -e "$OUT/Entware" ] && [ ! -e "$OUT/artifacts" ] ||
    fail "build directory is not clean: $OUT (choose a new directory; nothing removed)"

if [ -z "$ENGINE" ]; then
    if command -v podman >/dev/null 2>&1; then ENGINE=podman
    elif command -v docker >/dev/null 2>&1; then ENGINE=docker
    else fail 'Podman or Docker required'
    fi
fi
case "$ENGINE" in podman|docker) ;; *) fail 'engine must be podman or docker' ;; esac
mkdir -p "$OUT"
IMAGE='localhost/asus-edge-unbound-builder:bookworm-py2'
"$ENGINE" build --file "$RECIPE_DIR/Dockerfile" --tag "$IMAGE" "$RECIPE_DIR"
# Constrain the build to a disposable workstation path. No router access required.
"$ENGINE" run --rm --security-opt=no-new-privileges \
    --user "$(id -u):$(id -g)" \
    --env HOME=/tmp \
    --env "BUILD_JOBS=$JOBS" \
    --volume "$OUT:/work:Z" \
    --volume "$RECIPE_DIR:/recipe:ro,Z" \
    --workdir /work \
    "$IMAGE" /bin/sh /recipe/build-in-container.sh
echo "UNBOUND_BUILD_OUTPUT=$OUT/artifacts"
echo 'Do not install on router: review artifact hashes, dependencies and rollback first.'
