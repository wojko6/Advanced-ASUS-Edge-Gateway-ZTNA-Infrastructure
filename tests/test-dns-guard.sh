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
RUNTIME_STATE_DIR="$TMP_DIR/runtime"
FLAG="$STATE_DIR/dns-breakglass"
RECOVERY_STREAK_FILE="$RUNTIME_STATE_DIR/recovery-success-streak"
FAIL_LOCAL="$TMP_DIR/fail-local"
FAIL_BOOTSTRAP="$TMP_DIR/fail-bootstrap"
BOOTSTRAP_PRIMARY="$TMP_DIR/bootstrap-primary"
BOOTSTRAP_SECONDARY="$TMP_DIR/bootstrap-secondary"
BUSYBOX_MOCK="$TMP_DIR/busybox"
QUERY_ACTIVE="$TMP_DIR/query-active"
QUERY_STARTED="$TMP_DIR/query-started"
QUERY_COLLISION="$TMP_DIR/query-collision"
PROBE_LOG="$TMP_DIR/probe.log"
FAIL_PROBE_PRIMARY="$TMP_DIR/fail-probe-primary"
FAIL_PROBE_SECONDARY="$TMP_DIR/fail-probe-secondary"
FAIL_TCP_PRIMARY="$TMP_DIR/fail-tcp-primary"
FAIL_TCP_SECONDARY="$TMP_DIR/fail-tcp-secondary"
FAIL_DIG_RUNTIME="$TMP_DIR/fail-dig-runtime"
FAIL_PIHOLE_TCP_LISTENER="$TMP_DIR/fail-pihole-tcp-listener"
FAIL_BOOTSTRAP_HEALTH="$TMP_DIR/fail-bootstrap-health"
HANG_PROBE="$TMP_DIR/hang-probe"
HANG_LOGGER="$TMP_DIR/hang-logger"
LOCK_HELD="$TMP_DIR/lock-held"
FAIL_BOOTSTRAP_PRIMARY_SERVER="$TMP_DIR/fail-bootstrap-primary-server"

mkdir -p "$MOCK_BIN" "$STATE_DIR" "$RUNTIME_STATE_DIR"

cat >"$CONFIG" <<'EOF'
EDGE_UNBOUND_PORT=53535
EDGE_DNS_LOCAL_RESOLVER_IP=192.0.2.53
EDGE_DNS_FAILBACK_SUCCESS_THRESHOLD=1
EDGE_DNS_QUERY_TIMEOUT_SECONDS=2
EDGE_DNS_LOCK_WAIT_SECONDS=2
EOF

cat >"$MOCK_BIN/nvram" <<EOF
#!/bin/sh
[ "\$1" = "get" ] || exit 1
case "\$2" in
    ntp_ready) echo 1 ;;
    wan0_dns_r)
        if [ ! -f "$FAIL_BOOTSTRAP" ]; then
            if [ -f "$BOOTSTRAP_PRIMARY" ]; then
                cat "$BOOTSTRAP_PRIMARY"
            else
                echo "9.9.9.9 149.112.112.112"
            fi
        fi
        ;;
    wan0_dns)
        if [ ! -f "$FAIL_BOOTSTRAP" ] && [ -f "$BOOTSTRAP_SECONDARY" ]; then
            cat "$BOOTSTRAP_SECONDARY"
        fi
        ;;
    wan_dns_r|wan_dns) echo "" ;;
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
echo 'tcp 0 0 127.0.0.1:53535 0.0.0.0:* LISTEN'
echo 'udp 0 0 192.0.2.53:53 0.0.0.0:*'
[ -f "$FAIL_PIHOLE_TCP_LISTENER" ] ||
    echo 'tcp 0 0 192.0.2.53:53 0.0.0.0:* LISTEN'
EOF

cat >"$MOCK_BIN/logger" <<EOF
#!/bin/sh
[ -f "$HANG_LOGGER" ] && /bin/sleep 30
exit 0
EOF

