"""Fixture-only V0.3 DNS Guard telemetry tests, no network/ASUS writes."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parent.parent / "tools" / "v03_dns_guard_probe.py"
SPEC = importlib.util.spec_from_file_location("hcc_v03_dns_guard", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
NOW = dt.datetime(2026, 10, 26, 10, 0, tzinfo=dt.timezone.utc)
EPOCH = NOW.timestamp()


def metric_response(name, value, time=EPOCH, labels=None, count=1):
    metric = {"__name__": name}
    if labels:
        metric.update(labels)
    row = {"metric": metric, "value": [time, str(value)]}
    return json.dumps({
        "status": "success",
        "data": {"resultType": "vector", "result": [row] * count},
    }).encode()


def values(**overrides):
    result = {
        "collection": EPOCH - 20, "valid": 1, "local": 1,
        "bootstrap": 0, "breakglass": 0, "watchdog": 1,
    }
    result.update(overrides)
    return result


class PureProjection(unittest.TestCase):
    def test_local_fresh_means_reported_mode_not_dns_query_health(self):
        got = MODULE.snapshot(values(), NOW)
        self.assertEqual((got["status"], got["reason_code"], got["dns_mode"]),
                         ("OK", "LOCAL_MODE_REPORTED", "LOCAL"))
        self.assertEqual(got["collection_age_seconds"], 20)
        self.assertNotIn("router_ip", got)
        self.assertNotIn("query_path_healthy", got)

    def test_bootstrap_valid_is_degraded(self):
        got = MODULE.snapshot(values(local=0, bootstrap=1), NOW)
        self.assertEqual((got["status"], got["reason_code"], got["dns_mode"]),
                         ("DEGRADED", "BOOTSTRAP_MODE", "BOOTSTRAP"))

    def test_breakglass_precedes_watchdog_and_bootstrap(self):
        got = MODULE.snapshot(values(local=0, bootstrap=1, breakglass=1, watchdog=0), NOW)
        self.assertEqual((got["status"], got["reason_code"]), ("DEGRADED", "BREAKGLASS_ACTIVE"))

    def test_watchdog_absent_is_degraded(self):
        got = MODULE.snapshot(values(watchdog=0), NOW)
        self.assertEqual(got["reason_code"], "WATCHDOG_NOT_PRESENT")

    def test_old_collection_never_green(self):
        got = MODULE.snapshot(values(collection=EPOCH - 181), NOW)
        self.assertEqual((got["status"], got["reason_code"]), ("STALE", "COLLECTION_TOO_OLD"))
        self.assertIsNone(got["breakglass_active"])

    def test_missing_duplicate_or_contradictory_mode_never_green(self):
        for data in (
            {}, {"valid": 1}, values(valid=0), values(local=0, bootstrap=0),
            values(local=1, bootstrap=1), values(breakglass=2),
            values(watchdog=float("nan")), values(collection=EPOCH + 100),
            values(collection=0), values(collection=EPOCH - 1, valid=True),
            values(collection=EPOCH - 0.5),
        ):
            with self.subTest(data=data):
                self.assertEqual(MODULE.snapshot(data, NOW)["status"], "UNKNOWN")

    def test_collection_freshness_boundary(self):
        self.assertEqual(MODULE.snapshot(values(collection=EPOCH - 180), NOW)["status"], "OK")
        self.assertEqual(MODULE.snapshot(values(collection=EPOCH - 181), NOW)["status"], "STALE")
        self.assertEqual(MODULE.snapshot(values(collection=EPOCH + 5), NOW)["status"], "OK")
        self.assertEqual(MODULE.snapshot(values(collection=EPOCH + 6), NOW)["status"], "UNKNOWN")

    def test_unaware_clock_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.snapshot(values(), dt.datetime(2026, 10, 26))


class Parser(unittest.TestCase):
    def test_unique_exactly_named_unlabelled_series(self):
        for _, metric in MODULE.METRICS:
            self.assertEqual(MODULE.parse_metric(metric_response(metric, 1), metric, EPOCH), 1)

    def test_fail_closed_on_label_collision_and_duplicate_series(self):
        name = MODULE.METRICS[0][1]
        bad = [
            metric_response(name, 1, labels={"instance": "router.private"}),
            metric_response(name, 1, count=2),
            metric_response(name, 1, count=0),
            metric_response(MODULE.METRICS[1][1], 1),
            metric_response(name, 1, time=EPOCH - 31),
            metric_response(name, 1, time=EPOCH + 31),
            metric_response(name, "NaN"), metric_response(name, "-1"),
            metric_response(name, "1e3"), b"{}", b"[]", b"null", b"{",
            json.dumps({"status": "error", "data": {}}).encode(),
            b"x" * (MODULE.MAX_REPLY_BYTES + 1),
        ]
        for item in bad:
            with self.subTest(item=item[:45]):
                with self.assertRaises((ValueError, TypeError)):
                    MODULE.parse_metric(item, name, EPOCH)

    def test_bad_time_fields(self):
        name = MODULE.METRICS[0][1]
        for time in (True, None, "123", float("nan"), float("inf")):
            with self.subTest(time=time):
                with self.assertRaises((ValueError, TypeError)):
                    MODULE.parse_metric(metric_response(name, 1, time=time), name, EPOCH)


class BoundReader(unittest.TestCase):
    def test_metric_allowlist_has_expected_exporter_names(self):
        self.assertEqual(len(MODULE.METRICS), 6)
        self.assertEqual(set(MODULE.ALLOWLIST),
                         {name for _, name in MODULE.METRICS})
        for _, name in MODULE.METRICS:
            self.assertTrue(name.startswith("asus_edge_dns_guard_"))
        with self.assertRaises(ValueError):
            MODULE.fetch_metric('up{instance="127.0.0.1:8428"}')

    def test_exactly_six_queries_and_no_router_contact(self):
        readings = values()
        by_name = {name: readings[key] for key, name in MODULE.METRICS}
        requested = []
        def fetch(name):
            requested.append(name)
            return metric_response(name, by_name[name])
        got = MODULE.collect(fetch=fetch, clock=lambda: NOW)
        self.assertEqual(requested, [name for _, name in MODULE.METRICS])
        self.assertEqual(got["status"], "OK")
        self.assertEqual(got["mode"], "manual-local-vm-readonly")
        self.assertNotIn("192.168.", json.dumps(got))

    def test_fail_closed_and_sanitize_failed_read(self):
        def bad(_):
            raise OSError("private/path/router-credential")
        got = MODULE.collect(fetch=bad, clock=lambda: NOW)
        self.assertEqual(got["status"], "UNKNOWN")
        self.assertNotIn("private", json.dumps(got))
        self.assertIsNone(got["collection_age_seconds"])

    def test_partial_metrics_are_unknown_not_previous_good(self):
        calls = []
        def partial(name):
            calls.append(name)
            if len(calls) == 4:
                return metric_response(name, 1, count=0)
            return metric_response(name, 1)
        got = MODULE.collect(fetch=partial, clock=lambda: NOW)
        self.assertEqual(got["status"], "UNKNOWN")
        self.assertEqual(len(calls), 4)

    def test_default_mode_does_not_contact_vm(self):
        with patch.object(MODULE, "fetch_metric", side_effect=AssertionError("unexpected I/O")):
            self.assertEqual(len(MODULE.ALLOWLIST), 6)


if __name__ == "__main__":
    unittest.main()
