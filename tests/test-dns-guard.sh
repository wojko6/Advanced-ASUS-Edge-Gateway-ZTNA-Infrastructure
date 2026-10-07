#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
GUARD="$ROOT_DIR/router/scripts/dns-guard"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

MOCK_BIN="$TMP_DIR/bin"
CONFIG="$TMP_DIR/asus-edge.conf"
RESOLV="$TMP_DIR/resolv.conf"
STATE_DIR="$TMP_DIR/state"
FLAG="$STATE_DIR/dns-breakglass"
FAIL_LOCAL="$TMP_DIR/fail-local"
FAIL_BOOTSTRAP="$TMP_DIR/fail-bootstrap"
BUSYBOX_MOCK="$TMP_DIR/busybox"

mkdir -p "$MOCK_BIN" "$STATE_DIR"

cat >"$CONFIG" <<'EOF'
EDGE_UNBOUND_PORT=53535
EDGE_DNS_LOCAL_RESOLVER_IP=192.0.2.53
EOF

cat >"$MOCK_BIN/nvram" <<EOF
#!/bin/sh
[ "\$1" = "get" ] || exit 1
case "\$2" in
    ntp_ready) echo 1 ;;
    wan0_dns_r)
        [ -f "$FAIL_BOOTSTRAP" ] || echo "9.9.9.9 149.112.112.112"
        ;;
    wan0_dns|wan_dns_r|wan_dns) echo "" ;;
    *) echo "" ;;
esac
EOF

cat >"$MOCK_BIN/pidof" <<EOF
#!/bin/sh
if [ -f "$FAIL_LOCAL" ]; then
    exit 1
fi
case "\$1" in
    unbound|pihole-FTL) echo 1234; exit 0 ;;
esac
exit 1
EOF

cat >"$MOCK_BIN/netstat" <<EOF
#!/bin/sh
[ -f "$FAIL_LOCAL" ] && exit 0
cat <<'OUT'
tcp 0 0 127.0.0.1:53535 0.0.0.0:* LISTEN
udp 0 0 192.0.2.53:53 0.0.0.0:*
OUT
EOF

cat >"$MOCK_BIN/logger" <<'EOF'
#!/bin/sh
exit 0
EOF

cat >"$BUSYBOX_MOCK" <<'EOF'
#!/bin/sh
applet="$1"
shift
case "$applet" in
    nslookup)
        echo "Server: 192.0.2.53"
        echo "Address 1: 1.1.1.1"
        exit 0
        ;;
    cmp)
        cmp "$@"
        ;;
    *)
        exit 127
        ;;
esac
EOF

chmod +x "$MOCK_BIN/nvram" "$MOCK_BIN/pidof" "$MOCK_BIN/netstat"     "$MOCK_BIN/logger" "$BUSYBOX_MOCK"

run_guard() {
    EDGE_CONFIG_FILE="$CONFIG"     EDGE_RESOLV_CONF="$RESOLV"     EDGE_DNS_STATE_DIR="$STATE_DIR"     EDGE_DNS_BREAKGLASS_FLAG="$FLAG"     EDGE_TEST_PATH_PREFIX="$MOCK_BIN"     EDGE_BUSYBOX_BIN="$BUSYBOX_MOCK"         sh "$GUARD" "$@"
}

printf '%s\n'     'nameserver 9.9.9.9'     'nameserver 149.112.112.112'     >"$RESOLV"

echo "=== healthy promotion ==="
healthy_output="$(run_guard auto)"
printf '%s\n' "$healthy_output"
grep -F 'AUTO=LOCAL_DNS' <<EOF >/dev/null
$healthy_output
EOF
grep -qx 'nameserver 192.0.2.53' "$RESOLV"

echo "=== healthy idempotency ==="
repeat_output="$(run_guard auto)"
printf '%s\n' "$repeat_output"
grep -F 'PROMOTE=ALREADY_LOCAL' <<EOF >/dev/null
$repeat_output
EOF

