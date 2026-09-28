# Roadmap

## Completed and validated — observability baseline

**Status: completed 2026-09-27.**

The first external observability baseline is live-validated on the reference
ASUS TUF-AX5400. Time-series storage, probes and visualization remain off the
512 MiB router. The validated path combines read-only SSH collection, scheduled
Traffic Analyzer import, VictoriaMetrics, Blackbox Exporter and Grafana.

The TUF-AX5400 required one model-specific collector adaptation because the
Broadcom `chanim_stats` output returned hexadecimal chanspec values rather than
a directly parseable decimal channel. The patch uses read-only `wl channel`
output for the primary channel.

The Fedora host passed a real reboot/persistence validation: system and user
monitoring units returned automatically, user linger was enabled, all HTTP
listeners remained loopback-only, the SSH scrape converged to `up=1`, and the
Traffic Analyzer timer imported the next completed hourly bucket.

SNMP was not required for this baseline.

See:
- [observability case study](asus-tuf-ax5400-observability-case-study.md)
- [sanitized live validation](../evidence/2026-09-27/observability-stack-validation.md)
- [reproducible monitoring files](../monitoring/README.md)

The initial Grafana alerting baseline is also live-validated: collector loss and
stale telemetry reached firing state in a controlled Fedora-only fault test,
recovered after service restoration, and the WAN no-data policy was corrected
so missing collector data does not masquerade as WAN-down evidence.

The centralized syslog-ng path was subsequently live-validated over Tailscale
with mutual TLS, source-restricted firewalld policy, an end-to-end unique
message, and a short collector-outage recovery test that delivered 3/3 queued
messages after collector restoration.

**Next execution focus:** finish the remaining issue #108 acceptance work:
bounded storage/retention observation, rollback/uninstall validation and
correlation of the hard-coded external classic-DNS LAN interception path. The
Pi-hole-visible collector, Alloy/Loki backend, Grafana dashboard, Fedora reboot
persistence and two-client main-LAN distinguishability are already
live-validated. Issue #68 remains the separate encrypted-DNS coverage
assessment. No resolver-policy change is implied by the analytics work.

## In progress — Network DNS Visibility / Client Activity Analytics

Issue #108 is tracked in [Network DNS Visibility / Client Activity Analytics](network-dns-visibility-client-activity-analytics.md).

The implemented baseline provides domain-level DNS visibility by time and
client for the Pi-hole-filtered main-LAN path. Pi-hole FTL query history is the
primary source; a bounded read-only Fedora collector feeds local
Alloy -> Loki -> the existing Grafana instance. Indexing, retention and
visualization remain off-router.

The existing syslog-ng + Tailscale + mTLS path remains authoritative for system
logs and may later provide supplemental evidence for dnsmasq interception paths;
it is not the primary Pi-hole analytics transport.

The 2026-09-28 live validation covered API preflight, bounded collection,
transport-outage recovery, Alloy/Loki ingestion, dashboarding, Fedora reboot
persistence and two controlled main-LAN clients. A controlled Tailscale test
also confirmed that the current `Tailscale -> dnsmasq -> Unbound` classic-DNS
path is absent from Pi-hole history. The remaining classic-DNS coverage target
is the hard-coded external LAN interception path. The module excludes HTTPS
MITM, full URL capture and publication of real household browsing data.

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

A later read-only live checkpoint was retained on 2026-09-25 with both SSD filesystems, swap, core services, DNSSEC and the project health check healthy; see [the sanitized checkpoint](../evidence/2026-09-25/router-live-checkpoint.md). This is a point-in-time normal-operation checkpoint, not a replacement for explicit cold-start acceptance.

- Keep the validated SSD/Entware deployment under normal operation and retain later bounded stability snapshots.
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

## Completed post-firmware revalidation — 2026-09-27

The GNUton `3004.388.11_1-gnuton1_tuf` upgrade changed the platform baseline. Existing 2026-09-22 AUDIT-02/03 packet evidence remains valid for that earlier firmware, but current-firmware claims should be refreshed deliberately rather than inferred from successful smoke tests.

Current order:

