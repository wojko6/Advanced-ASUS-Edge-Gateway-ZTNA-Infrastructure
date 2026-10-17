# Issue #235 — production GO/NO-GO and recovery decision (2026-10-15)

**Decision: NO-GO / HOLD.** Draft PR #245 remains unmerged and none of its helper, private UUID files or insertion is installed on the reference ASUS. No production chmod, mount operation, hook edit, package installation, daemon restart or reboot is authorized by this document. The purpose of this document is to record evidence and operator review gates, **not** to provide a one-shot deployment command.

## Accepted evidence

| Review item | Status | Scope and limitation |
|---|---|---|
| Cause of mode regression | PASS (source + observed behavior) | GNUton firmware calls chmod 0777 on mount root and then post-mount. This is not a binary runtime trace. |
| Both ext4 SSD mounts, identity, mode | PASS | Read-only: both root:root 0777, unique device paths, stable valid distinct UUIDs. |
| Local expected UUID files | PASS | Prepared offline, independently audited, private directory 0700 and files 0600, integrity manifest; **not transferred to JFFS**. |
| Firmware-native helper executable dependencies | PASS (already-booted router) | BusyBox ls -ldn, /usr/bin/awk, /sbin/blkid, /bin/chmod work; no reliance on Entware stat. Early-boot timing remains untested. |
| Isolated candidate tests and CI | PASS | Synthetic block devices, directories, fail-closed parser cases, and swap-before-AMTM fixture; no production mount test. |
| Private post-mount composition | PASS | Independent original hash, exact pinned snippet byte insertion, original swap-before-AMTM source sections, sh -n; candidate only on Fedora. |
| Active JFFS post-mount baseline | PASS | Read-only hash twice, root:root 0755, syntax PASS; live source unchanged. |
| SSD runtime snapshot | PASS | Both mounts ext4/root 0777, protected RouterCloud and Entware children, exactly one active swap entry per volume. |
| Service identities | PASS (snapshot only) | dnsmasq 1 root + 1 nonroot; Unbound 1 nonroot; tailscaled/syslog-ng/Dufs sampled as root. |
| Resolver SSD FD snapshot | PASS (snapshot only) | Neither sampled nonroot resolver had a mount-root/first-level FD; Unbound had one nested FD; no future writer proof. |
| Independent protected original hook backup | PASS (partial DR scope) | Validated private Fedora copy and separate encrypted/offline external backup; not proof of live JFFS restore. |

## Material blockers before production GO

1. **Writer and service compatibility: OPEN.** Confirm expected non-root direct root-level create/rename/remove activity is absent or explicitly accept the residual uncertainty, especially scheduled jobs and firmware tools. The repo's forced-command RouterCloud rsync targets a protected child, not the mount root. A static code search and sampled FDs cannot prove all possible writes.
2. **Private UUID mapping installation contract: OPEN.** The draft insertion now **actively checks** each JFFS ancestor `/jffs`, `/jffs/addons`, `/jffs/addons/asus-edge`, `bin` as real non-symlink `0755 root:root` directories, the private directory as real `0700 root:root`, the expected UUID file as regular non-symlink `0600 root:root`, and the helper as regular non-symlink `0755 root:root` through firmware-native `/bin/busybox ls -ldn`; it refuses to call the helper if any gate fails while preserving swap and AMTM. **CI and exact on-router early-boot execution still need acceptance.** A separate predeployment copy/integrity and ownership check is still mandatory; private Fedora source files are not deployed automatically.
3. **Helper delivery contract: OPEN.** Root-owned regular non-symlink `/jffs/addons/asus-edge/bin/issue235-ssd-mount-mode`, executable mode 0755, byte-integrity against the vetted pinned PR commit, direct native-tool availability, correct allowlist and a reviewed rollback source. No whole-project installer.
4. **Narrow JFFS hook update and independent rollback rehearsal: OPEN.** The active baseline and private copy are known, but a real JFFS same-filesystem atomic-rename, owner/mode verification and recovery path have **not** been exercised on production. Do not directly append/truncate/overwrite the live event hook; any authorized operation must stop on baseline SHA drift and preserve the active custom hook's entire source. Explicitly preserve swap-before-AMTM in both the normal and recovery paths.
5. **Service startup health and backup checks after scoped activation: PENDING AUTHORIZATION.** Require both active swap entries, expected mount roots, protected child directories, Entware, DNS/dnsmasq/Unbound/Pi-hole, Tailscale, RouterCloud, rsync/backup, logs and monitoring, plus a no-restart check where feasible. Any unexpected regression triggers STOP/rollback rather than further changes.
6. **Separately approved reboot/remount persistence: NOT AUTHORIZED.** Needed to validate ordering, fresh firmware 0777 write followed by late 0755 repair, both swaps before AMTM/Entware and all dependent services. A live-mode check prior to reboot is insufficient. Hotplug/remount is a different future test with separate risk approval.
7. **Custom services-start ownership issue: OUT OF SCOPE / OPEN.** Live hook is owned by UID:GID 1000:1000, 0755 and byte-differs from managed bin. NEVER run the generic `scripts/install.sh` for this narrow Issue #235 change: its `install_hook` rewrites `services-start` and can preserve unexpected existing file ownership. Do not change live services-start, its owner or other startup code in this scope.

