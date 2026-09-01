#!/bin/sh

set -u

ROUTER_IP="${1:-}"
DENIED_LAN_IP="${2:-}"

[ -n "$ROUTER_IP" ] || {
    echo "Usage: $0 ROUTER_TAILSCALE_IP [DENIED_LAN_IP]" >&2
    exit 2
}

FAILURES=0
pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*"; FAILURES=$((FAILURES + 1)); }

if command -v dig >/dev/null 2>&1 && dig +time=3 +tries=1 @1.1.1.1 example.com A >/dev/null 2>&1; then
    pass "classic DNS query completed; confirm DNAT with router capture"
else
    fail "classic DNS query failed"
fi

if command -v nc >/dev/null 2>&1; then
    nc -z -w 3 "$ROUTER_IP" 8443 >/dev/null 2>&1 && pass "router HTTPS reachable for this identity" || fail "router HTTPS unavailable"
    nc -z -w 3 "$ROUTER_IP" 22 >/dev/null 2>&1 && fail "router SSH unexpectedly reachable" || pass "router SSH denied"
fi

if [ -n "$DENIED_LAN_IP" ] && command -v nc >/dev/null 2>&1; then
    nc -z -w 3 "$DENIED_LAN_IP" 445 >/dev/null 2>&1 && fail "SMB unexpectedly reachable" || pass "SMB denied"
fi

[ "$FAILURES" -eq 0 ]
