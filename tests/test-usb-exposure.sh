#!/bin/sh

set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
AUDIT_SCRIPT="$REPO_DIR/scripts/check-usb-exposure.sh"
TMP_DIR="$(mktemp -d)"
MOCK_BIN="$TMP_DIR/bin"
CONFIG_FILE="$TMP_DIR/edge.conf"
STATE_FILE="$TMP_DIR/state"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$MOCK_BIN"

cat >"$MOCK_BIN/nvram" <<'EOF'
#!/bin/sh
[ "$1" = "get" ] || exit 2
case "$2" in
    dms_enable) printf '%s\n' "${MOCK_DMS_ENABLE:-0}" ;;
    usb_printer) printf '%s\n' "${MOCK_USB_PRINTER:-0}" ;;
    *) exit 1 ;;
esac
EOF

cat >"$MOCK_BIN/pidof" <<'EOF'
#!/bin/sh
case " ${MOCK_RUNNING_PROCESSES:-} " in
    *" $1 "*) printf '1234\n'; exit 0 ;;
    *) exit 1 ;;
esac
EOF

cat >"$MOCK_BIN/netstat" <<'EOF'
#!/bin/sh
printf '%s\n' 'Proto Recv-Q Send-Q Local Address           Foreign Address         State'
case "${MOCK_LISTENERS:-}" in
    *515*) printf '%s\n' 'tcp        0      0 0.0.0.0:515             0.0.0.0:*               LISTEN' ;;
esac
case "${MOCK_LISTENERS:-}" in
    *8200*) printf '%s\n' 'tcp        0      0 0.0.0:8200            0.0.0.0:*               LISTEN' ;;
esac
case "${MOCK_LISTENERS:-}" in
    *1900*) printf '%s\n' 'udp        0      0 0.0.0.0:1900            0.0.0.0:*' ;;
esac
case "${MOCK_LISTENERS:-}" in
    *445*) printf '%s\n' 'tcp        0      0 0.0.0.0:445             0.0.0.0:*               LISTEN' ;;
esac
case "${MOCK_LISTENERS:-}" in
    *139*) printf '%s\n' 'tcp        0      0 0.0.0.0:139             0.0.0.0:*               LISTEN' ;;
esac
EOF

chmod +x "$MOCK_BIN/nvram" "$MOCK_BIN/pidof" "$MOCK_BIN/netstat"

cat >"$CONFIG_FILE" <<'EOF'
EDGE_REQUIRE_DLNA_DISABLED=1
EDGE_REQUIRE_SMB_DISABLED=1
EDGE_REQUIRE_USB_PRINTER_DISABLED=1
EOF

run_audit() {
    EDGE_AUDIT_PATH="$MOCK_BIN:/usr/bin:/bin" \
    EDGE_CONFIG_FILE="$CONFIG_FILE" \
    MOCK_DMS_ENABLE="${MOCK_DMS_ENABLE:-0}" \
    MOCK_USB_PRINTER="${MOCK_USB_PRINTER:-0}" \
    MOCK_RUNNING_PROCESSES="${MOCK_RUNNING_PROCESSES:-}" \
    MOCK_LISTENERS="${MOCK_LISTENERS:-}" \
    sh "$AUDIT_SCRIPT"
}

OUTPUT="$(run_audit)"
printf '%s\n' "$OUTPUT" | grep -F 'Summary: 0 failure(s)' >/dev/null

MOCK_RUNNING_PROCESSES='lpd'
if run_audit >"$STATE_FILE" 2>&1; then
    echo "FAIL: running lpd was accepted" >&2
    exit 1
fi
grep -F '[FAIL] lpd process running' "$STATE_FILE" >/dev/null
MOCK_RUNNING_PROCESSES=''

MOCK_USB_PRINTER=1
if run_audit >"$STATE_FILE" 2>&1; then
    echo "FAIL: enabled USB print server was accepted" >&2
    exit 1
fi
grep -F '[FAIL] ASUS USB print server enabled or unknown in NVRAM: 1' "$STATE_FILE" >/dev/null
MOCK_USB_PRINTER=0

MOCK_LISTENERS=515
if run_audit >"$STATE_FILE" 2>&1; then
    echo "FAIL: TCP/515 listener was accepted" >&2
    exit 1
fi
grep -F '[FAIL] router TCP/515 listener present' "$STATE_FILE" >/dev/null
MOCK_LISTENERS=''

MOCK_RUNNING_PROCESSES='smbd'
if run_audit >"$STATE_FILE" 2>&1; then
    echo "FAIL: running smbd was accepted" >&2
    exit 1
fi
grep -F '[FAIL] smbd process running' "$STATE_FILE" >/dev/null
MOCK_RUNNING_PROCESSES=''

MOCK_DMS_ENABLE=1
if run_audit >"$STATE_FILE" 2>&1; then
    echo "FAIL: enabled MiniDLNA was accepted" >&2
    exit 1
fi
grep -F '[FAIL] MiniDLNA enabled in NVRAM' "$STATE_FILE" >/dev/null
MOCK_DMS_ENABLE=0

cat >"$CONFIG_FILE" <<'EOF'
EDGE_REQUIRE_DLNA_DISABLED=2
EDGE_REQUIRE_SMB_DISABLED=1
EDGE_REQUIRE_USB_PRINTER_DISABLED=1
EOF
if run_audit >"$STATE_FILE" 2>&1; then
    echo "FAIL: invalid USB-audit boolean was accepted" >&2
    exit 1
fi
grep -F '[FAIL] invalid EDGE_REQUIRE_DLNA_DISABLED value: 2' "$STATE_FILE" >/dev/null

echo "PASS: USB exposure audit behavior"
