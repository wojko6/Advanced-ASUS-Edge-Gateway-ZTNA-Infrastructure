#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

FUNCS="$TMP_DIR/lan-dot-functions.sh"
awk '
    /^lan_dot_parent_jump_count\(\)/ { capture=1 }
    /^direct_parent_tailscale_nat_rule_count\(\)/ { capture=0 }
    capture { print }
' "$REPO_DIR/scripts/healthcheck.sh" >"$FUNCS"

for function_name in lan_dot_parent_jump_count lan_dot_parent_order_ok lan_dot_chain_matches_policy; do
    grep -F "$function_name()" "$FUNCS" >/dev/null || {
        echo "FAIL: could not extract $function_name from healthcheck" >&2
        exit 1
    }
done

MOCK_BIN="$TMP_DIR/bin"
mkdir -p "$MOCK_BIN"

cat >"$MOCK_BIN/iptables" <<'EOF'
#!/bin/sh
case "$*" in
    "-t filter -S FORWARD")
        case "${FIXTURE:-good}" in
            disabled)
                cat <<'RULES'
-P FORWARD ACCEPT
-A FORWARD -i tailscale0 -j EDGE_TS_FORWARD
-A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT
RULES
                ;;
            misordered)
                cat <<'RULES'
-P FORWARD ACCEPT
-A FORWARD -i br0 -j EDGE_LAN_DOT_FORWARD
-A FORWARD -i tailscale0 -j EDGE_TS_FORWARD
-A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT
RULES
                ;;
            duplicate)
                cat <<'RULES'
-P FORWARD ACCEPT
-A FORWARD -i tailscale0 -j EDGE_TS_FORWARD
-A FORWARD -i br0 -j EDGE_LAN_DOT_FORWARD
-A FORWARD -i br0 -j EDGE_LAN_DOT_FORWARD
RULES
                ;;
            *)
                cat <<'RULES'
-P FORWARD ACCEPT
-A FORWARD -i tailscale0 -j EDGE_TS_FORWARD
-A FORWARD -i br0 -j EDGE_LAN_DOT_FORWARD
-A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT
RULES
                ;;
        esac
        ;;
    "-t filter -S EDGE_LAN_DOT_FORWARD")
        case "${FIXTURE:-good}" in
            bad-chain)
                cat <<'RULES'
-N EDGE_LAN_DOT_FORWARD
-A EDGE_LAN_DOT_FORWARD -p tcp -m tcp --dport 853 -j DROP
RULES
                ;;
            extra-rule)
                cat <<'RULES'
-N EDGE_LAN_DOT_FORWARD
-A EDGE_LAN_DOT_FORWARD -p tcp -m tcp --dport 853 -j REJECT --reject-with tcp-reset
-A EDGE_LAN_DOT_FORWARD -p tcp -m tcp --dport 443 -j REJECT --reject-with tcp-reset
RULES
                ;;
            *)
                cat <<'RULES'
-N EDGE_LAN_DOT_FORWARD
-A EDGE_LAN_DOT_FORWARD -p tcp -m tcp --dport 853 -j REJECT --reject-with tcp-reset
RULES
                ;;
        esac
        ;;
    *)
        exit 1
        ;;
esac
EOF
chmod +x "$MOCK_BIN/iptables"

PATH="$MOCK_BIN:/usr/bin:/bin"
export PATH
EDGE_TS_IF=tailscale0
EDGE_LAN_IF=br0
EDGE_DOT_PORT=853
export EDGE_TS_IF EDGE_LAN_IF EDGE_DOT_PORT

# shellcheck disable=SC1090
. "$FUNCS"

FIXTURE=good
export FIXTURE
[ "$(lan_dot_parent_jump_count)" = "1" ] || {
    echo "FAIL: managed LAN DoT jump count is not one" >&2
    exit 1
}
lan_dot_parent_order_ok || {
    echo "FAIL: valid LAN DoT parent ordering was rejected" >&2
    exit 1
}
lan_dot_chain_matches_policy || {
    echo "FAIL: valid LAN DoT chain was rejected" >&2
    exit 1
}

FIXTURE=disabled
export FIXTURE
[ "$(lan_dot_parent_jump_count)" = "0" ] || {
    echo "FAIL: disabled LAN DoT fixture still reports a jump" >&2
    exit 1
}

FIXTURE=misordered
export FIXTURE
if lan_dot_parent_order_ok; then
    echo "FAIL: misordered LAN DoT parent jump was accepted" >&2
    exit 1
fi

FIXTURE=duplicate
export FIXTURE
[ "$(lan_dot_parent_jump_count)" = "2" ] || {
    echo "FAIL: duplicate LAN DoT jumps were not detected" >&2
    exit 1
}

FIXTURE=bad-chain
export FIXTURE
if lan_dot_chain_matches_policy; then
    echo "FAIL: DROP-only LAN DoT chain was accepted instead of tcp-reset REJECT" >&2
    exit 1
fi

FIXTURE=extra-rule
export FIXTURE
if lan_dot_chain_matches_policy; then
    echo "FAIL: LAN DoT chain with extra rule was accepted" >&2
    exit 1
fi

echo "PASS: LAN DoT healthcheck contract validates jump count, ordering and exact TCP/853 reject policy"
