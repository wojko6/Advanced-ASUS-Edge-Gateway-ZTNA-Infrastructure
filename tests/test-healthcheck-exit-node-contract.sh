#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

FUNCS="$TMP_DIR/exit-node-functions.sh"
awk '
    /^exit_forward_rule_exists\(\)/ { capture=1 }
    /^if \[ "\$EDGE_ENABLE_EXIT_NODE" = "1" \]; then/ { capture=0 }
    capture { print }
' "$REPO_DIR/scripts/healthcheck.sh" >"$FUNCS"

for function_name in exit_forward_rule_exists platform_wan_nat_exists platform_return_path_exists; do
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
    "-t filter -S EDGE_TS_FORWARD")
        case "${FIXTURE:-good}" in
            missing-forward)
                cat <<'RULES'
-P EDGE_TS_FORWARD -
-A EDGE_TS_FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
-A EDGE_TS_FORWARD -j DROP
RULES
                ;;
            *)
                cat <<'RULES'
-P EDGE_TS_FORWARD -
-A EDGE_TS_FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
-A EDGE_TS_FORWARD -o ppp0 -j ACCEPT
-A EDGE_TS_FORWARD -j DROP
RULES
                ;;
        esac
        ;;
    "-t nat -S POSTROUTING")
        case "${FIXTURE:-good}" in
            missing-nat)
                cat <<'RULES'
-P POSTROUTING ACCEPT
-A POSTROUTING -o vlan35 -j MASQUERADE
RULES
                ;;
            snat)
                cat <<'RULES'
-P POSTROUTING ACCEPT
-A POSTROUTING -o ppp0 -j SNAT --to-source 198.51.100.10
RULES
                ;;
            *)
                cat <<'RULES'
-P POSTROUTING ACCEPT
-A POSTROUTING ! -s 198.51.100.10/32 -o ppp0 -j MASQUERADE
RULES
                ;;
        esac
        ;;
    "-t filter -S FORWARD")
        case "${FIXTURE:-good}" in
            missing-return)
                cat <<'RULES'
-P FORWARD ACCEPT
-A FORWARD -i tailscale0 -j EDGE_TS_FORWARD
-A FORWARD ! -i br0 -o ppp0 -j DROP
-A FORWARD -j DROP
RULES
                ;;
            return-after-drop)
                cat <<'RULES'
-P FORWARD ACCEPT
-A FORWARD -i tailscale0 -j EDGE_TS_FORWARD
-A FORWARD ! -i br0 -o ppp0 -j DROP
-A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT
-A FORWARD -j DROP
RULES
                ;;
            *)
                cat <<'RULES'
-P FORWARD ACCEPT
-A FORWARD -i tailscale0 -j EDGE_TS_FORWARD
-A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT
-A FORWARD ! -i br0 -o ppp0 -j DROP
-A FORWARD -j DROP
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

# shellcheck disable=SC1090
. "$FUNCS"

FIXTURE=good
export FIXTURE
exit_forward_rule_exists ppp0
platform_wan_nat_exists ppp0
platform_return_path_exists ppp0

FIXTURE=snat
export FIXTURE
platform_wan_nat_exists ppp0

FIXTURE=missing-forward
export FIXTURE
if exit_forward_rule_exists ppp0; then
    echo "FAIL: missing exit-node forward rule was accepted" >&2
    exit 1
fi

FIXTURE=missing-nat
export FIXTURE
if platform_wan_nat_exists ppp0; then
    echo "FAIL: missing WAN NAT was accepted" >&2
    exit 1
fi

FIXTURE=missing-return
export FIXTURE
if platform_return_path_exists ppp0; then
    echo "FAIL: missing established/related return path was accepted" >&2
    exit 1
fi

FIXTURE=return-after-drop
export FIXTURE
if platform_return_path_exists ppp0; then
    echo "FAIL: return path ordered after WAN drop was accepted" >&2
    exit 1
fi

echo "PASS: healthcheck exit-node contract parsers accept the validated rule shape and reject missing/misordered dependencies"
