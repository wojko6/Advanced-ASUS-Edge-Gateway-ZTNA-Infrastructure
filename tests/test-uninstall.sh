#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

MOCK_LOG="$TMP_DIR/ops.log"
CRON_FILE="$TMP_DIR/cron"
RESOLV="$TMP_DIR/resolv.conf"
FAIL_GUARD="$TMP_DIR/fail-guard"
FAIL_CRU_DELETE="$TMP_DIR/fail-cru-delete"
export MOCK_LOG CRON_FILE RESOLV FAIL_GUARD FAIL_CRU_DELETE

cat >"$TMP_DIR/iptables" <<'EOF'
#!/bin/sh
printf 'iptables %s\n' "$*" >>"$MOCK_LOG"
case "$*" in
    *" -D "*) exit 1 ;;
    *) exit 0 ;;
esac
EOF
chmod +x "$TMP_DIR/iptables"

cat >"$TMP_DIR/ip6tables" <<'EOF'
#!/bin/sh
printf 'ip6tables %s\n' "$*" >>"$MOCK_LOG"
case "$*" in
    *" -D "*) exit 1 ;;
    *) exit 0 ;;
esac
EOF
chmod +x "$TMP_DIR/ip6tables"

cat >"$TMP_DIR/cru" <<'EOF'
#!/bin/sh
case "${1:-}" in
    l)
        [ -f "$CRON_FILE" ] && cat "$CRON_FILE"
        ;;
    d)
        printf 'cru d %s\n' "${2:-}" >>"$MOCK_LOG"
        [ -f "$FAIL_CRU_DELETE" ] && exit 1
        if [ -f "$CRON_FILE" ]; then
            grep -v '#AsusEdgeDNSGuard#' "$CRON_FILE" >"$CRON_FILE.tmp" || true
            mv -f "$CRON_FILE.tmp" "$CRON_FILE"
        fi
        ;;
    *)
        exit 1
        ;;
esac
EOF
chmod +x "$TMP_DIR/cru"

prepare_root() {
    root="$1"
    rm -rf "$root"
    mkdir -p \
        "$root/jffs/configs" \
        "$root/jffs/scripts" \
        "$root/jffs/addons/asus-edge/bin" \
        "$root/jffs/addons/asus-edge/legacy"

    cat >"$root/jffs/configs/asus-edge.conf" <<'EOF'
EDGE_TS_IF="tailscale-test"
EDGE_LAN_IF="lan-test"
EOF

    cat >"$root/jffs/addons/asus-edge/bin/dns-guard" <<'EOF'
#!/bin/sh
printf 'dns-guard %s\n' "$*" >>"$MOCK_LOG"
[ "${1:-}" = "fallback" ] || exit 1
[ -f "$FAIL_GUARD" ] && { echo "FALLBACK=FAILED"; exit 1; }
printf '%s\n' 'nameserver 9.9.9.9' 'nameserver 149.112.112.112' >"$RESOLV"
echo "FALLBACK=PASS"
EOF
    chmod +x "$root/jffs/addons/asus-edge/bin/dns-guard"
}

