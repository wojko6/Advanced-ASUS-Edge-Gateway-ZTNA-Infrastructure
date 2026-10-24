# Unbound 1.26.2 / Disaster Recovery post-audit documentation reconciliation — 2026-10-24

> **Classification:** documentation and non-deployed example comments only. Review base: public `main` `b497f0edddf2e2d7f4f0e56176d4a654c913b9c5` (merged PR #300). No ASUS or Fedora command, DNS lookup, package transaction, restore, reboot, mode/owner change, firewall, monitoring, RouterCloud, or live configuration edit was performed for this correction.

## Why the corrections were needed

The deep repository audit found that older DR procedures treated the top-level `/opt/var/lib/unbound` directory as `65534:0 0755` and recommended changing its owner on a rebuild. That contradicted the later observed production Unbound 1.26.2 R2 chroot root `root:root 0755`, with a separate `dnssec-auto` writable parent `65534:65534 0700`. The pre-failure historical directory owner/mode is still UNKNOWN.

The same-day initial upgrade/rollback failed at the RFC 5011 auto-trust-anchor sibling-write boundary; a separate authorized R2 upgrade **later passed** five-IPK version checks, direct DNSSEC good AD and bogus SERVFAIL on UDP/TCP, router/Pi-hole client-path checks, and one **real post-R2 functional reboot**. The anchor file was later found `65534:65534 0666` within a private `0700` directory. This is a **known unresolved hardening exception**, **not** a validated restore target or proof of power-loss cold boot. The actual production daemon umask was never measured.

## Files and intended effect

| Scope | Correction | Limit |
| --- | --- | --- |
| [Current DR baseline](../router-disaster-recovery.md) | Replace the superseded `chown 65534:0` top-level chroot recipe with chroot/anchor-directory separation and explicit STOP conditions. | No empty-router DR PASS. |
| [Pi-hole runbook](../pihole-dr-rebuild-runbook.md), [Polish blank-router guide](../router-bare-metal-recovery-pl.md), [DR navigation](../disaster-recovery-index.md) | Restore gates now refer to current five `1.26.2-1` packages, manager integration and active RFC 5011 writable-directory contract. | 65 IPK Pi-hole archive is a historical *different* scope. |
| [Compatibility](../compatibility.md) | Record Unbound R2 with functional reboot and file-mode/Manager HOLD. | Not proof of all platform combinations. |
| [Standalone configuration](../../config/unbound.conf.example), [README](../../README.md), [PL deployment](../deployment-pl.md) | **Keep** the standard Entware example path but mark it separate from active manager-owned `dnssec-auto`; prevent blind copying into Manager runtime. | No changed live config or untested automatic migration. |
| [Unbound case study](../case-studies/unbound-dnssec-autotrust-opkg-incident-2026-10-24.md) and [DNS Guard/Grafana case study](../case-studies/dns-guard-grafana-alert-delivery-dns-failure-2026-10-24.md) | Correct post-merge publication status of [PR #297](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/297); keep interim checklist labeled as historical. | Incidents and evidence not rewritten. |
| [Evidence navigation](../../evidence/README.md), [PL index](../pl/README.md), [document rules](../documentation-model.md) | Link October 24 reports that already exist under `docs/`; document source precedence. | No synthetic `evidence/2026-10-24/` folder or test output. |
| [English network design index](../network-design.md) | Two Polish PDF captions translated to English. | PDF contents unmodified. |

## Acceptance and remaining issues

- **Accepted earlier, operator-reported:** R2 production Unbound `1.26.2-1` 5/5, direct UDP/TCP DNSSEC AD/bogus SERVFAIL, one later functional reboot. System resolver unplanned fail-open/failback observed during previous outage.
- **Not accepted:** automatic LAN/Tailscale client DNS continuity, independently resilient Fedora alert transport, controlled DNS Guard fault-injection, multi-reboot/power-loss cold boot, full device/SSD restore, RFC 5011 30-day promotion, production anchor-mode fix.
- **Open:** #129 full recovery; #298 anchor file permissions; #299 Manager/PID compatibility. Issue #235 privileged-hook/SSD trust, #278 installer atomicity, #287 timer-lifetime and independent RouterCloud/Dufs workstreams remain separately held. No crossing into Draft PRs #202/#226/#245/#270.
- **Source:** [production R2/reboot](../operations/unbound-1.26.2-production-deployment-2026-10-24.md) · [incident](../case-studies/unbound-dnssec-autotrust-opkg-incident-2026-10-24.md) · [public chronology](../worklog/2026-10-24.md).

**Publication gate:** structural Markdown/path validation and CI are static-only. They do not show an actual resolver start or restoration from blank hardware. Review the documentation-only diff before merge; do not change production permissions or close open recovery/hardening issues because a documentation PR passes CI.
