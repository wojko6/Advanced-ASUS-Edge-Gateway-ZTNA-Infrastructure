# Issue #287 — C287.2J25–J27 BusyBox timer lifetime and standalone ARMv7 cleanup (2026-11-02)

**Outcome: LAB-ONLY CHECKPOINT COMPLETE; Issue #287 OPEN; `ISSUE287_DEPLOYMENT_GATE=HOLD`.** This is a sanitized synthesis of operator-supplied Fedora terminal outputs, not independent execution attestation, ASUS firmware acceptance, or permission to change production. Continue from the [J24 source-pinned acceptance matrix](dns-guard-issue287-c2872j24-acceptance-matrix-2026-11-02.md).

## Identity and environment

- Frozen reference: repository commit `da1838d38b37df2c7e8fcfe80ab01e258682df17`, `router/scripts/dns-guard` blob `9fe3f509b5b639b6a2dfb2af54f08866bff44933`. Laboratory scripts extracted the *original, unmodified* `native_bounded_exec()` and later ran the original `dns-guard auto` entry point.
- Test BusyBox 1.25.1 lab executable passed the operator-side SHA256 check. It is an exact **pinned lab executable**, not proof of identical firmware build configuration. The BusyBox configuration, early-boot search paths, and external applet availability on ASUS remain unverified.
- Fedora rootless Podman private PID namespace, network disabled; `python:3.14-slim` was a **cached, unpinned image tag**. The PID namespace used the **Fedora host kernel**, not ASUS Linux 4.1.52.
- The pre-existing GCC/glibc ARMv7 supervisor *candidate* was hash-validated by J27 as `PASS_PINNED_GCC_GLIBC_ARMV7`, but its cleanup test was a **standalone QEMU operation**, not an integrated replacement for `auto`. The original shipped binary and router installation were unchanged.

## J25 — failures preserved and isolated

| Run | Operator-observed evidence | Interpretation |
| --- | --- | --- |
| Initial J25 | Worker `sleep 3` under a 1-second bound: `RC=0`, wall 3006 ms, `HOLD_TIMEOUT_WORKER_RETURN` | Timeout ineffective in this initial fixture; do not misreport as a firmware defect |
| J25-R1 | Timer woke, but instrumented `TIMER_KILL_RESULT=NONZERO`; original and instrumented runs returned RC 0 at ~3030 ms | Reproduced fixture failure; tmpfs files avoided `capture_output` pipe-wait ambiguity |
| J25-R2 | BusyBox `ash` lookup of `kill`: RC 127, `sh: kill: not found`; explicit BusyBox `kill` ended workers (wait RC 137); Python `os.kill` succeeded | Initial test `PATH` omitted an executable `kill` dispatch, although the BusyBox applet worked |
| J25-R3 | `command -v kill` check: RC 127 (`sh: command: not found`) | Test's preflight relied on unavailable `command`; did not test the timer |
| J25-R4 | `kill -0` dispatch showed linked `kill` worked; both helper cases failed RC 2 with `[: not found` | A second fixture defect: missing `[` dispatch |
| J25-R5 | Both paths supplied `[` (container `/usr/bin/[`), differing only by `kill` symlink; negative control RC 0 / 3021 ms; positive control RC 137 / 1016 ms; quick worker RC 17 / 214 ms | **`PASS_ORIGINAL_FUNCTION_PATH_NEGATIVE_POSITIVE_LAB_ONLY`**; one external `sleep` orphan observed; unrelated sentinel alive |

Do not erase intermediate HOLD results: R5 isolated the source of the fixture faults, not an ASUS kernel/PATH guarantee. The `[` shim was provided by the **container**, so the test is not a complete firmware BusyBox equivalence exercise.

## J26 — selected full `dns-guard auto` execution with mock services

The **original** `dns-guard auto` entry point was run under pinned lab BusyBox timer dispatch. `nvram`, `pidof`, `netstat`, UDP DNS and optional TCP `dig` were synthetic mocks, and the test exercised **four selected scenarios, not an exhaustive real DNS recovery regression**.

