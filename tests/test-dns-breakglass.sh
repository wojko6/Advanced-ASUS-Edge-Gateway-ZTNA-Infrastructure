#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
HELPER="$ROOT_DIR/router/scripts/edge-dns-breakglass.sh"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

MOCK_BIN="$TMP_DIR/bin"
export EDGE_SERVICE_BIN="$MOCK_BIN/service"
GUARD="$TMP_DIR/dns-guard"
SUPERVISOR="$TMP_DIR/edge-dns-supervisor"
"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror \
    "$ROOT_DIR/router/src/edge-dns-supervisor.c" -o "$SUPERVISOR"
export EDGE_DNS_SUPERVISOR="$SUPERVISOR"
RESOLV="$TMP_DIR/resolv.conf"
STATE_DIR="$TMP_DIR/state"
WAN_STATE="$STATE_DIR/dns-breakglass-wan-dns.state"
NVRAM_LOG="$TMP_DIR/nvram.log"
SERVICE_LOG="$TMP_DIR/service.log"
WAN_VALUE="$TMP_DIR/wan-dnsenable"
WAN0_VALUE="$TMP_DIR/wan0-dnsenable"
FAIL_PING="$TMP_DIR/fail-ping"
FAIL_INTERNET_ONCE="$TMP_DIR/fail-internet-once"
FAIL_DNS="$TMP_DIR/fail-dns"
FAIL_DNS_ONCE="$TMP_DIR/fail-dns-once"
FAIL_FALLBACK_ONCE="$TMP_DIR/fail-fallback-once"
FAIL_FALLBACK_ALWAYS="$TMP_DIR/fail-fallback-always"
SLOW_FALLBACK="$TMP_DIR/slow-fallback"
STALL_FALLBACK="$TMP_DIR/stall-fallback"
STALL_LOCK="$TMP_DIR/stall-fallback.lock"
FAIL_READY="$TMP_DIR/fail-ready"
HOLD_BREAKGLASS_ON="$TMP_DIR/hold-breakglass-on"
BREAKGLASS_HOLD_STARTED="$TMP_DIR/breakglass-hold-started"
HANG_DNS="$TMP_DIR/hang-dns"
HANG_DNS_LOCK="$TMP_DIR/hang-dns-escape.lock"
HANG_DNS_CHILD="$TMP_DIR/hang-dns-escape.pid"
HANG_SERVICE="$TMP_DIR/hang-service"
FAIL_NVRAM_SET_WAN0="$TMP_DIR/fail-nvram-set-wan0"
FAIL_NVRAM_COMMIT_ONCE="$TMP_DIR/fail-nvram-commit-once"
FAIL_NVRAM_UNSET_WAN0="$TMP_DIR/fail-nvram-unset-wan0"

mkdir -p "$MOCK_BIN" "$STATE_DIR"
printf '0\n' >"$WAN_VALUE"
printf '0\n' >"$WAN0_VALUE"

