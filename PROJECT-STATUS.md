# Project status

**Status date:** 2026-09-22  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin  
**Current phase:** post-stability DNS-filtering validation / audit follow-up

## Executive status

The reference deployment is operational. The unchanged-state observation was closed on 2026-09-22 after continuous 24/7 powered operation from 2026-09-11 through 2026-09-22. The originally planned 14-day window through 2026-09-25 was ended early, so the project does not claim a completed 14-day endurance test.

The project currently has a validated SSD-backed Entware deployment, Tailscale-based remote access and exit-node capability, Unbound/DNSSEC integration, dnsmasq integration, syslog-ng logging, project-owned least-privilege firewall chains, recovery tooling, health checks, evidence collection, and automated repository validation.

The stability observation deliberately separated a successful point-in-time deployment from a broader stability claim. During the completed 2026-09-11 → 2026-09-22 window the router remained continuously powered and unchanged. Post-observation changes may now proceed as controlled maintenance with backup, rollback and explicit validation.

## Current validated baseline

The 2026-09-11 controlled reboot and post-migration validation established the current baseline. The final health check for that session reported:

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
| AUDIT-02 — exit-node NAT dependency not explicitly validated | **CLOSED / LIVE VALIDATED** | Live correlation on 2026-09-22 identified Asuswrt-Merlin's WAN `POSTROUTING` `MASQUERADE` as the effective NAT for Tailscale exit-node traffic, confirmed `ip_forward=1`, verified the project WAN-forward rule, and correlated the same fixed-ID ICMP flow on `tailscale0` before NAT and the WAN interface after NAT. |
| AUDIT-03 — Android/Fedora exit-node DNS datapath validation gap | **CLOSED / LIVE VALIDATED** | Controlled live tests on 2026-09-22 validated classic DNS over UDP/TCP 53 from Fedora and Android exit-node clients through `tailscale0` -> `EDGE_TS_PREROUTING` REDIRECT -> router-local dnsmasq -> Unbound on `127.0.0.1:53535`. Encrypted DNS (DoH/DoT) remains outside this claim. |
| AUDIT-04 — unnecessary deployment identifiers in Zen evidence | **CLOSED** | Evidence was sanitized while preserving the technical result. |
| AUDIT-05 — Android DNS datapath claim exceeded available evidence | **CLOSED** | README wording was corrected so the historical observation no longer overclaimed the resolver path. The remaining classic-DNS datapath question was subsequently closed by AUDIT-03 live validation on 2026-09-22. |

AUDIT-02 and AUDIT-03 are now closed from live evidence on the reference datapath. AUDIT-03 closure is explicitly bounded to classic DNS over UDP/TCP port 53; DoH/DoT and application-specific encrypted resolver transports remain separate limitations.

## Post-observation validation plan

Now that the unchanged-state observation is closed:

1. retain the 2026-09-22 closing stability checkpoint/report as the boundary for the completed observation;
2. retain the sanitized AUDIT-02 live-validation artifact documenting the platform-owned Asuswrt-Merlin NAT dependency;
3. retain the sanitized AUDIT-03 live-validation artifact documenting the Fedora/Android classic-DNS datapath and its encrypted-DNS limitation boundary;
4. make no configuration change unless the evidence demonstrates a real defect;
5. if a change is required, design the smallest remediation, test it in an isolated/planned maintenance context, deploy it deliberately, then repeat affected validation;
6. preserve the distinction between classic DNS interception and unvalidated encrypted/client-specific resolver transports.

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

As of 2026-09-22, the unchanged-state observation is closed and both AUDIT-02 and AUDIT-03 are live validated within their documented claim boundaries. The health-check code that verifies the platform-owned exit-node NAT/return-path prerequisites established by AUDIT-02 is now deployed on the reference router and has passed a live post-deployment validation with the repository-matching SHA-256, zero failures, zero warnings, and `HEALTHCHECK_RC=0`. A controlled Diversion A/B/C experiment has also established the current DNS-filtering boundary: `snbAdSupport=no` improves coverage, `Large` broadens the policy, but DNS blocking alone does not remove all rendered advertising. The Large profile is therefore in normal-use observation for false positives/resource impact rather than being treated as a proven complete ad-blocking solution.
