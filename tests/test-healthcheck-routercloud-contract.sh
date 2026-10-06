#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

FUNCS="$TMP_DIR/routercloud-functions.sh"

awk '
    /^routercloud_input_rule_exists\(\)/ { capture=1 }
    /^if \[ "\$EDGE_ALLOW_ROUTERCLOUD" = "1" \]; then/ { capture=0 }
    capture { print }
' "$REPO_DIR/scripts/healthcheck.sh" >"$FUNCS"

grep -F 'routercloud_input_rule_exists()' "$FUNCS" >/dev/null || {
    echo "FAIL: could not extract RouterCloud healthcheck helper" >&2
    exit 1
}

MOCK_BIN="$TMP_DIR/bin"
mkdir -p "$MOCK_BIN"

cat >"$MOCK_BIN/iptables" <<'MOCK'
#!/bin/sh

[ "$*" = "-t filter -S EDGE_TS_INPUT" ] || exit 1

case "${FIXTURE:-good}" in
    good)
        cat <<'RULES'
-N EDGE_TS_INPUT
-A EDGE_TS_INPUT -s 100.64.0.10/32 -d 198.51.100.254/32 -p tcp -m tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT
-A EDGE_TS_INPUT -j DROP
RULES
        ;;
    wrong-source)
        cat <<'RULES'
-N EDGE_TS_INPUT
-A EDGE_TS_INPUT -s 100.64.0.99/32 -d 198.51.100.254/32 -p tcp -m tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT
-A EDGE_TS_INPUT -j DROP
RULES
        ;;
    wrong-destination)
        cat <<'RULES'
-N EDGE_TS_INPUT
-A EDGE_TS_INPUT -s 100.64.0.10/32 -d 198.51.100.253/32 -p tcp -m tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT
-A EDGE_TS_INPUT -j DROP
RULES
        ;;
    wrong-port)
        cat <<'RULES'
-N EDGE_TS_INPUT
-A EDGE_TS_INPUT -s 100.64.0.10/32 -d 198.51.100.254/32 -p tcp -m tcp --dport 8443 -m conntrack --ctstate NEW -j ACCEPT
-A EDGE_TS_INPUT -j DROP
RULES
        ;;
esac
MOCK

chmod +x "$MOCK_BIN/iptables"

PATH="$MOCK_BIN:/usr/bin:/bin"
EDGE_ROUTERCLOUD_IP="198.51.100.254"
EDGE_ROUTERCLOUD_HTTPS_PORT="443"

export PATH EDGE_ROUTERCLOUD_IP EDGE_ROUTERCLOUD_HTTPS_PORT

# shellcheck disable=SC1090
. "$FUNCS"

FIXTURE=good
export FIXTURE
routercloud_input_rule_exists 100.64.0.10/32 || {
    echo "FAIL: valid RouterCloud admin rule was rejected" >&2
    exit 1
}

FIXTURE=wrong-source
export FIXTURE
if routercloud_input_rule_exists 100.64.0.10/32; then
    echo "FAIL: RouterCloud rule for wrong source was accepted" >&2
    exit 1
fi

FIXTURE=wrong-destination
export FIXTURE
if routercloud_input_rule_exists 100.64.0.10/32; then
    echo "FAIL: RouterCloud rule for wrong destination was accepted" >&2
    exit 1
fi

FIXTURE=wrong-port
export FIXTURE
if routercloud_input_rule_exists 100.64.0.10/32; then
    echo "FAIL: RouterCloud rule for wrong port was accepted" >&2
    exit 1
fi

echo "PASS: RouterCloud healthcheck contract accepts scoped admin rule and rejects drift"
