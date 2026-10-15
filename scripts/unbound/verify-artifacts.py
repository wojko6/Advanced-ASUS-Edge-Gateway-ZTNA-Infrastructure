#!/usr/bin/env python3
"""Offline package metadata/ELF contract for seven ARMv7 Unbound IPKs.

Read-only. Does not require or access the reference router.
"""
from __future__ import annotations

import io
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

NAMES = (
    "libunbound", "unbound-daemon", "unbound-anchor",
    "unbound-checkconf", "unbound-control", "unbound-control-setup",
    "unbound-host",
)
VERSION = "1.26.1-1"
ARCH = "armv7-3.2"


def fail(reason: str) -> None:
    raise SystemExit("UNBOUND_IPK_VERIFY=FAIL: " + reason)


def ipk_member(path: Path, basename: str) -> bytes:
    """Read one IPK member from either Debian ar or OpenWrt tar format."""
    if path.read_bytes()[:8] == b"!<arch>\n":
        output = subprocess.run(
            ["ar", "p", str(path), basename], capture_output=True, check=False
        )
        if output.returncode:
            fail(f"{path.name}: missing ar member {basename}")
        return output.stdout

    try:
        with tarfile.open(path, "r:*") as archive:
            candidates = [
                member for member in archive.getmembers()
                if member.name.removeprefix("./") == basename and member.isfile()
            ]
            if len(candidates) != 1:
                fail(f"{path.name}: expected exactly one {basename}")
            handle = archive.extractfile(candidates[0])
            if handle is None:
                fail(f"{path.name}: unreadable {basename}")
            return handle.read()
    except (tarfile.TarError, OSError) as exc:
        fail(f"{path.name}: invalid IPK container: {exc}")


def nested_tar_file(blob: bytes, wanted: str, owner: str) -> bytes:
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as archive:
            matches = [
                member for member in archive.getmembers()
                if member.name.removeprefix("./") == wanted and member.isfile()
            ]
            if len(matches) != 1:
                fail(f"{owner}: expected exactly one {wanted}")
            result = archive.extractfile(matches[0])
            if result is None:
                fail(f"{owner}: unreadable {wanted}")
            return result.read()
    except tarfile.TarError as exc:
        fail(f"{owner}: invalid nested tar: {exc}")


def verify_elf(binary: bytes) -> None:
    with tempfile.TemporaryDirectory(prefix="unbound-ipk-") as d:
        path = Path(d) / "unbound"
        path.write_bytes(binary)
        header = subprocess.run(["readelf", "-h", str(path)], capture_output=True, text=True, check=True).stdout
        phdr = subprocess.run(["readelf", "-l", str(path)], capture_output=True, text=True, check=True).stdout
        if not re.search(r"Class:\s+ELF32", header):
            fail("unbound executable is not ELF32")
        if not re.search(r"Machine:\s+ARM", header):
            fail("unbound executable is not ARM")
        if "Version5 EABI" not in header or "soft-float ABI" not in header:
            fail("unbound executable has unexpected ABI")
        if "/opt/lib/ld-linux.so.3" not in phdr:
            fail("unbound interpreter mismatch")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: verify-artifacts.py ARTIFACT_DIR")
    root = Path(sys.argv[1])
    expected_files = {f"{name}_{VERSION}_{ARCH}.ipk" for name in NAMES}
    if not root.is_dir():
        fail("artifact directory missing")
    files = {x.name for x in root.glob("*.ipk")}
    if files != expected_files:
        fail(f"unexpected package set: missing={expected_files-files}, extra={files-expected_files}")

    for name in NAMES:
        path = root / f"{name}_{VERSION}_{ARCH}.ipk"
        control = nested_tar_file(ipk_member(path, "control.tar.gz"), "control", path.name)
        fields = {}
        for line in control.decode("utf-8").splitlines():
            if ": " in line and not line.startswith((" ", "\t")):
                key, value = line.split(": ", 1)
                fields[key] = value
        for field, expected in (("Package", name), ("Version", VERSION), ("Architecture", ARCH)):
            if fields.get(field) != expected:
                fail(f"{path.name}: {field}={fields.get(field)!r}, expected {expected!r}")
        if name == "unbound-daemon":
            binary = nested_tar_file(
                ipk_member(path, "data.tar.gz"), "opt/sbin/unbound", path.name
            )
            verify_elf(binary)
        print(f"UNBOUND_IPK_METADATA=PASS {name}")

    print("UNBOUND_IPK_SET_AND_ABI=PASS")


if __name__ == "__main__":
    main()
