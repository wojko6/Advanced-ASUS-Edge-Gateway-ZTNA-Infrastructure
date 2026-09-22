#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
HELPER="$ROOT_DIR/router/scripts/tailscale-reconcile"
TMPROOT="$(mktemp -d)"
trap 'rm -rf "$TMPROOT"' EXIT HUP INT TERM

MOCK_BIN="$TMPROOT/bin"
mkdir -p "$MOCK_BIN"
CONFIG="$TMPROOT/asus-edge.conf"
LOG="$TMPROOT/tailscale.log"
LOGGER_LOG="$TMPROOT/logger.log"
LOCK_DIR="$TMPROOT/asus-edge-tailscale.lock"

cat >"$CONFIG" <<'EOF'
EDGE_TS_SOCKET="/var/run/tailscale/tailscaled.sock"
EDGE_TS_STATE="/opt/var/lib/tailscale/tailscaled.state"
EDGE_TAILSCALED_LOG="/opt/var/log/tailscaled.log"
EDGE_TS_NETFILTER_MODE="off"
EDGE_ADVERTISE_ROUTES="192.0.2.0/24"
EDGE_ENABLE_EXIT_NODE="1"
EDGE_ACCEPT_DNS="false"
EDGE_HOSTNAME="fixture-gateway"
EDGE_REQUIRE_SWAP="0"
EDGE_SWAP_WAIT_SECONDS="1"
EDGE_SERVICE_STABILITY_SECONDS="1"
EDGE_SERVICE_START_ATTEMPTS="1"
EDGE_SERVICE_RETRY_SECONDS="1"
EDGE_TS_READY_WAIT_SECONDS="1"
EDGE_TAILSCALE_LOCK_WAIT_SECONDS="1"
EOF

cat >"$MOCK_BIN/pidof" <<'EOF'
#!/bin/sh
[ "$1" = tailscaled ] && { echo 1234; exit 0; }
exit 1
EOF

cat >"$MOCK_BIN/tailscale" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$LOG"
case " \$* " in
  *" debug prefs "*)
    if [ "\${SCENARIO:-ok}" = bad_prefs ]; then
      echo '"NetfilterMode": 2,'
    else
      echo '"NetfilterMode": 0,'
    fi
    ;;
esac
exit 0
EOF

cat >"$MOCK_BIN/logger" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$LOGGER_LOG"
EOF

cat >"$MOCK_BIN/sleep" <<'EOF'
#!/bin/sh
exit 0
EOF

chmod +x "$MOCK_BIN/pidof" "$MOCK_BIN/tailscale" "$MOCK_BIN/logger" "$MOCK_BIN/sleep"

run_helper() {
    EDGE_CONFIG_FILE="$CONFIG" \
    EDGE_TAILSCALE_LOCK_DIR="$LOCK_DIR" \
    EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
    "$HELPER" "$@"
}

run_helper ensure

grep -F -- '--netfilter-mode=off' "$LOG" >/dev/null
grep -F -- '--accept-dns=false' "$LOG" >/dev/null
grep -F -- '--advertise-routes=192.0.2.0/24' "$LOG" >/dev/null
grep -F -- '--advertise-exit-node' "$LOG" >/dev/null
[ ! -d "$LOCK_DIR" ] || {
    echo "FAIL: reconciliation lock remained after success" >&2
    exit 1
}
echo "PASS: canonical ensure reapplies and verifies Tailscale policy"

mkdir "$LOCK_DIR"
printf '%s\n' 999999 >"$LOCK_DIR/owner"
: >"$LOG"
run_helper ensure
[ ! -d "$LOCK_DIR" ] || {
    echo "FAIL: stale lock was not reclaimed" >&2
    exit 1
}
grep -F -- '--netfilter-mode=off' "$LOG" >/dev/null
echo "PASS: stale Tailscale lock is reclaimed"

if SCENARIO=bad_prefs run_helper ensure >/dev/null 2>&1; then
    echo "FAIL: helper accepted non-off NetfilterMode" >&2
    exit 1
fi
echo "PASS: non-off NetfilterMode is rejected"

if EDGE_CONFIG_FILE="$CONFIG" \
   EDGE_TAILSCALE_LOCK_DIR="$TMPROOT/relative/../bad" \
   EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
   "$HELPER" ensure >/dev/null 2>&1
then
    echo "FAIL: unsafe lock path accepted" >&2
    exit 1
fi
echo "PASS: unsafe lock path rejected"
