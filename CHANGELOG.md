# Changelog

## 2.1.0 — 2026-09-04

- Added source-scoped Tailscale access for a legacy LAN printer and validated
  Android remote printing without an exit node.
- Hardened amtm/Entware startup coordination and direct Unbound recovery.
- Added mutual-TLS log forwarding, reliable buffering, retention controls, and
  live delivery validation.
- Prevented an ARMv7 Tailscale boot-time OOM by waiting for required swap,
  retrying daemon startup, preserving the previous log, and extending health
  and static checks.

## 2.0.1 — 2026-09-01

- Replaced the old architecture asset with a diagram that matches the v2 firewall, DNS, logging, and operations model.
- Renamed and tightened the Polish deployment guide.
- Corrected the management-address examples and the configured Tailscale socket command.
- Fixed the Unbound DNSSEC health check to query loopback port 53535.
- Kept IPv6 fail-closed while managed chains are rebuilt and added jump-count health checks.
- Added a manual CI trigger and tightened static test coverage.
- Added sanitized router evidence collection, a live-validation report template, and publication safeguards.
- Added negative configuration validation and evidence-redaction tests.
- Pinned the checkout action to an immutable commit.

## 2.0.0 — 2026-09-01

- Converted documented configuration into a reproducible repository structure.
- Added granular, idempotent Tailscale firewall and NAT chains.
- Removed boot-time package updates and fixed service readiness/locking.
- Added safe hook integration, health checks, backup/restore, maintenance update script, tests, CI, Tailscale Grants policy, threat model, operational runbook, and evidence plan.
