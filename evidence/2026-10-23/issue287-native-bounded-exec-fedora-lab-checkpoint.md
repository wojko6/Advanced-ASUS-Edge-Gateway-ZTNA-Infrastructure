# Issue #287 — bounded-exec cleanup and signed-worker research (Fedora-only checkpoint)

**Status:** LABORATORY / REVIEW ONLY — `DEPLOYMENT_GATE=HOLD`  
**Evidence date:** 2026-10-23  
**Source:** operator-provided Fedora regression output for the named laboratory packages, plus separately described disposable assistant-side local checks. The cited V0.7p–V0.7v regressions did not contact ASUS. An earlier, separately scoped **read-only router preflight** is distinguished below; no production change is claimed.  
**Scope:** [Issue #287](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/287), **not** Issue #235 / Draft PR #245 / RouterCloud / Dufs. This is a sanitized, bounded checkpoint, not a source-code commit or production acceptance.

## 1. Original finding and acceptance boundary

At [pinned commit `505ab768cf9d0bcf8fd34222c4df4ce3d8bac676`](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/blob/505ab768cf9d0bcf8fd34222c4df4ce3d8bac676/router/scripts/dns-guard#L51-L85), `native_bounded_exec()` starts a worker and a timer subshell; the external `sleep` launched by that subshell may survive cancellation of its parent. Its later `kill -KILL` targets a captured numeric worker PID. Reuse of that PID against an unrelated process is a **risk hypothesis**, **not** a demonstrated incident or production exploit.

The original Issue acceptance requires short-lived disposable workers exercising success, immediate exit, timeout, cancellation, repeated and concurrent calls; observation of timer/worker descendants and FD9 closure; and only if reproduction is RED, a deterministic BusyBox 1.25.1-compatible cleanup with regression coverage that preserves existing DNS Guard timeout and safety policy.

The already deployed DNS Guard v3.2 and the [ARMv7 supervisor PR #197 baseline](../../docs/DNS-SUPERVISOR-ARMV7.md) are **not** replaced by the experiments recorded here.

## 2. Earlier process-cleanup and ARMv7 laboratory stages

The preceding research (V0.6 and V0.7c2–V0.7o, as recorded in the engineering session) separated the original timer issue from a more ambitious alternative native supervisor:

- Disposable worker/timer experiments reproduced **orphanable `sleep` descendants**; direct/group-supervisor models tested normal cleanup and intentionally uncovered session escapes and forced supervisor-death limitations. This does **not** establish an unrelated process was killed.
- The pinned DNS Guard script was exercised with disposable mocked tools: V0.7c2 reported **10/10 script scenarios and 12/12 steps PASS**; later integrated thread-aware V0.7k reported **21/21 selftests, 8/8 process cases, 10/10 script scenarios and 12/12 steps PASS**. Results apply to their specific fixtures.
- A strict seccomp prototype initially blocked normal Fedora `dig -v` thread creation; a thread-aware policy allowed the tested workload. ARMv7 Zig/QEMU tests covered static builds and offline BPF models only. User-mode QEMU does **not** validate real ASUS kernel seccomp behavior.
- The target ASUS runs Linux 4.1.52/ARMv7. `SECCOMP_RET_KILL_PROCESS` semantics from newer kernels cannot be assumed on this kernel. The exact shipped router kernel configuration and runtime `SECCOMP_FILTER` support remain **UNKNOWN**. Neither a generic defconfig nor absence of `/proc/config.gz` proves the model's deployed filter support.
- V0.7o verified a **single nonroot x86_64 Fedora process's** self-only `NO_NEW_PRIVS`/seccomp behavior. A router preflight established that the SSH administrator is UID 0, and no separately validated nonroot router execution route was available. **No seccomp trial was run on ASUS.**

These stages are exploratory alternatives, **not** an accepted replacement for the Issue's minimal BusyBox-compatible cleanup fix.

## 3. Later privilege, FD, identity and signature experiments

All numbers in the following table are from **operator-provided Fedora output** for that version. Each PASS proves only the described synthetic or nonroot environment.

| Stage | Reported result | Bounded finding |
| --- | --- | --- |
| V0.7p | **22/22 selftests; 8/8 simulated cases; nonroot subprocess PASS; RC=0** | `setgroups → setresgid → setresuid` fail-closed contract; nonroot cannot regain UID/GID 0. The ordinary runner **did not** execute root-to-nonroot transition. |
| V0.7q / V0.7q1 | **22/22 source checks; 7/7 additional diagnostic checks, but 0/8 runtime cases; RC=125** | Deliberately failed closed on a **NONZERO** inherited capability baseline; not evidence that FD/ENV detection failed. No PASS should be credited to the 8 runtime cases. |
| V0.7q2 | **14/14 selftests; 8/8 FD/ENV cases; RC=0** | Separate nonroot child zeroed `CapInh/CapPrm/CapEff/CapAmb` and set `NO_NEW_PRIVS`. On the operator's Fedora, initial `CapInh` was nonzero; the other three sets were zero. Negative FD/ENV canaries rejected, clean cases accepted. `CapBnd` not modified. |
| V0.7q3 | **18/18 selftests; 10/10 cases; 8/8 V0.7q2 replay; RC=0** | `CapBnd` count **41** on this Fedora was nonzero and unchanged across `execve()`; four other sets remained zero and `NO_NEW_PRIVS=YES`. No `PR_CAPBSET_DROP` and no root-to-nonroot transition. |
| V0.7s | **22/22 selftests; 14/14 kernel cases; RC=0** | Synthetic static x86_64 ELF was started via sealed `memfd`/`execveat()`; mismatched image/hash, symlinks, writable source/parent, extra FD and environment canaries were rejected by their respective gates. The expected hash was generated in the same lab session. |
| V0.7t | **19/19 selftests; 18/18 signature/swap cases; RC=0** | Synthetic Ed25519 detached signature bound role, canonical manifest, hash and image bytes. Rogue key/signature, wrong role, file mutation and links rejected. **No worker execution** at this stage. |
| V0.7u | **19/19 selftests; 14/14 signed-exec cases; RC=0** | Signed and verified image bytes were executed from the **same sealed `memfd`**; swapping the source path after sealing did not change the executed image. Post-execution capability/FD audit was **not** performed by the original synthetic worker. |
| **V0.7v** | **25/25 selftests; 18/18 integration cases; RC=0** | Signed synthetic worker checked **post-`execveat()`** zero `CapInh/CapPrm/CapEff/CapAmb`, `NO_NEW_PRIVS=YES`, allowed FD state and controlled environment. |

### Security finding between V0.7u and V0.7v

The new post-exec worker exposed a **real laboratory FD leak in the original V0.7u launcher**: the sealed image `memfd` remained visible to the executed worker. The V0.7v **separate candidate** set `FD_CLOEXEC` on the image FD immediately before `execveat()`. The reported V0.7v tests passed without weakening the worker's FD audit. The original V0.7u source remains a pinned negative/historical baseline; the change has **not** been deployed or accepted as production DNS Guard code.

The laboratory Ed25519 **private signing key was not packaged**. Its public trust anchor, however, was distributed **inside the synthetic test bundle**, so **external production signing authority is NOT established**. Pinning a bundled public key or passing a same-session hash check cannot, by itself, authenticate a production root-owned release.

## 4. What this checkpoint does not prove

- The ASUS 4.1.52 kernel permits the relevant seccomp filter, `execveat()`, sealed `memfd`, capability semantics and complete supervisor behavior for the intended deployment.
- The tested static x86_64 synthetic worker is ABI-compatible with GNUton ARMv7 or with real Entware `dig`; the full real `dig`/DNS Guard workload and worker-tree containment were not run through the V0.7v signed execution test.
- A production-grade root-to-nonroot launcher with externally approved signed executable provenance, bounded inherited FDs, verified capabilities including `CapBnd` policy, independently assigned UID/GID authority and trusted loader state has been implemented or audited end-to-end.
- The process-cleanup approach withstands arbitrary supervisor termination, session escape, reused PIDs or crash/power-loss races on a real router.
- The current DNS Guard timer cleanup was patched, merged, installed, reboot-tested or roll-backed on the ASUS. No live process termination test against unrelated router processes was performed.

## 5. Issue acceptance and next engineering decision

| Original Issue #287 requirement | Current bounded conclusion |
| --- | --- |
| Disposable original-helper reproduction | **Laboratory evidence available** for timer/descendant cleanup risk, with modeled normal and negative cases. |
| Success, fast exit, timeout, cancellation, repeated/concurrent runs; worker/timer/FD9 lifetime | **Evidence exists in earlier mock/script stages**, but final coverage must be **reconciled against the exact Issue checklist** and published/CI-backed where needed. |
| Actual unrelated-process PID-reuse kill | **NOT OBSERVED**. Remains a hypothesis; do not claim an exploit. |
| Minimal BusyBox 1.25.1-compatible deterministic correction | **NOT ACCEPTED** as a production-ready patch. Native-supervisor and signed-launcher research is a broader alternative, not automatically the minimal fix. |
| Final source review, CI and platform-matched acceptance | **OPEN / HOLD**. |
| Live router deployment and rollback | **NOT AUTHORIZED / NOT DONE**. |

**Next action:** consolidate a minimal, separately reviewable `native_bounded_exec()` process-lifetime regression/patch proposal, preserving the existing timeout and DNS Guard semantics. Keep the signed-worker/privilege research as a distinct exploratory track instead of silently expanding Issue #287 acceptance.

**Change boundary:** Fedora/QEMU disposable research only. **ASUS contact for V0.7p–V0.7v Fedora regressions: NO; previous separately scoped read-only preflight: YES.** No JFFS, SSD, firmware, DNS, Cron, Tailscale, RouterCloud, Issue #235 or Draft PR #245 mutation or deployment. `ISSUE287_DEPLOYMENT_GATE=HOLD`.

## References

- [Issue #287](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/287)
- [Pinned original `dns-guard` source](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/blob/505ab768cf9d0bcf8fd34222c4df4ce3d8bac676/router/scripts/dns-guard#L51-L85)
- [DNS Guard supervisor ARMv7 build and rollback boundaries](../../docs/DNS-SUPERVISOR-ARMV7.md)
- [2026-10-21 AI-audit triage](../../docs/worklog/2026-10-21.md)
