# Tailscale maintenance and rollback

Tailscale updates on the ASUS Edge Gateway are explicit maintenance actions.
They are not performed automatically at boot and automatic Tailscale update
application is kept disabled.

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
