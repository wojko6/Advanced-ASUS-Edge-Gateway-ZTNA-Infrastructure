"""V0.5 manual-only fixed DNS Guard archive API, offline fixtures and defenses."""
from __future__ import annotations

import http.client
import json
import sys
from http.server import HTTPServer
from pathlib import Path
from threading import Event, Thread
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import dns_guard_history_join_v01 as join
import v05_history_archive as archive
import v05_local_server as v05

FIRST = 1793112063000
STEP = 65000


def raw_sources():
    states = (0, 1, 1, 0, 0)
    data = {metric: {"metric": {"__name__": metric}, "timestamps": [], "values": []}
            for metric in join.METRICS}
    transitions = 0
    changed_at = 0
    fallback_since = 0
    previous = states[0]
    for i, state in enumerate(states):
        ms = FIRST + STEP * i
        at = ms // 1000
        if i and state != previous:
            changed_at = at
            if state:
                transitions += 1
                fallback_since = at
            else:
                fallback_since = 0
        row = {
            "mode_local": 1 - state,
            "mode_bootstrap": state,
            "state_valid": 1,
            "last_transition_timestamp_seconds": changed_at,
            "fallback_since_timestamp_seconds": fallback_since,
            "fallback_transitions_runtime_total": transitions,
            "collection_timestamp_seconds": at,
        }
        for metric in join.METRICS:
            suffix = metric.removeprefix(join.PREFIX)
            data[metric]["timestamps"].append(ms)
            data[metric]["values"].append(row[suffix])
        previous = state
    return {metric: (json.dumps(value) + "\n").encode() for metric, value in data.items()}


def valid_report():
    return join.reconcile(raw_sources())


class Projection(unittest.TestCase):
    def test_successful_archived_source_only(self):
        data = archive.project(valid_report())
        self.assertEqual(data["status"], "ARCHIVE_VERIFIED")
        self.assertEqual(data["schema_version"], "0.5")
        self.assertEqual(data["event_count"], 2)
        self.assertEqual(data["sample_count"], 5)
        self.assertEqual([e["type"] for e in data["events"]],
                         ["LOCAL_TO_BOOTSTRAP", "BOOTSTRAP_TO_LOCAL"])
        self.assertEqual(data["events"][0]["confidence"], "BOUNDED_OBSERVATION")
        self.assertTrue(data["events"][0]["window_start_local"].endswith("+01:00"))
        self.assertLessEqual(data["events"][0]["gap_seconds"], 180)
        self.assertEqual(data["mode"], "manual-fixed-archive-readonly")
        self.assertNotIn("dns_mode", str(data))

    def test_unknown_on_no_verifiable_source(self):
        with patch.object(archive.join, "read_local", side_effect=OSError):
            data = archive.collect()
        self.assertEqual(data["status"], "UNKNOWN")
        self.assertEqual(data["events"], [])
        self.assertIsNone(data["sample_count"])

    def test_http_protocol_errors_fail_closed_to_unknown(self):
        # Invalid/truncated localhost HTTP responses must not terminate the
        # manual archive handler or accidentally retain an earlier good view.
        for fault in (http.client.BadStatusLine("malformed status"),
                      http.client.IncompleteRead(b"partial", 10),
                      http.client.ResponseNotReady("response not ready")):
            with self.subTest(fault=type(fault).__name__):
                with patch.object(archive.join, "read_local", side_effect=fault):
                    result = archive.collect()
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertEqual(result["reason_code"], "ARCHIVE_EVIDENCE_NOT_VERIFIED")
                self.assertEqual(result["events"], [])

    def test_unknown_for_contradictory_and_missing_evidence(self):
        for changes in (
            {"corroborated_sampled_transitions": False},
            {"model_unknown_or_gap_count": 1},
            {"metric_count": 6},
            {"sample_count": 201},
            {"model_observed_change_count": 1},
            {"sampled_mode_change_count": 3},
            {"source": "PRIVATE"},
            {"first_utc": "2026-10-28T00:00:00Z"},
            {"transition_windows": []},
        ):
            report = valid_report()
            report.update(changes)
            with self.subTest(changes=changes):
                self.assertEqual(archive.project(report)["status"], "UNKNOWN")

    def test_rejected_if_evidence_is_incorrect_or_tampered(self):
        for field, value in (
            ("confidence", "ROOT_CAUSE_CONFIRMED"),
            ("event_type", "DNS_GUARD_LOCAL_RESTORED"),
            ("status", "INFERRED"),
            ("reported_transition_at", "2026-10-27T14:40:00Z"),
            ("window_start", "2026-10-27T14:40:00Z"),
        ):
            report = valid_report()
            report["model_events"][0][field] = value
            with self.subTest(field=field):
                self.assertEqual(archive.project(report)["status"], "UNKNOWN")

    def test_privacy_filtered_even_for_tampered_report(self):
        report = valid_report()
        report["sensitive_client"] = "DO_NOT_ECHO_THIS"
        report["model_events"][0]["raw_ip"] = "PRIVATE_ROUTER_ADDRESS"
        report["transition_windows"][0]["raw_qname"] = "PRIVATE_QUERY"
        data = archive.project(report)
        self.assertNotIn("DO_NOT_ECHO_THIS", str(data))
        self.assertNotIn("PRIVATE_ROUTER_ADDRESS", str(data))
        self.assertNotIn("PRIVATE_QUERY", str(data))

    def test_reject_nonfinite_reported_gap(self):
        report = valid_report()
        report["transition_windows"][0]["gap_seconds"] = float("nan")
        # Nonfinite input must never be silently normalized to a verified archive.
        self.assertEqual(archive.project(report)["status"], "UNKNOWN")


class ArchiveHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), v05.RequestHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def get(self, path="/api/dns-guard-history-archive", method="GET", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            h = {"Host": "127.0.0.1:8788"}
            h.update(headers or {})
            conn.request(method, path, headers=h)
            result = conn.getresponse()
            return result.status, result.read(), dict(result.getheaders())
        finally:
            conn.close()

    def test_manual_archive_api_sanitized_json_and_headers(self):
        payload = archive.project(valid_report())
        with patch.object(v05.archive, "collect", return_value=payload) as collect:
            status, raw, headers = self.get()
        collect.assert_called_once_with()
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        value = json.loads(raw)
        self.assertEqual(value["event_count"], 2)
        self.assertNotIn("instance", str(value))
        self.assertNotIn("query_log", str(value))

    def test_unknown_remains_neutral_and_no_last_good(self):
        with patch.object(v05.archive, "collect", return_value=archive.unknown()):
            status, raw, _ = self.get()
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["status"], "UNKNOWN")

    def test_cross_site_host_and_origin_block_before_source(self):
        with patch.object(v05.archive, "collect",
                          side_effect=AssertionError("source must not be contacted")):
            for headers in (
                {"Host": "evil.invalid"},
                {"Host": "control.home.arpa"},
                {"Sec-Fetch-Site": "cross-site"},
                {"Sec-Fetch-Site": "same-site"},
                {"Origin": "https://evil.invalid"},
                {"Origin": "https://control.home.arpa"},
            ):
                with self.subTest(headers=headers):
                    self.assertEqual(self.get(headers=headers)[0], 403)

    def test_api_is_get_only_exact_and_fixed(self):
        with patch.object(v05.archive, "collect",
                          side_effect=AssertionError("do not query")):
            for method in ("POST", "PATCH", "PUT", "DELETE"):
                self.assertEqual(self.get(method=method)[0], 405)
            for path in ("/api/dns-guard-history-archive?start=now",
                         "/api/dns-guard-history-archive/",
                         "/tools/dns_guard_history_join_v01.py",
                         "/index-v05.html", "/api/v1/export"):
                self.assertEqual(self.get(path=path)[0], 404)

    def test_three_live_v04_panels_remain_present_and_archive_separate(self):
        status, body, headers = self.get(path="/")
        self.assertEqual(status, 200)
        html = body.decode()
        for token in ('V0.5', 'id="live-vm"', 'id="live-dns-guard"',
                      'id="live-router-dns"', 'id="dns-history-archive"',
                      'data-demo-gate="opt-in"', 'id="demo-toggle"',
                      'dns-history-archive.mjs', 'ARCHIWUM'):
            with self.subTest(token=token):
                self.assertIn(token, html)
        self.assertIn("connect-src 'self'", html)
        self.assertIn("no-store", headers["Cache-Control"])
        for asset in ("router-dns-model.mjs", "router-dns-live.mjs",
                      "dns-guard-live.mjs", "dns-history-archive.mjs",
                      "dns-history-archive-model.mjs", "dns-history-archive.css"):
            with self.subTest(asset=asset):
                self.assertEqual(self.get(path="/" + asset)[0], 200)

    def test_large_payload_does_not_leave_server(self):
        with patch.object(v05.archive, "collect",
                          return_value={"private": "X" * (v05.MAX_HISTORY_OUTPUT + 20)}):
            self.assertEqual(self.get()[0], 503)

    def test_existing_v04_router_dns_api_remains_compatible(self):
        with patch.object(v05.v04.dnsprobe, "collect",
                          return_value={"schema_version": "0.4", "status": "UNKNOWN"}):
            status, body, _ = self.get(path="/api/router-dns")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["schema_version"], "0.4")