cat >"$BUSYBOX_MOCK" <<EOF
#!/bin/sh
applet="\$1"
shift
case "\$applet" in
    timeout)
        exec /usr/bin/timeout "\$@"
        ;;
    nslookup)
        probe_name="\${1:-}"
        probe_server="\${2:-}"
        printf 'udp %s %s\n' "\$probe_name" "\$probe_server" >>"$PROBE_LOG"

        [ -f "$HANG_PROBE" ] && sleep 30

        if [ -n "\${EDGE_DNS_TEST_QUERY_SERIALIZE:-}" ]; then
            [ -f "$QUERY_ACTIVE" ] && : >"$QUERY_COLLISION"
            : >"$QUERY_ACTIVE"
            : >"$QUERY_STARTED"
            sleep 1
            rm -f "$QUERY_ACTIVE"
        fi

        case "\$probe_name" in
            example.com)
                [ -f "$FAIL_BOOTSTRAP_HEALTH" ] && exit 1
                echo "Server: \${probe_server:-9.9.9.9}"
                echo "Name: example.com"
                echo "Address 1: 93.184.216.34"
                ;;
            one.one.one.one)
                [ -f "$FAIL_PROBE_PRIMARY" ] && exit 1
                echo "Server: 192.0.2.53"
                echo "Address 1: 1.1.1.1"
                ;;
            dns.google)
                [ -f "$FAIL_PROBE_SECONDARY" ] && exit 1
                echo "Server: 192.0.2.53"
                echo "Address 1: 8.8.8.8"
                ;;
            *)
                exit 1
                ;;
        esac
        exit 0
        ;;
    cmp)
        cmp "\$@"
        ;;
    *)
        exit 127
        ;;
esac
EOF

cat >"$MOCK_BIN/dig" <<EOF
#!/bin/sh

case " \$* " in
    *" -v "*)
        [ -f "$FAIL_DIG_RUNTIME" ] && exit 1
        echo "DiG mock"
        exit 0
        ;;
esac

printf 'tcp %s\n' "\$*" >>"$PROBE_LOG"

case " \$* " in
    *" one.one.one.one "*)
        [ -f "$FAIL_TCP_PRIMARY" ] && exit 1
        echo "1.0.0.1"
        ;;
    *" dns.google "*)
        [ -f "$FAIL_TCP_SECONDARY" ] && exit 1
        echo "8.8.4.4"
        ;;
    *)
        exit 1
        ;;
esac
EOF

chmod +x "$MOCK_BIN/nvram" "$MOCK_BIN/pidof" "$MOCK_BIN/netstat" \
    "$MOCK_BIN/logger" "$MOCK_BIN/dig" "$BUSYBOX_MOCK"

run_guard() {
    EDGE_CONFIG_FILE="$CONFIG"     EDGE_RESOLV_CONF="$RESOLV"     EDGE_DNS_STATE_DIR="$STATE_DIR"     EDGE_DNS_RUNTIME_STATE_DIR="$RUNTIME_STATE_DIR"     EDGE_DNS_BREAKGLASS_FLAG="$FLAG"     EDGE_TEST_PATH_PREFIX="$MOCK_BIN"     EDGE_BUSYBOX_BIN="$BUSYBOX_MOCK"         sh "$GUARD" "$@"
}

printf '%s\n'     'nameserver 9.9.9.9'     'nameserver 149.112.112.112'     >"$RESOLV"

echo "=== concurrent invocations are serialized ==="
rm -f "$QUERY_ACTIVE" "$QUERY_STARTED" "$QUERY_COLLISION"

EDGE_DNS_TEST_QUERY_SERIALIZE=1 run_guard auto >"$TMP_DIR/lock-first.out" 2>&1 &
first_pid=$!

lock_wait=0
while [ ! -f "$QUERY_STARTED" ] && [ "$lock_wait" -lt 50 ]; do
    lock_wait=$((lock_wait + 1))
    sleep 0.1
done

[ -f "$QUERY_STARTED" ] || {
    echo "FAIL: first DNS Guard invocation did not reach the serialized query section" >&2
    kill "$first_pid" 2>/dev/null || true
    wait "$first_pid" 2>/dev/null || true
    exit 1
}

EDGE_DNS_TEST_QUERY_SERIALIZE=1 run_guard auto >"$TMP_DIR/lock-second.out" 2>&1 &
second_pid=$!

wait "$first_pid"
wait "$second_pid"

[ ! -f "$QUERY_COLLISION" ] || {
    echo "FAIL: concurrent DNS Guard invocations overlapped inside the critical section" >&2
    exit 1
}
grep -F 'AUTO=LOCAL_DNS' "$TMP_DIR/lock-first.out" >/dev/null
grep -F 'AUTO=LOCAL_DNS' "$TMP_DIR/lock-second.out" >/dev/null

