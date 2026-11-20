# Issue #287 — C287.2J24 evidence and acceptance review (2026-11-02)

**Decision: LABORATORY EVIDENCE CONSOLIDATED; ISSUE OPEN; `ISSUE287_DEPLOYMENT_GATE=HOLD`.**

This document is a sanitized, operator-reported summary of Fedora laboratories C287.2J13–C287.2J23 and the local J23 evidence bundle. It is **not** an independent execution attestation, a router runtime acceptance, a patch review approval, or an authorization to deploy. The evidence package itself remains on the operator's Fedora machine; only its bounded summary and identifiers are recorded here.

## Scope and separation from production changes

- [Issue #287](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/287) concerns the firmware-BusyBox `native_bounded_exec()` worker/timer lifecycle, possible orphaned external `sleep`, cleanup, FD9/lock behavior, and whole-`auto` duration. A Fedora fixture reproduced an orphaned timer descendant. **An unrelated-process kill caused by PID reuse has not been demonstrated.**
- The reviewed C `edge-dns-supervisor` is the existing bounded helper for operator-initiated break-glass; adapting it into the automatic Guard is **lab-only**. Automatic DNS Guard must remain conservative and must not inherit break-glass WAN-NVRAM/restart authority.
- The **separate** production [PR #350](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/350) / [PR #351](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/351) repair of the Cron/Entware `dig` loader environment is documented in the [2026-11-02 worklog](../worklog/2026-11-02.md). It did **not** deploy the Issue #287 supervisor adapter or resolve #287.
- Privileged-cron trust issue #235 and PR #245 are separate HOLD work, not addressed by these tests.

## Source and artifact identity

| Component | Pinned identifier | Meaning |
| --- | --- | --- |
| Reference repository commit | `da1838d38b37df2c7e8fcfe80ab01e258682df17` | Source snapshot used for the labs; changes on later branches require separate review |
| Original C source blob | `913d066068f34b253235e5d74fa74539e4f07ee4` | Unpatched supervisor |
| `router/scripts/dns-guard` blob | `9fe3f509b5b639b6a2dfb2af54f08866bff44933` | Guard fixture source |
| `tests/test-dns-guard.sh` blob | `39e653ebfd258e26af9a8478b74d7d0a92a9f4ae` | Guard test source |
| Shipped original ARMv7 binary SHA256 | `26f3615a99448469718f682bde6960e27e30b9466ecfc427c7e392c317103740` | Installer-pinned artifact; not replaced |
| Single candidate C source SHA256 | `ec942765ef66118d25162625591fef1c393fd38c695d79e9334172c07aa07845` | Original source plus the reviewed 8-line `SIGCHLD` reset, reconstructed only in the J23 local bundle |
| Candidate GCC/glibc ARMv7 binary SHA256 | `192aaa60e95a9181e45f83f7b5e0b337a436d954d587fae36392167e29dd4738` | **Reported in the J18 log; candidate bytes not independently rehashed by J23** |

**Reproducibility boundary:** In J16 the operator reproduced the *unpatched* shipped binary byte-for-byte using the documented Debian Bookworm / GCC 12 / glibc cross-build. This does not certify the patched binary or make the original container image and package versions immutable pins.

## Evidence matrix — proven in lab versus still open

| Checkpoint | Operator-reported observation | Precise scope and verdict |
| --- | --- | --- |
| C287.2J13-R4 | 19/19 `auto` paths, labels, exit codes and helper call counts agree | Zig/musl ARMv7 QEMU and Bash mock baseline; **PASS_LAB_ONLY** |
| C287.2J14–J15 | ARM EABI5 soft-float static ELF reviewed; original and Zig rebuild differ | Compiler/libc provenance investigated; no firmware execution proof |
| C287.2J16 | Shipped original equals Debian GCC/glibc rebuild, SHA256 parity | **PASS_ORIGINAL_REPRO_ONLY** |
| C287.2J17-R1 | 12/12 GCC/glibc ARMv7 QEMU scenarios: exit/timeout/signals, `SIGCHLD`, FD9, detached descendants | **PASS_LAB_ONLY**; original ignored-`SIGCHLD` case returned 125 while candidate propagated worker exit |
| C287.2J18 | GCC/glibc ARMv7 QEMU full `auto`: 19/19; baseline/native labels, RC and call-count parity | **PASS_LAB_ONLY**; uses explicit absolute command resolver and FD9 handling in a *lab adapter*, not deployed |
| C287.2J19 | 26/26 static source checks and 7/7 deterministic model checks | **PASS_STATIC_ONLY**; PID-race absence not proven on router |
| C287.2J20 | 11/11 synthetic checks and 12/12 private PID namespace/QEMU process cases; unrelated sentinel survived | **PASS_LAB_ONLY**, not an exhaustive forced PID-reuse proof; historical `C2872J20_QEMU_RUNTIME=HOLD_0` diagnostic contradiction retained despite final RC 0 |
| C287.2J21 | 17/17 source, 12/12 PID identity and 8/8 budget-model checks | **PASS_MODEL_ONLY**; protection from PID reuse is conditional on non-concurrent reaping and zombie lifetime |
| C287.2J22 | 18/18 budget, 15/15 fail-open model, 19/19 process-prerequisite checks | **PASS_MODEL_ONLY**; private namespace uses the Fedora host kernel, not ASUS Linux 4.1.52 |
| C287.2J23 | 7/7 required evidence stages and optional J13-R4 markers; four listed bundle-file SHA256 checks passed in operator readback | **PASS_MARKERS_PRESENT**; no rerun or independent attestation |

The J23 source and evidence reports explicitly distinguish **local log-marker validation** from independent verification of historical process execution. J20's `HOLD_0` marker is a reporting defect, not evidence that its 12 listed runtime scenarios failed.

### Local evidence filenames and SHA256 (not uploaded to this PR)

| Stage | Log filename | SHA256 as listed in J23 |
| --- | --- | --- |
| J16 | `issue287_c2872j16_supervised.log` | `859f85b911731a13ab1c2da8e9df352a09d6156caecea99e7c6f198ccf694dda` |
| J17-R1 | `issue287_c2872j17_r1_supervised.log` | `bbbdbc6d5bb67cbd8a92706ff8c3d16b087031a5268ce79aa7e3e16581691b67` |
| J18 | `issue287_c2872j18_supervised.log` | `40c080bde530d3f194fdaa9ae435310c2e4b114acc6f0c6255173004dbd45e5f` |
| J19 | `issue287_c2872j19_ponownie.log` | `390e9feb3d567ef21fee29d575487c009045741e11892584d395030df0edc286` |
| J20 | `issue287_c2872j20_supervised.log` | `b32359995a1569fbeecb647535e793938df885081951e76ae1f13003f6467e2f` |
| J21 | `issue287_c2872j21_audit.log` | `177fb87760d717aec2a7af74f108a1f7f28368457080d5099cdcdb6e731e7f4e` |
| J22 | `issue287_c2872j22_supervised.log` | `0aed29325470aeab74b91d9299a18dfea490314bd5b1bf92d6d6dca941d56bb7` |
| J13-R4 | `issue287_c2872j13_r4_supervised.log` | `582d3e7b768a40d24269a6bf221c658efdc69806395ea7bd97d330a2d112edb6` |

These hashes identify **operator-local logs**, not public artifacts or a signed trusted execution transcript.

## Acceptance gates still open

1. **Exact supported BusyBox 1.25.1 and early boot:** test the complete supported `dns-guard auto` path, firmware shell behavior and PATH, standalone external `sleep` lifetime, detached worker/descendant cleanup, FD9 closure/lock fairness, and accurate reporting. Existing Bash mocks and QEMU do not replace this evidence.
2. **ASUS Linux 4.1.52 and real runtime assumptions:** observe `SIGCHLD`, `waitid(WNOWAIT)`, child-subreaper, `/proc`, UID/GID, capabilities/LSM, JFFS and early-boot availability in a separately authorized **read-only** preflight. Fedora/QEMU executes on Fedora's kernel.
3. **End-to-end duration:** establish an accepted complete-`auto` bound covering serial helper calls, lock acquisition, cleanup and retries. **60 seconds was a hypothetical design model, not an approved requirement or implemented hard guarantee.**
4. **Fail-open safety:** budget exhaustion cannot be labeled successful fail-open without confirmed fallback. Models passed; no production implementation or firmware proof exists.
5. **PID-target identity:** no unrelated-PID kill was observed or proven impossible on router. The zombie/PPid model protects identity only under explicitly documented reaping assumptions; no `pidfd` pin is present in this source.
6. **Review and rollback:** any code, packaged binary or installer SHA change requires separate source/security review, complete supported-environment regression, rollback verification, and explicit operator authorization. The docs-only PR and this issue update grant **none** of those permissions.

## Stop/go decision

**HOLD.** Keep Issue #287 open. Do not modify the deployed `native_bounded_exec()`, install a candidate `edge-dns-supervisor`, change `scripts/install.sh` pins, cron/systemd hooks, resolver configuration, WAN NVRAM, or restart services as a consequence of these labs. Avoid further near-duplicate QEMU variants without a named unresolved acceptance criterion. A router preflight must be separately approved, read-only, and distinct from any deployment approval.

**Source:** [Issue #287](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/287) · [existing supervisor build/rollback reference](../DNS-SUPERVISOR-ARMV7.md) · [day-scoped worklog](../worklog/2026-11-02.md)

`ISSUE287_DEPLOYMENT_GATE=HOLD`
