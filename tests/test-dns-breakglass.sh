#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
HELPER="$ROOT_DIR/router/scripts/edge-dns-breakglass.sh"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

MOCK_BIN="$TMP_DIR/bin"
GUARD="$TMP_DIR/dns-guard"
RESOLV="$TMP_DIR/resolv.conf"
STATE_DIR="$TMP_DIR/state"
WAN_STATE="$STATE_DIR/dns-breakglass-wan-dns.state"
NVRAM_LOG="$TMP_DIR/nvram.log"
SERVICE_LOG="$TMP_DIR/service.log"
WAN_VALUE="$TMP_DIR/wan-dnsenable"
WAN0_VALUE="$TMP_DIR/wan0-dnsenable"
FAIL_PING="$TMP_DIR/fail-ping"
FAIL_DNS="$TMP_DIR/fail-dns"
FAIL_READY="$TMP_DIR/fail-ready"
HANG_DNS="$TMP_DIR/hang-dns"

mkdir -p "$MOCK_BIN" "$STATE_DIR"
printf '0\n' >"$WAN_VALUE"
printf '0\n' >"$WAN0_VALUE"

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
    ready)
        [ -f "$FAIL_READY" ] && { echo "READY=FAIL"; exit 1; }
        echo "READY=PASS"
        exit 0
        ;;
    breakglass-off)
        echo "BREAKGLASS=INACTIVE"
        exit 0
        ;;
    promote)
        printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"
        echo "PROMOTE=PASS"
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
            wan_dnsenable_x) cat "$WAN_VALUE" ;;
            wan0_dnsenable_x) cat "$WAN0_VALUE" ;;
            *) echo "" ;;
        esac
        ;;
    set)
        key="\${2%%=*}"
        value="\${2#*=}"
        case "\$key" in
            wan_dnsenable_x) printf '%s\n' "\$value" >"$WAN_VALUE" ;;
            wan0_dnsenable_x) printf '%s\n' "\$value" >"$WAN0_VALUE" ;;
            *) exit 1 ;;
        esac
        printf 'set %s\n' "\${2:-}" >>"$NVRAM_LOG"
        ;;
    unset)
        case "\${2:-}" in
            wan_dnsenable_x) : >"$WAN_VALUE" ;;
            wan0_dnsenable_x) : >"$WAN0_VALUE" ;;
            *) exit 1 ;;
        esac
        printf 'unset %s\n' "\${2:-}" >>"$NVRAM_LOG"
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
applet="\${1:-}"
shift || true
case "\$applet" in
    timeout)
        exec /usr/bin/timeout "\$@"
        ;;
    nslookup)
        [ -f "$HANG_DNS" ] && sleep 30
        [ -f "$FAIL_DNS" ] && exit 1
        echo "Address 1: 93.184.216.34"
        exit 0
        ;;
    *)
        exit 127
        ;;
esac
EOF

chmod +x "$GUARD" "$MOCK_BIN/nvram" "$MOCK_BIN/service" "$MOCK_BIN/ping" \
    "$MOCK_BIN/sleep" "$MOCK_BIN/sync" "$MOCK_BIN/pidof" "$MOCK_BIN/busybox"

run_helper() {
    EDGE_DNS_GUARD="$GUARD" \
    EDGE_RESOLV_CONF="$RESOLV" \
    EDGE_DNS_STATE_DIR="$STATE_DIR" \
    EDGE_DNS_BREAKGLASS_WAN_STATE="$WAN_STATE" \
    EDGE_BUSYBOX_BIN="$MOCK_BIN/busybox" \
    EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
    EDGE_DNS_BREAKGLASS_WAN_WAIT_SECONDS=1 \
    EDGE_DNS_BREAKGLASS_DNS_TIMEOUT_SECONDS=1 \
        sh "$HELPER" "$@"
}

reset_fixture() {
    rm -f "$WAN_STATE" "$FAIL_PING" "$FAIL_DNS" "$FAIL_READY" "$HANG_DNS" "$NVRAM_LOG" "$SERVICE_LOG"
    printf '0\n' >"$WAN_VALUE"
    printf '0\n' >"$WAN0_VALUE"
    printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"
}

echo "=== break-glass activation snapshots WAN DNS mode ==="
reset_fixture
success_output="$(run_helper on)"
printf '%s\n' "$success_output"

