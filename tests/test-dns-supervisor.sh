#!/bin/sh
set -eu
ROOT="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
TEMP="$(mktemp -d)"
cleanup() {
    if [ -s "$TEMP/escaped.pid" ]; then
        child_pid=$(cat "$TEMP/escaped.pid")
        case "$child_pid" in
            ''|*[!0-9]*) ;;
            *)
                if [ -r "/proc/$child_pid/cmdline" ] &&
                   tr '\000' ' ' <"/proc/$child_pid/cmdline" |
                     grep -Fq "$TEMP/escape-sleeper"; then
                    kill "$child_pid" 2>/dev/null || true
                fi
                ;;
        esac
    fi
    rm -rf "$TEMP"
}
trap 'cleanup' EXIT HUP INT TERM
cc -std=c11 -O2 -Wall -Wextra -Werror "$ROOT/../router/src/edge-dns-supervisor.c" -o "$TEMP/edge-dns-supervisor"
S="$TEMP/edge-dns-supervisor"
"$S" 2 -- /bin/true
printf '%s\n' 'PASS: successful command exit preserved'
rc=0
"$S" 2 -- /bin/false >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 1 ]
printf '%s\n' 'PASS: failed command exit preserved'
cat >"$TEMP/stall.sh" <<'STALLED'
#!/bin/sh
exec 9>"$2"
flock -x 9 || exit 1
/bin/sleep 30 &
echo $! > "$1"
wait
STALLED
chmod +x "$TEMP/stall.sh"
rc=0
"$S" 1 -- "$TEMP/stall.sh" "$TEMP/pid" "$TEMP/lock" >/dev/null 2>"$TEMP/log" || rc=$?
[ "$rc" -eq 124 ] || { echo "FAIL: expected timeout 124, got $rc" >&2; exit 1; }
[ -s "$TEMP/pid" ] || { echo 'FAIL: child PID not recorded' >&2; exit 1; }
pid=$(cat "$TEMP/pid")
if kill -0 "$pid" 2>/dev/null; then
  echo 'FAIL: child survived the supervisor timeout' >&2; exit 1
fi
flock -n "$TEMP/lock" true || { echo 'FAIL: flock lock remains held' >&2; exit 1; }
printf '%s\n' 'PASS: timeout=124, descendants terminated, flock released'
cat >"$TEMP/orphan.sh" <<'ORPHAN'
#!/bin/sh
/bin/sleep 30 &
echo $! > "$1"
exit 0
ORPHAN
chmod +x "$TEMP/orphan.sh"
"$S" 2 -- "$TEMP/orphan.sh" "$TEMP/orphanpid" >/dev/null
pid=$(cat "$TEMP/orphanpid")
if kill -0 "$pid" 2>/dev/null; then
  echo 'FAIL: detached background child survived normal parent exit' >&2; exit 1
fi
printf '%s\n' 'PASS: background children terminated after normal parent exit'
rc=0
"$S" nope -- /bin/true >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || { echo "FAIL: invalid argument accepted: $rc" >&2; exit 1; }
printf '%s\n' 'PASS: invalid arguments rejected'
echo '=== descendant escaping the process group ==='

ln -s /bin/sleep "$TEMP/escape-sleeper"

cat >"$TEMP/escape.sh" <<'ESCAPE'
#!/bin/sh
set -eu

setsid /bin/sh -c '
    exec 9>"$1"
    flock -x 9
    printf "%s\n" "$$" >"$2"
    exec "$3" 30
' sh "$1" "$2" "$3" &

attempt=0
while [ ! -s "$2" ] && [ "$attempt" -lt 40 ]; do
    sleep 0.05
    attempt=$((attempt + 1))
done

[ -s "$2" ] || exit 90
exec /bin/sleep 30
ESCAPE

chmod +x "$TEMP/escape.sh"

escape_rc=0
"$S" 1 -- "$TEMP/escape.sh" \
    "$TEMP/escaped.lock" \
    "$TEMP/escaped.pid" \
    "$TEMP/escape-sleeper" \
    >"$TEMP/escaped.log" 2>&1 || escape_rc=$?

if [ "$escape_rc" -ne 124 ]; then
    echo "FAIL: supervisor could not reap escaped descendant (rc=$escape_rc)" >&2
    cat "$TEMP/escaped.log" >&2
    exit 1
fi

if [ -s "$TEMP/escaped.pid" ] &&
   kill -0 "$(cat "$TEMP/escaped.pid")" 2>/dev/null; then
    echo 'FAIL: escaped descendant survived timeout' >&2
    exit 1
fi

flock -n "$TEMP/escaped.lock" true || {
    echo 'FAIL: escaped descendant retained flock lock' >&2
    exit 1
}

echo 'PASS: escaped descendant terminated and flock released'

printf '%s\n' 'SUPERVISOR_NATIVE_TESTS=PASS'
