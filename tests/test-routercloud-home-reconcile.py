#!/usr/bin/env python3
"""Unit gates for RouterCloud Home AJAX vs. live storage hotfix reconciliation."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts/routercloud-home-reconcile.py"
spec = importlib.util.spec_from_file_location("routercloud_home_reconcile", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

HEADER = "const demo = 1;\n"
BASE_STORAGE = (
    "function setupStorageInfo() {\n"
    "  return 'dostępne z';\n"
    "}\n"
)
LIVE_STORAGE = (
    "function setupStorageInfo() {\n"
    "  return 'wolne łącznie niedostępne';\n"
    "}\n"
)
TRAILER = "\n// ROUTERCLOUD_BACKUP_TILE_V1\nconst end = true;\n"
BASE = HEADER + BASE_STORAGE + TRAILER
LIVE = HEADER + LIVE_STORAGE + TRAILER
FEATURE = HEADER + "const ROUTERCLOUD_HOME_AJAX_V1 = true;\n" + BASE_STORAGE + TRAILER


class ReconcileTests(unittest.TestCase):
    def test_expected_hotfix_preserved_and_home_added(self):
        output = mod.reconcile(BASE, FEATURE, LIVE)
        self.assertIn("wolne łącznie niedostępne", output)
        self.assertIn("ROUTERCLOUD_HOME_AJAX_V1", output)
        self.assertEqual(mod.parts(output)[0], mod.parts(FEATURE)[0])
        self.assertEqual(mod.parts(output)[2], mod.parts(FEATURE)[2])

    def test_reject_unexpected_live_outside_drift(self):
        with self.assertRaisesRegex(mod.ReconcileRejected, "OUTSIDE_STORAGE"):
            mod.reconcile(BASE, FEATURE, LIVE.replace(HEADER, "const demo = 2;\n"))

    def test_reject_unexpected_live_tail_drift(self):
        with self.assertRaisesRegex(mod.ReconcileRejected, "OUTSIDE_STORAGE"):
            mod.reconcile(BASE, FEATURE, LIVE.replace("end = true", "end = false"))

    def test_reject_missing_live_hotfix(self):
        with self.assertRaisesRegex(mod.ReconcileRejected, "HOTFIX_NOT_FOUND"):
            mod.reconcile(BASE, FEATURE, BASE)

    def test_reject_incomplete_hotfix(self):
        incomplete = LIVE.replace("niedostępne", "")
        with self.assertRaisesRegex(mod.ReconcileRejected, "STORAGE_MARKER"):
            mod.reconcile(BASE, FEATURE, incomplete)

    def test_reject_feature_modified_storage(self):
        modified = FEATURE.replace("'dostępne z'", "'modified'")
        with self.assertRaisesRegex(mod.ReconcileRejected, "FEATURE_CHANGED_STORAGE"):
            mod.reconcile(BASE, modified, LIVE)

    def test_reject_missing_home_feature(self):
        with self.assertRaisesRegex(mod.ReconcileRejected, "HOME_AJAX_MARKER"):
            mod.reconcile(BASE, BASE, LIVE)

    def test_reject_ambiguous_storage_block(self):
        duplicate = BASE + BASE_STORAGE
        with self.assertRaisesRegex(mod.ReconcileRejected, "STORAGE_FUNCTION_AMBIGUOUS"):
            mod.reconcile(duplicate, FEATURE, LIVE)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReconcileTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    print("ROUTERCLOUD_RECONCILE_SELFTEST=" + ("PASS" if result.wasSuccessful() else "FAIL"))
    raise SystemExit(0 if result.wasSuccessful() else 1)
