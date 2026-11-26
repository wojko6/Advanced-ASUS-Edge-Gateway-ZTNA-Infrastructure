"""V0.4 fixed VM query and source-projection tests — all mocked, no router/VM."""
import datetime as dt
import http.client
import json
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT / 'tools'))
import v04_router_dns_probe as probe

NOW=dt.datetime(2026,10,27,14,0,tzinfo=dt.timezone.utc)


def fixture(value, *, labels=None, time=None, results=1):
    if time is None:
        time=NOW.timestamp()
    entry={"metric":{} if labels is None else labels,"value":[time,str(value)]}
    data={"status":"success","data":{"resultType":"vector","result":[entry for _ in range(results)]}}
    return json.dumps(data).encode("ascii")


def reader(*,count=1,success=1,age=1.5,corrupt=None):
    values={"count":count,"success":success,"age":age}
    mapping={query:key for key,query in probe.QUERIES}
    def read(query):
        if query not in mapping:
            raise AssertionError("unexpected query")
        key=mapping[query]
        return corrupt[key] if corrupt and key in corrupt else fixture(values[key])
    return read


class FixedDnsAdapter(unittest.TestCase):
    def test_exactly_three_fixed_queries_and_no_router_contact(self):
        seen=[]
        read=reader()
        def tracked(q):
            seen.append(q)
            return read(q)
        value=probe.collect(tracked,lambda:NOW)
        self.assertEqual(value["status"],"OK")
        self.assertEqual(value["schema_version"],"0.4")
        self.assertEqual(value["mode"],"manual-local-vm-readonly")
        self.assertEqual(value["probe_success"],True)
        self.assertEqual(seen,[q for _,q in probe.QUERIES])
        self.assertEqual(probe.VM,"127.0.0.1")
        self.assertEqual(probe.PORT,8428)

    def test_single_negative_probe_only_degraded(self):
        value=probe.collect(reader(success=0),lambda:NOW)
        self.assertEqual(value["status"],"DEGRADED")
        self.assertEqual(value["reason_code"],"ONE_DNS_PROBE_FAILED")
        self.assertNotEqual(value["status"],"DOWN")

    def test_missing_or_multiple_series_fails_closed(self):
        for count in (0,2,10):
            with self.subTest(count=count):
                value=probe.collect(reader(count=count),lambda:NOW)
                self.assertEqual(value["status"],"UNKNOWN")
                self.assertIsNone(value["probe_success"])

    def test_future_and_old_evidence_never_green(self):
        for age,status in ((-1,"UNKNOWN"),(120.1,"STALE"),(800,"STALE")):
            with self.subTest(age=age):
                value=probe.collect(reader(age=age),lambda:NOW)
                self.assertEqual(value["status"],status)
                self.assertIsNone(value["probe_success"])

    def test_bad_success_flags_fail_closed(self):
        for flag in (-1,0.5,2):
            with self.subTest(flag=flag):
                self.assertEqual(probe.collect(reader(success=flag),lambda:NOW)["status"],"UNKNOWN")

    def test_unexpected_labels_duplicates_or_mismatched_evaluation(self):
        bad=(
            fixture(1,labels={"instance":"private"}),
            fixture(1,time=NOW.timestamp()-100),
            fixture(1,results=2),
            b'{"status":"success","data":{"resultType":"vector","result":[]}}',
            b"{}",
        )
        for raw in bad:
            with self.subTest(raw=raw[:25]):
                value=probe.collect(reader(corrupt={"success":raw}),lambda:NOW)
                self.assertEqual(value["status"],"UNKNOWN")

    def test_errors_produce_privacy_safe_unknown(self):
        for error in (OSError("private host"),ValueError("private instance"),TimeoutError("no metric")):
            with self.subTest(error=type(error).__name__):
                def failing(_):
                    raise error
                value=probe.collect(failing,lambda:NOW)
                self.assertEqual(value["status"],"UNKNOWN")
                self.assertNotIn("private",str(value))
                self.assertIsNone(value["sample_age_seconds"])

    def test_only_fixed_selectors_allowed(self):
        with self.assertRaises(ValueError):
            probe.get_fixed('probe_success{job="some-other-job"}')
        with self.assertRaises(ValueError):
            probe.get_fixed('up')
        self.assertEqual(len(probe.ALLOWED),3)

    def test_missing_nonfinite_or_extra_aggregate_fails_closed(self):
        bad=(fixture("NaN"),fixture("Inf"),fixture(1,labels={"job":"private"}))
        for raw in bad:
            self.assertEqual(probe.collect(reader(corrupt={"count":raw}),lambda:NOW)["status"],"UNKNOWN")

    def test_clock_requires_timezone(self):
        with self.assertRaises(ValueError):
            probe.collect(reader(),lambda:dt.datetime(2026,10,27,14,0))

    def test_no_direct_router_or_dynamic_url_in_source(self):
        source=Path(probe.__file__).read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "ssh ", "192.168.", "getenv(", "http_proxy"):
            self.assertNotIn(forbidden,source)
        self.assertNotIn("router",str(probe.collect(reader(),lambda:NOW)["source"]).lower())


if __name__=="__main__":
    unittest.main()
