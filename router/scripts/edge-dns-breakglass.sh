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
STATE_DIR="${EDGE_DNS_STATE_DIR:-/jffs/addons/asus-edge/state}"
WAN_STATE_FILE="${EDGE_DNS_BREAKGLASS_WAN_STATE:-$STATE_DIR/dns-breakglass-wan-dns.state}"
WAN_WAIT_SECONDS="${EDGE_DNS_BREAKGLASS_WAN_WAIT_SECONDS:-30}"
IP_TEST_TARGET="${EDGE_DNS_BREAKGLASS_IP_TEST_TARGET:-1.1.1.1}"
DNS_TEST_NAME="${EDGE_DNS_BREAKGLASS_DNS_TEST_NAME:-example.com}"
DNS_TEST_TIMEOUT_SECONDS="${EDGE_DNS_BREAKGLASS_DNS_TIMEOUT_SECONDS:-5}"
ACTION="${1:-on}"

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

case "$DNS_TEST_TIMEOUT_SECONDS" in
    ''|*[!0-9]*)
        echo "ERROR: EDGE_DNS_BREAKGLASS_DNS_TIMEOUT_SECONDS must be a positive integer"
        exit 1
        ;;
esac

[ "$DNS_TEST_TIMEOUT_SECONDS" -gt 0 ] || {
    echo "ERROR: EDGE_DNS_BREAKGLASS_DNS_TIMEOUT_SECONDS must be greater than zero"
    exit 1
}

case "$ACTION" in
    on|off)
        ;;
    *)
        echo "Usage: $0 [on|off]"
        exit 2
        ;;
esac

echo "=== ASUS EDGE DNS BREAK-GLASS ==="
date

if [ ! -x "$GUARD" ]; then
    echo "ERROR: DNS Guard unavailable: $GUARD"
    exit 1
fi

mkdir -p "$STATE_DIR" || {
    echo "ERROR: cannot create DNS Guard state directory: $STATE_DIR"
    exit 1
}
chmod 700 "$STATE_DIR" 2>/dev/null || true

encode_nvram_value() {
    value="$1"

    case "$value" in
        0|1)
            printf '%s\n' "$value"
            ;;
        '')
            printf '%s\n' EMPTY
            ;;
        *)
            return 1
            ;;
    esac
}

save_wan_dns_state() {
    if [ -f "$WAN_STATE_FILE" ]; then
        echo "WAN_DNS_SNAPSHOT=EXISTING"
        return 0
    fi

    wan_value="$(nvram get wan_dnsenable_x 2>/dev/null)" || return 1
    wan0_value="$(nvram get wan0_dnsenable_x 2>/dev/null)" || return 1

    wan_token="$(encode_nvram_value "$wan_value")" || {
        echo "ERROR: unsupported wan_dnsenable_x value: $wan_value"
        return 1
    }
    wan0_token="$(encode_nvram_value "$wan0_value")" || {
        echo "ERROR: unsupported wan0_dnsenable_x value: $wan0_value"
        return 1
    }

    tmp="${WAN_STATE_FILE}.tmp.$$"
    umask 077

    {
        printf 'wan_dnsenable_x=%s\n' "$wan_token"
        printf 'wan0_dnsenable_x=%s\n' "$wan0_token"
    } >"$tmp" || {
        rm -f "$tmp"
        return 1
    }

    chmod 600 "$tmp" 2>/dev/null || true

    mv -f "$tmp" "$WAN_STATE_FILE" || {
        rm -f "$tmp"
        return 1
    }

    echo "WAN_DNS_SNAPSHOT=SAVED"
    return 0
}

read_saved_value() {
    key="$1"

    awk -F= -v key="$key" '
        $1 == key {
            print $2
            found=1
            exit
        }
        END { if (!found) exit 1 }
    ' "$WAN_STATE_FILE"
}

apply_saved_value() {
    key="$1"
    token="$2"
    current="$(nvram get "$key" 2>/dev/null)" || return 1

    case "$token" in
        0|1)
            [ "$current" = "$token" ] && return 2
            nvram set "$key=$token" || return 1
            ;;
        EMPTY)
            [ -z "$current" ] && return 2
            nvram unset "$key" || return 1
            ;;
        *)
            return 1
            ;;
    esac

    return 0
}