echo "=== lock acquisition is bounded ==="
rm -f "$LOCK_HELD"
(
    exec 8>"$STATE_DIR/dns-guard.lock"
    flock -x 8
    : >"$LOCK_HELD"
    /bin/sleep 5
) &
lock_holder_pid=$!

lock_wait=0
while [ ! -f "$LOCK_HELD" ] && [ "$lock_wait" -lt 50 ]; do
    lock_wait=$((lock_wait + 1))
    /bin/sleep 0.1
done

[ -f "$LOCK_HELD" ] || {
    echo "FAIL: test lock holder did not acquire DNS Guard lock" >&2
    kill "$lock_holder_pid" 2>/dev/null || true
    wait "$lock_holder_pid" 2>/dev/null || true
    exit 1
}

set +e
lock_blocked_output="$(
    timeout 5 env \
        EDGE_CONFIG_FILE="$CONFIG" \
        EDGE_RESOLV_CONF="$RESOLV" \
        EDGE_DNS_STATE_DIR="$STATE_DIR" \
        EDGE_DNS_RUNTIME_STATE_DIR="$RUNTIME_STATE_DIR" \
        EDGE_DNS_BREAKGLASS_FLAG="$FLAG" \
        EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
        EDGE_BUSYBOX_BIN="$BUSYBOX_MOCK" \
        sh "$GUARD" status 2>&1
)"
lock_blocked_rc=$?
set -e

[ "$lock_blocked_rc" -ne 124 ] || {
    echo "FAIL: DNS Guard waited indefinitely on the global lock" >&2
    kill "$lock_holder_pid" 2>/dev/null || true
    wait "$lock_holder_pid" 2>/dev/null || true
    exit 1
}
[ "$lock_blocked_rc" -ne 0 ] || {
    echo "FAIL: DNS Guard unexpectedly acquired a held lock" >&2
    kill "$lock_holder_pid" 2>/dev/null || true
    wait "$lock_holder_pid" 2>/dev/null || true
    exit 1
}
printf '%s\n' "$lock_blocked_output" |
    grep -F 'cannot acquire DNS Guard lock within' >/dev/null

kill "$lock_holder_pid" 2>/dev/null || true
wait "$lock_holder_pid" 2>/dev/null || true
rm -f "$LOCK_HELD"

echo "=== logger hang cannot block DNS Guard recovery ==="
: >"$HANG_LOGGER"
set +e
logger_bounded_output="$(
    timeout 5 env \
        EDGE_CONFIG_FILE="$CONFIG" \
        EDGE_RESOLV_CONF="$RESOLV" \
        EDGE_DNS_STATE_DIR="$STATE_DIR" \
        EDGE_DNS_RUNTIME_STATE_DIR="$RUNTIME_STATE_DIR" \
        EDGE_DNS_BREAKGLASS_FLAG="$FLAG" \
        EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
        EDGE_BUSYBOX_BIN="$BUSYBOX_MOCK" \
        EDGE_DNS_LOG_TIMEOUT_SECONDS=1 \
        sh "$GUARD" breakglass-on logger-hang 2>&1
)"
logger_bounded_rc=$?
set -e
[ "$logger_bounded_rc" -ne 124 ] || {
    echo "FAIL: DNS Guard logger blocked recovery beyond the outer 5-second safety bound" >&2
    exit 1
}
[ "$logger_bounded_rc" -eq 0 ] || {
    echo "FAIL: bounded logger failure changed break-glass semantics" >&2
    printf '%s\n' "$logger_bounded_output" >&2
    exit 1
}
printf '%s\n' "$logger_bounded_output" | grep -F 'BREAKGLASS=ACTIVE' >/dev/null
rm -f "$HANG_LOGGER" "$FLAG"

echo "=== stable multi-provider DNS probes use UDP and TCP when dig is available ==="
rm -f "$PROBE_LOG" "$FAIL_PROBE_PRIMARY" "$FAIL_PROBE_SECONDARY" \
    "$FAIL_TCP_PRIMARY" "$FAIL_TCP_SECONDARY" "$FAIL_PIHOLE_TCP_LISTENER"

