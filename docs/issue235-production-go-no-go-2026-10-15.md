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
2. **Private UUID mapping installation contract: OPEN.** Root-owned JFFS ancestors remain 0755; proposed private UUID directory must be a real directory, `0700 root:root`, each UUID file must be regular, non-symlink, `0600 root:root`, and content/hash must match the independently verified private local originals. These restrictions must be checked before activation and at the maintenance gate. The current snippet checks existence/non-symlink/readability, **not owner/mode by itself**; unsafe ownership/mode must STOP deployment rather than be silently accepted.
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

## Limits and related tracks

The project has previously detected three separate world-writable RouterCloud subtrees under ROUTER_DATA; this narrow patch does not secure those internal directories. The external encrypted backup and local dry-run restore do not establish full bare-metal DR, which remains tracked by Issue #129. The firmware source-backed issue is specific to this GNUton build and needs revalidation following firmware change.

**Acceptance:** GO requires every material blocker to be resolved, the residual risk explicitly accepted and a separate operator approval for scoped production installation. A later reboot needs another explicit approval. Absent these, remain HOLD.

Evidence and implementation: [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235), [Draft PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245), [detailed post-mount review](issue235-ssd-mount-postmount-repair.md), and [startup-order guide](architecture/boot-service-dependency-flow.md).
