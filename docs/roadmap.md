# Roadmap

## Near-term — SSD Migration + Personal Cloud / Automated File Sync

- Replace the current router USB flash drive with a dedicated SSD connected to the ASUS TUF-AX5400 through a compatible M.2 SATA-to-USB enclosure.
- Migrate the existing Entware environment, swap usage, logs, add-on data, and other required persistent router storage from the current USB flash drive to the SSD.
- Preserve the current router configuration and service behaviour during the migration, with a documented rollback path to the original USB flash drive.
- Reserve a separate directory on the SSD for private user data, isolated from Entware and router-service files.
- Create a workstation sync directory (for example `~/RouterCloud`) on Zorin OS.
- Implement incremental synchronization with `rsync` over SSH.
- Support secure remote synchronization through Tailscale without exposing file-sharing services to the public Internet.
- Automate synchronization with a systemd user timer and/or a filesystem-triggered workflow.
- Default to upload/copy semantics so accidental local deletion does not automatically remove the remote copy.
- Validate LAN and Tailscale transfers, interrupted-transfer recovery, router/workstation reboot behaviour, permissions, and unauthorized-access handling.
- Verify transferred-file integrity with SHA-256 and record measured throughput.
- Validate Entware and router services after migration, including startup/autostart and storage mounts.
- Document the SSD migration procedure, synchronization workflow, failure handling, recovery, and rollback procedure.
- Retain sanitized test evidence suitable for portfolio documentation.

Target end state: the SSD becomes the router's persistent USB storage for Entware and related services, while also providing a separate private cloud-like data area synchronized automatically from Zorin OS.

The feature must only be documented as **Completed and validated** after the storage migration, service validation, file synchronization, recovery, and integrity tests have actually been completed.

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
