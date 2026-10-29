"""HCC V0.6-B2 manual source adapter: deterministic mock HTTP, no real network."""
from __future__ import annotations

from datetime import datetime, timezone
import http.client
import json
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import v06_history_source as src
import v06_coverage_model as coverage

END = 1793260800000
FIXED_CLOCK = datetime.fromtimestamp(END/1000, timezone.utc)


def fixture(count=61, *, span=60000, end=END):
    start = end - (count-1)*span
    stamps = [start+i*span for i in range(count)]
    data = {}
    for name in coverage.SUFFIXES:
        if name == "mode_local":
            values = [1]*count
        elif name == "state_valid":
            values = [1]*count
        elif name == "collection_timestamp_seconds":
            values = [x//1000 for x in stamps]
        else:
            values = [0]*count
        data[src.METRIC_PREFIX+name] = (stamps, values)
    return data


def encode(metric, samples, *, chunk=200, extra_labels=None):
    stamps, values = samples
    labels = {"__name__": metric}
    if extra_labels:
        labels.update(extra_labels)
    lines = []
    for i in range(0, len(stamps), chunk):
        lines.append(json.dumps({
            "metric": labels, "timestamps": stamps[i:i+chunk],
            "values": values[i:i+chunk]
        }, separators=(",", ":")))
    return ("\n".join(lines)+"\n").encode()


class FakeHTTP:
    def __init__(self, response, status=200, fault=None):
        self.raw = response
        self.status = status
        self.fault = fault
        self.headers = []
        self.calls = []
        self.closed = 0
        self.connections = []

    def connect(self, host, port, timeout):
        if host != "127.0.0.1" or port != 8428 or timeout != 5:
            raise AssertionError("unexpected network target")
        self.connections.append((host, port, timeout))
        parent = self
        class Conn:
            def request(self, method, path, headers):
                parent.calls.append((method, path, headers))
                if method != "GET" or not path.startswith("/api/v1/export?"):
                    raise AssertionError("wrong request")
                params = parse_qs(urlsplit(path).query)
                if (set(params) != {"match[]", "start", "end", "max_rows_per_line"}
                        or params["max_rows_per_line"] != ["200"]):
                    raise AssertionError("unexpected query parameters")
                self.metric = params["match[]"][0]
                if self.metric not in src.METRICS:
                    raise AssertionError("unapproved metric")
            def getresponse(self):
                if parent.fault:
                    raise parent.fault
                class Response:
                    status = parent.status
                    def read(self, size):
                        return parent.raw[self_metric][:size]
                self_metric = self.metric
                return Response()
            def close(self):
                parent.closed += 1
        return Conn()


class SourceTests(unittest.TestCase):
    def test_fixed_uri_exact_source_and_bad_selector_denied(self):
        path = src.fixed_path(src.METRICS[0], "24h", END)
        params = parse_qs(urlsplit(path).query)
        self.assertEqual(params["match[]"], [src.METRICS[0]])
        self.assertEqual(params["max_rows_per_line"], ["200"])
        self.assertEqual(set(params), {"match[]", "start", "end", "max_rows_per_line"})
        for metric, window in (("probe_success", "24h"),
                               (src.METRICS[0], "30d"),
                               (src.METRICS[0], [])):
            with self.subTest(metric=metric, window=window):
                with self.assertRaises(ValueError):
                    src.fixed_path(metric, window, END)

    def test_1h_realistic_synthetic_local_manual_read(self):
        raw = {m: encode(m, samples) for m, samples in fixture().items()}
        fake = FakeHTTP(raw)
        result = src.read_local("1h", clock=lambda: FIXED_CLOCK,
                                connector=fake.connect)
        self.assertEqual(result["status"], "COVERAGE_OBSERVED")
        self.assertEqual(result["sample_count"], 61)
        self.assertEqual(result["segments"][0]["sample_count"], 61)
        self.assertEqual(result["source_adapter"], src.SCHEMA)
        self.assertEqual(result["gaps"], [])
        self.assertEqual(len(fake.calls), 7)
        self.assertEqual(fake.closed, 7)
        self.assertEqual(len(fake.connections), 7)
        self.assertNotIn("values", str(result))
        self.assertNotIn("127.0.0.1", str(result))

    def test_24h_chunked_history_with_inactive_hours(self):
        times = [END-86400000+60000, END-86400000+120000]
        times.extend([END-20000000+i*60000 for i in range(640)])
        raw_data = {}
        for name in coverage.SUFFIXES:
            metric = src.METRIC_PREFIX+name
            if name in ("mode_local", "state_valid"):
                vals = [1]*len(times)
            elif name == "collection_timestamp_seconds":
                vals = [x//1000 for x in times]
            else:
                vals = [0]*len(times)
            raw_data[metric] = (times, vals)
        raw = {m: encode(m, sample) for m, sample in raw_data.items()}
        fake = FakeHTTP(raw)
        result = src.read_local("24h", clock=lambda: FIXED_CLOCK,
                                connector=fake.connect)
        self.assertEqual(result["sample_count"], 642)
        self.assertEqual(result["status"], "COVERAGE_OBSERVED_WITH_UNCERTAINTY")
        self.assertTrue(any(g["position"] == "INTERNAL" for g in result["gaps"]))
        self.assertNotIn("DNS_OUTAGE", str(result))

    def test_bounded_7d_4963_samples_with_25_chunks(self):
        raw = {m: encode(m, pair) for m, pair in
               fixture(count=4963, end=END).items()}
        self.assertEqual(len(raw[src.METRICS[0]].splitlines()), 25)
        fake = FakeHTTP(raw)
        result = src.read_local("7d", clock=lambda: FIXED_CLOCK,
                                connector=fake.connect)
        self.assertEqual(result["sample_count"], 4963)
        self.assertEqual(result["max_cross_series_skew_ms"], 0)
        self.assertEqual(result["status"], "COVERAGE_OBSERVED_WITH_UNCERTAINTY")
        self.assertEqual(len(fake.calls), 7)
        self.assertTrue(any(g["position"] == "LEADING" for g in result["gaps"]))

    def test_one_series_misaligned_fails_closed(self):
        rows = fixture()
        ts, vs = rows[src.METRICS[0]]
        ts[1] += 5001
        fake = FakeHTTP({m: encode(m, pair) for m, pair in rows.items()})
        result = src.read_local("1h", clock=lambda: FIXED_CLOCK,
                                connector=fake.connect)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["segments"], [])
        self.assertNotIn("localhost", str(result))

    def test_http_failure_does_not_leak_or_contact_remaining_series(self):
        raw = {m: encode(m, samples) for m, samples in fixture().items()}
        for fault in (http.client.BadStatusLine("PRIVATE_HOST"),
                      http.client.IncompleteRead(b"PRIVATE", 10)):
            with self.subTest(fault=type(fault).__name__):
                fake = FakeHTTP(raw, fault=fault)
                result = src.read_local("1h", clock=lambda: FIXED_CLOCK,
                                        connector=fake.connect)
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertEqual(fake.closed, 1)
                self.assertEqual(len(fake.calls), 1)
                self.assertNotIn("PRIVATE", str(result))
        bad = FakeHTTP(raw, status=503)
        self.assertEqual(src.read_local("1h", clock=lambda: FIXED_CLOCK,
                                        connector=bad.connect)["status"], "UNKNOWN")

    def test_wrong_labels_duplicate_json_and_invalid_chunk_fail(self):
        base = fixture()
        metric = src.METRICS[0]
        start = END-coverage.WINDOWS_MS["1h"]
        wrong = encode(metric, base[metric], extra_labels={"instance": "SECRET"})
        with self.assertRaises(ValueError):
            src.parse_chunks(metric, wrong, start, END)
        duplicate_key = b'{"metric":{"__name__":"'+metric.encode()+b'"},"metric":{"__name__":"'+metric.encode()+b'"},"timestamps":[1793260800000],"values":[1]}\n'
        with self.assertRaises(ValueError):
            src.parse_chunks(metric, duplicate_key, start, END)
        old = (b'{"metric":{"__name__":"'+metric.encode()+b'"},"timestamps":[1793260800000],"values":[1]}\n')*65
        with self.assertRaises(ValueError):
            src.parse_chunks(metric, old, start, END)
        with self.assertRaises(ValueError):
            src.parse_chunks(metric, b"x"*(src.MAX_BYTES_PER_METRIC+1), start, END)

    def test_no_data_unknown_and_bad_clock_unknown(self):
        self.assertEqual(src.read_local("30d")["status"], "UNKNOWN")
        self.assertEqual(src.read_local("1h", clock=lambda: None)["status"], "UNKNOWN")
        no_data = FakeHTTP({m: b"" for m in src.METRICS})
        self.assertEqual(src.read_local("1h", clock=lambda: FIXED_CLOCK,
                                        connector=no_data.connect)["status"], "UNKNOWN")

    def test_parser_rejects_cross_chunk_out_of_order(self):
        metric = src.METRICS[0]
        start = END - coverage.WINDOWS_MS["1h"]
        row = fixture()[metric]
        stamps, vals = row
        a = encode(metric, (stamps[20:40], vals[20:40]))
        b = encode(metric, (stamps[:20], vals[:20]))
        with self.assertRaises(ValueError):
            src.parse_chunks(metric, a+b, start, END)

    def test_inspect_is_explicit_and_source_unchanged(self):
        self.assertEqual(src.HOST, "127.0.0.1")
        self.assertEqual(src.PORT, 8428)
        self.assertEqual(src.METRICS, tuple(
            src.METRIC_PREFIX+n for n in coverage.SUFFIXES))
        self.assertEqual(coverage.GAP_THRESHOLD_MS, 180000)
        self.assertEqual(src.MAX_TOTAL_SAMPLES, 12000)


if __name__ == "__main__":
    unittest.main()
