# Roadmap

### Security #235 — services-start source and owner trust (2026-10-20; read-only)

- [Operator-reported V1.4–V1.7 results](../evidence/2026-10-20/issue-235-services-start-trust-chain-v14-v17.md): firmware full-script hook is nonroot-owned 0755 but byte-identical to pinned source; addon root:root 0755 and config root:root 0600. The addon preserves the watchdog function and Cron tokens but moves watchdog registration later, so it is **not** proven semantically interchangeable.
- **Priority:** private Fedora source/backup copies for **both** targets now verify correctly; independently protected recovery media still remains unproven. Review the [two-target maintenance design](operations/issue235-privileged-startup-trust-maintenance-design-2026-10-20.md), preserving current bytes and startup behavior. Establish safe startup, **WAN-direct invocation, break-glass and Cron** quiescence/coordination, writer exclusion and JFFS2 failure handling. [V1.10](../evidence/2026-10-20/issue-235-wan-trigger-source-v18.md) has now byte-verified the live WAN wrapper and intermediate addon, with downstream handler and break-glass helper pinned separately. V1.11 confirmed root:root/no group/other write for standard WAN files and ancestors; **V1.12 identified the optional legacy WAN hook as absent at the read-only check**. This closes bounded WAN source/DAC/legacy-presence classification, **not** continuous owner/writer trust, live invocation or a safe method to inhibit all entrypoints. Do **not** run the generic installer or convert the live hook to a wrapper as a side effect.
- **Gate:** no production edit, Cron disable, service restart or reboot; `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.

### Security #235 — DNS Guard root-Cron trust checkpoint (2026-10-19; no deployment)

- **Completed within scope:** validated same-UID and cross-UID DAC/transaction models on Fedora, fresh approved read-only ASUS metadata and mount observations, historical SHA-256 match of live DNS Guard, off-router verified private backup, disposable restore and rootless rollback V1.3 **32/32 PASS**. [Sanitized evidence](../evidence/2026-10-19/issue-235-dns-guard-root-cron-trust-and-rollback.md).
- **Open risk:** nonroot-owned, owner-writable executable remains scheduled by root-Cron every minute. Process snapshots and hash matches do not make execution ownership trustworthy.
- **GO/NO-GO gates:** independently recoverable verified backup; trusted path/owner/writer preflight; dispatcher and startup re-registration inhibition; in-flight Cron/open-FD/other-writer quiescence; JFFS2 publication and failure recovery; trusted root:root 0755 rollback; bounded DNS/Unbound/Pi-hole postflight; **separate operator authorization** for each mutating stage.
- **Boundaries:** no `chown`/`chmod`, Cron disable, router reboot, installer or service restart; `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `DEPLOYMENT_GATE=HOLD`. Do not merge this work with SSD mode [Draft PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245), RouterCloud PrivDrop/origin or Dufs upgrades. Issue #235 remains broader than DNS Guard.

### Fedora Homelab Update — 2026-10-18 (off-router, partly deployed)

Completed: deployed a **check-only** daily update-watch timer and manually upgraded Grafana 13.2.3→13.2.4 after verified consistent backup, 15-rule/0-paused checks and Email+Telegram receipt. Operator-reported isolated engine/lock tests reached v0.9, including root/nonroot, cooperative job and descendant tests; **synthetic PASS is not RouterCloud production integration**. Follow-up gates before unattended AUTO: Caddy HTTP E2E, syslog-ng ASUS-specific ingestion, Restic repo/restore, verified real shared lock on backup wrappers, candidate-bearing transaction/rollback tests, individual package allowlist and explicit deployment approval. See [runbook](operations/fedora-homelab-automatic-updates.md), [worklog](worklog/2026-10-18.md). Router/SSD/Issue #235 scope unchanged.

### Security #235 checkpoint — 2026-10-16 (research milestone, not production)

