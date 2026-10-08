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
SUPERVISOR="${EDGE_DNS_SUPERVISOR:-/jffs/addons/asus-edge/bin/edge-dns-supervisor}"
SERVICE_BIN="${EDGE_SERVICE_BIN:-/sbin/service}"
GUARD_CALL_TIMEOUT_SECONDS="${EDGE_DNS_BREAKGLASS_GUARD_CALL_TIMEOUT_SECONDS:-30}"
RESOLV_CONF="${EDGE_RESOLV_CONF:-/tmp/resolv.conf}"
BUSYBOX="${EDGE_BUSYBOX_BIN:-/bin/busybox}"
STATE_DIR="${EDGE_DNS_STATE_DIR:-/jffs/addons/asus-edge/state}"
WAN_STATE_FILE="${EDGE_DNS_BREAKGLASS_WAN_STATE:-$STATE_DIR/dns-breakglass-wan-dns.state}"
WAN_WAIT_SECONDS="${EDGE_DNS_BREAKGLASS_WAN_WAIT_SECONDS:-30}"
IP_TEST_TARGET="${EDGE_DNS_BREAKGLASS_IP_TEST_TARGET:-1.1.1.1}"
DNS_TEST_NAME="${EDGE_DNS_BREAKGLASS_DNS_TEST_NAME:-example.com}"
DNS_TEST_TIMEOUT_SECONDS="${EDGE_DNS_BREAKGLASS_DNS_TIMEOUT_SECONDS:-5}"
SERVICE_TIMEOUT_SECONDS="${EDGE_DNS_BREAKGLASS_SERVICE_TIMEOUT_SECONDS:-30}"
BOOTSTRAP_TOTAL_TIMEOUT_SECONDS="${EDGE_DNS_BREAKGLASS_BOOTSTRAP_TOTAL_TIMEOUT_SECONDS:-30}"
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

case "$SERVICE_TIMEOUT_SECONDS" in
    ''|*[!0-9]*)
        echo "ERROR: EDGE_DNS_BREAKGLASS_SERVICE_TIMEOUT_SECONDS must be a positive integer"
        exit 1
        ;;
esac

[ "$SERVICE_TIMEOUT_SECONDS" -gt 0 ] || {
    echo "ERROR: EDGE_DNS_BREAKGLASS_SERVICE_TIMEOUT_SECONDS must be greater than zero"
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

case "$BOOTSTRAP_TOTAL_TIMEOUT_SECONDS" in
    ''|0*|*[!0-9]*)
        echo "ERROR: bootstrap retry budget must be a positive integer"
        exit 1
        ;;
esac

if [ "${#BOOTSTRAP_TOTAL_TIMEOUT_SECONDS}" -gt 3 ] ||
   [ "$BOOTSTRAP_TOTAL_TIMEOUT_SECONDS" -gt 120 ]; then
    echo "ERROR: bootstrap retry budget must not exceed 120 seconds"
    exit 1
fi

case "$GUARD_CALL_TIMEOUT_SECONDS" in
    ''|0|0*|*[!0-9]*)
        echo "ERROR: DNS Guard operation timeout must be a positive integer"
        exit 1
        ;;
esac
if [ "${#GUARD_CALL_TIMEOUT_SECONDS}" -gt 3 ] ||
   [ "$GUARD_CALL_TIMEOUT_SECONDS" -gt 120 ]; then
    echo "ERROR: DNS Guard operation timeout must not exceed 120 seconds"
    exit 1
fi

# WAN service is an rc notification client. The supervisor only
# bounds the request dispatcher, not PID 1 or the WAN restart itself.

echo "=== ASUS EDGE DNS BREAK-GLASS ==="
date

if [ ! -x "$GUARD" ]; then
    echo "ERROR: DNS Guard unavailable: $GUARD"
    exit 1
fi

if [ ! -x "$SUPERVISOR" ]; then
    echo "ERROR: DNS supervisor unavailable: $SUPERVISOR"
    exit 1
fi

mkdir -p "$STATE_DIR" || {
    echo "ERROR: cannot create DNS Guard state directory: $STATE_DIR"
    exit 1
}
chmod 700 "$STATE_DIR" 2>/dev/null || true

# Serialize entire break-glass transactions, including WAN DNS snapshots.
# The supervisor closes FD 9 before executing managed child processes.
umask 077
exec 9>"$STATE_DIR/dns-breakglass-operation.lock" || exit 1

