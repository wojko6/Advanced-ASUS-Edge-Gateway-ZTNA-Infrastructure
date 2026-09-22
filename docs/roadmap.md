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

## Completed validation observation — 2026-09-11 to 2026-09-22

The 2026-09-11 deployment passed controlled reboot validation for the checks recorded in the SSD migration artifact, and the repository validation suite passes for the current code/documentation state. A subsequent unchanged-state observation ran with the router continuously powered 24/7 from **2026-09-11 through 2026-09-22**.

Validation controls and closure:

- GitHub Actions runs static, recovery, configuration, firewall, evidence-redaction, and log-retention checks.
- A dedicated CI job runs WAN-event-handler mock scenarios and the isolated install/rollback test.
- The current sanitized router-state snapshot is published in `evidence/ROUTER-STATE-2026-09-11.md`.
- The originally planned observation end date was 2026-09-25, but the unchanged-state period was deliberately closed on 2026-09-22 to begin the next controlled project phase.
- The closing read-only health check reported `0 failure(s), 0 warning(s)` and `HEALTHCHECK_RC=0`.
- At closure, Entware/SSD, swap, Tailscale, Unbound/DNSSEC, dnsmasq integration, syslog-ng and project firewall chains were healthy, and the inspected syslog contained no matching OOM, crash, filesystem-I/O or read-only-filesystem errors.

The correct claim is therefore a successful continuous 2026-09-11 → 2026-09-22 observation, not a completed 14-day endurance test and not proof of indefinite long-term stability.

### Work that was allowed during the no-touch observation window

During that completed no-touch observation window, the router configuration remained unchanged while project work continued away from the router:

- Improve repository structure, documentation, diagrams, threat-model notes, test methodology, and sanitized evidence organization.
- Prepare future DNS/filtering rules and test cases offline without deploying them to the router.
- Audit third-party aggregate blocklists offline (including `hululu1068/AdGuard-Rule`) as candidate inputs rather than trusted policy: identify upstream sources, remove irrelevant or high-risk entries, estimate false positives, and extract a small project-owned candidate set for later validation. The reference router was not subscribed directly to a large third-party aggregate during the observation.
- Validate endpoint-side filtering on a Windows workstation without changing router services or policies.
- Test Zen as a system-level endpoint content filter with Chrome, including YouTube ad blocking, HTTPS/certificate behaviour, CPU/RAM impact, false positives, and browser compatibility.
- Confirm that endpoint filtering does not bypass the existing router DNS path. Router-side activity during this check must remain read-only, for example inspecting already-generated dnsmasq logs.
- If useful, compare Zen with a trial of AdGuard for Windows using the same test methodology. AdGuard DNS protection should remain disabled for this comparison so the existing router DNS architecture remains authoritative.
- Prepare, but do not yet deploy, the methodology for later mobile telemetry assessment.

These activities were intentionally separated from router configuration changes so they did not invalidate the unchanged-state stability observation.

## Endpoint filtering validation status

Endpoint filtering is an optional defense-in-depth layer, not a replacement for router-side DNS controls.

Completed evidence now includes the Windows Zen validation and the Fedora/GNOME Zen proxy-integration case study. Those results are endpoint-specific and do not prove equivalent router-side filtering. AdGuard for Windows remains an optional comparison rather than a completed result.

Reference validation matrix:

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

Full telemetry/capture changes that require modifying router configuration may now proceed as controlled post-observation work.

## Near-term — Personal cloud / automated file sync

- Create a workstation sync directory (for example `~/RouterCloud`) on Fedora Workstation.
- Implement incremental synchronization with `rsync` over SSH.
- Store synchronized data on the dedicated `ROUTER_DATA` filesystem, isolated from Entware and router-service files.
- Support secure remote synchronization through Tailscale without exposing file-sharing services to the public Internet.
- Automate synchronization with a systemd user timer and/or a filesystem-triggered workflow.
- Default to upload/copy semantics so accidental local deletion does not automatically remove the remote copy.
- Validate LAN and Tailscale transfers, interrupted-transfer recovery, router/workstation reboot behaviour, permissions, and unauthorized-access handling.
- Verify transferred-file integrity with SHA-256 and record measured throughput.
- Document synchronization, failure handling, recovery, and rollback procedures.
- Retain sanitized test evidence suitable for portfolio documentation.