ready_output="$(run_guard ready)"
printf '%s\n' "$ready_output"
grep -F 'READY=PASS' <<EOF >/dev/null
$ready_output
EOF
grep -F 'udp one.one.one.one' "$PROBE_LOG" >/dev/null
grep -F 'tcp ' "$PROBE_LOG" | grep -F ' one.one.one.one ' >/dev/null
if grep -E 'sslip\.io|edge-health-' "$PROBE_LOG" >/dev/null; then
    echo "FAIL: DNS Guard still generated unique external probe names" >&2
    exit 1
fi

echo "=== unusable optional dig does not make local DNS unhealthy ==="
: >"$FAIL_DIG_RUNTIME"
rm -f "$PROBE_LOG"

broken_dig_output="$(run_guard ready)"
printf '%s\n' "$broken_dig_output"

grep -F 'READY=PASS' <<EOF >/dev/null
$broken_dig_output
EOF

grep -F 'udp one.one.one.one' "$PROBE_LOG" >/dev/null

if grep -F 'tcp ' "$PROBE_LOG" >/dev/null; then
    echo "FAIL: DNS Guard attempted active TCP query with unusable dig" >&2
    exit 1
fi

rm -f "$FAIL_DIG_RUNTIME"

echo "=== secondary provider keeps health independent from primary probe ==="
: >"$FAIL_PROBE_PRIMARY"
secondary_ready_output="$(run_guard ready)"
printf '%s\n' "$secondary_ready_output"
grep -F 'READY=PASS' <<EOF >/dev/null
$secondary_ready_output
EOF
grep -F 'udp dns.google' "$PROBE_LOG" >/dev/null
grep -F 'tcp ' "$PROBE_LOG" | grep -F ' dns.google ' >/dev/null
rm -f "$FAIL_PROBE_PRIMARY"

echo "=== TCP probe failure on primary falls through to secondary ==="
: >"$FAIL_TCP_PRIMARY"
tcp_secondary_output="$(run_guard ready)"
printf '%s\n' "$tcp_secondary_output"
grep -F 'READY=PASS' <<EOF >/dev/null
$tcp_secondary_output
EOF
grep -F 'udp dns.google' "$PROBE_LOG" >/dev/null
rm -f "$FAIL_TCP_PRIMARY"

echo "=== both providers failing makes local DNS unhealthy ==="
: >"$FAIL_PROBE_PRIMARY"
: >"$FAIL_PROBE_SECONDARY"
if both_failed_output="$(run_guard ready 2>&1)"; then
    echo "FAIL: DNS Guard accepted local DNS while both fixed probes failed" >&2
    exit 1
fi
printf '%s\n' "$both_failed_output"
grep -F 'READY=FAIL' <<EOF >/dev/null
$both_failed_output
EOF
rm -f "$FAIL_PROBE_PRIMARY" "$FAIL_PROBE_SECONDARY"

echo "=== Pi-hole must expose both UDP and TCP port 53 listeners ==="
: >"$FAIL_PIHOLE_TCP_LISTENER"
if listener_failed_output="$(run_guard ready 2>&1)"; then
    echo "FAIL: DNS Guard accepted Pi-hole without TCP/53 listener" >&2
    exit 1
fi
printf '%s\n' "$listener_failed_output"
grep -F 'READY=FAIL' <<EOF >/dev/null
$listener_failed_output
EOF
rm -f "$FAIL_PIHOLE_TCP_LISTENER"

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

echo "=== bootstrap DNS filters invalid, local, loopback and duplicate candidates ==="
cat >"$CONFIG" <<'EOF'
EDGE_UNBOUND_PORT=53535
EDGE_DNS_LOCAL_RESOLVER_IP=192.0.2.53
EDGE_DNS_FAILBACK_SUCCESS_THRESHOLD=1
EOF
rm -f "$FAIL_BOOTSTRAP" "$BOOTSTRAP_SECONDARY"
printf '%s\n' '127.0.0.1 192.0.2.53 9.9.9.9 9.9.9.9 149.112.112.112 999.1.1.1 0.0.0.0' >"$BOOTSTRAP_PRIMARY"
printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"