cat >"$GUARD" <<EOF
#!/bin/sh
case "\${1:-}" in
    breakglass-on)
        if [ -f "$HOLD_BREAKGLASS_ON" ]; then
            : >"$BREAKGLASS_HOLD_STARTED"
            /bin/sleep 5
        fi
        echo "BREAKGLASS=ACTIVE_FALLBACK_PENDING"
        exit 0
        ;;
    fallback)
        if [ -f "$STALL_FALLBACK" ]; then
            exec 9>"$STALL_LOCK"
            flock -x 9 || exit 1
            exec /bin/sleep 12
        fi
        if [ -f "$SLOW_FALLBACK" ]; then
            /bin/sleep 3
            echo "FALLBACK=UNHEALTHY_BOOTSTRAP"
            exit 1
        fi
        if [ -f "$FAIL_FALLBACK_ALWAYS" ]; then
            echo "FALLBACK=UNHEALTHY_BOOTSTRAP"
            exit 1
        fi
        if [ -f "$FAIL_FALLBACK_ONCE" ]; then
            rm -f "$FAIL_FALLBACK_ONCE"
            echo "FALLBACK=UNHEALTHY_BOOTSTRAP"
            exit 1
        fi
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
            wan0_dnsenable_x)
                if [ -f "$FAIL_NVRAM_SET_WAN0" ]; then
                    rm -f "$FAIL_NVRAM_SET_WAN0"
                    exit 1
                fi
                printf '%s\n' "\$value" >"$WAN0_VALUE"
                ;;
            *) exit 1 ;;
        esac
        printf 'set %s\n' "\${2:-}" >>"$NVRAM_LOG"
        ;;
    unset)
        case "\${2:-}" in
            wan_dnsenable_x) : >"$WAN_VALUE" ;;
            wan0_dnsenable_x)
                if [ -f "$FAIL_NVRAM_UNSET_WAN0" ]; then
                    rm -f "$FAIL_NVRAM_UNSET_WAN0"
                    exit 1
                fi
                : >"$WAN0_VALUE"
                ;;
            *) exit 1 ;;
        esac
        printf 'unset %s\n' "\${2:-}" >>"$NVRAM_LOG"
        ;;
    commit)
        echo commit >>"$NVRAM_LOG"
        if [ -f "$FAIL_NVRAM_COMMIT_ONCE" ]; then
            rm -f "$FAIL_NVRAM_COMMIT_ONCE"
            exit 1
        fi
        ;;
    *)
        exit 1
        ;;
esac
EOF

cat >"$MOCK_BIN/service" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$SERVICE_LOG"
[ -f "$HANG_SERVICE" ] && exec /bin/sleep 30
exit 0
EOF

cat >"$MOCK_BIN/ping" <<EOF
#!/bin/sh
[ -f "$FAIL_PING" ] && exit 1
if [ "\${1:-}" = "-c" ] &&
   [ "\${2:-}" = "2" ] &&
   [ -f "$FAIL_INTERNET_ONCE" ]; then
    rm -f "$FAIL_INTERNET_ONCE"
    exit 1
fi
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

cat >"$MOCK_BIN/hang-dns-worker" <<'EOF'
#!/bin/sh
exec 9>"$1"
flock -x 9 || exit 1
printf '%s\n' "$$" >"$2"
exec /bin/sleep 30
EOF
chmod +x "$MOCK_BIN/hang-dns-worker"

cat >"$MOCK_BIN/busybox" <<EOF
#!/bin/sh
applet="\${1:-}"
shift || true
case "\$applet" in
    timeout)
        echo "timeout: applet not found" >&2
        exit 127
        ;;
    sleep)
        exec /bin/sleep "\$@"
        ;;
    nslookup)
        if [ -f "$HANG_DNS" ]; then
            rm -f "$HANG_DNS_CHILD"
            setsid "$MOCK_BIN/hang-dns-worker" "$HANG_DNS_LOCK" "$HANG_DNS_CHILD" </dev/null >/dev/null 2>&1 &
            for unused in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
                [ -s "$HANG_DNS_CHILD" ] && break
                /bin/sleep 0.02
            done
            [ -s "$HANG_DNS_CHILD" ] || exit 90
            exec /bin/sleep 30
        fi
        if [ -f "$FAIL_DNS_ONCE" ]; then
            rm -f "$FAIL_DNS_ONCE"
            exit 1
        fi
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
    EDGE_DNS_BREAKGLASS_SERVICE_TIMEOUT_SECONDS=1 \
        sh "$HELPER" "$@"
}

reset_fixture() {
    rm -f "$WAN_STATE" "$FAIL_PING" "$FAIL_DNS" "$FAIL_DNS_ONCE" "$FAIL_FALLBACK_ONCE" "$FAIL_FALLBACK_ALWAYS" "$SLOW_FALLBACK" "$STALL_FALLBACK" "$FAIL_INTERNET_ONCE" "$FAIL_READY" "$HANG_DNS" "$HANG_SERVICE" \
        "$FAIL_NVRAM_SET_WAN0" "$FAIL_NVRAM_COMMIT_ONCE" "$FAIL_NVRAM_UNSET_WAN0" \
        "$NVRAM_LOG" "$SERVICE_LOG"
    printf '0\n' >"$WAN_VALUE"
    printf '0\n' >"$WAN0_VALUE"
    printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"
}

