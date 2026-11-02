# DNS Guard ARMv7 supervisor — build, verification and rollback (PR #197)

Scope: ASUS TUF-AX5400, Linux 4.1.52, ARMv7 EABI5 soft-float. The
`router/src/edge-dns-supervisor.c` source is compiled as a **static** Linux ARM
executable. The reviewed executable is `router/bin/edge-dns-supervisor`, installed
as `/jffs/addons/asus-edge/bin/edge-dns-supervisor`. Do not execute the PR
artifact on the production router during development.

## Current status and distinct timers — 2026-10-24

**Historical lifecycle:** this is the source/build/rollback reference for the PR #197 **ARMv7 external supervisor binary** used by supervised break-glass operations. PR #197 was merged and the bounded production DNS Guard v3.2/break-glass validation passed on 2026-10-08. The original "before any deployment" section below is therefore an archival **gate for reproducing or replacing this binary**, not a claim that v3.2 is still awaiting installation.

**Do not confuse separate primitives:**

- The `edge-dns-supervisor` C binary is responsible for bounded external commands within the supervised recovery procedure; its tested process-tree behavior must not be generalized to every DNS Guard command.
- The current `router/scripts/dns-guard` **shell function** `native_bounded_exec()` uses firmware BusyBox 1.25.1 `sleep` and PID-targeted `kill` to bound individual commands during early bootstrap, before Entware is available. It is a **different** implementation. Fedora-only [#287](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/287) reproduced an external timer `sleep` left behind by cancelled timer subshells, but did **not** prove unrelated PID-reuse kills, and no replacement was accepted on ASUS.
- October 24 logs also recorded repeated `dig` wrapper failures that **skipped the optional DNS Guard TCP readiness probe**. Direct Unbound TCP checks passing cannot prove that optional Guard probe executed. [Current DNS Guard limits](dns-guard-v3.2-recovery-audit.md) · [incident analysis](case-studies/dns-guard-grafana-alert-delivery-dns-failure-2026-10-24.md).

**No further production supervisor/timer/cron modification is approved**; separate #235 privileged-cron trust work is still HOLD.

## Issue #287 laboratory update — 2026-11-02 (C287.2J24)

A [source-pinned laboratory evidence and acceptance matrix](operations/dns-guard-issue287-c2872j24-acceptance-matrix-2026-11-02.md) records C287.2J13–J23: byte-reproduction of the **original** Debian GCC/glibc ARMv7 binary, an 8-line `SIGCHLD` candidate tested under QEMU, 12/12 candidate process cases, 19/19 mocked `auto` A/B paths, and later static/private-namespace/deadline-model checks. The J23 bundle checks local log markers; it is not independent firmware evidence.

These results do **not** mean the automatic `native_bounded_exec()` has been replaced by the C supervisor, nor do they establish execution on ASUS Linux 4.1.52, exact BusyBox 1.25.1 early-boot operation, a whole-`auto` hard deadline, or absolute protection against PID reuse. The proposed 60-second budget is not an approved requirement. The separate November 2 Cron/Entware `dig` fix (PR #350/#351) did not resolve Issue #287.

**Issue #287 remains OPEN with `ISSUE287_DEPLOYMENT_GATE=HOLD`.** No production candidate, installer digest, DNS Guard timing primitive, or service configuration is approved by this documentation update.

## Issue #287 end-of-day laboratory follow-up — 2026-11-02 (C287.2J25–J27)

The [J25–J27 laboratory evidence annex](operations/dns-guard-issue287-c2872j25-j27-timer-lifetime-2026-11-02.md) follows the source-pinned J24 review without changing the deployed helper. Initial J25/R1–R4 fixture failures arose from missing `kill` / `[` executable dispatch or unsupported `command -v` in an artificially restricted shell PATH; the corrected J25-R5 laboratory negative/positive test showed an original-helper timeout of `RC=137` at 1016 ms **with** `kill`, contrasted with `RC=0` at 3021 ms **without** `kill`, and observed an orphaned external timer `sleep`.

J26 exercised **four selected original `dns-guard auto` paths** against mocked services in a private PID namespace, with bounded lock contention and sampled FD9 checks PASS. J27 observed 27 unique adopted timer descendants after three `auto` calls: zero were active by 2300 ms, but all 27 were zombies until deliberately reaped by the test PID 1. Separately, the pinned GCC/glibc ARMv7 candidate cleaned up a detached child in standalone QEMU (RC 0, 465 ms). **This is not a same-scenario, integrated whole-`auto` A/B verdict.**

`C287.2J27_RESULT=PASS_TIMER_LIFETIME_AND_SEPARATE_CANDIDATE_CLEANUP_LAB_ONLY`. Next proposed check: J28 full-`auto` original-versus-lab-adapter parity with descendants, FD9, locking, timing and labels; **not run on 2026-11-02**. Router kernel 4.1.52, firmware BusyBox config/PATH, absolute PID-reuse safety, a hard total `auto` deadline and real-router acceptance remain untested. **Issue OPEN; `ISSUE287_DEPLOYMENT_GATE=HOLD`.**

## Local verification (Fedora)

```sh
sh tests/test-dns-supervisor.sh
sh tests/test-dns-supervisor-artifact.sh
sh tests/test-dns-breakglass.sh
sh tests/test-install-rollback.sh
```

The native regression checks timeout, process-tree teardown (including
`setsid` escape), error propagation, and `flock` release. The installer rejects
an absent, symlinked, empty or SHA-mismatched artifact *before* staging files;
installer snapshots already cover all of `/jffs/addons/asus-edge/bin` and the
isolated rollback regression checks restoration of the previous executable.

## Rebuild and compare

```sh
sh scripts/build-dns-supervisor-armv7.sh
# or: EDGE_SUPERVISOR_CONTAINER_ENGINE=docker sh scripts/build-dns-supervisor-armv7.sh
```

The script runs `gcc-arm-linux-gnueabi`, `libc6-dev-armel-cross`, and
`binutils-arm-linux-gnueabi` in `debian:bookworm-slim`. It compiles with
`-std=c11 -O2 -Wall -Wextra -Werror -march=armv7-a -marm -mfloat-abi=soft
-static`. Output is placed under `~/.cache/pr197-armv7`, **not** written back
to the reviewed artifact; a byte-for-byte `cmp` rejects drift.

The image tag and apt repository versions are not immutable pins. For
long-term bit-for-bit reproducibility, pin the container image digest and the
package versions, then update the packaged SHA only after reviewing source
and repeating all tests. Do not automatically replace the installer SHA with
the hash of an unreviewed build.

## ARM user-mode emulator evidence

The reviewed ARMv7 binary was exercised under QEMU 10.0.13 with the
subreaper syscall succeeding, and regression checks for timeout, children,
escaped session and `flock` passing. QEMU 7.2 Linux-user does *not* implement
`PR_SET_CHILD_SUBREAPER` (it returns `EINVAL`), so it is not a valid test
environment for this supervisor. Emulation is **not proof** of behavior on
the router's own 4.1.52 kernel or BusyBox environment.

## Deployment gate

Before any production deployment: verify the final PR code and CI; confirm
adequate router JFFS space; take a verified independent recovery backup;
prepare physical/local rollback access and a no-network-change read-only
preflight. Only then schedule an explicitly approved controlled deployment.
Do not treat QEMU passing as authorization to deploy.
