# Tailscale maintenance and rollback

Tailscale updates on the ASUS Edge Gateway are explicit maintenance actions.
They are not performed automatically at boot and automatic Tailscale update
application is kept disabled.

## Reference router live checkpoint — 2026-11-17

**Status: OPERATOR-REPORTED LIVE / BOUNDED PASS.** On the ARMv7
reference ASUS, a separate Fedora 45 cross-build of upstream Tailscale
`v1.104.7` (commit `cbc74fe48ef1b1649f69a4d9a602319427e25102`,
Go 1.27.4, `CGO_ENABLED=0`) was transferred through a LAN-only
management session and deployed explicitly, without `opkg`, automatic
updaters or a router reboot. CLI and active daemon were both observed at
`1.104.7` after the service restart, with matching SHA-256 hashes,
`BackendState=Running`, preserved tailnet IPv4 and an active direct
Fedora peer. The ASUS continued advertising its exit-node capability.
A cellular client observed its public IPv4 change to the home-WAN egress
when selecting this exit node (IPv4 smoke PASS).

The managed Entware package metadata still reported `1.96.1-1`; it
does not reflect the manually installed `1.104.7` binaries. The
existing service and the ASUS Edge startup configuration were
inspected; the externally sourced configuration resolved to the active
daemon state path. No file-state migration or service-script rewrite
was performed.

A **separate operator-created protected on-device backup** (reported
66.6 MB) retained the previous `1.104.4` binaries, both existing
state files, daemon-state directory and startup scripts. It is on the
same Entware storage device; it is not an off-device disaster-recovery
copy. The one-shot updater's automatic rollback path was prepared but
**not exercised**. This procedure is distinct from the
`update-tailscale.sh` package-manager updater and its snapshot layout
documented in the following sections; do not assume they share a
manifest, path or identical recovery behavior.

The router returned `ipv6_service=disabled` and no default IPv6 route.
There was no new DNS-path validation, packet-level forwarding proof,
reboot-persistence test, rollback drill or long soak during this update.
See the [dated worklog](worklog/2026-11-17.md) for the exact acceptance
boundary. Do not use the historical October `1.102.3` example below as
the current live version.

## Why

The reference router has demonstrated real package/live-version drift:

```text
Entware installed metadata: 1.96.1-1
Entware feed candidate:     1.96.1-1
live tailscale:             1.102.3
live tailscaled:            1.102.3
```

A package manager can therefore consider a package to be an upgrade even when
installing it would replace a newer manually validated live binary with an older
one.

`update-tailscale.sh` treats the actual live binary version as an independent
source of truth and does not rely on `opkg list-upgradable` alone.

## Preflight

Before package mutation the updater verifies:

- root execution and Entware availability;
- managed `services-start` and healthcheck paths;
- live `tailscale` and `tailscaled` versions;
- CLI/daemon version agreement;
- resolved executable paths;
- SHA-256 hashes of both live binaries;
- running daemon provenance where available;
- installed Entware package version;
- current Entware candidate version.

The candidate version is compared deterministically with the live version.

Behavior:

```text
candidate > live  -> update path may continue
candidate = live  -> no package mutation
candidate < live  -> fail closed, RC=2
unknown/malformed -> fail closed
```

## Rollback material

Before an allowed package mutation the known-good binaries are copied to:

```text
/opt/var/backups/asus-edge/tailscale-update/YYYYMMDD-HHMMSS-PID/
```

Each snapshot contains:

```text
tailscale
tailscaled
manifest.txt
```

The manifest records the installed package version, candidate package version,
live version, original executable paths and SHA-256 hashes.

The copied binaries are hashed again before the package transaction. A snapshot
that does not verify aborts the update.

## Recovery

Rollback is a manual maintenance action. Do not restore binaries through a
remote Tailscale-only session because restarting `tailscaled` can terminate that
management path. Use LAN/local administrative access and first select the
verified snapshot whose manifest matches the intended known-good version.

After restoring known-good binaries, recover through the project-owned path:

```sh
/jffs/addons/asus-edge/bin/services-start
/jffs/addons/asus-edge/bin/healthcheck.sh
```

Then verify:

```sh
tailscale --socket=/var/run/tailscale/tailscaled.sock status
tailscale version
tailscaled --version
```

The authentication state is not replaced by the updater or by the binary
snapshot.

## Automatic updates

The project configuration requires:

```text
EDGE_TS_AUTO_UPDATE=false
```

`services-start` applies this through the Tailscale local API, and
`healthcheck.sh` fails if automatic update application is enabled or cannot be
verified.

This ensures package changes remain deliberate, observable maintenance actions.

## Validation boundary

Static/mock coverage includes:

- candidate newer than live;
- candidate equal to live;
- candidate older than live;
- malformed version input;
- service recovery failure;
- post-update healthcheck failure.

The 2026-10-06 reference-router live test exercised the real downgrade-refusal
path. A real positive package upgrade was not claimed because the active Entware
feed still offered `1.96.1-1`, older than the validated live `1.102.3`.
