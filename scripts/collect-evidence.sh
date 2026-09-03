#!/bin/sh
# Collect a reviewable, sanitized validation snapshot on the router.

set -u

PATH="${EVIDENCE_PATH:-/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin}"
umask 077

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="${1:-/tmp/asus-edge-evidence-$TIMESTAMP}"
CONFIG_FILE="${EDGE_CONFIG_FILE:-/jffs/configs/asus-edge.conf}"
HEALTHCHECK_BIN="${EVIDENCE_HEALTHCHECK:-/jffs/addons/asus-edge/bin/healthcheck.sh}"
IPTABLES_BIN="${EVIDENCE_IPTABLES:-iptables}"
IP6TABLES_BIN="${EVIDENCE_IP6TABLES:-ip6tables}"
DIG_BIN="${EVIDENCE_DIG:-dig}"

[ ! -e "$OUTPUT_DIR" ] || {
    echo "ERROR: output path already exists: $OUTPUT_DIR" >&2
    exit 1
}
mkdir -p "$OUTPUT_DIR" || exit 1

# Older Asuswrt-Merlin BusyBox shells may not implement "command -v".
# Resolve executables directly through PATH so collection works consistently.
executable_exists() {
    executable_name="$1"
    case "$executable_name" in
        */*)
            [ -x "$executable_name" ]
            return
            ;;
    esac

    saved_ifs="$IFS"
    IFS=:
    # PATH splitting is intentional here.
    # shellcheck disable=SC2086
    for executable_dir in $PATH; do
        [ -n "$executable_dir" ] || continue
        if [ -x "$executable_dir/$executable_name" ]; then
            IFS="$saved_ifs"
            return 0
        fi
    done
    IFS="$saved_ifs"
    return 1
}

sha256sum_run() {
    if executable_exists sha256sum; then
        sha256sum "$@"
        return
    fi
    if [ -x /bin/busybox ] && /bin/busybox sha256sum /dev/null >/dev/null 2>&1; then
        /bin/busybox sha256sum "$@"
        return
    fi
    return 1
}

if [ -r "$CONFIG_FILE" ]; then
    # shellcheck disable=SC1090
    . "$CONFIG_FILE"
fi
: "${EDGE_UNBOUND_PORT:=53535}"

first_line_or() {
    fallback="$1"
    shift
    if executable_exists "$1"; then
        value="$("$@" 2>/dev/null | head -n 1)"
        [ -n "$value" ] && printf '%s\n' "$value" || printf '%s\n' "$fallback"
    else
        printf '%s\n' "$fallback"
    fi
}

nvram_value() {
    if executable_exists nvram; then
        nvram get "$1" 2>/dev/null
    fi
}

redact_firewall_addresses() {
    awk '
        /^num[[:space:]]/ { print; next }
        /^[[:space:]]*[0-9]+[[:space:]]/ {
            if (NF >= 10) {
                $9 = "[source-redacted]"
                $10 = "[destination-redacted]"
            }
        }
        {
            for (field = 1; field <= NF; field++) {
                if ($field ~ /^to:[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*/) {
                    sub(/^to:[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*/, "to:[translated-address-redacted]", $field)
                }
            }
            print
        }
    '
}

capture_chain() {
    tool="$1"
    table="$2"
    chain="$3"
    if executable_exists "$tool"; then
        "$tool" -t "$table" -nvL "$chain" --line-numbers 2>&1 \
            | redact_firewall_addresses
    else
        printf '%s is not available\n' "$tool"
    fi
}

MODEL="$(nvram_value productid)"
FIRMWARE="$(nvram_value firmver)"
BUILD="$(nvram_value buildno)"
EXTEND="$(nvram_value extendno)"
KERNEL="$(uname -r 2>/dev/null || printf 'unavailable')"
TAILSCALE_VERSION="$(first_line_or "not installed" tailscale version)"
UNBOUND_VERSION="$(first_line_or "not installed" unbound -V)"
SYSLOG_VERSION="$(first_line_or "not installed" syslog-ng --version)"
MEM_TOTAL="$(awk '/^MemTotal:/ { print $2 " " $3; exit }' /proc/meminfo 2>/dev/null)"
UPTIME_SECONDS="$(cut -d. -f1 /proc/uptime 2>/dev/null)"

