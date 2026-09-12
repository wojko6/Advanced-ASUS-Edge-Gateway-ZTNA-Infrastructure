#!/bin/sh
set -eu
FILE="${1:-router/scripts/firewall-start}"
wan_line="$(grep -n '^WAN_IF=""$' "$FILE" | head -n 1 | cut -d: -f1)"
mutation_line="$(grep -n '^"\$IPTABLES" -t filter -I INPUT 1 ' "$FILE" | head -n 1 | cut -d: -f1)"
[ -n "$wan_line" ] && [ -n "$mutation_line" ] && [ "$wan_line" -lt "$mutation_line" ] || { echo 'FAIL: WAN prevalidation must precede iptables mutation' >&2; exit 1; }
grep -F 'WAN_IF="$(detect_wan_if)" || die "cannot detect valid WAN interface; set EDGE_WAN_IF"' "$FILE" >/dev/null || exit 1
! grep -F 'then WAN_IF="$(detect_wan_if)' "$FILE" >/dev/null || { echo 'FAIL: late WAN discovery remains' >&2; exit 1; }
grep -F 'EDGE_TS_FORWARD -o "$WAN_IF" -j ACCEPT' "$FILE" >/dev/null || exit 1
echo 'PASS: WAN interface is resolved before firewall mutation'
