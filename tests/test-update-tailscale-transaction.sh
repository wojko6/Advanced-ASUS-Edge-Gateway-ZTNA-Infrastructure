#!/bin/sh

set -u

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
SOURCE_SCRIPT="$REPO_DIR/scripts/update-tailscale.sh"

TMP_DIR="$(mktemp -d)" || exit 1
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

prepare_runner() {
    case_dir="$1"
    mock_bin="$case_dir/bin"
    runner="$case_dir/update-tailscale.sh"

    mkdir -p "$mock_bin" || return 1
    cp "$SOURCE_SCRIPT" "$runner" || return 1

    sed \
        -e 's#^PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"$#PATH="$MOCK_BIN:/usr/bin:/bin"#' \
        -e 's#for executable_dir in /opt/sbin /opt/bin /usr/sbin /usr/bin /sbin /bin; do#for executable_dir in "$MOCK_BIN" /opt/sbin /opt/bin /usr/sbin /usr/bin /sbin /bin; do#g' \
        -e 's#^uid="$(current_uid)".*$#uid=0#' \
        -e 's#^SERVICES_START=/jffs/addons/asus-edge/bin/services-start$#SERVICES_START="$MOCK_SERVICES_START"#' \
        -e 's#^HEALTHCHECK=/jffs/addons/asus-edge/bin/healthcheck.sh$#HEALTHCHECK="$MOCK_HEALTHCHECK"#' \
        "$runner" >"$runner.tmp" || return 1

    mv "$runner.tmp" "$runner" || return 1
    chmod +x "$runner" || return 1

    cat >"$mock_bin/opkg" <<'MOCK'
#!/bin/sh

case "${1:-}" in
    update)
        exit "${OPKG_UPDATE_RC:-0}"
        ;;

    status)
        [ "${2:-}" = "tailscale" ] || exit 1
        cat <<STATUS
Package: tailscale
Version: $INSTALLED_VERSION
Status: install user installed
Architecture: armv7-3.2
STATUS
        ;;

    list)
        [ "${2:-}" = "tailscale" ] || exit 1
        echo "tailscale - $CANDIDATE_VERSION - mocked package"
        ;;

    list-upgradable)
        if [ "${UPGRADABLE:-1}" = "1" ]; then
            echo "tailscale - $INSTALLED_VERSION - $CANDIDATE_VERSION"
        fi
        ;;

    upgrade)
        [ "${2:-}" = "tailscale" ] || exit 1

        echo "upgrade" >"$UPGRADE_MARKER"

        if [ "${OPKG_UPGRADE_RC:-0}" -ne 0 ]; then
            exit "$OPKG_UPGRADE_RC"
        fi

        new_live="${CANDIDATE_VERSION%%-*}"
        printf '%s\n' "$new_live" >"$LIVE_STATE"
        exit 0
        ;;

    *)
        echo "mock opkg: unsupported arguments: $*" >&2
        exit 1
        ;;
esac
MOCK

    cat >"$mock_bin/tailscale" <<'MOCK'
#!/bin/sh

case "${1:-}" in
    version)
        cat "$LIVE_STATE"
        ;;
    *)
        exit 1
        ;;
esac
MOCK

    cat >"$mock_bin/tailscaled" <<'MOCK'
#!/bin/sh

case "${1:-}" in
    --version)
        cat "$LIVE_STATE"
        ;;
    *)
        exit 1
        ;;
esac
MOCK

    cat >"$mock_bin/sha256sum" <<'MOCK'
#!/bin/sh

case "${1:-}" in
    /proc/*/exe)
        set -- "$MOCK_BIN/tailscaled"
        ;;
esac

exec /usr/bin/sha256sum "$@"
MOCK

    cat >"$mock_bin/pidof" <<'MOCK'
#!/bin/sh

if [ "${1:-}" = "tailscaled" ]; then
    echo 4242
    exit 0
fi

exit 1
MOCK

    cat >"$mock_bin/readlink" <<'MOCK'
#!/bin/sh

if [ "${1:-}" = "-f" ]; then
    shift
fi

case "${1:-}" in
    /proc/*/exe)
        printf '%s\n' "$MOCK_BIN/tailscaled"
        ;;
    *)
        printf '%s\n' "${1:-}"
        ;;
esac
MOCK

    cat >"$case_dir/services-start" <<'MOCK'
