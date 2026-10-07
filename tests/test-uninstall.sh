#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

MOCK_LOG="$TMP_DIR/ops.log"
CRON_FILE="$TMP_DIR/cron"
RESOLV="$TMP_DIR/resolv.conf"
FAIL_GUARD="$TMP_DIR/fail-guard"
FAIL_CRU_DELETE="$TMP_DIR/fail-cru-delete"
export MOCK_LOG CRON_FILE RESOLV FAIL_GUARD FAIL_CRU_DELETE

cat >"$TMP_DIR/iptables" <<'EOF'
#!/bin/sh
printf 'iptables %s\n' "$*" >>"$MOCK_LOG"
case "$*" in
    *" -D "*) exit 1 ;;
    *) exit 0 ;;
esac
EOF
chmod +x "$TMP_DIR/iptables"

cat >"$TMP_DIR/ip6tables" <<'EOF'
#!/bin/sh
printf 'ip6tables %s\n' "$*" >>"$MOCK_LOG"
case "$*" in
    *" -D "*) exit 1 ;;
    *) exit 0 ;;
esac
EOF
chmod +x "$TMP_DIR/ip6tables"

cat >"$TMP_DIR/cru" <<'EOF'
#!/bin/sh
case "${1:-}" in
    l)
        [ -f "$CRON_FILE" ] && cat "$CRON_FILE"
        ;;
    d)
        printf 'cru d %s\n' "${2:-}" >>"$MOCK_LOG"
        [ -f "$FAIL_CRU_DELETE" ] && exit 1
        if [ -f "$CRON_FILE" ]; then
            grep -v '#AsusEdgeDNSGuard#' "$CRON_FILE" >"$CRON_FILE.tmp" || true
            mv -f "$CRON_FILE.tmp" "$CRON_FILE"
        fi
        ;;
    *)
        exit 1
        ;;
esac
EOF
chmod +x "$TMP_DIR/cru"

prepare_root() {
    root="$1"
    rm -rf "$root"
    mkdir -p \
        "$root/jffs/configs" \
        "$root/jffs/scripts" \
        "$root/jffs/addons/asus-edge/bin" \
        "$root/jffs/addons/asus-edge/legacy"

    cat >"$root/jffs/configs/asus-edge.conf" <<'EOF'
EDGE_TS_IF="tailscale-test"
EDGE_LAN_IF="lan-test"
EOF

    cat >"$root/jffs/addons/asus-edge/bin/dns-guard" <<'EOF'
#!/bin/sh
printf 'dns-guard %s\n' "$*" >>"$MOCK_LOG"
[ "${1:-}" = "fallback" ] || exit 1
[ -f "$FAIL_GUARD" ] && { echo "FALLBACK=FAILED"; exit 1; }
printf '%s\n' 'nameserver 9.9.9.9' 'nameserver 149.112.112.112' >"$RESOLV"
echo "FALLBACK=PASS"
EOF
    chmod +x "$root/jffs/addons/asus-edge/bin/dns-guard"
}

run_uninstall() {
    root="$1"
    stdout="$2"
    stderr="$3"

    cp "$REPO_DIR/scripts/uninstall.sh" "$TMP_DIR/uninstall.sh"
    sed -i 's/^uid="$(current_uid)".*$/uid=0/' "$TMP_DIR/uninstall.sh"

    EDGE_TEST_ROOT="$root" \
    EDGE_IPTABLES="$TMP_DIR/iptables" \
    EDGE_IP6TABLES="$TMP_DIR/ip6tables" \
    EDGE_CRU="$TMP_DIR/cru" \
    sh "$TMP_DIR/uninstall.sh" >"$stdout" 2>"$stderr"
}

assert_logged() {
    grep -F -- "$1" "$MOCK_LOG" >/dev/null || {
        echo "FAIL: missing uninstall command: $1" >&2
        cat "$MOCK_LOG" >&2
        exit 1
    }
}

echo "=== validated bootstrap precedes watchdog and firewall cleanup ==="
ROOT="$TMP_DIR/root-success"
prepare_root "$ROOT"
: >"$MOCK_LOG"
printf '%s\n' '* * * * * /jffs/addons/asus-edge/bin/dns-guard auto >/dev/null 2>&1 #AsusEdgeDNSGuard#' >"$CRON_FILE"
printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"

run_uninstall "$ROOT" "$TMP_DIR/stdout" "$TMP_DIR/stderr"

