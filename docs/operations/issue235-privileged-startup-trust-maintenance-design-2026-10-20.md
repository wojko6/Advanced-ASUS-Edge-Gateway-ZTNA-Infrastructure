# Issue #235 — privileged startup trust maintenance design (2026-10-20)

> **Status:** DRAFT / DESIGN ONLY / `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD` / `DEPLOYMENT_GATE=HOLD`.  
> **Scope:** the *existing* firmware hook `/jffs/scripts/services-start` and DNS Guard `/jffs/addons/asus-edge/bin/dns-guard`.  
> **Not in scope:** PR #245 SSD mode repair, RouterCloud/DUFS PrivDrop or HTTP origin, generic installer, unrelated firmware hook rewrites, router reboot, and automatic Cron/permission modifications.  
> **This is not a deployable runbook:** there are no production apply commands, approved maintenance windows, or authorizations.

## Evidence and design boundaries

The [19 October root-Cron investigation](../../evidence/2026-10-19/issue-235-dns-guard-root-cron-trust-and-rollback.md) and [20 October services-start audit](../../evidence/2026-10-20/issue-235-services-start-trust-chain-v14-v17.md) show two owner-writable, nonroot-owned **privileged entrypoint files**. Both currently match reviewed source bytes in bounded point-in-time reads. The existing full `services-start` firmware hook exactly matches the pinned source, while the root-owned addon script differs by moving watchdog registration to a later startup call site. Do not conflate those entrypoints or replace the full hook with the installer's generated short wrapper.

The operator has verified **private Fedora copies of both live script byte streams**. DNS Guard had an off-router disposable restore and V1.3 32/32 isolated rollback rehearsal. The hook backup has source-byte integrity PASS, file mode 0600 and private directory mode 0700. **Neither backup yet establishes independently protected media or full on-router JFFS2 recovery**; the hook restore rehearsal and live root-owned publish have not been verified. Source hashes alone do not resolve owner trust or continuous writers.

## Direct privileged execution and re-entry inventory (source and DAC snapshot verified; runtime not traced)

Disabling `AsusEdgeDNSGuard` via `cru` alone **does not** inhibit every legitimate DNS Guard invocation. Each row requires separate treatment; the source repository is evidence of *possible entrypoints*, not proof that all files and settings are deployed identically:

| Origin | Reviewed source path | DNS Guard impact | Required treatment |
| --- | --- | --- | --- |
| Merlin boot hook | `/jffs/scripts/services-start`, full approved pinned source | Calls `configure_dns_guard_watchdog` (line 325) to add/delete named cron; no direct `dns-guard auto` in this function | During future approved window, prevent new boot/manual hook invocation and rule out any active instance; do **not** assume every ordinary service restart calls this hook |
| Named root-Cron | `AsusEdgeDNSGuard` | Runs `/jffs/addons/asus-edge/bin/dns-guard auto` every minute while registered | Only separately approved dispatcher inhibition; verify absence after applying and drain in-flight runs; deleting the entry by itself is not quiescence |
| WAN-connected event | `router/scripts/wan-event` → `router/scripts/wan-event-handler` | `wan-event` dispatches on primary WAN `connected`; handler calls DNS Guard `auto` immediately and conditionally a second time after readiness wait | Treat as **independent re-entry**. **Do not indiscriminately disable WAN or its fail-open recovery**. A separately reviewed trusted transition mechanism or demonstrable event exclusion is required |
| Operator emergency | `router/scripts/edge-dns-breakglass.sh` | Calls DNS Guard through checked and supervised `breakglass-on/off` and fallback paths | Preserve operator emergency channel; coordinate its use during any window. Disabling it without an independent rescue method is a NO-GO |
| Deliberate maintenance | `scripts/uninstall.sh`, manual healthcheck and explicit DNS Guard calls | May invoke DNS Guard or change `cru` state | Never run overlapping maintenance/diagnostic operations while expecting quiescence |

