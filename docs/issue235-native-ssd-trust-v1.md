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

## Explicit incomplete security gates

1. **Private UUID binding is NOT implemented.** A `/dev/*` string is not authenticated media provenance.
2. **Actual ASUS kernel execution is NOT tested.** Linux 4.1.52 cannot be inferred compatible from QEMU alone.
3. **Ancestor/mount lifetime exclusion is NOT established.** A pinned fd and second read-only check cannot prevent privileged remounts or an asynchronous rename; world-writable parents require separate policy acceptance.
4. **There is NO fchmod implementation in v1.** Do not replace PR #245's helper with this diagnostic program.
5. **Boot, swap-before-AMTM, Entware, and storage consumer compatibility remain unproven.** Existing Draft PR #245 and original `post-mount` remain untouched.

Future work requires a reviewed UUID mapping contract, live read-only preflight with separate authorization, a separately gated and auditable `fchmod` implementation, complete regression suite, independent rollback rehearsal and explicit deployment authorization. `DEPLOYMENT_GATE=HOLD` throughout.