## Guardrails for a *future explicitly authorized* maintenance

- **Before any change:** verify trusted local admin wired access independent of Tailscale/Pi-hole; backups and off-router decryption availability; fresh baseline SHA/owner/mode; two SSD mount identities; both swap entries; staging artifacts and private UUID integrity; no conflicting AMTM/installer maintenance; adequate JFFS free capacity.
- **Narrow stage first:** install only exact reviewed helper and private UUIDs in already approved JFFS locations with explicit owner/mode and byte checks; stop if a component exists unexpectedly. Staging is different from activation.
- **Activation only with separate operator authorization:** atomically replace only `post-mount` using a verified same-JFFS staged file; retain untouched original in safe private off-router storage; reverify owner root:root, mode 0755, syntax and expected hash before any execution. Never call `post-mount` manually to test.
- **No automatic restarts/reboots:** validate non-disruptively after any authorized activation; root-mode repair might only execute on the NEXT mount event. Do not claim it has run until observed.
- **Rollback decision:** if activation breaks startup or an acceptance gate fails, restore the exact original `post-mount` with an independently verified source and atomic same-filesystem replacement, root:root 0755; validate hash and sh -n. Remove staged helper/UUID artifacts only after dependency review and explicit scope approval. Restoration of the old hook does not itself revert already changed SSD inode permissions, and on a future mount the firmware may again write 0777; log that security tradeoff.
- **Do not force mode 0777 as an emergency default** and do not modify private RouterCloud subtrees, services-start, swap, Entware, or SSD files to conceal a failed gate. If router accessibility depends on the malfunctioning service, use local Ethernet/WebUI and the independently tested recovery path.

## 2026-10-15 draft hardening follow-up (not deployed)

The security review identified the missing runtime owner/mode checks in the first snippet version. Draft PR #245 now requires absolute firmware-native numeric `ls -ldn` for the JFFS root/ancestor chain, private UUID directory/file and helper, rejects symlinks, and leaves the original swap-before-AMTM path running on failed metadata. The synthetic composed test adds wrong mode and symlink cases. This is **draft-only** until CI confirms the test results and the operator independently verifies firmware boot compatibility. The previous V2 byte-exact local `post-mount` candidate embeds an older snippet and remains **STALE**. A new V3 private Fedora candidate has now been independently built from the verified original plus the updated snippet pinned at commit `be191e1098a5145d58e38baceebf061190ce11a9`; operator reports independent full-byte and manifest parity PASS and an isolated Fedora-only same-directory atomic replacement/rollback PASS. The V3 source and original are unchanged. **These are not live JFFS delivery, root:root ownership or production restore tests.** The encrypted original hook backup remains valid; no actual router change occurred.

## 2026-10-15 independent V3 gate and approved-scope separation

V3 private candidate, pinned blob identity, shell syntax, exact original-plus-snippet bytes, local file privacy, manifest and independent synthetic atomic replace/restore on Fedora were all reported PASS. The lab proved original digest/mode restoration only on **Fedora**. No router connection or modification occurred. This closes the offline candidate and local rollback simulation gates but not full JFFS atomicity, owner:group 0:0 delivery, boot ordering or SSD writer behavior after 0755.

Use the new [scoped JFFS staging / activation / rollback DRAFT runbook](issue235-jffs-staging-activation-rollback-runbook-draft.md), which requires **separate approvals** for payload staging, event-hook activation and reboot persistence, while keeping unrelated custom services-start untouched. **Production decision remains NO-GO/HOLD.**

## Limits and related tracks

The project has previously detected three separate world-writable RouterCloud subtrees under ROUTER_DATA; this narrow patch does not secure those internal directories. The external encrypted backup and local dry-run restore do not establish full bare-metal DR, which remains tracked by Issue #129. The firmware source-backed issue is specific to this GNUton build and needs revalidation following firmware change.

**Acceptance:** GO requires every material blocker to be resolved, the residual risk explicitly accepted and a separate operator approval for scoped production installation. A later reboot needs another explicit approval. Absent these, remain HOLD.

