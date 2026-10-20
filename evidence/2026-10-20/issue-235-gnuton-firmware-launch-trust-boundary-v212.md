# Issue #235 — V2.12 pinned GNUton firmware launch trust-boundary source verification (2026-10-20)

> **READ-ONLY UPSTREAM SOURCE EVIDENCE, NOT ROUTER BINARY ATTESTATION.** Reviewed the public GNUton repository at **exact tag `3004.388.11_1-gnuton1`** using immutable GitHub file blob identifiers via the GitHub connector. No router, live binary, Cron, JFFS, NVRAM, SSD, installer, source code or restic state modified. This supplements V2.11 without rerunning V2.0–V2.9 synthetic tests. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.

## Fixed upstream evidence and byte provenance

| Exact tag-relative file | Git blob SHA (not SHA-256) | Narrow source context |
| --- | --- | --- |
| `release/src/router/shared/scripts.c` | `be75c75b9a0b26f479bd1927f82dd32496bcc73a` | `run_custom_script`, **lines 54–88** |
| `release/src/router/shared/shutils.c` | `8b65de2279158fd96486546441f218ff23db1916` | `_eval`, **lines 251–402**, especially `fork()` line 283 and `execvp(argv[0], argv)` line 391 |
| `release/src/router/rc/services.c` | `c8a3bf924b625b28de0fba9600c5957a74e77225` | `run_custom_script("services-start", 0, NULL, NULL)`, **line 11506** (in reviewed start-services completion sequence) |
| `release/src/router/rc/init.c` | `f7a886c4f09e97a7d9912fb68c436b36ee52070e` | `run_custom_script("init-start", 0, NULL, NULL)`, **line 21144**, earlier in startup |
| `release/src/router/others/cru` | `910c75078c5d5fe0b8d67a297a326e30f525be41` | **lines 1–36**, locks file write when adding/deleting named crontab line, not scheduling/executing process |
 
