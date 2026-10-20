# Issue #235 — privileged startup trust maintenance design (2026-10-20)

> **Status:** DRAFT / DESIGN ONLY / `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD` / `DEPLOYMENT_GATE=HOLD`.  
> **Scope:** the *existing* firmware hook `/jffs/scripts/services-start` and DNS Guard `/jffs/addons/asus-edge/bin/dns-guard`.  
> **Not in scope:** PR #245 SSD mode repair, RouterCloud/DUFS PrivDrop or HTTP origin, generic installer, unrelated firmware hook rewrites, router reboot, and automatic Cron/permission modifications.  
> **This is not a deployable runbook:** there are no production apply commands, approved maintenance windows, or authorizations.

## Evidence and design boundaries

The [19 October root-Cron investigation](../../evidence/2026-10-19/issue-235-dns-guard-root-cron-trust-and-rollback.md) and [20 October services-start audit](../../evidence/2026-10-20/issue-235-services-start-trust-chain-v14-v17.md) show two owner-writable, nonroot-owned **privileged entrypoint files**. Both currently match reviewed source bytes in bounded point-in-time reads. The existing full `services-start` firmware hook exactly matches the pinned source, while the root-owned addon script differs by moving watchdog registration to a later startup call site. Do not conflate those entrypoints or replace the full hook with the installer's generated short wrapper.

The operator has verified **private Fedora copies of both live script byte streams**. DNS Guard had an off-router disposable restore and V1.3 32/32 isolated rollback rehearsal. The hook backup has source-byte integrity PASS, file mode 0600 and private directory mode 0700. **Neither backup yet establishes independently protected media or full on-router JFFS2 recovery**; the hook restore rehearsal and live root-owned publish have not been verified. Source hashes alone do not resolve owner trust or continuous writers.

## Direct privileged execution and re-entry inventory (source-backed; live WAN not yet verified)

Disabling `AsusEdgeDNSGuard` via `cru` alone **does not** inhibit every legitimate DNS Guard invocation. Each row requires separate treatment; the source repository is evidence of *possible entrypoints*, not proof that all files and settings are deployed identically:

| Origin | Reviewed source path | DNS Guard impact | Required treatment |
| --- | --- | --- | --- |
| Merlin boot hook | `/jffs/scripts/services-start`, full approved pinned source | Calls `configure_dns_guard_watchdog` (line 325) to add/delete named cron; no direct `dns-guard auto` in this function | During future approved window, prevent new boot/manual hook invocation and rule out any active instance; do **not** assume every ordinary service restart calls this hook |
| Named root-Cron | `AsusEdgeDNSGuard` | Runs `/jffs/addons/asus-edge/bin/dns-guard auto` every minute while registered | Only separately approved dispatcher inhibition; verify absence after applying and drain in-flight runs; deleting the entry by itself is not quiescence |
| WAN-connected event | `router/scripts/wan-event` → `router/scripts/wan-event-handler` | `wan-event` dispatches on primary WAN `connected`; handler calls DNS Guard `auto` immediately and conditionally a second time after readiness wait | Treat as **independent re-entry**. **Do not indiscriminately disable WAN or its fail-open recovery**. A separately reviewed trusted transition mechanism or demonstrable event exclusion is required |
| Operator emergency | `router/scripts/edge-dns-breakglass.sh` | Calls DNS Guard through checked and supervised `breakglass-on/off` and fallback paths | Preserve operator emergency channel; coordinate its use during any window. Disabling it without an independent rescue method is a NO-GO |
| Deliberate maintenance | `scripts/uninstall.sh`, manual healthcheck and explicit DNS Guard calls | May invoke DNS Guard or change `cru` state | Never run overlapping maintenance/diagnostic operations while expecting quiescence |

The official [Asuswrt-Merlin user-script reference](https://github.com/RMerl/asuswrt-merlin.ng/wiki/User-scripts) describes `services-start` **after boot services are started**. It does not document automatic execution for every ordinary service restart. The prior generic term “service-start re-entry” must be read as **boot / manually invoked hook / unverified platform-specific trigger**, not as an observed recurring service-restart behavior. A future controlled test would be needed to prove any additional GNUton-specific invocation routes.

[V1.8–V1.10 WAN source verification](../../evidence/2026-10-20/issue-235-wan-trigger-source-v18.md) resolves the apparent hook drift: the live eight-line wrapper exactly matches the **installer-generated** source, while the intermediate addon `/jffs/addons/asus-edge/bin/wan-event`, downstream `wan-event-handler` and the independently pinned DNS Guard match their corresponding source bytes. The emergency `edge-dns-breakglass.sh` also matches pinned bytes. **Four-hop standard WAN source chain: EXACT_MATCH_AT_READ_TIME.** The actual WAN event dispatch, filesystem owner/mode/parent trust, optional legacy branch and concurrent writers remain **unverified**. A hash match is not execution assurance or proof of trusted privilege separation.

Previous limitation remains: the router's live `wan-event`, `wan-event-handler` and emergency `edge-dns-breakglass.sh` **owner/DAC chain and runtime invocation have not yet been attested in this audit**; do not claim current active WAN-specific routing solely from repository code. Do not confuse a source-level trigger map with a runtime trace.

**Quiescence acceptance must account for all launch sources, as well as possible already-open executable/script FDs and nonroot ownership.** If a trustworthy inhibitor would break WAN DNS bootstrap or operator break-glass, the window is a **NO-GO**. A root-owned metadata marker/lock, alone, cannot prevent independent firmware-triggered child processes or cron launches.

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
| Scheduler + all entrypoints | Precise prevention of named root-Cron launches, boot/manual `services-start` re-registration **and** independent primary-WAN `connected` handler entry, while preserving verified bootstrap DNS and operator break-glass; verify live WAN deployed code and trusted ancestors | **SOURCE INVENTORY ONLY; LIVE WAN NOT ATTESTED; INHIBITION NOT PROVEN** |
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

## Ordering and rollback constraints

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
