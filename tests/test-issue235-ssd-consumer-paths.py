#!/usr/bin/env python3
"""Synthetic /tmp-only Issue235 consumer access regression; NEVER touches ASUS mounts.

Fedora operator run:
    sudo python3 tests/test-issue235-ssd-consumer-paths.py

Root is required only to create synthetic UID/GID ownership and fork a
short-lived nonroot test process. No services or production files are used.
"""
from __future__ import annotations

import errno
import os
import tempfile

TEST_UID = 65534
TEST_GID = 65534


def probe(path: str, mode: str) -> str:
    rd, wr = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(rd)
        try:
            os.setgroups([])
            os.setgid(TEST_GID)
            os.setuid(TEST_UID)
            flags = os.O_RDONLY if mode == "read" else os.O_WRONLY | os.O_CREAT | os.O_EXCL
            try:
                fd = os.open(path, flags, 0o600)
                os.close(fd)
                result = "ALLOW"
            except OSError as exc:
                result = "DENY" if exc.errno in (errno.EACCES, errno.EPERM) else f"ERROR_{exc.errno}"
        except OSError as exc:
            result = f"UID_SWITCH_ERROR_{exc.errno}"
        os.write(wr, result.encode("ascii"))
        os.close(wr)
        os._exit(0)
    os.close(wr)
    answer = os.read(rd, 100).decode("ascii")
    os.close(rd)
    _, status = os.waitpid(pid, 0)
    return answer if os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0 else "CHILD_FAIL"


def run_case(parent: str, name: str, mount_mode: int, expected_top_write: str) -> bool:
    mount = os.path.join(parent, name)
    os.mkdir(mount, 0o700)
    data = os.path.join(mount, "RouterCloud")
    state = os.path.join(mount, ".routercloud-system")
    delegated = os.path.join(mount, "nonroot-owned-workspace")
    for path in (data, state, delegated):
        os.mkdir(path, 0o700)
    os.chown(delegated, TEST_UID, TEST_GID)
    secret = os.path.join(data, "private-fixture")
    state_secret = os.path.join(state, "private-state-fixture")
    for private_file in (secret, state_secret):
        with open(private_file, "w", encoding="utf-8") as out:
            out.write("synthetic only\n")
        os.chmod(private_file, 0o600)
    os.chmod(mount, mount_mode)

    # Model the existing root-owned restricted sync/backup destination.
    root_write = os.path.join(data, "root-sync-fixture")
    try:
        with open(root_write, "w", encoding="utf-8") as out:
            out.write("synthetic sync\n")
        root_sync = "ALLOW"
    except OSError:
        root_sync = "DENY"

    observed = {
        "root_sync_existing_0700": root_sync,
        "nobody_read_root_data": probe(secret, "read"),
        "nobody_write_root_data": probe(os.path.join(data, "nobody-new"), "write"),
        "nobody_read_root_state": probe(state_secret, "read"),
        "nobody_write_own_0700_subdir": probe(os.path.join(delegated, "nobody-new"), "write"),
        "nobody_write_mount_root": probe(os.path.join(mount, "nobody-top"), "write"),
    }
    expected = {
        "root_sync_existing_0700": "ALLOW",
        "nobody_read_root_data": "DENY",
        "nobody_write_root_data": "DENY",
        "nobody_read_root_state": "DENY",
        "nobody_write_own_0700_subdir": "ALLOW",
        "nobody_write_mount_root": expected_top_write,
    }
    passed = observed == expected
    print(f"{name}={'PASS' if passed else 'FAIL'} " + " ".join(f"{key}={val}" for key, val in observed.items()))
    return passed


def main() -> int:
    print("=== ISSUE235 / SSD CONSUMER COMPATIBILITY LAB ===")
    if os.name != "posix" or os.geteuid() != 0 or not hasattr(os, "fork"):
        print("ROOT_LAB_PREREQUISITE=FAIL")
        return 2
    with tempfile.TemporaryDirectory(prefix="issue235-ssd-consumers-", dir="/tmp") as root:
        os.chmod(root, 0o755)
        sticky_ok = run_case(root, "STICKY_1777", 0o1777, "ALLOW")
        strict_ok = run_case(root, "STRICT_0755", 0o755, "DENY")
    print("TEST_FIXTURES_REMOVED=YES")
    print("ROUTER_FILES_TOUCHED=NO")
    print("PRODUCTION_SERVICES_RESTARTED=NO")
    print(f"ISSUE235_CONSUMER_COMPATIBILITY={'PASS' if sticky_ok and strict_ok else 'FAIL'}")
    return 0 if sticky_ok and strict_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
