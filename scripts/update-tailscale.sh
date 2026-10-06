#!/bin/sh

set -u

PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"

executable_exists() {
    executable_name="$1"
    case "$executable_name" in
        */*)
            [ -x "$executable_name" ]
            return
            ;;
    esac

    for executable_dir in /opt/sbin /opt/bin /usr/sbin /usr/bin /sbin /bin; do
        [ -x "$executable_dir/$executable_name" ] && return 0
    done
    return 1
}

current_uid() {
    while read -r status_key status_uid _; do
        if [ "$status_key" = "Uid:" ]; then
            printf '%s\n' "$status_uid"
            return 0
        fi
    done </proc/self/status
    return 1
}

version_core() {
    raw_version="$1"

    case "$raw_version" in
        v*) raw_version="${raw_version#v}" ;;
    esac

    core_version="${raw_version%%-*}"

    case "$core_version" in
        ''|*[!0-9.]*|.*|*.|*..*)
            return 1
            ;;
    esac

    old_ifs="$IFS"
    IFS=.
    set -- $core_version
    IFS="$old_ifs"

    [ "$#" -eq 3 ] || return 1

    for version_part in "$@"; do
        case "$version_part" in
            ''|*[!0-9]*)
                return 1
                ;;
        esac
    done

    printf '%s\n' "$core_version"
}

version_compare() {
    version_a="$(version_core "$1")" || return 2
    version_b="$(version_core "$2")" || return 2

    awk -v a="$version_a" -v b="$version_b" '
        BEGIN {
            split(a, av, ".")
            split(b, bv, ".")

            for (i = 1; i <= 3; i++) {
                ai = av[i] + 0
                bi = bv[i] + 0

                if (ai < bi) {
                    print -1
                    exit
                }

                if (ai > bi) {
                    print 1
                    exit
                }
            }

            print 0
        }
    '
}

opkg_installed_version() {
    opkg status tailscale 2>/dev/null |
        awk '
            $1 == "Version:" {
                value=$2
                count++
            }
            END {
                if (count == 1) {
                    print value
                    exit 0
                }
                exit 1
            }
        '
}

opkg_candidate_version() {
    opkg list tailscale 2>/dev/null |
        awk '
            $1 == "tailscale" && $2 == "-" {
                value=$3
                count++
            }
            END {
                if (count == 1) {
                    print value
                    exit 0
                }
                exit 1
            }
        '
}

executable_path() {
    executable_name="$1"

    case "$executable_name" in
        */*)
            [ -x "$executable_name" ] || return 1
            readlink -f "$executable_name"
            return
            ;;
    esac

    for executable_dir in /opt/sbin /opt/bin /usr/sbin /usr/bin /sbin /bin; do
        if [ -x "$executable_dir/$executable_name" ]; then
            readlink -f "$executable_dir/$executable_name"
            return
        fi
    done

    return 1
}

file_sha256() {
    target_file="$1"
    sha256sum "$target_file" 2>/dev/null | awk 'NR == 1 { print $1 }'
}

create_rollback_snapshot() {
    installed_version="$1"
    candidate_version="$2"
    live_version="$3"
    cli_path="$4"
    daemon_path="$5"
    cli_sha="$6"
    daemon_sha="$7"

    rollback_root="${EDGE_TS_UPDATE_ROLLBACK_ROOT:-/opt/var/backups/asus-edge/tailscale-update}"
    rollback_stamp="$(date '+%Y%m%d-%H%M%S')" || return 1
    rollback_dir="$rollback_root/${rollback_stamp}-$$"

    old_umask="$(umask)"
    umask 077

    mkdir -p "$rollback_root" || {
        umask "$old_umask"
        return 1
    }

    mkdir "$rollback_dir" || {
        umask "$old_umask"
        return 1
    }

    cp -p "$cli_path" "$rollback_dir/tailscale" || {
        umask "$old_umask"
        return 1
    }

    cp -p "$daemon_path" "$rollback_dir/tailscaled" || {
        umask "$old_umask"
        return 1
    }

    {
        printf 'installed_package_version=%s\n' "$installed_version"
        printf 'candidate_package_version=%s\n' "$candidate_version"
        printf 'live_version=%s\n' "$live_version"
        printf 'tailscale_path=%s\n' "$cli_path"
        printf 'tailscale_sha256=%s\n' "$cli_sha"
        printf 'tailscaled_path=%s\n' "$daemon_path"
        printf 'tailscaled_sha256=%s\n' "$daemon_sha"
    } >"$rollback_dir/manifest.txt" || {
        umask "$old_umask"
        return 1
    }

    snapshot_cli_sha="$(file_sha256 "$rollback_dir/tailscale")" || snapshot_cli_sha=""
    snapshot_daemon_sha="$(file_sha256 "$rollback_dir/tailscaled")" || snapshot_daemon_sha=""

    if [ "$snapshot_cli_sha" != "$cli_sha" ] || [ "$snapshot_daemon_sha" != "$daemon_sha" ]; then
        echo "ERROR: rollback snapshot hash verification failed" >&2
        umask "$old_umask"
        return 1
    fi

    umask "$old_umask"

    ROLLBACK_SNAPSHOT_DIR="$rollback_dir"
    export ROLLBACK_SNAPSHOT_DIR

    echo "Rollback snapshot: $ROLLBACK_SNAPSHOT_DIR"
}

