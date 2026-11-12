# Issue #235 — controlled JFFS staging, activation and rollback (DRAFT)

**Status:** PROCEDURE FOR REVIEW ONLY — NO PRODUCTION AUTHORIZATION. **GO/NO-GO = HOLD.**

This is a narrowly scoped operational design for the GNUton ASUS TUF-AX5400 SSD mount-root mode regression tracked in [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) and [Draft PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245). The draft helper/UUID mapping is **NOT installed** and active `/jffs/scripts/post-mount` is unchanged. No command in this document should be interpreted as approval to mutate the reference router.

## Evidence accepted as of 2026-10-15

- Firmware source's mount-success path changes a partition root to 0777 before `post-mount`; two live ext4 roots were observed root:root 0777.
- Both partition UUID mappings were verified read-only on ASUS and staged in a **private Fedora-only** archive. Independent local UUID/manifest audit PASS. No UUID value is to be copied into any public repository or issue.
- A new V3 **private Fedora-only** post-mount candidate was built from the previously backed-up original with the integration snippet pinned to public commit `be191e1098a5145d58e38baceebf061190ce11a9`. Pinned snippet Git blob SHA `7a55ae66e917fd67cb90524f15d85201094c8dc3`; exact inserted bytes, original sections, syntax, private permissions and manifest PASS.
- **Independent** V3 audit verified the stage, source SHA, blob identity, exact composition and manifest. A same-directory, same-filesystem **Fedora synthetic** `os.replace` activation/rollback rehearsal passed with original SHA, syntax and mode restored and no temporary files remaining. This does **not** prove JFFS rename semantics, remote root ownership, actual boot sequencing or early-tool availability.
- Production `post-mount` was read-only rechecked root:root 0755, regular non-symlink, `sh -n` PASS and original SHA-256 `8625bee2558d046e789e9ea871ed5d7758be42c39548ca7f6a63757704a02b66` twice. If this value changes, **STOP**; do not use the saved candidate without rebuilding from the new reviewed baseline.
- External encrypted original-hook recovery archive was independently checked and safely disconnected; no full live-JFFS restore has been tested.
- Latest relevant isolated-code CI for the guarded snippet was SUCCESS. CI does not assert production execution.

## Strict scope and forbidden side effects

Permitted **only after separately requested and explicit operator approval**, the future change may stage one exact reviewed mount-mode helper, two root-only UUID files, and exactly one snippet insertion in the existing `post-mount`; only the two allowlisted SSD mount root inode modes may ever be changed at runtime from 0777 to 0755. No recursive chmod, no changes to child directory owner/mode, no partition remount, no package install, no service restart, no swap cycle and no reboot are implied.

Do **not** use `scripts/install.sh` for this fix: its `install_hook` code can overwrite the independent custom live `services-start` hook. The latter currently has UID:GID 1000:1000 and different contents from managed bin, constituting a **separate** unresolved owner/provenance case. Do not change that hook or its owner under Issue #235.

Do not use `/opt` tooling in the early-mount snippet/helper. The intended firmware utilities are absolute `/bin/busybox`, `/usr/bin/awk`, `/sbin/blkid` and `/bin/chmod`.

## Stage A — non-mutating acceptance preflight (must PASS independently)

