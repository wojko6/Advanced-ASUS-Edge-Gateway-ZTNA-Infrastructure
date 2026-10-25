#!/bin/sh
# Issue #289: exercise source-extracted healthcheck warning branches offline.
# No router, DNS, firewall, or real resolver is contacted.
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
SOURCE="$REPO_DIR/scripts/healthcheck.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
MOCK_BIN="$TMP/bin"
mkdir -p "$MOCK_BIN"

awk '
    /^# BEGIN DNS Guard health helpers/ { capture=1; next }
    /^# END DNS Guard health helpers/ { capture=0 }
    capture { print }
' "$SOURCE" > "$TMP/helpers.sh"

awk '
    /^ok\(\) \{/ || /^warn\(\) \{/ || /^fail\(\) \{/ { print }
' "$SOURCE" > "$TMP/verdict-functions.sh"

awk '
    /^dns_guard_mode="\$\(dns_guard_resolver_mode 2>\/dev\/null\)" \|\| true$/ { capture=1 }
    /^if \[ "\$EDGE_REQUIRE_WAN_WEBUI_DISABLED" = "1" \]; then$/ { capture=0 }
    capture { print }
' "$SOURCE" > "$TMP/dns-mode-block.sh"

awk '
    /^if executable_exists dig >\/dev\/null 2>&1; then$/ { capture=1 }
    capture { print; if (/^else warn "dig not installed; DNSSEC test skipped"; fi$/) exit }
' "$SOURCE" > "$TMP/dig-block.sh"

tail -n 2 "$SOURCE" > "$TMP/exit-block.sh"

for expected in \
    'dns_guard_resolver_mode()' \
    'warn()' \
    'DNS Guard resolver mode: bootstrap/fail-open' \
    'dig not installed; DNSSEC test skipped' \
    'Summary: %s failure(s), %s warning(s)'
do
    grep -F "$expected" "$TMP"/*.sh >/dev/null || {
        echo "FAIL: missing source-extracted healthcheck contract: $expected" >&2
        exit 1
    }
done

grep -F 'dns_guard_mode="$(dns_guard_resolver_mode 2>/dev/null)" || true' \
    "$TMP/dns-mode-block.sh" >/dev/null
grep -F 'dig +time=3 +tries=1 +dnssec' "$TMP/dig-block.sh" >/dev/null
grep -F '[ "$FAILURES" -eq 0 ]' "$TMP/exit-block.sh" >/dev/null

cat > "$MOCK_BIN/dig" <<'MOCK'
#!/bin/sh
[ "${MOCK_DIG_RC:-0}" -eq 0 ] || exit 1
printf '%s\n' ';; flags: qr rd ra ad; QUERY: 1, ANSWER: 1'
MOCK
chmod +x "$MOCK_BIN/dig"

DNS_GUARD_RESOLV_CONF="$TMP/resolv.conf"
DNS_GUARD_BREAKGLASS_FLAG="$TMP/breakglass"
EDGE_DNS_LOCAL_RESOLVER_IP="192.0.2.53"
EDGE_UNBOUND_PORT=53535
export DNS_GUARD_RESOLV_CONF DNS_GUARD_BREAKGLASS_FLAG EDGE_DNS_LOCAL_RESOLVER_IP EDGE_UNBOUND_PORT

run_case() {
    name="$1"
    resolver="$2"
    dig_present="$3"
    dig_rc="$4"
    expected_rc="$5"
    expected_warnings="$6"
    expected_failures="$7"
    printf '%s\n' "$resolver" > "$DNS_GUARD_RESOLV_CONF"
    rc=0
    (
        # Both counters are consumed by source-extracted healthcheck functions.
        # shellcheck disable=SC2034
        FAILURES=0
        # shellcheck disable=SC2034
        WARNINGS=0
        MOCK_DIG_PRESENT="$dig_present"
        MOCK_DIG_RC="$dig_rc"
        export MOCK_DIG_PRESENT MOCK_DIG_RC
        PATH="$MOCK_BIN:/usr/bin:/bin"
        export PATH
        . "$TMP/helpers.sh"
        . "$TMP/verdict-functions.sh"
        executable_exists() {
            [ "$1" = dig ] && [ "$MOCK_DIG_PRESENT" = 1 ]
        }
        . "$TMP/dns-mode-block.sh"
        . "$TMP/dig-block.sh"
        . "$TMP/exit-block.sh"
    ) > "$TMP/output" 2>&1 || rc=$?
    if [ "$rc" -ne "$expected_rc" ] ||
        ! grep -F "Summary: $expected_failures failure(s), $expected_warnings warning(s)" "$TMP/output" >/dev/null; then
        echo "FAIL: $name (RC=$rc; expected $expected_rc)" >&2
        cat "$TMP/output" >&2
        exit 1
    fi
    printf 'PASS: %s (RC=%s, FAIL=%s, WARN=%s)\n' \
        "$name" "$rc" "$expected_failures" "$expected_warnings"
}

run_case local_missing_dig 'nameserver 192.0.2.53' 0 0 0 1 0
run_case bootstrap_missing_dig 'nameserver 9.9.9.9' 0 0 0 2 0
run_case local_unrunnable_dig 'nameserver 192.0.2.53' 1 1 0 1 0
run_case bootstrap_ad_success 'nameserver 9.9.9.9' 1 0 0 1 0
run_case local_all_healthy 'nameserver 192.0.2.53' 1 0 0 0 0
run_case mixed_resolver_failure 'nameserver 192.0.2.53
nameserver 9.9.9.9' 0 0 1 1 1
run_case empty_resolver_failure '' 1 0 1 0 1

echo 'ISSUE289_HEALTHCHECK_WARNING_CONTRACT=PASS_7_OF_7'
