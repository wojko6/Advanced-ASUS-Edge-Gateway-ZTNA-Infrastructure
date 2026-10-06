# Tailscale package/live-version drift hardening — live validation

Date: 2026-10-06

Issue: #177

## Scope

Bounded validation of the hardened Tailscale maintenance path on the reference
ASUS TUF-AX5400.

The test was designed to prove that Entware package metadata cannot silently
replace a newer validated live Tailscale binary with an older package.

No Tailscale package mutation was intentionally performed.

## Observed baseline

After a successful `opkg update`:

```text
installed package metadata: 1.96.1-1
feed candidate:             1.96.1-1
live tailscale CLI:         1.102.3
live tailscaled:            1.102.3
```

Resolved binaries:

```text
/tmp/mnt/ENTWARE/entware/bin/tailscale
/tmp/mnt/ENTWARE/entware/bin/tailscaled
```

Pre-test SHA-256:

```text
tailscale:
9b2aa24340d813d3eeb52344548239d71e54b82f68fbb0ef172ae16819b4944f

tailscaled:
f093488dcb7a2204787de2e0ab12882e2e3caf44f87024a101df04e8753f9eed
```

The running daemon resolved to the same `tailscaled` binary path.

## Controlled downgrade-refusal test

The hardened updater refreshed the Entware package index, inspected installed
metadata, feed candidate and live binaries, and detected:

```text
Entware installed: 1.96.1-1
Entware candidate: 1.96.1-1
Live binary:       1.102.3
```

It then terminated before package mutation with:

```text
ERROR: refusing implicit Tailscale downgrade
ERROR: Entware candidate 1.96.1-1 is older than live binary 1.102.3
UPDATER_RC=2
```

## Mutation check

Post-test versions remained:

```text
tailscale:  1.102.3
tailscaled: 1.102.3
```

Post-test SHA-256 values were identical to the pre-test hashes.

This demonstrates that the refusal occurred before live binary replacement.

## Runtime validation

After the refusal:

```text
TAILSCALE_STATUS_RC=0
HEALTHCHECK_RC=0
```

The project healthcheck reported:

```text
Summary: 0 failure(s), 0 warning(s)
```

The router continued to advertise exit-node capability. The active preferences
included default-route advertisements and `NetfilterMode: 0`, consistent with
the project-owned firewall model.

## Automatic update policy

The live Tailscale preferences initially showed automatic update application
enabled.

Automatic application was explicitly disabled so future package changes cannot
bypass the project maintenance path.

The intended project state is:

```text
EDGE_TS_AUTO_UPDATE=false
AutoUpdate.Apply=false
```

Post-change Tailscale status and the project healthcheck remained successful.

## Test boundary

The repository mock tests exercise the positive newer-candidate transaction and
the defined failure paths.

A real positive live upgrade was not performed because the current Entware feed
offered only `1.96.1-1`, which is older than the validated live `1.102.3`.

Therefore this evidence claims live validation of downgrade prevention and
runtime preservation, not a successful real package upgrade.
