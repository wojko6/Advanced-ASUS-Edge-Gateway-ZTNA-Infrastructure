# Issue #235 — DNS Guard privileged Cron trust: 2026-10-19 bounded checkpoint

> **Status:** OPERATOR-REPORTED / EVIDENCE-SCOPED / NO PRODUCTION REMEDIATION.  
> **Platforms:** isolated Fedora laboratory and separately authorized read-only ASUS TUF-AX5400 SSH observations.  
> **Security gates:** `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `STAGE_B_C_E_AUTHORIZATION=NOT_GRANTED`, `DEPLOYMENT_GATE=HOLD`.  
> **Scope:** DNS Guard root-Cron target ownership only. This is **not** production RouterCloud PrivDrop/origin acceptance or SSD mount-root PR #245 acceptance.

## Provenance and evidence classes

This is a sanitized summary of terminal outputs supplied by the operator on 2026-10-19. Laboratory PASS refers to the stated fixture and test conditions; production read-only results are point-in-time observations. None is independently attested GitHub CI or a complete on-router transaction. No raw Cron commands, account identifiers, private backup paths, SSH endpoints, credentials, or complete private logs are published.

On 2026-10-18, a separately approved live audit found that the root-Cron DNS Guard target had a **nonroot UID/GID and owner-write permission**; the content already matched reviewed DNS Guard v3.2 from [PR #197](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/197). The 2026-10-19 checks below re-evaluated the specific target without mutating it. See the [earlier dated worklog](../../docs/worklog/2026-10-18.md).

## Fedora-only research (no ASUS production mutations)

| Lab | Operator-reported result | Bounded conclusion |
| --- | --- | --- |
| Integrated DAC V0.1 | 35/35 PASS | Synthetic cross-UID owner/mode, Cron/hook, lock and SSD DAC fixtures |
| V0.2 | 38/38 PASS | Open FDs, pinned directory FDs, hardlinks and atomic replacement/rollback |
| V0.3 | 46/46 PASS | `flock` inode substitution, stale writes and transaction guards in isolated processes |
| V0.4 | 116/116 PASS | Seven simulated process-crash points, journal/recovery fail-closed behavior; **not power-loss durability** |
| V0.5 | 48/48 PASS; 3/3 source fingerprints | Static writer-contract audit and synthetic lost-update behavior |
| V0.6 | 37/37 PASS in synthetic and source-snippet replay modes | Expected-red same-UID symlink/hardlink stage collisions reproduced; **not a cross-UID exploit** |
| V0.7 | 59/59 synthetic; 68/68 with source audit | Candidate writer guards reject many substitutions; a late same-UID commit race **remains reproducible** |
| V0.8 | 35/35 synthetic; 45/45 with source audit | Separate same-UID processes bypass DAC-based isolation in the fixture; same-UID adversarial race safety **not proven** |
| V0.9 and V1.0 | 12/12 and 24/24 PASS; pinned source audits PASS | Installer owner-normalization gap and distinction between `flock`, dispatcher disablement and active-job drain |
| Root-Cron rollback V1.3 | 32/32 PASS twice, including with the verified off-router file | Rootless Fedora 0755 publish/copy-rollback and fail-closed model; **not actual root:root or JFFS2** |

The 414 basic V0.1–V0.8 tests are a sum of *one run per model*, not a percentage of Issue #235 completion; replays/source audits are not additional production acceptance. Some PASS lines deliberately assert expected-red vulnerabilities in isolated, disposable fixtures.

**Source observation:** pinned public `scripts/install.sh` writes destinations via `cp` and `chmod` without an explicit `chown` in `install_file`. That is a plausible mechanism for preserving anomalous ownership on an existing destination, **not proven provenance** of the live file. The source `router/scripts/services-start` schedules DNS Guard once per minute and may re-register the named Cron entry at service startup; acquisition of a DNS Guard `flock` is not proof of dispatcher quiescence.

## Read-only ASUS results, 2026-10-19

| Check | Operator-reported snapshot | Boundary |
| --- | --- | --- |
| UID/tooling probes | Remote shell was root; V1.2 and V1.2.1 held due to incomplete tool-provider support; V1.2.3 numeric `ls -ldn` parser 11/11 | Tool compatibility failures are **not** DNS Guard failures |
| Project JFFS ancestor directories | root:root, mode 0755; `METADATA_ITEM_FAILURES=0` | DAC snapshot, not continuous path/inode identity |
| DNS Guard executable | Non-root owner/group, owner-writable, mode 0755, link count one | **Privileged-execution trust concern persists** |
| Named Cron entry | Exactly one matching expected target in one snapshot | No evidence that dispatcher is stopped or active jobs drained |
| Owner-UID process snapshot | Zero matches in 147 inspected processes; no scan truncation/errors | Cannot exclude future/indirect writers or open-FD writers |
| Mount topology | `/` on read-only SquashFS; `/jffs` on writable JFFS2 | Root directory mode 0777 must not be interpreted as unrestricted SquashFS mutation; mountpoint inode trust and JFFS2 crash recovery unproven |
| Current target SHA-256 | Fresh SSH streaming hash matched reviewed historical v3.2 pin `ecd44c59532073d33290b8eb500144e12ecfb4537542bc58a4c75be8753ab0db` | Byte equality at read time; **not immutable ownership or trusted future execution** |

The V1.2.3 built-in hash provider returned `UNAVAILABLE`, not mismatch. A separate bounded SSH read streamed the approved target into Fedora `sha256sum` without saving router file contents there. Router Cron, ownership and services were not modified.

## Off-router recovery evidence

- Operator read an off-router DNS Guard copy from ASUS into a private Fedora directory; its hash matched the above historical pin.
- Source backup DAC was checked (`0700` directory; `0600` file, single link), and restored bytes passed a disposable Fedora restore/cmp test at mode `0600`.
- Rootless V1.3 rehearsed staging with final file mode `0755`, simulated interruption and independent byte-copy rollback against both synthetic bytes and that verified backup. The backup itself was unchanged.
- The backup is **off-router**, but a physically independent additional medium, production application-consistent restore, live `root:root` restoration, and JFFS2 power-loss recovery are **not verified**. Private copy paths and contents are intentionally excluded from this public report.

## Remaining gates and safety decision

1. Establish a trustworthy source/parent-chain ownership and explicit authorized writer policy for the root-executed target; preserve a verified independent recovery copy with a storage/failure-domain assessment.
2. Design **separately authorized** Cron dispatcher inhibition and suppression of `services-start` re-registration; establish no already-running instances, no open writable FDs, and no competing privileged writers during a bounded service window. A free `flock` alone does not establish these conditions.
3. Review atomic publish and fail-closed rollback on the **actual JFFS2 target**, including interruption and re-entry; ensure both published and rollback executable are trusted root:root with intended executable mode.
4. Require an explicit router stage/apply authorization, operator-held recovery access, DNS Guard/Unbound/Pi-hole service and query postflight, Cron restoration and a separate approval for any reboot. No router command in this report is an apply instruction.
5. Keep [Draft PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) (SSD mount-root mode) and RouterCloud/DUFS HTTP-origin/PrivDrop tracks independent. [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) is broader than this DNS Guard sub-track and remains OPEN.

**Final verdict:** investigation and isolated backup rehearsal PASS within their stated scope. **No live owner repair; no Cron changes; no RouterCloud, SSD, JFFS hook, installer, or service deployment.** `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.