{
    echo "# Environment snapshot"
    echo
    echo "| Field | Value |"
    echo "|---|---|"
    printf '| Collected (UTC) | %s |\n' "$TIMESTAMP"
    printf '| Router model | %s |\n' "${MODEL:-unavailable}"
    printf '| Firmware | %s %s %s |\n' "${FIRMWARE:-unavailable}" "${BUILD:-}" "${EXTEND:-}"
    printf '| Kernel | %s |\n' "$KERNEL"
    printf '| Memory | %s |\n' "${MEM_TOTAL:-unavailable}"
    printf '| Uptime (seconds) | %s |\n' "${UPTIME_SECONDS:-unavailable}"
    printf '| Tailscale | %s |\n' "$TAILSCALE_VERSION"
    printf '| Unbound | %s |\n' "$UNBOUND_VERSION"
    printf '| syslog-ng | %s |\n' "$SYSLOG_VERSION"
    echo
    echo "Hostnames, user identities, Tailscale status, routing tables, and configuration contents are intentionally excluded."
} >"$OUTPUT_DIR/environment.md"

{
    echo "# Health check"
    echo
    echo '```text'
    if [ -x "$HEALTHCHECK_BIN" ]; then
        "$HEALTHCHECK_BIN" 2>&1 || true
    else
        echo "Healthcheck is not available at $HEALTHCHECK_BIN"
    fi
    echo '```'
} >"$OUTPUT_DIR/healthcheck.md"

{
    echo "# Sanitized firewall counters"
    echo
    echo "Source and destination addresses are replaced before this file is written."
    for chain in EDGE_TS_INPUT EDGE_TS_FORWARD; do
        echo
        printf '## IPv4 filter/%s\n\n' "$chain"
        echo '```text'
        capture_chain "$IPTABLES_BIN" filter "$chain"
        echo '```'
    done
    echo
    echo "## IPv4 nat/EDGE_TS_PREROUTING"
    echo
    echo '```text'
    capture_chain "$IPTABLES_BIN" nat EDGE_TS_PREROUTING
    echo '```'
    for chain in EDGE_TS6_INPUT EDGE_TS6_FORWARD; do
        echo
        printf '## IPv6 filter/%s\n\n' "$chain"
        echo '```text'
        capture_chain "$IP6TABLES_BIN" filter "$chain"
        echo '```'
    done
} >"$OUTPUT_DIR/firewall-counters.md"

DNS_OUTPUT=""
if executable_exists "$DIG_BIN"; then
    DNS_OUTPUT="$("$DIG_BIN" +time=3 +tries=1 +dnssec -p "$EDGE_UNBOUND_PORT" @127.0.0.1 cloudflare.com A 2>/dev/null || true)"
fi
DNS_STATUS="$(printf '%s\n' "$DNS_OUTPUT" | sed -n 's/.*status: \([^,]*\).*/\1/p' | head -n 1)"
DNS_QUERY_TIME="$(printf '%s\n' "$DNS_OUTPUT" | awk -F': ' '/Query time:/ { print $2; exit }')"
if printf '%s\n' "$DNS_OUTPUT" | grep -q 'flags:.* ad'; then
    DNSSEC_RESULT="PASS (AD flag present)"
else
    DNSSEC_RESULT="NOT CONFIRMED"
fi

{
    echo "# Direct Unbound validation"
    echo
    echo "| Check | Result |"
    echo "|---|---|"
    printf '| Resolver endpoint | loopback:%s |\n' "$EDGE_UNBOUND_PORT"
    printf '| DNS status | %s |\n' "${DNS_STATUS:-unavailable}"
    printf '| DNSSEC validation | %s |\n' "$DNSSEC_RESULT"
    printf '| Query time | %s |\n' "${DNS_QUERY_TIME:-unavailable}"
    echo
    echo "The full DNS response is not stored because it can contain addresses that require manual review."
} >"$OUTPUT_DIR/dns-validation.md"

{
    echo "# Evidence bundle"
    echo
    echo "Generated: $TIMESTAMP"
    echo
    echo "- Review every file manually before publishing."
    echo "- Do not add packet captures, public IP addresses, credentials, hostnames, email addresses, or Tailscale node state."
    echo "- Complete the remote-client matrix separately; this local snapshot cannot prove WAN or identity-policy behavior."
} >"$OUTPUT_DIR/README.md"

if ! (
    cd "$OUTPUT_DIR" || exit 1
    sha256sum_run README.md environment.md healthcheck.md firewall-counters.md dns-validation.md
) >"$OUTPUT_DIR/SHA256SUMS"; then
    rm -f "$OUTPUT_DIR/SHA256SUMS"
    echo "WARNING: SHA-256 utility unavailable; manifest not created" >&2
fi

echo "Evidence snapshot created: $OUTPUT_DIR"
echo "Review it manually before copying selected files into the public repository."

