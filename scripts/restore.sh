#!/bin/sh

set -u

PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"
JOURNAL_BASE="${EDGE_RESTORE_JOURNAL_DIR:-/jffs/addons/asus-edge-recovery}"
JOURNAL_DIR="$JOURNAL_BASE/current"

current_uid() {
    while read -r status_key status_uid _; do
        if [ "$status_key" = "Uid:" ]; then
            printf '%s\n' "$status_uid"
            return 0
        fi
    done </proc/self/status
    return 1
}

secure_temp_dir() {
    temp_prefix="$1"
    temp_counter=0
    while [ "$temp_counter" -lt 100 ]; do
        temp_candidate="$temp_prefix.$.$temp_counter"
        if (umask 077 && mkdir "$temp_candidate") 2>/dev/null; then
            printf '%s\n' "$temp_candidate"
            return 0
        fi
        temp_counter=$((temp_counter + 1))
    done
    return 1
}

sha256sum_run() {
    for sum_bin in /opt/bin/sha256sum /opt/sbin/sha256sum /usr/bin/sha256sum /usr/sbin/sha256sum /bin/sha256sum /sbin/sha256sum; do
        [ -x "$sum_bin" ] && { "$sum_bin" "$@"; return; }
    done
    if [ -x /bin/busybox ] && /bin/busybox sha256sum /dev/null >/dev/null 2>&1; then
        /bin/busybox sha256sum "$@"
        return
    fi
    echo "ERROR: sha256sum unavailable" >&2
    return 1
}

ARCHIVE="${1:-}"
MODE="${2:---dry-run}"

usage() {
    echo "Usage: $0 BACKUP.tar.gz [--dry-run|--apply]"
}

[ -n "$ARCHIVE" ] || { usage; exit 2; }
[ -f "$ARCHIVE" ] || { echo "ERROR: backup not found" >&2; exit 1; }
case "$MODE" in --dry-run|--apply) ;; *) usage; exit 2 ;; esac

TMP_DIR="$(secure_temp_dir /tmp/asus-edge-restore)" || {
    echo "ERROR: cannot create private restore workspace" >&2
    exit 1
}
cleanup_tmp() {
    rm -rf "$TMP_DIR"
}
trap cleanup_tmp EXIT

tar -tzf "$ARCHIVE" >"$TMP_DIR/paths" || exit 1
if ! awk '
    !/^[A-Za-z0-9_.$\/-]+$/ || /^\// || /(^|\/)\.\.?($|\/)/ { exit 1 }
    {
        sub(/\/$/, "")
        if (seen[$0]++) exit 1
        split($0, parts, "/")
        if (root != "" && root != parts[1]) exit 1
        root=parts[1]
    }
    END { if (root == "") exit 1 }
' "$TMP_DIR/paths"; then
    echo "ERROR: unsafe, duplicate, or multiple-root archive paths" >&2
    exit 1
fi

tar -tvzf "$ARCHIVE" >"$TMP_DIR/types" || exit 1
if ! awk 'substr($1,1,1) != "-" && substr($1,1,1) != "d" { exit 1 }' "$TMP_DIR/types"; then
    echo "ERROR: only regular files and directories are accepted in backups" >&2
    exit 1
fi

mkdir "$TMP_DIR/payload" || exit 1
tar -xzf "$ARCHIVE" -C "$TMP_DIR/payload" || exit 1
ROOT="$(find "$TMP_DIR/payload" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[ -n "$ROOT" ] || { echo "ERROR: invalid backup" >&2; exit 1; }
[ -f "$ROOT/SHA256SUMS" ] || { echo "ERROR: missing manifest" >&2; exit 1; }