grep -F 'WAN_DNS_SNAPSHOT=SAVED' <<EOF >/dev/null
$success_output
EOF
grep -F 'BREAKGLASS_RESULT=PASS' <<EOF >/dev/null
$success_output
EOF
grep -qx 'wan_dnsenable_x=0' "$WAN_STATE"
grep -qx 'wan0_dnsenable_x=0' "$WAN_STATE"
grep -qx '1' "$WAN_VALUE"
grep -qx '1' "$WAN0_VALUE"
grep -qx 'nameserver 9.9.9.9' "$RESOLV"

echo "=== break-glass clear restores previous WAN DNS mode ==="
clear_output="$(run_helper off)"
printf '%s\n' "$clear_output"

grep -F 'READY=PASS' <<EOF >/dev/null
$clear_output
EOF
grep -F 'WAN_DNS_RESTORE=UPDATED' <<EOF >/dev/null
$clear_output
EOF
grep -F 'LOCAL_PROMOTION_AFTER_CLEAR=PASS' <<EOF >/dev/null
$clear_output
EOF
grep -F 'BREAKGLASS_CLEAR_RESULT=PASS' <<EOF >/dev/null
$clear_output
EOF
grep -F 'WAN_DNS_SNAPSHOT=REMOVED' <<EOF >/dev/null
$clear_output
EOF
grep -qx '0' "$WAN_VALUE"
grep -qx '0' "$WAN0_VALUE"
[ ! -f "$WAN_STATE" ]
grep -qx 'nameserver 192.0.2.53' "$RESOLV"

echo "=== clear is blocked while local DNS is unhealthy ==="
reset_fixture
run_helper on >/dev/null
: >"$FAIL_READY"

if blocked_output="$(run_helper off 2>&1)"; then
    echo "FAIL: break-glass clear succeeded while local DNS was unhealthy" >&2
    exit 1
fi
printf '%s\n' "$blocked_output"

grep -F 'BREAKGLASS_CLEAR_RESULT=BLOCKED_LOCAL_DNS_UNHEALTHY' <<EOF >/dev/null
$blocked_output
EOF
[ -f "$WAN_STATE" ]
grep -qx '1' "$WAN_VALUE"
grep -qx '1' "$WAN0_VALUE"

echo "=== final activation recovery failure is non-zero ==="
reset_fixture
: >"$FAIL_PING"

if failure_output="$(run_helper on 2>&1)"; then
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
[ -f "$WAN_STATE" ]

echo "=== activation DNS validation failure is non-zero ==="
reset_fixture
: >"$FAIL_DNS"

if dns_failure_output="$(run_helper on 2>&1)"; then
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
[ -f "$WAN_STATE" ]

echo "=== break-glass DNS validation is explicitly bounded ==="
reset_fixture
: >"$HANG_DNS"
set +e
bounded_output="$(
    timeout 5 env \
        EDGE_DNS_GUARD="$GUARD" \
        EDGE_RESOLV_CONF="$RESOLV" \
        EDGE_DNS_STATE_DIR="$STATE_DIR" \
        EDGE_DNS_BREAKGLASS_WAN_STATE="$WAN_STATE" \
        EDGE_BUSYBOX_BIN="$MOCK_BIN/busybox" \
        EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
        EDGE_DNS_BREAKGLASS_WAN_WAIT_SECONDS=1 \
        EDGE_DNS_BREAKGLASS_DNS_TIMEOUT_SECONDS=1 \
        sh "$HELPER" on 2>&1
)"
bounded_rc=$?
set -e
[ "$bounded_rc" -ne 124 ] || {
    echo "FAIL: break-glass DNS validation exceeded the outer 5-second safety bound" >&2
    exit 1
}
[ "$bounded_rc" -ne 0 ] || {
    echo "FAIL: hanging break-glass DNS validation was reported as success" >&2
    exit 1
}
printf '%s\n' "$bounded_output" | grep -F 'DNS=FAIL' >/dev/null
printf '%s\n' "$bounded_output" | grep -F 'BREAKGLASS_RESULT=FAIL' >/dev/null
rm -f "$HANG_DNS"

echo "PASS: break-glass snapshot, restore, ordering and final recovery verdict"
