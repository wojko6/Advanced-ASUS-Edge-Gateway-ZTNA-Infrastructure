"""Synthetic-only B3B2A worker/contract tests. NO VictoriaMetrics access."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import v06_b3b2_source_supervisor as guard
import v06_coverage_model as coverage
import v06_history_source as source

END = 1793260800000

def synthetic(window="1h"):
    times = [END-120000, END-60000, END]
    series = {}
    for name in coverage.SUFFIXES:
        if name in ("mode_local", "state_valid"):
            vals = [1, 1, 1]
        elif name == "collection_timestamp_seconds":
            vals = [x//1000 for x in times]
        else:
            vals = [0, 0, 0]
        series[name] = list(zip(times, vals))
    result = coverage.analyze(series, window, END)
    assert result["status"] == "COVERAGE_OBSERVED_WITH_UNCERTAINTY"
    result["source_adapter"] = source.SCHEMA
    return result

def cmd(script):
    return [sys.executable, "-B", "-c", script]

class SupervisorTests(unittest.TestCase):
    def test_project_only_approved_b2_contract_and_strip_untrusted_fields(self):
        report = synthetic()
        report["PRIVATE_HOST"] = "sensitive content"
        result = guard._project(json.dumps(report).encode(), "1h")
        self.assertEqual(result["sample_count"], 3)
        self.assertEqual(result["max_cross_series_skew_ms"], 0)
        self.assertEqual(len(result["segments"]), 1)
        self.assertEqual(len(result["gaps"]), 1)
        self.assertEqual(result["status"], "COVERAGE_OBSERVED_WITH_UNCERTAINTY")
        self.assertNotIn("PRIVATE_HOST", json.dumps(result))
        self.assertEqual(result["deployment_gate"], "HOLD")

    def test_synthetic_worker_success_and_identical_no_stale_cache(self):
        payload = json.dumps(synthetic())
        with patch.object(guard, "_fixed_argv", return_value=cmd(
                "import sys;sys.stdout.write(" + repr(payload) + ")")):
            result = guard.read_b2_supervised("1h")
        self.assertEqual(result["sample_count"], 3)
        self.assertEqual(result["status"], "COVERAGE_OBSERVED_WITH_UNCERTAINTY")
        with patch.object(guard, "_fixed_argv", return_value=cmd(
                "print('not JSON')")):
            bad = guard.read_b2_supervised("1h")
        self.assertEqual(bad["status"], "UNKNOWN")
        self.assertIsNone(bad["sample_count"])
        self.assertEqual(bad["segments"], [])
        self.assertNotEqual(result, bad)

    def test_bad_window_never_spawns_a_process(self):
        with patch.object(guard.subprocess, "Popen", side_effect=AssertionError("Popen called")):
            self.assertEqual(guard.read_b2_supervised("30d")["status"], "UNKNOWN")
            self.assertEqual(guard.read_b2_supervised(True)["status"], "UNKNOWN")

    def test_worker_total_deadline_kills_and_returns_unknown(self):
        with patch.object(guard, "MAX_CHILD_SECONDS", 0.15), patch.object(
            guard, "_fixed_argv", return_value=cmd("import time;time.sleep(10)")
        ):
            t = time.monotonic()
            report = guard.read_b2_supervised("24h")
            elapsed = time.monotonic() - t
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertLess(elapsed, 2.5)

    def test_stdout_above_cap_rejected_while_streaming(self):
        with patch.object(guard, "_fixed_argv", return_value=cmd(
                "import sys;sys.stdout.write('x'*70000)")):
            result = guard.read_b2_supervised("7d")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["sample_count"])

    def test_nonzero_child_and_private_stderr_not_exposed(self):
        with patch.object(guard, "_fixed_argv", return_value=cmd(
                "import sys;sys.stderr.write('SECRET');print('bad');sys.exit(2)")):
            report = guard.read_b2_supervised("1h")
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertNotIn("SECRET", json.dumps(report))

    def test_reject_wrong_window_timestamp_and_provenance(self):
        base = synthetic()
        for changes in (
            {"window": "24h"},
            {"source_adapter": "untrusted"},
            {"status": "OK"},
            {"deployment_gate": "OPEN"},
            {"max_cross_series_skew_ms": 5001},
            {"sample_count": True},
            {"window_end_utc": "2026-02-30T13:00:00.000Z"},
            {"segments": []},
            {"invalid_sample_count": 1},
        ):
            with self.subTest(changes=changes), self.assertRaises((ValueError, TypeError)):
                guard._project(json.dumps({**base, **changes}).encode(), "1h")

    def test_duplicate_keys_or_invalid_json_fail_closed(self):
        for raw in (b'{"status":"OK","status":"UNKNOWN"}',
                    b'{"status":NaN}', b'not-json', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, UnicodeError)):
                guard._project(raw, "1h")

    def test_real_command_is_fixed_and_inspect_is_no_network(self):
        argv = guard._fixed_argv("24h")
        self.assertEqual(argv[0], sys.executable)
        self.assertEqual(argv[-3:], ["--read-local", "--window", "24h"])
        self.assertEqual(Path(argv[2]).name, "v06_history_source.py")
        code = Path(guard.__file__).read_text(encoding="utf-8")
        self.assertNotIn("serve_forever", code)
        self.assertNotIn("ThreadingHTTPServer", code)
        self.assertEqual(guard.MAX_STDOUT_BYTES, 65536)

if __name__ == "__main__":
    unittest.main()
