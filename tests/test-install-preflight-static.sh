#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
INSTALLER="$REPO_DIR/scripts/install.sh"

[ -r "$INSTALLER" ] || { echo "FAIL: missing installer" >&2; exit 1; }

# Every shell/config source copied by install_file must be covered by the
# installer's syntax-preflight loop before any backup/staging mutation begins.
install_sources="$(sed -n 's/^install_file "\$REPO_DIR\/\([^\"]*\)".*/\1/p' "$INSTALLER")"
[ -n "$install_sources" ] || { echo "FAIL: no installer sources discovered" >&2; exit 1; }

preflight_end="$(grep -n '^umask 077$' "$INSTALLER" | cut -d: -f1)"
[ -n "$preflight_end" ] || { echo "FAIL: cannot locate end of installer preflight" >&2; exit 1; }

for source in $install_sources; do
    case "$source" in
        *.sh|config/edge.conf)
            if ! sed -n "1,${preflight_end}p" "$INSTALLER" | grep -F "\$REPO_DIR/$source" >/dev/null; then
                echo "FAIL: installed shell/config source is not syntax-prevalidated: $source" >&2
                exit 1
            fi
            ;;
    esac
done

# The preflight itself must fail the install on syntax errors.
grep -F 'sh -n "$file" || exit 1' "$INSTALLER" >/dev/null || {
    echo "FAIL: installer syntax preflight is not fail-closed" >&2
    exit 1
}

echo "PASS: installer syntax preflight covers every installed shell/config source"
