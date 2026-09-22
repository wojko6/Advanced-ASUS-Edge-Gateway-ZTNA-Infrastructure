# Validation evidence

Automated shell, configuration, mock-firewall, recovery, and evidence-redaction tests run in [GitHub Actions](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/actions).

Live results are environment-specific and are not fabricated in this repository. Use [the collection procedure](../docs/evidence-collection.md) on the deployed router, review and sanitize the output, complete the relevant client-side checks, and then add a dated evidence directory.

Use the template that matches the evidence class:

- The [live-validation template](live-validation-template.md) is for router, firewall, DNS/Tailscale, remote-client, and related live-network validation. A row is evidence only after its date, source role, command or method, observation, and verdict have been completed.
- The [endpoint-filtering template](endpoint-filtering-template.md) is for workstation-local Zen, AdGuard for Windows, or comparable endpoint-filter validation. It records baseline/filtered states, DNS-path preservation, HTTPS/root-CA behaviour, compatibility, resource observations, cleanup, and claim boundaries.

Both files are templates only. A template or unfilled placeholder is never validation evidence.

## Published validation timeline

- **2026-09-22 — LAN classic-DNS enforcement prototype:** Fedora was confirmed to route external DNS through the LAN gateway rather than the Tailscale exit node. A temporary `br0` NAT chain then intercepted controlled UDP/53 and TCP/53 queries addressed to `8.8.8.8`, while router-addressed DNS used the return path. The test policy was removed afterward. See the [sanitized prototype validation](2026-09-22/lan-dns-enforcement-prototype-validation.md).
- **2026-09-22 — runtime-drift health-check hardening deployed and live validated:** the revision that detects direct Tailscale NAT rules outside `EDGE_TS_PREROUTING` and unsafe active JFFS hook modes was staged, syntax-checked, test-run, backed up, deployed, and executed from the live path. The active file matched SHA-256 `5d96555bad141c40191855e2f121de0412635cb7e5fe14d41b5ec73842db6233`; final result was `0 failure(s), 0 warning(s)` with `HEALTHCHECK_RC=0`. See the [sanitized hardening deployment validation](2026-09-22/healthcheck-drift-hardening-live-validation.md).
- **2026-09-22 — legacy NAT hook cleanup:** identified a stale `nat-start` containing duplicate direct Tailscale DNS redirects. The direct rules had zero counters because the project-owned `EDGE_TS_PREROUTING` jump was evaluated first. The hook was privately backed up, removed from the active JFFS hooks, duplicate runtime rules were removed, and the deployed health check remained `0 failure(s), 0 warning(s)` with `HEALTHCHECK_RC=0`. See the [sanitized cleanup record](2026-09-22/legacy-nat-hook-cleanup.md).
- **2026-09-22 — updated health-check deployed and live validated:** the post-AUDIT health-check implementation was deployed to the reference ASUS router. The active file matched the repository SHA-256 `e03d6abd7a740524ba5a2c6799a47559ef187b22bb1a3209eb94ffc4a30a7e47`; the live run completed with `0 failure(s), 0 warning(s)` and `HEALTHCHECK_RC=0`. See the [sanitized deployment validation](2026-09-22/healthcheck-deployment-validation.md).
- **2026-09-22 — Diversion ad-blocking A/B/C validation:** compared Standard with SNBForums ad support enabled, Standard with that support disabled, and Large with support disabled. Disabling the SNBForums exception measurably improved DNS blocking, and the Large profile broadened DNS coverage, but visible ads still remained on representative sites despite multiple ad-tech domains returning `NXDOMAIN`. This documents the practical boundary between DNS-domain filtering and browser/content-level ad removal. See the [sanitized Diversion validation report](2026-09-22/diversion-ad-blocking-validation.md).
- **2026-09-22 — AUDIT-02 exit-node NAT ownership:** live packet/counter correlation validated the reference exit-node boundary as project-owned Tailscale forwarding plus platform-owned Asuswrt-Merlin WAN NAT. Raw deployment identifiers were not published. See the [sanitized AUDIT-02 report](2026-09-22/audit-02-exit-node-nat-validation.md).
- **2026-09-22 — AUDIT-03 classic DNS datapath:** controlled Fedora and Android exit-node tests validated classic DNS over UDP/TCP 53 through `tailscale0` -> `EDGE_TS_PREROUTING` REDIRECT -> dnsmasq -> Unbound on `127.0.0.1:53535`. The claim explicitly excludes DoH/DoT and application-specific encrypted resolver transports. See the [sanitized AUDIT-03 report](2026-09-22/audit-03-dns-datapath-validation.md).

- **2026-09-18 — Fedora clean-room Disaster Recovery:** a clean VMware restore reached the recovered Fedora graphical desktop. The validation identified and corrected target `/boot` UUID/GRUB adaptation and SELinux labeling requirements, then revalidated the recovered system. This is host-recovery evidence, not router-live evidence. See the [sanitized Fedora DR validation report](../docs/FEDORA-DR-RESTORE-VALIDATION-2026-09-18.md).

