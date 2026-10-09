# Disaster Recovery — navigation and current validation boundary

**Status:** CURRENT navigation only (not a separate restore procedure).  
**Reviewed:** 2026-10-09  
**Tracking:** [#129 — Pi-hole-aware Disaster Recovery](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129) **OPEN**; [#100 — historical router DR baseline](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/100) completed.

For **current deployment status**, start at [PROJECT-STATUS](../PROJECT-STATUS.md). For the hierarchy of evidence and instructions, use the [documentation model](documentation-model.md). This page is a **reading map**: it does not replace the manuals or repeat shell commands.

## Which document to use?

| Need | Authoritative document | Scope |
|---|---|---|
| Understand what a backup covers / excludes | [Router disaster-recovery baseline](router-disaster-recovery.md) (EN) | Current coverage matrix, off-router artifacts, source-of-truth boundaries and gaps |
| Rebuild the Pi-hole-aware stack step by step | [Pi-hole reconstruction runbook](pihole-dr-rebuild-runbook.md) (EN) | Gates 0–5, dependency order, rollback/STOP criteria, FTL capabilities and DNS acceptance |
| Recover an empty ASUS TUF-AX5400 and SSD | [Polish bare-router emergency guide](router-bare-metal-recovery-pl.md) (PL) | Operator-oriented adaptation; **not** a successfully executed blank-router drill |
| Generate and verify private Pi-hole recovery archives | [Pi-hole DR generator reference](pihole-dr-generator.md) (EN) | Allowlisted backup content and archive verification contract |
| Inspect rebuild metadata capture | [DR manifest collector](../scripts/collect-dr-manifest.sh) | Source-controlled read-only inventory tool, not the private backup itself |
| Review 2026-10-09 actual router reboot | [Controlled reboot evidence](../evidence/2026-10-09/issue-129-pihole-dr-reboot-persistence.md) | Existing-router startup and DNS Guard persistence **PASS**, not a fresh restore |
| Review 2026-10-09 package rebuild | [65-package offline clean-room evidence](../evidence/2026-10-09/issue-129-offline-pihole-opkg-cleanroom.md) | Recursive 65-IPK closure and real `opkg --offline-root` ARMv7 container installation **PASS**, not router boot/DNS |
| Follow the engineering chronology | [Worklog 2026-10-09](worklog/2026-10-09.md) | Historical activity, distinct from acceptance evidence |

The [Polish documentation index](pl/README.md) groups translated/adapted operator guides. **English** is the canonical recovery contract; the Polish bare-router guide is a reviewed operator adaptation, not a certified literal translation. If safety gates differ, stop and reconcile with dated evidence.

## What is proved, and what is not?

| Tested scope | Status as of 2026-10-09 |
|---|---|
| Three private encrypted backups and their SHA-256 sidecars | PASS for integrity/decryption checks; **CFG import not tested** |
| CORE alternate-root file restore | PASS in disposable Fedora `tmpfs`: **39 restored files**, not the unrelated 41-entry manifest stream check |
| Pi-hole archive / Gravity / private file restoration | PASS for selected offline checks and staged files; target UID/GID/xattr reapplication not validated in the same exercise |
| Pi-hole package availability | PASS: **65 exact-version IPKs** with SHA-256, **340** declared dependency groups, none missing |
| Pi-hole package-manager reconstruction | PASS: offline, rootless ARMv7 Podman `opkg` install, **65 installed status records** and FTL SHA-256 |
| Existing production router restart | PASS: services persisted and project healthcheck had **0 failures / 0 warnings** |
| **Full replacement router/blank SSD firmware → restored DNS/DHCP/API** | **NOT TESTED** |

**Next recovery gate:** on a disposable rebuilt target, validate service account **999:999**, restored modes and the seven FTL `security.capability` bits, deferred maintainer-script effects, Gravity restoration, Unbound → Pi-hole DNS, DHCP/reverse lookup, DNS Guard and post-recovery reboot. Maintain physical fallback management access. **Do not run `restore.sh --apply`, `setcap`, CFG import, formatting or experimental reboot on the healthy production router.**

## Private materials and change control

Encrypted `.gpg` backups, native CFG, IPKs, credential/API state, detailed operator logs, Tailscale auth material and private SHA-256 manifests are stored **off-router and outside the public Git repo**. Public `evidence/` files record sanitized observations, never package payloads or secrets.

A documentation-only merge or green CI run does **not** mean deployment/restore took place. Keep #129 OPEN until an actual compatible isolated blank-device exercise satisfies its acceptance gates. Do not substitute the different historical checkpoint [#200 permission hardening](../evidence/2026-10-09/issue-200-final-permissions-acceptance.md) for a recovery test.
