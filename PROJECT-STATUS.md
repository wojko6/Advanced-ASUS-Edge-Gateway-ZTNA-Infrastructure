# Project status

**Status date:** 2026-09-18  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin  
**Current phase:** unchanged-state stability observation and audit remediation

## Executive status

The reference deployment is operational and is currently inside the 14-day unchanged-state stability observation window that began on 2026-09-11 and is scheduled to complete on 2026-09-25.

The project currently has a validated SSD-backed Entware deployment, Tailscale-based remote access and exit-node capability, Unbound/DNSSEC integration, dnsmasq integration, syslog-ng logging, project-owned least-privilege firewall chains, recovery tooling, health checks, evidence collection, and automated repository validation.

The stability gate deliberately separates a successful point-in-time deployment from a claim of long-term stability. Until the observation window completes, the reference router is kept unchanged except for recovery or security intervention. Repository-only work, CI/static/mock validation, documentation, endpoint testing, and read-only router observations may continue.

## Current validated baseline

The 2026-09-11 controlled reboot and post-migration validation established the current baseline. The final health check for that session reported:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

A later sanitized stability checkpoint retained a healthy router state without changing the reference configuration. These snapshots are point-in-time evidence and are not substitutes for completion of the stability gate.

Key validated areas include:

- persistent SSD-backed Entware storage and swap;
- Tailscale service availability and intended `netfilter-mode=off` architecture;
- project-owned IPv4 filter/NAT chains and fail-closed IPv6 guards;
- Unbound availability and DNSSEC validation;
- dnsmasq integration with the intended local Unbound listener;
- syslog-ng availability;
- printer exposure hardening;
- backup/recovery and evidence tooling;
- CI/static/mock validation of configuration, firewall, WAN recovery, installer rollback, restore validation, and maintenance paths.

## Stability gate

**Window:** 2026-09-11 through 2026-09-25.

During the gate:

- no intentional router reboot unless recovery requires it;
- no package, DNS, firewall, filtering-list, startup-hook, or service configuration changes;
- no deployment of audit remediations to the reference router;
- router-side corroboration is read-only;
- endpoint and repository work may continue when it does not alter router state.

The final gate review will evaluate uptime, memory/swap, SSD mounts, Tailscale, Unbound/DNSSEC, dnsmasq, syslog-ng, project health checks, and logs for crashes, OOM events, unexpected restarts, WAN/DNS recovery failures, and storage errors.

If a recovery or security intervention changes the validated router state, record the intervention and restart the unchanged-state baseline after recovery.

## Security/code audit remediation status

A full repository audit covered code, security, install/rollback, firewall/DNS/Tailscale behaviour, logging, backup/recovery, tests/CI, documentation, evidence/privacy, and portfolio presentation.

| Finding | Status | Current state |
|---|---|---|
| AUDIT-01 — restore apply was not transactional | **CLOSED** | Restore now snapshots affected live paths and rolls back partial apply failures; regression coverage was added and CI passed. |
| AUDIT-02 — exit-node NAT dependency not explicitly validated | **OPEN / GATED** | Documentation now states that project forwarding does not itself prove WAN SNAT/MASQUERADE ownership. Read-only inspection and post-gate live validation are required. |
| AUDIT-03 — Android/Fedora exit-node DNS datapath validation gap | **OPEN / GATED** | A controlled comparison procedure is documented. Exact client-to-router resolver paths must be demonstrated after the stability gate rather than inferred from successful DNS resolution. |
| AUDIT-04 — unnecessary deployment identifiers in Zen evidence | **CLOSED** | Evidence was sanitized while preserving the technical result. |
| AUDIT-05 — Android DNS datapath claim exceeded available evidence | **CLOSED** | README wording now preserves the historical observation while explicitly documenting the unresolved datapath question. |

The two remaining findings are not documentation-only defects that should be closed by assumption. They require evidence from the actual reference datapath.

## Post-gate validation plan

After the unchanged-state window completes successfully:

1. capture the final stability-gate evidence and produce a sanitized checkpoint/report;
2. validate AUDIT-02 by identifying the effective IPv4 WAN NAT rule/chain used by authorized Tailscale exit-node traffic and correlating it with the real packet path;
3. validate AUDIT-03 with a controlled Fedora/Android comparison using the same router state and exit node, separating classic DNS from encrypted/client-specific resolver paths;
4. make no configuration change unless the evidence demonstrates a real defect;
5. if a change is required, design the smallest remediation, test it in an isolated/planned maintenance context, deploy it deliberately, then repeat affected validation;
6. close the audit findings only when sanitized evidence supports the conclusion.

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

## Current decision

As of 2026-09-18, no additional router-side remediation is justified during the active stability gate. The correct engineering action is to preserve the reference state, continue observation, improve repository/test/documentation quality offline where useful, and defer AUDIT-02/AUDIT-03 live closure until the gate has completed.