Target end state: the SSD remains the router's persistent storage for Entware and related services while `ROUTER_DATA` provides a separate private cloud-like data area synchronized automatically from Fedora Workstation.

The synchronization feature must only be documented as **Completed and validated** after file synchronization, recovery, integrity, permissions, and reboot tests have actually been completed.

## Stability follow-up

- Keep the validated SSD/Entware deployment under normal operation and retain a later stability snapshot.
- Review logs for recurring Tailscale memory failures, WAN/DNS recovery errors, storage/mount failures, and unexpected service restarts.
- Publish only sanitized evidence; never publish raw router syslog or credentials.

## Resolved finding — LAN DNS policy bypass and DoT follow-up

Read-only validation during the completed stability observation identified a DNS-enforcement gap. That specific classic-DNS bypass and the direct LAN DoT follow-up were both addressed through controlled maintenance on 2026-09-22.

Historical finding and closure:

- At discovery time, ASUS DNS Director was disabled (`dnsfilter_enable_x=0`) and the project firewall redirected classic TCP/UDP 53 only on the validated Tailscale path, not for ordinary LAN/Wi-Fi clients.
- A Fedora LAN client successfully resolved through an explicitly selected external resolver, proving a real classic-DNS bypass on the normal LAN path.
- A temporary `br0` NAT prototype then intercepted controlled UDP/53 and TCP/53 traffic and was removed cleanly after validation.
- **Production classic-DNS closure:** PR #57 introduced opt-in `EDGE_ENFORCE_LAN_DNS` and the managed `EDGE_LAN_DNS_PREROUTING` chain. The reference router was deployed with `EDGE_ENFORCE_LAN_DNS=1`; the live health check remained clean and controlled Fedora external UDP/TCP 53 queries incremented the production redirect counters.
- A separate Fedora baseline confirmed that direct TLS to `8.8.8.8:853` was reachable before any DoT control, proving a direct LAN DNS-over-TLS bypass of the classic port-53 policy.
- **DoT prototype A/B/A:** a temporary `br0` FORWARD rule rejected TCP/853 with `tcp-reset`, recorded the controlled packet, and rollback restored successful TLS/853 connectivity.
- **Production DoT closure:** PR #58 introduced opt-in `EDGE_BLOCK_LAN_DOT` and the managed `EDGE_LAN_DOT_FORWARD` chain. The reference router was deployed with `EDGE_BLOCK_LAN_DOT=1`; a controlled Fedora production connection to `8.8.8.8:853` was rejected, the managed rule recorded 1 packet / 60 bytes, and the post-test health check remained clean.
- The completed claims are deliberately scoped: classic IPv4 LAN TCP/UDP 53 enforcement and direct IPv4 LAN DoT/TCP 853 blocking are live validated. They do not establish control over DoH/HTTPS, DoQ/QUIC, VPN-carried DNS, IPv6 resolver paths, application-specific encrypted DNS, or equivalent traffic entering through other interfaces.
- **Next DNS-control milestone:** perform read-only assessment of DoH/HTTPS and DoQ/QUIC first, then design any enforcement only after compatibility, false-positive, rollback, and protocol-identification limits are understood. IPv6 and VPN-carried resolver paths remain separate assessment items.

## Post-observation router filtering work

After the completed unchanged-state observation:

- Review candidate stronger DNS/content-filtering lists and policies prepared offline, including the curated candidate set derived from the third-party aggregate-list assessment.
- Baseline false positives before enabling stricter filtering broadly.
- Deploy changes incrementally with explicit rollback steps; do not make a large external aggregate list a single unreviewed point of policy.
- Re-run DNSSEC, resolution, firewall, service-health, and recovery validation after each material change.
- Capture sanitized before/after evidence without overstating what DNS-level filtering can block.