filtered_output="$(run_guard fallback)"
printf '%s\n' "$filtered_output"
grep -F 'FALLBACK=PASS' <<EOF >/dev/null
$filtered_output
EOF
[ "$(grep -c '^nameserver 9\.9\.9\.9$' "$RESOLV")" -eq 1 ]
[ "$(grep -c '^nameserver 149\.112\.112\.112$' "$RESOLV")" -eq 1 ]
[ "$(grep -c '^nameserver ' "$RESOLV")" -eq 2 ]
! grep -F 'nameserver 127.0.0.1' "$RESOLV" >/dev/null
! grep -F 'nameserver 192.0.2.53' "$RESOLV" >/dev/null
! grep -F 'nameserver 0.0.0.0' "$RESOLV" >/dev/null

echo "=== bootstrap DNS falls through when higher-priority source has no valid candidates ==="
printf '%s\n' '127.0.0.1 192.0.2.53 999.1.1.1' >"$BOOTSTRAP_PRIMARY"
printf '%s\n' '8.8.8.8 8.8.8.8 1.1.1.1' >"$BOOTSTRAP_SECONDARY"
printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"

secondary_output="$(run_guard fallback)"
printf '%s\n' "$secondary_output"
grep -F 'FALLBACK=PASS' <<EOF >/dev/null
$secondary_output
EOF
grep -qx 'nameserver 8.8.8.8' "$RESOLV"
grep -qx 'nameserver 1.1.1.1' "$RESOLV"
[ "$(grep -c '^nameserver 8\.8\.8\.8$' "$RESOLV")" -eq 1 ]
[ "$(grep -c '^nameserver ' "$RESOLV")" -eq 2 ]

echo "=== valid later WAN DNS source rescues a dead higher-priority source ==="
printf '%s\n' '9.9.9.9' >"$BOOTSTRAP_PRIMARY"
printf '%s\n' '8.8.8.8' >"$BOOTSTRAP_SECONDARY"
printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"
: >"$FAIL_BOOTSTRAP_PRIMARY_SERVER"

later_source_output="$(run_guard fallback)"
printf '%s\n' "$later_source_output"
grep -F 'FALLBACK=PASS' <<EOF >/dev/null
$later_source_output
EOF
grep -qx 'nameserver 9.9.9.9' "$RESOLV"
grep -qx 'nameserver 8.8.8.8' "$RESOLV"
[ "$(grep -c '^nameserver ' "$RESOLV")" -eq 2 ]
rm -f "$FAIL_BOOTSTRAP_PRIMARY_SERVER"

echo "=== bootstrap DNS refuses all-local or invalid candidate sets ==="
printf '%s\n' '127.0.0.1 192.0.2.53 0.0.0.0 999.1.1.1' >"$BOOTSTRAP_PRIMARY"
printf '%s\n' '127.0.0.2 192.0.2.53' >"$BOOTSTRAP_SECONDARY"
printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"

if rejected_output="$(run_guard fallback 2>&1)"; then
    echo "FAIL: fallback accepted a bootstrap set without an independent resolver" >&2
    exit 1
fi
printf '%s\n' "$rejected_output"
grep -F 'FALLBACK=FAILED' <<EOF >/dev/null
$rejected_output
EOF
grep -qx 'nameserver 192.0.2.53' "$RESOLV"

rm -f "$BOOTSTRAP_PRIMARY" "$BOOTSTRAP_SECONDARY"

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

echo "=== syntactically valid but dead bootstrap DNS is not reported as healthy ==="
cat >"$CONFIG" <<'EOF'
EDGE_UNBOUND_PORT=53535
EDGE_DNS_LOCAL_RESOLVER_IP=192.0.2.53
EDGE_DNS_FAILBACK_SUCCESS_THRESHOLD=1
EDGE_DNS_QUERY_TIMEOUT_SECONDS=1
EDGE_DNS_LOCK_WAIT_SECONDS=2
EOF
rm -f "$FAIL_BOOTSTRAP" "$BOOTSTRAP_PRIMARY" "$BOOTSTRAP_SECONDARY"
printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"
: >"$FAIL_BOOTSTRAP_HEALTH"

if dead_bootstrap_output="$(run_guard fallback 2>&1)"; then
    echo "FAIL: DNS Guard reported fallback success although every bootstrap DNS probe failed" >&2
    exit 1