echo "=== break-glass fixture has no firmware BusyBox timeout applet ==="
if "$MOCK_BIN/busybox" timeout 1 /bin/true >/dev/null 2>&1; then
    echo "FAIL: firmware fixture unexpectedly provides BusyBox timeout" >&2
    exit 1
fi

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

echo "=== corrupt existing WAN DNS snapshot blocks activation before NVRAM mutation ==="
reset_fixture
cat >"$WAN_STATE" <<'EOF'
wan_dnsenable_x=CORRUPT
wan0_dnsenable_x=0
EOF

if corrupt_snapshot_output="$(run_helper on 2>&1)"; then
    echo "FAIL: break-glass activation accepted a corrupt existing WAN DNS snapshot" >&2
    exit 1
fi
printf '%s\n' "$corrupt_snapshot_output"
printf '%s\n' "$corrupt_snapshot_output" | grep -F 'WAN_DNS_SNAPSHOT=INVALID' >/dev/null
grep -qx '0' "$WAN_VALUE"
grep -qx '0' "$WAN0_VALUE"
if [ -s "$SERVICE_LOG" ]; then
    echo "FAIL: WAN restart occurred despite corrupt recovery snapshot" >&2
    exit 1
fi

echo "=== partial activation NVRAM mutation is rolled back from snapshot ==="
reset_fixture
: >"$FAIL_NVRAM_SET_WAN0"

if partial_nvram_output="$(run_helper on 2>&1)"; then
    echo "FAIL: break-glass activation succeeded despite injected second NVRAM set failure" >&2
    exit 1
fi
printf '%s\n' "$partial_nvram_output"
grep -F 'WAN_DNS_ACTIVATION_ROLLBACK=PASS' <<EOF >/dev/null
$partial_nvram_output
EOF
grep -qx '0' "$WAN_VALUE"
grep -qx '0' "$WAN0_VALUE"
[ -f "$WAN_STATE" ]

echo "=== activation commit failure rolls back to saved WAN DNS mode ==="
reset_fixture
: >"$FAIL_NVRAM_COMMIT_ONCE"

if commit_failure_output="$(run_helper on 2>&1)"; then
    echo "FAIL: break-glass activation succeeded despite injected NVRAM commit failure" >&2
    exit 1
fi
printf '%s\n' "$commit_failure_output" | grep -F 'WAN_DNS_ACTIVATION_ROLLBACK=PASS' >/dev/null
grep -qx '0' "$WAN_VALUE"
grep -qx '0' "$WAN0_VALUE"
[ -f "$WAN_STATE" ]

echo "=== interrupted activation state converges on retry ==="
reset_fixture
cat >"$WAN_STATE" <<'EOF'
wan_dnsenable_x=0
wan0_dnsenable_x=0
EOF
printf '1\n' >"$WAN_VALUE"
printf '0\n' >"$WAN0_VALUE"

retry_activation_output="$(run_helper on)"
printf '%s\n' "$retry_activation_output" | grep -F 'WAN_DNS_SNAPSHOT=EXISTING' >/dev/null
printf '%s\n' "$retry_activation_output" | grep -F 'BREAKGLASS_RESULT=PASS' >/dev/null
grep -qx '1' "$WAN_VALUE"
grep -qx '1' "$WAN0_VALUE"

retry_activation_clear="$(run_helper off)"
printf '%s\n' "$retry_activation_clear" | grep -F 'BREAKGLASS_CLEAR_RESULT=PASS' >/dev/null
grep -qx '0' "$WAN_VALUE"
grep -qx '0' "$WAN0_VALUE"
[ ! -f "$WAN_STATE" ]

echo "=== interrupted clear state converges on retry ==="
reset_fixture
run_helper on >/dev/null
printf '0\n' >"$WAN_VALUE"
printf '1\n' >"$WAN0_VALUE"