1. Confirm the operator has **physical/wired LAN and WebUI/SSH recovery** without relying on Tailscale, DNS Guard, Unbound or Pi-hole. Identify an alternate management path and a bounded maintenance window; do not adjust router firewall/WAN access to create one.
2. Recheck model/firmware baseline, JFFS free space and read-only mount identity. Confirm 1:1 ext4 mounts for both named partitions, root-owned 0777 roots and exactly **two active swap files**. Existing RouterCloud/Entware protected child directories and expected service health must match the recorded baseline.
3. Confirm that the live `post-mount` is a root:root 0755 regular non-symlink file, is syntactically valid, and **exactly matches** the pinned original SHA above. Ensure no concurrent AMTM or firmware script updater will replace it during a future maintenance step. No `services-start` edit.
4. Independently verify the local V3 artifact, its immutable pinned snippet and the helper's reviewed repository revision, both private UUID file/manifest checks, source permissions, and original off-router backup. Reconfirm the encrypted Verbatim recovery archive is usable without relying on the router. **Never print, commit or log UUID contents.**
5. Confirm post-mount insertion preserves original swap activation **before** AMTM sourcing and does not introduce `set -e`, `exit` or `return` that could interrupt unrelated mount events. Accept remaining timing/TOCTOU risk explicitly before production GO.
6. Resolve the residual compatibility decision for direct first-level SSD writers, including scheduled/transient jobs. Snapshot FD checks of DNS/Unbound are evidence only, not proof. Failure or unaccepted risk = **NO-GO**.

## Stage B — future limited JFFS payload staging (requires explicit approval, NOT YET EXECUTED)

1. Before any copy, verify the exact destination is not a symlink or unexpected file, and ensure the existing JFFS ancestor chain remains trusted. The snippet's numeric BusyBox checks **require** `/jffs`, `/jffs/addons`, `/jffs/addons/asus-edge`, `/jffs/addons/asus-edge/bin` all non-symlink, `0755 root:root`.
2. Prepare `/jffs/addons/asus-edge/private` as a real non-symlink directory `0700 root:root`. Prepare only `router-data.uuid` and `entware.uuid` as regular non-symlink files `0600 root:root`. Prepare the helper in `bin` as regular non-symlink `0755 root:root`. **Never assume Fedora UID/GID and file mode automatically survive SSH transfer.**
3. Transfer with a separate scoped and reviewed operation that does not truncate existing trusted paths. Verify remote owner/mode, contents/digest (without publishing them) and file types **after transfer**, including no aliases. On collision or unexpected mode, STOP and recover only the separately approved staged items.
4. No change to `post-mount`, mount-root inode modes, swap or services in this stage. A successful file stage does not activate anything and does not authorize the next stage. Reconfirm JFFS capacity and no accidental loose-permission file artifacts.

## Stage C — future scoped post-mount activation (requires a SECOND explicit approval)

1. Recheck exact original live SHA, owner, mode, current JFFS access, JFFS trusted parents, both UUID/helper private metadata and bytes. Verify on the router that the candidate has valid shell syntax, preserves every original line outside the **single** pinned insertion, and does not contain private literal UUIDs.
2. Ensure a byte-identical original exists in *independent off-router* recovery storage and the operator is at the wired management endpoint before attempting activation.
3. A separately audited implementation should deliver the candidate into a **unique, root-owned temporary regular file on the same JFFS filesystem**, with `0755 root:root`, verify complete bytes and syntax, and only then perform a single atomic same-filesystem rename to `/jffs/scripts/post-mount`. Never append or truncate the live hook, never use a cross-filesystem `mv`, and never change `services-start`.
4. Verify live hook SHA against the **V3 candidate** and owner/mode, and verify there is no leftover half-staged file. On failure, STOP rather than run a second write blindly. Activation may not affect mounted volumes until a future mount event: **do not manually source/execute post-mount or trigger a remount** to force the patch.
5. Collect read-only service health (swap, /opt, DNS/Unbound/Pi-hole, Tailscale, RouterCloud and rsync/backup), active SSH/WAN/LAN and JFFS free-space evidence. Neither silent service restarts nor a reboot are part of this phase.

## Stage D — emergency restoration decision (requires authorized incident scope)

