# Issue #235 — monotonic per-target publication alternative V2.1 (2026-10-20)

> **Status:** Fedora-only, **synthetic in-memory model** (19/19 local assertions PASS); **NOT** a runtime mitigation, JFFS2 publication test, power-loss test or operator authorization. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.

## Hypothesis and constraints

The prior [V2.0 four-launcher model](issue-235-dual-target-quiescence-model-v20.md) found that blocking just Cron is insufficient and a volatile pre-execution gate cannot protect an incomplete two-file transaction after power loss. A **distinct alternative** is to treat each target owner repair as a *strictly monotonic* per-path change rather than asserting that both changes form one crash-atomic transaction:

- Prepare **trusted, pinned exact bytes** for the *existing full firmware* `/jffs/scripts/services-start` and *existing approved* `/jffs/addons/asus-edge/bin/dns-guard`. The current source snapshots matched their pins; the files were nonroot-owned and owner-writable.
- A hypothetical trusted publisher prepares fresh root-owned, mode-0755 files within trusted ancestry, verifies content/metadata, and atomically replaces **one pathname at a time**, never automatically reverting to the original nonroot owner. All of this is **an unimplemented assumption**, not an apply command.
- If the process stops after the first replacement, the initial threat surface is **partly**, not completely, addressed; maintenance must stop in a flagged incomplete state, preserve independent DNS recovery, and require new authorization to resume. A phase record written after normal boot does not stop earlier untrusted privileged execution.
- The approach cannot declare continuous safety without demonstrating writer exclusion, handling preexisting opened script FDs and running jobs, protected independently retrievable source copies, trusted publisher identity, live crash-safe JFFS2 file publication and legitimate DNS/WAN recovery. No router action is permitted under the current HOLD.

This *could* avoid assuming a magical four-entrypoint crash-durable boot barrier **for the narrow claim that the count of untrusted installed target pathnames decreases**, assuming individual name replacements really preserve a trusted published inode across interruption. **It does not make interrupted maintenance fully safe or prove that any such replacement has that property on the reference firmware**. The residual pre-existing nonroot-owned script remains executable as root. A manual recovery path may be needed; a future operational plan would have to document and explicitly accept that risk rather than hiding it behind a successful model.

## Artifact and local tests

Standalone off-router Python model: `issue235_monotonic_publish_model_v21.py`. SHA-256: `2218762f4c9519cde7db0664f132e70e4adc658c3eaa7cc0da18b2bb9de57fa1`. Created in isolated assistant runtime; executed `--self-test` **19/19 PASS** and `--matrix` with seven synthetic scenarios. It has **no** subprocess/SSH/OS filesystem mutation surface. User's independent Fedora replay is **not yet reported**.

| Synthetic state | Untrusted root-executed targets | Model launch classes still reaching an untrusted target |
| --- | ---: | ---: |
| Initial | 2 | 4 — startup hook, Cron, WAN event, operator break-glass |
| Guard published first | 1 | 1 — startup hook |
| Hook published first | 1 | 3 — Cron, WAN event, operator break-glass |
| Guard first, then interrupted | 1 | 1 |
| Hook first, then interrupted | 1 | 3 |
| Both published | 0 | 0 (only for the owner-trust variable modeled) |
| Both published, then interrupted | 0 | 0 (only for the owner-trust variable modeled) |

Tests intentionally refuse idealized publication when any assumed precondition is false: independently retrievable backup, source pin verification, root-owned trusted staging/mode, trusted ancestor binding, writer exclusion or drained execution. They also refuse automatic resumption after an incomplete operation.

**Counts are abstract classes, not probabilities, measured attack paths or a production risk score**. The model assumes, rather than proves, that a path replaced with a trusted inode stays trusted after power failure; it cannot represent JFFS2 power-loss persistence, torn state, open FDs, post-check replacement races or external invocation timing.

## Alternatives and current assessment

| Candidate | Advantage | Unresolved / hard restriction |
| --- | --- | --- |
| In-place `chown` of existing live inode | Changes metadata only | **Rejected as an unproven immediate fix:** the previous owner may alter content before the operation or retain writable FD access; an ordinary prior hash cannot bind trusted bytes atomically to ownership |
| Generic installer / wrapper regeneration | Existing installer workflow | **Rejected:** may replace live full `services-start` with different short wrapper and does not address existing owners; unrelated production behavior can change |
| Cron delete or `flock` only | Reduces one trigger while held | **Insufficient:** WAN and break-glass can invoke guard directly; startup can re-register cron, and volatile state can vanish on power loss |
| Earlier JFFS `init-start` guard | Runs early in boot | **Not independently trusted:** pinned GNUton `run_custom_script` uses the same JFFS execution trust boundary and lacks an owner check in the inspected dispatch function |
| Single-path monotonic trusted replacement (V2.1) | Conditionally improves one target at a time without claiming a two-file atomic transaction | **Research candidate only:** trusted publisher, real JFFS2 persistence, no-inflight/writer races, DNS recovery and interrupted state handling all unproven |

## Needed to move beyond the model

1. Establish protected independent backup/recovery for both targets **outside the Fedora failure domain**; review exact source and metadata binding.
2. Develop trusted, same-filesystem, per-target *read-only/off-router first* fixtures with real inode identity and atomic publication behavior in the chosen filesystem; **ext4 experiments cannot prove JFFS2 power-loss durability**.
3. Prove how a real privileged publisher could exclude old UID writers and open FDs, and how a same-file descriptor would be source-pinned and atomically published with owner/mode correct.
4. Model and separately validate **service availability** with the guard first and after each possible early interruption, especially WAN/bootstrap DNS and operator break-glass. No disabling DNS safety merely to help the test.
5. Independently assess actual GNUton/JFFS2 crash interruption and reboot order before any staged router change. Until that exists, a partially completed state has **residual root-execution risk**, and any choice to accept it requires explicit operator decision.
6. Preserve the separation from PR #245 SSD DAC and parallel RouterCloud/DUFS and Issue #235 rootless tracks.

**Verdict:** V2.1 local abstract monotonicity **PASS**, real publisher and crash durability **NOT PROVEN**, privileged owner trust still **HOLD**. No ASUS connection, no Cron change, no production file mutation.
