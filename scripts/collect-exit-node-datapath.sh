#!/bin/sh
# Read-only AUDIT-02 collector. Output may contain private/public addresses.
# Review and sanitize locally; never commit raw output.

set -u

PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"
LABEL="${1:-snapshot}"

echo "WARNING: output may contain WAN/LAN/Tailscale addresses; keep it private until sanitized."
echo "=== LABEL ==="
printf '%s\n' "$LABEL"
echo "=== TIME ==="
date
echo "=== IP FORWARD ==="
cat /proc/sys/net/ipv4/ip_forward 2>/dev/null || true
echo "=== ROUTES ==="
ip route 2>/dev/null || true
echo "=== POLICY ROUTING ==="
ip rule 2>/dev/null || true
ip route show table all 2>/dev/null || true
echo "=== FILTER TABLE ==="
if iptables-save -t filter 2>/dev/null; then :; else iptables -t filter -S 2>/dev/null || true; fi
echo "=== NAT TABLE ==="
if iptables-save -t nat 2>/dev/null; then :; else iptables -t nat -S 2>/dev/null || true; fi
echo "=== EDGE FORWARD COUNTERS ==="
iptables -nvL EDGE_TS_FORWARD --line-numbers 2>/dev/null || true
echo "=== POSTROUTING COUNTERS ==="
iptables -t nat -nvL POSTROUTING --line-numbers 2>/dev/null || true
echo "=== CONNTRACK SUMMARY ==="
if [ -r /proc/net/nf_conntrack ]; then
    wc -l /proc/net/nf_conntrack 2>/dev/null || true
elif [ -r /proc/net/ip_conntrack ]; then
    wc -l /proc/net/ip_conntrack 2>/dev/null || true
else
    echo "conntrack procfs table unavailable"
fi
echo "=== TAILSCALE STATUS ==="
tailscale status 2>/dev/null || true
