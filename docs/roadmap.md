# Roadmap

## Completed and validated — SSD migration

The persistent router storage migration was completed and reboot-validated on 2026-09-11.

Completed work:

- Replaced the previous Entware USB flash-drive deployment with a dedicated M.2 SATA SSD connected to the ASUS TUF-AX5400 through a compatible USB enclosure.
- Partitioned the SSD into a dedicated `ENTWARE` filesystem and a separate `ROUTER_DATA` filesystem.
- Migrated the existing Entware environment while preserving the original USB flash drive as rollback media during validation.
- Restored swap-backed service startup and validated both swap files after a clean router reboot.
- Validated automatic SSD mounts, active swap, Tailscale process/control-plane status, Unbound process state, direct DNSSEC resolution, and the recorded dnsmasq upstream configuration after reboot.
- Retained sanitized validation evidence suitable for public portfolio documentation.
- Documented the migration procedure and recovery considerations in `docs/ENTWARE-SSD-MIGRATION.md`.

The 2026-09-11 SSD artifact does not independently prove syslog-ng recovery, end-to-end mTLS collector delivery, every firewall/printer path, every exit-node traffic path, or long-term stability. Those behaviors remain tied to their own dated evidence or later validation.

The SSD is now the router's persistent Entware storage. The separate `ROUTER_DATA` partition is reserved for data and future storage workflows rather than being mixed with Entware service files.

## Current validation gate — stability observation

The 2026-09-11 deployment has passed controlled reboot validation for the checks recorded in the SSD migration artifact, and the repository validation suite passes for the current code/documentation state. Long-term stability is intentionally tracked separately from reboot success.

Current validation controls:

- GitHub Actions runs static, recovery, configuration, firewall, evidence-redaction, and log-retention checks.
- A dedicated CI job runs WAN-event-handler mock scenarios and the isolated install/rollback test.
- The current sanitized router-state snapshot is published in `evidence/ROUTER-STATE-2026-09-11.md`.
- A 14-day unchanged-state observation window runs from 2026-09-11 through 2026-09-25 under normal use.
- During the observation window, avoid intentional router reboots and major configuration changes unless recovery is required.
- At the end of the window, review uptime, RAM/swap, SSD mounts, Tailscale, Unbound/DNSSEC, syslog-ng, project health checks, and logs for OOM, crashes, unexpected restarts, WAN/DNS recovery failures, or storage errors.

The deployment must not be described as long-term stable until that observation is completed and the resulting evidence has been reviewed and sanitized.

### Work allowed during the no-touch observation window

The router configuration remains unchanged, but project work can continue away from the router:

- Improve repository structure, documentation, diagrams, threat-model notes, test methodology, and sanitized evidence organization.
- Prepare future DNS/filtering rules and test cases offline without deploying them to the router.
- Audit third-party aggregate blocklists offline (including `hululu1068/AdGuard-Rule`) as candidate inputs rather than trusted policy: identify upstream sources, remove irrelevant or high-risk entries, estimate false positives, and extract a small project-owned candidate set for later validation. Do not subscribe the reference router directly to a large third-party aggregate during the stability gate.
- Validate endpoint-side filtering on a Windows workstation without changing router services or policies.
- Test Zen as a system-level endpoint content filter with Chrome, including YouTube ad blocking, HTTPS/certificate behaviour, CPU/RAM impact, false positives, and browser compatibility.
- Confirm that endpoint filtering does not bypass the existing router DNS path. Router-side activity during this check must remain read-only, for example inspecting already-generated dnsmasq logs.
- If useful, compare Zen with a trial of AdGuard for Windows using the same test methodology. AdGuard DNS protection should remain disabled for this comparison so the existing router DNS architecture remains authoritative.
- Prepare, but do not yet deploy, the methodology for later mobile telemetry assessment.

These activities are intentionally separated from router configuration changes so they do not invalidate the unchanged-state stability observation.

## Planned endpoint filtering validation

Endpoint filtering is an optional defense-in-depth layer, not a replacement for router-side DNS controls.

Planned validation matrix:

- Existing router DNS/filtering only — baseline.
- Router DNS/filtering + Brave on supported endpoints.
- Router DNS/filtering + Zen on Windows/Chrome.
- Optional router DNS/filtering + AdGuard for Windows comparison if Zen does not provide sufficient coverage or if a controlled comparison is useful.

Record blocking effectiveness, YouTube behaviour, HTTPS compatibility, DNS-path preservation, false positives, CPU/RAM impact, and operational issues. Only validated results should be promoted into portfolio evidence.

## Planned mobile telemetry assessment

A later phase will assess residual mobile telemetry without restoring applications or services that were intentionally removed from the hardened/debloated phone.

- Treat the current hardened/debloated Xiaomi device as its own post-hardening case study.
- A second Xiaomi device may be assessed as an additional independent case study even if it uses a different model or OS version.
- Do not present different Xiaomi devices or OS versions as a strict before/after debloat experiment.
- Use controlled scenarios such as idle periods, reboot/startup, selected system-app use, and normal interactive use.
- Record relevant DNS destinations, request frequency, blocked destinations, and notable vendor/advertising/telemetry endpoints.
- Clearly document device/OS differences and methodological limitations.
- Publish only sanitized evidence.

Full telemetry/capture changes that require modifying router configuration are deferred until after the current stability observation window.

## Near-term — Personal cloud / automated file sync

