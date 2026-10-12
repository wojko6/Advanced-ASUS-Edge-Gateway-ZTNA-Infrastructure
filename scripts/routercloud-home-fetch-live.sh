#!/usr/bin/env bash
# RouterCloud: read-only pull of active index.js from ASUS via existing SSH access.
# Usage: bash scripts/routercloud-home-fetch-live.sh admin1@ROUTER_HOST [SSH_PORT]
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  printf 'Usage: %s admin1@ROUTER_HOST [SSH_PORT]\n' "$0" >&2
  exit 2
fi

SSH_TARGET="$1"
SSH_PORT=1122
if [[ $# -eq 2 ]]; then SSH_PORT="$2"; fi
EXPECTED_SHA='d5052ea33917bad9314a49792bc555dd2e7ce2a3f2532aaff3b83c23e4c593b4'
DEST_DIR="$HOME/Archiwa/RouterCloud-Home-AJAX-20261012"
DEST_FILE="$DEST_DIR/production-index.js"

case "$SSH_PORT" in
  ''|*[!0-9]*) echo 'SSH_PORT_INVALID' >&2; exit 2 ;;
esac

umask 077
mkdir -p "$DEST_DIR"
chmod 700 "$DEST_DIR"
if [[ -e "$DEST_FILE" ]]; then
  echo "DEST_ALREADY_EXISTS: $DEST_FILE" >&2
  exit 3
fi

TMP_FILE="$(mktemp "$DEST_DIR/production-index.tmp.XXXXXXXX")"
trap 'rm -f "$TMP_FILE"' EXIT

# The remote script prints ONLY the asset bytes on stdout.
# Nothing is written to the ASUS filesystem and no services are restarted.
ssh -T -p "$SSH_PORT" "$SSH_TARGET" 'sh -s' > "$TMP_FILE" <<'REMOTE'
set -eu
CONF=/opt/etc/dufs-personal-cloud.yaml
test -r "$CONF" || exit 20
ASSETS_DIR="$(awk '
  /^[[:space:]]*assets:[[:space:]]*/ {
    sub(/^[[:space:]]*assets:[[:space:]]*/, "")
    gsub(/"/, "")
    sub(/[[:space:]]*$/, "")
    print
    exit
  }' "$CONF")"
case "$ASSETS_DIR" in
  /*) ;;
  *) exit 21 ;;
esac
test -r "$ASSETS_DIR/index.js" || exit 22
cat "$ASSETS_DIR/index.js"
REMOTE

ACTUAL_SHA="$(sha256sum "$TMP_FILE" | awk '{print $1}')"
if [[ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]]; then
  printf 'ROUTERCLOUD_LIVE_COPY_SHA256_MISMATCH\nEXPECTED=%s\nACTUAL=%s\n' "$EXPECTED_SHA" "$ACTUAL_SHA" >&2
  exit 4
fi

mv "$TMP_FILE" "$DEST_FILE"
chmod 600 "$DEST_FILE"
trap - EXIT
printf 'ROUTERCLOUD_LIVE_COPY=PASS\nSHA256=%s\nLOCAL_FILE=%s\nROUTER_MODIFIED=NO\n' "$ACTUAL_SHA" "$DEST_FILE"