uid="$(current_uid)" || { echo "ERROR: cannot determine current user" >&2; exit 1; }
[ "$uid" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }
executable_exists opkg >/dev/null 2>&1 || { echo "ERROR: Entware not available" >&2; exit 1; }

SERVICES_START=/jffs/addons/asus-edge/bin/services-start
HEALTHCHECK=/jffs/addons/asus-edge/bin/healthcheck.sh
[ -x "$SERVICES_START" ] || {
    echo "ERROR: managed services-start hook missing or not executable: $SERVICES_START" >&2
    exit 1
}
[ -x "$HEALTHCHECK" ] || {
    echo "ERROR: managed healthcheck missing or not executable: $HEALTHCHECK" >&2
    exit 1
}

executable_exists readlink >/dev/null 2>&1 || {
    echo "ERROR: readlink unavailable" >&2
    exit 1
}
executable_exists sha256sum >/dev/null 2>&1 || {
    echo "ERROR: sha256sum unavailable" >&2
    exit 1
}

LIVE_CLI_PATH="$(executable_path tailscale)" || {
    echo "ERROR: cannot resolve live tailscale CLI path" >&2
    exit 1
}

LIVE_DAEMON_PATH="$(executable_path tailscaled)" || {
    echo "ERROR: cannot resolve live tailscaled path" >&2
    exit 1
}

LIVE_CLI_SHA256="$(file_sha256 "$LIVE_CLI_PATH")"
LIVE_DAEMON_SHA256="$(file_sha256 "$LIVE_DAEMON_PATH")"

[ -n "$LIVE_CLI_SHA256" ] || {
    echo "ERROR: cannot hash live tailscale CLI" >&2
    exit 1
}

[ -n "$LIVE_DAEMON_SHA256" ] || {
    echo "ERROR: cannot hash live tailscaled binary" >&2
    exit 1
}

LIVE_CLI_VERSION="$(tailscale version 2>/dev/null | head -n 1)"
LIVE_DAEMON_VERSION="$(tailscaled --version 2>/dev/null | head -n 1)"

[ -n "$LIVE_CLI_VERSION" ] || {
    echo "ERROR: cannot determine live tailscale CLI version" >&2
    exit 1
}

[ -n "$LIVE_DAEMON_VERSION" ] || {
    echo "ERROR: cannot determine live tailscaled version" >&2
    exit 1
}

LIVE_VERSION_RELATION="$(version_compare "$LIVE_CLI_VERSION" "$LIVE_DAEMON_VERSION")" || {
    echo "ERROR: malformed or unsupported live Tailscale version" >&2
    exit 1
}

[ "$LIVE_VERSION_RELATION" = "0" ] || {
    echo "ERROR: tailscale/tailscaled live version mismatch: CLI=$LIVE_CLI_VERSION daemon=$LIVE_DAEMON_VERSION" >&2
    exit 1
}

echo "Live tailscale CLI: $LIVE_CLI_VERSION"
echo "Live tailscaled:     $LIVE_DAEMON_VERSION"
echo "CLI path:            $LIVE_CLI_PATH"
echo "CLI SHA-256:         $LIVE_CLI_SHA256"
echo "Daemon path:         $LIVE_DAEMON_PATH"
echo "Daemon SHA-256:      $LIVE_DAEMON_SHA256"

