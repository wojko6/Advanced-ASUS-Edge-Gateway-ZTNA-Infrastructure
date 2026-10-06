#!/bin/sh

set -u

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
SCRIPT="$REPO_DIR/scripts/update-tailscale.sh"

TMP_DIR="$(mktemp -d)" || exit 1
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

FUNCS="$TMP_DIR/version-functions.sh"

awk '
    /^version_core\(\)/ {
        capture=1
    }

    /^opkg_installed_version\(\)/ {
        capture=0
    }

    capture {
        print
    }
' "$SCRIPT" >"$FUNCS"

grep -F 'version_compare()' "$FUNCS" >/dev/null || {
    echo "FAIL: version_compare could not be extracted" >&2
    exit 1
}

# shellcheck disable=SC1090
. "$FUNCS"

check_compare() {
    expected="$1"
    left="$2"
    right="$3"

    actual="$(version_compare "$left" "$right")"
    rc=$?

    [ "$rc" -eq 0 ] || {
        echo "FAIL: comparison rejected valid versions: $left / $right" >&2
        exit 1
    }

    [ "$actual" = "$expected" ] || {
        echo "FAIL: $left vs $right expected=$expected actual=$actual" >&2
        exit 1
    }
}

check_invalid() {
    value="$1"

    version_compare "$value" "1.102.3" >/dev/null 2>&1
    rc=$?

    [ "$rc" -ne 0 ] || {
        echo "FAIL: malformed version accepted: $value" >&2
        exit 1
    }
}

check_compare 1  "1.104.0-1" "1.102.3"
check_compare 0  "1.102.3-1" "1.102.3"
check_compare -1 "1.96.1-1"  "1.102.3"
check_compare 1  "1.103.309" "1.102.5"
check_compare 0  "v1.102.3"  "1.102.3"

check_invalid "unknown"
check_invalid "1.102"
check_invalid "1.102.x"
check_invalid ""

echo "PASS: Tailscale version comparison is deterministic and fails closed"