Upstream: [scripts.c](https://github.com/gnuton/asuswrt-merlin.ng/blob/3004.388.11_1-gnuton1/release/src/router/shared/scripts.c), [shutils.c](https://github.com/gnuton/asuswrt-merlin.ng/blob/3004.388.11_1-gnuton1/release/src/router/shared/shutils.c), [services.c](https://github.com/gnuton/asuswrt-merlin.ng/blob/3004.388.11_1-gnuton1/release/src/router/rc/services.c), [init.c](https://github.com/gnuton/asuswrt-merlin.ng/blob/3004.388.11_1-gnuton1/release/src/router/rc/init.c), [cru](https://github.com/gnuton/asuswrt-merlin.ng/blob/3004.388.11_1-gnuton1/release/src/router/others/cru).

**Important provenance distinction:** Git blob SHA identifiers record fetched exact repository objects; they are not source SHA-256 and **do not establish that the production router's compiled firmware binary is identical** to source compiled with a given toolchain/model configuration. No binary extraction, ELF disassembly, firmware build or live read-only router audit was performed.

## Source-level call chain and executable identity

```text
firmware start-services path / rc/services.c:11506
    |
    v
run_custom_script("services-start", 0, NULL, NULL)
    |
    +-- builds absolute /jffs/scripts/services-start
    +-- stat(path, &st): follows symlinks
    +-- rejects only if global jffs2_scripts literal "0"
    +-- rejects only if no S_IXUSR / S_IXGRP / S_IXOTH
    +-- NO st_uid/st_gid/mode writer/regular/hardlink/digest check here
    v
_eval([absolute-path, args], NULL, 0, &pid)
    |
    +-- fork() => separate child, without a pinned source FD
    +-- child resets signals, redirects FDs and sets PATH
    +-- NO explicit setuid/setgid or revalidation of JFFS script inode in this function
    v
execvp(argv[0], argv)  # opens current path identity, not stat-checked FD
```

**Finding V2.12-F1 — object identity not bound across validation and execution.** The `stat()` and later `execvp()` operate through separate pathname resolutions with a `fork()` in between; a different object may be present under that pathname at execution. The inspected code does not use `openat2`, `fexecve`, `execveat`, `O_PATH` pins or ownership checks. A nonroot owner able to change bytes on the existing regular inode may also modify the executable's contents independently of name replacement. This is a **source-derived design gap**; it is *not* proof of a practical successful exploit on current live JFFS or a claim all GNUton code has been audited.

**Finding V2.12-F2 — `_eval` is not a trust root or privilege drop.** `_eval` forks and calls `execvp`; its reviewed function does not switch to a less-privileged user/group or authenticate the file. Executed UID is inherited from its actual invoking process, so **the currently running router process UID must be separately evidenced** rather than inferred solely from this function. When `argv[0]` is the absolute JFFS hook path, `PATH` manipulation is not what supplies source authenticity.

**Finding V2.12-F3 — in-hook locks are too late.** The checked full `services-start` project source acquires its cooperative PID/starttime lock **inside** the launched shell script; it may prevent concurrent cooperating instances, but cannot prevent the firmware from first executing old/nonroot-owned bytes. An earlier ordinary JFFS `init-start` uses the *same* `run_custom_script` dispatcher (confirmed directly in `init.c`), not a stronger trusted firmware-layer gate.

**Finding V2.12-F4 — `cru` is a crontab writer lock.** The exact `others/cru` implementation opens `/var/lock/cron.lock` and serializes its **add/delete** mutation of a `/var/spool/cron/crontabs` file; no logic in that shell script blocks an already-running DNS Guard or independent direct WAN / emergency invocation. Our full `services-start` re-registers the `AsusEdgeDNSGuard` entry when configured. A Cron-only deletion is therefore neither durable nor comprehensive.

**Finding V2.12-F5 — interruption remains fatal to the safety argument.** The tag-source review offers no verified built-in owner gate, root-protected per-target pre-exec inhibit or JFFS2 two-path crash transaction. In a crash between separate repairs, untrusted hook bytes may execute before normal post-boot reconciliation. Merely using `chown root:root`, untrusted `rename`, a user `flock`, `init-start`, or `jffs2_scripts=0` (global recovery impact) is **not an approved fix**. No two-file atomic operation was discovered here; this was **not** an exhaustive search for every vendor-private firmware option.

## Reconciliation with project work

- [V2.0 earlier source-focused review](issue-235-dual-target-quiescence-model-v20.md) identified the `stat` + `_eval` path and absence of owner checks, but did not verify `_eval` internals. **V2.12 closes that narrow upstream source gap**: `fork()` + `execvp()`, not execution from a validated open FD.
- [V2.3 source name race](issue-235-fd-to-name-publication-race-v23.md) illustrates a *different* stage-name handoff risk. These two races belong to different layers: (a) firmware's hook validation/dispatch and (b) the hypothetical root publisher's source/staging publication. Neither is fixed by a post-hoc checksum.
- [V2.7 independent approval scope](../../docs/operations/issue235-two-script-offline-approval-authority-v27-2026-10-20.md) is specific to **two privileged scripts**, not PR #245 SSD authority. No real approval has been issued, and no trusted root stage or publishing helper exists.
- Existing V2.8 verified primary Fedora script copies and V2.9 showed `SAME_ST_DEV`; operator deferred making another backup under [V2.10](../../docs/operations/issue235-independent-script-recovery-options-v210-2026-10-20.md). No backup/Restic task is revived by V2.12.
- Separate RouterCloud/DUFS active-origin and root process privilege-drop work is unaffected.

## Concrete next engineering choice (no live action approved)

| Candidate | Technical prerequisites | V2.12 decision |
| --- | --- | --- |
| Existing GNUton selective pre-execution inhibit + protected publisher | Pin a firmware-native earlier-than-JFFS-dispatch trusted gate, preserve DNS/boot/emergency, prove persists across restart; trusted source FD/stage + old writable FD exclusion | **NOT PROVEN; NO-GO** |
| Firmware-level defensive modification | Separately reviewed source patch to check trusted owner/parents and optionally pin object/exec with secure semantics; build exact supported hardware image, verify binary equivalence and hard failure/DNS boot cases | **Architectural option only; NO patch or firmware deployment authorized** |
| Supervised offline/manual repair with explicit risk | Separately approved in-person LAN/DNS recovery; complete old writer/FD/process quiescence, exact two source provenance, root-controlled stage and interrupted JFFS behavior; separate production approvals | **Risk discussion only, not a default bypass of NO-GO** |

A future **read-only, explicitly coordinated** device-version/binary attestation may close the source-vs-production proof gap, but it **cannot by itself** provide a crash-safe selective gate. Stop inventing new synthetic grammar tests; next evidence should address either real trusted launcher implementation feasibility in an isolated environment or firmware-level safety architecture and independent DNS recovery.

```text
V212_UPSTREAM_TAG=3004.388.11_1-gnuton1
V212_DISPATCHER_SOURCE=VERIFIED_AT_TAG
V212_EVAL_SOURCE=VERIFIED_AT_TAG
V212_STAT_TO_EXECVP_IDENTITY=NOT_BOUND
V212_NAMED_CRU_LOCK=CRONTAB_WRITES_ONLY
V212_LIVE_ROUTER_BINARY_IDENTITY=NOT_ATTESTED
V212_ROOT_PUBLISHER=NOT_IMPLEMENTED
V212_DURABLE_PREEXEC_INHIBITION=NOT_PROVEN
V212_JFFS2_POWERLOSS_RECOVERY=NOT_PROVEN
ASUS_CONTACTED=NO
PROJECT_CODE_MODIFIED=NO
PRIVILEGED_EXECUTION_TRUST_GATE=HOLD
DEPLOYMENT_GATE=HOLD
```