run_uninstall() {
    root="$1"
    stdout="$2"
    stderr="$3"

    cp "$REPO_DIR/scripts/uninstall.sh" "$TMP_DIR/uninstall.sh"
    sed -i 's/^uid="$(current_uid)".*$/uid=0/' "$TMP_DIR/uninstall.sh"

    # Issue #285 stage 1: patch only the copied uninstaller for an isolated
    # diagnostic candidate. The repository's scripts/uninstall.sh is unchanged.
    if [ "$ISSUE285_STRICT_NAT_FIXTURE" = "1" ]; then
        python3 - "$TMP_DIR/uninstall.sh" <<'PY_NAT_CANDIDATE'
from pathlib import Path
import sys
path = Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
needle = 'remove_jump_and_chain nat PREROUTING "$EDGE_TS_IF" EDGE_TS_PREROUTING\n'
if source.count(needle) != 1:
    raise SystemExit("FAIL: candidate must find exactly one NAT cleanup call")
# Do NOT delete ambiguous -i-less jumps. Verify the chain was actually
# removed and report a nonzero result if it remains. A failed inspection is
# a HOLD, not a green cleanup claim. This is a diagnostic-only candidate,
# not a full transaction/rollback implementation.
postcheck = """\
if ! "$IPTABLES" -t nat -S PREROUTING >/dev/null 2>&1; then
    echo "ERROR: ISSUE285 NAT parent inspection unavailable; cleanup state unknown" >&2
    exit 1
fi
if "$IPTABLES" -t nat -S EDGE_TS_PREROUTING >/dev/null 2>&1; then
    echo "ERROR: ISSUE285 managed NAT chain remains; cleanup incomplete" >&2
    exit 1
fi
"""
path.write_text(source.replace(needle, needle + postcheck, 1), encoding="utf-8")
PY_NAT_CANDIDATE
    fi

    EDGE_TEST_ROOT="$root" \
    EDGE_IPTABLES="$TMP_DIR/iptables" \
    EDGE_IP6TABLES="$TMP_DIR/ip6tables" \
    EDGE_CRU="$TMP_DIR/cru" \
    sh "$TMP_DIR/uninstall.sh" >"$stdout" 2>"$stderr"
}

assert_logged() {
    grep -F -- "$1" "$MOCK_LOG" >/dev/null || {
        echo "FAIL: missing uninstall command: $1" >&2
        cat "$MOCK_LOG" >&2
        exit 1
    }
}

echo "=== validated bootstrap precedes watchdog and firewall cleanup ==="
ROOT="$TMP_DIR/root-success"
prepare_root "$ROOT"
: >"$MOCK_LOG"
printf '%s\n' '* * * * * /jffs/addons/asus-edge/bin/dns-guard auto >/dev/null 2>&1 #AsusEdgeDNSGuard#' >"$CRON_FILE"
printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"

run_uninstall "$ROOT" "$TMP_DIR/stdout" "$TMP_DIR/stderr"

grep -F 'DNS_UNINSTALL_BOOTSTRAP=PASS' "$TMP_DIR/stdout" >/dev/null
grep -F 'DNS_GUARD_WATCHDOG=REMOVED' "$TMP_DIR/stdout" >/dev/null
grep -qx 'nameserver 9.9.9.9' "$RESOLV"
grep -qx 'nameserver 149.112.112.112' "$RESOLV"
! grep -F '#AsusEdgeDNSGuard#' "$CRON_FILE" >/dev/null

fallback_line="$(grep -n -m1 '^dns-guard fallback$' "$MOCK_LOG" | cut -d: -f1)"
cru_line="$(grep -n -m1 '^cru d AsusEdgeDNSGuard$' "$MOCK_LOG" | cut -d: -f1)"
iptables_line="$(grep -n -m1 '^iptables ' "$MOCK_LOG" | cut -d: -f1)"
[ "$fallback_line" -lt "$cru_line" ]
[ "$cru_line" -lt "$iptables_line" ]

assert_logged "iptables -t filter -D INPUT -i tailscale-test -j EDGE_TS_INPUT"
assert_logged "iptables -t filter -D FORWARD -i tailscale-test -j EDGE_TS_FORWARD"
assert_logged "iptables -t nat -D PREROUTING -i tailscale-test -j EDGE_TS_PREROUTING"
assert_logged "iptables -t filter -D FORWARD -i lan-test -j EDGE_LAN_DOT_FORWARD"
assert_logged "iptables -t filter -F EDGE_LAN_DOT_FORWARD"
assert_logged "iptables -t filter -X EDGE_LAN_DOT_FORWARD"
assert_logged "iptables -t nat -D PREROUTING -i lan-test -j EDGE_LAN_DNS_PREROUTING"
assert_logged "iptables -t nat -F EDGE_LAN_DNS_PREROUTING"
assert_logged "iptables -t nat -X EDGE_LAN_DNS_PREROUTING"
assert_logged "ip6tables -t filter -D INPUT -i tailscale-test -j EDGE_TS6_INPUT"
assert_logged "ip6tables -t filter -D FORWARD -i tailscale-test -j EDGE_TS6_FORWARD"
grep -F "Runtime rules removed and previous hooks restored when available." "$TMP_DIR/stdout" >/dev/null