- If Stage C verification fails or unexpected service impact occurs, prefer a controlled rollback rather than escalating to reboot. Reconfirm access via wired LAN, the integrity and SHA of the saved **original**, and that the target is not a symlink. Prepare a separately verified root-owned `0755` regular temp file on the **same JFFS filesystem**, check source SHA/syntax, then atomically replace only `post-mount`. Verify the original SHA, root:root 0755 mode and preservation of the historical **swap-before-AMTM** logic.
- The earlier private Fedora `os.replace` fixture is **not** a real JFFS recovery proof. A JFFS same-filesystem rename and recovery procedure remains an untested production risk until an independently authorized maintenance exercise is approved.
- Rollback of the hook does **not** instantly revert already hardened SSD directory inode modes. Nor does it prevent GNUton firmware from writing 0777 again on the next mount. Do not use permissive chmod as an automatic emergency shortcut; record and decide the security trade-off explicitly.
- Do not automatically delete helper or UUID payloads as part of hook rollback. Confirm they are unused and remove them only if explicitly included in incident scope, preserving their privacy and preventing residual world-readable temporary files.
- If router access is lost, use local wired recovery and established device/vendor runbooks; do not assume remote Tailscale/DNS is functional. Never reinstall the full project as a shortcut.

## Stage E — separately approved boot and remount persistence acceptance (NOT AUTHORIZED)

Only after Stage C acceptance, request new consent for a planned test reboot. Verify boot ordering and both swap entries, real SSD modes 0755 after firmware rewrite and JFFS post-mount, AMTM/Entware startup, DNS/Unbound/Pi-hole, Tailscale, RouterCloud/backup, DNS Guard, monitoring and recovery. A hotplug/remount test is another independent operation requiring its own risk review. **No reboot, `swapon`, `chmod`, `mount`, `umount`, or hook execution is authorized here.**

## Required approvals and release rule

- **A: operator acknowledges all non-mutating evidence and accepts outstanding compatibility/race risks.**
- **B: separately approves installing scoped private UUID/helper stage** (only after exact plan and recovery confirmed).
- **C: separately approves atomic activation of the reviewed post-mount candidate** after successful Stage B.
- **E: separately approves a controlled reboot/physical remount** (never implied by earlier approvals).