#!/bin/sh
exit "${SERVICE_RC:-0}"
MOCK

    cat >"$case_dir/healthcheck.sh" <<'MOCK'
#!/bin/sh
exit "${HEALTH_RC:-0}"
MOCK

    chmod +x \
        "$mock_bin/opkg" \
        "$mock_bin/tailscale" \
        "$mock_bin/tailscaled" \
        "$mock_bin/sha256sum" \
        "$mock_bin/pidof" \
        "$mock_bin/readlink" \
        "$case_dir/services-start" \
        "$case_dir/healthcheck.sh"
}

run_case() {
    name="$1"
    installed="$2"
    candidate="$3"
    live="$4"
    expected_rc="$5"
    expected_upgrade="$6"
    service_rc="$7"
    health_rc="$8"

    case_dir="$TMP_DIR/$name"
    mkdir -p "$case_dir" || fail "$name: cannot create fixture"

    prepare_runner "$case_dir" || fail "$name: cannot prepare runner"

    live_state="$case_dir/live-version"
    upgrade_marker="$case_dir/upgraded"
    output="$case_dir/output.txt"

    printf '%s\n' "$live" >"$live_state"

    MOCK_BIN="$case_dir/bin" \
    MOCK_SERVICES_START="$case_dir/services-start" \
    MOCK_HEALTHCHECK="$case_dir/healthcheck.sh" \
    INSTALLED_VERSION="$installed" \
    CANDIDATE_VERSION="$candidate" \
    LIVE_STATE="$live_state" \
    UPGRADE_MARKER="$upgrade_marker" \
    UPGRADABLE=1 \
    OPKG_UPDATE_RC=0 \
    OPKG_UPGRADE_RC=0 \
    SERVICE_RC="$service_rc" \
    HEALTH_RC="$health_rc" \
    EDGE_TS_UPDATE_ROLLBACK_ROOT="$case_dir/rollback" \
        "$case_dir/update-tailscale.sh" >"$output" 2>&1

    rc=$?

    [ "$rc" -eq "$expected_rc" ] || {
        cat "$output" >&2
        fail "$name: expected rc=$expected_rc actual=$rc"
    }

    case "$expected_upgrade" in
        yes)
            [ -f "$upgrade_marker" ] || {
                cat "$output" >&2
                fail "$name: expected package mutation did not occur"
            }

            find "$case_dir/rollback" -name manifest.txt -type f \
                | grep . >/dev/null || {
                    cat "$output" >&2
                    fail "$name: verified rollback snapshot missing"
                }
            ;;

        no)
            [ ! -e "$upgrade_marker" ] || {
                cat "$output" >&2
                fail "$name: unexpected package mutation occurred"
            }
            ;;

        *)
            fail "$name: invalid test expectation"
            ;;
    esac

    echo "PASS: $name"
}

run_case \
    newer-allowed \
    "1.96.1-1" \
    "1.104.0-1" \
    "1.102.3" \
    0 yes 0 0

run_case \
    equal-no-mutation \
    "1.96.1-1" \
    "1.102.3-1" \
    "1.102.3" \
    0 no 0 0

run_case \
    older-rejected \
    "1.96.1-1" \
    "1.98.0-1" \
    "1.102.3" \
    2 no 0 0

grep -F \
    'ERROR: refusing implicit Tailscale downgrade' \
    "$TMP_DIR/older-rejected/output.txt" >/dev/null || {
        fail "older-rejected: downgrade refusal was not explicit"
    }

run_case \
    malformed-fail-closed \
    "1.96.1-1" \
    "unknown" \
    "1.102.3" \
    1 no 0 0

run_case \
    service-recovery-failure \
    "1.96.1-1" \
    "1.104.0-1" \
    "1.102.3" \
    1 yes 1 0

grep -F \
    'ERROR: post-update service recovery failed' \
    "$TMP_DIR/service-recovery-failure/output.txt" >/dev/null || {
        fail "service-recovery-failure: expected error missing"
    }

run_case \
    healthcheck-failure \
    "1.96.1-1" \
    "1.104.0-1" \
    "1.102.3" \
    1 yes 0 1

grep -F \
    'ERROR: post-update health check failed' \
    "$TMP_DIR/healthcheck-failure/output.txt" >/dev/null || {
        fail "healthcheck-failure: expected error missing"
    }

echo
echo "PASS: all Tailscale update/version-drift transaction scenarios"