echo "=== bootstrap failure aborts before watchdog or firewall mutation ==="
FAIL_ROOT="$TMP_DIR/root-fail-guard"
prepare_root "$FAIL_ROOT"
: >"$MOCK_LOG"
printf '%s\n' '* * * * * /jffs/addons/asus-edge/bin/dns-guard auto >/dev/null 2>&1 #AsusEdgeDNSGuard#' >"$CRON_FILE"
: >"$FAIL_GUARD"

if run_uninstall "$FAIL_ROOT" "$TMP_DIR/fail-guard.out" "$TMP_DIR/fail-guard.err"; then
    echo "FAIL: uninstall succeeded although DNS Guard fallback failed" >&2
    exit 1
fi
grep -F 'refusing uninstall' "$TMP_DIR/fail-guard.err" >/dev/null
grep -qx 'dns-guard fallback' "$MOCK_LOG"
! grep -qx 'cru d AsusEdgeDNSGuard' "$MOCK_LOG"
! grep -q '^iptables ' "$MOCK_LOG"
rm -f "$FAIL_GUARD"

echo "=== watchdog removal failure aborts before firewall mutation ==="
FAIL_CRU_ROOT="$TMP_DIR/root-fail-cru"
prepare_root "$FAIL_CRU_ROOT"
: >"$MOCK_LOG"
printf '%s\n' '* * * * * /jffs/addons/asus-edge/bin/dns-guard auto >/dev/null 2>&1 #AsusEdgeDNSGuard#' >"$CRON_FILE"
: >"$FAIL_CRU_DELETE"

if run_uninstall "$FAIL_CRU_ROOT" "$TMP_DIR/fail-cru.out" "$TMP_DIR/fail-cru.err"; then
    echo "FAIL: uninstall succeeded although watchdog remained scheduled" >&2
    exit 1
fi
grep -F 'watchdog remains scheduled' "$TMP_DIR/fail-cru.err" >/dev/null
grep -qx 'dns-guard fallback' "$MOCK_LOG"
grep -qx 'cru d AsusEdgeDNSGuard' "$MOCK_LOG"
! grep -q '^iptables ' "$MOCK_LOG"
rm -f "$FAIL_CRU_DELETE"

echo "PASS: uninstall restores independent DNS before watchdog and firewall cleanup"

# Issue #285 / Fedora-only synthetic NAT laboratory. Replace the disposable
# IPv4 mock (never real iptables) with a stateful one *after* the existing tests.
# Historical no-interface ownership is NOT proven: RED cases characterize the
# present deinstaller behavior and must not be treated as authorization to fix.
cat >"$TMP_DIR/iptables" <<'PY_MOCK'
#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
with open(os.environ["MOCK_LOG"], "a", encoding="utf-8") as log:
    log.write("iptables " + " ".join(args) + "\n")
if len(args) < 4 or args[0] != "-t" or args[2] not in ("-D", "-F", "-X", "-S"):
    sys.exit(2)
key = args[1] + "/" + args[3]
action = args[2]
state_path = Path(os.environ["MOCK_NAT_STATE"])
state = json.loads(state_path.read_text(encoding="utf-8"))
if key not in state:
    sys.exit(1)  # this mock models only the selected NAT chains
rules = state[key]

if action == "-S":
    if len(args) != 4 or os.environ.get("MOCK_DENY_INSPECT", "") == key:
        sys.exit(1)
    for rule in rules:
        print("-A " + args[3] + " " + rule)
    sys.exit(0)

if action == "-D":
    candidate = " ".join(args[4:])
    if os.environ.get("MOCK_DENY_DELETE", "") == key + "|" + candidate:
        sys.exit(1)
    if candidate not in rules:
        sys.exit(1)
    rules.remove(candidate)
elif action == "-F":
    if len(args) != 4:
        sys.exit(2)
    state[key] = []
