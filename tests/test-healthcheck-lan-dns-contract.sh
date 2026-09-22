#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

FUNCS="$TMP_DIR/lan-dns-functions.sh"
awk '
    /^lan_dns_parent_jump_count\(\)/ { capture=1 }
    /^direct_parent_tailscale_nat_rule_count\(\)/ { capture=0 }
    capture { print }
' "$REPO_DIR/scripts/healthcheck.sh" >"$FUNCS"

for function_name in lan_dns_parent_jump_count direct_parent_lan_dns_rule_count lan_dns_chain_matches_policy; do
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
    "-t nat -S PREROUTING")
        case "${FIXTURE:-good}" in
            disabled)
                cat <<'RULES'
-P PREROUTING ACCEPT
-A PREROUTING -i tailscale0 -j EDGE_TS_PREROUTING
RULES
                ;;
            direct-dns)
                cat <<'RULES'
-P PREROUTING ACCEPT
-A PREROUTING -i br0 -j EDGE_LAN_DNS_PREROUTING
-A PREROUTING -i tailscale0 -j EDGE_TS_PREROUTING
-A PREROUTING -i br0 -p udp -m udp --dport 53 -j REDIRECT --to-ports 53
RULES
                ;;
            *)
                cat <<'RULES'
-P PREROUTING ACCEPT
-A PREROUTING -i br0 -j EDGE_LAN_DNS_PREROUTING
-A PREROUTING -i tailscale0 -j EDGE_TS_PREROUTING
RULES
                ;;
        esac
        ;;
    "-t nat -S EDGE_LAN_DNS_PREROUTING")
        case "${FIXTURE:-good}" in
            bad-chain)
                cat <<'RULES'
-N EDGE_LAN_DNS_PREROUTING
-A EDGE_LAN_DNS_PREROUTING -d 192.168.50.1/32 -p udp -m udp --dport 53 -j RETURN
-A EDGE_LAN_DNS_PREROUTING -d 192.168.50.1/32 -p tcp -m tcp --dport 53 -j RETURN
-A EDGE_LAN_DNS_PREROUTING -p udp -m udp --dport 53 -j REDIRECT --to-ports 53
RULES
                ;;
            *)
                cat <<'RULES'
-N EDGE_LAN_DNS_PREROUTING
-A EDGE_LAN_DNS_PREROUTING -d 192.168.50.1/32 -p udp -m udp --dport 53 -j RETURN
-A EDGE_LAN_DNS_PREROUTING -d 192.168.50.1/32 -p tcp -m tcp --dport 53 -j RETURN
-A EDGE_LAN_DNS_PREROUTING -p udp -m udp --dport 53 -j REDIRECT --to-ports 53
-A EDGE_LAN_DNS_PREROUTING -p tcp -m tcp --dport 53 -j REDIRECT --to-ports 53
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
EDGE_LAN_IF=br0
EDGE_ROUTER_LAN_IP=192.168.50.1
EDGE_DNS_PORT=53
export EDGE_LAN_IF EDGE_ROUTER_LAN_IP EDGE_DNS_PORT

# shellcheck disable=SC1090
. "$FUNCS"

FIXTURE=good
export FIXTURE
[ "$(lan_dns_parent_jump_count)" = "1" ] || {
    echo "FAIL: managed LAN DNS jump count is not one" >&2
    exit 1
}
[ "$(direct_parent_lan_dns_rule_count)" = "0" ] || {
    echo "FAIL: managed LAN DNS policy was treated as direct drift" >&2
    exit 1
}
lan_dns_chain_matches_policy || {
    echo "FAIL: valid LAN DNS chain was rejected" >&2
    exit 1
}

FIXTURE=direct-dns
export FIXTURE
[ "$(direct_parent_lan_dns_rule_count)" = "1" ] || {
    echo "FAIL: direct parent LAN DNS redirect was not detected" >&2
    exit 1
}

FIXTURE=bad-chain
export FIXTURE
if lan_dns_chain_matches_policy; then
    echo "FAIL: incomplete LAN DNS chain was accepted" >&2
    exit 1
fi

FIXTURE=disabled
export FIXTURE
[ "$(lan_dns_parent_jump_count)" = "0" ] || {
    echo "FAIL: disabled LAN DNS fixture still reports a managed jump" >&2
    exit 1
}

echo "PASS: LAN DNS healthcheck contract accepts the managed policy and rejects drift"