1. **Completed — management authorization negative test:** a distinct unauthorized Windows tailnet client retained Tailscale peer reachability but could not establish TCP/8443. Five client SYN packets were correlated with a source-specific counter-only firewall rule before the unchanged production deny tail; cleanup and the final health check passed. See [sanitized evidence](../evidence/2026-09-23/unauthorized-tailnet-management-denial.md).
2. **Completed — exit-node datapath revalidation:** on GNUton `3004.388.11_1-gnuton1_tuf`, a controlled fixed-ID ICMP flow was correlated on `tailscale0` before NAT and `ppp0` after source translation, with 5/5 client replies and a clean final health check. See [sanitized evidence](../evidence/2026-09-23/audit-02-post-firmware-exit-node-revalidation.md).
3. **Completed 2026-09-27 — classic-DNS current-firmware revalidation:** controlled Fedora UDP/53 and TCP/53 probes were correlated through `tailscale0 -> EDGE_TS_PREROUTING -> dnsmasq -> Unbound`, with exact managed redirect-counter deltas and matching loopback resolver traffic. See [sanitized evidence](../evidence/2026-09-27/audit-03-current-firmware-dns-datapath-revalidation.md).
4. **Completed 2026-09-27 — reboot/normal-use acceptance:** #66 recorded three clean startup cycles after the pre-Entware swap-order correction, and #65 completed the Diversion Large normal-use acceptance criteria. The Android exit-node public-IP check was also repeated under #67.

These revalidations should not introduce broader policy changes. Keep them as bounded measurements with current backups, explicit cleanup for any temporary instrumentation, and sanitized evidence.

## Historical filtering work and current Pi-hole follow-up

After the completed unchanged-state observation, stronger Diversion filtering was evaluated and the main-LAN path was subsequently migrated to Pi-hole on 2026-09-28. The retained engineering rules now apply to Pi-hole/Gravity policy changes rather than to a pending Diversion expansion:

- review candidate lists/policies offline and avoid making a large external aggregate list a single unreviewed point of policy;
- baseline false positives before broader filtering changes;
- deploy list/policy changes incrementally with explicit rollback;
- re-run DNSSEC, resolution, Pi-hole blocking, DHCP/local-name, firewall, service-health and reboot validation after material resolver-policy changes;
- capture sanitized before/after evidence without overstating what DNS-level filtering can block;
- keep issue #108 analytics read-only and separate from filtering-policy changes so observability work does not silently change enforcement.

## Completed Diversion Large normal-use acceptance

**Status: completed 2026-09-27.** The current `Large + snbAdSupport=no` state completed the defined normal-use acceptance gate. The retained criteria are listed below as the basis of that acceptance:

- at least five representative normal-use sessions across multiple days;
- at least three clean router startup/power-on cycles with DNS and core-service checks passing;
- no unresolved critical false positives affecting required sites, applications or local services;
- no health-check failures attributable to the filtering policy;
- representative LAN and Android-over-Tailscale classic-DNS checks remain functional;
- a normal Diversion list refresh/update completes without breaking the validated resolver path;
- RAM/swap behavior shows no sustained abnormal growth relative to the pre-change baseline;
- rollback to the previous policy remains documented and practical.

The 2026-09-27 acceptance evidence records completion of these criteria. Future list/profile changes require a new bounded validation rather than inheriting this result automatically. See [issue-65 acceptance evidence](../evidence/2026-09-27/issue-65-diversion-large-normal-use-acceptance.md).

## Completed and adopted — Diversion to Pi-hole on-router migration

**Status: main-LAN DHCP cutover completed and reboot-validated 2026-09-28.**

Issue #80 progressed from staged pilot to an adopted reference main-LAN DNS-filtering path.

Final validated design:

```text
DHCP-managed main-LAN clients
        |
        v
Pi-hole FTL on dedicated LAN alias :53
        |
        v
Unbound 127.0.0.1:53535
        |
        v
Internet

firmware dnsmasq
        +-- DHCP
        +-- local/reverse names
        +-- existing classic-DNS interception endpoint
        |
        v
Unbound 127.0.0.1:53535
```

Completed work includes:

