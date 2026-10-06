#!/bin/sh
# ASUS_EDGE_MANAGED_RECOVERY

PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"

GUARD="/jffs/addons/asus-edge/bin/dns-guard"

echo "=== ASUS EDGE DNS BREAK-GLASS ==="
date

if [ ! -x "$GUARD" ]; then
    echo "ERROR: DNS Guard unavailable: $GUARD"
    exit 1
fi

echo
echo "=== ACTIVATE STICKY BREAK-GLASS ==="

"$GUARD" breakglass-on desktop-emergency || {
    echo "ERROR: unable to activate break-glass"
    exit 1
}

echo
echo "=== ENSURE INDEPENDENT WAN DNS MODE ==="

changed=0

if [ "$(nvram get wan_dnsenable_x)" != "1" ]; then
    nvram set wan_dnsenable_x=1
    changed=1
fi

if [ "$(nvram get wan0_dnsenable_x)" != "1" ]; then
    nvram set wan0_dnsenable_x=1
    changed=1
fi

if [ "$changed" -eq 1 ]; then
    nvram commit
    sync
    echo "NVRAM_DNS_MODE=UPDATED"
else
    echo "NVRAM_DNS_MODE=ALREADY_SAFE"
fi

echo
echo "=== RESTART WAN ==="
service restart_wan

echo
echo "=== WAIT FOR WAN ==="

elapsed=0

while [ "$elapsed" -lt 30 ]; do
    if ping -c 1 -W 1 1.1.1.1 >/dev/null 2>&1; then
        echo "WAN_IP=PASS"
        break
    fi

    elapsed=$((elapsed + 1))
    sleep 1
done

[ "$elapsed" -lt 30 ] || echo "WAN_IP=TIMEOUT"

echo
echo "=== REASSERT BOOTSTRAP DNS ==="
"$GUARD" fallback || true

echo
echo "=== CURRENT RESOLVER ==="
cat /tmp/resolv.conf

echo
echo "=== INTERNET IP TEST ==="
ping -c 2 1.1.1.1 || true

echo
echo "=== DNS TEST ==="
busybox nslookup example.com 2>&1 || true

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
"$GUARD" status

echo
echo "=== BREAK-GLASS COMPLETE ==="
echo "NOTE: break-glass remains ACTIVE until explicitly cleared."
