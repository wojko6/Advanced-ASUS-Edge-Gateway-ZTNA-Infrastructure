#!/bin/sh
# Rebuild the vetted ARMv7 static supervisor in Podman or Docker and compare bytes.
# Never deploys to router. Build environment: Debian Bookworm armel cross toolchain.
set -eu
ROOT="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
SOURCE="$ROOT/router/src/edge-dns-supervisor.c"
PACKAGED="$ROOT/router/bin/edge-dns-supervisor"
OUT="${EDGE_SUPERVISOR_BUILD_DIR:-$HOME/.cache/pr197-armv7}"
ENGINE="${EDGE_SUPERVISOR_CONTAINER_ENGINE:-}"
if [ -z "$ENGINE" ]; then
    if command -v podman >/dev/null 2>&1; then
        ENGINE=podman
    elif command -v docker >/dev/null 2>&1; then
        ENGINE=docker
    else
        echo 'ERROR: Podman or Docker required' >&2
        exit 1
    fi
fi
case "$ENGINE" in
    podman) MOUNT_SUFFIX=:Z ;;
    docker) MOUNT_SUFFIX='' ;;
    *) echo 'ERROR: engine must be podman or docker' >&2; exit 2 ;;
esac
case "$OUT" in
    /*) ;;
    *) echo 'ERROR: EDGE_SUPERVISOR_BUILD_DIR must be absolute' >&2; exit 2 ;;
esac
[ -f "$SOURCE" ] && [ -f "$PACKAGED" ] || {
    echo 'ERROR: supervisor source or packaged ELF missing' >&2
    exit 1
}
mkdir -p "$OUT"
cp "$SOURCE" "$OUT/edge-dns-supervisor.c"
"$ENGINE" run --rm --pull=missing \
    --security-opt=no-new-privileges \
    -v "$OUT:/build$MOUNT_SUFFIX" -w /build \
    docker.io/library/debian:bookworm-slim /bin/sh -ec '
      export DEBIAN_FRONTEND=noninteractive
      apt-get update -qq
      apt-get install -y -qq --no-install-recommends \
        gcc-arm-linux-gnueabi libc6-dev-armel-cross binutils-arm-linux-gnueabi
      arm-linux-gnueabi-gcc -std=c11 -O2 -Wall -Wextra -Werror \
        -march=armv7-a -marm -mfloat-abi=soft -static \
        edge-dns-supervisor.c -o edge-dns-supervisor.armv7
      echo ARMV7_CROSS_BUILD=PASS
    '
BIN="$OUT/edge-dns-supervisor.armv7"
[ -s "$BIN" ] || { echo 'ARMV7_BUILD_OUTPUT=MISSING' >&2; exit 1; }
sha256sum "$BIN" "$PACKAGED"
if ! cmp -s "$BIN" "$PACKAGED"; then
    echo 'ARMV7_BINARY_PARITY=FAIL: compiled executable differs from reviewed package' >&2
    exit 1
fi
echo 'ARMV7_BINARY_PARITY=PASS'
echo "ARTIFACT=$BIN"