## Diversion Large normal-use acceptance criteria

The current `Large + snbAdSupport=no` state is a controlled post-test configuration, not yet a permanent validated baseline. Promote it only after the following evidence is recorded:

- at least five representative normal-use sessions across multiple days;
- at least three clean router startup/power-on cycles with DNS and core-service checks passing;
- no unresolved critical false positives affecting required sites, applications or local services;
- no health-check failures attributable to the filtering policy;
- representative LAN and Android-over-Tailscale classic-DNS checks remain functional;
- a normal Diversion list refresh/update completes without breaking the validated resolver path;
- RAM/swap behavior shows no sustained abnormal growth relative to the pre-change baseline;
- rollback to the previous policy remains documented and practical.

If any criterion fails, keep `Large` in evaluation, record the failure and either tune the policy or revert before describing it as the accepted baseline.

## Post-observation idea — Pi-hole + Unbound DNS filtering migration

**Status: idea / design candidate only — not deployed.**

The current Diversion-based filtering is considered insufficient for some real-world mobile application flows, especially Android applications that render web content through WebView or browser Custom Tabs instead of a full browser session with its own strong content blocker. The purpose of this idea is therefore broader than improving browser ad blocking: it is to improve network-wide filtering for applications that do not provide an effective in-app blocker.

The preferred target architecture is:

```text
LAN / authorized Tailscale clients
              |
              v
        Pi-hole FTL :53
          /        \
         /          \
        v            v
Unbound 127.0.0.1:53535   firmware dnsmasq :8053
recursive DNS + DNSSEC    DHCP / local names / reverse DNS
```

Design principles for this migration:

- Treat Pi-hole as a potential **replacement for Diversion**, not an additional parallel filtering layer.
- Keep Unbound as the recursive validating resolver and preserve DNSSEC validation.
- Keep firmware dnsmasq for DHCP, local naming and reverse-DNS duties after moving it away from port 53.
- Reuse the existing project-owned Tailscale/firewall policy so only authorized remote clients can use the router DNS service.
- Keep the Pi-hole administrative UI restricted to trusted LAN management and explicitly authorized Tailscale administration sources; do not expose it to WAN or broad remote access.
- Use Pi-hole query logging, per-client statistics, groups and API data to improve DNS observability and evidence quality.
- Create a dedicated Android/mobile policy group only after baseline measurements show which advertising, tracking and telemetry domains are actually observed.
- Preserve the existing privacy boundary: do not publish raw browsing history, private hostnames, client identifiers or unsanitized DNS logs.
- Do not subscribe blindly to very large third-party blocklists. Prefer curated, attributable sources and small evidence-backed additions with rollback.
- Do not claim that Pi-hole can block same-origin advertising, encrypted resolver bypasses, or all in-app advertising; WebView/Custom Tabs benefit must be measured rather than assumed.

A key use case is remote mobile protection:

```text
home Wi-Fi:
Android -> ASUS/Pi-hole -> Unbound

LTE/5G:
Android -> Tailscale -> ASUS/Pi-hole -> Unbound
```

This should allow the same project-owned DNS policy to protect Android applications both at home and away from the LAN, provided the measured client DNS path actually traverses the router. The completed 2026-09-22 AUDIT-03 validation provides the classic-DNS baseline for Fedora and Android; any Pi-hole migration must repeat the affected datapath checks before equivalent claims are made for the new listener architecture.

### Required migration/acceptance plan

The unchanged-state observation was closed on 2026-09-22 after continuous 24/7 operation from 2026-09-11 through 2026-09-22. Pi-hole work may now move from repository-only design into a controlled maintenance/test phase.

Before deployment:

Implementation prerequisites:

