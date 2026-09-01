#!/bin/sh

set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"

find "$REPO_DIR/router" "$REPO_DIR/scripts" "$REPO_DIR/tests" -type f -name '*.sh' -o -path '*/router/scripts/*' | while IFS= read -r file; do
    sh -n "$file"
done

if command -v shellcheck >/dev/null 2>&1; then
    find "$REPO_DIR/router" "$REPO_DIR/scripts" "$REPO_DIR/tests" -type f \( -name '*.sh' -o -path '*/router/scripts/*' \) -print0 \
        | xargs -0 shellcheck -S warning
else
    echo "WARN: shellcheck not installed"
fi

if grep -F 'opkg update && opkg upgrade tailscale' "$REPO_DIR/router/scripts/services-start" >/dev/null; then
    echo "FAIL: package upgrade present in boot path" >&2
    exit 1
fi

if grep -E 'iptables .*-(I|A) (INPUT|FORWARD) -i tailscale\+? -j ACCEPT' "$REPO_DIR/router/scripts/firewall-start" >/dev/null; then
    echo "FAIL: broad Tailscale ACCEPT rule found" >&2
    exit 1
fi

"$TEST_DIR/test-firewall-mock.sh"
echo "PASS: static test suite"
