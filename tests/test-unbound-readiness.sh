#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
HANDLER="$ROOT_DIR/router/scripts/wan-event-handler"
TMPROOT="$(mktemp -d)"
trap 'rm -rf "$TMPROOT"' EXIT HUP INT TERM
MOCK_BIN="$TMPROOT/bin"
mkdir -p "$MOCK_BIN"
CONFIG="$TMPROOT/asus-edge.conf"
RESOLV="$TMPROOT/resolv.conf"
HELPER="$TMPROOT/tailscale-reconcile"
LOG="$TMPROOT/logger.log"

cat >"$CONFIG" <<EOF
EDGE_UNBOUND_PORT=53535
EDGE_WAN_DNS_WAIT_SECONDS=1
EDGE_TAILSCALE_WAIT_SECONDS=1
EDGE_TS_SOCKET="$TMPROOT/tailscaled.sock"
EOF
printf 'nameserver 8.8.8.8\n' >"$RESOLV"

cat >"$MOCK_BIN/pidof" <<'EOF'
#!/bin/sh
case "$1" in dnsmasq|unbound|tailscaled) echo 1234; exit 0 ;; esac
exit 1
EOF

cat >"$MOCK_BIN/netstat" <<'EOF'
#!/bin/sh
[ "$SCENARIO" = no_listener ] && exit 0
echo 'tcp 0 0 127.0.0.1:53535 0.0.0.0:* LISTEN'
EOF

cat >"$MOCK_BIN/dig" <<'EOF'
#!/bin/sh
case "$SCENARIO" in
  servfail) echo ';; ->>HEADER<<- opcode: QUERY, status: SERVFAIL, id: 1'; exit 0 ;;
  timeout) exit 1 ;;
  *) echo ';; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1'; exit 0 ;;
esac
EOF

cat >"$MOCK_BIN/tailscale" <<'EOF'
#!/bin/sh
case " $* " in *" debug prefs "*) echo '"'"'NetfilterMode'"'"': 0,' ;; esac
exit 0
EOF

cat >"$MOCK_BIN/logger" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$LOG"
EOF
cat >"$MOCK_BIN/sleep" <<'EOF'
#!/bin/sh
exit 0
EOF
cat >"$HELPER" <<'EOF'
#!/bin/sh
exit 0
EOF
chmod +x "$MOCK_BIN/pidof" "$MOCK_BIN/netstat" "$MOCK_BIN/dig" "$MOCK_BIN/tailscale" "$MOCK_BIN/logger" "$MOCK_BIN/sleep" "$HELPER"

run_case() {
    scenario="$1"
    SCENARIO="$scenario" \
    EDGE_CONFIG_FILE="$CONFIG" \
    EDGE_RESOLV_CONF="$RESOLV" \
    EDGE_TAILSCALE_HELPER="$HELPER" \
    EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
    "$HANDLER" >/dev/null 2>&1
}

for scenario in no_listener servfail timeout; do
    printf 'nameserver 8.8.8.8\n' >"$RESOLV"
    if run_case "$scenario"; then
        echo "FAIL: readiness accepted scenario $scenario" >&2
        exit 1
    fi
done
echo 'PASS: PID without listener, SERVFAIL and query timeout are rejected'

printf 'nameserver 8.8.8.8\n' >"$RESOLV"
run_case ok
grep -qx 'nameserver 127.0.0.1' "$RESOLV"
echo 'PASS: listener plus successful local DNS query is accepted'