- confirm that the selected Pi-hole/FTL build is supportable on the router CPU and Entware environment before treating it as an implementation candidate;
- measure the current RAM/swap and storage-write baseline, then define a resource and retention budget for FTL databases/query logging;
- document exact listener ownership and cutover order for Pi-hole `:53`, firmware dnsmasq `:8053`, and Unbound `:53535` so two services never compete for the same socket;
- implement a rollback path that restores the current Diversion + dnsmasq + Unbound arrangement without depending on a functioning Pi-hole service;
- define Pi-hole/FTL update ownership and maintenance procedure rather than introducing package mutation into the boot path;
- define explicit firewall and administrative-UI exposure rules plus negative tests so the UI cannot become reachable from WAN or broadly from the tailnet.

1. Capture a fresh pre-change health/evidence snapshot and back up the current Diversion/dnsmasq/Unbound state.
2. Create a dedicated feature branch and implement Pi-hole integration, health checks, rollback and configuration validation before deployment.
3. Measure a Diversion baseline using representative Android app, WebView/Custom Tab, browser and telemetry scenarios.
4. Stage Pi-hole without destroying the rollback path.
5. Move firmware dnsmasq away from port 53 while preserving DHCP/local-name/reverse-DNS behavior.
6. Bind Pi-hole to the intended LAN/Tailscale interfaces and forward upstream resolution to Unbound on loopback:53535.
7. Disable Diversion only after Pi-hole has demonstrated equivalent or better DNS-layer coverage.
8. Validate LAN DNS, Android WebView/Custom Tabs, LTE/5G over Tailscale, DNSSEC, reverse DNS, WAN reconnect, reboot recovery, Gravity updates, RAM/swap behavior, firewall exposure and administrative UI access.
9. Compare before/after blocking effectiveness and false positives rather than accepting the migration on subjective appearance alone.
10. Validate the accepted Pi-hole design across several normal-use sessions and multiple full router power-on/startup cycles before promoting it into the validated baseline; a continuous 7-14 day unchanged-state gate is not required for this deployment because the reference router is normally powered only for part of each day.

Primary success criterion: improve advertising/tracking suppression in applications without strong browser-native blockers while preserving DNSSEC, local-network functionality, Tailscale policy, recoverability and an auditable DNS datapath.

Post-migration acceptance should emphasize repeated successful cold/startup cycles, normal daily-use sessions, WAN reconnect handling, Gravity maintenance, RAM/swap behavior and clean health checks rather than continuous multi-day uptime.

## Post-observation — severity-aware alerting and phone notifications

After the completed unchanged-state observation:

- Keep full operational logs separate from actionable notifications so routine firewall drops, filtering events, and other expected noise do not generate phone alerts.
- Classify actionable events into at least `INFO`, `WARNING`, `CRITICAL`, and `RECOVERED` states.
- Reserve immediate phone notifications for sustained or high-impact failures such as repeated health-check failures, DNS/Unbound failure, Tailscale recovery failure, firewall-policy load failure, persistent WAN loss, SSD/Entware storage loss, filesystem errors, OOM/crash loops, unexpected reboot, or backup-integrity failure.
- Add persistence thresholds, deduplication, and per-event cooldowns so a transient failure or repeated identical log entry does not create alert storms.
- Emit a distinct `RECOVERED` notification when a previously active incident returns to a validated healthy state.
- Prefer alert evaluation and notification delivery on an external collector/NAS/workstation rather than adding unnecessary processing to the low-memory router.
- Evaluate a privacy-preserving phone notification path such as self-hosted ntfy or Gotify.
- Add an external heartbeat/dead-man check so complete router or WAN failure can still be detected when the router itself is unable to send an alert.
- Validate alert severity, false-positive rate, duplicate suppression, recovery notifications, and loss-of-router scenarios before describing the feature as production-ready.

Router-side alerting changes may now be tested only as deliberate maintenance changes with rollback and post-change validation.

## Post-observation — off-router backup and reproducible recovery

Extend the existing project configuration backup/restore workflow in the post-observation phase:

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
