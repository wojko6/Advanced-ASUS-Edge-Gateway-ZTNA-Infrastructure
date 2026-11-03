#!/bin/sh
# Run ONLY inside the disposable Debian build container from ../Dockerfile.
# This is a proposed rebuild from pinned pre-remediation snapshots, NOT proof
# of byte-for-byte identity with the historical September 2026 build.
set -eu

ENTWARE_COMMIT=969c703e6fd8b2ad84d82affaeb14b48d1fcb105
PACKAGES_COMMIT=b6a6f2962f62882b76dfe45f9f9e1238cd9b74fd
UNBOUND_SOURCE_SHA256=35a6dc0e425a9282c3426d9a3043144011bf0534aed4b73ab62c52aee0af1503
BUILD_JOBS="${BUILD_JOBS:-2}"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[ "$(id -u)" != 0 ] || fail 'never build Entware as root'
[ -d /work ] && [ -r /recipe/HISTORICAL-SHA256SUMS.txt ] || fail 'missing isolated mounts'
[ ! -e /work/Entware ] && [ ! -e /work/artifacts ] || fail 'build output already present'
cd /work

echo '=== Entware pinned source checkout ==='
git clone --no-checkout https://github.com/Entware/Entware.git Entware
git -C Entware checkout --detach "$ENTWARE_COMMIT"
[ "$(git -C Entware rev-parse HEAD)" = "$ENTWARE_COMMIT" ] || fail 'Entware revision mismatch'
cd Entware
ln -s configs/armv7-3.2.config .config
grep -Fq 'CONFIG_TARGET_armv7_3_2=y' .config || fail 'wrong target'
grep -Fq 'CONFIG_TARGET_ARCH_PACKAGES="armv7-3.2"' .config || fail 'wrong package ABI'

echo '=== Entware package-feed pinned source checkout ==='
./scripts/feeds update packages
git -C feeds/packages checkout --detach "$PACKAGES_COMMIT"
[ "$(git -C feeds/packages rev-parse HEAD)" = "$PACKAGES_COMMIT" ] || fail 'package-feed revision mismatch'

# Only bump upstream Unbound tarball and SHA, preserving historical release=1.
# Assert exact old fields so an unexpected upstream source fails closed.
python3 - <<'PY'
from pathlib import Path
p = Path('feeds/packages/net/unbound/Makefile')
s = p.read_text()
old_v = 'PKG_VERSION:=1.24.2'
old_hash = 'PKG_HASH:=44e7b53e008a6dcaec03032769a212b46ab5c23c105284aa05a4f3af78e59cdb'
assert s.count(old_v) == 1 and s.count(old_hash) == 1, 'unexpected upstream Makefile'
assert s.count('PKG_RELEASE:=1') == 1, 'historical release differs'
s = s.replace(old_v, 'PKG_VERSION:=1.26.1')
s = s.replace(old_hash, 'PKG_HASH:=35a6dc0e425a9282c3426d9a3043144011bf0534aed4b73ab62c52aee0af1503')
p.write_text(s)
names = ['libunbound', 'unbound-daemon', 'unbound-anchor',
         'unbound-checkconf', 'unbound-control', 'unbound-control-setup',
         'unbound-host']
cfg = Path('.config')
lines = cfg.read_text().splitlines()
for name in names:
    key = 'CONFIG_PACKAGE_' + name
    lines = [line for line in lines if not (line.startswith(key + '=') or line == '# ' + key + ' is not set')]
    lines.append(key + '=m')
cfg.write_text('\n'.join(lines) + '\n')
PY
echo "ENTWARE_SNAPSHOT=$ENTWARE_COMMIT"
echo "PACKAGES_SNAPSHOT=$PACKAGES_COMMIT"
echo "UNBOUND_SOURCE_SHA256=$UNBOUND_SOURCE_SHA256"
./scripts/feeds install -p packages unbound
make defconfig
for name in libunbound unbound-daemon unbound-anchor unbound-checkconf unbound-control unbound-control-setup unbound-host; do
    grep -Fqx "CONFIG_PACKAGE_${name}=m" .config || fail "module not enabled: $name"
done
echo 'UNBOUND_CONFIG_PREFLIGHT=PASS'

echo '=== Build toolchain and Unbound (may need substantial disk/time) ==='
make tools/install -j"$BUILD_JOBS"
make toolchain/install -j"$BUILD_JOBS"
make target/compile -j"$BUILD_JOBS"
make package/feeds/packages/unbound/compile -j"$BUILD_JOBS"
echo 'UNBOUND_COMPILE=PASS'

# Export exactly the seven intended output packages; no installer or router
# scripts are run. Reject missing/duplicate files or unexpected release/ABI.
mkdir -p /work/artifacts
for name in libunbound unbound-daemon unbound-anchor unbound-checkconf unbound-control unbound-control-setup unbound-host; do
    file="${name}_1.26.1-1_armv7-3.2.ipk"
    matches="$(find bin -type f -name "$file")"
    [ -n "$matches" ] || fail "missing $file"
    [ "$(printf '%s\n' "$matches" | wc -l | tr -d ' ')" = 1 ] || fail "ambiguous $file"
    cp "$matches" "/work/artifacts/$file"
done

cd /work/artifacts
python3 /recipe/verify-artifacts.py /work/artifacts
sha256sum ./*.ipk | sed 's#  ./#  #' > SHA256SUMS.generated
# A hash mismatch is expected when toolchain inputs/environment drift; report
# parity honestly and leave outputs for review, never authorize deployment.
if sha256sum -c /recipe/HISTORICAL-SHA256SUMS.txt; then
    echo 'UNBOUND_HISTORICAL_BYTE_PARITY=PASS'
else
    echo 'UNBOUND_HISTORICAL_BYTE_PARITY=NOT_PROVEN'
fi
echo 'UNBOUND_ARTIFACT_SET=PASS'
echo 'ROUTER_DEPLOYMENT=NOT_PERFORMED'