grep -F 'DNS_UNINSTALL_BOOTSTRAP=PASS' "$TMP_DIR/stdout" >/dev/null
grep -F 'DNS_GUARD_WATCHDOG=REMOVED' "$TMP_DIR/stdout" >/dev/null
grep -qx 'nameserver 9.9.9.9' "$RESOLV"
grep -qx 'nameserver 149.112.112.112' "$RESOLV"
! grep -F '#AsusEdgeDNSGuard#' "$CRON_FILE" >/dev/null

fallback_line="$(grep -n -m1 '^dns-guard fallback$' "$MOCK_LOG" | cut -d: -f1)"
cru_line="$(grep -n -m1 '^cru d AsusEdgeDNSGuard$' "$MOCK_LOG" | cut -d: -f1)"
iptables_line="$(grep -n -m1 '^iptables ' "$MOCK_LOG" | cut -d: -f1)"
[ "$fallback_line" -lt "$cru_line" ]
[ "$cru_line" -lt "$iptables_line" ]

assert_logged "iptables -t filter -D INPUT -i tailscale-test -j EDGE_TS_INPUT"
assert_logged "iptables -t filter -D FORWARD -i tailscale-test -j EDGE_TS_FORWARD"
assert_logged "iptables -t nat -D PREROUTING -i tailscale-test -j EDGE_TS_PREROUTING"
assert_logged "iptables -t filter -D FORWARD -i lan-test -j EDGE_LAN_DOT_FORWARD"
assert_logged "iptables -t filter -F EDGE_LAN_DOT_FORWARD"
assert_logged "iptables -t filter -X EDGE_LAN_DOT_FORWARD"
assert_logged "iptables -t nat -D PREROUTING -i lan-test -j EDGE_LAN_DNS_PREROUTING"
assert_logged "iptables -t nat -F EDGE_LAN_DNS_PREROUTING"
assert_logged "iptables -t nat -X EDGE_LAN_DNS_PREROUTING"
assert_logged "ip6tables -t filter -D INPUT -i tailscale-test -j EDGE_TS6_INPUT"
assert_logged "ip6tables -t filter -D FORWARD -i tailscale-test -j EDGE_TS6_FORWARD"
grep -F "Runtime rules removed and previous hooks restored when available." "$TMP_DIR/stdout" >/dev/null

echo "=== bootstrap failure aborts before watchdog or firewall mutation ==="
FAIL_ROOT="$TMP_DIR/root-fail-guard"
prepare_root "$FAIL_ROOT"
: >"$MOCK_LOG"
printf '%s\n' '* * * * * /jffs/addons/asus-edge/bin/dns-guard auto >/dev/null 2>&1 #AsusEdgeDNSGuard#' >"$CRON_FILE"
: >"$FAIL_GUARD"

if run_uninstall "$FAIL_ROOT" "$TMP_DIR/fail-guard.out" "$TMP_DIR/fail-guard.err"; then
    echo "FAIL: uninstall succeeded although DNS Guard fallback failed" >&2
    exit 1
fi
grep -F 'refusing uninstall' "$TMP_DIR/fail-guard.err" >/dev/null
grep -F '^dns-guard fallback$' "$MOCK_LOG" >/dev/null
! grep -F '^cru d AsusEdgeDNSGuard$' "$MOCK_LOG" >/dev/null
! grep -F '^iptables ' "$MOCK_LOG" >/dev/null
rm -f "$FAIL_GUARD"

echo "=== watchdog removal failure aborts before firewall mutation ==="
FAIL_CRU_ROOT="$TMP_DIR/root-fail-cru"
prepare_root "$FAIL_CRU_ROOT"
: >"$MOCK_LOG"
printf '%s\n' '* * * * * /jffs/addons/asus-edge/bin/dns-guard auto >/dev/null 2>&1 #AsusEdgeDNSGuard#' >"$CRON_FILE"
: >"$FAIL_CRU_DELETE"

if run_uninstall "$FAIL_CRU_ROOT" "$TMP_DIR/fail-cru.out" "$TMP_DIR/fail-cru.err"; then
    echo "FAIL: uninstall succeeded although watchdog remained scheduled" >&2
    exit 1
fi
grep -F 'watchdog remains scheduled' "$TMP_DIR/fail-cru.err" >/dev/null
grep -F '^dns-guard fallback$' "$MOCK_LOG" >/dev/null
grep -F '^cru d AsusEdgeDNSGuard$' "$MOCK_LOG" >/dev/null
! grep -F '^iptables ' "$MOCK_LOG" >/dev/null
rm -f "$FAIL_CRU_DELETE"

echo "PASS: uninstall restores independent DNS before watchdog and firewall cleanup"
