#!/bin/sh
# Collect a sanitized, read-only rebuild manifest for router disaster recovery.

set -eu

PATH="${DR_PATH:-/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin}"
umask 077

ROOT="${EDGE_DR_ROOT:-}"
PROC_SWAPS="${EDGE_DR_PROC_SWAPS:-${ROOT}/proc/swaps}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="${1:-/tmp/asus-edge-dr-manifest-$TIMESTAMP}"

root_path() {
    printf '%s%s\n' "$ROOT" "$1"
}

executable_exists() {
    executable_name="$1"
    case "$executable_name" in
        */*)
            [ -x "$executable_name" ]
            return
            ;;
    esac

    saved_ifs="$IFS"
    IFS=:
    # PATH splitting is intentional here.
    # shellcheck disable=SC2086
    for executable_dir in $PATH; do
        [ -n "$executable_dir" ] || continue
        if [ -x "$executable_dir/$executable_name" ]; then
            IFS="$saved_ifs"
            return 0
        fi
    done
    IFS="$saved_ifs"
    return 1
}

sha256sum_run() {
    for sum_bin in "$(root_path /opt/bin/sha256sum)" "$(root_path /opt/sbin/sha256sum)" \
        /usr/bin/sha256sum /usr/sbin/sha256sum /bin/sha256sum /sbin/sha256sum; do
        [ -x "$sum_bin" ] && { "$sum_bin" "$@"; return; }
    done
    if [ -z "$ROOT" ] && [ -x /bin/busybox ] && /bin/busybox sha256sum /dev/null >/dev/null 2>&1; then
        /bin/busybox sha256sum "$@"
        return
    fi
    echo "ERROR: sha256sum unavailable" >&2
    return 1
}

nvram_value() {
    if executable_exists nvram; then
        nvram get "$1" 2>/dev/null || true
    fi
}

first_line() {
    "$@" 2>/dev/null | sed -n '1p'
}

metadata_if_present() {
    live_path="$1"
    display_path="$2"
    if [ -e "$live_path" ]; then
        printf '%s\t' "$display_path"
        ls -ldn "$live_path" 2>/dev/null || true
    fi
}

hash_if_present() {
    live_path="$1"
    display_path="$2"
    if [ -f "$live_path" ]; then
        hash_value="$(sha256sum_run "$live_path" 2>/dev/null | awk '{print $1}')"
        [ -n "$hash_value" ] && printf '%s  %s\n' "$hash_value" "$display_path"
    fi
}

[ ! -e "$OUTPUT_DIR" ] || {
    echo "ERROR: output path already exists: $OUTPUT_DIR" >&2
    exit 1
}
mkdir -p "$OUTPUT_DIR"

MODEL="$(nvram_value productid)"
FIRMVER="$(nvram_value firmver)"
BUILDNO="$(nvram_value buildno)"
EXTENDNO="$(nvram_value extendno)"

{
    echo "# Router DR rebuild manifest"
    echo
    printf 'Collected (UTC): %s\n' "$TIMESTAMP"
    printf 'Model: %s\n' "${MODEL:-unavailable}"
    printf 'Firmware: %s %s %s\n' "${FIRMVER:-unavailable}" "${BUILDNO:-}" "${EXTENDNO:-}"
    echo
    echo "This bundle is intentionally sanitized and read-only."
    echo "It does not contain NVRAM values, Tailscale node state, auth keys, credentials, private keys, or configuration file contents."
    echo "A separate encrypted ASUS/Merlin settings export is required for NVRAM recovery."
} >"$OUTPUT_DIR/README.md"

{
    echo "# Storage and swap topology"
    echo
    echo "## Mounts"
    if executable_exists mount; then
        mount 2>/dev/null | grep -E ' on (/jffs|/tmp/mnt/[^ ]+|/opt)( |/)' || true
    else
        echo "mount unavailable"
    fi
    echo
    echo "## Swap"
    if [ -r "$PROC_SWAPS" ]; then
        cat "$PROC_SWAPS"
    else
        echo "swap inventory unavailable"
    fi
    echo
    echo "Filesystem UUIDs are intentionally omitted from the public/sanitized rebuild manifest."
} >"$OUTPUT_DIR/storage.txt"

OPKG="$(root_path /opt/bin/opkg)"
{
    echo "# Entware package inventory"
    if [ -x "$OPKG" ]; then
        "$OPKG" list-installed 2>/dev/null | sort
    else
        echo "opkg unavailable"
    fi
} >"$OUTPUT_DIR/packages.txt"

TAILSCALE="$(root_path /opt/bin/tailscale)"
TAILSCALED="$(root_path /opt/bin/tailscaled)"
{
    echo "# Tailscale package/runtime provenance"
    echo
    echo "## Package metadata"
    if [ -x "$OPKG" ]; then
        "$OPKG" status tailscale 2>/dev/null | grep -E '^(Package|Version|Architecture|Status):' || true
        echo
        echo "## Package-owned binary paths"
        "$OPKG" files tailscale 2>/dev/null | grep -E '/tailscale(d)?$' || true
    else
        echo "opkg unavailable"
    fi

    echo
    echo "## Live binary versions"
    if [ -x "$TAILSCALE" ]; then
        first_line "$TAILSCALE" version || true
    else
        echo "tailscale CLI unavailable"
    fi
    if [ -x "$TAILSCALED" ]; then
        first_line "$TAILSCALED" --version || true
    else
        echo "tailscaled unavailable"
    fi

    echo
    echo "## Live binary hashes"
    hash_if_present "$TAILSCALE" /opt/bin/tailscale
    hash_if_present "$TAILSCALED" /opt/bin/tailscaled

    echo
    echo "Tailscale status, node identity and authentication state are intentionally excluded."
} >"$OUTPUT_DIR/tailscale-provenance.txt"

{
    echo "# Critical recovery file metadata"
    for path in \
        /jffs/scripts/post-mount \
        /jffs/scripts/dnsmasq.postconf \
        /jffs/scripts/firewall-start \
        /jffs/scripts/services-start \
        /jffs/scripts/wan-event \
        /jffs/scripts/service-event \
        /jffs/configs/asus-edge.conf \
        /jffs/configs/dnsmasq.conf.add \
        /opt/var/lib/unbound \
        /opt/var/lib/unbound/unbound.conf \
        /opt/var/lib/unbound/root.key \
        /opt/etc/init.d/S61unbound \
        /opt/etc/init.d/S06tailscaled \
        /opt/etc/init.d/S01syslog-ng
    do
        metadata_if_present "$(root_path "$path")" "$path"
    done

    echo
    echo "# Content hashes for selected integration files"
    for path in \
        /jffs/scripts/post-mount \
        /jffs/scripts/dnsmasq.postconf \
        /jffs/scripts/firewall-start \
        /jffs/scripts/services-start \
        /jffs/scripts/wan-event \
        /jffs/configs/dnsmasq.conf.add \
        /opt/var/lib/unbound/unbound.conf \
        /opt/etc/init.d/S61unbound \
        /opt/etc/init.d/S06tailscaled
    do
        hash_if_present "$(root_path "$path")" "$path"
    done
} >"$OUTPUT_DIR/critical-file-metadata.txt"

{
    echo "# Addon ownership inventory"
    for path in \
        /jffs/addons/amtm \
        /jffs/addons/diversion \
        /jffs/addons/unbound \
        /jffs/addons/uiDivStats.d \
        /jffs/addons/asus-edge
    do
        live_path="$(root_path "$path")"
        if [ -d "$live_path" ]; then
            printf '%s: present\n' "$path"
            find "$live_path" -maxdepth 2 -type f 2>/dev/null \
                | sed "s#^$ROOT##" | sort | sed -n '1,120p'
        else
            printf '%s: missing\n' "$path"
        fi
        echo
    done
    echo "File contents are intentionally excluded."
} >"$OUTPUT_DIR/addons.txt"

{
    echo "# Service versions"
    UNBOUND="$(root_path /opt/sbin/unbound)"
    SYSLOG_NG="$(root_path /opt/sbin/syslog-ng)"
    if [ -x "$UNBOUND" ]; then
        printf 'Unbound: '
        first_line "$UNBOUND" -V || true
    else
        echo "Unbound: unavailable"
    fi
    if [ -x "$SYSLOG_NG" ]; then
        printf 'syslog-ng: '
        first_line "$SYSLOG_NG" -V || true
    else
        echo "syslog-ng: unavailable"
    fi
} >"$OUTPUT_DIR/service-versions.txt"

if (
    cd "$OUTPUT_DIR" || exit 1
    sha256sum_run README.md storage.txt packages.txt tailscale-provenance.txt \
        critical-file-metadata.txt addons.txt service-versions.txt
) >"$OUTPUT_DIR/SHA256SUMS"; then
    :
else
    rm -f "$OUTPUT_DIR/SHA256SUMS"
    echo "ERROR: cannot create DR manifest checksums" >&2
    exit 1
fi

echo "DR rebuild manifest created: $OUTPUT_DIR"
echo "Review it manually before publishing or attaching to evidence."
