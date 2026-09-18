# Changelog

## Unreleased

### Added
- Added Fedora clean-room Disaster Recovery validation and a guarded restore-finalization helper with dry-run/apply modes.
- Added a post-stability-gate validation plan for exit-node NAT and Fedora/Android DNS datapath closure.
- Added a case-study index and surfaced the uiDivStats and Zen integration investigations.
- Added a dedicated Entware SSD migration runbook and sanitized reboot-validation evidence.
- Added printer-hardening documentation and health-check coverage for disabling the router USB print server and TCP/515 exposure.
- Added recruiter-facing portfolio highlights to the README.
- Added a controlled endpoint-filtering validation methodology for workstation-local Zen and optional AdGuard for Windows testing.
- Added evidence guidance for post-hardening mobile telemetry case studies without inventing a pre-debloat baseline.

### Changed
- Expanded GitHub Actions to execute the existing Python recovery, firewall mock/configuration, evidence-collector, and log-retention tests directly.
- Sanitized deployment-specific identifiers in the Fedora Zen case study while preserving technically relevant public service examples.
- Standardized README architecture rendering on `docs/images/architecture-v2.png`.
- Migrated the persistent Entware environment from USB flash storage to SSD with separate `ENTWARE` and `ROUTER_DATA` filesystems.
- Added active swap on the SSD-backed Entware and data partitions to protect memory-constrained services such as Tailscale.
- Refreshed the roadmap and README to reflect the validated 2026-09-11 deployment state.
- Updated the pinned `actions/checkout` dependency to v7.0.1 on its immutable commit SHA for the Node 24 GitHub Actions runtime.
- Extended the security design and threat model to treat endpoint HTTPS interception, local CA trust, DNS-path preservation, and evidence privacy as explicit trust boundaries.
- Split testing and evidence documentation into CI/mock, router-live, remote-client, endpoint-filtering, and mobile-telemetry validation tracks so results from one layer are not overstated as another layer's capability.
- Documented that repo/documentation work and workstation-local tests may continue during the 2026-09-11 through 2026-09-25 stability observation while router-side corroboration remains read-only.

### Fixed
- Hardened Fedora DR target selection so the helper refuses the running root, same-root backing source, and missing separate `/boot` or `/boot/efi` mounts.
- Made Fedora DR rollback directory creation collision-resistant with `mktemp -d`.
- Made backup sidecar checksums portable by storing the archive basename instead of an absolute archive path.
- Corrected IPv6 documentation so fail-closed enforcement is not claimed when `ip6tables` is unavailable.
- Finalized WAN event handling and rollback tests, including recovery from DNS-path and Tailscale restart failures.
- Hardened firewall, service-start, WAN-event, health-check, log-retention, USB-exposure, uninstall, and Tailscale-update failure handling with regression coverage for the repository-side behavior.
- Removed stale ExpressVPN and NordVPN client configuration from the deployed reference environment.
- Disabled Adaptive QoS after repeatable firmware QoS failures were isolated to the enabled feature.
- Removed unnecessary router-side printer exposure while preserving direct LAN printing through the printer's own network service.

### Validated
- The sanitized 2026-09-11 SSD-migration artifact directly confirms automatic mounting of both SSD filesystems, activation of both swap files, successful Tailscale status with exit-node capability advertised, Unbound running, direct DNSSEC-validated resolution on `127.0.0.1:53535`, and dnsmasq configured to use the local Unbound resolver.
- The 2026-09-11 SSD-migration artifact does not by itself prove syslog-ng recovery, end-to-end mTLS delivery, firewall/printer behavior, every exit-node traffic path, a complete health-check result, or long-term stability; those claims require their own dated evidence.
- Printer regression checks and the repository static/recovery/configuration-validation suite pass in GitHub Actions; CI results are repository-level evidence, not a substitute for live-router validation.
- A 14-day unchanged-state stability observation is in progress; long-term stability is not claimed until that observation completes.
- Endpoint-filtering and mobile-telemetry results are not yet claimed as validated; the repository currently contains methodology and evidence rules for those future tests.

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