class ConcurrentManualV05(unittest.TestCase):
    """Synthetic loopback-only concurrency checks: never access real VM/router."""

    @classmethod
    def setUpClass(cls):
        cls.server = v05.BoundedLocalHTTPServer(("127.0.0.1", 0),
                                                v05.RequestHandler)
        cls.worker = Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=2)

    def get(self, path="/api/dns-guard-history-archive"):
        conn = http.client.HTTPConnection("127.0.0.1",
                                          self.server.server_port, timeout=3)
        try:
            conn.request("GET", path, headers={"Host": "127.0.0.1:8788"})
            response = conn.getresponse()
            response.read()
            return response.status
        finally:
            conn.close()

    def test_static_requests_continue_while_history_is_slow(self):
        entered, release = Event(), Event()

        def synthetic_slow_archive():
            entered.set()
            if not release.wait(timeout=4):
                raise AssertionError("synthetic archive release timed out")
            return archive.unknown()

        try:
            with patch.object(v05.archive, "collect", side_effect=synthetic_slow_archive) as collect:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    slow = pool.submit(self.get)
                    self.assertTrue(entered.wait(2), "archive handler was not entered")
                    # This must complete WHILE the archive is still blocked.
                    fast = pool.submit(self.get, "/")
                    self.assertEqual(fast.result(timeout=1.5), 200)
                    self.assertFalse(slow.done())
                    release.set()
                    self.assertEqual(slow.result(timeout=2), 200)
                collect.assert_called_once_with()
        finally:
            release.set()

    def test_parallel_duplicate_archive_is_denied_without_extra_vm_read(self):
        entered, release = Event(), Event()

        def synthetic_slow_archive():
            entered.set()
            if not release.wait(timeout=4):
                raise AssertionError("synthetic archive release timed out")
            return archive.unknown()

        try:
            with patch.object(v05.archive, "collect", side_effect=synthetic_slow_archive) as collect:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    first = pool.submit(self.get)
                    self.assertTrue(entered.wait(2), "archive handler was not entered")
                    self.assertEqual(self.get(), 503)
                    release.set()
                    self.assertEqual(first.result(timeout=2), 200)
                collect.assert_called_once_with()
        finally:
            release.set()

    def test_http_worker_limit_rejects_excess_without_dispatch(self):
        # Saturate the semaphore synthetically: no real client flood.
        acquired = 0
        try:
            for _ in range(v05.MAX_CONCURRENT_HTTP_REQUESTS):
                self.assertTrue(self.server._slots.acquire(blocking=False))
                acquired += 1
            with patch.object(v05.archive, "collect",
                              side_effect=AssertionError("no VM calls allowed")):
                self.assertEqual(self.get(), 503)
        finally:
            for _ in range(acquired):
                self.server._slots.release()


if __name__ == "__main__":
    unittest.main()
