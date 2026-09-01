#!/bin/sh

set -u

[ "$(id -u)" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }
command -v opkg >/dev/null 2>&1 || { echo "ERROR: Entware not available" >&2; exit 1; }

OLD_VERSION="$(tailscale version 2>/dev/null | head -n 1)"
echo "Installed Tailscale: ${OLD_VERSION:-unknown}"
echo "This is an explicit maintenance action; no package upgrades run at boot."

opkg update || exit 1
opkg list-upgradable | grep '^tailscale ' || { echo "No Tailscale update available."; exit 0; }
opkg upgrade tailscale || exit 1

if [ -x /jffs/addons/asus-edge/bin/services-start ]; then
    /jffs/addons/asus-edge/bin/services-start
fi

NEW_VERSION="$(tailscale version 2>/dev/null | head -n 1)"
echo "Updated Tailscale: ${NEW_VERSION:-unknown}"
/jffs/addons/asus-edge/bin/healthcheck.sh