if ! /usr/bin/flock -xn 9; then
    echo "BREAKGLASS_OPERATION_LOCK=BUSY"
    echo "ERROR: another break-glass operation is running"
    exit 1
fi

guard_checked() {
    "$SUPERVISOR" "$GUARD_CALL_TIMEOUT_SECONDS" -- "$GUARD" "$@"
}

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

wan_dns_snapshot_valid() {
    [ -f "$WAN_STATE_FILE" ] || return 1

    awk -F= '
        NF != 2 { exit 1 }
        $1 == "wan_dnsenable_x" {
            if (seen_wan++) exit 1
            if ($2 != "0" && $2 != "1" && $2 != "EMPTY") exit 1
            next
        }
        $1 == "wan0_dnsenable_x" {
            if (seen_wan0++) exit 1
            if ($2 != "0" && $2 != "1" && $2 != "EMPTY") exit 1
            next
        }
        { exit 1 }
        END {
            if (seen_wan != 1 || seen_wan0 != 1) exit 1
        }
    ' "$WAN_STATE_FILE"
}

save_wan_dns_state() {
    if [ -f "$WAN_STATE_FILE" ]; then
        if wan_dns_snapshot_valid; then
            echo "WAN_DNS_SNAPSHOT=EXISTING"
            return 0
        fi

        echo "WAN_DNS_SNAPSHOT=INVALID"
        echo "ERROR: existing WAN DNS snapshot is invalid; refusing to mutate WAN DNS mode"
        return 1
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

wan_restart_dispatch_attempted=0

restart_wan_checked() {
    if [ "$wan_restart_dispatch_attempted" -eq 1 ]; then
        echo "WAN_RESTART_DISPATCH=SKIPPED_REPEAT"
        echo "WAN_RESTART=FAIL"
        return 1
    fi

    # A timeout does not tell us whether rc already received the event.
    # Never dispatch an ambiguous restart twice in one recovery attempt.
    wan_restart_dispatch_attempted=1

    if "$SUPERVISOR" "$SERVICE_TIMEOUT_SECONDS" -- "$SERVICE_BIN" restart_wan; then
        echo "WAN_RESTART_DISPATCH=SUBMITTED"
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
    internet_ip_attempt=1

    while [ "$internet_ip_attempt" -le 4 ]; do
        if ping -c 2 -W 1 "$IP_TEST_TARGET" >/dev/null 2>&1; then
            echo "INTERNET_IP=PASS"
            echo "INTERNET_IP_ATTEMPTS=$internet_ip_attempt"
            return 0
        fi

        if [ "$internet_ip_attempt" -ge 4 ]; then
            break
        fi

        echo "INTERNET_IP_RETRY=$internet_ip_attempt"
        sleep 3 || {
            echo "INTERNET_IP=FAIL"
            return 1
        }

        internet_ip_attempt=$((internet_ip_attempt + 1))
    done

    echo "INTERNET_IP=FAIL"
    return 1
}

validate_dns() {
    dns_attempt=1

    while [ "$dns_attempt" -le 2 ]; do
        if "$SUPERVISOR" "$DNS_TEST_TIMEOUT_SECONDS" -- \
            "$BUSYBOX" nslookup "$DNS_TEST_NAME" >/dev/null 2>&1; then
            echo "DNS=PASS"
            echo "DNS_ATTEMPTS=$dns_attempt"
            return 0
        fi

        if [ "$dns_attempt" -ge 2 ]; then
            break
        fi

        echo "DNS_RETRY=$dns_attempt"

        sleep 1 || {
            echo "DNS=FAIL"
            return 1
        }

        dns_attempt=$((dns_attempt + 1))
    done

    echo "DNS=FAIL"
    return 1
}

# Retry transient DNS failures after WAN restart without restarting WAN again.
# Each DNS Guard fallback probe is independently bounded by DNS Guard.
monotonic_uptime_seconds() {
    read -r uptime_value _ < /proc/uptime || return 1
    uptime_seconds=${uptime_value%%.*}

    case "$uptime_seconds" in
        ''|*[!0-9]*) return 1 ;;
    esac

    # Keep arithmetic safe on 32-bit firmware.
    [ "${#uptime_seconds}" -le 9 ] || return 1
    printf '%s\n' "$uptime_seconds"
}

