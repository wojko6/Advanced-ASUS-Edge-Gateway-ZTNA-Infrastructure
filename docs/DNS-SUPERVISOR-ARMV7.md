# DNS Guard ARMv7 supervisor — build, verification and rollback (PR #197)

Scope: ASUS TUF-AX5400, Linux 4.1.52, ARMv7 EABI5 soft-float. The
`router/src/edge-dns-supervisor.c` source is compiled as a **static** Linux ARM
executable. The reviewed executable is `router/bin/edge-dns-supervisor`, installed
as `/jffs/addons/asus-edge/bin/edge-dns-supervisor`. Do not execute the PR
artifact on the production router during development.

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