retry_clear_output="$(run_helper off)"
printf '%s\n' "$retry_clear_output" | grep -F 'BREAKGLASS_CLEAR_RESULT=PASS' >/dev/null
grep -qx '0' "$WAN_VALUE"
grep -qx '0' "$WAN0_VALUE"
grep -qx 'nameserver 192.0.2.53' "$RESOLV"
[ ! -f "$WAN_STATE" ]

echo "=== failed EMPTY restore re-arms safe break-glass ==="
reset_fixture
: >"$WAN_VALUE"
: >"$WAN0_VALUE"
run_helper on >/dev/null
grep -qx 'wan_dnsenable_x=EMPTY' "$WAN_STATE"
grep -qx 'wan0_dnsenable_x=EMPTY' "$WAN_STATE"
: >"$FAIL_NVRAM_UNSET_WAN0"

if unset_failure_output="$(run_helper off 2>&1)"; then
    echo "FAIL: break-glass clear succeeded despite injected NVRAM unset failure" >&2
    exit 1
fi
printf '%s\n' "$unset_failure_output" | grep -F 'WAN_DNS_RESTORE=FAIL' >/dev/null
printf '%s\n' "$unset_failure_output" | grep -F 'BREAKGLASS_REARMED=YES' >/dev/null
grep -qx '1' "$WAN_VALUE"
grep -qx '1' "$WAN0_VALUE"
[ -f "$WAN_STATE" ]

echo "=== failed rearm does not claim full recovery ==="
reset_fixture
run_helper on >/dev/null
: >"$HANG_SERVICE"
requests_before=$(grep -c '^restart_wan$' "$SERVICE_LOG")

if rearm_partial_output="$(run_helper off 2>&1)"; then
    echo "FAIL: break-glass clear succeeded despite a hung WAN restart" >&2
    exit 1
fi
printf '%s\n' "$rearm_partial_output"
printf '%s\n' "$rearm_partial_output" | grep -F 'BREAKGLASS_REARMED=PARTIAL' >/dev/null
if printf '%s\n' "$rearm_partial_output" | grep -F 'BREAKGLASS_REARMED=YES' >/dev/null; then
    echo "FAIL: failed recovery rearm was falsely reported as fully rearmed" >&2
    exit 1
fi
[ -f "$WAN_STATE" ]

requests_after=$(grep -c '^restart_wan$' "$SERVICE_LOG")
if [ "$((requests_after - requests_before))" -ne 1 ]; then
    echo "FAIL: hung WAN dispatch was repeated during rearm" >&2
    exit 1
fi
echo "WAN_TIMEOUT_SINGLE_DISPATCH=PASS"

rm -f "$HANG_SERVICE"

echo "=== failed WAN IP recovery must not redispatch ==="
reset_fixture
run_helper on >/dev/null
requests_before=$(grep -c '^restart_wan$' "$SERVICE_LOG")
: >"$FAIL_PING"

if ip_clear_output="$(run_helper off 2>&1)"; then
    echo "FAIL: WAN IP timeout unexpectedly cleared break-glass" >&2
    exit 1
fi

requests_after=$(grep -c '^restart_wan$' "$SERVICE_LOG")

if [ "$((requests_after - requests_before))" -ne 1 ] ||
   [ ! -f "$WAN_STATE" ] ||
   ! printf '%s\n' "$ip_clear_output" |
       grep -Fq 'BREAKGLASS_REARMED=PARTIAL'; then
    echo "FAIL: repeated WAN dispatch or unsafe recovery verdict" >&2
    exit 1
fi

echo "WAN_IP_FAILURE_SINGLE_DISPATCH=PASS"

