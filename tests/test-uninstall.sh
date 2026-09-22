#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

ROOT="$TMP_DIR/root"
mkdir -p "$ROOT/jffs/configs" "$ROOT/jffs/scripts" "$ROOT/jffs/addons/asus-edge/legacy"

cat >"$ROOT/jffs/configs/asus-edge.conf" <<'EOF'
EDGE_TS_IF="tailscale-test"
EDGE_LAN_IF="lan-test"
EOF

MOCK_LOG="$TMP_DIR/iptables.log"
export MOCK_LOG

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

# Run the real uninstall logic from a temporary copy, changing only the
# root-privilege preflight so the CI user can exercise the cleanup contract.
cp "$REPO_DIR/scripts/uninstall.sh" "$TMP_DIR/uninstall.sh"
sed -i 's/^uid="$(current_uid)".*$/uid=0/' "$TMP_DIR/uninstall.sh"

EDGE_TEST_ROOT="$ROOT" \
EDGE_IPTABLES="$TMP_DIR/iptables" \
EDGE_IP6TABLES="$TMP_DIR/ip6tables" \
sh "$TMP_DIR/uninstall.sh" >"$TMP_DIR/stdout"

assert_logged() {
    grep -F -- "$1" "$MOCK_LOG" >/dev/null || {
        echo "FAIL: missing uninstall command: $1" >&2
        cat "$MOCK_LOG" >&2
        exit 1
    }
}

# Existing Tailscale-owned project chains.
assert_logged "iptables -t filter -D INPUT -i tailscale-test -j EDGE_TS_INPUT"
assert_logged "iptables -t filter -D FORWARD -i tailscale-test -j EDGE_TS_FORWARD"
assert_logged "iptables -t nat -D PREROUTING -i tailscale-test -j EDGE_TS_PREROUTING"

# H1 regression: LAN DNS and LAN DoT chains must be detached and removed.
assert_logged "iptables -t filter -D FORWARD -i lan-test -j EDGE_LAN_DOT_FORWARD"
assert_logged "iptables -t filter -F EDGE_LAN_DOT_FORWARD"
assert_logged "iptables -t filter -X EDGE_LAN_DOT_FORWARD"
assert_logged "iptables -t nat -D PREROUTING -i lan-test -j EDGE_LAN_DNS_PREROUTING"
assert_logged "iptables -t nat -F EDGE_LAN_DNS_PREROUTING"
assert_logged "iptables -t nat -X EDGE_LAN_DNS_PREROUTING"

# Existing IPv6 project cleanup remains intact.
assert_logged "ip6tables -t filter -D INPUT -i tailscale-test -j EDGE_TS6_INPUT"
assert_logged "ip6tables -t filter -D FORWARD -i tailscale-test -j EDGE_TS6_FORWARD"

grep -F "Runtime rules removed and previous hooks restored when available." "$TMP_DIR/stdout" >/dev/null

echo "PASS: uninstall removes Tailscale, LAN DNS and LAN DoT managed runtime chains"