The official [Asuswrt-Merlin user-script reference](https://github.com/RMerl/asuswrt-merlin.ng/wiki/User-scripts) describes `services-start` **after boot services are started**. It does not document automatic execution for every ordinary service restart. The prior generic term “service-start re-entry” must be read as **boot / manually invoked hook / unverified platform-specific trigger**, not as an observed recurring service-restart behavior. A future controlled test would be needed to prove any additional GNUton-specific invocation routes.

[V1.8–V1.10 WAN source verification](../../evidence/2026-10-20/issue-235-wan-trigger-source-v18.md) resolves the apparent hook drift: the live eight-line wrapper exactly matches the **installer-generated** source, while the intermediate addon `/jffs/addons/asus-edge/bin/wan-event`, downstream `wan-event-handler` and the independently pinned DNS Guard match their corresponding source bytes. The emergency `edge-dns-breakglass.sh` also matches pinned bytes. **Four-hop standard WAN source chain: EXACT_MATCH_AT_READ_TIME.** The actual WAN runtime dispatch, ACL/xattr effects and future competing writers remain **unverified**. Point-in-time standard WAN owner/mode/parent DAC passed V1.11, and the optional legacy hook was absent in V1.12. A hash match is not execution assurance or proof of trusted privilege separation.

Current limitation: read-only WAN owner/DAC pathname checks and source bytes passed at observation time, but **runtime invocation, ACL/xattrs, writer/FD races and persistence** remain unproven; do not present source and DAC evidence as a full live WAN execution trace. Do not confuse a source-level trigger map with a runtime trace.

**Quiescence acceptance must account for all launch sources, as well as possible already-open executable/script FDs and nonroot ownership.** If a trustworthy inhibitor would break WAN DNS bootstrap or operator break-glass, the window is a **NO-GO**. A root-owned metadata marker/lock, alone, cannot prevent independent firmware-triggered child processes or cron launches.

### V1.11 WAN DAC checkpoint: source-matching standard chain is root-owned at snapshot time

The [same-day V1.11 read-only metadata check](../../evidence/2026-10-20/issue-235-wan-trigger-source-v18.md) observed root:root ownership, single-link regular executable files and no group/other write for the firmware WAN wrapper, addon WAN hook, addon WAN handler, and emergency break-glass helper. Ancestor JFFS directories passed root:root/no group-or-other write, while edge config was root:root mode 0600. **The observed standard WAN chain has no DAC deviation**. V1.11's optional legacy WAN file was `ABSENT_OR_UNREADABLE_UNRESOLVED` because failed `ls` alone was ambiguous. **V1.12 resolved this with `LEGACY_WAN=ABSENT_POINT_IN_TIME`** using only fixed-path shell existence/type predicates: the candidate cannot run through the source-verified wrapper's guarded legacy branch at that instant. Private `EDGE_RUN_LEGACY_HOOKS` value was not read and does not need to be read to resolve this absent-file question. The bounded source/DAC/legacy inventory is complete; no WAN event was triggered. Source/DAC at two separate observation times is **not** full runtime attestation and cannot prove unobserved ACL/xattr/writers are absent.

## V2.0 offline two-target quiescence and crash model — EXPECTED-RED gates (2026-10-20)

The [standalone off-router model evidence](../../evidence/2026-10-20/issue-235-dual-target-quiescence-model-v20.md) (synthetic Fedora state machine; **20/20 self-tests PASS**) provides **no production mechanism or security acceptance**. Its eight-scenario matrix includes intentional expected-red witnesses:

- Named Cron inhibition alone leaves boot/manual `services-start`, direct WAN and operator emergency trigger classes available. Do not block the operator emergency path without independently available DNS recovery.
- Publishing **only one of the two targets** followed by a simulated crash exposes the remaining nonroot-owned privileged target when volatile controls disappear.
- Even a perfect abstract quiescence assumption cannot protect against **power loss before a safe early-boot gate** is established. Normal firmware boot may invoke `services-start` before a later user-space reconciliation controller.
- The model's trusted *persistent pre-boot barrier* is **hypothetical and unproven** for the actual GNUton/TUF-AX5400 setup. No JFFS2 power-loss or early boot durability was tested.

**New hard NO-GO:** a plan that only deletes Cron, holds a `flock` or writes a transaction log after normal boot is **not an interruption-safe two-file trust repair**. First prove a concrete safe strategy across restart/power interruption, or accept an explicit *unautomated, operator-driven recovery* proposal with documented residual risks — never claim the model itself authorizes either strategy. A root-owned rollback must not recreate previously observed nonroot-owned privileged entrypoints.

### Firmware-native bootstrap gating — inspected source, NOT PROVEN

The [V2.0 operator-replay and pinned GNUton source investigation](../../evidence/2026-10-20/issue-235-dual-target-quiescence-model-v20.md) directly reviewed `run_custom_script` at tag `3004.388.11_1-gnuton1`: it checks global user-script enablement and any execute bit before path-based `_eval`, **not root ownership, trusted parent chain or pinned same-FD content** in that function. `services-start` and earlier `init-start` are both invoked via this mechanism from writable JFFS. Installing another JFFS `init-start` wrapper alone cannot be assumed to provide a trusted crash-durable guard, and global `jffs2_scripts=0` is not an approved targeted mitigation because it could disable recovery hooks. An early-boot barrier remains **NOT PROVEN**, not a feature we can claim on the reference firmware.

## Four independent operator approvals — not granted

1. Scope and additional *read-only* evidence collection, including any necessary separately approved ASUS access.
2. Staging trusted sources and recovery materials. Staging on ASUS is a **mutating action** and is not implicitly approved by read-only checks.
3. One controlled production **apply** window for the exact two targets, only after the GO gates below are demonstrably met and an operator accepts the outage/recovery risk.
4. Any reboot or wider dependency intervention requires its own explicit authorization.

No repository merge, synthetic PASS, hash match, or maintenance calendar provides these approvals.

## Required GO/NO-GO before any apply

| Gate | Required acceptance evidence | Current state |
| --- | --- | --- |
| Trusted recovery | Protected, independently retrievable verified source and rollback copies for both scripts; document provenance, checksums and recovery from inaccessible router/JFFS | Fedora copies verified; independent failure-domain recovery **NOT PROVEN** |
| Scope pin | Exact active path, file identity, link count, no symlinks, trusted ancestry, SHA-256 and intended original behavior; no unauthorized writer | Point-in-time snapshots, no race-free guarantee |
| Identity boundary | An execution/transaction authority inaccessible to the observed nonroot owner, including its staging, receipts and lock | **NOT PROVEN** |
| Runtime quiescence | No in-flight `services-start` or DNS Guard, no writable active FDs or cooperating/competing writer, no new privileged trigger during publish | **NOT PROVEN** |
| Scheduler + all entrypoints | Precise prevention of named root-Cron launches, boot/manual `services-start` re-registration **and** independent primary-WAN `connected` handler entry, while preserving verified bootstrap DNS and operator break-glass; account for all launch sources and early-boot recovery | **WAN SOURCE/DAC POINT-IN-TIME PASS; DISPATCH INHIBITION AND LIVE RECOVERY NOT PROVEN** |
| Atomic file publication | Per-file trusted same-filesystem staging, root:root ownership, 0755 mode, content digest checks, directory/file publication identity constraints and safe handling of failures | Fedora fixture only, not proven on real JFFS2 |
| Interruption semantics | Tested and documented recovery for partial publish, process crash, uncertain JFFS2 persistence and potential restart/power interruption | **NOT PROVEN** |
| Functional recovery | Independent LAN admin access and preapproved DNS fallback; bounded DNS Guard, Unbound, Pi-hole and root-Cron verification after any change | **NOT AUTHORIZED** |

**Hard NO-GO:** any failed/ambiguous gate or detected source/owner drift; do not perform a partial or ad hoc single-file `chown` as a substitute.

## Draft execution state machine (not executable)

| State | Intent | Permitted transition after separate approval |
| --- | --- | --- |
| `HOLD` | Normal reference services, no action. Preserve evidence only | To `PREPARED` after protected sources/recovery exist and the maintenance proposal is approved |
| `PREPARED` | Independently authenticated immutable inputs for both scripts, no router mutation yet | To `QUIESCED` after separately approved scheduler/startup inhibition and verified drain |
| `QUIESCED` | No new launch through root-Cron, boot/manual startup hook, primary-WAN event or operator maintenance path; active jobs/FD writers drained; demonstrably safe DNS bootstrap and break-glass held | To `PUBLISHING` only if the trusted mutation authority and JFFS2 prerequisites are proven |
| `PUBLISHING` | Stage both files with verified root:root 0755 and pinned bytes. Publish each path using separately checked atomic file replacements | To `VERIFYING` only after **both** paths have trusted inode identity/metadata/content |
| `VERIFYING` | Validate both on-disk targets, independent DNS Guard/Unbound/Pi-hole health and expected watchdog schedule without unsafe duplicate registration | To `ACCEPTED` after operator approval and independently recoverable record |
| `RECOVERY_HOLD` | Any uncertain, mixed or failed state. Keep privilege launch inhibited as safely feasible, follow a preapproved recovery path | Return to a vetted trusted state; do not automatically restore insecure ownership |
| `ACCEPTED` | Two trusted owned targets and bounded functional recovery confirmed | Any future changes become a new maintenance event |

**Two renames are not one atomic transaction.** An interruption may leave the hook replaced while DNS Guard is not (or vice versa). The plan therefore requires a trustworthy persistent phase record and explicit detection/repair of mixed states; a stale or same-UID-writable receipt/lock is not adequate. Power-loss persistence on the real JFFS2 system has not been demonstrated. Do not infer directory `fsync` support or crash consistency from Fedora/ext4 tests.

## V2.1 research alternative — monotonic *per-target* publication, NOT a two-file transaction

The [offline V2.1 comparison](../../evidence/2026-10-20/issue-235-monotonic-two-target-model-v21.md) completed **19/19 synthetic local tests**. It models two independent publications of the *existing* pinned bytes as trusted root-owned files. Conditional idealized counts of **untrusted launch classes** decline from four at baseline to one when DNS Guard is hypothetically published first, versus three if the boot hook is published first. **These are Boolean exposure counts, not probabilities, actual exploited paths or production recommendations.**

**Nuance relative to the strict V2.0 boot-barrier finding:** under ideal assumptions, a crash after the first trusted per-file replacement *could* leave a namespace with one *remaining pre-existing* nonroot-owned target, without introducing a new target. This is a partial security improvement, **not a completed trust repair**. V2.0's warning remains applicable to any claim of **complete power-loss-safe maintenance**: the untrusted path could execute before an after-boot recovery script. No JFFS2 crash-persistent single-file publication, old-FD/writer exclusion, or independent recovery has been proven on the reference device.

Do not substitute live in-place `chown` for vetted source-to-root-owned publication; the previous owner could modify content or retain a writable FD. A one-file repair is not safe merely because a prior checksum matched. If incomplete, the procedure must stop with an explicitly untrusted target, not automatically resume or roll back to nonroot ownership. Any practical preferred publication order is subject to later independently reviewed DNS availability and firmware-specific checks; `DEPLOYMENT_GATE=HOLD`.

## Ordering and rollback constraints## V2.2 rootless Linux filesystem fixture — real inode and stale-FD behavior

The [V2.2 isolated filesystem test](../../evidence/2026-10-20/issue-235-rootless-file-inode-publish-v22.md) ran **19/19 local self-tests** with *real* user-owned disposable files and same-filesystem `os.replace`. New pathname reads saw the new inode and expected synthetic bytes, while a previously open writable FD continued to access the **old inode** after rename. It also demonstrated mixed states when stopping after only one of two path replacements. Its negative checks rejected symlinks, a hardlinked stage, changed candidate bytes and unsafe stage modes.

**Important limit:** this is *not* root-owned publication and *not* JFFS2. An FD pin checked before pathname-based rename does not prove an attacker-resistant FD-to-name handoff; an intervening replacement is still a distinct risk. File/dir `fsync` calls returning in the local fixture do not prove power-loss persistence. The operator's Fedora replay of V2.2 has not yet been reported. **No reduction of production HOLD.**



- Source priority: **preserve exact byte content of the currently deployed full hook** and approved DNS Guard source. Do not introduce the addon’s delayed watchdog call or a short wrapper during ownership remediation.
- Prefer a trusted startup-entrypoint replacement before Cron target reactivation, but **do not assume an execution order is safe** without proven suppression of both privileged entrypoints. The order is still subject to review.
- Both candidate and rollback publications must be **trusted root:root, mode 0755**. Historical evidence must retain the old nonroot ownership for forensic provenance, but a rollback must **not re-introduce owner-writable nonroot privileged scripts**.
- If safe `root:root` publication or rollback cannot be guaranteed, stay in a documented `RECOVERY_HOLD` with operator recovery rather than silently reopening the original privilege boundary.
- DNS Guard watchdog is part of fail-open recovery. Disabling Cron without demonstrating independent DNS recovery is **not** a safe maintenance precondition. The primary-WAN `connected` path calls DNS Guard directly, independent of Cron; boot/manual `services-start` hook invocation can also re-register Cron. Never suppress WAN or break-glass recovery casually.
- No generic installer, recursive DAC changes, runtime shell sourcing of untrusted data, or blanket service restarts.

## Current operator checkpoint and next work

**20 October:** fixed-path hook backup on Fedora `HOOK_OFFROUTER_BACKUP=PASS`, `BACKUP_HASH=PASS`, backup file mode 0600, directory 0700, `ASUS_MODIFIED=NO`, `CRON_MODIFIED=NO`. The off-router backup is a recovery **input**, not proof of independent resilience or live rollback.

**Next engineering decision:** validate an independently recoverable backup destination *without* publishing its path or contents; then review a concrete firmware-compatible protocol for quiescence and trusted two-target staging. Any active router intervention is a separate operator decision.

**Current final status:** `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.