- staged single-client validation and corrected A/B latency testing;
- OISD source parity comparison: Pi-hole retained 244,128 normalized domains while Diversion retained 244,126 because its essential allowlist intentionally excluded two OISD entries through their parent domains;
- Pi-hole SQLite query-history validation and synthetic rate-limit observation;
- main-LAN DHCP cutover that advertises only Pi-hole;
- conditional reverse DNS through firmware dnsmasq for active DHCP leases;
- removal of uiDivStats, Diversion, Stubby/DNS Privacy and inactive NextDNS hook logic;
- discovery of a post-mount regression that left swap inactive and caused Tailscale to fail with a Go-runtime OOM;
- restoration of explicit per-volume pre-Entware swap activation;
- final clean reboot with both swap files, Tailscale, Pi-hole, Unbound, DHCP DNS, blocking and DNSSEC behavior restored automatically.

The final case study deliberately keeps one boundary explicit: the existing project classic-DNS interception path for arbitrary external resolver destinations, and the historical Tailscale classic-DNS redirect, still terminate at firmware dnsmasq before Unbound. The main-LAN DHCP path is Pi-hole-filtered, but universal Pi-hole filtering of those interception paths is not claimed without a separate datapath change and revalidation.

See:
- [final Pi-hole migration case study](pi-hole-on-router-case-study.md)
- [case-study plan and acceptance history](pi-hole-on-router-case-study-plan.md)
- [single-client pilot evidence](../evidence/2026-09-28/pi-hole-single-client-pilot-validation.md)
- [main-LAN cutover and final reboot evidence](../evidence/2026-09-28/pi-hole-main-lan-cutover-validation.md)

Follow-up work under #108 now focuses on the remaining acceptance gaps:
storage/retention observation, rollback/uninstall validation and correlation of
the hard-coded external LAN classic-DNS interception path. The Pi-hole-visible
Fedora analytics baseline and the tested Tailscale classic-DNS coverage boundary
are already live-validated. The separate #68 encrypted-DNS bypass assessment
continues independently. Any decision to move interception paths behind Pi-hole
remains a later datapath change requiring its own rollback and live
revalidation. None of these follow-ups invalidate the completed main-LAN DHCP
migration.

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

## Completed baseline — off-router backup and reproducible recovery

**Baseline completed 2026-09-27 under #100.** The project now has:

- a sanitized router rebuild inventory;
- a separate private native ASUS/Merlin settings export encrypted off-router;
- a verified off-router project backup and sidecar checksum;
- internal payload-manifest validation;
- `restore.sh --dry-run` validation;
- a successful alternate-root clean-room restore;
- byte-for-byte JFFS/opt content comparison and permission-mode comparison;
- explicit Unbound runtime ownership reconstruction;
- review-only handling for addon-managed `post-mount`, including safe behavior
  for older backups that stored it under the live JFFS path.

See [router disaster recovery](router-disaster-recovery.md) and the
[clean-room restore evidence](../evidence/2026-09-27/issue-100-dr-cleanroom-restore-validation.md).

Remaining recovery-maturity work:

- Extend clean-room router recovery to the post-2026-09-28 Pi-hole state: reinstall/rebuild Pi-hole/FTL, recreate the dedicated LAN alias/startup ordering, reconstruct reviewed filtering inputs/Gravity, and validate DHCP-only-Pi-hole, Pi-hole -> Unbound, DNSSEC-negative, blocking and reverse-DNS behavior.
- Decide what minimal Pi-hole configuration belongs in the project backup versus a separately protected private recovery artifact; do not treat the live query-history database as a required gateway-recovery payload.
- Automate copying completed project backups to an independent system without making the router-attached SSD the only recovery location.
- Retain multiple dated generations and define explicit retention/rotation.
- Add backup-result monitoring so failed creation, transfer or integrity verification becomes observable.
- Extend the documented bootstrap sequence for a clean compatible Asuswrt-Merlin/Entware installation as future recovery testing justifies it.
- Measure recovery time and expected configuration-loss window in a future timed drill before defining evidence-backed RTO/RPO.
- Continue to keep router-attached storage and off-router recovery copies as separate failure domains.

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