- **2026-09-15 — Stability Gate checkpoint:** read-only checkpoint during the 14-day unchanged-state observation period. The deployed health check returned `0 failure(s), 0 warning(s)` with `HEALTHCHECK_RC=0`; required swap, Entware storage, Tailscale, firewall/ZTNA policy, Unbound/DNSSEC, syslog-ng, and dnsmasq were observed healthy. The targeted recent-error check found no matching OOM, panic, segmentation-fault, I/O, read-only, or filesystem-error entries in the inspected log. See the [sanitized Stability Gate checkpoint](2026-09-15/stability-gate-checkpoint.md). This is an interim PASS, not a long-term-stability claim.
- **2026-09-11 — current router baseline:** sanitized SSD/Entware migration and controlled reboot validation. The underlying migration artifact directly records automatic mounting of both SSD filesystems, active swap, successful Tailscale status with exit-node capability advertised, Unbound running, direct DNSSEC-validated resolution on `127.0.0.1:53535`, and dnsmasq forwarding to local Unbound. It does **not** by itself prove syslog-ng recovery, end-to-end mTLS delivery, firewall/printer behavior, every exit-node traffic path, a complete health-check result, or long-term stability. Start with the recruiter-facing [validated router-state snapshot](ROUTER-STATE-2026-09-11.md), then review the underlying [2026-09-11 evidence](2026-09-11/entware-ssd-migration-validation.txt).
- **2026-09-08 — remote-client validation:** Android over LTE/5G with Tailscale DNS enabled. It records a dated observation consistent with the intended remote DNS path through Tailscale, dnsmasq/Diversion, and recursive Unbound, including normal resolution, DNSSEC validation, and NXDOMAIN blocking of a test advertising/tracking domain. A later 2026-09-22 controlled test resolved the classic-DNS exit-node datapath question, but the 2026-09-08 artifact remains bounded to its own test date and conditions. See the [live validation report](2026-09-08/live-validation.md).
- Earlier dated directories preserve narrower validation snapshots and regression evidence from the deployment process.

The 2026-09-08 Android remote-client test used a Tailscale beta client. The report does not claim that the previously observed stable-client DNS issue has been fixed in a stable Android release.

## Evidence classes

Keep evidence separated by what actually produced it:

| Class | Examples | What it can demonstrate |
|---|---|---|
| CI / mock | shell syntax, config validation, mocked firewall behaviour, recovery tests | repository logic and expected policy behaviour in the test harness |
| Host recovery | Fedora clean-room restore, boot/SELinux recovery validation | observed recoverability of the documented workstation backup in the defined test environment |
| Router live | health check, mounts, processes, firewall counters, DNSSEC query | observed state of the reference ASUS deployment at a point in time |
| Remote client | LTE/5G Tailscale path, DNS resolution, service reachability | observed end-to-end behaviour from a defined client |
| Endpoint filter | Zen or AdGuard test on Windows/Chrome | endpoint-specific content filtering, DNS-path preservation, compatibility and overhead |
| Mobile telemetry | sanitized DNS/traffic observations from a defined phone/scenario | traffic observed for that device, OS, configuration and test window |

Do not merge these classes into a stronger claim than the underlying evidence supports. In particular, endpoint HTTPS/content filtering does not prove equivalent router-side filtering capability.

## Endpoint-filter evidence

Use the methodology in [endpoint filtering validation](../docs/endpoint-filtering-validation.md) and record the run with the [endpoint-filtering evidence template](endpoint-filtering-template.md). A dated endpoint result should identify at minimum:

- test date;
- Windows and browser versions;
- filter product/version and relevant settings;
- baseline state and filtered state;
- DNS-path result;
- HTTPS/certificate result;
- defined YouTube/browser test observations;
- false positives or broken sites observed;
- basic CPU/RAM observations when measured;
- PASS, FAIL, INCONCLUSIVE, or NOT TESTED verdicts.

Do not publish browser profiles, cookies, session identifiers, certificate private keys, exported trust stores, unrelated browsing history, or raw captures containing private sessions.

## Mobile-telemetry evidence

Mobile telemetry is device- and software-specific. Record the phone model, OS/version, relevant hardening/debloat state, network path, test duration, and scenario. Prefer controlled scenarios such as idle, reboot/startup, selected system-app use, and normal interactive use.

A second Xiaomi device with a different model or OS version is an independent comparative case study, not a controlled before/after debloat baseline. Differences may be caused by hardware, OS version, region, installed applications, configuration, vendor services, or hardening choices. State those limitations next to the results.

Historical individual DNS observations may provide context but must not be converted into an invented quantitative baseline.

## Evidence policy

Published evidence must not contain authentication material, private keys, Tailscale identity details, public WAN addresses, device MAC addresses, router serial numbers, DDNS credentials, raw authorization headers, cookies, browser/session tokens, or certificate private material. Raw router logs and packet captures require manual sanitization before publication.

Prefer the smallest artifact that proves the claim. Sanitized text output is usually preferable to a full packet capture or screenshot because it reduces accidental disclosure and makes the evidence easier to review.

Use precise result language:

- **Observed** — directly demonstrated during the documented test.
- **Not observed** — not seen during the documented test window; not proof that it can never occur.
- **Not tested** — no evidence collected.
- **Inconclusive** — available evidence is insufficient or confounded.

A successful controlled reboot and health check demonstrate reboot stability and functional recovery at that point in time. They do **not** by themselves prove long-term stability. The reference deployment's unchanged-state observation was closed on 2026-09-22 after continuous 24/7 powered operation from 2026-09-11 through 2026-09-22; this must not be described as a completed 14-day endurance test.

Subsequent live validation and router changes should remain explicit, bounded maintenance actions with sanitized evidence and rollback planning where state changes are involved.
