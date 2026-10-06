#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

FUNCS="$TMP_DIR/router-https-functions.sh"

awk '
    /^router_https_nat_rule_exists\(\)/ { capture=1 }
    /^if \[ "\$EDGE_ALLOW_ROUTER_HTTPS" = "1" \]; then/ { capture=0 }
    capture { print }
' "$REPO_DIR/scripts/healthcheck.sh" >"$FUNCS"

for helper in \
    'router_https_nat_rule_exists()' \
    'router_https_input_rule_exists()' \
    'router_https_listener_exists()'
do
    grep -F "$helper" "$FUNCS" >/dev/null || {
        echo "FAIL: could not extract helper: $helper" >&2
        exit 1
    }
done

MOCK_BIN="$TMP_DIR/bin"
mkdir -p "$MOCK_BIN"

cat >"$MOCK_BIN/iptables" <<'MOCK'
#!/bin/sh

case "$*" in
    "-t nat -S EDGE_TS_PREROUTING")
        case "${NAT_FIXTURE:-good}" in
            good)
                cat <<'RULES'
-N EDGE_TS_PREROUTING
-A EDGE_TS_PREROUTING -s 100.64.0.10/32 -p tcp -m tcp --dport 8443 -j DNAT --to-destination 192.168.50.1:443
RULES
                ;;
            wrong-source)
                cat <<'RULES'
-N EDGE_TS_PREROUTING
-A EDGE_TS_PREROUTING -s 100.64.0.99/32 -p tcp -m tcp --dport 8443 -j DNAT --to-destination 192.168.50.1:443
RULES
                ;;
            wrong-incoming-port)
                cat <<'RULES'
-N EDGE_TS_PREROUTING
-A EDGE_TS_PREROUTING -s 100.64.0.10/32 -p tcp -m tcp --dport 443 -j DNAT --to-destination 192.168.50.1:443
RULES
                ;;
            wrong-target-port)
                cat <<'RULES'
-N EDGE_TS_PREROUTING
-A EDGE_TS_PREROUTING -s 100.64.0.10/32 -p tcp -m tcp --dport 8443 -j DNAT --to-destination 192.168.50.1:8443
RULES
                ;;
        esac
        ;;

    "-t filter -S EDGE_TS_INPUT")
        case "${INPUT_FIXTURE:-good}" in
            good)
                cat <<'RULES'
-N EDGE_TS_INPUT
-A EDGE_TS_INPUT -s 100.64.0.10/32 -d 192.168.50.1/32 -p tcp -m tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT
-A EDGE_TS_INPUT -j DROP
RULES
                ;;
            wrong-source)
                cat <<'RULES'
-N EDGE_TS_INPUT
-A EDGE_TS_INPUT -s 100.64.0.99/32 -d 192.168.50.1/32 -p tcp -m tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT
-A EDGE_TS_INPUT -j DROP
RULES
                ;;
            wrong-destination)
                cat <<'RULES'
-N EDGE_TS_INPUT
-A EDGE_TS_INPUT -s 100.64.0.10/32 -d 198.51.100.254/32 -p tcp -m tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT
-A EDGE_TS_INPUT -j DROP
RULES
                ;;
            wrong-port)
                cat <<'RULES'
-N EDGE_TS_INPUT
-A EDGE_TS_INPUT -s 100.64.0.10/32 -d 192.168.50.1/32 -p tcp -m tcp --dport 8443 -m conntrack --ctstate NEW -j ACCEPT
-A EDGE_TS_INPUT -j DROP
RULES
                ;;
        esac
        ;;

    *)
        exit 1
        ;;
esac
MOCK

cat >"$MOCK_BIN/netstat" <<'MOCK'
#!/bin/sh

case "${LISTENER_FIXTURE:-good}" in
    good)
        cat <<'OUT'
Proto Recv-Q Send-Q Local Address           Foreign Address         State
tcp        0      0 192.168.50.1:443        0.0.0.0:*               LISTEN
OUT
        ;;
    old-port)
        cat <<'OUT'
Proto Recv-Q Send-Q Local Address           Foreign Address         State
tcp        0      0 192.168.50.1:8443       0.0.0.0:*               LISTEN
OUT
        ;;
    wrong-address)
        cat <<'OUT'
Proto Recv-Q Send-Q Local Address           Foreign Address         State
tcp        0      0 198.51.100.254:443      0.0.0.0:*               LISTEN
OUT
        ;;
    missing)
        echo "Proto Recv-Q Send-Q Local Address Foreign Address State"
        ;;
esac
MOCK

chmod +x "$MOCK_BIN/iptables" "$MOCK_BIN/netstat"

PATH="$MOCK_BIN:/usr/bin:/bin"
EDGE_ROUTER_LAN_IP="192.168.50.1"
EDGE_ROUTER_HTTPS_PORT="8443"
EDGE_ROUTER_HTTPS_TARGET_PORT="443"

export PATH
export EDGE_ROUTER_LAN_IP
export EDGE_ROUTER_HTTPS_PORT
export EDGE_ROUTER_HTTPS_TARGET_PORT

# shellcheck disable=SC1090
. "$FUNCS"

NAT_FIXTURE=good
export NAT_FIXTURE
router_https_nat_rule_exists 100.64.0.10/32 || {
    echo "FAIL: valid 8443 -> 443 DNAT was rejected" >&2
    exit 1
}

for fixture in wrong-source wrong-incoming-port wrong-target-port; do
    NAT_FIXTURE="$fixture"
    export NAT_FIXTURE

    if router_https_nat_rule_exists 100.64.0.10/32; then
        echo "FAIL: invalid DNAT fixture accepted: $fixture" >&2
        exit 1
    fi
done

INPUT_FIXTURE=good
export INPUT_FIXTURE
router_https_input_rule_exists 100.64.0.10/32 || {
    echo "FAIL: valid post-DNAT INPUT rule was rejected" >&2
    exit 1
}

for fixture in wrong-source wrong-destination wrong-port; do
    INPUT_FIXTURE="$fixture"
    export INPUT_FIXTURE

    if router_https_input_rule_exists 100.64.0.10/32; then
        echo "FAIL: invalid INPUT fixture accepted: $fixture" >&2
        exit 1
    fi
done

LISTENER_FIXTURE=good
export LISTENER_FIXTURE
router_https_listener_exists || {
    echo "FAIL: valid router HTTPS listener was rejected" >&2
    exit 1
}

for fixture in old-port wrong-address missing; do
    LISTENER_FIXTURE="$fixture"
    export LISTENER_FIXTURE

    if router_https_listener_exists; then
        echo "FAIL: invalid listener fixture accepted: $fixture" >&2
        exit 1
    fi
done

echo "PASS: router HTTPS contract enforces 8443 -> 443 DNAT, post-DNAT INPUT and target listener"
