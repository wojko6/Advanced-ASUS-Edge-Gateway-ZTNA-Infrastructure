#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
HANDLER="$ROOT_DIR/router/scripts/wan-event-handler"

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT HUP INT TERM

make_common() {
    case_dir="$1"
    mkdir -p "$case_dir/bin"

    cat >"$case_dir/asus-edge.conf" <<EOF
EDGE_UNBOUND_PORT=53535
EDGE_TS_SOCKET="$case_dir/tailscaled.sock"
EDGE_WAN_DNS_WAIT_SECONDS=1
EDGE_TAILSCALE_WAIT_SECONDS=1
EOF

    cat >"$case_dir/bin/logger" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$case_dir/logger.log"
EOF

    cat >"$case_dir/bin/sleep" <<'EOF'
#!/bin/sh
exit 0
EOF

    cat >"$case_dir/bin/tailscale" <<'EOF'
#!/bin/sh
exit 0
EOF

    chmod +x "$case_dir/bin/logger" "$case_dir/bin/sleep" "$case_dir/bin/tailscale"
}

run_handler() {
    case_dir="$1"
    EDGE_CONFIG_FILE="$case_dir/asus-edge.conf"     EDGE_DNS_GUARD="$case_dir/dns-guard"     EDGE_TAILSCALED_INIT="$case_dir/S06tailscaled"     EDGE_TEST_PATH_PREFIX="$case_dir/bin"         "$HANDLER" 0 connected
}

echo "=== TEST: healthy local DNS path ==="
CASE="$TMP_ROOT/healthy"
make_common "$CASE"

cat >"$CASE/bin/pidof" <<'EOF'
#!/bin/sh
case "$1" in
    dnsmasq|unbound|tailscaled) echo 1234; exit 0 ;;
esac
exit 1
EOF

cat >"$CASE/bin/netstat" <<'EOF'
#!/bin/sh
echo "tcp 0 0 127.0.0.1:53535 0.0.0.0:* LISTEN"
EOF

cat >"$CASE/dns-guard" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$CASE/guard.log"
exit 0
EOF

cat >"$CASE/S06tailscaled" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$CASE/init.log"
exit 0
EOF

chmod +x "$CASE/bin/pidof" "$CASE/bin/netstat" "$CASE/dns-guard" "$CASE/S06tailscaled"

run_handler "$CASE"

[ "$(grep -c '^auto$' "$CASE/guard.log")" -eq 2 ]
grep -qx 'restart' "$CASE/init.log"
grep -F 'DNS Guard policy applied during WAN initial phase' "$CASE/logger.log" >/dev/null
grep -F 'DNS Guard policy applied during WAN settled phase' "$CASE/logger.log" >/dev/null
echo "PASS: healthy path applies initial+settled DNS policy"

echo "=== TEST: local DNS path unavailable remains fail-open ==="
CASE="$TMP_ROOT/unhealthy"
make_common "$CASE"

cat >"$CASE/bin/pidof" <<'EOF'
#!/bin/sh
[ "$1" = "tailscaled" ] && { echo 1234; exit 0; }
exit 1
EOF

cat >"$CASE/bin/netstat" <<'EOF'
#!/bin/sh
exit 0
EOF

cat >"$CASE/dns-guard" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$CASE/guard.log"
exit 0
EOF

cat >"$CASE/S06tailscaled" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$CASE/init.log"
exit 0
EOF

chmod +x "$CASE/bin/pidof" "$CASE/bin/netstat" "$CASE/dns-guard" "$CASE/S06tailscaled"

run_handler "$CASE"

[ "$(grep -c '^auto$' "$CASE/guard.log")" -eq 1 ]
grep -qx 'restart' "$CASE/init.log"
grep -F 'keeping bootstrap DNS' "$CASE/logger.log" >/dev/null
echo "PASS: unavailable local DNS keeps bootstrap path and still recovers Tailscale"

echo "=== TEST: DNS Guard initial failure stops handler ==="
CASE="$TMP_ROOT/guard-fail"
make_common "$CASE"

cat >"$CASE/bin/pidof" <<'EOF'
#!/bin/sh
case "$1" in
    dnsmasq|unbound|tailscaled) echo 1234; exit 0 ;;
esac
exit 1
EOF

cat >"$CASE/bin/netstat" <<'EOF'
#!/bin/sh
echo "tcp 0 0 127.0.0.1:53535 0.0.0.0:* LISTEN"
EOF

cat >"$CASE/dns-guard" <<'EOF'
#!/bin/sh
exit 1
EOF

cat >"$CASE/S06tailscaled" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$CASE/init.log"
exit 0
EOF

chmod +x "$CASE/bin/pidof" "$CASE/bin/netstat" "$CASE/dns-guard" "$CASE/S06tailscaled"

if run_handler "$CASE"; then
    echo "FAIL: handler succeeded although initial DNS Guard policy failed" >&2
    exit 1
fi

grep -F 'DNS Guard policy failed during WAN initial phase' "$CASE/logger.log" >/dev/null
[ ! -s "$CASE/init.log" ] 2>/dev/null || {
    echo "FAIL: tailscaled restart attempted after DNS Guard failure" >&2
    exit 1
}
echo "PASS: DNS Guard failure is propagated"

echo "=== TEST: tailscaled restart failure ==="
CASE="$TMP_ROOT/tailscale-fail"
make_common "$CASE"

cat >"$CASE/bin/pidof" <<'EOF'
#!/bin/sh
case "$1" in
    dnsmasq|unbound|tailscaled) echo 1234; exit 0 ;;
esac
exit 1
EOF

cat >"$CASE/bin/netstat" <<'EOF'
#!/bin/sh
echo "tcp 0 0 127.0.0.1:53535 0.0.0.0:* LISTEN"
EOF

cat >"$CASE/dns-guard" <<'EOF'
#!/bin/sh
exit 0
EOF

cat >"$CASE/S06tailscaled" <<'EOF'
#!/bin/sh
exit 1
EOF

chmod +x "$CASE/bin/pidof" "$CASE/bin/netstat" "$CASE/dns-guard" "$CASE/S06tailscaled"

if run_handler "$CASE"; then
    echo "FAIL: handler succeeded although tailscaled restart failed" >&2
    exit 1
fi

grep -F 'failed to restart tailscaled after WAN DNS update' "$CASE/logger.log" >/dev/null
echo "PASS: tailscaled restart failure is propagated"