echo "=== restart_wan hang is bounded ==="
reset_fixture
: >"$HANG_SERVICE"
set +e
service_bounded_output="$(
    timeout 5 env \
        EDGE_DNS_GUARD="$GUARD" \
        EDGE_RESOLV_CONF="$RESOLV" \
        EDGE_DNS_STATE_DIR="$STATE_DIR" \
        EDGE_DNS_BREAKGLASS_WAN_STATE="$WAN_STATE" \
        EDGE_BUSYBOX_BIN="$MOCK_BIN/busybox" \
        EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
        EDGE_DNS_BREAKGLASS_WAN_WAIT_SECONDS=1 \
        EDGE_DNS_BREAKGLASS_DNS_TIMEOUT_SECONDS=1 \
        EDGE_DNS_BREAKGLASS_SERVICE_TIMEOUT_SECONDS=1 \
        sh "$HELPER" on 2>&1
)"
service_bounded_rc=$?
set -e
[ "$service_bounded_rc" -ne 124 ] || {
    echo "FAIL: break-glass restart_wan exceeded the outer 5-second safety bound" >&2
    exit 1
}
[ "$service_bounded_rc" -ne 0 ] || {
    echo "FAIL: hanging restart_wan was reported as success" >&2
    exit 1
}
printf '%s\n' "$service_bounded_output" | grep -F 'WAN_RESTART=FAIL' >/dev/null
printf '%s\n' "$service_bounded_output" | grep -F 'BREAKGLASS_RESULT=FAIL' >/dev/null
rm -f "$HANG_SERVICE"

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

echo "=== transient bootstrap failure after WAN recovery ==="
reset_fixture
: >"$FAIL_FALLBACK_ONCE"

set +e
transient_output="$(run_helper on 2>&1)"
transient_rc=$?
set -e

printf '%s\n' "$transient_output" |
    grep -E '^(FALLBACK=|FALLBACK_REASSERT=|BREAKGLASS_RESULT=)' || true

if [ "$transient_rc" -ne 0 ] ||
   ! printf '%s\n' "$transient_output" |
       grep -Fq 'BREAKGLASS_RESULT=PASS'; then
    echo "FAIL: transient bootstrap failure was not recovered" >&2
    exit 1
fi

echo "TRANSIENT_BOOTSTRAP_RECOVERY=PASS"

echo "=== transient Internet IP failure after WAN restart ==="
reset_fixture
: >"$FAIL_INTERNET_ONCE"

set +e
ip_transient_output="$(run_helper on 2>&1)"
ip_transient_rc=$?
set -e

printf '%s\n' "$ip_transient_output" |
    grep -E '^(WAN_RESTART|WAN_IP|INTERNET_IP|BREAKGLASS_RESULT)=' || true

if [ "$ip_transient_rc" -ne 0 ] ||
   ! printf '%s\n' "$ip_transient_output" |
       grep -Fq 'BREAKGLASS_RESULT=PASS'; then
    echo "FAIL: transient post-WAN Internet IP failure was not recovered" >&2
    exit 1
fi

if ! printf '%s\\n' "$ip_transient_output" |
    grep -Fxq 'INTERNET_IP_ATTEMPTS=2'; then
    echo "FAIL: expected Internet IP recovery on attempt 2" >&2
    exit 1
fi

echo "TRANSIENT_INTERNET_IP_RECOVERY=PASS"

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

echo "=== transient final DNS failure after WAN restart ==="
reset_fixture
: >"$FAIL_DNS_ONCE"

dns_transient_rc=0
dns_transient_output="$(run_helper on 2>&1)" ||
    dns_transient_rc=$?

printf '%s\n' "$dns_transient_output" |
    grep -E '^(DNS=|BREAKGLASS_RESULT=)' || true

if [ "$dns_transient_rc" -ne 0 ] ||
   ! printf '%s\n' "$dns_transient_output" |
       grep -Fxq 'BREAKGLASS_RESULT=PASS'; then
    echo "FAIL: transient final DNS failure was not recovered" >&2
    exit 1
fi

if ! printf '%s\\n' "$dns_transient_output" |
    grep -Fxq 'DNS_ATTEMPTS=2'; then
    echo "FAIL: expected final DNS recovery on attempt 2" >&2
    exit 1
fi

echo "TRANSIENT_FINAL_DNS_RECOVERY=PASS"

echo "=== transient bootstrap failure during break-glass off ==="
reset_fixture

run_helper on >/dev/null
: >"$FAIL_FALLBACK_ONCE"

