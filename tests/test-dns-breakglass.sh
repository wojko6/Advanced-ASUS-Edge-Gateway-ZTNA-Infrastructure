#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
HELPER="$ROOT_DIR/router/scripts/edge-dns-breakglass.sh"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

MOCK_BIN="$TMP_DIR/bin"
GUARD="$TMP_DIR/dns-guard"
RESOLV="$TMP_DIR/resolv.conf"
NVRAM_LOG="$TMP_DIR/nvram.log"
SERVICE_LOG="$TMP_DIR/service.log"
FAIL_PING="$TMP_DIR/fail-ping"
FAIL_DNS="$TMP_DIR/fail-dns"

mkdir -p "$MOCK_BIN"

cat >"$GUARD" <<EOF
#!/bin/sh
case "\${1:-}" in
    breakglass-on)
        echo "BREAKGLASS=ACTIVE_FALLBACK_PENDING"
        exit 0
        ;;
    fallback)
        printf '%s\n' 'nameserver 9.9.9.9' >"$RESOLV"
        echo "FALLBACK=PASS"
        exit 0
        ;;
    status)
        echo "BREAKGLASS=ACTIVE"
        exit 0
        ;;
esac
exit 1
EOF

cat >"$MOCK_BIN/nvram" <<EOF
#!/bin/sh
case "\${1:-}" in
    get)
        case "\${2:-}" in
            wan_dnsenable_x|wan0_dnsenable_x) echo 0 ;;
            *) echo "" ;;
        esac
        ;;
    set)
        printf 'set %s\n' "\${2:-}" >>"$NVRAM_LOG"
        ;;
    commit)
        echo commit >>"$NVRAM_LOG"
        ;;
    *)
        exit 1
        ;;
esac
EOF

cat >"$MOCK_BIN/service" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$SERVICE_LOG"
exit 0
EOF

cat >"$MOCK_BIN/ping" <<EOF
#!/bin/sh
[ -f "$FAIL_PING" ] && exit 1
exit 0
EOF

cat >"$MOCK_BIN/sleep" <<'EOF'
#!/bin/sh
exit 0
EOF

cat >"$MOCK_BIN/sync" <<'EOF'
#!/bin/sh
exit 0
EOF

cat >"$MOCK_BIN/pidof" <<'EOF'
#!/bin/sh
exit 1
EOF

cat >"$MOCK_BIN/busybox" <<EOF
#!/bin/sh
[ "\${1:-}" = "nslookup" ] || exit 127
[ -f "$FAIL_DNS" ] && exit 1
echo "Address 1: 93.184.216.34"
exit 0
EOF

chmod +x "$GUARD" "$MOCK_BIN/nvram" "$MOCK_BIN/service" "$MOCK_BIN/ping" \
    "$MOCK_BIN/sleep" "$MOCK_BIN/sync" "$MOCK_BIN/pidof" "$MOCK_BIN/busybox"

run_helper() {
    EDGE_DNS_GUARD="$GUARD" \
    EDGE_RESOLV_CONF="$RESOLV" \
    EDGE_BUSYBOX_BIN="$MOCK_BIN/busybox" \
    EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
    EDGE_DNS_BREAKGLASS_WAN_WAIT_SECONDS=1 \
        sh "$HELPER"
}

echo "=== break-glass recovery success ==="
success_output="$(run_helper)"
printf '%s\n' "$success_output"

grep -F 'BREAKGLASS=ACTIVE_FALLBACK_PENDING' <<EOF >/dev/null
$success_output
EOF
grep -F 'WAN_RESTART=PASS' <<EOF >/dev/null
$success_output
EOF
grep -F 'FALLBACK_REASSERT=PASS' <<EOF >/dev/null
$success_output
EOF
grep -F 'INTERNET_IP=PASS' <<EOF >/dev/null
$success_output
EOF
grep -F 'DNS=PASS' <<EOF >/dev/null
$success_output
EOF
grep -F 'BREAKGLASS_RESULT=PASS' <<EOF >/dev/null
$success_output
EOF

grep -F 'set wan_dnsenable_x=1' "$NVRAM_LOG" >/dev/null
grep -F 'set wan0_dnsenable_x=1' "$NVRAM_LOG" >/dev/null
grep -F 'commit' "$NVRAM_LOG" >/dev/null
grep -F 'restart_wan' "$SERVICE_LOG" >/dev/null
grep -qx 'nameserver 9.9.9.9' "$RESOLV"

echo "=== final recovery failure is non-zero ==="
: >"$FAIL_PING"

if failure_output="$(run_helper 2>&1)"; then
    echo "FAIL: break-glass helper succeeded although WAN/IP recovery failed" >&2
    exit 1
fi
printf '%s\n' "$failure_output"

grep -F 'WAN_IP=TIMEOUT' <<EOF >/dev/null
$failure_output
EOF
grep -F 'INTERNET_IP=FAIL' <<EOF >/dev/null
$failure_output
EOF
grep -F 'BREAKGLASS_RESULT=FAIL' <<EOF >/dev/null
$failure_output
EOF

rm -f "$FAIL_PING"
: >"$FAIL_DNS"

if dns_failure_output="$(run_helper 2>&1)"; then
    echo "FAIL: break-glass helper succeeded although DNS validation failed" >&2
    exit 1
fi
printf '%s\n' "$dns_failure_output"
grep -F 'DNS=FAIL' <<EOF >/dev/null
$dns_failure_output
EOF
grep -F 'BREAKGLASS_RESULT=FAIL' <<EOF >/dev/null
$dns_failure_output
EOF

echo "PASS: break-glass ordering and final recovery verdict"
