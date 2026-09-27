#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMPROOT="$(mktemp -d)"
trap 'rm -rf "$TMPROOT"' EXIT HUP INT TERM

ROOT="$TMPROOT/root"
BIN="$TMPROOT/bin"
OUT="$TMPROOT/output"
mkdir -p "$ROOT/jffs/scripts" "$ROOT/jffs/configs" "$ROOT/jffs/addons/amtm" \
    "$ROOT/jffs/addons/unbound" "$ROOT/jffs/addons/asus-edge" \
    "$ROOT/opt/bin" "$ROOT/opt/sbin" "$ROOT/opt/var/lib/unbound" \
    "$ROOT/opt/etc/init.d" "$ROOT/proc" "$BIN"

cat >"$BIN/nvram" <<'EOF'
#!/bin/sh
case "$2" in
    productid) echo TUF-AX5400 ;;
    firmver) echo 3.0.0.4 ;;
    buildno) echo 388.11 ;;
    extendno) echo 1-gnuton1_tuf ;;
    *) echo 'SECRET-UNEXPECTED' ;;
esac
EOF

cat >"$BIN/mount" <<'EOF'
#!/bin/sh
echo '/dev/mtdblock9 on /jffs type jffs2 (rw,noatime)'
echo '/dev/sda2 on /tmp/mnt/ROUTER_DATA type ext4 (rw,nodev)'
echo '/dev/sda1 on /tmp/mnt/ENTWARE type ext4 (rw,nodev)'
EOF

cat >"$ROOT/opt/bin/opkg" <<'EOF'
#!/bin/sh
case "$1" in
    list-installed)
        echo 'tailscale - 1.96.1-1'
        echo 'unbound-daemon - 1.26.1-1'
        ;;
    status)
        echo 'Package: tailscale'
        echo 'Version: 1.96.1-1'
        echo 'Status: install user installed'
        echo 'Architecture: armv7-3.2'
        ;;
    files)
        echo '/opt/bin/tailscale'
        echo '/opt/bin/tailscaled'
        ;;
esac
EOF

cat >"$ROOT/opt/bin/tailscale" <<'EOF'
#!/bin/sh
echo '1.102.3'
echo 'private-node-name.example'
EOF

cat >"$ROOT/opt/bin/tailscaled" <<'EOF'
#!/bin/sh
echo '1.102.3'
echo 'private-node-name.example'
EOF

cat >"$ROOT/opt/sbin/unbound" <<'EOF'
#!/bin/sh
echo 'Version 1.26.1'
EOF

cat >"$ROOT/opt/sbin/syslog-ng" <<'EOF'
#!/bin/sh
echo 'syslog-ng 4 (4.10.2)'
EOF

chmod +x "$BIN/nvram" "$BIN/mount" "$ROOT/opt/bin/opkg" \
    "$ROOT/opt/bin/tailscale" "$ROOT/opt/bin/tailscaled" \
    "$ROOT/opt/sbin/unbound" "$ROOT/opt/sbin/syslog-ng"

cat >"$ROOT/proc/swaps" <<'EOF'
Filename Type Size Used Priority
/tmp/mnt/ROUTER_DATA/myswap.swp file 2097148 0 -1
/tmp/mnt/ENTWARE/myswap.swp file 524284 0 -2
EOF

for file in \
    "$ROOT/jffs/scripts/post-mount" \
    "$ROOT/jffs/scripts/firewall-start" \
    "$ROOT/jffs/scripts/services-start" \
    "$ROOT/jffs/scripts/wan-event" \
    "$ROOT/jffs/configs/asus-edge.conf" \
    "$ROOT/jffs/configs/dnsmasq.conf.add" \
    "$ROOT/opt/var/lib/unbound/unbound.conf" \
    "$ROOT/opt/etc/init.d/S61unbound" \
    "$ROOT/opt/etc/init.d/S06tailscaled"
do
    mkdir -p "$(dirname "$file")"
    printf '%s\n' 'fixture-content' >"$file"
done

printf '%s\n' 'addon' >"$ROOT/jffs/addons/amtm/mount-entware.mod"
printf '%s\n' 'addon' >"$ROOT/jffs/addons/unbound/unbound_manager.sh"

DR_PATH="$BIN:/usr/bin:/bin" \
EDGE_DR_ROOT="$ROOT" \
EDGE_DR_PROC_SWAPS="$ROOT/proc/swaps" \
sh "$REPO_DIR/scripts/collect-dr-manifest.sh" "$OUT" >/dev/null

for file in README.md storage.txt packages.txt tailscale-provenance.txt \
    critical-file-metadata.txt addons.txt service-versions.txt SHA256SUMS
do
    [ -s "$OUT/$file" ] || {
        echo "FAIL: DR manifest missing $file" >&2
        exit 1
    }
done

grep -F 'Model: TUF-AX5400' "$OUT/README.md" >/dev/null
grep -F 'Version: 1.96.1-1' "$OUT/tailscale-provenance.txt" >/dev/null
grep -F '1.102.3' "$OUT/tailscale-provenance.txt" >/dev/null
grep -F '/jffs/scripts/post-mount' "$OUT/critical-file-metadata.txt" >/dev/null
grep -F '/jffs/addons/amtm: present' "$OUT/addons.txt" >/dev/null

if grep -R -E 'SECRET-UNEXPECTED|private-node-name|sshd_pass|wan_pppoe_passwd' "$OUT" >/dev/null; then
    echo "FAIL: DR manifest leaked excluded data" >&2
    exit 1
fi

(cd "$OUT" && sha256sum -c SHA256SUMS >/dev/null)

if grep -F 'nvram show' "$REPO_DIR/scripts/collect-dr-manifest.sh" >/dev/null; then
    echo "FAIL: DR manifest must not collect raw NVRAM" >&2
    exit 1
fi

if grep -F 'tailscale status' "$REPO_DIR/scripts/collect-dr-manifest.sh" >/dev/null; then
    echo "FAIL: DR manifest must not collect Tailscale node state" >&2
    exit 1
fi

echo "PASS: sanitized DR rebuild manifest"