- Create a workstation sync directory (for example `~/RouterCloud`) on Zorin OS.
- Implement incremental synchronization with `rsync` over SSH.
- Store synchronized data on the dedicated `ROUTER_DATA` filesystem, isolated from Entware and router-service files.
- Support secure remote synchronization through Tailscale without exposing file-sharing services to the public Internet.
- Automate synchronization with a systemd user timer and/or a filesystem-triggered workflow.
- Default to upload/copy semantics so accidental local deletion does not automatically remove the remote copy.
- Validate LAN and Tailscale transfers, interrupted-transfer recovery, router/workstation reboot behaviour, permissions, and unauthorized-access handling.
- Verify transferred-file integrity with SHA-256 and record measured throughput.
- Document synchronization, failure handling, recovery, and rollback procedures.
- Retain sanitized test evidence suitable for portfolio documentation.

Target end state: the SSD remains the router's persistent storage for Entware and related services while `ROUTER_DATA` provides a separate private cloud-like data area synchronized automatically from Zorin OS.

The synchronization feature must only be documented as **Completed and validated** after file synchronization, recovery, integrity, permissions, and reboot tests have actually been completed.

## Stability follow-up

- Keep the validated SSD/Entware deployment under normal operation and retain a later stability snapshot.
- Review logs for recurring Tailscale memory failures, WAN/DNS recovery errors, storage/mount failures, and unexpected service restarts.
- Publish only sanitized evidence; never publish raw router syslog or credentials.

## Post-observation router filtering work

After the unchanged-state stability gate is complete and its evidence is captured:

- Review candidate stronger DNS/content-filtering lists and policies prepared offline, including the curated candidate set derived from the third-party aggregate-list assessment.
- Baseline false positives before enabling stricter filtering broadly.
- Deploy changes incrementally with explicit rollback steps; do not make a large external aggregate list a single unreviewed point of policy.
- Re-run DNSSEC, resolution, firewall, service-health, and recovery validation after each material change.
- Capture sanitized before/after evidence without overstating what DNS-level filtering can block.

## Post-observation — severity-aware alerting and phone notifications

After the unchanged-state stability gate is complete and its evidence is captured:

- Keep full operational logs separate from actionable notifications so routine firewall drops, filtering events, and other expected noise do not generate phone alerts.
- Classify actionable events into at least `INFO`, `WARNING`, `CRITICAL`, and `RECOVERED` states.
- Reserve immediate phone notifications for sustained or high-impact failures such as repeated health-check failures, DNS/Unbound failure, Tailscale recovery failure, firewall-policy load failure, persistent WAN loss, SSD/Entware storage loss, filesystem errors, OOM/crash loops, unexpected reboot, or backup-integrity failure.
- Add persistence thresholds, deduplication, and per-event cooldowns so a transient failure or repeated identical log entry does not create alert storms.
- Emit a distinct `RECOVERED` notification when a previously active incident returns to a validated healthy state.
- Prefer alert evaluation and notification delivery on an external collector/NAS/workstation rather than adding unnecessary processing to the low-memory router.
- Evaluate a privacy-preserving phone notification path such as self-hosted ntfy or Gotify.
- Add an external heartbeat/dead-man check so complete router or WAN failure can still be detected when the router itself is unable to send an alert.
- Validate alert severity, false-positive rate, duplicate suppression, recovery notifications, and loss-of-router scenarios before describing the feature as production-ready.

Do not deploy router-side hooks, cron jobs, syslog changes, or other alerting changes during the active unchanged-state stability observation.

## Post-observation — off-router backup and reproducible recovery

Extend the existing project configuration backup/restore workflow after the stability gate:

- Keep the current integrity-checked project backup as the configuration/application recovery layer.
- Automatically copy completed backups away from the router-attached SSD to a trusted NAS or other independent system.
- Retain multiple dated backup generations and define an explicit retention policy.
- Encrypt off-router backups at rest and keep authentication material outside the public repository.
- Verify the archive sidecar checksum and internal `SHA256SUMS` manifest after transfer rather than treating a successful copy as sufficient.
- Add backup-result monitoring so a failed backup, failed transfer, or failed integrity check can become an actionable alert.
- Document a bootstrap procedure for a clean compatible ASUSWRT-Merlin/Entware installation that restores the project configuration without pretending to be a firmware-level bare-metal image.
- Test restore first in dry-run mode, then perform a controlled recovery drill with rollback and post-restore health validation.
- Record measured recovery time and the expected data/configuration loss window so later project maturity work can define evidence-backed RTO/RPO.
- Keep the router-attached SSD and the off-router copy as separate failure domains; neither should be described as sufficient on its own.

Target end state: a versioned, integrity-verified, encrypted off-router recovery path that complements the repository and existing `backup.sh`/`restore.sh` workflow.

## Phase 2 — dedicated x86 edge

- OPNsense on supported x86 hardware.
- VLAN 10 (trusted LAN), VLAN 20 (IoT), VLAN 30 (lab), and a management VLAN.
- Explicit inter-VLAN default deny and documented service exceptions.
- Configuration backup/restore drill and UPS-aware shutdown.

## Phase 3 — detection and response

- Suricata IDS first, IPS only after false-positive baselining.
- Wazuh agents/collector, indexer, dashboards, alert routing, and retention policy.
- TLS log transport with a managed CA and monitored delivery queue.
- Attack simulations mapped to MITRE ATT&CK and retained evidence.

## Phase 4 — engineering maturity

- Metrics for DNS latency/cache, VPN throughput, drops, CPU, RAM, temperature, and storage wear.
- Golden configuration, reproducible restore, and quarterly recovery exercises.
- Policy-as-code validation for Tailscale and OPNsense changes.
- Hardware/ISP failure tests, measured RTO/RPO, and a documented incident runbook.

The ASUS router can remain an access point or isolated secondary lab node after enforcement moves to OPNsense.