else:  # -X must fail if the chain still has referencing jumps
    if len(args) != 4 or rules:
        sys.exit(1)
    target = args[3]
    for existing in state.values():
        if any((" -j " + target + " ") in (" " + item + " ") or
               (" -g " + target + " ") in (" " + item + " ")
               for item in existing):
            sys.exit(1)
    del state[key]

state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
PY_MOCK
chmod 0700 "$TMP_DIR/iptables"
MOCK_NAT_STATE="$TMP_DIR/nat-state.json"
export MOCK_NAT_STATE

seed_nat_state() {
    python3 - "$MOCK_NAT_STATE" "$1" <<'PY_SEED'
import json
from pathlib import Path
import sys
state = {
    "nat/PREROUTING": [
        "-i tailscale-test -j EDGE_TS_PREROUTING",
        "-i lan-test -j EDGE_LAN_DNS_PREROUTING",
        "-p udp --dport 123 -j FOREIGN_NAT",
    ],
    "nat/EDGE_TS_PREROUTING": [
        "-p tcp --dport 53 -j REDIRECT --to-ports 53"
    ],
    "nat/EDGE_LAN_DNS_PREROUTING": ["-j RETURN"],
    "nat/FOREIGN_NAT": ["-j RETURN"],
}
mode = sys.argv[2]
if mode == "duplicates":
    state["nat/PREROUTING"].insert(
        0, "-i tailscale-test -j EDGE_TS_PREROUTING")
elif mode == "hypothetical-legacy":
    state["nat/PREROUTING"].insert(0, "-j EDGE_TS_PREROUTING")
elif mode not in ("current", "denied"):
    raise SystemExit("unexpected synthetic NAT mode")
Path(sys.argv[1]).write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
PY_SEED
}

assert_nat_case() {
    python3 - "$MOCK_NAT_STATE" "$1" <<'PY_ASSERT'
import json
from pathlib import Path
import sys
state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
mode = sys.argv[2]
jump = "-i tailscale-test -j EDGE_TS_PREROUTING"
legacy = "-j EDGE_TS_PREROUTING"
parent = state["nat/PREROUTING"]
assert "-p udp --dport 123 -j FOREIGN_NAT" in parent
assert state["nat/FOREIGN_NAT"] == ["-j RETURN"]
assert "-i lan-test -j EDGE_LAN_DNS_PREROUTING" not in parent
assert "nat/EDGE_LAN_DNS_PREROUTING" not in state
if mode in ("current", "duplicates", "repeat"):
    assert jump not in parent
    assert legacy not in parent
    assert "nat/EDGE_TS_PREROUTING" not in state
    print("PASS: NAT owned scoped rule removed; unrelated NAT preserved:", mode)
elif mode == "hypothetical-legacy":
    assert legacy in parent
    assert jump not in parent
    assert state["nat/EDGE_TS_PREROUTING"] == []
    print("EXPECTED_RED: unqualified synthetic NAT jump prevents -X cleanup")
    print("HOLD: historical syntax/project ownership not verified")
elif mode == "denied":
    assert jump in parent
    assert state["nat/EDGE_TS_PREROUTING"] == []
    print("EXPECTED_RED: exact -D failure leaves jump; ignored -X failure")
else:
    raise AssertionError("unknown case")
PY_ASSERT
}

# Only an isolated root and copied deinstaller may be used. These fixtures do
# not connect to the ASUS, alter Linux iptables or touch any live JFFS paths.
NAT_LAB_ROOT="$TMP_DIR/nat-lab-root"
prepare_root "$NAT_LAB_ROOT"
: >"$CRON_FILE"
: >"$MOCK_LOG"
seed_nat_state current
run_uninstall "$NAT_LAB_ROOT" "$TMP_DIR/nat-current.out" "$TMP_DIR/nat-current.err"
assert_nat_case current
grep -Fx 'dns-guard fallback' "$MOCK_LOG" >/dev/null
grep -F 'ip6tables -t filter -D INPUT -i tailscale-test -j EDGE_TS6_INPUT' "$MOCK_LOG" >/dev/null
grep -F 'Runtime rules removed' "$TMP_DIR/nat-current.out" >/dev/null
printf 'PASS: DNS fallback and IPv6 mock calls preserved in NAT lab\n'

