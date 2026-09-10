# Roadmap

## Near-term — Personal Cloud / Automated File Sync

- Temporarily attach a dedicated USB SSD to the ASUS TUF-AX5400 and use it as private file storage.
- Create a workstation sync directory (for example `~/RouterCloud`) on Zorin OS.
- Implement incremental synchronization with `rsync` over SSH.
- Support secure remote synchronization through Tailscale without exposing file-sharing services to the public Internet.
- Automate synchronization with a systemd user timer or filesystem-triggered workflow.
- Default to upload/copy semantics so accidental local deletion does not automatically remove the remote copy.
- Validate LAN and Tailscale transfers, interrupted-transfer recovery, router/workstation reboot behaviour, permissions, and unauthorized-access handling.
- Verify transferred-file integrity with SHA-256 and record measured throughput.
- Document deployment and rollback procedures and retain sanitized test evidence.
- After validation, the temporary SSD may be removed and the router returned to its current Entware USB-storage arrangement.

Target documentation status after successful testing: **Completed and validated — currently not active**. This status must only be used after the implementation and validation steps above have actually been completed.

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