- [Native SSD Trust Helper v1](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/tree/security/issue235-native-ssd-trust-v1-lab-20261016): published C read-only candidate and 15 x86-64 isolated checks; branch CI PASS. Operator-reported static ARMv7 build/QEMU smoke PASS, synthetic `RC=2/HOLD` and `RC=3/REJECT` behavior, **12/12 ARMv7 negative matrix PASS**. See [dated worklog](worklog/2026-10-16.md).
- **Hard block:** v1 returns **no authorization code 0**, has no `fchmod` or private UUID-to-device binding, and cannot assure continuous namespace identity. QEMU does not prove ASUS 4.1.52 compatibility. [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) remains OPEN; [Draft #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) is a distinct shell-mode repair design and remains unmerged/uninstalled. `DEPLOYMENT_GATE=HOLD`.
- **Next:** review UUID binding and mount lifetime/quiescence, firmware behavior and independent rollback; then request **separate authorization** before any router read-only run, staging, mode repair, activation, or reboot.
- **RouterCloud #254:** resumable/hash-verified large-file transfer is proposed, not implemented. Preserve #235 security constraints and stable-only DUFS update policy.

### Security #235 checkpoint — 2026-10-15 (evidence-scoped)

- **Current priority:** finish the [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) security scope without risking the reference router. See [dated worklog](worklog/2026-10-15.md). The issue remains **OPEN** and SSD persistence [PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) remains **DRAFT / NOT INSTALLED / GO-NO-GO HOLD**.
- **SSD/JFFS:** the accepted Oct 14 DAC Stage 1 was not boot-persistent: matching GNUton firmware mode reset left two live ext4 mount roots `0777` on Oct 15. UUID-guarded repair, secure JFFS metadata gates and exact V3 insertion passed isolated/offline checks only. Classify two SSD-referencing scripts; require validated rollback and **separate operator approval for staging, activation, and reboot**. Avoid the generic installer and do not change the separate UID 1000-owned `services-start`.
- **ARMv7 PrivDrop:** operator-reported local branch `security/issue235-privdrop-armv7`, latest local `e2ad8dc` (JFFS-8). QEMU fixture PASS is **not** remote-reviewed source, authenticated deployment hash, proven target `memfd` execution or a real ASUS nonroot service. Publish/review sanitized source and test actual binary/service behavior before a scoped pilot; live Dufs remains root.
- **HTTP active-content origin:** complete 404, HTML/SVG/XML, content-disposition/CSP, authentication and preview regressions. Tests and draft upstream assets work must not be presented as an installed origin fix.
- **Acceptance:** reviewable code and CI, consistent service/backup health, documented recovery, and properly authorized live verification; estimates of percent/time never substitute for these gates. No new Dufs RC update, routing/DNS changes or unattended router modification.


### Current work scheduling — 2026-10-13 (supersedes older #212 next-step text)

- **#212 LAN/Tailscale client DNS failover is PAUSED until separate suitable hardware is available**. Its issue remains open for traceability, not as scheduled engineering or deployment; RC13J v0.41 sidecar direct-access bypass and ASUS firmware feature gates remain unresolved. No further lab/pilot/production work is approved without a new operator decision.
- **PR #227 was merged to `main`** on 2026-10-13 as dated RC13J evidence, not implementation acceptance. Older draft-PR mentions in historical 2026-10-12 checkpoints retain their point-in-time meaning.
- Benchmark [methodology](benchmarks/asus-opnsense-comparison-methodology.md) is preserved for measured current ASUS baseline and a future independent OPNsense/x86 firewall, only when obtained/approved; no RT-BE88U purchase or new performance result.

### Current reference router checkpoint — 2026-10-10 (documentation review; last broad live gate 2026-10-09)

- Current router: ASUS TUF-AX5400 / GNUton 3004.388.11_1.
- Current live Tailscale: **1.103.375 unstable/dev**; earlier 1.102.3 evidence
  is historical pre-upgrade state.
- **Current DNS Guard v3.2** (PR #197 merged): bounded manual ON/OFF and power-cycle acceptance passed on 2026-10-08. An additional controlled reboot of the **existing router** on 2026-10-09 recovered the Pi-hole-aware DNS stack with healthcheck 0/0; no blank-device restore is claimed. v3.1 remains historical.
- **2026-10-12 superseding decision:** there is **NO planned RT-BE88U migration**. Maintain current TUF-AX5400 in production while completing CORE v1.0. OPNsense/x86 is an **optional future replacement**, with no date, purchase or production approval; explore only as an isolated Windows 11 VM lab when ready. See [platform decision](architecture/platform-direction-2026-10-12.md).

### Grafana alerting acceptance checkpoint — 2026-10-12

The Fedora monitoring-host audit verified 15/15 enabled healthy Grafana rules
with valid direct receiver assignments; the default fallback receiver was
corrected from `empty` to `ASUS Edge Gateway Email` and confirmed via API.
Email and Telegram **contact test** messages reached the operator.
A 2026-10-12 temporary synthetic `E2E-TEST-2026-10-12` rule achieved
`Firing → automatic Gmail+Telegram delivery → Normal → Resolved delivery on
both channels` (operator-confirmed; Firing delivery screenshots reviewed),
without stopping production services. **Synthetic dual-channel E2E: PASS**.
Afterwards the operator deleted the temporary rule and confirmed **15 rules
remain (cleanup PASS, operator-reported)**. **Issue #178 is CLOSED**;
this bounded dual-channel test does not settle grouping/anti-flap, drift
between live Telegram and Email-only provisioning, or fallback-policy
persistence. Track those as explicit open acceptance gaps before claiming
complete notification lifecycle validation; do not force a live restart. Evidence:
[2026-10-12](../evidence/2026-10-12/grafana-alerting-routing-audit.md).

### Optional utility extension (2026-10-09)

A separately installed BusyBox 1.36.1 ARM EABI5 adds FIND/TIMEOUT/SHA256SUM and
other utilities for explicitly scoped operator commands. The firmware's
BusyBox 1.25.1 and /bin/sh remain authoritative; no global PATH or DNS Guard
startup change is planned. See [safe usage and rollback contract](custom-busybox-armv7.md).
The binary is not part of the current CORE backup; optional recovery follows
basic router restoration. #200 was closed after the full protected-tree audit and isolated tests. The optional tool's latest-reboot persistence **PASS** was recorded on 2026-10-10 after a read-only existing-router comparison; its removal/rollback and clean-device restore remain untested, and **#129 stays OPEN**. See [follow-up evidence](../evidence/2026-10-10/issue-129-custom-busybox-reboot-persistence.md).

### Issue #212 kernel extension feasibility — 2026-10-12 (source-only)

**Historical scope note (2026-10-13):** RT-BE88U was removed from the purchase/migration plan on 2026-10-12. Model-specific comparisons here are archived feasibility research, **not a scheduled kernel change or hardware target**. See [platform direction](architecture/platform-direction-2026-10-12.md).

Public Broadcom/Merlin source inspection: TUF-AX5400 uses production 4.1.52/ARMv7 (operator reports no netns handle); the RT-BE88U model profile selects 4.19 on BCM6813. The **generic** ARM64 defconfig has `VETH=m`, while an optional OpenSync config generator supports VETH/TPROXY; however `BUILD_OPENSYNC` is disabled in the RT-BE88U model profile, and **the exact shipped model kernel .config and module ABI were not obtained**. **Decision:** NO-GO for any production router custom kernel and for 6.x rebase; CONDITIONAL GO for offline final-config reproduction and vendor-module/build compatibility research only. Even available netns/veth would not solve v0.41's direct-gateway bypass. See [kernel-extension source feasibility assessment](design/issue212-kernel-extension-feasibility-2026-10-12.md).

### Issue #212 RC13J engineering checkpoint — 2026-10-12 (lab only)

The previously documented topology remains authoritative: **main-LAN Pi-hole -> Unbound** and **firmware dnsmasq -> the same Unbound at 127.0.0.1:53535**. Reusing current dnsmasq can at most bypass a failed Pi-hole/FTL while Unbound stays healthy; it is **not independent DNS continuity across Unbound outage**. DNS Guard v3.2 remains a separate router-system-resolver policy.

Operator-reported RC13J v0.26–v0.33 laboratory and read-only router checks passed within their stated scopes, including ARMv7 dnsmasq synthetic signed DNSSEC under QEMU, four Fedora kernel hook-order permutations, source-copied guard-only firewall and coordinated standby listener lifecycle. **v0.34 deliberately reproduced a P0 exposure**: on an *uncoordinated* INPUT reset, a wildcard-bound standby at `0.0.0.0:55353` became directly reachable from LAN via UDP/TCP before watchdog response. v0.35 initially timed out because the guard also blocked loopback. v0.35b and **v0.36 PASS** showed that a **loopback-only** listener plus narrow local INPUT exceptions preserves local UDP/TCP and prevents direct ingress during the *tested* private-kernel INPUT resets.

**No functional client DNS failover via the loopback-only design yet exists**: the old DNAT path cannot simply target `127.0.0.1:55353` with `route_localnet=0`; neither changing `route_localnet` nor modifying production firmware dnsmasq is authorized. Next: off-router proof of a source-scoped LAN/Tailscale UDP+TCP transport to an **independent** resolver without direct exposed sockets, then private-domain/PTR privacy, DNSSEC, failure/rollback, ASUS firmware/runtime and explicit single-client pilot gates. **#212 stays OPEN; no production or live repo firewall changes.** Full dated evidence: [RC13J v0.26–v0.40 checkpoint](../evidence/2026-10-12/issue-212-rc13j-v26-v40-checkpoint.md).

**Follow-up v0.41–v0.42 (2026-10-12; still research-only):** a private Fedora netns/veth routed sidecar passed scoped synthetic UDP/TCP and separate sidecar-ACL checks, **but the authorized selected client could address the sidecar gateway directly** (`SELECTED_DIRECT_GATE_EXCLUSION_PROVED=NO`). This remains a blocking origin/bypass security finding. Read-only current-ASUS inventory did **not** establish NET_NS, veth, TPROXY or socket-match deployment support on GNUton 4.1.52; absent visible handles/modules are not proof of compile-time absence. Neither feature feasibility nor DNS wire/DNSSEC production acceptance was proven. **No client DNS failover is deployed; #212 stays OPEN**. Details in the [v0.41/v0.42 continuation](../evidence/2026-10-12/issue-212-rc13j-v26-v40-checkpoint.md#rc13j-v041-follow-up--private-dns-sidecar-transport-2026-10-12) and [kernel feasibility review](design/issue212-kernel-extension-feasibility-2026-10-12.md).


### 2026-10-10 DNS Guard-first engineering checkpoint (design/lab, not deployed)

The accepted **router-system** DNS Guard v3.2 and the main-LAN Pi-hole → Unbound topology remain unchanged. [#212](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212) now records selected-source **client** failover RC1–RC12 isolated Fedora tests, read-only GNUton lifecycle research, RC13 process-name risk, RC13b SmartDNS/dnsmasq parity and RC13c cryptographic fixture. **The full RC13c DNSSEC resolver run is PENDING; no new ASUS standby, fallback NAT/filter or DHCP configuration is deployed.**

Execution order: #129/#196 recovery and evidence, #142 client-visible observation and #214 missing-cron detection, #213 cache-resistant fresh recursion, #212 design/firmware-matched testing, and guarded #215 validation before any separately approved single-client pilot. #217 is an isolated Tailscale ARMv7 build research item; #216 independent Pi-hole remains optional hardware research, not HA. This addendum supersedes older DNS-related ordering only. See [2026-10-10 worklog](worklog/2026-10-10.md) and [lab evidence](../evidence/2026-10-10/issue-212-client-dns-failover-lab.md).

### Current CORE closeout priorities

Completed on 2026-10-06:

- #130 — protected `main` / required Validation suite;
- #177 — Tailscale package/live-version drift and downgrade hardening;
- DNS Guard v3.1 — historical 2026-10-06 milestone; v3.2 is now current (PR #197 merged 2026-10-08).

Completed 2026-10-09:

- [#200](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/200) — least-privilege hardening of four JFFS backup/legacy/rollback trees accepted after a full 698-object inventory (zero group/world-writable entries or symlinks), managed hook/cron review and [PR #209](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/209) isolated installer/restore regression (8/8 CI). One private Pi-hole-owned mode 0640 file was retained. **No live emergency rollback or clean-device rebuild** was performed; see [acceptance evidence](../evidence/2026-10-09/issue-200-final-permissions-acceptance.md).
- [PR #208](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/208) — optional ARMv7 BusyBox 1.36.1 deployment/recovery documentation merged; the firmware binary and PATH stay unchanged.

Still open:

- #176 — router-local source scoping for exit-node forwarding;
- #129 — Pi-hole-aware disaster-recovery refresh;
- #108 — remaining DNS-visibility retention/rollback/interception work;
- #68 — DoH/DoQ/encrypted-DNS assessment;
- #143 — platform-neutral Trusted/IoT/Guest segmentation **design only**, usable in a future OPNsense comparison but not activated now.
- PR #202 — **open workstation-only** reproducible Unbound 1.26.1-1 ARMv7 rebuild candidate, not an Unbound upgrade or production rollout.
- DNS Guard follow-up — unmountable Entware at boot and simultaneous local/bootstrap DNS faults remain untested live; maintenance window only.

**Closed with bounded acceptance, residual follow-up not closed:**
- [#178](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/178) — closed after synthetic Gmail+Telegram `Firing/Resolved` acceptance on 2026-10-12. Grouping/anti-flap, provisioning/live contact divergence, reload persistence and per-rule failure injection are **still unverified**; track explicitly before claiming full monitoring continuity.



### 2026-10-08 documentation and observability synchronization

PR #197 merged after an up-to-date 4/4 PASS Validation suite.
Grafana's present YAML defines **15** alert rules: nine from the
2026-10-07 RouterCloud checkpoint, one earlier sustained DNS Guard
fail-open rule, and five additional DNS Guard recovery checks. The
five new alerts were observed loaded in Grafana, but individual
Firing/inbox delivery was not established. The nine-rule narrative
below is **historical**.

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
- [observability case study](case-studies/asus-tuf-ax5400-observability-case-study.md)
- [sanitized live validation](../evidence/2026-09-27/observability-stack-validation.md)
- [reproducible monitoring files](../monitoring/README.md)
- [RouterCloud Grafana live alerting validation](../evidence/2026-10-07/grafana-routercloud-alerting-live-validation.md)

The Grafana rule-evaluation baseline is live-validated: collector loss and
stale telemetry reached firing state in a controlled Fedora-only fault test,
recovered after service restoration, and the WAN no-data policy was corrected
so missing collector data does not masquerade as WAN-down evidence. A dedicated
e-mail contact point is also provisioned and the WAN-speed rule has bounded
end-to-end firing and resolved e-mail evidence. PR #190 then extended the
baseline to nine rules, added four RouterCloud backup/maintenance failure and
staleness rules, routed all nine **then-current** rules to the existing e-mail contact
point, and live-tested `routercloud_backup_bad` through firing and recovery.
**Historical 2026-10-07 status:** #178 then tracked grouping/anti-flap and
mobile/critical escalation rather than RouterCloud backup coverage itself.
**Current 2026-10-12 status:** #178 is CLOSED after controlled Gmail+Telegram
synthetic Firing/Resolved proof; grouping/anti-flap and provisioning parity
remain evidence gaps.

The centralized syslog-ng path was subsequently live-validated over Tailscale
with mutual TLS, source-restricted firewalld policy, an end-to-end unique
message, and a short collector-outage recovery test that delivered 3/3 queued
messages after collector restoration.

**Immediate continuation (updated 2026-10-12):** keep the completed Engineering/CI
dashboard baseline stable; review the remaining grouping/anti-flap and
live Email+Telegram provisioning gaps as follow-up work, even though #178
is now closed. That **nine-rule 2026-10-07 checkpoint** and RouterCloud backup/maintenance
alert validation remain historical facts. The **current 2026-10-08 YAML has 15**
rules directed to the e-mail receiver; individual firing and inbox delivery of
the five newly loaded DNS Guard recovery rules have not been proven.

The #127 LAN-management/WAN-exposure hardening, #128 IPv6/Wi-Fi security
parity evidence and #130 GitHub main-ruleset/required-validation work are
completed. Issue #177 Tailscale package/live-version drift hardening is also
completed. The current bounded hardening/recovery sequence is #176 local
source-scoping for exit-node forwarding, #129 Pi-hole-aware disaster recovery,
the remaining #108 DNS-visibility gaps, #68 encrypted-DNS assessment,
notification grouping/provisioning follow-ups after closed #178, and the later
platform-neutral #143 trust-zone segmentation design.

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

## Completed and adopted — Personal Cloud / RouterCloud stack

**Status: #136 completed 2026-09-30; #137 completed 2026-10-01; #138 completed 2026-10-02; current RouterCloud browser baseline documented 2026-10-03.**

The Fedora workstation has an evidence-backed one-way sync path from
`~/RouterCloud/` to the dedicated `ROUTER_DATA/RouterCloud/` directory on the
router SSD.

The accepted #136 design uses `rsync -rtv` over the existing SSH service, a
dedicated client identity, a fail-closed router-side forced-command wrapper,
`systemd.path` for low-latency top-level triggers, and a five-minute
`systemd.timer` for reconciliation. Automatic deletion remains intentionally
absent. The final client prevents fallback to ordinary workstation SSH
identities.

Issue #137 added browser-based access as a separate RouterCloud service while
preserving the LAN/Tailscale-only trust boundary and dedicated data root.
The current UI includes dedicated authentication, upload/download, bounded file
operations, selected server-side ZIP, WebDAV integration, AJAX sorting, live
AJAX search, recent files, persistent favorites and production-tested password
recovery.

Issue #138 added independent versioned encrypted backups. A dedicated read-only
backup identity pulls RouterCloud data to Fedora staging, and restic maintains
history in a separate repository with documented retention, integrity checking
and isolated restore procedures. The staging mirror is not itself treated as a
backup.

The Personal Cloud roadmap should now treat #136/#137/#138 as the completed
baseline. Future work is incremental hardening, compatibility, observability or
UX maintenance and must not reopen those completed milestones without a material
architecture change.

See:

- [Personal Cloud design and operations](personal-cloud-sync.md)
- [sanitized #136 live validation](../evidence/2026-09-30/issue-136-personal-cloud-sync-validation.md)
- [RouterCloud versioned encrypted backups](routercloud-versioned-backup.md)
- [RouterCloud 2026-10-03 production checkpoint](routercloud-production-checkpoint-2026-10-03.md)
- [RouterCloud UI production validation](../evidence/2026-10-03/routercloud-ui-production-validation.md)
- [RouterCloud password-recovery production validation](../evidence/2026-10-03/routercloud-password-recovery-production-validation.md)

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
- Telegram is the accepted live phone notification path as of the 2026-10-12 synthetic Gmail+Telegram `Firing/Resolved` test; ongoing grouping/provisioning/reload consistency still needs independent validation. Self-hosted ntfy/Gotify remain optional alternatives if the design later changes.
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

## Phase 2 — ASUS CORE v1.0, optional OPNsense lab (2026-10-12 decision)

**The earlier RT-BE88U migration plan has been cancelled.** No ASUS replacement
is ordered or scheduled. Current TUF-AX5400 remains the production gateway,
with DNS/Firewall/Tailscale/RouterCloud/monitoring baseline preserved. The
former 2026-10-06 RT-BE88U plan is **historical**, not a deployment gate.

**Complete CORE first:** #129 disaster recovery, #196 DNS Guard candidate
hardening, #142/#213/#214 independent DNS health/watchdog coverage, #139/#140
observability, #176 exit-node local source policy, plus bounded RouterCloud
and relevant documentation. Keep #212 LAN/Tailscale client DNS failover
OFF-ROUTER and OPEN: synthetic v0.41 pass had a direct-gateway bypass,
and v0.42 did not prove ASUS netns/veth/TPROXY support. No production trial.

**OPNsense/x86:** possible future platform, with no committed date or purchase.
A **separate Windows 11 laptop** (16 GiB RAM, one physical USB Ethernet
adapter; no current virtualization deployment) may host an isolated VM
laboratory. Virtual WAN+LAN NICs do not require a second physical adapter.
No lab DHCP/bridge to production LAN and no uncontrolled fault injection
on a NAT uplink that can still reach the home network.

A possible future architecture would be a separate x86 firewall with PF/
Unbound, optional independent resolver/filtered failover, and ASUS as AP or
otherwise repurposed — **all design hypotheses requiring real acceptance**.
Do not imply an installed OPNsense host, migrated Pi-hole, proven DNS
failover or current VLANs. Preserve historical RT-BE88U benchmark work
as a comparison artifact only. Platform and transition decisions must be
based on measured evidence, security, maintenance and recoverability.

See [2026-10-12 platform decision](architecture/platform-direction-2026-10-12.md).

## Phase 3 — detection and response

- Continue improving off-router alerting and response around the ASUS edge.
- Evaluate IDS/IPS only if a supported placement provides measurable value
  without destabilizing the router dataplane.
- Keep Wazuh/collector/indexer/dashboard workloads off-router.
- Maintain TLS log transport with monitored delivery and retained evidence.
- Map controlled attack simulations to MITRE ATT&CK where useful.

## Phase 4 — engineering maturity

- Metrics for DNS latency/cache, VPN throughput, drops, CPU, RAM, temperature, and storage wear.
- Golden configuration, reproducible restore, and quarterly recovery exercises.
- Policy-as-code validation for Tailscale and ASUS Edge policy changes.
- Hardware/ISP failure tests, measured RTO/RPO, and a documented incident runbook.
- Power-continuity / UPS assessment for the gateway, ISP handoff/CPE and Fedora monitoring host; do not claim uninterrupted operation until runtime and recovery behavior are measured.

The TUF-AX5400 remains the production gateway. Only after a separately
approved, validated future platform migration could it become a secondary
lab/AP node; there is no current retirement date or target hardware order.
