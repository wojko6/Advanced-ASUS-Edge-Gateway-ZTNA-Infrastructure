# Changelog

## Unreleased

## [2.1.3] - 2026-09-09

### Security
- Hardened installer file and Merlin-hook deployment against overwriting symbolic-link destinations.
- Added regression coverage verifying that protected symlink targets remain unchanged.
- Expanded `.gitignore` coverage for private keys, certificates, environment files, and Tailscale state.

### Fixed
- Restored `EDGE_SERVICE_RETRY_SECONDS` to the example configuration so documented settings match runtime behavior.
- Made the installer report its release version directly from the repository `VERSION` file.
- Marked the USB exposure checker executable so its repository mode matches deployment behavior.

### Changed
- Refactored health-check condition handling to remove ShellCheck SC2015 findings without changing validation behavior.
- Clarified the final evidence checksum workflow so `SHA256SUMS` is regenerated after publication sanitization.

### Validated
- Added sanitized live-validation evidence from 2026-09-09 covering the local DNS path, observed DoT bypass, temporary TCP/853 enforcement, and encrypted DNS bypass over port 443.
- Router evidence collection completed with 34 checks passing, 0 warnings, and 0 failures.
- Static test suite passes with 11 recovery tests.
- GitHub Actions `Shell tests` passed for the release candidate.

### Notes
- DNS interception remains a classic TCP/UDP 53 control and does not claim comprehensive prevention of DoH, DoT, or DoQ.
- Permanent optional DoT/DoQ enforcement is planned separately rather than being included in this maintenance release.

## [2.1.2] - 2026-09-08

### Added
- Sanitized live-validation evidence for remote Android DNS over Tailscale.
- Documented LTE/5G and home Wi-Fi validation of the dnsmasq/Diversion/Unbound path.

### Changed
- Hardened infrastructure USB exposure by disabling unnecessary SMB/DLNA services.
- Updated project documentation to surface the latest live DNS validation.

### Validated
- Remote Android client retained Internet connectivity with Tailscale DNS enabled.
- DNS queries and responses traversed the Tailscale tunnel to the router.
- Normal DNS resolution and Diversion NXDOMAIN blocking were confirmed.
- Unbound DNSSEC validation passed.
- Router healthcheck completed with 0 failures and 0 warnings.

### Notes
- The Android remote-client validation used a Tailscale beta client.
- This release does not claim that the previously observed stable Android client DNS issue has been fixed in a stable release.

## 2.1.1 — 2026-09-05

- Made ASUS Edge explicitly own the Tailscale firewall policy by enforcing
  `netfilter-mode=off`.
- Added health checks and regression tests for `NetfilterMode: 0` and the
  absence of competing native `ts-input`, `ts-forward`, and `ts-postrouting`
  chains.
- Resolved the Asuswrt-Merlin Tailscale `ts-postrouting` health warning while
  preserving subnet routing and exit-node operation.
- Added sanitized post-deployment, post-reboot validation evidence with a
  verified SHA-256 manifest.


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