off_rc=0
off_output="$(run_helper off 2>&1)" || off_rc=$?

printf '%s\n' "$off_output" |
    grep -E '^(FALLBACK=|BOOTSTRAP_REASSERT_|FALLBACK_REASSERT=|BREAKGLASS_CLEAR_RESULT=|WAN_DNS_SNAPSHOT=)' || true

if [ "$off_rc" -ne 0 ] ||
   ! printf '%s\n' "$off_output" |
       grep -Fxq 'BOOTSTRAP_REASSERT_ATTEMPTS=2' ||
   ! printf '%s\n' "$off_output" |
       grep -Fxq 'BREAKGLASS_CLEAR_RESULT=PASS'; then
    echo "FAIL: transient bootstrap failure blocked break-glass off" >&2
    exit 1
fi

restart_count="$(grep -c '^restart_wan$' "$SERVICE_LOG" || true)"

if [ "$restart_count" -ne 2 ]; then
    echo "FAIL: unexpected WAN restart count: $restart_count" >&2
    exit 1
fi

if [ -f "$WAN_STATE" ] ||
   ! grep -qx '0' "$WAN_VALUE" ||
   ! grep -qx '0' "$WAN0_VALUE" ||
   ! grep -qx 'nameserver 192.0.2.53' "$RESOLV"; then
    echo "FAIL: break-glass off did not restore original state" >&2
    exit 1
fi

echo "TRANSIENT_BREAKGLASS_OFF_RECOVERY=PASS"
echo "WAN_RESTART_COUNT=2"
echo "SNAPSHOT_RESTORED_AND_REMOVED=PASS"

echo "=== permanent bootstrap failure is bounded ==="
reset_fixture
: >"$FAIL_FALLBACK_ALWAYS"

permanent_rc=0
permanent_output="$(run_helper on 2>&1)" ||
    permanent_rc=$?

printf '%s\n' "$permanent_output" |
    grep -E '^(BOOTSTRAP_REASSERT|BREAKGLASS_RESULT=)' || true

retry_count="$(printf '%s\n' "$permanent_output" |
    grep -c '^BOOTSTRAP_REASSERT_RETRY=' || true)"

restart_count="$(grep -c '^restart_wan$' "$SERVICE_LOG" || true)"

if [ "$permanent_rc" -eq 0 ] ||
   [ "$retry_count" -ne 3 ] ||
   [ "$restart_count" -ne 1 ] ||
   ! printf '%s\n' "$permanent_output" |
       grep -Fxq 'BOOTSTRAP_REASSERT=FAILED_AFTER_RETRIES' ||
   ! printf '%s\n' "$permanent_output" |
       grep -Fxq 'BREAKGLASS_RESULT=FAIL' ||
   [ ! -f "$WAN_STATE" ] ||
   [ "$(cat "$WAN_VALUE")" != 1 ] ||
   [ "$(cat "$WAN0_VALUE")" != 1 ]; then
    echo "FAIL: permanent bootstrap failure handling is unsafe" >&2
    exit 1
fi

echo "PERMANENT_BOOTSTRAP_FAILURE=PASS"
echo "BOOTSTRAP_TOTAL_ATTEMPTS=4"
echo "WAN_RESTART_COUNT=1"
echo "RECOVERY_SNAPSHOT=PRESERVED"

echo "=== slow bootstrap total time budget ==="
reset_fixture
: >"$SLOW_FALLBACK"

slow_rc=0
slow_output="$(
    timeout -k 1s 9s env \
        EDGE_DNS_GUARD="$GUARD" \
        EDGE_RESOLV_CONF="$RESOLV" \
        EDGE_DNS_STATE_DIR="$STATE_DIR" \
        EDGE_DNS_BREAKGLASS_WAN_STATE="$WAN_STATE" \
        EDGE_BUSYBOX_BIN="$MOCK_BIN/busybox" \
        EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
        EDGE_DNS_BREAKGLASS_WAN_WAIT_SECONDS=1 \
        EDGE_DNS_BREAKGLASS_DNS_TIMEOUT_SECONDS=1 \
        EDGE_DNS_BREAKGLASS_SERVICE_TIMEOUT_SECONDS=1 \
        EDGE_DNS_BREAKGLASS_BOOTSTRAP_TOTAL_TIMEOUT_SECONDS=5 \
        sh "$HELPER" on 2>&1
)" || slow_rc=$?

