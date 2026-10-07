#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

FUNCS="$TMP_DIR/dns-guard-health-functions.sh"

awk '
    /^# BEGIN DNS Guard health helpers/ { capture=1; next }
    /^# END DNS Guard health helpers/ { capture=0 }
    capture { print }
' "$REPO_DIR/scripts/healthcheck.sh" >"$FUNCS"

for function_name in dns_guard_cron_entry_ok dns_guard_resolver_mode; do
    grep -F "$function_name()" "$FUNCS" >/dev/null || {
        echo "FAIL: could not extract $function_name from healthcheck" >&2
        exit 1
    }
done

MOCK_BIN="$TMP_DIR/bin"
mkdir -p "$MOCK_BIN"

CRON_FILE="$TMP_DIR/cron"
RESOLV="$TMP_DIR/resolv.conf"

cat >"$MOCK_BIN/cru" <<'EOF'
#!/bin/sh
[ "${1:-}" = "l" ] || exit 1
cat "${CRON_FILE:?}"
EOF
chmod +x "$MOCK_BIN/cru"

executable_exists() {
    [ "$1" = "cru" ] && [ -x "$MOCK_BIN/cru" ]
}

PATH="$MOCK_BIN:/usr/bin:/bin"
DNS_GUARD_BIN="/jffs/addons/asus-edge/bin/dns-guard"
DNS_GUARD_RESOLV_CONF="$RESOLV"
EDGE_DNS_LOCAL_RESOLVER_IP="192.0.2.53"
export PATH CRON_FILE DNS_GUARD_BIN DNS_GUARD_RESOLV_CONF EDGE_DNS_LOCAL_RESOLVER_IP

# shellcheck disable=SC1090
. "$FUNCS"

echo "=== exact watchdog entry ==="
cat >"$CRON_FILE" <<'EOF'
* * * * * /jffs/addons/asus-edge/bin/dns-guard auto >/dev/null 2>&1 #AsusEdgeDNSGuard#
EOF
dns_guard_cron_entry_ok || {
    echo "FAIL: exact DNS Guard watchdog entry rejected" >&2
    exit 1
}

echo "=== drifted watchdog entry ==="
cat >"$CRON_FILE" <<'EOF'
*/5 * * * * /jffs/addons/asus-edge/bin/dns-guard auto >/dev/null 2>&1 #AsusEdgeDNSGuard#
EOF
if dns_guard_cron_entry_ok; then
    echo "FAIL: drifted DNS Guard watchdog schedule accepted" >&2
    exit 1
fi

echo "=== local resolver mode ==="
printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"
[ "$(dns_guard_resolver_mode)" = "LOCAL" ] || {
    echo "FAIL: local resolver mode not detected" >&2
    exit 1
}

echo "=== bootstrap resolver mode ==="
printf '%s\n' 'nameserver 9.9.9.9' 'nameserver 149.112.112.112' >"$RESOLV"
[ "$(dns_guard_resolver_mode)" = "BOOTSTRAP" ] || {
    echo "FAIL: bootstrap resolver mode not detected" >&2
    exit 1
}

echo "=== mixed resolver mode is rejected ==="
printf '%s\n' 'nameserver 192.0.2.53' 'nameserver 9.9.9.9' >"$RESOLV"
if dns_guard_resolver_mode >/tmp/dns-guard-mode.out 2>/dev/null; then
    echo "FAIL: mixed resolver state accepted" >&2
    exit 1
fi
grep -qx 'MIXED' /tmp/dns-guard-mode.out
rm -f /tmp/dns-guard-mode.out

echo "=== empty resolver is rejected ==="
: >"$RESOLV"
if dns_guard_resolver_mode >/tmp/dns-guard-mode.out 2>/dev/null; then
    echo "FAIL: empty resolver state accepted" >&2
    exit 1
fi
grep -qx 'UNKNOWN' /tmp/dns-guard-mode.out
rm -f /tmp/dns-guard-mode.out

echo "PASS: DNS Guard healthcheck contract detects watchdog drift and resolver state"