LIVE_DAEMON_PID="$(pidof tailscaled 2>/dev/null | awk '{ print $1 }')"

if [ -n "$LIVE_DAEMON_PID" ]; then
    RUNNING_DAEMON_PATH="$(readlink -f "/proc/$LIVE_DAEMON_PID/exe" 2>/dev/null)"

    if [ -n "$RUNNING_DAEMON_PATH" ]; then
        echo "Running daemon path: $RUNNING_DAEMON_PATH"

        [ "$RUNNING_DAEMON_PATH" = "$LIVE_DAEMON_PATH" ] || {
            echo "ERROR: running tailscaled path differs from resolved binary path" >&2
            exit 1
        }

        RUNNING_DAEMON_SHA256="$(file_sha256 "/proc/$LIVE_DAEMON_PID/exe")"

        [ -n "$RUNNING_DAEMON_SHA256" ] || {
            echo "ERROR: cannot hash running tailscaled process image" >&2
            exit 1
        }

        [ "$RUNNING_DAEMON_SHA256" = "$LIVE_DAEMON_SHA256" ] || {
            echo "ERROR: running tailscaled process image differs from resolved binary" >&2
            exit 1
        }

        echo "Running daemon SHA-256: $RUNNING_DAEMON_SHA256"
    fi
else
    echo "WARNING: tailscaled is not currently running; binary provenance only."
fi

echo "This is an explicit maintenance action; no package upgrades run at boot."

opkg update || exit 1

INSTALLED_PACKAGE_VERSION="$(opkg_installed_version)" || {
    echo "ERROR: cannot determine installed Entware Tailscale package version" >&2
    exit 1
}

CANDIDATE_PACKAGE_VERSION="$(opkg_candidate_version)" || {
    echo "ERROR: cannot determine a unique Entware Tailscale candidate version" >&2
    exit 1
}

echo "Entware installed:   $INSTALLED_PACKAGE_VERSION"
echo "Entware candidate:   $CANDIDATE_PACKAGE_VERSION"
echo "Live binary:         $LIVE_CLI_VERSION"

CANDIDATE_RELATION="$(version_compare "$CANDIDATE_PACKAGE_VERSION" "$LIVE_CLI_VERSION")" || {
    echo "ERROR: malformed or unsupported package/live Tailscale version" >&2
    exit 1
}

case "$CANDIDATE_RELATION" in
    -1)
        echo "ERROR: refusing implicit Tailscale downgrade" >&2
        echo "ERROR: Entware candidate $CANDIDATE_PACKAGE_VERSION is older than live binary $LIVE_CLI_VERSION" >&2
        exit 2
        ;;
    0)
        if [ "$INSTALLED_PACKAGE_VERSION" != "$CANDIDATE_PACKAGE_VERSION" ]; then
            echo "WARNING: package metadata differs from the live/candidate version."
        fi
        echo "No Tailscale package mutation required: candidate matches live version."
        exit 0
        ;;
    1)
        echo "Candidate is newer than the live binary; package transaction may proceed."
        ;;
    *)
        echo "ERROR: unexpected Tailscale version comparison result: $CANDIDATE_RELATION" >&2
        exit 1
        ;;
esac

create_rollback_snapshot     "$INSTALLED_PACKAGE_VERSION"     "$CANDIDATE_PACKAGE_VERSION"     "$LIVE_CLI_VERSION"     "$LIVE_CLI_PATH"     "$LIVE_DAEMON_PATH"     "$LIVE_CLI_SHA256"     "$LIVE_DAEMON_SHA256" || {
        echo "ERROR: failed to preserve verified Tailscale rollback snapshot" >&2
        exit 1
    }

UPGRADABLE="$(opkg list-upgradable)" || {
    echo "ERROR: failed to query upgradable packages" >&2
    exit 1
}

printf '%s\n' "$UPGRADABLE" | grep '^tailscale ' >/dev/null || {
    echo "ERROR: candidate is newer than live, but opkg does not advertise a Tailscale upgrade" >&2
    exit 1
}

opkg upgrade tailscale || exit 1

