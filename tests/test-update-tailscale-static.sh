#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
SCRIPT="$REPO_DIR/scripts/update-tailscale.sh"

require_text() {
    text="$1"
    message="$2"
    grep -F "$text" "$SCRIPT" >/dev/null || {
        echo "FAIL: $message" >&2
        exit 1
    }
}

require_text 'SERVICES_START=/jffs/addons/asus-edge/bin/services-start' 'managed services-start path missing'
require_text 'HEALTHCHECK=/jffs/addons/asus-edge/bin/healthcheck.sh' 'managed healthcheck path missing'
require_text '[ -x "$SERVICES_START" ] || {' 'services-start is not required before update'
require_text '[ -x "$HEALTHCHECK" ] || {' 'healthcheck is not required before update'
require_text 'opkg update || exit 1' 'opkg metadata refresh failure is not fatal'
require_text 'UPGRADABLE="$(opkg list-upgradable)" || {' 'package query failure is not distinguished'
require_text 'opkg upgrade tailscale || exit 1' 'Tailscale package upgrade failure is not fatal'
require_text '"$SERVICES_START" || {' 'post-update service recovery failure is not fatal'
require_text '"$HEALTHCHECK" || {' 'post-update healthcheck failure is not fatal'

services_line="$(grep -n -F '[ -x "$SERVICES_START" ] || {' "$SCRIPT" | head -n 1 | cut -d: -f1)"
health_line="$(grep -n -F '[ -x "$HEALTHCHECK" ] || {' "$SCRIPT" | head -n 1 | cut -d: -f1)"
upgrade_line="$(grep -n -F 'opkg upgrade tailscale || exit 1' "$SCRIPT" | head -n 1 | cut -d: -f1)"

[ "$services_line" -lt "$upgrade_line" ] || {
    echo 'FAIL: services-start requirement is checked only after package mutation' >&2
    exit 1
}
[ "$health_line" -lt "$upgrade_line" ] || {
    echo 'FAIL: healthcheck requirement is checked only after package mutation' >&2
    exit 1
}

echo 'PASS: Tailscale update recovery guards are enforced before package mutation'