# Check manifest paths BEFORE sha256sum opens them, and require an exact
# one-to-one match with payload files. Hashes detect corruption, not authenticity.
if ! awk '
    {
        hash=substr($0,1,64); separator=substr($0,65,2); path=substr($0,67)
        if (length(hash) != 64 || hash ~ /[^0-9a-fA-F]/) exit 1
        if (separator != "  " && separator != " *") exit 1
        sub(/^\.\//, "", path)
        if (path !~ /^[A-Za-z0-9_.$\/-]+$/ || path ~ /^\// ||
            path ~ /(^|\/)\.\.?($|\/)/ || path == "SHA256SUMS" || seen[path]++) exit 1
        if (path ~ /^jffs\/addons\/asus-edge-recovery(\/|$)/) exit 1
        print path
    }
' "$ROOT/SHA256SUMS" >"$TMP_DIR/manifest-paths"; then
    echo "ERROR: invalid manifest paths or records" >&2
    exit 1
fi

(cd "$ROOT" && find . -type f ! -path './SHA256SUMS' | sed 's#^\./##' | sort) >"$TMP_DIR/payload-paths" || exit 1
sort "$TMP_DIR/manifest-paths" >"$TMP_DIR/sorted-manifest" || exit 1
if ! cmp -s "$TMP_DIR/payload-paths" "$TMP_DIR/sorted-manifest"; then
    echo "ERROR: manifest must cover every payload file exactly once" >&2
    exit 1
fi
(cd "$ROOT" && sha256sum_run -c SHA256SUMS) || exit 1

echo "Verified backup contents:"
find "$ROOT" -type f | sed "s#^$ROOT/##" | sort

[ "$MODE" = "--apply" ] || { echo "Dry-run only. Re-run with --apply to restore."; exit 0; }
uid="$(current_uid)" || { echo "ERROR: cannot determine current user" >&2; exit 1; }
[ "$uid" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }

case "$JOURNAL_BASE" in
    /jffs/addons/*|/opt/var/lib/*) ;;
    *)
        echo "ERROR: restore journal must be below /jffs/addons or /opt/var/lib" >&2
        exit 1
        ;;
esac
[ ! -L "$JOURNAL_BASE" ] || { echo "ERROR: restore journal base must not be a symlink" >&2; exit 1; }
mkdir -p "$JOURNAL_BASE" || exit 1
chmod 0700 "$JOURNAL_BASE" 2>/dev/null || true
[ ! -L "$JOURNAL_DIR" ] || { echo "ERROR: restore journal must not be a symlink" >&2; exit 1; }

state_write() {
    state_value="$1"
    printf '%s\n' "$state_value" >"$JOURNAL_DIR/STATE.new" || return 1
    mv "$JOURNAL_DIR/STATE.new" "$JOURNAL_DIR/STATE" || return 1
}

rollback_from_journal() {
    rollback_journal="$1"
    rollback_dir="$rollback_journal/pre-restore"
    rollback_manifest="$rollback_journal/manifest-paths"
    [ -f "$rollback_manifest" ] || {
        echo "ERROR: recovery journal is missing manifest-paths: $rollback_journal" >&2
        return 1
    }
    [ -d "$rollback_dir" ] || {
        echo "ERROR: recovery journal is missing pre-restore snapshot: $rollback_journal" >&2
        return 1
    }

    rollback_failed=0
    while IFS= read -r relative_path; do
        case "$relative_path" in
            jffs/*|opt/*) ;;
            *) continue ;;
        esac
        live_path="/$relative_path"
        rollback_path="$rollback_dir/$relative_path"
        marker="$rollback_dir/.absent/$relative_path"

        if [ -f "$marker" ]; then
            rm -rf "$live_path" || rollback_failed=1
        else
            rm -rf "$live_path" || rollback_failed=1
            mkdir -p "$(dirname "$live_path")" || rollback_failed=1
            cp -Rp "$rollback_path" "$live_path" || rollback_failed=1
        fi
    done <"$rollback_manifest"

    if [ "$rollback_failed" -ne 0 ]; then
        echo "ERROR: rollback encountered errors; journal preserved at $rollback_journal" >&2
        return 1
    fi
    echo "Rollback completed; pre-restore state recovered." >&2
    return 0
}

recover_pending_journal() {
    [ -d "$JOURNAL_DIR" ] || return 0
    [ -f "$JOURNAL_DIR/STATE" ] || {
        echo "ERROR: restore recovery directory exists without STATE: $JOURNAL_DIR" >&2
        return 1
    }

    journal_state="$(cat "$JOURNAL_DIR/STATE" 2>/dev/null)"
    case "$journal_state" in
        PREPARED)
            # No live mutation begins before APPLYING is persisted.
            rm -rf "$JOURNAL_DIR" || return 1
            return 0
            ;;
        APPLYING)
            echo "WARNING: interrupted restore detected; recovering pre-restore state before any new apply" >&2
            rollback_from_journal "$JOURNAL_DIR" || return 1
            rm -rf "$JOURNAL_DIR" || return 1
            echo "Recovery completed. Re-run the requested restore after reviewing the router state." >&2
            return 10
            ;;
        COMMITTED)
            rm -rf "$JOURNAL_DIR" || return 1
            return 0
            ;;
        *)
            echo "ERROR: unknown restore journal state: $journal_state" >&2
            return 1
            ;;
    esac
}

recovery_rc=0
recover_pending_journal || recovery_rc=$?
if [ "$recovery_rc" -eq 10 ]; then
    exit 3
fi
[ "$recovery_rc" -eq 0 ] || exit 1

mkdir "$JOURNAL_DIR" || {
    echo "ERROR: cannot create restore recovery journal: $JOURNAL_DIR" >&2
    exit 1
}
chmod 0700 "$JOURNAL_DIR" 2>/dev/null || true
cp "$TMP_DIR/manifest-paths" "$JOURNAL_DIR/manifest-paths" || exit 1
ROLLBACK_DIR="$JOURNAL_DIR/pre-restore"
mkdir "$ROLLBACK_DIR" || exit 1
state_write PREPARED || exit 1

# Snapshot every live path that the archive can overwrite. An absent marker is
# recorded for paths that do not exist so rollback can remove newly created data.
while IFS= read -r relative_path; do
    case "$relative_path" in
        jffs/*|opt/*) ;;
        *) continue ;;
    esac
    live_path="/$relative_path"
    rollback_path="$ROLLBACK_DIR/$relative_path"
    marker="$ROLLBACK_DIR/.absent/$relative_path"
    mkdir -p "$(dirname "$rollback_path")" "$(dirname "$marker")" || exit 1
    if [ -e "$live_path" ] || [ -L "$live_path" ]; then
        cp -Rp "$live_path" "$rollback_path" || {
            echo "ERROR: cannot snapshot $live_path; restore not started" >&2
            rm -rf "$JOURNAL_DIR"
            exit 1
        }
    else
        : >"$marker" || exit 1
    fi
done <"$TMP_DIR/manifest-paths"

state_write APPLYING || {
    echo "ERROR: cannot persist APPLYING restore state; restore not started" >&2
    rm -rf "$JOURNAL_DIR"
    exit 1
}
APPLY_ACTIVE=1

interrupt_restore() {
    signal_name="$1"
    trap - HUP INT TERM
    echo "ERROR: restore interrupted by $signal_name; attempting rollback" >&2
    if [ "$APPLY_ACTIVE" = "1" ] && rollback_from_journal "$JOURNAL_DIR"; then
        APPLY_ACTIVE=0
        rm -rf "$JOURNAL_DIR" || true
    else
        echo "ERROR: automatic rollback incomplete; preserve $JOURNAL_DIR for next-run/manual recovery" >&2
    fi
    exit 1
}
trap 'interrupt_restore HUP' HUP
trap 'interrupt_restore INT' INT
trap 'interrupt_restore TERM' TERM

for destination in jffs opt; do
    if [ -d "$ROOT/$destination" ]; then
        if ! cp -Rp "$ROOT/$destination/." "/$destination/"; then
            trap - HUP INT TERM
            echo "ERROR: restore failed; rolling back pre-restore state" >&2
            if rollback_from_journal "$JOURNAL_DIR"; then
                APPLY_ACTIVE=0
                rm -rf "$JOURNAL_DIR" || true
            else
                echo "ERROR: rollback incomplete; journal preserved at $JOURNAL_DIR" >&2
            fi
            exit 1
        fi
    fi
done

if ! state_write COMMITTED; then
    trap - HUP INT TERM
    echo "ERROR: restore payload applied but COMMITTED state could not be persisted; journal preserved for safe recovery" >&2
    exit 1
fi
APPLY_ACTIVE=0
trap - HUP INT TERM
rm -rf "$JOURNAL_DIR" || {
    echo "WARNING: committed restore succeeded but journal cleanup failed: $JOURNAL_DIR" >&2
}
echo "Restore completed. Reboot or restart services after reviewing files."
