#!/usr/bin/env python3
"""Synthetic, offline regression tests; never contact the production router."""
import hashlib
import importlib.util
import io
from pathlib import Path
import sqlite3
import tarfile
import tempfile
import unittest

MODPATH = Path(__file__).resolve().parents[1] / "scripts/backup-pihole-dr.py"
spec = importlib.util.spec_from_file_location("pihole_dr_generator", MODPATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

ACCOUNT = "uid=999(pihole) gid=999(pihole) groups=999(pihole)\n"
PACKAGE = "Package: pi-hole\nVersion: synthetic-only\nArchitecture: synthetic\n"
CAPS = "/opt/bin/pihole-FTL cap_chown,cap_net_bind_service,cap_net_admin,cap_net_raw,cap_ipc_lock,cap_sys_nice,cap_sys_time=eip\n"


def fixture(tmp, overrides=None):
    overrides = overrides or {}
    sqlite_path = tmp / "synthetic-gravity.db"
    con = sqlite3.connect(sqlite_path)
    try:
        con.execute("CREATE TABLE domainlist (id INTEGER PRIMARY KEY, domain TEXT)")
        con.execute("INSERT INTO domainlist (domain) VALUES ('synthetic.example.org')")
        con.commit()
    finally:
        con.close()
    path = tmp / "snapshot.tar"
    with tarfile.open(path, "w") as tar:
        for name in mod.SOURCE_FILES:
            payload = sqlite_path.read_bytes() if name.endswith("gravity.db") else ("synthetic fixture for " + name).encode()
            meta = overrides.get(name, mod.CRITICAL_METADATA.get(name, (0, 0, 0o755)))
            item = tarfile.TarInfo(name)
            item.uid, item.gid, item.mode = meta
            item.size = len(payload)
            tar.addfile(item, io.BytesIO(payload))
    dirs = {d: (0, 0, 0o755) for d in mod.SOURCE_DIRS}
    dirs["opt/etc/pihole"] = (999, 999, 0o755)
    return path, dirs


class Tests(unittest.TestCase):
    def test_cleanroom_archive_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source, dirs = fixture(tmp)
            result = tmp / "output.tar.gz"
            count = mod.build_archive(source, result, dirs, ACCOUNT, PACKAGE, CAPS)
            self.assertEqual(count, len(mod.SOURCE_FILES))
            mod.verify_archive(result)
            with tarfile.open(result, "r:gz") as arc:
                self.assertEqual(arc.getmember("./opt/etc/pihole/").uid, 999)
                self.assertEqual(arc.getmember("./opt/etc/pihole/gravity.db").gid, 999)
                self.assertEqual(arc.getmember("./opt/etc/pihole/gravity.db").mode, 0o640)
                self.assertIn("./recovery-reference/jffs/scripts/post-mount", arc.getnames())
                self.assertNotIn("./jffs/scripts/post-mount", arc.getnames())
                text = arc.extractfile("./manifest/files.sha256").read().decode()
                self.assertEqual(len(text.splitlines()), len(mod.SOURCE_FILES)+3)

    def test_legacy_gravity_uid_and_mode_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source, dirs = fixture(tmp, {"opt/etc/pihole/gravity.db": (0, 0, 0o600)})
            with self.assertRaisesRegex(ValueError, "SOURCE_METADATA_DRIFT:opt/etc/pihole/gravity.db"):
                mod.build_archive(source, tmp / "out.tar.gz", dirs, ACCOUNT, PACKAGE, CAPS)

    def test_legacy_pihole_directory_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source, dirs = fixture(tmp)
            dirs["opt/etc/pihole"] = (0, 0, 0o700)
            with self.assertRaisesRegex(ValueError, "PIHOLE_DIRECTORY_METADATA_DRIFT"):
                mod.build_archive(source, tmp / "out.tar.gz", dirs, ACCOUNT, PACKAGE, CAPS)

    def test_invalid_caps_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source, dirs = fixture(tmp)
            with self.assertRaisesRegex(ValueError, "FTL_CAPABILITIES_UNEXPECTED"):
                mod.build_archive(source, tmp / "out.tar.gz", dirs, ACCOUNT, PACKAGE, "cap_net_bind_service=eip\n")

    def test_sqlite_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source, dirs = fixture(tmp)
            altered = tmp / "bad.tar"
            with tarfile.open(source, "r:") as first, tarfile.open(altered, "w") as second:
                for member in first:
                    blob = b"not sqlite" if member.name.endswith("gravity.db") else first.extractfile(member).read()
                    member.size = len(blob)
                    second.addfile(member, io.BytesIO(blob))
            with self.assertRaises(sqlite3.Error):
                mod.build_archive(altered, tmp / "out.tar.gz", dirs, ACCOUNT, PACKAGE, CAPS)

    def test_excluded_paths_not_allowlisted(self):
        self.assertNotIn("opt/etc/pihole/pihole-FTL.db", mod.SOURCE_FILES)
        self.assertNotIn("opt/etc/pihole/cli_pw", mod.SOURCE_FILES)
        self.assertNotIn("opt/var/lib/tailscale/tailscaled.state", mod.SOURCE_FILES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
