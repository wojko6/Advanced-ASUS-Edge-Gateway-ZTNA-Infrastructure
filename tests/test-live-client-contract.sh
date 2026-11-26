#!/bin/sh

# Deterministic, offline #289 regressions. Fake dig/nc prevent real network use.
set -eu
TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
CLIENT="$TEST_DIR/test-live-client.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
mkdir -p "$TMP/no-nc" "$TMP/with-nc"

cat > "$TMP/no-nc/dig" <<'MOCK'
#!/bin/sh
exit "${MOCK_DIG_RC:-0}"
MOCK
cat > "$TMP/with-nc/nc" <<'MOCK'
#!/bin/sh
case "$*" in
    *' 8443') exit "${MOCK_HTTPS_RC:-0}" ;;
    *' 22')   exit "${MOCK_SSH_RC:-1}" ;;
    *' 445')  exit "${MOCK_SMB_RC:-1}" ;;
    *) exit 99 ;;
esac
MOCK
cp "$TMP/no-nc/dig" "$TMP/with-nc/dig"
chmod 755 "$TMP/no-nc/dig" "$TMP/with-nc/dig" "$TMP/with-nc/nc"

run_case() {
    name="$1"; bin="$2"; expected="$3"
    shift 3
    rc=0
    env PATH="$bin" \
        MOCK_DIG_RC="${MOCK_DIG_RC:-0}" \
        MOCK_HTTPS_RC="${MOCK_HTTPS_RC:-0}" \
        MOCK_SSH_RC="${MOCK_SSH_RC:-1}" \
        MOCK_SMB_RC="${MOCK_SMB_RC:-1}" \
        /bin/sh "$CLIENT" "$@" > "$TMP/result" 2>&1 || rc=$?
    if [ "$rc" -ne "$expected" ]; then
        printf 'FAIL: %s: expected RC=%s, got %s\n' "$name" "$expected" "$rc" >&2
        cat "$TMP/result" >&2
        exit 1
    fi
    printf 'PASS: %s (RC=%s)\n' "$name" "$rc"
}

run_case missing_nc "$TMP/no-nc" 3 203.0.113.1
[ "$(grep -c '^SKIP:' "$TMP/result")" -eq 2 ]
grep -F 'Summary: 0 failure(s), 2 skipped check(s)' "$TMP/result" >/dev/null
! grep -q 'PASS: router SSH denied' "$TMP/result"

run_case missing_nc_with_smb "$TMP/no-nc" 3 203.0.113.1 203.0.113.2
[ "$(grep -c '^SKIP:' "$TMP/result")" -eq 3 ]

MOCK_DIG_RC=1 run_case dns_failure_and_missing_nc "$TMP/no-nc" 1 203.0.113.1
grep -F 'FAIL: classic DNS query failed' "$TMP/result" >/dev/null

run_case all_probes_pass "$TMP/with-nc" 0 203.0.113.1 203.0.113.2
[ "$(grep -c '^PASS:' "$TMP/result")" -eq 4 ]
! grep -q '^SKIP:' "$TMP/result"

run_case optional_smb_omitted "$TMP/with-nc" 0 203.0.113.1
! grep -q 'SMB' "$TMP/result"

MOCK_HTTPS_RC=1 run_case https_unreachable "$TMP/with-nc" 1 203.0.113.1
MOCK_SSH_RC=0 run_case ssh_unexpectedly_open "$TMP/with-nc" 1 203.0.113.1
MOCK_SMB_RC=0 run_case smb_unexpectedly_open "$TMP/with-nc" 1 203.0.113.1 203.0.113.2
MOCK_DIG_RC=1 run_case dns_unavailable "$TMP/with-nc" 1 203.0.113.1
run_case missing_required_argument "$TMP/no-nc" 2

echo 'ISSUE289_OFFLINE_CONTRACT_TESTS=PASS_10_OF_10'