Evidence and implementation: [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235), [Draft PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245), [detailed post-mount review](issue235-ssd-mount-postmount-repair.md), and [startup-order guide](architecture/boot-service-dependency-flow.md).


## 2026-10-17 — Stage B Fedora design-gate review

The operator-reported isolated Fedora staging progression is now complete as a **design/test-fixture gate only**:

| Evidence (synthetic Fedora only) | Result | What it does NOT establish |
|---|---|---|
| Initial file creation / no overwrite / symlink and insecure-parent refusal | **6/6 PASS** | JFFS/GNUton transfer, root:root ownership |
| Single-file staged publish / simulated exception / no target replacement | **7/7 PASS** | Sudden power-loss durability, all-file transaction, JFFS hardlink support |
| Directory-FD trust / ancestor swap detection / orphan handling | **9/9 PASS** | A portable production JFFS stager, race-free router implementation |
| Byte-exact V3 original+snippet composition recheck | **6/6 PASS** | Manifest revalidated this session, production activation or in-boot behavior |

The fresh V3 integrity check reconfirmed the saved original's expected SHA-256 and the current guarded snippet Git blob; the previous apparent FAIL arose from confusing **2803 Unicode characters** with **2805 UTF-8 bytes**. Both corrected checks PASS; no source rewrite needed. The earlier independent V3 manifest audit and Fedora-only atomic replacement/rollback simulation were already recorded PASS on 2026-10-15; these historical gates were **not newly rerun** on 2026-10-17.

Design requirements were added to the [scoped JFFS Stage B runbook](issue235-jffs-staging-activation-rollback-runbook-draft.md): strict target/owner/mode allowlist; pinned payload provenance; trusted non-symlink directory ancestry; verified complete same-filesystem temporary files; explicit **no-clobber** publication; verify after publish; refuse ambiguous partial stage, symlink collisions, changed parents and orphan temp entries; do not automatically overwrite or delete anything. Fedora Python `dir_fd` / `os.link` behavior is a laboratory model, **not** a validated router primitive. If the implementation cannot provide the required filesystem/ownership guarantees on real JFFS, **Stage B must remain blocked**; simply replacing those operations with ordinary `mv` is not an accepted workaround.

**Updated decision matrix:**

| Decision gate | Status on 2026-10-17 |
|---|---|
| Offline safety *design and mock behavior* | **PASS, closed at design level** |
| Production-ready scoped Stage B delivery mechanism | **OPEN: not implemented/reviewed for JFFS** |
| Scheduled/transient mount-root writers and remaining mode-0755 compatibility risk | **OPEN: static scans and process snapshots only** |
| Remaining first-level 12 files `0666` and 3 directories `0777` | **INDEPENDENT audit: [Issue #263](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/263)** |
| Fresh pre-maintenance JFFS original/UUID/backup/boot-path gate | **PENDING: must repeat at authorized window** |
| Explicit authorization for payload staging (B), hook activation (C), reboot/remount (E) | **NOT GRANTED** |
| Production root-mode change or any service/reboot action | **NOT EXECUTED / HOLD** |

**No scope expansion:** PrivDrop, UID/GID/DAC migration, SSD Trust Helper, unrelated RouterCloud worktrees and custom `services-start` remain out of scope. Do not edit those mechanisms from this branch's Stage B design work. Neither staged helper/UUID payloads nor a modified `post-mount` have been installed on production. **Issue #235 OPEN / Draft PR #245 / DEPLOYMENT_GATE=HOLD.**


## 2026-10-17 — Stage B v1.3 and authenticated manifest design gate

- **Fedora LAB PASS:** Stage B v1.3 importer **26/26** and preserved v1.2 regression **60/60**, with ARMv7 static soft-float/QEMU and Clang ASan/UBSan PASS, all using synthetic data. No real UUID, router JFFS or root:root delivery was exercised.
- **Independent provenance OPEN:** compiled synthetic manifest hash does **not** authenticate real production file origins. No reviewed independent production manifest trust anchor, secure input channel or source snapshot exists.
- **Device semantics OPEN:** sequential three-file publication is **not** a bundle transaction. JFFS2 no-clobber/`linkat`, directory fsync/durability, partial-state reconciliation, actual root ownership and concurrent writer safety remain unverified.
- **Design reference:** [Stage B payload provenance, three-file state machine and recovery](issue235-stageb-payload-provenance-recovery-design-draft.md) (DRAFT; no implementation approval).
- **Permissions unchanged:** B staging, C post-mount activation and E reboot/remount require **separate explicit operator approvals**; no production change, no PR merge. `DEPLOYMENT_GATE=HOLD`.
