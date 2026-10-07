#!/bin/sh
# ASUS_EDGE_MANAGED_RECOVERY

BASE_PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"

if [ -n "${EDGE_TEST_PATH_PREFIX:-}" ]; then
    PATH="${EDGE_TEST_PATH_PREFIX}:${BASE_PATH}"
else
    PATH="$BASE_PATH"
fi
export PATH

GUARD="${EDGE_DNS_GUARD:-/jffs/addons/asus-edge/bin/dns-guard}"
RESOLV_CONF="${EDGE_RESOLV_CONF:-/tmp/resolv.conf}"
BUSYBOX="${EDGE_BUSYBOX_BIN:-/bin/busybox}"
WAN_WAIT_SECONDS="${EDGE_DNS_BREAKGLASS_WAN_WAIT_SECONDS:-30}"
IP_TEST_TARGET="${EDGE_DNS_BREAKGLASS_IP_TEST_TARGET:-1.1.1.1}"
DNS_TEST_NAME="${EDGE_DNS_BREAKGLASS_DNS_TEST_NAME:-example.com}"

case "$WAN_WAIT_SECONDS" in
    ''|*[!0-9]*)
        echo "ERROR: EDGE_DNS_BREAKGLASS_WAN_WAIT_SECONDS must be a positive integer"
        exit 1
        ;;
esac

[ "$WAN_WAIT_SECONDS" -gt 0 ] || {
    echo "ERROR: EDGE_DNS_BREAKGLASS_WAN_WAIT_SECONDS must be greater than zero"
    exit 1
}

echo "=== ASUS EDGE DNS BREAK-GLASS ==="
date

if [ ! -x "$GUARD" ]; then
    echo "ERROR: DNS Guard unavailable: $GUARD"
    exit 1
fi

echo
echo "=== ACTIVATE STICKY BREAK-GLASS ==="

"$GUARD" breakglass-on desktop-emergency || {
    echo "ERROR: unable to activate sticky break-glass"
    exit 1
}

echo
echo "=== ENSURE INDEPENDENT WAN DNS MODE ==="

changed=0

if [ "$(nvram get wan_dnsenable_x 2>/dev/null)" != "1" ]; then
    nvram set wan_dnsenable_x=1 || {
        echo "ERROR: failed to enable wan_dnsenable_x"
        exit 1
    }
    changed=1
fi

if [ "$(nvram get wan0_dnsenable_x 2>/dev/null)" != "1" ]; then
    nvram set wan0_dnsenable_x=1 || {
        echo "ERROR: failed to enable wan0_dnsenable_x"
        exit 1
    }
    changed=1
fi

if [ "$changed" -eq 1 ]; then
    nvram commit || {
        echo "ERROR: failed to commit WAN DNS mode"
        exit 1
    }
    sync
    echo "NVRAM_DNS_MODE=UPDATED"
else
    echo "NVRAM_DNS_MODE=ALREADY_SAFE"
fi

failures=0

echo
echo "=== RESTART WAN ==="

if service restart_wan; then
    echo "WAN_RESTART=PASS"
else
    echo "WAN_RESTART=FAIL"
    failures=$((failures + 1))
fi

echo
echo "=== WAIT FOR WAN ==="

elapsed=0
wan_ready=0

while [ "$elapsed" -lt "$WAN_WAIT_SECONDS" ]; do
    if ping -c 1 -W 1 "$IP_TEST_TARGET" >/dev/null 2>&1; then
        wan_ready=1
        echo "WAN_IP=PASS"
        break
    fi

    elapsed=$((elapsed + 1))
    sleep 1
done

if [ "$wan_ready" -ne 1 ]; then
    echo "WAN_IP=TIMEOUT"
    failures=$((failures + 1))
fi

echo
echo "=== REASSERT BOOTSTRAP DNS ==="

if "$GUARD" fallback; then
    echo "FALLBACK_REASSERT=PASS"
else
    echo "FALLBACK_REASSERT=FAIL"
    failures=$((failures + 1))
fi

echo
echo "=== CURRENT RESOLVER ==="
cat "$RESOLV_CONF" 2>/dev/null || true

echo
echo "=== INTERNET IP TEST ==="

if ping -c 2 -W 1 "$IP_TEST_TARGET" >/dev/null 2>&1; then
    echo "INTERNET_IP=PASS"
else
    echo "INTERNET_IP=FAIL"
    failures=$((failures + 1))
fi

echo
echo "=== DNS TEST ==="

if "$BUSYBOX" nslookup "$DNS_TEST_NAME" >/dev/null 2>&1; then
    echo "DNS=PASS"
else
    echo "DNS=FAIL"
    failures=$((failures + 1))
fi

echo
echo "=== SERVICES ==="
pidof unbound >/dev/null 2>&1 &&
    echo "UNBOUND=RUNNING" ||
    echo "UNBOUND=NOT_RUNNING"

pidof pihole-FTL >/dev/null 2>&1 &&
    echo "PIHOLE=RUNNING" ||
    echo "PIHOLE=NOT_RUNNING"

pidof tailscaled >/dev/null 2>&1 &&
    echo "TAILSCALE=RUNNING" ||
    echo "TAILSCALE=NOT_RUNNING"

echo
echo "=== BREAK-GLASS STATE ==="
"$GUARD" status || true

echo
if [ "$failures" -eq 0 ]; then
    echo "BREAKGLASS_RESULT=PASS"
    echo "NOTE: break-glass remains ACTIVE until explicitly cleared."
    exit 0
fi

echo "BREAKGLASS_RESULT=FAIL"
echo "NOTE: sticky break-glass remains ACTIVE; inspect WAN/bootstrap DNS before clearing it."
exit 1