fi
printf '%s\n' "$dead_bootstrap_output"
grep -F 'FALLBACK=UNHEALTHY_BOOTSTRAP' <<EOF >/dev/null
$dead_bootstrap_output
EOF
grep -qx 'nameserver 9.9.9.9' "$RESOLV"
grep -qx 'nameserver 149.112.112.112' "$RESOLV"

dead_metrics="$(run_guard metrics)"
printf '%s\n' "$dead_metrics" | grep -qx 'asus_edge_dns_guard_bootstrap_dns_healthy 0'
dead_check_epoch="$(printf '%s\n' "$dead_metrics" | awk '$1=="asus_edge_dns_guard_bootstrap_dns_last_check_timestamp_seconds"{print $2}')"
[ "$dead_check_epoch" -gt 0 ]

rm -f "$FAIL_BOOTSTRAP_HEALTH"
recovered_bootstrap_output="$(run_guard fallback)"
printf '%s\n' "$recovered_bootstrap_output"
grep -F 'FALLBACK=ALREADY_BOOTSTRAP' <<EOF >/dev/null
$recovered_bootstrap_output
EOF
healthy_metrics="$(run_guard metrics)"
printf '%s\n' "$healthy_metrics" | grep -qx 'asus_edge_dns_guard_bootstrap_dns_healthy 1'

echo "=== hanging UDP DNS probe is bounded ==="
: >"$HANG_PROBE"
set +e
bounded_output="$(
    timeout 5 env \
        EDGE_CONFIG_FILE="$CONFIG" \
        EDGE_RESOLV_CONF="$RESOLV" \
        EDGE_DNS_STATE_DIR="$STATE_DIR" \
        EDGE_DNS_RUNTIME_STATE_DIR="$RUNTIME_STATE_DIR" \
        EDGE_DNS_BREAKGLASS_FLAG="$FLAG" \
        EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
        EDGE_BUSYBOX_BIN="$BUSYBOX_MOCK" \
        sh "$GUARD" ready 2>&1
)"
bounded_rc=$?
set -e
[ "$bounded_rc" -ne 124 ] || {
    echo "FAIL: DNS Guard UDP probe exceeded the outer 5-second safety bound" >&2
    exit 1
}
[ "$bounded_rc" -ne 0 ] || {
    echo "FAIL: hanging DNS probe was treated as healthy" >&2
    exit 1
}
printf '%s\n' "$bounded_output" | grep -F 'READY=FAIL' >/dev/null
rm -f "$HANG_PROBE"

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

echo "=== dead bootstrap is escaped immediately once local DNS is healthy ==="
cat >"$CONFIG" <<'EOF'
EDGE_UNBOUND_PORT=53535
EDGE_DNS_LOCAL_RESOLVER_IP=192.0.2.53
EDGE_DNS_FAILBACK_SUCCESS_THRESHOLD=3
EDGE_DNS_QUERY_TIMEOUT_SECONDS=2
EDGE_DNS_LOCK_WAIT_SECONDS=2
EOF
rm -f "$FAIL_LOCAL" "$RECOVERY_STREAK_FILE"
printf '%s\n' 'nameserver 9.9.9.9' 'nameserver 149.112.112.112' >"$RESOLV"
: >"$FAIL_BOOTSTRAP_HEALTH"

dead_escape_output="$(run_guard auto)"
printf '%s\n' "$dead_escape_output"
grep -F 'AUTO=LOCAL_DNS_BOOTSTRAP_UNHEALTHY' <<EOF >/dev/null
$dead_escape_output
EOF
grep -qx 'nameserver 192.0.2.53' "$RESOLV"
[ ! -f "$RECOVERY_STREAK_FILE" ]
rm -f "$FAIL_BOOTSTRAP_HEALTH"

echo "=== failback hysteresis requires consecutive healthy checks ==="
cat >"$CONFIG" <<'EOF'
EDGE_UNBOUND_PORT=53535
EDGE_DNS_LOCAL_RESOLVER_IP=192.0.2.53
EDGE_DNS_FAILBACK_SUCCESS_THRESHOLD=3
EOF
rm -f "$FAIL_LOCAL" "$RECOVERY_STREAK_FILE"
printf '%s\n' 'nameserver 9.9.9.9' 'nameserver 149.112.112.112' >"$RESOLV"