restore_wan_dns_state() {
    [ -f "$WAN_STATE_FILE" ] || {
        echo "WAN_DNS_RESTORE=NO_SNAPSHOT"
        return 0
    }

    wan_token="$(read_saved_value wan_dnsenable_x)" || return 1
    wan0_token="$(read_saved_value wan0_dnsenable_x)" || return 1

    changed=0

    apply_saved_value wan_dnsenable_x "$wan_token"
    rc=$?
    case "$rc" in
        0) changed=1 ;;
        2) ;;
        *) return 1 ;;
    esac

    apply_saved_value wan0_dnsenable_x "$wan0_token"
    rc=$?
    case "$rc" in
        0) changed=1 ;;
        2) ;;
        *) return 1 ;;
    esac

    if [ "$changed" -eq 1 ]; then
        nvram commit || return 1
        sync
        echo "WAN_DNS_RESTORE=UPDATED"
    else
        echo "WAN_DNS_RESTORE=ALREADY_RESTORED"
    fi

    return 0
}

force_safe_wan_dns_mode() {
    changed=0

    if [ "$(nvram get wan_dnsenable_x 2>/dev/null)" != "1" ]; then
        nvram set wan_dnsenable_x=1 || return 1
        changed=1
    fi

    if [ "$(nvram get wan0_dnsenable_x 2>/dev/null)" != "1" ]; then
        nvram set wan0_dnsenable_x=1 || return 1
        changed=1
    fi

    if [ "$changed" -eq 1 ]; then
        nvram commit || return 1
        sync
        echo "NVRAM_DNS_MODE=UPDATED"
    else
        echo "NVRAM_DNS_MODE=ALREADY_SAFE"
    fi

    return 0
}

restart_wan_checked() {
    if service restart_wan; then
        echo "WAN_RESTART=PASS"
        return 0
    fi

    echo "WAN_RESTART=FAIL"
    return 1
}

wait_for_wan_ip() {
    elapsed=0

    while [ "$elapsed" -lt "$WAN_WAIT_SECONDS" ]; do
        if ping -c 1 -W 1 "$IP_TEST_TARGET" >/dev/null 2>&1; then
            echo "WAN_IP=PASS"
            return 0
        fi

        elapsed=$((elapsed + 1))
        sleep 1
    done

    echo "WAN_IP=TIMEOUT"
    return 1
}

validate_internet_ip() {
    if ping -c 2 -W 1 "$IP_TEST_TARGET" >/dev/null 2>&1; then
        echo "INTERNET_IP=PASS"
        return 0
    fi

    echo "INTERNET_IP=FAIL"
    return 1
}

validate_dns() {
    if "$BUSYBOX" timeout "$DNS_TEST_TIMEOUT_SECONDS" \
        "$BUSYBOX" nslookup "$DNS_TEST_NAME" >/dev/null 2>&1; then
        echo "DNS=PASS"
        return 0
    fi

    echo "DNS=FAIL"
    return 1
}

rearm_safe_breakglass() {
    echo
    echo "=== REARM SAFE BREAK-GLASS ==="

    "$GUARD" breakglass-on restore-rollback >/dev/null 2>&1 || true
    force_safe_wan_dns_mode || true
    service restart_wan >/dev/null 2>&1 || true
    "$GUARD" fallback >/dev/null 2>&1 || true

    echo "BREAKGLASS_REARMED=YES"
}

show_services() {
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
}

