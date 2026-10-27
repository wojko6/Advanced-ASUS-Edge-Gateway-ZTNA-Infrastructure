"""Offline-only tests for the V0.4 proposed router DNS Blackbox tile.

No VM, Blackbox, router, Caddy, browser, subprocess or network access.
"""
import importlib.util
import math
from pathlib import Path
import unittest
from datetime import datetime, timezone, timedelta

SOURCE = Path(__file__).resolve().parents[1] / "tools" / "v04_router_dns_model.py"
SPEC = importlib.util.spec_from_file_location("v04_router_dns_model", SOURCE)
assert SPEC is not None and SPEC.loader is not None
model = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


class RouterDnsOfflineModel(unittest.TestCase):
    def project(self, values=None, now=NOW):
        if values is None:
            values = {"probe_success": 1, "sample_age_seconds": 5}
        return model.project(values, now)

    def test_one_fresh_positive_probe_is_only_scoped_ok(self):
        result = self.project()
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["reason_code"], "ONE_DNS_PROBE_SUCCEEDED")
        self.assertIs(result["probe_success"], True)
        self.assertIn("not Pi-hole/Unbound health", result["limitation"])
        self.assertEqual(result["mode"], "offline-fixture-only")

    def test_one_fresh_negative_probe_does_not_claim_router_down(self):
        result = self.project({"probe_success": 0, "sample_age_seconds": 8})
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["reason_code"], "ONE_DNS_PROBE_FAILED")
        self.assertNotEqual(result["status"], "DOWN")

    def test_exact_ttl_is_fresh_but_older_is_stale(self):
        self.assertEqual(self.project({"probe_success": 1, "sample_age_seconds": 120})["status"], "OK")
        for probe in (0, 1):
            with self.subTest(probe=probe):
                result = self.project({"probe_success": probe, "sample_age_seconds": 120.001})
                self.assertEqual(result["status"], "STALE")
                self.assertIsNone(result["probe_success"])

    def test_missing_or_extra_fields_are_unknown(self):
        for values in ({}, {"probe_success": 1}, {"sample_age_seconds": 1},
                       {"probe_success": 1, "sample_age_seconds": 1, "instance": "PRIVATE"},
                       None, [], "positive"):
            with self.subTest(values=values):
                result = self.project(values)
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertIsNone(result["probe_success"])

    def test_fractional_or_out_of_range_probe_is_unknown(self):
        for probe in (0.5, -1, 2, -0.01):
            with self.subTest(probe=probe):
                self.assertEqual(self.project({"probe_success": probe, "sample_age_seconds": 5})["status"], "UNKNOWN")

    def test_negative_future_sample_age_fails_closed(self):
        self.assertEqual(self.project({"probe_success": 1, "sample_age_seconds": -0.01})["status"], "UNKNOWN")

    def test_extreme_sample_age_is_unknown(self):
        self.assertEqual(self.project({"probe_success": 0, "sample_age_seconds": 86401})["status"], "UNKNOWN")

    def test_bool_and_string_values_not_numeric(self):
        for bad in (True, False, "1", None, [], {}):
            with self.subTest(bad=bad):
                self.assertEqual(self.project({"probe_success": bad, "sample_age_seconds": 10})["status"], "UNKNOWN")
                self.assertEqual(self.project({"probe_success": 1, "sample_age_seconds": bad})["status"], "UNKNOWN")

    def test_nan_and_infinity_fail_closed(self):
        for bad in (math.nan, math.inf, -math.inf):
            with self.subTest(bad=str(bad)):
                self.assertEqual(self.project({"probe_success": bad, "sample_age_seconds": 10})["status"], "UNKNOWN")
                self.assertEqual(self.project({"probe_success": 1, "sample_age_seconds": bad})["status"], "UNKNOWN")

    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            self.project(now=datetime(2026, 10, 27, 12, 0))

    def test_timezone_normalization_is_stable(self):
        local = datetime(2026, 10, 27, 13, 0, tzinfo=timezone(timedelta(hours=1)))
        self.assertEqual(self.project(now=local)["observed_at"], "2026-10-27T12:00:00Z")

    def test_no_private_untrusted_fields_ever_emitted(self):
        result = self.project({"probe_success": 1, "sample_age_seconds": 2, "host": "PRIVATE"})
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertNotIn("host", result)
        self.assertNotIn("PRIVATE", str(result))
        self.assertEqual(set(result), {
            "schema_version", "kind", "mode", "source", "observed_at",
            "status", "reason_code", "probe_success", "sample_age_seconds",
            "ttl_seconds", "limitation",
        })

    def test_provisional_contract_is_bounded_and_offline(self):
        self.assertEqual(model.TTL_SECONDS, 120)
        self.assertEqual(model.FIELDS, {"probe_success", "sample_age_seconds"})
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in ("subprocess", "socket.", "urllib.", "requests.", "http.client."):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("127.0.0.1:8428", source)


if __name__ == "__main__":
    unittest.main()