pending_one="$(run_guard auto)"
printf '%s\n' "$pending_one"
grep -F 'RECOVERY_STREAK=1/3' <<EOF >/dev/null
$pending_one
EOF
grep -F 'AUTO=BOOTSTRAP_RECOVERY_PENDING' <<EOF >/dev/null
$pending_one
EOF
grep -qx 'nameserver 9.9.9.9' "$RESOLV"

pending_two="$(run_guard auto)"
printf '%s\n' "$pending_two"
grep -F 'RECOVERY_STREAK=2/3' <<EOF >/dev/null
$pending_two
EOF
grep -F 'AUTO=BOOTSTRAP_RECOVERY_PENDING' <<EOF >/dev/null
$pending_two
EOF

echo "=== unhealthy sample resets recovery streak immediately ==="
: >"$FAIL_LOCAL"
reset_output="$(run_guard auto)"
printf '%s\n' "$reset_output"
grep -F 'AUTO=BOOTSTRAP_UNHEALTHY' <<EOF >/dev/null
$reset_output
EOF
[ ! -f "$RECOVERY_STREAK_FILE" ]
grep -qx 'nameserver 9.9.9.9' "$RESOLV"

rm -f "$FAIL_LOCAL"

for expected in 1 2; do
    pending_output="$(run_guard auto)"
    printf '%s\n' "$pending_output"
    grep -F "RECOVERY_STREAK=$expected/3" <<EOF >/dev/null
$pending_output
EOF
    grep -F 'AUTO=BOOTSTRAP_RECOVERY_PENDING' <<EOF >/dev/null
$pending_output
EOF
    grep -qx 'nameserver 9.9.9.9' "$RESOLV"
done

promoted_output="$(run_guard auto)"
printf '%s\n' "$promoted_output"
grep -F 'RECOVERY_STREAK=3/3' <<EOF >/dev/null
$promoted_output
EOF
grep -F 'AUTO=LOCAL_DNS' <<EOF >/dev/null
$promoted_output
EOF
grep -qx 'nameserver 192.0.2.53' "$RESOLV"
[ ! -f "$RECOVERY_STREAK_FILE" ]

echo "=== corrupted oversized recovery streak cannot deadlock auto recovery ==="
cat >"$CONFIG" <<'EOF'
EDGE_UNBOUND_PORT=53535
EDGE_DNS_LOCAL_RESOLVER_IP=192.0.2.53
EDGE_DNS_FAILBACK_SUCCESS_THRESHOLD=3
EDGE_DNS_QUERY_TIMEOUT_SECONDS=2
EDGE_DNS_LOCK_WAIT_SECONDS=2
EOF
rm -f "$FAIL_LOCAL"
printf '%s\n' 'nameserver 9.9.9.9' 'nameserver 149.112.112.112' >"$RESOLV"
printf '%s\n' '999999999999999999999999999999999999999999' >"$RECOVERY_STREAK_FILE"
printf '%s\n' '999999999999999999999999999999999999999999' >"$RUNTIME_STATE_DIR/fallback-transitions"

corrupt_state_output="$(run_guard auto)"
printf '%s\n' "$corrupt_state_output"
grep -F 'RECOVERY_STREAK=1/3' <<EOF >/dev/null
$corrupt_state_output
EOF
grep -F 'AUTO=BOOTSTRAP_RECOVERY_PENDING' <<EOF >/dev/null
$corrupt_state_output
EOF

corrupt_metrics="$(run_guard metrics)"
# The oversized counter is sanitized before arithmetic. Because this fixture
# also transitions observed mode from local to bootstrap, reconciliation
# records one real transition instead of preserving the corrupt value.
printf '%s\n' "$corrupt_metrics" |
    grep -qx 'asus_edge_dns_guard_fallback_transitions_runtime_total 1'

echo "=== local failure still fails open on first unhealthy check ==="
: >"$FAIL_LOCAL"
failopen_output="$(run_guard auto)"
printf '%s\n' "$failopen_output"
grep -F 'AUTO=BOOTSTRAP_UNHEALTHY' <<EOF >/dev/null
$failopen_output
EOF
grep -qx 'nameserver 9.9.9.9' "$RESOLV"
grep -qx 'nameserver 149.112.112.112' "$RESOLV"
[ ! -f "$RECOVERY_STREAK_FILE" ]

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
