"""Synthetic-only HCC V0.6-B1 coverage contract and negative tests."""
from __future__ import annotations

from copy import deepcopy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import v06_coverage_model as coverage

END = 1793260800000  # fixed clock: synthetic UTC 2026-10-29
START = END - coverage.WINDOWS_MS["24h"]


def fixture(times=None, *, end=END, window="24h"):
    if times is None:
        times = [end-240000, end-180000, end-120000, end-60000]
    out = {name: [] for name in coverage.SUFFIXES}
    modes = (0, 0, 1, 1)
    for i, ts in enumerate(times):
        # All values are synthetic, not derived from the production repository.
        boot = modes[i] if len(times) == 4 else 0
        row = {
            "mode_local": 1-boot,
            "mode_bootstrap": boot,
            "state_valid": 1,
            "last_transition_timestamp_seconds": 0,
            "fallback_since_timestamp_seconds": (ts // 1000 if boot else 0),
            "fallback_transitions_runtime_total": int(boot),
            "collection_timestamp_seconds": ts // 1000,
        }
        for k in coverage.SUFFIXES:
            out[k].append((ts, row[k]))
    return out


class CoverageModel(unittest.TestCase):
    def test_regular_samples_no_gaps_in_window(self):
        times = list(range(END-3600000, END+1, 60000))
        report = coverage.analyze(fixture(times), "1h", END)
        self.assertEqual(report["status"], "COVERAGE_OBSERVED")
        self.assertEqual(report["sample_count"], 61)
        self.assertEqual(report["gaps"], [])
        self.assertEqual(len(report["segments"]), 1)
        self.assertEqual(report["segments"][0]["sample_count"], 61)
        self.assertEqual(report["max_cross_series_skew_ms"], 0)
        self.assertEqual(report["deployment_gate"], "HOLD")
        self.assertNotIn("events", report)

    def test_long_internal_gap_is_missing_telemetry_not_dns_outage(self):
        times = [START+60000, START+120000, START+240000,
                 START+38190000, START+38250000]
        report = coverage.analyze(fixture(times), "24h", END)
        self.assertEqual(report["status"], "COVERAGE_OBSERVED_WITH_UNCERTAINTY")
        internal = [g for g in report["gaps"] if g["position"] == "INTERNAL"]
        self.assertEqual(len(internal), 1)
        self.assertEqual(internal[0]["kind"], "TELEMETRY_GAP")
        self.assertEqual(internal[0]["cause"], "NOT_DETERMINED")
        self.assertEqual(internal[0]["duration_seconds"], 37950)
        self.assertEqual(len(report["segments"]), 2)
        self.assertNotIn("PLANNED_SHUTDOWN", str(report))
        self.assertNotIn("DNS_OUTAGE", str(report))

    def test_leading_trailing_boundary_gaps_have_separate_labels(self):
        times = [START+600000, START+660000]
        report = coverage.analyze(fixture(times), "24h", END)
        self.assertEqual([g["position"] for g in report["gaps"]],
                         ["LEADING", "TRAILING"])
        self.assertEqual(len(report["segments"]), 1)

    def test_invalid_state_breaks_segment_without_claiming_transition(self):
        times = [END-240000, END-180000, END-120000, END-60000]
        data = fixture(times)
        data["state_valid"][2] = (times[2], 0)
        report = coverage.analyze(data, "24h", END)
        self.assertEqual(report["invalid_sample_count"], 1)
        self.assertEqual(len(report["segments"]), 2)
        self.assertNotIn("events", report)
        self.assertEqual(report["status"], "COVERAGE_OBSERVED_WITH_UNCERTAINTY")

    def test_same_counts_but_bad_cross_series_timestamp_fails_closed(self):
        data = fixture()
        ts, val = data["state_valid"][1]
        data["state_valid"][1] = (ts+5001, val)
        report = coverage.analyze(data, "24h", END)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(report["segments"], [])
        self.assertIsNone(report["sample_count"])

    def test_slight_cross_series_timestamp_skew_allowed_but_reported(self):
        data = fixture()
        ts, val = data["state_valid"][1]
        data["state_valid"][1] = (ts+1200, val)
        report = coverage.analyze(data, "24h", END)
        self.assertEqual(report["max_cross_series_skew_ms"], 1200)
        self.assertEqual(report["status"], "COVERAGE_OBSERVED_WITH_UNCERTAINTY")

    def test_mismatched_counts_fails_closed(self):
        data = fixture()
        data["state_valid"].pop()
        self.assertEqual(coverage.analyze(data, "24h", END)["status"], "UNKNOWN")

    def test_reject_extra_labels_unsorted_and_duplicate_timestamps(self):
        base = fixture()
        cases = []
        extra = deepcopy(base)
        extra["instance"] = []
        cases.append(extra)
        duplicate = deepcopy(base)
        duplicate["mode_local"][1] = duplicate["mode_local"][0]
        cases.append(duplicate)
        reverse = deepcopy(base)
        reverse["mode_bootstrap"].reverse()
        cases.append(reverse)
        for case in cases:
            with self.subTest(case=str(list(case)[:3])):
                self.assertEqual(coverage.analyze(case, "24h", END)["status"], "UNKNOWN")

    def test_reject_boolean_nonfinite_future_collection_and_invalid_window(self):
        import math
        for field, value in (("mode_local", True),
                             ("mode_bootstrap", math.inf),
                             ("collection_timestamp_seconds", 4102444800)):
            data = fixture()
            ts, _ = data[field][1]
            data[field][1] = (ts, value)
            with self.subTest(field=field):
                self.assertEqual(coverage.analyze(data, "24h", END)["status"], "UNKNOWN")
        self.assertEqual(coverage.analyze(fixture(), "30d", END)["status"], "UNKNOWN")
        self.assertEqual(coverage.analyze(fixture(), "24h", True)["status"], "UNKNOWN")
        self.assertEqual(coverage.analyze(fixture(), "24h", END+10000000000000)["status"], "UNKNOWN")

    def test_large_seven_day_synthetic_sample_set_is_bounded_and_supported(self):
        times = [END-4962*60000 + i*60000 for i in range(4963)]
        result = coverage.analyze(fixture(times), "7d", END)
        self.assertEqual(result["sample_count"], 4963)
        self.assertEqual(result["status"], "COVERAGE_OBSERVED_WITH_UNCERTAINTY")
        self.assertEqual(len(result["segments"]), 1)
        self.assertTrue(any(g["position"] == "LEADING" for g in result["gaps"]))

    def test_protect_against_unbounded_input_and_output_segments(self):
        too_many = [END-(12000-i)*500 for i in range(12001)]
        self.assertEqual(coverage.analyze(fixture(too_many), "24h", END)["status"], "UNKNOWN")
        split = [END-(256-i)*240000 for i in range(257)]
        report = coverage.analyze(fixture(split), "24h", END)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(report["reason_code"], "SOURCE_OR_COVERAGE_CONTRACT_NOT_VERIFIED")

    def test_no_samples_is_unknown_not_healthy(self):
        report = coverage.analyze({name: [] for name in coverage.SUFFIXES}, "24h", END)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(report["reason_code"], "NO_TELEMETRY_IN_WINDOW")
        self.assertEqual(report["deployment_gate"], "HOLD")


if __name__ == "__main__":
    unittest.main()