echo "SLOW_BOOTSTRAP_RC=$slow_rc"

if [ "$slow_rc" -eq 124 ] || [ "$slow_rc" -eq 137 ]; then
    echo "FAIL: bootstrap retries exceeded outer time bound" >&2
    exit 1
fi

if [ "$slow_rc" -eq 0 ] ||
   [ ! -f "$WAN_STATE" ] ||
   ! printf '%s\n' "$slow_output" |
       grep -Fxq 'BREAKGLASS_RESULT=FAIL'; then
    echo "FAIL: unsafe slow bootstrap recovery verdict" >&2
    exit 1
fi

if ! printf '%s\n' "$slow_output" |
    grep -Fxq 'BOOTSTRAP_REASSERT=TIME_BUDGET_EXHAUSTED'; then
    echo "FAIL: bootstrap retry budget was not enforced" >&2
    exit 1
fi

echo "SLOW_BOOTSTRAP_BUDGET=PASS"

echo "=== single stalled fallback exceeds bootstrap budget ==="
reset_fixture
: >"$STALL_FALLBACK"

stall_rc=0
stall_output="$(
    timeout -k 1s 6s env \
        EDGE_DNS_GUARD="$GUARD" \
        EDGE_RESOLV_CONF="$RESOLV" \
        EDGE_DNS_STATE_DIR="$STATE_DIR" \
        EDGE_DNS_BREAKGLASS_WAN_STATE="$WAN_STATE" \
        EDGE_BUSYBOX_BIN="$MOCK_BIN/busybox" \
        EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
        EDGE_DNS_BREAKGLASS_WAN_WAIT_SECONDS=1 \
        EDGE_DNS_BREAKGLASS_DNS_TIMEOUT_SECONDS=1 \
        EDGE_DNS_BREAKGLASS_SERVICE_TIMEOUT_SECONDS=1 \
        EDGE_DNS_BREAKGLASS_BOOTSTRAP_TOTAL_TIMEOUT_SECONDS=2 \
        sh "$HELPER" on 2>&1
)" || stall_rc=$?

echo "STALLED_FALLBACK_RC=$stall_rc"

if [ "$stall_rc" -eq 124 ] || [ "$stall_rc" -eq 137 ]; then
    echo "FAIL: one stalled fallback exceeded total bootstrap budget" >&2
    exit 1
fi

if [ "$stall_rc" -eq 0 ] ||
   [ ! -f "$WAN_STATE" ] ||
   ! printf '%s\n' "$stall_output" |
       grep -Fxq 'BREAKGLASS_RESULT=FAIL'; then
    echo "FAIL: stalled fallback recovery verdict was unsafe" >&2
    exit 1
fi

flock -n "$STALL_LOCK" true || {
    echo "FAIL: stalled DNS Guard child retained flock after timeout" >&2
    exit 1
}
echo "SUPERVISOR_FLOCK_RELEASE=PASS"
echo "SINGLE_FALLBACK_BUDGET=PASS"

echo "=== break-glass DNS validation is explicitly bounded ==="
reset_fixture
: >"$HANG_DNS"
set +e
bounded_output="$(
    timeout 7 env \
        EDGE_DNS_GUARD="$GUARD" \
        EDGE_RESOLV_CONF="$RESOLV" \
        EDGE_DNS_STATE_DIR="$STATE_DIR" \
        EDGE_DNS_BREAKGLASS_WAN_STATE="$WAN_STATE" \
        EDGE_BUSYBOX_BIN="$MOCK_BIN/busybox" \
        EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
        EDGE_DNS_BREAKGLASS_WAN_WAIT_SECONDS=1 \
        EDGE_DNS_BREAKGLASS_DNS_TIMEOUT_SECONDS=1 \
        EDGE_DNS_BREAKGLASS_SERVICE_TIMEOUT_SECONDS=1 \
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
[ -s "$HANG_DNS_CHILD" ] || {
    echo "FAIL: escaped DNS child fixture did not start" >&2
    exit 1
}
if kill -0 "$(cat "$HANG_DNS_CHILD")" 2>/dev/null; then
    echo "FAIL: escaped DNS child survived supervisor timeout" >&2
    exit 1