The next action today is **documentation and independent read-only audit only**. Production decision stays **NO-GO / HOLD** until the above gates are satisfied. Related references: [detailed diagnosis](issue235-ssd-mount-postmount-repair.md), [GO/NO-GO matrix](issue235-production-go-no-go-2026-10-15.md), [boot dependencies](architecture/boot-service-dependency-flow.md), [DR issue #129](router-bare-metal-recovery-pl.md).

## 2026-10-15 — operator-confirmed independent wired recovery route

Following the read-only JFFS, ext4 and dual-swap preflight PASS, the operator explicitly confirmed the ability to connect the Fedora workstation directly to ASUS by Ethernet and use the router administration WebUI **without depending on Tailscale, Pi-hole or Unbound**. This is a credible **operator-attested available recovery path**, not a newly executed cable/GUI test or a demonstrated recovery during an outage. Do not represent this as a completed live failure/recovery drill.

Remaining gates are unchanged: fresh read-only post-mount source hash/owner check at the actual maintenance time, independently available original off-router/encrypted recovery evidence, final review/acceptance of unknown periodic/direct-root SSD writers and other residual risk, operator-authorized narrow payload staging, later separately approved hook activation and still later separately approved reboot. No JFFS artifacts installed; `DEPLOYMENT_GATE=HOLD`. Operator confirmation of Ethernet recovery is **not** authorization to mutate production.

## 2026-10-15 — recovery media and GPG access attested

The operator additionally confirmed having access to the separate external Verbatim SSD holding the independently verified GPG-encrypted original `post-mount` recovery archive **and** the corresponding GPG passphrase. Neither the passphrase nor its parts were requested, shared or recorded. Together with the prior independently attested Ethernet/WebUI access, this closes **operator availability attestation** for both recovery paths; the earlier verified decrypt-and-hash test remains documented elsewhere. It does **not** constitute a new post-disconnection decrypt/reconnect test, a live JFFS restore exercise, or a guarantee against access-loss scenarios.

The next decision gate is formal acceptance/rejection of residual scheduled/transient direct-root SSD writer compatibility risk and a final fresh read-only prechange live `post-mount` digest check. **No production installation permission has been given.** Separately authorize UUID/helper staging, hook activation and a future reboot only after explicit review; keep `services-start` untouched. `DEPLOYMENT_GATE=HOLD`.


## 2026-10-17 — Stage B publication safety contract (DESIGN REVIEW CLOSED; PRODUCTION HOLD)

This section closes the *design-level acceptance criteria* for future Stage B file delivery. It does **not** approve or implement a production stager, supersede the rollback runbook, or close the production compatibility gate. Isolated Fedora tests were operator-reported PASS: basic synthetic staging **6/6**, single-file publish/interruption/collision **7/7**, and directory-FD / ancestor replacement / orphan handling **9/9**. These tests used synthetic data and simulated ownership using the local Fedora UID. No actual JFFS filesystem, root:root transfer, physical power loss, private V3/archive modification or ASUS connection was involved. They are **evidence of test-fixture behavior**, not proof of portable JFFS correctness.

### Exact future Stage B objects and provenance

Only the following install targets are in scope (all below `/jffs/addons/asus-edge/`):

| Target | Required file type and mode | Owner | Content source |
|---|---|---|---|
| `bin/issue235-ssd-mount-mode` | regular, non-symlink, `0755` | `0:0` | byte-pinned helper from reviewed PR #245 commit |
| `private/` | real directory, non-symlink, `0700` | `0:0` | private JFFS directory only |
| `private/router-data.uuid` | regular, non-symlink, `0600` | `0:0` | privately verified local UUID mapping |
| `private/entware.uuid` | regular, non-symlink, `0600` | `0:0` | privately verified local UUID mapping |

The existing JFFS ancestor directories `/jffs`, `/jffs/addons`, `/jffs/addons/asus-edge`, and `bin` must be trustworthy **root:root 0755 non-symlink** directories, as required by the draft runtime snippet. Recheck the exact helper SHA, private UUID *identity/manifest* and confidentiality **without writing/printing the UUIDs in logs, Git, diagnostics or issues**. Revalidate exact V3/original hook byte integrity separately; Stage B must **not** publish or edit V3 or touch `/jffs/scripts/post-mount`. No `services-start` edit, generic `scripts/install.sh`, `/opt`-dependent boot tooling, child SSD chmod, remount, swap operation or daemon restart.

### Non-overwrite publication and directory-trust design

1. Revalidate the approved destination allowlist and the entire trusted directory chain, including numeric owner/group, mode, type and absence of symlinks. A symlink/unknown object, path drift, unexpected target collision, missing provenance, unsafe permission, insufficient free space or failure to pin identities is an immediate **STOP/REVIEW**, not an invitation to chmod or delete existing material.
2. The Fedora `dir_fd` experiment demonstrates the **intent** to anchor and re-check directory identity, but is **not** a deployable JFFS mechanism. A future audited implementation must avoid reconstructing unchecked pathnames from mutable ancestors between validation and publication; use independently justified firmware-supported descriptor-relative primitives if available. If the router's tooling cannot meet the contract, Stage B stays HOLD; do not replace it silently with an unchecked shell `mv`.
3. Prepare each candidate under a unique, restrictive, non-symlink temporary name in its **intended directory/on the same filesystem**, opened with exclusive creation and no-follow semantics where supported. Write complete content, verify bytes/digest, assign required numeric ownership and final mode, verify on the final descriptor, and sync the file before publication. In particular, Fedora's `os.getuid()` checks are **not** evidence of `root:root` after transfer to GNUton.
4. Publish a **single verified file without replacing an existing destination**, using a publication primitive whose no-clobber/atomicity and filesystem support are explicitly established for the target JFFS environment. The Fedora `os.link` experiment does not establish JFFS hard-link or power-loss behavior; ordinary `rename`/`mv` may replace a destination and is not an acceptable implicit equivalent. After publication, verify target type, owner, mode, digest and directory identity; establish file/directory durability semantics independently before production use.
5. A successful *per-file* publish is **not a transaction for the complete helper + two UUID files**. An interrupted session may leave only a subset installed; any partial set, ambiguous existing target or unexpected hidden temp name requires **STOP and operator reconciliation**, not an automatic retry/overwrite/cleanup. Treat unverified staging as untrusted. Do not label Stage B PASS or contemplate Stage C until all three files and trusted parents independently pass post-transfer checks.
6. Fedora simulated exception interruption, **not sudden power loss**. Orphaned temporary entries must remain untouched pending owner/type/path/integrity review. Cleanup of only specifically verified artifacts needs its own narrow recovery decision. Do not remove unknown third-party entries or recursively delete the private subtree. If the directory was replaced during staging, refuse publication and require a fresh trust assessment.

### Stage B audit/decision record (before ANY future authorized router write)

Record only nonsecret boolean/aggregate evidence: exact reviewed PR revision and helper digest verification, private mapping/manifest verified (never the values), current live `post-mount` hash/owner/mode, expected two ext4 mount identities and two active swap entries, trusted JFFS directory metadata, secure wired recovery + off-router original backup availability, Stage B transfer/rollback plan and its file/directory atomicity assumptions. Re-evaluate scheduled/transient *non-root mount-root writers* and acknowledge the separately scoped permissive first-level SSD objects in [Issue #263](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/263). Do not equate a static script scan or sampled file descriptor inventory to full write-compatibility proof.

**Gate separation remains mandatory:**
- **Design gate:** Fedora synthetic tests PASS; acceptance criteria documented; **not a production stager implementation**.
- **Stage A:** read-only fresh preflight + explicit acceptance of any remaining writer/recovery risk.
- **Stage B:** separately and explicitly approved, narrow helper/private-UUID delivery only, with actual JFFS primitive/ownership/integrity compatibility independently justified.
- **Stage C:** a **second** separate approval to atomically activate the byte-exact V3 hook under the existing runbook; do not execute `post-mount` manually to trigger the change.
- **Stage E:** later **separate** approval for controlled reboot/remount persistence and service checks.

Do not infer Stage B authorization from a positive lab test, PR/issue comment, or approval of this design document. **Issue #235 OPEN / Draft PR #245 unmerged / DEPLOYMENT_GATE=HOLD.** Work on PrivDrop, SSD Trust Helper, process UID/GID and DAC migration is separate; this section makes no changes to those worktrees or their production behavior.


## 2026-10-17 — Stage B three-file provenance / recovery state-machine draft

The following **DESIGN-ONLY** companion is now available: [Stage B payload provenance and recovery contract](issue235-stageb-payload-provenance-recovery-design-draft.md). It supersedes **no** mandatory Stage A/B/C/E approvals in this runbook. Stage B v1.3 synthetic importer independently passed **60/60 unchanged v1.2 regressions + 26/26 new input checks** in the operator-provided Fedora native / static ARMv7 soft-float QEMU / Clang ASan+UBSan runs. This remains test-fixture evidence, not an installer.

The proposed production-facing *contract*, not yet implemented, requires independent manifest authenticity, exactly three allowlisted targets, root:root JFFS ownership/modes, a verified prepared set, strict no-replace publish (private UUIDs first, helper last), post-link sync/readback verification, explicit `PARTIAL_STATE_REVIEW` on uncertainty and **no automatic retry or cleanup**. The helper-last ordering is **not** an atomic transaction or authorization to execute it. JFFS2 file/directory `fsync`, no-clobber primitive semantics, power-loss state, source immutability, root-writer coverage and prechange live hook hash remain **unproven/open**. No router files touched, no Stage B/C/E permission granted. `DEPLOYMENT_GATE=HOLD`.
