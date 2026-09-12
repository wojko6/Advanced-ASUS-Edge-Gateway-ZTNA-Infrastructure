#!/bin/sh

PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"
CONFIG_FILE="${EDGE_CONFIG_FILE:-/jffs/configs/asus-edge.conf}"
FAILURES=0
WARNINGS=0

ok() { printf '[OK]   %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; WARNINGS=$((WARNINGS + 1)); }
fail() { printf '[FAIL] %s\n' "$*"; FAILURES=$((FAILURES + 1)); }

if [ -r "$CONFIG_FILE" ]; then
    # shellcheck disable=SC1090
    . "$CONFIG_FILE"
else
    warn "configuration missing: $CONFIG_FILE; using secure defaults"
fi

: "${EDGE_REQUIRE_DLNA_DISABLED:=1}"
: "${EDGE_REQUIRE_SMB_DISABLED:=1}"
: "${EDGE_REQUIRE_USB_PRINTER_DISABLED:=1}"

case "$EDGE_REQUIRE_DLNA_DISABLED" in
    0|1) ;;
    *) fail "invalid EDGE_REQUIRE_DLNA_DISABLED value: $EDGE_REQUIRE_DLNA_DISABLED" ;;
esac

case "$EDGE_REQUIRE_SMB_DISABLED" in
    0|1) ;;
    *) fail "invalid EDGE_REQUIRE_SMB_DISABLED value: $EDGE_REQUIRE_SMB_DISABLED" ;;
esac

case "$EDGE_REQUIRE_USB_PRINTER_DISABLED" in
    0|1) ;;
    *) fail "invalid EDGE_REQUIRE_USB_PRINTER_DISABLED value: $EDGE_REQUIRE_USB_PRINTER_DISABLED" ;;
esac

if [ "$EDGE_REQUIRE_DLNA_DISABLED" = "1" ]; then
    if [ "$(nvram get dms_enable 2>/dev/null)" = "0" ]; then
        ok "MiniDLNA disabled in NVRAM"
    else
        fail "MiniDLNA enabled in NVRAM"
    fi

    if pidof minidlna >/dev/null 2>&1; then
        fail "minidlna process running"
    else
        ok "minidlna process stopped"
    fi

    if netstat -lnptu 2>/dev/null | grep -E ':(1900|8200)[[:space:]]' >/dev/null 2>&1; then
        fail "DLNA/SSDP listener present on port 1900 or 8200"
    else
        ok "DLNA/SSDP ports closed"
    fi
fi

if [ "$EDGE_REQUIRE_SMB_DISABLED" = "1" ]; then
    if pidof smbd >/dev/null 2>&1; then
        fail "smbd process running"
    else
        ok "smbd process stopped"
    fi

    if pidof nmbd >/dev/null 2>&1; then
        fail "nmbd process running"
    else
        ok "nmbd process stopped"
    fi

    if netstat -lnptu 2>/dev/null | grep -E ':(139|445)[[:space:]]' >/dev/null 2>&1; then
        fail "SMB listener present on port 139 or 445"
    else
        ok "SMB ports closed"
    fi
fi

if [ "$EDGE_REQUIRE_USB_PRINTER_DISABLED" = "1" ]; then
    usb_printer_state="$(nvram get usb_printer 2>/dev/null)"
    if [ "$usb_printer_state" = "0" ]; then
        ok "ASUS USB print server disabled in NVRAM"
    else
        fail "ASUS USB print server enabled or unknown in NVRAM: ${usb_printer_state:-unset}"
    fi

    if pidof lpd >/dev/null 2>&1; then
        fail "lpd process running"
    else
        ok "lpd process stopped"
    fi

    if pidof u2ec >/dev/null 2>&1; then
        fail "u2ec process running"
    else
        ok "u2ec process stopped"
    fi

    if netstat -lnt 2>/dev/null |
        awk 'NR > 1 { local_addr=$4; if (local_addr ~ /:515$/) found=1 } END { exit !found }'; then
        fail "router TCP/515 listener present"
    else
        ok "router TCP/515 closed"
    fi
fi

printf '\nSummary: %s failure(s), %s warning(s)\n' "$FAILURES" "$WARNINGS"
[ "$FAILURES" -eq 0 ]
