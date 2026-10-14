#!/usr/bin/env python3
"""Issue #235: isolated Linux DAC and sticky-bit regression fixture.

Run on Fedora only after reviewing the script:
    sudo python3 tests/test-issue235-ssd-dac.py

Creates synthetic directories under a randomized /tmp folder; never reads
RouterCloud settings, SSD mount paths, tokens, keys, or production files.
Requires root solely to fork a short-lived UID/GID 65534 test child.
"""

from __future__ import annotations

import errno
import os
import stat
import tempfile

ATTACK_UID = 65534
ATTACK_GID = 65534


def attack(path: str, destination: str | None = None, *, create: bool = False) -> str:
    """Try one filesystem entry mutation as nobody; return ALLOW/DENY/ERROR."""
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        result = "ERROR"
        try:
            os.setgroups([])
            os.setgid(ATTACK_GID)
            os.setuid(ATTACK_UID)
            try:
                if create:
                    os.mkdir(path)
                else:
                    assert destination is not None
                    os.rename(path, destination)
                result = "ALLOW"
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EPERM):
                    result = "DENY"
                else:
                    result = f"ERROR_{exc.errno}"
        except OSError as exc:
            result = f"IDENTITY_ERROR_{exc.errno}"
        os.write(write_fd, result.encode("ascii"))
        os.close(write_fd)
        os._exit(0)

    os.close(write_fd)
    output = os.read(read_fd, 128).decode("ascii")
    os.close(read_fd)
    _, status = os.waitpid(pid, 0)
    if not os.WIFEXITED(status) or os.WEXITSTATUS(status):
        return "CHILD_ERROR"
    return output


def fixture(root: str, mount_mode: int, state_mode: int, seq: int) -> tuple[str, str, str]:
    """Create fresh root-owned pretend mount, state and protected favorites."""
    mount = os.path.join(root, f"isolated-mount-{seq}")
    os.mkdir(mount, 0o700)
    state = os.path.join(mount, ".routercloud-system")
    os.mkdir(state, 0o700)
    favorites = os.path.join(state, "favorites")
    os.mkdir(favorites, 0o700)
    os.chmod(mount, mount_mode)
    os.chmod(state, state_mode)
    assert os.stat(mount).st_uid == 0
    assert os.stat(state).st_uid == 0
    assert stat.S_IMODE(os.stat(mount).st_mode) == mount_mode
    assert stat.S_IMODE(os.stat(state).st_mode) == state_mode
    return mount, state, favorites


def main() -> int:
    print("=== ISSUE235 / ISOLATED SSD DAC REGRESSION ===")
    if os.name != "posix" or not hasattr(os, "fork"):
        print("PLATFORM=UNSUPPORTED")
        return 2
    if os.geteuid() != 0:
        print("LAB_ONLY_ROOT_REQUIRED=YES")
        print("RESULT=NOT_RUN")
        return 2

    # name, mount mode, state mode, can rename state, can rename favorites,
    # can create a new entry directly under pretend mount root
    cases = [
        ("BASELINE_0777_0777", 0o777, 0o777, True, True, True),
        ("STICKY_1777_0700", 0o1777, 0o700, False, False, True),
        ("STRICT_0755_0700", 0o755, 0o700, False, False, False),
        ("STICKY_ONLY_1777_0777", 0o1777, 0o777, False, True, True),
        ("STATE_ONLY_0777_0700", 0o777, 0o700, True, False, True),
    ]
    failures = 0

    with tempfile.TemporaryDirectory(prefix="issue235-ssd-dac-", dir="/tmp") as temp:
        # The nonroot test identity needs to traverse the synthetic parent.
        os.chmod(temp, 0o755)
        seq = 0
        for name, mount_mode, state_mode, expect_mount, expect_leaf, expect_create in cases:
            seq += 1
            _, state, _ = fixture(temp, mount_mode, state_mode, seq)
            state_result = attack(state, state + ".renamed")

            seq += 1
            _, _, favorites = fixture(temp, mount_mode, state_mode, seq)
            leaf_result = attack(favorites, favorites + ".renamed")

            seq += 1
            mount, _, _ = fixture(temp, mount_mode, state_mode, seq)
            create_result = attack(os.path.join(mount, "nonroot-new-entry"), create=True)

            expected = tuple(
                "ALLOW" if flag else "DENY"
                for flag in (expect_mount, expect_leaf, expect_create)
            )
            observed = (state_result, leaf_result, create_result)
            status = "PASS" if observed == expected else "FAIL"
            failures += status != "PASS"
            print(
                f"{name}={status} "
                f"state_rename={state_result} "
                f"leaf_rename={leaf_result} "
                f"mount_create={create_result}"
            )

    print("PRODUCTION_FILES_TOUCHED=NO")
    print("SOURCE_DEVICE_MOUNTS_TOUCHED=NO")
    print("TEMP_FIXTURE_REMOVED=YES")
    print(f"ISSUE235_SSD_DAC_LAB={'PASS' if failures == 0 else 'FAIL'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