fi
echo "DNS_ESCAPE_CHILD_REAP=PASS"

flock -n "$HANG_DNS_LOCK" true || {
    echo "FAIL: escaped DNS child retained flock" >&2
    exit 1
}
echo "DNS_ESCAPE_FLOCK_RELEASE=PASS"

rm -f "$HANG_DNS"

echo "=== concurrent break-glass transactions are rejected ==="
reset_fixture
rm -f "$BREAKGLASS_HOLD_STARTED"
: >"$HOLD_BREAKGLASS_ON"

first_log="$TMP_DIR/concurrent-first.log"
run_helper on >"$first_log" 2>&1 &
first_pid=$!

attempt=0
while [ ! -f "$BREAKGLASS_HOLD_STARTED" ] &&
      [ "$attempt" -lt 100 ]; do
    /bin/sleep 0.05
    attempt=$((attempt + 1))
done

if [ ! -f "$BREAKGLASS_HOLD_STARTED" ] ||
   ! kill -0 "$first_pid" 2>/dev/null; then
    echo "FAIL: first transaction did not enter the hold" >&2
    cat "$first_log" >&2
    exit 1
fi

lock_file="$STATE_DIR/dns-breakglass-operation.lock"

if flock -n "$lock_file" /bin/true 2>/dev/null; then
    echo "FAIL: transaction lock was not held" >&2
    exit 1
fi

[ -f "$WAN_STATE" ] || {
    echo "FAIL: first transaction did not preserve snapshot" >&2
    exit 1
}

cp "$WAN_STATE" "$TMP_DIR/concurrent-snapshot-before"

for action in off on; do
    if busy_output="$(run_helper "$action" 2>&1)"; then
        echo "FAIL: concurrent $action was accepted" >&2
        exit 1
    fi

    printf '%s\n' "$busy_output" |
        grep -Fxq 'BREAKGLASS_OPERATION_LOCK=BUSY' || {
            echo "FAIL: concurrent $action missed busy verdict" >&2
            exit 1
        }
done

cmp -s "$WAN_STATE" "$TMP_DIR/concurrent-snapshot-before" || {
    echo "FAIL: concurrent operation changed snapshot" >&2
    exit 1
}

if [ -e "$NVRAM_LOG" ] || [ -e "$SERVICE_LOG" ]; then
    echo "FAIL: rejected operation changed NVRAM or WAN dispatch" >&2
    exit 1
fi

echo "CONCURRENT_ON_OFF_REJECTED=PASS"
echo "CONCURRENT_SNAPSHOT_PRESERVED=PASS"
echo "CONCURRENT_NO_WAN_DISPATCH=PASS"

if ! wait "$first_pid"; then
    echo "FAIL: first transaction did not complete" >&2
    cat "$first_log" >&2
    exit 1
fi

grep -Fq 'BREAKGLASS_RESULT=PASS' "$first_log" || {
    echo "FAIL: first transaction verdict missing" >&2
    exit 1
}

rm -f "$HOLD_BREAKGLASS_ON"

flock -n "$lock_file" /bin/true || {
    echo "FAIL: transaction lock remained held" >&2
    exit 1
}

clear_output="$(run_helper off)"
printf '%s\n' "$clear_output" |
    grep -Fq 'BREAKGLASS_CLEAR_RESULT=PASS'

[ ! -f "$WAN_STATE" ] || {
    echo "FAIL: snapshot remained after clear" >&2
    exit 1
}

echo "OPERATION_LOCK_RELEASE=PASS"
echo "POST_CONTENTION_RECOVERY=PASS"

echo "PASS: break-glass snapshot, restore, ordering and final recovery verdict"
