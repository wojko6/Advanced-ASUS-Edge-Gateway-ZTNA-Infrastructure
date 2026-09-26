# Project status

**Status date:** 2026-09-26

**Latest live router checkpoint:** 2026-09-25

**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin

**Current phase:** post-firmware validation, completed HE160 interoperability case study, and Diversion Large normal-use observation

## Executive status

This status document was reviewed on 2026-09-26. The 2026-09-25 read-only reference-router checkpoint remains the latest broad health/security checkpoint. On 2026-09-26, a separate Wi-Fi 6 HE160 troubleshooting session completed a controlled HE80/HE160 client-interoperability comparison on the ASUS 5 GHz radio. That session is documented as a performance/interoperability case study and does not replace the router security-validation evidence.

The reference deployment is operational. The unchanged-state observation was closed on 2026-09-22 after continuous 24/7 powered operation from 2026-09-11 through 2026-09-22. The originally planned 14-day window through 2026-09-25 was ended early, so the project does not claim a completed 14-day endurance test.

On 2026-09-23 the reference router was updated to GNUton `3004.388.11_1-gnuton1_tuf`. The project `v2.1.4-dev` scripts were deployed from source revision `de1cf10`, and a later private configuration change limited tailnet administration to the Fedora workstation and Android phone. A same-day reboot and bounded router/workstation/phone checks passed. The previously outstanding negative management-access check was then completed from a distinct unauthorized Windows tailnet client and published as sanitized live evidence; see the [dated worklog](docs/worklog/2026-09-23.md) and [negative-management validation](evidence/2026-09-23/unauthorized-tailnet-management-denial.md).

The project currently has a validated SSD-backed Entware deployment, Tailscale-based remote access and exit-node capability, Unbound/DNSSEC integration, dnsmasq integration, syslog-ng logging, project-owned least-privilege firewall chains, recovery tooling, health checks, evidence collection, and automated repository validation.

The stability observation deliberately separated a successful point-in-time deployment from a broader stability claim. During the completed 2026-09-11 → 2026-09-22 window the router remained continuously powered and unchanged. Post-observation changes may now proceed as controlled maintenance with backup, rollback and explicit validation.

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
| AUDIT-03 — Android/Fedora exit-node DNS datapath validation gap | **CLOSED / LIVE VALIDATED** | Controlled live tests on 2026-09-22 validated classic DNS over UDP/TCP 53 from Fedora and Android exit-node clients through `tailscale0` -> `EDGE_TS_PREROUTING` REDIRECT -> router-local dnsmasq -> Unbound on `127.0.0.1:53535`. Encrypted DNS (DoH/DoT) remains outside this claim. |
| AUDIT-04 — unnecessary deployment identifiers in Zen evidence | **CLOSED** | Evidence was sanitized while preserving the technical result. |
| AUDIT-05 — Android DNS datapath claim exceeded available evidence | **CLOSED** | README wording was corrected so the historical observation no longer overclaimed the resolver path. The remaining classic-DNS datapath question was subsequently closed by AUDIT-03 live validation on 2026-09-22. |

AUDIT-02 and AUDIT-03 are closed from live evidence on the reference datapath. AUDIT-02 has additionally been revalidated on the 2026-09-23 GNUton firmware for the tested IPv4 ICMP exit-node flow. AUDIT-03 remains live-validated on the 2026-09-22 firmware and is explicitly bounded to classic DNS over UDP/TCP port 53; DoH/DoT and application-specific encrypted resolver transports remain separate limitations.

## Post-observation validation status and next actions

The 2026-09-22 closing observation and AUDIT-02/03 sanitized live-validation artifacts are retained as historical checkpoints. Following the 2026-09-23 firmware and policy changes:

1. **Completed:** post-firmware exit-node packet correlation on GNUton `3004.388.11_1-gnuton1_tuf` confirmed the same fixed-flow datapath before NAT on `tailscale0` and after NAT on `ppp0`; see the [sanitized revalidation](evidence/2026-09-23/audit-02-post-firmware-exit-node-revalidation.md).
2. **Partially refreshed on 2026-09-25:** current-firmware Tailscale UDP/53 interception and resolver health were reconfirmed with a successful controlled query, an exact +1 managed redirect-counter delta and a clean resolver/health check. Repeat the full packet-by-packet `tailscale0 -> REDIRECT -> dnsmasq -> Unbound` correlation only if a current-firmware AUDIT-03-equivalent claim is required; the 2026-09-25 checkpoint does not overstate the narrower evidence.
3. Observe Diversion Large across the sessions and starts specified in [the roadmap](docs/roadmap.md#diversion-large-normal-use-acceptance-criteria), including false positives and RAM/swap behavior. One successful reboot does not meet those acceptance criteria.
4. Record additional clean startup/power-on cycles and re-check storage, swap, Tailscale, DNS and project health after each cycle so reboot persistence is supported by more than one same-day restart.
5. Keep new live evidence minimized and sanitized, and treat any further router change as planned maintenance with a current backup, rollback path and affected live revalidation.

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

Current post-test filtering state:

```text
Diversion: enabled
profile: Large
snbAdSupport=no
focused denylist entry: sdk-videoplayer.optad360.info
```

The correct architectural conclusion is that DNS filtering remains useful for broad network-wide domain suppression, but it must not be presented as complete browser-content or in-app advertising removal. Pi-hole remains a policy/observability candidate rather than a guarantee of perfect ad removal.

Sanitized evidence: `evidence/2026-09-22/diversion-ad-blocking-validation.md`.

## Current decision

As of 2026-09-23, the reference router runs GNUton `3004.388.11_1-gnuton1_tuf` with the `v2.1.4-dev` project deployed. The same-day reboot, core health and USB audits, both admin rules, Fedora DNS/verified HTTPS, operator-reported Android admin access, the distinct unauthorized-tailnet management denial, and the post-firmware Exit Node fixed-flow packet correlation all passed within their documented limits. Requirement F-01 has authorized and unauthorized role evidence for the tested deployment, and AUDIT-02 is now post-firmware live revalidated on the current GNUton build. AUDIT-03 retains its 2026-09-22 live-validation scope and still needs an equivalent current-firmware packet-correlation rerun if that stronger claim is required. Diversion `Large + snbAdSupport=no` remains under normal-use observation rather than a permanently accepted filtering baseline. Next: refresh the classic-DNS Tailscale datapath on the current firmware, then continue reboot and normal-use acceptance evidence.