| Scenario | RC, wall time | Output / verdict |
| --- | --- | --- |
| Local DNS healthy | 0, 1302 ms | `AUTO=LOCAL_DNS` |
| Local path fails | 0, 1320 ms | `FALLBACK=PASS,AUTO=BOOTSTRAP_UNHEALTHY` in mock fixture |
| Break-glass flag present | 0, 1148 ms | `FALLBACK=PASS,AUTO=BOOTSTRAP_BREAKGLASS`; no operator break-glass tool invoked |
| Lock held by contender | 1, 1156 ms | Expected `cannot acquire DNS Guard lock within 1s` |

`J26_SCENARIOS=4/4` and `C2872J26_RESULT=PASS_MOCKED_AUTO_PATHS_FD9_AND_LOCK_PRIVATE_LAB_ONLY`. After those runs the fixture reacquired FD9 lock. Among 28 mock worker events and sampled timer processes it recorded **zero FD9 lock matches/leaks**; this is **sampled coverage, not a proof of universal descriptor cleanup**. At the final observation point there were **seven adopted timer `sleep` processes**. The 1635 timer-process observations were repeat samples, **not 1635 distinct PIDs**. The unrelated sentinel survived.

## J27 — actual duration and distinction between active timers and zombies

Three consecutive **original** `auto` calls returned `AUTO=LOCAL_DNS`, RC 0; their individual wall times were 1159, 1020, and 1005 ms (reported total 3185 ms). The private-namespace PID 1 deliberately delayed reaping to expose descendant lifetime.

| Time after last `auto` | Active adopted timer processes | Adopted zombies |
| --- | ---: | ---: |
| 0 ms | 17 | 10 |
| 250 ms | 15 | 12 |
| 700 ms | 10 | 17 |
| 1300 ms | 6 | 21 |
| 2300 ms | 0 | 27 |
| 3400 ms | 0 | 27 |

There were **27 unique observed adopted timer descendants**. By the 2300 ms sample, no active ones remained, but 27 were zombies awaiting laboratory PID 1. The lab's PID 1 then reaped **27/27**, leaving 0 unreaped. The number of zombies here **must not be projected onto the router**; the lab intentionally controlled its own reaper, and the ASUS PID 1 behavior was not tested.

The SHA256-validated **standalone** GCC/glibc ARMv7 candidate ran in QEMU/private namespace with `RC=0`, wall 465 ms; its detached child was **absent from `/proc` afterward**. `J27_CANDIDATE_STANDALONE_DESCENDANT_CLEANUP=PASS_QEMU_PRIVATE_NAMESPACE`; unrelated sentinel survived. This is **not** direct original-vs-candidate integrated `auto` A/B parity. J27 did not independently repeat J26's FD9 observations.

`C2872J27_RESULT=PASS_TIMER_LIFETIME_AND_SEPARATE_CANDIDATE_CLEANUP_LAB_ONLY`; both container and supervised RC were 0.

## Boundary, decision and next planned checkpoint

1. **No firmware validation:** ASUS Linux 4.1.52, actual early-boot PATH/applet dispatch, BusyBox build configuration, `/proc`, capabilities/UID/GID, FD9 and lock behavior on router, and production fail-open continuity remain unverified.
2. **No demonstrated unrelated-process PID-reuse kill:** the sentinel surviving a bounded test does not rule out all PID reuse races.
3. **No approved whole-`auto` hard deadline:** a 60-second budget was a model, not an implemented or agreed requirement; failure cannot be called fail-open success without verified fallback.
4. **No automatic break-glass authority:** no WAN NVRAM modifications, service restarts, Cron/installer/binary changes, or candidate deployment were authorized as part of J25–J27. The *separate* Cron/Entware `dig` production repair in PRs #350/#351 is documented in the [same-day worklog](../worklog/2026-11-02.md) and did not resolve #287.

**Next session, not performed today:** `C287.2J28`, controlled full-`auto` A/B comparison between the original BusyBox bounded helper and a **laboratory-only** candidate supervisor adapter, with outputs, descendant cleanup, FD9, locking and execution time measured under equivalent mock conditions. Separately approved read-only ASUS preflight is still a later gate.

**Decision: Issue OPEN, `ISSUE287_DEPLOYMENT_GATE=HOLD`; documentation only.**
