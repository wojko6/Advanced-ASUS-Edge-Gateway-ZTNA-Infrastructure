# Rebuilding the locally deployed Unbound 1.26.1 for Entware ARMv7

**State:** candidate workstation-only recovery recipe; **not yet live rebuilt in CI**. The reference ASUS TUF-AX5400 **already runs** the five locally built `1.26.1-1` packages. **Do not redeploy or add jacklul's Entware feed** for this task.

## Proven historical deployment (26–27 September 2026)

Authoritative production record: [Unbound 1.26.1 CVE remediation case study](../docs/case-studies/unbound-cve-2026-81642-remediation-case-study.md). Actually installed:

- `libunbound`
- `unbound-daemon`
- `unbound-anchor`
- `unbound-checkconf`
- `unbound-control`

These were installed together as `1.26.1-1` for `armv7-3.2`. The historical build also produced `unbound-control-setup` and `unbound-host`, which were **not installed**. Deployment retained the Unbound Manager integration and customized `/opt/etc/init.d/S61unbound` with `ARGS="-c /opt/var/lib/unbound/unbound.conf"`. Offline rollback to the previously installed `1.24.2-1` set was prepared, but never exercised destructively. After a trust-anchor directory ownership incident, the production resolver passed positive AD and negative SERVFAIL DNSSEC tests.

The 8 October production read-only check reconfirmed that all five installed packages report `1.26.1-1`. This does not, alone, attest the byte identity of their installed payloads.

## Reproduction scope and uncertainty

The original case study preserved upstream Unbound source SHA, package names/versions, Entware ABI, seven IPK SHA-256 hashes and the Debian 12/Python 2 builder requirements. **It did not retain exact Git commit IDs of the original two Entware trees or a digest-pinned container base.** Consequently a true byte-for-byte historical rebuild cannot be promised.

This recipe deliberately pins a *candidate pre-remediation snapshot* (last historical revisions visible before the 26 September build):

- `Entware/Entware` at `969c703e6fd8b2ad84d82affaeb14b48d1fcb105`;
- `Entware/entware-packages` at `b6a6f2962f62882b76dfe45f9f9e1238cd9b74fd`;
- Unbound source release `1.26.1` SHA-256 `35a6dc0e425a9282c3426d9a3043144011bf0534aed4b73ab62c52aee0af1503`;
- Entware target `armv7-3.2`, Cortex-A9, EABI5 soft-float, glibc 2.27;
- `PKG_RELEASE:=1` (our packages, not the independent jacklul `1.26.1-0` feed).

The builder runs in a disposable Debian 12 container. Its legacy Python 2.7.18 tarball SHA-256 is pinned. Other builder/base-image and downloaded build dependencies are *not* yet pinned to immutable digests. A successful source rebuild is therefore **not** proof of identical binaries.

## Offline/static checks (do not download anything)

```sh
sh scripts/build-unbound-entware-armv7.sh --check
sh tests/test-unbound-rebuild-contract.sh
```

## Isolated workstation build

Requires Linux, Podman (preferred) or Docker, an available network and substantial free disk space (allocate at least 30 GiB; toolchain builds can require more). No router account, Entware feed modification, production path or daemon access is required.

```sh
export EDGE_UNBOUND_BUILD_DIR="$HOME/.cache/asus-edge-unbound-armv7-$(date +%Y%m%d)"
export EDGE_UNBOUND_BUILD_JOBS=2
# Optional: export EDGE_UNBOUND_CONTAINER_ENGINE=docker
sh scripts/build-unbound-entware-armv7.sh --build
```

**Use a fresh output directory.** The runner refuses to replace a pre-existing `Entware` checkout or `artifacts` directory. It checks Git commit IDs, rejects unexpected old Unbound recipe fields, builds host tools and target toolchain, and exports exactly seven `armv7-3.2` IPKs plus `SHA256SUMS.generated`. Container build and toolchain bootstrap have **not yet** been exercised for this PR; errors must be fixed and rerun in a new directory.

No `opkg` command is executed against the router. The script never restarts Unbound and never installs the output.

## Artifact acceptance before any production use

1. Require all seven expected IPK filenames, `1.26.1-1` version and `armv7-3.2` package metadata. Compare the generated hash manifest to `scripts/unbound/HISTORICAL-SHA256SUMS.txt`. Matching all hashes establishes package-byte parity; divergence demands independent source/toolchain review, not blind deployment.
2. Inspect package control metadata/dependencies, the ELF32 ARM EABI5 soft-float target, and use of the `/opt/lib/ld-linux.so.3` interpreter. Verify dependency resolution on a **disposable** Entware root matching the production ABI. Filename checks alone are insufficient.
3. Verify packaged `S61unbound` handling. The stock package can replace the custom Manager-owned service script; recover it from a predeployment backup if testing an upgrade.
4. Validate the actual runtime configuration `/opt/var/lib/unbound/unbound.conf`, listener `127.0.0.1:53535` on UDP/TCP, DNSSEC AD and negative SERVFAIL, and dnsmasq forwarding in an isolated lab.
5. Verify that `/opt/var/lib/unbound` and the trust-anchor file are writable by the configured runtime identity. The 2026-09-27 deployment initially failed this check when Unbound ran as `nobody`.
6. Preserve a SHA-256-verified **offline** rollback bundle of all five previous `1.24.2-1` IPKs and the active Unbound/Manager config/integration. Review the existing documented rollback procedure before any future maintenance.
7. Only after isolated testing, a maintenance-window decision and current backups may a router-side change be considered. This PR intentionally provides **no production install script**, to avoid accidental upgrades of the active DNS chain.

## Risk and CI scope

The fast CI test checks the pinned source/ABI contract, syntax and historical manifest. **It does not cross-build Unbound**, assess package dependencies, run an isolated resolver, validate DR, or compare actual binary hashes. Those are separate acceptance gates before promoting the build from candidate to fully reproduced.

See also [DNS Guard audit](../docs/dns-guard-v3.2-recovery-audit.md) and [upstream Entware update request](https://github.com/Entware/Entware/issues/1274). The goal is recovery engineering, not enabling automated upgrades or public redistribution of deployment-specific configuration.