EDGE_FORCE_TAILSCALE_RESTART=1 "$SERVICES_START" || {
    echo "ERROR: post-update service recovery failed" >&2
    echo "Rollback material preserved at: ${ROLLBACK_SNAPSHOT_DIR:-unknown}" >&2
    exit 1
}

NEW_CLI_VERSION="$(tailscale version 2>/dev/null | head -n 1)"
NEW_DAEMON_VERSION="$(tailscaled --version 2>/dev/null | head -n 1)"

[ -n "$NEW_CLI_VERSION" ] && [ -n "$NEW_DAEMON_VERSION" ] || {
    echo "ERROR: cannot determine post-update Tailscale versions" >&2
    exit 1
}

NEW_LIVE_RELATION="$(version_compare "$NEW_CLI_VERSION" "$NEW_DAEMON_VERSION")" || {
    echo "ERROR: malformed post-update Tailscale version" >&2
    exit 1
}

[ "$NEW_LIVE_RELATION" = "0" ] || {
    echo "ERROR: post-update CLI/daemon version mismatch: CLI=$NEW_CLI_VERSION daemon=$NEW_DAEMON_VERSION" >&2
    exit 1
}

NEW_CANDIDATE_RELATION="$(version_compare "$NEW_CLI_VERSION" "$CANDIDATE_PACKAGE_VERSION")" || {
    echo "ERROR: cannot compare post-update version with package candidate" >&2
    exit 1
}

[ "$NEW_CANDIDATE_RELATION" = "0" ] || {
    echo "ERROR: post-update live version $NEW_CLI_VERSION does not match candidate $CANDIDATE_PACKAGE_VERSION" >&2
    exit 1
}

NEW_CLI_PATH="$(executable_path tailscale)" || {
    echo "ERROR: cannot resolve post-update tailscale path" >&2
    exit 1
}

NEW_DAEMON_PATH="$(executable_path tailscaled)" || {
    echo "ERROR: cannot resolve post-update tailscaled path" >&2
    exit 1
}

NEW_CLI_SHA256="$(file_sha256 "$NEW_CLI_PATH")"
NEW_DAEMON_SHA256="$(file_sha256 "$NEW_DAEMON_PATH")"

[ -n "$NEW_CLI_SHA256" ] && [ -n "$NEW_DAEMON_SHA256" ] || {
    echo "ERROR: cannot hash post-update Tailscale binaries" >&2
    exit 1
}

NEW_DAEMON_PID="$(pidof tailscaled 2>/dev/null | awk '{ print $1 }')"

[ -n "$NEW_DAEMON_PID" ] || {
    echo "ERROR: tailscaled is not running after update" >&2
    exit 1
}

RUNNING_NEW_DAEMON_PATH="$(readlink -f "/proc/$NEW_DAEMON_PID/exe" 2>/dev/null)"

[ "$RUNNING_NEW_DAEMON_PATH" = "$NEW_DAEMON_PATH" ] || {
    echo "ERROR: running tailscaled does not match the post-update binary path" >&2
    exit 1
}

RUNNING_NEW_DAEMON_SHA256="$(file_sha256 "/proc/$NEW_DAEMON_PID/exe")"

[ -n "$RUNNING_NEW_DAEMON_SHA256" ] || {
    echo "ERROR: cannot hash post-update running tailscaled process image" >&2
    exit 1
}

[ "$RUNNING_NEW_DAEMON_SHA256" = "$NEW_DAEMON_SHA256" ] || {
    echo "ERROR: post-update running tailscaled process image differs from installed binary" >&2
    echo "Rollback material preserved at: ${ROLLBACK_SNAPSHOT_DIR:-unknown}" >&2
    exit 1
}

echo "Updated tailscale CLI: $NEW_CLI_VERSION"
echo "Updated tailscaled:     $NEW_DAEMON_VERSION"
echo "Updated CLI path:       $NEW_CLI_PATH"
echo "Updated CLI SHA-256:    $NEW_CLI_SHA256"
echo "Updated daemon path:    $NEW_DAEMON_PATH"
echo "Updated daemon SHA-256: $NEW_DAEMON_SHA256"

"$HEALTHCHECK" || {
    echo "ERROR: post-update health check failed" >&2
    echo "Rollback material preserved at: ${ROLLBACK_SNAPSHOT_DIR:-unknown}" >&2
    exit 1
}
