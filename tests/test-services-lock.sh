#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
SCRIPT="$REPO_DIR/router/scripts/services-start"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

HELPERS="$TMP_DIR/lock-helpers.sh"
sed -n '/^# BEGIN services-start lock helpers$/,/^# END services-start lock helpers$/p' "$SCRIPT" >"$HELPERS"

grep -F 'acquire_services_lock()' "$HELPERS" >/dev/null || {
    echo "FAIL: services-start lock helpers could not be extracted" >&2
    exit 1
}

log() {
    printf '%s\n' "$*" >>"$TMP_DIR/log"
}

LOCK_DIR="$TMP_DIR/services.lock"
LOCK_OWNER="$LOCK_DIR/owner"

# shellcheck disable=SC1090
. "$HELPERS"

# 1. Fresh acquisition records the current process identity and releases cleanly.
acquire_services_lock || {
    echo "FAIL: fresh services-start lock acquisition failed" >&2
    exit 1
}
[ -r "$LOCK_OWNER" ] || {
    echo "FAIL: lock owner metadata was not written" >&2
    exit 1
}
read -r recorded_pid recorded_start <"$LOCK_OWNER"
[ "$recorded_pid" = "$$" ] || {
    echo "FAIL: lock owner PID does not match current process" >&2
    exit 1
}
[ "$recorded_start" = "$(services_lock_start_time "$$")" ] || {
    echo "FAIL: lock owner process start time does not match" >&2
    exit 1
}
release_services_lock
[ ! -e "$LOCK_DIR" ] || {
    echo "FAIL: released services-start lock directory remains" >&2
    exit 1
}

# 2. A lock left by a dead/nonexistent process is reclaimed.
mkdir "$LOCK_DIR"
printf '%s %s\n' 999999 1 >"$LOCK_OWNER"
acquire_services_lock || {
    echo "FAIL: stale services-start lock was not reclaimed" >&2
    exit 1
}
grep -F 'WARNING: reclaiming stale services-start lock' "$TMP_DIR/log" >/dev/null || {
    echo "FAIL: stale-lock recovery was not logged" >&2
    exit 1
}
read -r recorded_pid recorded_start <"$LOCK_OWNER"
[ "$recorded_pid" = "$$" ] || {
    echo "FAIL: reclaimed lock was not assigned to current process" >&2
    exit 1
}
release_services_lock

# 3. A lock owned by this live process is treated as active and preserved.
mkdir "$LOCK_DIR"
printf '%s %s\n' "$$" "$(services_lock_start_time "$$")" >"$LOCK_OWNER"
if acquire_services_lock; then
    echo "FAIL: live competing services-start lock was overwritten" >&2
    exit 1
else
    rc="$?"
fi
[ "$rc" = "1" ] || {
    echo "FAIL: live competing lock returned unexpected status $rc" >&2
    exit 1
}
[ -r "$LOCK_OWNER" ] || {
    echo "FAIL: live competing lock was removed" >&2
    exit 1
}
release_services_lock

# 4. Unknown contents fail closed instead of using rm -rf on the lock path.
mkdir "$LOCK_DIR"
touch "$LOCK_DIR/unexpected"
if acquire_services_lock; then
    echo "FAIL: non-empty stale lock directory was unsafely reclaimed" >&2
    exit 1
else
    rc="$?"
fi
[ "$rc" = "2" ] || {
    echo "FAIL: unsafe stale lock returned unexpected status $rc" >&2
    exit 1
}
[ -e "$LOCK_DIR/unexpected" ] || {
    echo "FAIL: unexpected lock contents were deleted" >&2
    exit 1
}

echo "PASS: services-start lock survives crashes without permanent stale-lock blockage"