activate_breakglass() {
    echo
    echo "=== ACTIVATE STICKY BREAK-GLASS ==="

    "$GUARD" breakglass-on desktop-emergency || {
        echo "ERROR: unable to activate sticky break-glass"
        return 1
    }

    echo
    echo "=== SNAPSHOT WAN DNS MODE ==="

    save_wan_dns_state || {
        echo "ERROR: unable to snapshot current WAN DNS mode"
        return 1
    }

    echo
    echo "=== ENSURE INDEPENDENT WAN DNS MODE ==="

    force_safe_wan_dns_mode || {
        echo "ERROR: failed to enable independent WAN DNS mode"

        # The snapshot already exists at this point. If forcing the emergency
        # WAN-DNS mode fails after mutating only one NVRAM key, restore the
        # pre-break-glass values before returning. Keep the sticky break-glass
        # flag and snapshot in place so the operator still has a recovery
        # anchor and can retry safely.
        if restore_wan_dns_state; then
            echo "WAN_DNS_ACTIVATION_ROLLBACK=PASS"
        else
            echo "WAN_DNS_ACTIVATION_ROLLBACK=FAIL"
        fi

        return 1
    }

    failures=0

    echo
    echo "=== RESTART WAN ==="
    restart_wan_checked || failures=$((failures + 1))

    echo
    echo "=== WAIT FOR WAN ==="
    wait_for_wan_ip || failures=$((failures + 1))

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
    validate_internet_ip || failures=$((failures + 1))

    echo
    echo "=== DNS TEST ==="
    validate_dns || failures=$((failures + 1))

    show_services

    echo
    echo "=== BREAK-GLASS STATE ==="
    "$GUARD" status || true

    echo
    if [ "$failures" -eq 0 ]; then
        echo "BREAKGLASS_RESULT=PASS"
        echo "NOTE: break-glass remains ACTIVE until explicitly cleared with: $0 off"
        return 0
    fi

    echo "BREAKGLASS_RESULT=FAIL"
    echo "NOTE: sticky break-glass and WAN DNS snapshot remain active for recovery."
    return 1
}

deactivate_breakglass() {
    echo
    echo "=== VERIFY LOCAL DNS BEFORE RESTORE ==="

    if ! "$GUARD" ready; then
        echo "BREAKGLASS_CLEAR_RESULT=BLOCKED_LOCAL_DNS_UNHEALTHY"
        echo "NOTE: break-glass remains ACTIVE and WAN DNS settings are unchanged."
        return 1
    fi

    echo
    echo "=== RESTORE PRE-BREAKGLASS WAN DNS MODE ==="

    if ! restore_wan_dns_state; then
        echo "WAN_DNS_RESTORE=FAIL"
        rearm_safe_breakglass
        return 1
    fi

    echo
    echo "=== RESTART WAN WITH RESTORED DNS MODE ==="

    if ! restart_wan_checked; then
        rearm_safe_breakglass
        return 1
    fi

    echo
    echo "=== WAIT FOR WAN ==="

    if ! wait_for_wan_ip; then
        rearm_safe_breakglass
        return 1
    fi

    echo
    echo "=== VERIFY BOOTSTRAP PATH AFTER RESTORE ==="

    if ! "$GUARD" fallback; then
        echo "FALLBACK_REASSERT=FAIL"
        rearm_safe_breakglass
        return 1
    fi
    echo "FALLBACK_REASSERT=PASS"

    if ! validate_dns; then
        rearm_safe_breakglass
        return 1
    fi

    echo
    echo "=== RECHECK LOCAL DNS BEFORE CLEAR ==="

    if ! "$GUARD" ready; then
        echo "BREAKGLASS_CLEAR_RESULT=BLOCKED_LOCAL_DNS_UNHEALTHY_AFTER_WAN_RESTART"
        rearm_safe_breakglass
        return 1
    fi

    echo
    echo "=== CLEAR STICKY BREAK-GLASS ==="

    if ! "$GUARD" breakglass-off; then
        echo "BREAKGLASS_CLEAR=FAIL"
        rearm_safe_breakglass
        return 1
    fi

    echo
    echo "=== PROMOTE LOCAL DNS ==="

    if ! "$GUARD" promote; then
        echo "LOCAL_PROMOTION_AFTER_CLEAR=FAIL"
        rearm_safe_breakglass
        return 1
    fi

    echo "LOCAL_PROMOTION_AFTER_CLEAR=PASS"

    rm -f "$WAN_STATE_FILE" || {
        echo "ERROR: unable to remove restored WAN DNS snapshot"
        rearm_safe_breakglass
        return 1
    }

    echo
    echo "BREAKGLASS_CLEAR_RESULT=PASS"
    echo "WAN_DNS_SNAPSHOT=REMOVED"
    return 0
}

case "$ACTION" in
    on)
        activate_breakglass
        ;;
    off)
        deactivate_breakglass
        ;;
esac