wait_for_bootstrap_dns() {
    bootstrap_start="$(monotonic_uptime_seconds)" || {
        echo "BOOTSTRAP_REASSERT=MONOTONIC_CLOCK_UNAVAILABLE"
        return 1
    }

    bootstrap_deadline=$((bootstrap_start + BOOTSTRAP_TOTAL_TIMEOUT_SECONDS))
    bootstrap_attempt=1

    while [ "$bootstrap_attempt" -le 4 ]; do
        bootstrap_now="$(monotonic_uptime_seconds)" || return 1

        if [ "$bootstrap_now" -ge "$bootstrap_deadline" ]; then
            echo "BOOTSTRAP_REASSERT=TIME_BUDGET_EXHAUSTED"
            return 1
        fi

        # The child DNS Guard process is isolated and reaped by the
        # supervisor, even if the fallback itself stalls or forks descendants.
        # Remaining bootstrap budget is also the hard child deadline.
        bootstrap_remaining=$((bootstrap_deadline - bootstrap_now))
        if "$SUPERVISOR" "$bootstrap_remaining" -- "$GUARD" fallback; then
            echo "BOOTSTRAP_REASSERT_ATTEMPTS=$bootstrap_attempt"
            return 0
        else
            bootstrap_rc=$?
            case "$bootstrap_rc" in
                124)
                    echo "BOOTSTRAP_REASSERT=SUPERVISOR_TIMEOUT"
                    return 1
                    ;;
                125|126|127)
                    echo "BOOTSTRAP_REASSERT=SUPERVISOR_FAILURE"
                    return 1
                    ;;
            esac
        fi

        if [ "$bootstrap_attempt" -ge 4 ]; then
            break
        fi

        bootstrap_now="$(monotonic_uptime_seconds)" || return 1
        bootstrap_remaining=$((bootstrap_deadline - bootstrap_now))

        # Do not start another attempt if its retry delay
        # would consume the remaining budget.
        if [ "$bootstrap_remaining" -le 3 ]; then
            echo "BOOTSTRAP_REASSERT=TIME_BUDGET_EXHAUSTED"
            return 1
        fi

        echo "BOOTSTRAP_REASSERT_RETRY=$bootstrap_attempt"
        sleep 3 || return 1
        bootstrap_attempt=$((bootstrap_attempt + 1))
    done

    echo "BOOTSTRAP_REASSERT=FAILED_AFTER_RETRIES"
    return 1
}

rearm_safe_breakglass() {
    echo
    echo "=== REARM SAFE BREAK-GLASS ==="

    failures=0

    guard_checked breakglass-on restore-rollback >/dev/null 2>&1 ||
        failures=$((failures + 1))
    force_safe_wan_dns_mode >/dev/null 2>&1 ||
        failures=$((failures + 1))
    restart_wan_checked >/dev/null 2>&1 ||
        failures=$((failures + 1))
    wait_for_bootstrap_dns >/dev/null 2>&1 ||
        failures=$((failures + 1))

    if [ "$failures" -eq 0 ]; then
        echo "BREAKGLASS_REARMED=YES"
        return 0
    fi

    echo "BREAKGLASS_REARMED=PARTIAL"
    echo "BREAKGLASS_REARM_FAILURES=$failures"
    return 1
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
    echo "=== SNAPSHOT WAN DNS MODE ==="

    save_wan_dns_state || {
        echo "ERROR: unable to snapshot current WAN DNS mode"
        return 1
    }

    echo
    echo "=== ACTIVATE STICKY BREAK-GLASS ==="

    guard_checked breakglass-on desktop-emergency || {
        echo "ERROR: unable to activate sticky break-glass"
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
    if wait_for_bootstrap_dns; then
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
    guard_checked status || true

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

    if ! guard_checked ready; then
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

    if ! wait_for_bootstrap_dns; then
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

    if ! guard_checked ready; then
        echo "BREAKGLASS_CLEAR_RESULT=BLOCKED_LOCAL_DNS_UNHEALTHY_AFTER_WAN_RESTART"
        rearm_safe_breakglass
        return 1
    fi

    echo
    echo "=== CLEAR STICKY BREAK-GLASS ==="

    if ! guard_checked breakglass-off; then
        echo "BREAKGLASS_CLEAR=FAIL"
        rearm_safe_breakglass
        return 1
    fi

    echo
    echo "=== PROMOTE LOCAL DNS ==="

    if ! guard_checked promote; then
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
