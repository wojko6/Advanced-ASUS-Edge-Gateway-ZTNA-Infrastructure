# Issue #235 / JFFS-13 — Native SSD Trust Helper v1 (read-only research)

**Status: EXPERIMENTAL / READ-ONLY / HOLD.** No production deployment, `chmod`, `fchmod`, post-mount activation, service restart, installer, or migration is implemented.

## Scope

`router/native/issue235-ssd-trust-v1.c` is the first deliberately constrained native ARM candidate. It accepts only `--check ROUTER_DATA` or `--check ENTWARE` in its normal build. It anchors traversal at `/` and uses `openat(O_DIRECTORY|O_NOFOLLOW)` for `/tmp`, `/tmp/mnt`, and the exact allowlisted SSD root. It obtains kernel `mnt_id` from `/proc/self/fdinfo/<fd>`, verifies a *unique* matching record in `/proc/self/mountinfo`, and requires:

- mountpoint equals the expected exact path, mount root equals `/`, filesystem type `ext4`, and `rw` present in mount and superblock options;
- a `/dev/` source (NOT yet verified by private UUID), and `major:minor` equal to `fstat(fd).st_dev`;
- root ownership for `/`, `/tmp`, `/tmp/mnt`, and SSD root; `0777` or `0755` on the SSD root; a distinct `st_dev` for the SSD compared with `/tmp/mnt` in production;
- matching inode/device across a second `openat` of the same entry and identical mount IDs at the snapshot.

The program reports whether the ancestors are world-writable. The actual ASUS has world-writable `/tmp` and `/tmp/mnt`, so `ANCESTOR_WORLD_WRITE=PRESENT` is expected. The program **does not** interpret an identity snapshot as continued trusted path. It intentionally always exits with `2` (`HOLD`) for a valid snapshot and `3` (`REJECTED`) for mismatched evidence. It never exits `0` and never writes any file or filesystem metadata.

## Offline tests

```
python3 tests/test-issue235-native-ssd-trust-v1.py
```

The suite compiles a lab-only binary (`ISSUE235_TEST_BUILD`) with test fixtures under `/tmp`. It fakes `mountinfo` records and exercises read-only identity handling, malformed and duplicated records, wrong device/mount ID/fs/root/options, symlinks, path traversal, wrong mode, and absence of the test-only CLI in the normal executable. **Lab fixture `mountinfo` is synthetic, not proof of a real ext4 mount.**

ARM Cortex-A7 compilation candidate on Fedora with installed Zig 0.16 (NOT run on ASUS):

```
zig cc -target arm-linux-musleabi -mcpu=cortex_a7 -mfloat-abi=soft \
  -static -O2 -std=c11 -Wall -Wextra -Werror \
  router/native/issue235-ssd-trust-v1.c -o /tmp/issue235-ssd-trust-v1-arm
```

Inspect ELF flags, interpreter, dynamic dependencies and run only QEMU tests **before** any live router execution. The prior prototype v0.2 QEMU success is not verification of this new source.

## 2026-10-16 — ARMv7/QEMU off-router verification

The **v1 source above** (not only the earlier v0.2 prototype) was cross-compiled by the operator on Fedora using Zig **0.16.0**, target `arm-linux-musleabi`, CPU `cortex_a7`, soft-float and `-static`. Reported `ARMV7_BUILD=PASS`; `file`/`readelf` showed **ELF32 ARM EABI5 soft-float**, no ELF interpreter (`INTERP=ABSENT`) and no dynamic `NEEDED` dependencies (`STATIC_LINK=PASS`). QEMU user-mode **10.2.2** emulated Cortex-A7. The **normal production CLI build**, invoked only with invalid `--check INVALID`, printed usage and exited **3/REJECT**, confirming emulated startup and argument rejection, **not** checking a mounted SSD.

A **separate laboratory-only** `-DISSUE235_TEST_BUILD` build used disposable Fedora directories and **synthetic** `mountinfo` fixtures. A self-consistent synthetic snapshot returned **RC=2/HOLD**; a deliberately wrong filesystem returned **RC=3/REJECT**. Both checks passed (`ARMV7_SYNTHETIC_LAB=PASS`). The subsequent Cortex-A7 negative matrix was **12/12 PASS**, each **RC=3** with `DEPLOYMENT_GATE=HOLD`: wrong mount ID, wrong device, wrong mount root, read-only mount options, read-only superblock, invalid source, wrong mountpoint, duplicate record, duplicate mount ID, symlink leaf, invalid mode and `..` traversal. The separate native x86-64 synthetic suite previously reported **15/15 PASS**. GitHub [Validation suite 38943417079](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/actions/runs/38943417079) on branch commit `866385d3c20924e31b64cfcbbaf6bf88850cf98a` **SUCCESS**, but this does **not** mean the operator's complete QEMU matrix ran inside CI.

**Acceptance boundary:** Synthetic `mountinfo` is not real ext4 proof. QEMU user-mode is not the ASUS 4.1.52 kernel, not physical SSD UUID verification and not a concurrency or power-loss test. `openat`/`O_NOFOLLOW`, `fstat`, `mnt_id` and re-opening constrain the observed identity snapshot, **not** the lifetime of the pathname during a later mutation. World-writable ancestors, privileged remounts, UUID binding, writer quiescence, Entware/RouterCloud/swap compatibility, and on-router restore/reboot validation remain unproven. Normal v1 returns **2/HOLD** for a valid diagnostic snapshot and **3/REJECT** on mismatch; **never 0**. The lab-only binary must **never be installed**. No ASUS contacted, SSD permissions changed or production services modified by these tests; `DEPLOYMENT_GATE=HOLD`.


## Explicit incomplete security gates

1. **Private UUID binding is NOT implemented.** A `/dev/*` string is not authenticated media provenance.
2. **Actual ASUS kernel execution is NOT tested.** Linux 4.1.52 cannot be inferred compatible from QEMU alone.
3. **Ancestor/mount lifetime exclusion is NOT established.** A pinned fd and second read-only check cannot prevent privileged remounts or an asynchronous rename; world-writable parents require separate policy acceptance.
4. **There is NO fchmod implementation in v1.** Do not replace PR #245's helper with this diagnostic program.
5. **Boot, swap-before-AMTM, Entware, and storage consumer compatibility remain unproven.** Existing Draft PR #245 and original `post-mount` remain untouched.

Future work requires a reviewed UUID mapping contract, live read-only preflight with separate authorization, a separately gated and auditable `fchmod` implementation, complete regression suite, independent rollback rehearsal and explicit deployment authorization. `DEPLOYMENT_GATE=HOLD` throughout.