# Run twice: absent managed chains should remain absent (no new mutations).
cp "$MOCK_NAT_STATE" "$TMP_DIR/nat-before-second.json"
: >"$MOCK_LOG"
run_uninstall "$NAT_LAB_ROOT" "$TMP_DIR/nat-repeat.out" "$TMP_DIR/nat-repeat.err"
cmp "$MOCK_NAT_STATE" "$TMP_DIR/nat-before-second.json"
assert_nat_case repeat

seed_nat_state duplicates
: >"$MOCK_LOG"
run_uninstall "$NAT_LAB_ROOT" "$TMP_DIR/nat-dupes.out" "$TMP_DIR/nat-dupes.err"
assert_nat_case duplicates

# Hypothetical unqualified jump: existing deinstaller only deletes -i scoped
# jumps. It reports success even though -X cannot remove the referenced chain.
seed_nat_state hypothetical-legacy
: >"$MOCK_LOG"
run_uninstall "$NAT_LAB_ROOT" "$TMP_DIR/nat-legacy.out" "$TMP_DIR/nat-legacy.err"
assert_nat_case hypothetical-legacy
grep -F 'iptables -t nat -X EDGE_TS_PREROUTING' "$MOCK_LOG" >/dev/null
grep -F 'Runtime rules removed' "$TMP_DIR/nat-legacy.out" >/dev/null

# Exact scoped -D failure should not be misreported as a complete cleanup.
seed_nat_state denied
: >"$MOCK_LOG"
MOCK_DENY_DELETE='nat/PREROUTING|-i tailscale-test -j EDGE_TS_PREROUTING'
export MOCK_DENY_DELETE
run_uninstall "$NAT_LAB_ROOT" "$TMP_DIR/nat-denied.out" "$TMP_DIR/nat-denied.err"
unset MOCK_DENY_DELETE
assert_nat_case denied
grep -F 'iptables -t nat -X EDGE_TS_PREROUTING' "$MOCK_LOG" >/dev/null
grep -F 'Runtime rules removed' "$TMP_DIR/nat-denied.out" >/dev/null

# DNS Guard fallback failure must stop before any fake IPv4/IPv6 operations.
seed_nat_state current
cp "$MOCK_NAT_STATE" "$TMP_DIR/nat-before-fail.json"
: >"$MOCK_LOG"
: >"$FAIL_GUARD"
if run_uninstall "$NAT_LAB_ROOT" "$TMP_DIR/nat-dnsfail.out" "$TMP_DIR/nat-dnsfail.err"; then
    echo "FAIL: NAT lab allowed uninstall after DNS fallback failure" >&2
    exit 1
fi
rm -f "$FAIL_GUARD"
cmp "$MOCK_NAT_STATE" "$TMP_DIR/nat-before-fail.json"
! grep -E '^(iptables|ip6tables) ' "$MOCK_LOG" >/dev/null
grep -Fx 'dns-guard fallback' "$MOCK_LOG" >/dev/null
echo "PASS: NAT lab fail-closed on DNS bootstrap failure"
# Stage 1 candidate: a disposable, root-check-transformed copy of uninstall
# only. It reports failed NAT-chain cleanup instead of hiding the failure.
# Production scripts/uninstall.sh remains untouched. No unqualified jump is
# deleted, and the candidate does NOT implement transactional rollback.
echo "=== issue #285 / diagnostic-only strict NAT postflight candidate ==="
ISSUE285_STRICT_NAT_FIXTURE=1
export ISSUE285_STRICT_NAT_FIXTURE
seed_nat_state current
: >"$MOCK_LOG"
run_uninstall "$NAT_LAB_ROOT" "$TMP_DIR/strict-current.out" "$TMP_DIR/strict-current.err"
assert_nat_case current
grep -F 'Runtime rules removed' "$TMP_DIR/strict-current.out" >/dev/null
grep -F 'iptables -t nat -S PREROUTING' "$MOCK_LOG" >/dev/null
grep -F 'ip6tables -t filter -D INPUT -i tailscale-test -j EDGE_TS6_INPUT' "$MOCK_LOG" >/dev/null
echo "PASS: strict candidate removes scoped NAT and preserves IPv6 mock invocation"

