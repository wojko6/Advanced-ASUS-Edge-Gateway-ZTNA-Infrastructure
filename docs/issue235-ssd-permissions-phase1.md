# Issue #235 — SSD directory-entry integrity and RouterCloud least-privilege plan

**Status:** DESIGN / ISOLATED TEST ONLY — not approved for the production ASUS.  
**Evidence cutoff:** 2026-10-14 (operator-reported read-only snapshots).  
**Scope:** production ASUS TUF-AX5400, shared `ROUTER_DATA` ext4 SSD partition and RouterCloud state.  
**Tracking:** [infrastructure issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235); [Dufs draft PR #4](https://github.com/wojko6/dufs/pull/4). Neither the source PR nor this branch constitutes deployment approval.

## Confirmed baseline (read-only)

| Observed item | Owner/mode and capability | Interpretation |
| --- | --- | --- |
| Shared data-partition mount root (also DATA_PARENT) | root:root `0777`, **non-sticky**; ext4 mounted `rw,nodev`, without `nosuid` | Locally writable parent permits directory-entry changes. This is an integrity exposure, not evidence of remote exploitation. |
| RouterCloud serve/data root | root:root `0700` | Direct access by an ordinary UID is denied, but its entry is under the writable mount root. |
| `.routercloud-system` direct child of mount root | root:root `0777`, **non-sticky** | Leaf names underneath this directory are exposed to local rename/replacement. |
| `favorites`, `password-reset`, `password-overrides` | root:root `0700`; state symlinks observed: zero | Leaf traversal blocked to ordinary UID. Does **not** protect each leaf *name* from its writable parent. |
| Trusted Metro assets | root:root `0755` | Unprivileged read/traverse YES; write NO. |
| RouterCloud YAML configuration | root:root `0600` | Unprivileged read NO, including a future service account until access is deliberately engineered. |
| Live Dufs executable | root:root `0755` | Executable by ordinary UID. This is not proof that the service will start or function nonroot. |
| Optional versioned JFFS BusyBox | root:root `0700` including directory | Use only **before** changing identity. Do not grant other users execute rights as a diagnostic workaround. |

A separate live test with the hash-verified BusyBox changed a *temporary child process* to UID/GID 65534 and showed CapEff/CapPrm zero; prctl independently reported `no_new_privs=1` before dropping UID. One supplementary group was 65534, not zero. An earlier attempted post-drop re-execution of root-only BusyBox returned 126 as expected. The active RouterCloud daemon itself **has not been migrated** and remains root-run.

The mount root contains 20 direct entries: 18 other than the known data and state entries. Four direct subdirectories were confirmed root:root `0777` **without sticky bit**; one is `.routercloud-system`, three are still anonymized `OTHER` directories (9/6/1 direct entries). Literal references in inspected Entware/Merlin init scripts: zero for all three. A `/proc` cwd/open-fd snapshot of 150 observed processes likewise found zero matches. **Neither scan proves unused status** (idle jobs, dynamic paths, other configs, unavailable links, namespace paths, symlinks and future mounts were not excluded). Top-level symlink count was zero in the snapshot.

## Dependency boundaries and do-not-break list

- **RouterCloud sync:** Fedora rsync through a restricted, exact-allowlist Dropbear forced command to `ROUTER_DATA/RouterCloud`; existing data root requires careful writable-access handling after future service UID changes. Source: [personal-cloud-sync.md](personal-cloud-sync.md), [personal-cloud-rsync](../router/scripts/personal-cloud-rsync).
- **Versioned backups:** separate read-only SSH/rsync identity and Fedora staging, then encrypted restic snapshots to independent local storage. The forced-command read path must continue to work. Source: [routercloud-versioned-backup.md](routercloud-versioned-backup.md) and [personal-cloud-rsync-backup](../router/scripts/personal-cloud-rsync-backup).
- **Mount/boot:** Entware and ROUTER_DATA are different ext4 SSD partitions. The data partition hosts additional swap; on the reference router, post-mount must activate swap before the relevant Entware startup path. Source: [ENTWARE-SSD-MIGRATION.md](ENTWARE-SSD-MIGRATION.md), [boot-service-dependency-flow.md](architecture/boot-service-dependency-flow.md).
- **Other consumers:** the three `OTHER` directories are not identified and must **not** be deleted, recursively chmodded, or presumed idle. A shared root mount may host special files, downloads, logs, addons or periodic jobs.
- **Security:** maintain existing UI origin protections, LAN/Tailscale-only scope, YAML secrecy and private persistent password state. Scope does not include DNS, Unbound, Tailscale, DHCP, firewall, or router firmware changes.

## Threat model

Linux DAC for a directory entry is enforced on its **parent directory**. A root-owned `0700` child does not prevent a different UID from renaming/unlinking its *name* when the parent is `0777` and has no sticky bit. This exposes path integrity even if it does not disclose protected contents. Trusted data remains inaccessible to normal read syscalls, but a root-run service resolving a substituted path is a higher-value potential consumer. A zero-symlink inventory does not preclude later replacement.

The sticky bit on a writable directory (e.g. `1777`) prevents ordinary users from renaming/removing entries they do not own, while still allowing users to create their own entries. It **does not** prevent creation, disk-filling, replacement of an attacker-owned entry, or operations below a separate `0777` child directory. It is only a defense-in-depth candidate, not a complete repair for unknown users and their files.

## Phase 1A — isolated design and testing (NOW)

1. Use synthetic directories only. The root-owned temporary SSD mount root, state directory and favorites leaf are created under a disposable temporary fixture.
2. Test at least five DAC combinations: `0777/0777` baseline, `1777/0700` transitional, `0755/0700` restrictive, `1777/0777` partial, and `0777/0700` partial. As UID 65534 test rename of root-owned state and favorites directory entries, and creation of a new mount-root entry.
3. Require expected allow/deny observations and automatic test-fixture cleanup. The regression harness: [test-issue235-ssd-dac.py](../tests/test-issue235-ssd-dac.py).
4. Execute this **independently on Fedora** as a reviewed local test (requires sudo for an ephemeral UID switch). A successful container Linux test alone is not Fedora/ASUS acceptance.

## Phase 1B — mount/state hardening decision (NO GO on production yet)

Two candidate modes for the shared mount root:

| Variant | Root mount mode | State root mode | Benefit | Limitation |
| --- | --- | --- | --- | --- |
| Transitional compatibility | root:root `1777` | root:root `0700` | Blocks ordinary-UID rename of root-owned state and other root-owned top-level entries while preserving direct top-level creation | Other users still can create entries and fill disk; the three other `0777` directories remain vulnerable within their own children. |
| Preferred restrictive target **when consumers permit** | root:root `0755` | root:root `0700` | Denies unprivileged creation at mount root and prevents replacement of state entries | May disrupt unknown users/services that need direct mount-root write. Requires affirmative consumer mapping. |

**Do not choose either simply because a /proc scan saw zero live file handles.** Identify all direct root-mount writers, ownership models, mount remount scripts, backup and restore expectations, and behavior after clean boot. Inspect effective ACL and mount options if available. Restrict the state root without *first* protecting its mount-root parent leaves a rename vector. Protecting only the mount root without restricting state itself leaves the favorites/password state entry vector.

Other `OTHER` directories must have a separate owner/consumer decision before any changes; their existing 0777 mode is an open issue, not a reason to change all recursively.

## Stage-gated production procedure (NOT AUTHORIZED OR EXECUTED)

**Preflight:** verified off-router recovery backup and permission/owner manifest (include swap file exclusion/handling); exact active mount identity, existing user/group owners, and all direct writers inventoried; tested Fedora fixture and service compatibility; documented maintenance window, health baseline and clear operator go/no-go decision.

**Controlled stage 1:** with explicit approval, apply only the *selected* nonrecursive mount-root and state-root protections; avoid touching live data-root contents, init, YAML, backup keys, other three directories, DNS, and network services. Check with actual nonroot path-entry challenge and no post-change symlink/unwanted path substitution.

**Acceptance:** RouterCloud HTTP/S login and file browse, Metro asset rendering, favorites create/read, reset flow, active data sync over restricted rsync, readonly backup, swap availability and boot/startup behavior as scheduled, and absence of health regressions. Use synthetic actions that do not expose actual user secrets. A full reboot is not included without separate approval.

**Rollback:** record pre-change owner/mode/ACL and hashes of relevant service/init/config inputs, preserve trusted rollback material off the data root, and specify both stop conditions and restoration procedures. **Do not automatically or silently restore world-writable `0777` merely to recover service availability**; that would reintroduce the integrity weakness. Restoration of an insecure baseline is an explicit, exceptional risk decision with compensating controls.

## Phase 2 — separate, later RouterCloud UID-drop rollout

After stage 1 is validated in production: design a **dedicated persistent** UID/GID `routercloud` rather than shared `nobody`; consider restricted config visibility (e.g. `root:routercloud 0640` only after explicit review), asset root-owned read-only, private data/state access `0700/0600` with secure ancestors, backup/sync interoperability and Entware/JFFS mount sequence. Use verified optional BusyBox launcher **before** UID/GID drop. Check actual child's identities, supplementary groups, effective/permitted caps and prctl NNP, not the unavailable Linux 4.1 `NoNewPrivs` proc-status field. Validate logout, sessions, favorites, reset and rollback. DUFS PR #4 must undergo its own release gate and binary reconciliation; it is not merged or deployed.

## Current status and decision

- Isolated Linux fixture five-scenario gate: **PASS** on 2026-10-14 in a temporary Linux test environment; **Fedora operator execution on 2026-10-14: PASS (all five scenarios)**. Reported individual results: `0777/0777` state rename ALLOW, leaf rename ALLOW, mount create ALLOW; `1777/0700` DENY/DENY/ALLOW; `0755/0700` DENY/DENY/DENY; `1777/0777` DENY/ALLOW/ALLOW; `0777/0700` ALLOW/DENY/ALLOW. `PRODUCTION_FILES_TOUCHED=NO`, `SOURCE_DEVICE_MOUNTS_TOUCHED=NO`, `TEMP_FIXTURE_REMOVED=YES`, `ISSUE235_SSD_DAC_LAB=PASS`.
- Mount-root/state permission changes on ASUS: **NOT PERFORMED**.
- All production changes, user creation, init changes and service restarts: **NOT PERFORMED**.
- Three OTHER world-writable directory consumers: **UNRESOLVED**.
- Production rollout: **BLOCKED pending explicit authorization, dependencies and rollback validation**.

## Dufs update hold — operator decision (2026-10-14)

- Operator decision: **do not update/deploy Dufs now; wait for a future stable release**. No RC build or automatic promotion of upstream Dufs into the RouterCloud production binary; do not merge the current draft PR #4 as a deployment shortcut.
- The Linux/ASUS SSD permissions work in Issue #235 proceeds separately as a design and isolated testing track. Fedora five-scenario DAC test PASSED; production ASUS remains untouched.
- Any later Dufs upgrade will have a separate compatibility, application-feature, browser and rollback gate, explicitly authorized before deployment.


## Phase 1A extension — existing sync and delegated workspace access

A second self-contained, /tmp-only regression script is available at [test-issue235-ssd-consumer-paths.py](../tests/test-issue235-ssd-consumer-paths.py). It compares the `1777` (sticky-bit compatibility) and `0755` (restrictive) mount-root candidate with the protected `0700` root-owned `RouterCloud` serve folder and `.routercloud-system` state folder.

Expected in both variants:
- UID 0 can still write inside a pre-existing root-owned `RouterCloud` folder, as a **filesystem model** for a privileged sync process.
- UID 65534 cannot read or write root-owned private data and cannot read the state file.
- UID 65534 **can** write under its own explicitly delegated UID-owned `0700` workspace under a `0755` parent.
- Direct creation of new top-level entries by UID 65534 is **allowed with `1777`** and **denied with `0755`**.

An isolated Linux fixture run of this second suite completed with `ISSUE235_CONSUMER_COMPATIBILITY=PASS`. **Independent run on the user's Fedora: PENDING.** This test **does not** prove that production SSH/rsync, backup or addons actually run as UID 0, or that all other consumers are compatible. A separate read-only real-identity/access audit and dependency review remain mandatory before selecting the production mode. In particular, no current process snapshot proves the three OTHER folders are unused.

This remains a design/test branch: no RouterCloud release promotion or Dufs update is authorized; operator's explicit decision is to await a future stable Dufs release.
