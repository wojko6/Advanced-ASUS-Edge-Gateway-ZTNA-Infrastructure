# Roadmap

## Completed and validated — SSD migration

The persistent router storage migration was completed and reboot-validated on 2026-09-11.

Completed work:

- Replaced the previous Entware USB flash-drive deployment with a dedicated M.2 SATA SSD connected to the ASUS TUF-AX5400 through a compatible USB enclosure.
- Partitioned the SSD into a dedicated `ENTWARE` filesystem and a separate `ROUTER_DATA` filesystem.
- Migrated the existing Entware environment while preserving the original USB flash drive as rollback media during validation.
- Restored swap-backed service startup and validated both swap files after a clean router reboot.
- Validated automatic storage mounts and the startup of Tailscale, Unbound, dnsmasq integration, syslog-ng, and project firewall controls.
- Confirmed direct Unbound DNS resolution with DNSSEC validation after reboot.
- Retained sanitized validation evidence suitable for public portfolio documentation.
- Documented the migration procedure and recovery considerations in `docs/ENTWARE-SSD-MIGRATION.md`.

The SSD is now the router's persistent Entware storage. The separate `ROUTER_DATA` partition is reserved for data and future storage workflows rather than being mixed with Entware service files.

## Current validation gate — stability observation

The 2026-09-11 deployment has passed controlled reboot validation, the project health check, and the repository validation suite. Long-term stability is intentionally tracked separately from reboot success.

Current validation controls:

- GitHub Actions runs static, recovery, configuration, firewall, evidence-redaction, and log-retention checks.
- A dedicated CI job runs WAN-event-handler mock scenarios and the isolated install/rollback test.
- The current sanitized router-state snapshot is published in `evidence/ROUTER-STATE-2026-09-11.md`.
- A 14-day unchanged-state observation window runs from 2026-09-11 through 2026-09-25 under normal use.
- During the observation window, avoid intentional router reboots and major configuration changes unless recovery is required.
- At the end of the window, review uptime, RAM/swap, SSD mounts, Tailscale, Unbound/DNSSEC, syslog-ng, project health checks, and logs for OOM, crashes, unexpected restarts, WAN/DNS recovery failures, or storage errors.

The deployment must not be described as long-term stable until that observation is completed and the resulting evidence has been reviewed and sanitized.

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
