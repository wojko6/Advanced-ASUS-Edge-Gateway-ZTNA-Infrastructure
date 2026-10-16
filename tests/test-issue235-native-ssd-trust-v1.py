#!/usr/bin/env python3
"""Isolated, READ-ONLY unit tests. Uses synthetic mountinfo, not a real ext4 mount.

No ASUS, no elevated privileges, no chmod of existing files, no production binaries.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "router/native/issue235-ssd-trust-v1.c"


class NativeSSDTrustV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory(prefix="issue235-native-gate-", dir="/tmp")
        cls.bin = Path(cls.work.name) / "native-gate-test"
        result = subprocess.run(
            ["cc", "-DISSUE235_TEST_BUILD", "-std=c11", "-Wall", "-Wextra",
             "-Werror", "-O2", str(SOURCE), "-o", str(cls.bin)],
            capture_output=True, text=True,
        )
        if result.returncode:
            raise AssertionError("TEST_COMPILATION_FAILED: " + result.stderr[-3000:])

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def setUp(self):
        # Path has exactly 3 components: /tmp/<random test parent>/<mount entry>.
        self.d = tempfile.TemporaryDirectory(prefix="case-", dir="/tmp")
        self.base = Path(self.d.name)
        self.target = self.base / "ROUTER_DATA"
        self.target.mkdir()
        self.mountinfo = self.base / "mountinfo.txt"
        fd = os.open(self.target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            content = Path(f"/proc/self/fdinfo/{fd}").read_text()
        finally:
            os.close(fd)
        self.mntid = int(next(x.split(":", 1)[1].strip() for x in content.splitlines()
                              if x.startswith("mnt_id:")))
        st = self.target.stat()
        self.maj, self.min = os.major(st.st_dev), os.minor(st.st_dev)

    def tearDown(self):
        self.d.cleanup()

    def make_record(self, *, fs="ext4", root="/", opts="rw,relatime",
                    sb="rw", mntid=None, device=None, dest=None, source="/dev/mock"):
        record = (f"{self.mntid if mntid is None else mntid} 1 "
                  f"{self.maj}:{self.min}" if device is None else
                  f"{self.mntid if mntid is None else mntid} 1 {device}")
        record += f" {root} {dest or self.target} {opts} - {fs} {source} {sb}\n"
        self.mountinfo.write_text(record)

    def run_gate(self, target=None):
        return subprocess.run(
            [str(self.bin), "--lab-check", str(target or self.target), str(self.mountinfo)],
            capture_output=True, text=True, timeout=10,
        )

    def test_synthetic_identity_snapshot_is_hold(self):
        self.make_record()
        p = self.run_gate()
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("PINNED_MOUNTINFO_IDENTITY=PASS", p.stdout)
        self.assertIn("ENTRY_IDENTITY_RECHECK=PASS", p.stdout)
        self.assertIn("SEPARATE_DEVICE_BOUNDARY=NOT_PROVEN_SYNTHETIC", p.stdout)
        self.assertIn("DEPLOYMENT_GATE=HOLD", p.stdout)

    def test_wrong_mount_id_is_rejected(self):
        self.make_record(mntid=self.mntid + 5000)
        self.assertEqual(self.run_gate().returncode, 3)

    def test_wrong_device_is_rejected(self):
        self.make_record(device="9:999999")
        self.assertEqual(self.run_gate().returncode, 3)

    def test_wrong_fstype_is_rejected(self):
        self.make_record(fs="tmpfs")
        self.assertEqual(self.run_gate().returncode, 3)

    def test_not_fs_root_is_rejected(self):
        self.make_record(root="/nested")
        self.assertEqual(self.run_gate().returncode, 3)

    def test_ro_options_are_rejected(self):
        self.make_record(opts="ro", sb="ro")
        self.assertEqual(self.run_gate().returncode, 3)

    def test_non_block_source_is_rejected(self):
        self.make_record(source="tmpfs")
        self.assertEqual(self.run_gate().returncode, 3)

    def test_mountpoint_mismatch_is_rejected(self):
        self.make_record(dest=self.base / "OTHER")
        self.assertEqual(self.run_gate().returncode, 3)

    def test_duplicate_mountpoint_is_rejected(self):
        self.make_record()
        self.mountinfo.write_text(self.mountinfo.read_text() * 2)
        self.assertEqual(self.run_gate().returncode, 3)

    def test_symlink_target_is_rejected(self):
        self.make_record()
        real = self.base / "real"
        self.target.rename(real)
        self.target.symlink_to(real, target_is_directory=True)
        self.assertEqual(self.run_gate().returncode, 3)

    def test_symlink_ancestor_is_rejected(self):
        self.make_record()
        alias = Path("/tmp") / ("issue235-test-alias-" + str(os.getpid()))
        try:
            if alias.exists() or alias.is_symlink():
                self.skipTest("test alias collision")
            alias.symlink_to(self.base, target_is_directory=True)
            self.assertEqual(self.run_gate(target=alias / self.target.name).returncode, 3)
        finally:
            if alias.is_symlink():
                alias.unlink()

    def test_dot_dot_component_is_rejected(self):
        self.make_record()
        path = f"{self.base}/../{self.base.name}/ROUTER_DATA"
        self.assertEqual(self.run_gate(target=path).returncode, 3)

    def test_invalid_mode_is_rejected(self):
        self.make_record()
        # Fixture mode is the only change and remains inside temporary test tree.
        self.target.chmod(0o1777)
        self.assertEqual(self.run_gate().returncode, 3)

    def test_no_hidden_mutation_in_source(self):
        source = SOURCE.read_text()
        for forbidden in ("fchmod(", "chmod(", "fchown(", "chown(", "mount(", "umount("):
            self.assertNotIn(forbidden, source)

    def test_production_binary_rejects_lab_option(self):
        prod = self.base / "native-production"
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2",
                        str(SOURCE), "-o", str(prod)], check=True, capture_output=True)
        self.make_record()
        p = subprocess.run([str(prod), "--lab-check", str(self.target),
                            str(self.mountinfo)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)