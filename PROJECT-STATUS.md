# Project status

**Status date:** 2026-09-29

**Latest live router checkpoint:** 2026-09-28

**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin

**Current phase:** the deferred Grafana GitHub/CI dashboard work is complete and source-controlled; execute the short post-audit hardening round (#127, #128, #130), then return to the bounded remaining #108 retention/storage, rollback/uninstall and LAN interception-correlation gaps.

## Executive status

This status document was reconciled on 2026-09-29. The earlier post-firmware validation set is complete: current-firmware classic DNS, the historical Diversion Large acceptance, clean startup/persistence, Android exit-node behavior, and the source-controlled canonical architecture diagrams all have their required evidence. On 2026-09-27, issue #100 completed the router disaster-recovery baseline with a sanitized rebuild inventory, private encrypted NVRAM/settings export, verified off-router project backup, restore dry-run, clean-room restore, Unbound ownership reconstruction proof, and final review-only handling for addon-managed `post-mount`. The external observability baseline was also implemented and reboot-validated with read-only SSH collection, Traffic Analyzer history import, VictoriaMetrics, Blackbox Exporter and Grafana kept off-router.

The centralized logging path is now also live-validated: router syslog-ng forwards the Asuswrt log over Tailscale and mutually authenticated TLS to the Fedora collector, with source-restricted firewall policy and successful short-outage recovery (3/3 test messages delivered after collector restoration). Grafana 13 uses its native Polish interface option; the project dashboard remains explicitly localized in JSON because application language settings do not translate project-owned panel content.

On 2026-09-28 the Fedora Grafana instance was extended with the read-only GitHub datasource plus Polystat and Business Charts plugins. On 2026-09-29 the deferred `ASUS Edge Gateway — Engineering / CI` work was completed: merged-PR and recent-commit tables, final layout cleanup and a seven-signal Polystat infrastructure-health overview were added and live-checked. The dashboard is now source-controlled as a Grafana v2 resource under `monitoring/grafana/dashboards/`. Business Charts remains installed but optional and unused by this dashboard.

The reference deployment is operational. The unchanged-state observation was closed on 2026-09-22 after continuous 24/7 powered operation from 2026-09-11 through 2026-09-22. The originally planned 14-day window through 2026-09-25 was ended early, so the project does not claim a completed 14-day endurance test.

On 2026-09-23 the reference router was updated to GNUton `3004.388.11_1-gnuton1_tuf`. The project `v2.1.4-dev` scripts were deployed from source revision `de1cf10`, and a later private configuration change limited tailnet administration to the Fedora workstation and Android phone. A same-day reboot and bounded router/workstation/phone checks passed. The previously outstanding negative management-access check was then completed from a distinct unauthorized Windows tailnet client and published as sanitized live evidence; see the [dated worklog](docs/worklog/2026-09-23.md) and [negative-management validation](evidence/2026-09-23/unauthorized-tailnet-management-denial.md).

The project currently has a validated SSD-backed Entware deployment, Tailscale-based remote access and exit-node capability, Pi-hole main-LAN filtering, Unbound/DNSSEC integration, firmware dnsmasq for DHCP/local naming and existing interception paths, syslog-ng logging, project-owned least-privilege firewall chains, recovery tooling, health checks, evidence collection, external observability and automated repository validation.

The stability observation deliberately separated a successful point-in-time deployment from a broader stability claim. During the completed 2026-09-11 → 2026-09-22 window the router remained continuously powered and unchanged. Post-observation changes may now proceed as controlled maintenance with backup, rollback and explicit validation.

## 2026-09-28 Pi-hole main-LAN migration

The reference main LAN now uses Pi-hole running directly on the ASUS router through Entware as its DHCP-advertised DNS-filtering service. Unbound remains the validating upstream resolver, while firmware dnsmasq remains responsible for DHCP, local/reverse naming and the existing project classic-DNS interception endpoint.

The migration was staged from the previously accepted Diversion baseline. The controlled work validated a dedicated Pi-hole listener, single-client query history, DNSSEC behavior through Unbound, OISD blocking-list parity, corrected local A/B latency measurements, normal-use query statistics, DHCP cutover and reverse DNS. After the cutover, uiDivStats, Diversion, ASUS DNS Privacy/Stubby and inactive NextDNS hook logic were removed from the active stack.

An intermediate reboot exposed a real recovery fault: both SSD swap files existed but the current `post-mount` hook no longer executed `swapon`. Tailscale therefore failed to start and the Go runtime reported an out-of-memory heap-arena allocation failure. Manual swap activation immediately restored Tailscale. The hook was corrected to activate each mounted `myswap.swp` before the AMTM Entware startup path, and the next clean reboot returned both swap files, Tailscale, Pi-hole, Unbound and the main-LAN DHCP DNS policy automatically.

The final checkpoint observed approximately 128 MiB memory available; Pi-hole FTL was about 10 MiB RSS, Unbound about 17 MiB RSS and tailscaled about 37 MiB RSS, with 0 kB process swap for all three at that point in time.

The claim remains bounded: DHCP-managed main-LAN clients use Pi-hole, but the existing firewall interception of arbitrary external classic DNS and the historical Tailscale redirect still terminate at firmware dnsmasq before Unbound. Those paths require separate revalidation if they are moved behind Pi-hole.

### Pi-hole-visible DNS activity analytics status

Issue #108 Phase 0 passed against the deployed Pi-hole v6 API. The preflight
validated the required query schema, authenticated read-only access through a
Fedora loopback SSH forward, bounded RAM/disk read cost and the RAM-versus-disk
cursor edge case.

The bounded Fedora collector is live-validated, including restart/outage
recovery. The local Alloy/Loki path and the first Grafana DNS dashboard are also
live-validated. A bounded equality check matched 11,116 events in the private
spool to 11,116 Loki events, and a label audit confirmed that domain/client
values are not persistent Loki labels. The dashboard now exposes blocked,
cache, forwarded and unfinished status, latency, top activity and an explicit
coverage disclaimer.

The accepted dataset still represents only DHCP-managed main-LAN traffic that
actually traverses Pi-hole. Current dnsmasq interception paths, the Tailscale
classic-DNS redirect and encrypted-DNS bypasses remain explicitly outside that
dataset until separately measured.

See [the DNS activity analytics plan](docs/network-dns-visibility-client-activity-analytics.md),
[sanitized Phase 0 evidence](evidence/2026-09-28/pi-hole-api-phase0-preflight.md),
[collector validation](evidence/2026-09-28/pi-hole-dns-collector-live-validation.md)
and [Phase 2/3 analytics validation](evidence/2026-09-28/pi-hole-dns-analytics-phase2-3-validation.md).

See [the final case study](docs/pi-hole-on-router-case-study.md) and [sanitized cutover evidence](evidence/2026-09-28/pi-hole-main-lan-cutover-validation.md).

## Historical baseline and subsequent live checks

The 2026-09-11 controlled reboot and post-migration validation established the historical SSD-backed baseline. The final health check for that session reported:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

A later closing read-only checkpoint on 2026-09-22 retained a healthy router state without changing the reference configuration. The closing project health check reported `0 failure(s), 0 warning(s)` and `HEALTHCHECK_RC=0`.

Key validated areas include:

- persistent SSD-backed Entware storage and swap;
- Tailscale service availability and intended `netfilter-mode=off` architecture;
- project-owned IPv4 filter/NAT chains and fail-closed IPv6 guards;
- live validation of the exit-node runtime contract: IPv4 forwarding, project WAN-forward rule, platform WAN NAT, and established/related return path;
- Unbound availability and DNSSEC validation;
- dnsmasq integration with the intended local Unbound listener;
- syslog-ng availability;
- printer exposure hardening;
- backup/recovery and evidence tooling;
- CI/static/mock validation of configuration, firewall, WAN recovery, installer rollback, restore validation, and maintenance paths.

The current `scripts/healthcheck.sh` implementation checks the AUDIT-02 exit-node runtime prerequisites when exit-node mode is enabled. The implementation was merged through PR #51 and was subsequently deployed to the reference router on 2026-09-22. A live post-deployment run matched the repository SHA-256 (`e03d6abd7a740524ba5a2c6799a47559ef187b22bb1a3209eb94ffc4a30a7e47`) and completed with `0 failure(s), 0 warning(s)` and `HEALTHCHECK_RC=0`. See `evidence/2026-09-22/healthcheck-deployment-validation.md`.

A later 2026-09-22 maintenance check also found and removed a legacy `/jffs/scripts/nat-start` hook that duplicated the managed Tailscale DNS redirects and was group/world writable. The runtime duplicates had zero counters because the project-owned parent jump was evaluated first. The hook was backed up privately, removed from the active hook directory, and the duplicate runtime rules were deleted; the deployed health check remained `0 failure(s), 0 warning(s)`. A follow-up repository revision added explicit detection for direct `tailscale0` NAT rules outside `EDGE_TS_PREROUTING` and unsafe active JFFS hook modes. That hardened revision was subsequently deployed to the reference router and live-validated with SHA-256 `5d96555bad141c40191855e2f121de0412635cb7e5fe14d41b5ec73842db6233`, `0 failure(s), 0 warning(s)`, and `HEALTHCHECK_RC=0`. See `evidence/2026-09-22/healthcheck-drift-hardening-live-validation.md`.

## 2026-09-27 post-firmware closure and disaster-recovery baseline

The remaining post-firmware validation debt was closed on the current GNUton
reference firmware:

- #64 revalidated the classic UDP/TCP 53 Tailscale DNS datapath through
  `EDGE_TS_PREROUTING -> dnsmasq -> Unbound`;
- #65 completed Diversion `Large + snbAdSupport=no` normal-use acceptance;
- #66 completed three clean startup cycles after correcting pre-Entware swap
  ordering in the reference `post-mount`;
- #67 repeated the Android exit-node public-IP validation after reboot;
- #70 replaced the canonical raster architecture with four source-controlled
  Mermaid diagrams.

Issue #100 then established the current disaster-recovery baseline. The project
now has a sanitized rebuild manifest, a separate private native ASUS/Merlin
settings export, verified off-router project backup artifacts, dry-run restore,
an alternate-root clean-room restore, content/mode comparison, and a documented
post-restore validation sequence.

The clean-room restore was additionally hardened after final review: the
partly AMTM-managed `post-mount` hook is retained only as a review reference
and is never auto-applied. The final implementation also refuses to auto-apply
that live-path hook from older project backups.

The safe restore evidence is recorded in
[evidence/2026-09-27/issue-100-dr-cleanroom-restore-validation.md](evidence/2026-09-27/issue-100-dr-cleanroom-restore-validation.md),
and the recovery contract is documented in
[docs/router-disaster-recovery.md](docs/router-disaster-recovery.md).

That clean-room DR baseline predates the 2026-09-28 Pi-hole adoption. The
archive/restore mechanics remain validated, but current-state recovery now has
a documented follow-up gap: Pi-hole/FTL package/service reconstruction,
dedicated alias/startup ordering, Gravity/filtering policy rebuild and the
Pi-hole -> Unbound/DHCP/reverse-DNS checks have not yet been repeated as a
clean-room rebuild. The project must not imply otherwise.

That observability phase is now complete and remains the design precedent for
new analytics work: expensive storage, indexing and dashboards stay outside the
512 MiB router. The next extension reuses Pi-hole's existing query history
read-only rather than adding a new router-side analytics service.


## 2026-09-27 external observability baseline

The planned external monitoring phase is implemented on the Fedora reference
host while keeping time-series/database/dashboard workloads off the router.

Validated components include the read-only SSH exporter, the TUF-AX5400
Broadcom chanspec compatibility patch, VictoriaMetrics with 90-day retention,
Blackbox HTTPS/ICMP/router-DNS probes, scheduled Traffic Analyzer history
import, Grafana provisioning and automatic recovery after a real Fedora reboot.

All monitoring HTTP listeners bind to `127.0.0.1`. SNMP was not required.

See [the case study](docs/asus-tuf-ax5400-observability-case-study.md),
[sanitized validation](evidence/2026-09-27/observability-stack-validation.md) and
[reproducible monitoring configuration](monitoring/README.md).

Centralized logging and the initial Grafana alerting baseline are now
live-validated. Issue #108 has also advanced through the Fedora collector,
local Alloy/Loki ingestion, the Grafana DNS dashboard, full Fedora reboot
persistence and controlled two-client main-LAN acceptance. The tested
Tailscale classic-DNS exclusion is evidence-backed. Remaining #108 work is
bounded storage/retention observation, rollback/uninstall validation and
hard-coded external LAN interception correlation; issue #68 remains the
separate encrypted-DNS bypass assessment.

## 2026-09-26 HE160 interoperability investigation

A controlled Wi-Fi 6 performance investigation isolated a severe HE160-specific
throughput problem on the tested Windows client equipped with a MediaTek MT7922.

Key bounded observations:

- the MT7922 performed strongly at HE80, with approximately 850–880 Mb/s in the
  validated current-driver runs;
- at HE160 the same client degraded sharply and asymmetrically, including
  approximately 74.7 Mb/s receiver throughput in the most affected direction
  and approximately 401 Mb/s in the reverse direction;
- updating the Windows MT7922 driver improved the HE160 symptom but did not
  remove the large HE80/HE160 gap;
- an independent Android 2x2 HE160 client on the same ASUS 5 GHz radio achieved
  approximately 706 Mb/s in one direction and approximately 671 Mb/s in the
  other, strongly weakening the hypothesis that the ASUS radio is globally
  incapable of useful HE160 throughput;
- high negotiated PHY rate did not guarantee high application throughput;
- Broadcom `wl sta_info` retry-related counters were retained as
  station-associated telemetry and were not equated one-to-one with TCP
  retransmissions.

The router-side 160 MHz enablement experiment was deliberately temporary. The
`bw_switch_160` family was changed together without `nvram commit`, so the
evidence establishes involvement of that mechanism family but does not identify
one individual key as causal or promote the temporary test state into permanent
configuration.

The final fault-domain assessment is intentionally bounded to HE160 behavior in
the tested MT7922 ↔ ASUS/Broadcom combination. The evidence does not assign a
universal defect to MediaTek, Broadcom, ASUS firmware or Windows.

See the [HE160 interoperability case study](docs/wifi6-he160-mt7922-interoperability-case-study.md)
and the [2026-09-26 worklog](docs/worklog/2026-09-26.md).

## 2026-09-25 reference deployment checkpoint

- The router remained on GNUton `3004.388.11_1-gnuton1_tuf`. Both SSD-backed filesystems were mounted read/write, both swap files were active, and `tailscaled`, Unbound, dnsmasq and syslog-ng were running.
- Tailscale reported version `1.102.3`. The router continued to advertise exit-node capability and the project health check confirmed the intended `netfilter-mode=off` ownership model, IPv4/IPv6 managed chains, exit-node runtime prerequisites, printer hardening, DNS policy and resolver health.
- A direct Unbound query on loopback port 53535 returned `NOERROR` with the DNSSEC `AD` flag. The final project health result was `0 failure(s), 0 warning(s)` with `HEALTHCHECK_RC=0`; the bounded kernel/system error scan found no matching OOM, panic, filesystem-I/O, read-only-filesystem or EXT4 error entries.
- Controlled Fedora tests reconfirmed the production LAN classic-DNS policy on the current firmware: one external UDP/53 query increased the managed UDP redirect counter by one packet and one TCP/53 query increased the managed TCP redirect counter by one packet. A direct TCP/853 attempt failed with `Connection refused` while the production DoT reject rule increased by exactly one packet / 60 bytes.
- A UDP/53 query sent through the router's Tailscale address succeeded and increased the managed `EDGE_TS_PREROUTING` UDP redirect counter by one packet. This reconfirms current-firmware interception and resolver health, but is not presented as a full replacement for the 2026-09-22 packet-by-packet AUDIT-03 correlation.
- A new same-day exit-node packet-correlation attempt was not accepted as evidence: the first controlled flow ran while the Fedora client had no exit node selected, and a later router capture attempt could not start because the router shell lacked the expected `timeout` utility. The published 2026-09-23 fixed-flow `tailscale0`/WAN capture remains the authoritative current-firmware AUDIT-02 evidence.
- A later normal-use GeForce NOW Ethernet observation remained stable for approximately one hour with zero application-reported packet loss and stable latency. Toggling the endpoint Zen filter did not produce an observed difference in that window. An attempted Exit Node A/B/A overlay comparison was rejected as symmetric evidence after route verification showed the nominal final A segment still used the exit node.

See the [2026-09-25 worklog](docs/worklog/2026-09-25.md) and [sanitized router checkpoint](evidence/2026-09-25/router-live-checkpoint.md).

## 2026-09-23 reference deployment checkpoint

- Before the project and firmware changes, the operator verified independent, private backup copies and restore dry-runs. The project archive is scoped to selected JFFS/Entware files; separate encrypted backups cover router settings, full JFFS, NVRAM reference data and Tailscale state. These are different recovery layers, not a complete firmware image or a successful restore drill.
- After the firmware upgrade and an operator-initiated same-day reboot, both SSD partitions and swap were available. WPS remained disabled; ports 1900 and 8200 had no listeners. The USB exposure audit and project health check each reported zero failures and warnings. The project health check verified the configured exit-node runtime prerequisites, DNS, managed firewall and core services at that point in time.
- Both authorized Tailscale admin sources retained exact managed HTTPS input and DNAT rules after reboot. From Fedora, router-addressed and separately addressed external UDP/53 lookups answered; the after-reboot probe did not record a NAT redirect-counter delta. Fedora HTTPS using the router's DDNS name over the tailnet returned `HTTP=200` with certificate verification successful (`TLS_VERIFY=0`).
- The operator reported that Android could load and log in to the admin panel over both cellular data and Wi-Fi with Tailscale enabled; the page did not load with Tailscale disabled in either tested condition. The phone browser's certificate indicator and exact packet path were not captured. These observations do not establish a general WAN-side block.
- The distinct unauthorized-tailnet management test was completed later the same day. The unauthorized client remained a functioning Tailscale peer but could not establish TCP/8443; a directional `tailscale0` capture and source-specific temporary counter-only rule correlated exactly five NEW TCP/8443 SYN packets / 260 bytes before the unchanged production deny tail. The temporary instrumentation was removed and the final production health check returned zero failures and warnings.
- The exit-node datapath was then revalidated on GNUton `3004.388.11_1-gnuton1_tuf`. A Fedora client used the ASUS as its active exit node and sent five ICMP requests with fixed identifier `4244` and sequence numbers `1..5`. Simultaneous captures observed the same flow on `tailscale0` before NAT and on `ppp0` after source translation, including the matching replies; both captures recorded 10 packets and zero kernel drops. The client received 5/5 replies with 0% loss, and the final production health check again returned zero failures and warnings. A second post-reboot Android public-IP comparison, current-firmware AUDIT-03 DNS packet correlation, several cold starts and long-term normal-use observation remain outstanding.

The full chronology and claim limits are in [the 2026-09-23 worklog](docs/worklog/2026-09-23.md). Firmware compatibility is scoped in [compatibility and revalidation](docs/compatibility.md); test ownership and outstanding acceptance checks are mapped in [requirements and acceptance](docs/requirements.md).

## Stability observation — closed 2026-09-22

**Observed window:** 2026-09-11 through 2026-09-22.  
**Operating mode:** continuous 24/7 powered operation during the observed window.  
**Original plan:** continue through 2026-09-25; the observation was deliberately closed early to begin the next controlled project phase.

During the observed window the reference router remained unchanged except for read-only validation. At closure, the project health check reported zero failures and zero warnings. Entware/SSD availability, required swap, Tailscale connectivity, project firewall chains, Unbound/DNSSEC and syslog-ng were healthy; the inspected current syslog contained no matching OOM, crash, filesystem-I/O or read-only-filesystem errors.

This supports a bounded claim of successful continuous operation over the exact 2026-09-11 → 2026-09-22 interval. It must not be described as a completed 14-day endurance test or as proof of indefinite long-term stability.

## Security/code audit remediation status

A full repository audit covered code, security, install/rollback, firewall/DNS/Tailscale behaviour, logging, backup/recovery, tests/CI, documentation, evidence/privacy, and portfolio presentation.

| Finding | Status | Current state |
|---|---|---|
| AUDIT-01 — restore apply was not transactional | **CLOSED** | Restore now snapshots affected live paths and rolls back partial apply failures; regression coverage was added and CI passed. |
| AUDIT-02 — exit-node NAT dependency not explicitly validated | **CLOSED / POST-FIRMWARE LIVE REVALIDATED** | The 2026-09-22 correlation established the ownership model, and the 2026-09-23 GNUton `3004.388.11_1-gnuton1_tuf` rerun reconfirmed `ip_forward=1`, the project WAN-forward rule, platform `ppp0` `MASQUERADE`, the established/related return path, and the same fixed-ID ICMP flow on `tailscale0` before NAT and `ppp0` after NAT. See [current-firmware evidence](evidence/2026-09-23/audit-02-post-firmware-exit-node-revalidation.md). |
| AUDIT-03 — Android/Fedora exit-node DNS datapath validation gap | **CLOSED / CURRENT-FIRMWARE FEDORA REVALIDATED** | Controlled live tests on 2026-09-22 validated classic DNS over UDP/TCP 53 from Fedora and Android exit-node clients. On 2026-09-27 the Fedora path was revalidated on GNUton `3004.388.11_1-gnuton1_tuf` after the Unbound 1.26.1 update: unique UDP/TCP queries were captured on `tailscale0`, the managed REDIRECT counters increased by exactly +1/+1, matching loopback traffic was observed to `127.0.0.1:53535`, temporary instrumentation was removed, and the final health check was clean. See [current-firmware DNS evidence](evidence/2026-09-27/audit-03-current-firmware-dns-datapath-revalidation.md). Encrypted DNS remains outside this claim. |
| AUDIT-04 — unnecessary deployment identifiers in Zen evidence | **CLOSED** | Evidence was sanitized while preserving the technical result. |
| AUDIT-05 — Android DNS datapath claim exceeded available evidence | **CLOSED** | README wording was corrected so the historical observation no longer overclaimed the resolver path. The remaining classic-DNS datapath question was subsequently closed by AUDIT-03 live validation on 2026-09-22. |

AUDIT-02 and AUDIT-03 are closed from live evidence on the reference datapath. AUDIT-02 has additionally been revalidated on the 2026-09-23 GNUton firmware for the tested IPv4 ICMP exit-node flow. The Fedora portion of AUDIT-03 was revalidated on 2026-09-27 on GNUton `3004.388.11_1-gnuton1_tuf` after the Unbound 1.26.1 deployment and remains explicitly bounded to classic DNS over UDP/TCP port 53; Android-specific post-reboot behavior and encrypted resolver transports remain separate items.

## Current execution checkpoint and next actions

The earlier post-firmware validation debt is closed: the exit-node datapath, current-firmware classic DNS, Diversion Large acceptance, repeated clean startup behavior and Android exit-node public-IP behavior all have dated evidence. The main-LAN filtering path was then migrated from Diversion to Pi-hole on 2026-09-28, so Diversion observation is no longer a current action item.

The 2026-09-28 worklog intentionally stopped Grafana work after the first useful GitHub/CI dashboard was validated. The immediate continuation is therefore documentation/observability work rather than a router-policy change:

1. **Finish the Grafana Engineering / CI dashboard:** merged PRs over a bounded recent period, recent repository activity/commits, final layout cleanup and a separate Polystat infrastructure-health overview.
2. **#127 — LAN management / automatic exposure:** verify and, only where justified, restrict normal-LAN WebUI access and audit UPnP/NAT-PMP, Port Trigger, Port Forwarding and DMZ state.
3. **#128 — IPv6 and Wi-Fi security parity evidence:** establish the current IPv6 WAN/LAN/client state plus WPA2/WPA3, PMF/802.11w and guest/client-isolation evidence before any enforcement change.
4. **#130 — repository supply-chain protection:** add a `main` ruleset, require the Validation suite, and block force-push/branch deletion while preserving the PR workflow.
5. **#108 — finish bounded DNS-analytics gaps:** measure retention/storage behavior, validate rollback/uninstall and correlate the hard-coded external LAN classic-DNS interception path.
6. **#68 — DoH/DoQ bypass assessment:** measure encrypted-DNS bypass paths before designing enforcement.
7. **#129 — Pi-hole-aware disaster-recovery refresh:** extend the validated recovery mechanics to Pi-hole/FTL, dedicated listener/alias, Gravity, DHCP/reverse DNS and Pi-hole -> Unbound reconstruction.

Keep new live evidence minimized and sanitized, and treat every router change as planned maintenance with a current backup, rollback path and affected live revalidation.

## Evidence and privacy boundary

Raw operational evidence remains private when it contains deployment-specific identifiers. Repository evidence must not expose credentials, tokens, private keys, real Tailscale addresses or node identifiers, WAN identifiers, device MAC addresses, private hostnames, resolver account identifiers, exact storage UUIDs/PARTUUIDs, or other unnecessary infrastructure identifiers.

Published evidence should contain only the minimum sanitized information required to reproduce or support the technical conclusion.


## Fedora Disaster Recovery validation

On 2026-09-18, the Fedora recovery set was validated in a clean-room VMware test VM.

**Result: PASS.** The restored Fedora installation booted successfully from the recovered virtual NVMe disk to the graphical desktop after the recovery ISO was detached.

Post-restore validation confirmed:

- `/`, `/home`, `/boot`, and `/boot/efi` mounted from the recovered target layout;
- the recovered user environment and project files were present;
- `systemctl --failed` contained only the known VM-specific `mcelog.service` exception;
- the initial `/boot` SELinux labeling problem was identified as `unlabeled_t`;
- `restorecon -RFv /boot` restored the expected Fedora `boot_t` labels;
- a subsequent boot-level error scan showed no new `boot`, `logind`, SELinux denial, or related errors.

The clean-room restore also established three explicit recovery requirements: adapt `/boot` UUID references in `/etc/fstab` and Fedora EFI/GRUB configuration when the target partition identity differs, and relabel `/boot` with `restorecon` after restore.

Detailed sanitized evidence: `docs/FEDORA-DR-RESTORE-VALIDATION-2026-09-18.md`.

Raw recovery evidence remains private and is not published with deployment-specific UUIDs or other infrastructure identifiers.

## 2026-09-18 repository validation update

The Fedora clean-room restore findings have been converted into a guarded recovery finalization helper (`scripts/fedora-dr-restore.sh`) with dry-run/apply modes, configuration-file rollback protection, `/boot` UUID adaptation, GRUB UUID correction, SELinux relabeling via `restorecon`, and explicit refusal of unsafe or missing target mounts. It is intentionally not described as a complete bare-metal restore engine. A focused regression test is integrated into CI. GitHub Actions run #462 completed successfully after correcting the test invocation. The router reference state was not modified by this work.

GitHub Actions run #474 completed successfully after the remediation batch. The workflow now executes the previously unwired recovery, firewall/configuration, evidence-collector, and log-retention tests directly, in addition to the existing focused validation steps.

## LAN DNS-over-TLS (DoT/853) control — LIVE VALIDATED

A controlled Fedora A/B/A test on 2026-09-22 first confirmed that direct DNS-over-TLS was a real bypass of the classic port-53 enforcement on the tested IPv4 LAN path.

Baseline: Fedora routed `8.8.8.8` through the normal LAN gateway and successfully established TLS 1.3 to `8.8.8.8:853` with a verified `dns.google` certificate.

Prototype block: a temporary `EDGE_LAN_DOT_TEST` FORWARD chain on `br0` rejected TCP/853 with `tcp-reset`. The client received `Connection refused`, the router rule recorded `1 packet / 60 bytes`, and rollback restored successful TLS/853 connectivity.

The production implementation from PR #58 was then deployed to the reference router with `EDGE_BLOCK_LAN_DOT=1`. The deployed scripts matched the repository revisions:

```text
firewall-start SHA-256: 3b51ab285605d379c28552853331921f4f2afa58562e97772866ec243ff60667
healthcheck.sh SHA-256: e1b9436a8aed5e7f16e725c0769e3f6275198ca1e6f7ed1d8d51ef504304045d
```

The live health check reported `0 failure(s), 0 warning(s)` and `HEALTHCHECK_RC=0`, including PASS results for the single LAN DoT FORWARD jump, parent ordering before platform FORWARD rules, and the exact TCP/853 blocking policy.

A subsequent Fedora production test, with `8.8.8.8` routed through `192.168.50.1` over the LAN, failed with `Connection refused`. The managed production `EDGE_LAN_DOT_FORWARD` rule simultaneously recorded `1 packet / 60 bytes`, tying the client failure to the deployed TCP/853 reject policy.

The claim is deliberately limited to direct IPv4 DoT on TCP/853. It does not control DoH/HTTPS, DoQ/QUIC, VPN-carried DNS, IPv6 resolver paths, or application-specific encrypted DNS.

Sanitized evidence: `evidence/2026-09-22/dot-853-block-production-validation.md`.

## LAN classic-DNS enforcement — LIVE VALIDATED

A controlled temporary test on 2026-09-22 first validated the LAN classic-DNS interception mechanism on the reference path. Fedora was confirmed to route `8.8.8.8` through the LAN gateway rather than through the Tailscale exit node. A temporary `br0` NAT chain intercepted controlled UDP/53 and TCP/53 queries addressed to `8.8.8.8`, while DNS already addressed to the router followed the explicit router-return rule. The temporary chain was removed after the prototype.

The production implementation was then merged through PR #57 as opt-in `EDGE_ENFORCE_LAN_DNS`, using the dedicated managed `EDGE_LAN_DNS_PREROUTING` chain plus health-check and regression coverage. The example remains disabled by default, but the reference router was explicitly enabled and deployed under controlled maintenance.

The deployed production files matched the tested repository revisions:

```text
firewall-start SHA-256: ae7f1e5794cbbcf6e1e9fc828bba1cdabe43a021ca518d6466cc44bec5997d6a
healthcheck.sh SHA-256: ba78afe34ba27b582d6bbeb399d97e89e51f6199d11220805bbe2a71d791a9a1
```

The live health check reported `0 failure(s), 0 warning(s)` and `HEALTHCHECK_RC=0`, including explicit PASS results for the LAN DNS parent jump and managed chain policy. A subsequent Fedora validation, with `8.8.8.8` routed through `192.168.50.1` over the LAN rather than Tailscale, increased the production `EDGE_LAN_DNS_PREROUTING` external redirect counters to 6 UDP packets / 480 bytes and 6 TCP packets / 360 bytes.

The scope is deliberately limited to classic IPv4 TCP/UDP port 53. DoH, DoT, DoQ, VPN-carried DNS, IPv6 resolver paths, and application-specific encrypted DNS remain separate controls/limitations.

Sanitized evidence: `evidence/2026-09-22/lan-dns-enforcement-production-validation.md`.

## DNS filtering validation — 2026-09-22

A controlled Diversion comparison was completed after the unchanged-state observation closed.

Tested states:

```text
A. Standard + snbAdSupport=yes
B. Standard + snbAdSupport=no
C. Large + snbAdSupport=no
```

Disabling SNBForums ad support removed a hard-coded exception that allowed `pagead2.googlesyndication.com` to bypass a broader `googlesyndication.com` block. The Android LTE/5G Tailscale exit-node classic-DNS path was re-checked after the change and remained healthy.

The Large profile materially broadened DNS blocking, but visible advertising still remained on representative real-world sites even while many observed advertising/RTB hostnames returned `NXDOMAIN` from the Android client. One focused denylist experiment for `sdk-videoplayer.optad360.info` also did not remove the observed advertising by itself.

Historical 2026-09-22 post-test filtering state:

```text
Diversion: enabled
profile: Large
snbAdSupport=no
focused denylist entry: sdk-videoplayer.optad360.info
```

The historical Diversion result established that DNS filtering is useful for broad network-wide domain suppression but is not equivalent to complete browser-content or in-app advertising removal. That conclusion still applies after the 2026-09-28 Pi-hole adoption: Pi-hole is now the active main-LAN filtering/visibility layer, but it is not a guarantee of perfect ad removal or complete client visibility.

Sanitized evidence: `evidence/2026-09-22/diversion-ad-blocking-validation.md`.

## Current decision

As of 2026-09-28, the reference router runs GNUton `3004.388.11_1-gnuton1_tuf` with Unbound 1.26.1 and Pi-hole adopted for the main-LAN DHCP DNS-filtering path. Diversion and uiDivStats are no longer active; ASUS DNS Privacy/Stubby is disabled; stale NextDNS hook logic is removed. The final reboot validated both swap files, Tailscale, Pi-hole, Unbound, main-LAN DHCP DNS, blocking, DNSSEC negative behavior and active-lease reverse DNS.

The source-controlled issue #108 Fedora collector, local Alloy/Loki ingestion and the Grafana DNS dashboard are live-validated. A controlled Fedora reboot also returned the complete path automatically; the post-reboot collector integrity check remained duplicate-free and a final seven-day equality check matched 12,183 source events to 12,183 Loki events. A later controlled two-client test distinguished two separate main-LAN clients in the Pi-hole-visible dataset. The same test confirmed that a Windows classic-DNS query carried over Tailscale is visible on `tailscale0` but absent from Pi-hole history, matching the documented Tailscale -> dnsmasq -> Unbound coverage boundary. The remaining classic-DNS correlation target is the hard-coded external LAN interception path; encrypted-DNS assessment continues separately under #68. Any decision to route those interception paths through Pi-hole remains a later datapath change with its own rollback and live validation. Public evidence remains sanitized and deployment-specific identifiers stay private.
