#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
NOTE="$ROOT_DIR/evidence/INTEGRITY-NOTE-2026-09-22.md"

[ -f "$NOTE" ] || { echo 'FAIL: evidence integrity note missing' >&2; exit 1; }

legacy_bundle() {
    case "$1" in
        2026-09-03|2026-09-04|2026-09-05|2026-09-08|2026-09-09) return 0 ;;
        *) return 1 ;;
    esac
}

find "$ROOT_DIR/evidence" -mindepth 2 -maxdepth 2 -type f -name SHA256SUMS | sort | while IFS= read -r manifest; do
    bundle_dir="$(dirname "$manifest")"
    bundle_name="$(basename "$bundle_dir")"

    if legacy_bundle "$bundle_name"; then
        tmp_manifest="${TMPDIR:-/tmp}/asus-edge-sha-$$-$bundle_name"
        awk '$NF != "README.md" && $NF != "./README.md" { print }' "$manifest" >"$tmp_manifest"
        (cd "$bundle_dir" && sha256sum -c "$tmp_manifest" >/dev/null) || {
            rm -f "$tmp_manifest"
            echo "FAIL: non-README evidence checksum mismatch in legacy bundle $bundle_name" >&2
            exit 1
        }
        rm -f "$tmp_manifest"
        grep -F "$bundle_name" "$NOTE" >/dev/null || {
            echo "FAIL: legacy checksum exception is undocumented: $bundle_name" >&2
            exit 1
        }
    else
        (cd "$bundle_dir" && sha256sum -c SHA256SUMS >/dev/null) || {
            echo "FAIL: evidence manifest verification failed: $bundle_name" >&2
            exit 1
        }
    fi
done

echo 'PASS: evidence manifests verified with only documented historical README exceptions'