cp "$MOCK_NAT_STATE" "$TMP_DIR/strict-before-repeat.json"
run_uninstall "$NAT_LAB_ROOT" "$TMP_DIR/strict-repeat.out" "$TMP_DIR/strict-repeat.err"
cmp "$MOCK_NAT_STATE" "$TMP_DIR/strict-before-repeat.json"
echo "PASS: strict candidate is idempotent on missing managed NAT chain"

# Unverified historical jump is intentionally preserved; a nonzero status
# replaces the previous misleading "Runtime rules removed" success verdict.
seed_nat_state hypothetical-legacy
if run_uninstall "$NAT_LAB_ROOT" "$TMP_DIR/strict-legacy.out" "$TMP_DIR/strict-legacy.err"; then
    echo "FAIL: strict candidate claimed success for unqualified jump" >&2
    exit 1
fi
grep -F 'ERROR: ISSUE285 managed NAT chain remains' "$TMP_DIR/strict-legacy.err" >/dev/null
! grep -F 'Runtime rules removed' "$TMP_DIR/strict-legacy.out" >/dev/null
python3 - "$MOCK_NAT_STATE" <<'PY_STRICT_ASSERT'
import json
from pathlib import Path
import sys
s = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert "-j EDGE_TS_PREROUTING" in s["nat/PREROUTING"]
assert "-p udp --dport 123 -j FOREIGN_NAT" in s["nat/PREROUTING"]
assert "nat/EDGE_TS_PREROUTING" in s
assert "-i lan-test -j EDGE_LAN_DNS_PREROUTING" in s["nat/PREROUTING"], "partial cleanup must be explicit"
PY_STRICT_ASSERT
echo "PASS: strict candidate reports incomplete cleanup, does not delete ambiguous NAT jump"

seed_nat_state denied
MOCK_DENY_DELETE='nat/PREROUTING|-i tailscale-test -j EDGE_TS_PREROUTING'
export MOCK_DENY_DELETE
if run_uninstall "$NAT_LAB_ROOT" "$TMP_DIR/strict-denied.out" "$TMP_DIR/strict-denied.err"; then
    echo "FAIL: strict candidate hid exact deletion failure" >&2
    exit 1
fi
unset MOCK_DENY_DELETE
grep -F 'ERROR: ISSUE285 managed NAT chain remains' "$TMP_DIR/strict-denied.err" >/dev/null
! grep -F 'Runtime rules removed' "$TMP_DIR/strict-denied.out" >/dev/null
echo "PASS: strict candidate reports failed exact deletion"

# If even the parent-rule inspection fails, the postflight must report
# unknown rather than success. This is deliberately not treated as absence.
seed_nat_state current
MOCK_DENY_INSPECT='nat/PREROUTING'
export MOCK_DENY_INSPECT
if run_uninstall "$NAT_LAB_ROOT" "$TMP_DIR/strict-inspect.out" "$TMP_DIR/strict-inspect.err"; then
    echo "FAIL: strict candidate treated unreadable NAT parent as clean" >&2
    exit 1
fi
unset MOCK_DENY_INSPECT
grep -F 'ERROR: ISSUE285 NAT parent inspection unavailable' "$TMP_DIR/strict-inspect.err" >/dev/null
! grep -F 'Runtime rules removed' "$TMP_DIR/strict-inspect.out" >/dev/null
echo "PASS: strict candidate fails closed when postflight parent inspection is unavailable"
unset ISSUE285_STRICT_NAT_FIXTURE
echo "ISSUE285_CANDIDATE=PASS_LAB_ONLY_DEPLOYMENT_HOLD"

echo "ISSUE285_LAB=PASS_WITH_EXPECTED_RED_AND_DEPLOYMENT_HOLD"