echo "=== sticky break-glass ==="
breakglass_output="$(run_guard breakglass-on test-suite)"
printf '%s\n' "$breakglass_output"
[ -f "$FLAG" ]
grep -qx 'nameserver 9.9.9.9' "$RESOLV"
grep -qx 'nameserver 149.112.112.112' "$RESOLV"

if run_guard promote >/tmp/asus-edge-dns-guard-promote-test.out 2>&1; then
    echo "FAIL: promotion succeeded while break-glass was active" >&2
    exit 1
fi
grep -F 'PROMOTE=BLOCKED_BREAKGLASS' /tmp/asus-edge-dns-guard-promote-test.out >/dev/null
rm -f /tmp/asus-edge-dns-guard-promote-test.out

run_guard breakglass-off >/dev/null
[ ! -f "$FLAG" ]

echo "=== break-glass arms even before bootstrap DNS is available ==="
: >"$FAIL_BOOTSTRAP"
printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"

pending_output="$(run_guard breakglass-on bootstrap-not-ready)"
printf '%s\n' "$pending_output"
grep -F 'BREAKGLASS=ACTIVE_FALLBACK_PENDING' <<EOF >/dev/null
$pending_output
EOF
[ -f "$FLAG" ]
grep -qx 'nameserver 192.0.2.53' "$RESOLV"

rm -f "$FAIL_BOOTSTRAP"
reassert_output="$(run_guard fallback)"
printf '%s\n' "$reassert_output"
grep -F 'FALLBACK=PASS' <<EOF >/dev/null
$reassert_output
EOF
grep -qx 'nameserver 9.9.9.9' "$RESOLV"
grep -qx 'nameserver 149.112.112.112' "$RESOLV"

run_guard breakglass-off >/dev/null
[ ! -f "$FLAG" ]

echo "=== fail-open unhealthy path ==="
printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"
: >"$FAIL_LOCAL"

unhealthy_output="$(run_guard auto)"
printf '%s\n' "$unhealthy_output"
grep -F 'AUTO=BOOTSTRAP_UNHEALTHY' <<EOF >/dev/null
$unhealthy_output
EOF
grep -qx 'nameserver 9.9.9.9' "$RESOLV"
grep -qx 'nameserver 149.112.112.112' "$RESOLV"

echo "=== idempotent fallback ==="
fallback_output="$(run_guard fallback)"
printf '%s\n' "$fallback_output"
grep -F 'FALLBACK=ALREADY_BOOTSTRAP' <<EOF >/dev/null
$fallback_output
EOF

echo "=== missing local resolver target fails open ==="
cat >"$CONFIG" <<'EOF'
EDGE_UNBOUND_PORT=53535
EOF
rm -f "$FAIL_LOCAL"
printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"

missing_output="$(run_guard auto)"
printf '%s\n' "$missing_output"
grep -F 'AUTO=BOOTSTRAP_CONFIG_INVALID' <<EOF >/dev/null
$missing_output
EOF
grep -qx 'nameserver 9.9.9.9' "$RESOLV"
grep -qx 'nameserver 149.112.112.112' "$RESOLV"

if run_guard promote >/tmp/asus-edge-dns-guard-invalid-target.out 2>&1; then
    echo "FAIL: promotion succeeded without a configured local resolver target" >&2
    exit 1
fi
grep -F 'PROMOTE=BLOCKED_INVALID_LOCAL_RESOLVER' \
    /tmp/asus-edge-dns-guard-invalid-target.out >/dev/null
rm -f /tmp/asus-edge-dns-guard-invalid-target.out

echo "=== invalid local resolver target fails open ==="
cat >"$CONFIG" <<'EOF'
EDGE_UNBOUND_PORT=53535
EDGE_DNS_LOCAL_RESOLVER_IP=999.0.2.53
EOF
printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"

invalid_output="$(run_guard auto)"
printf '%s\n' "$invalid_output"
grep -F 'AUTO=BOOTSTRAP_CONFIG_INVALID' <<EOF >/dev/null
$invalid_output
EOF
grep -qx 'nameserver 9.9.9.9' "$RESOLV"
grep -qx 'nameserver 149.112.112.112' "$RESOLV"

echo "PASS: DNS Guard healthy, fail-open, explicit-target and idempotency policies"
