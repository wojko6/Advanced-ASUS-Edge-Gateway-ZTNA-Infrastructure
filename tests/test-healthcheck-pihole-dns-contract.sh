#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

FUNCS="$TMP_DIR/pihole-functions.sh"

awk '
    /^ts_pihole_nat_rule_and_order_ok\(\)/ { capture=1 }
    /^if \[ -n "\$EDGE_TS_PIHOLE_SOURCES" \]; then/ { capture=0 }
    capture { print }
' "$REPO_DIR/scripts/healthcheck.sh" >"$FUNCS"

grep -F 'ts_pihole_nat_rule_and_order_ok()' "$FUNCS" >/dev/null || {
    echo "FAIL: could not extract Pi-hole healthcheck helper" >&2
    exit 1
}

MOCK_BIN="$TMP_DIR/bin"
mkdir -p "$MOCK_BIN"

cat >"$MOCK_BIN/iptables" <<'MOCK'
#!/bin/sh

[ "$*" = "-t nat -S EDGE_TS_PREROUTING" ] || exit 1

case "${FIXTURE:-good}" in
    good)
        cat <<'RULES'
-N EDGE_TS_PREROUTING
-A EDGE_TS_PREROUTING -s 100.64.0.20/32 -p udp -m udp --dport 53 -j DNAT --to-destination 198.51.100.53:53
-A EDGE_TS_PREROUTING -s 100.64.0.20/32 -p tcp -m tcp --dport 53 -j DNAT --to-destination 198.51.100.53:53
-A EDGE_TS_PREROUTING -p udp -m udp --dport 53 -j REDIRECT --to-ports 53
-A EDGE_TS_PREROUTING -p tcp -m tcp --dport 53 -j REDIRECT --to-ports 53
RULES
        ;;
    misordered)
        cat <<'RULES'
-N EDGE_TS_PREROUTING
-A EDGE_TS_PREROUTING -p udp -m udp --dport 53 -j REDIRECT --to-ports 53
-A EDGE_TS_PREROUTING -s 100.64.0.20/32 -p udp -m udp --dport 53 -j DNAT --to-destination 198.51.100.53:53
RULES
        ;;
    missing)
        cat <<'RULES'
-N EDGE_TS_PREROUTING
-A EDGE_TS_PREROUTING -p udp -m udp --dport 53 -j REDIRECT --to-ports 53
RULES
        ;;
esac
MOCK

chmod +x "$MOCK_BIN/iptables"

PATH="$MOCK_BIN:/usr/bin:/bin"
EDGE_DNS_PORT=53
EDGE_TS_PIHOLE_DNS_IP=198.51.100.53

export PATH EDGE_DNS_PORT EDGE_TS_PIHOLE_DNS_IP

# shellcheck disable=SC1090
. "$FUNCS"

FIXTURE=good
export FIXTURE

ts_pihole_nat_rule_and_order_ok 100.64.0.20/32 udp || {
    echo "FAIL: valid UDP Pi-hole DNAT was rejected" >&2
    exit 1
}

ts_pihole_nat_rule_and_order_ok 100.64.0.20/32 tcp || {
    echo "FAIL: valid TCP Pi-hole DNAT was rejected" >&2
    exit 1
}

FIXTURE=misordered
export FIXTURE

if ts_pihole_nat_rule_and_order_ok 100.64.0.20/32 udp; then
    echo "FAIL: misordered Pi-hole DNAT was accepted" >&2
    exit 1
fi

FIXTURE=missing
export FIXTURE

if ts_pihole_nat_rule_and_order_ok 100.64.0.20/32 udp; then
    echo "FAIL: missing Pi-hole DNAT was accepted" >&2
    exit 1
fi

echo "PASS: Pi-hole DNS healthcheck contract accepts correct ordering and rejects drift"
