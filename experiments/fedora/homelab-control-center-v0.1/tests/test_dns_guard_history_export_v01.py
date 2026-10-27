"""#319: synthetic VM raw export parser and bounded localhost HTTP preflight."""
import importlib.util
import json
from pathlib import Path
import unittest

FILE = Path(__file__).resolve().parents[1] / "tools" / "dns_guard_history_export_v01.py"
SPEC = importlib.util.spec_from_file_location("dns_guard_history_export_v01", FILE)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

FIRST = 1793112063000
STEP = 65000


def synthetic(n=113):
    timestamps = [FIRST + i * STEP for i in range(n)]
    values = [1 if 74 <= i <= 76 else 0 for i in range(n)]
    return {"metric": {"__name__": m.METRIC},
            "timestamps": timestamps, "values": values}


def pack(data):
    return (json.dumps(data) + "\n").encode("utf-8")


class ParsingAndEvidence(unittest.TestCase):
    def test_exact_window_and_source_contract(self):
        self.assertEqual(m.MIN_MS, 1793112000000)
        self.assertEqual(m.MAX_MS, 1793119380000)
        self.assertEqual(m.METRIC, "asus_edge_dns_guard_mode_bootstrap")
        self.assertIn("match%5B%5D=asus_edge_dns_guard_mode_bootstrap", m.fixed_uri())
        self.assertIn("max_rows_per_line=200", m.fixed_uri())

    def test_full_bounded_historical_fixture(self):
        samples = m.parse_export(pack(synthetic()))
        output = m.summarize(samples)
        self.assertEqual(output["series_count"], 1)
        self.assertEqual(output["samples_count"], 113)
        self.assertEqual(output["observed_change_count"], 2)
        self.assertEqual(output["initial_sampled_mode"], "LOCAL")
        self.assertEqual(output["final_sampled_mode"], "LOCAL")
        start, recovered = output["events"]
        self.assertEqual(start["from"], "LOCAL")
        self.assertEqual(start["to"], "BOOTSTRAP")
        self.assertEqual(recovered["from"], "BOOTSTRAP")
        self.assertEqual(recovered["to"], "LOCAL")
        self.assertEqual(start["gap_seconds"], 65)
        self.assertEqual(start["confidence"], "BOUNDED_OBSERVATION")
        self.assertIn("Europe", "Europe/Warsaw")
        self.assertIn("+01:00", start["local_window_start"])
        self.assertNotIn("duration_seconds", str(output))
        self.assertEqual(output["deployment_gate"], "HOLD")

    def test_stable_series_has_no_events(self):
        data=synthetic(10)
        result=m.summarize(m.parse_export(pack(data)))
        self.assertEqual(result["events"],[])
        self.assertEqual(result["observed_change_count"],0)

    def test_gap_marks_unknown_not_definite_transition(self):
        samples=[(FIRST,0),(FIRST+181000,1)]
        result=m.summarize(samples)
        self.assertEqual(result["observed_change_count"],0)
        self.assertEqual(result["events"][0]["event_type"],"DNS_GUARD_OBSERVATION_GAP")
        self.assertEqual(result["events"][0]["confidence"],"UNKNOWN")

    def test_no_fabricated_start_event_on_initial_bootstrap(self):
        data=synthetic(5)
        data["values"]=[1,1,1,1,1]
        result=m.summarize(m.parse_export(pack(data)))
        self.assertEqual(result["initial_sampled_mode"],"BOOTSTRAP")
        self.assertEqual(result["events"],[])

    def test_wrong_series_cardinality(self):
        line=pack(synthetic(1))
        for raw in (b"",line+line,b"\n",b"[]\n"):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                m.parse_export(raw)

    def test_disallow_labels_and_unknown_fields(self):
        for item in (
            {**synthetic(1),"other":"private"},
            {**synthetic(1),"metric":{"__name__":m.METRIC,"instance":"PRIVATE"}},
            {**synthetic(1),"metric":{"__name__":"other"}},
        ):
            with self.subTest(item=str(item)[:28]), self.assertRaises(ValueError):
                m.parse_export(pack(item))

    def test_negative_nan_bool_and_nonbinary_values(self):
        for value in (True,-1,2,0.5,None,"1",float("nan"),float("inf")):
            item=synthetic(1)
            item["values"]=[value]
            with self.subTest(value=str(value)), self.assertRaises(ValueError):
                m.parse_export(pack(item))

    def test_invalid_duplicate_and_unsorted_times(self):
        good=synthetic(2)
        cases=(
            [True, FIRST+STEP],
            [FIRST,FIRST],
            [FIRST+STEP,FIRST],
            [FIRST-1000,FIRST],
            [FIRST, m.MAX_MS+1000],
            ["1793112063000",FIRST+STEP],
        )
        for timestamps in cases:
            item=dict(good,timestamps=timestamps)
            with self.subTest(times=timestamps), self.assertRaises(ValueError):
                m.parse_export(pack(item))

    def test_sample_count_and_length_limits(self):
        for item in (synthetic(0),synthetic(201), dict(synthetic(2),values=[0])):
            with self.subTest(length=len(item["timestamps"])), self.assertRaises(ValueError):
                m.parse_export(pack(item))
        with self.assertRaises(ValueError):
            m.parse_export(b"0"*(m.MAX_BYTES+1))

    def test_bad_types_and_corrupt_json(self):
        for raw in (b"not-json",b"\xff",b"null\n",b'{"metric":NaN}\n'):
            with self.subTest(raw=raw[:10]), self.assertRaises(ValueError):
                m.parse_export(raw)

    def test_summary_detects_bad_order(self):
        for invalid in ([],[(FIRST+STEP,1),(FIRST,0)],[(FIRST,0),(FIRST,1)]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                m.summarize(invalid)

    def test_local_http_only_and_capped_read(self):
        data=pack(synthetic(2))
        calls=[]
        class FakeHTTPResponse:
            status=200
            def read(self,n):
                calls.append(("read",n))
                return data
        class FakeClient:
            def __init__(self,host,port,timeout):
                calls.append(("connect",host,port,timeout))
            def request(self,method,url):
                calls.append(("request",method,url))
            def getresponse(self):
                return FakeHTTPResponse()
            def close(self):
                calls.append(("close",))
        result=m.read_local(connector=FakeClient)
        self.assertEqual(result["samples_count"],2)
        self.assertEqual(calls[0],("connect","127.0.0.1",8428,5))
        self.assertEqual(calls[1],("request","GET",m.fixed_uri()))
        self.assertEqual(calls[2],("read",m.MAX_BYTES+1))
        self.assertEqual(calls[-1],("close",))

    def test_non_200_and_large_responses_fail_closed(self):
        for code,raw in ((500,pack(synthetic(1))),(200,b"x"*(m.MAX_BYTES+1))):
            class FakeResponse:
                status=code
                def read(self,n):
                    return raw
            class FakeClient:
                def __init__(self,*args,**kwargs): pass
                def request(self,*args): pass
                def getresponse(self): return FakeResponse()
                def close(self): pass
            with self.subTest(code=code),self.assertRaises(ValueError):
                m.read_local(connector=FakeClient)

    def test_no_auto_run_or_notification_apis(self):
        source=FILE.read_text("utf-8")
        self.assertIn("required=True",source)
        self.assertNotIn("import subprocess",source)
        self.assertNotIn("import smtplib",source)
        self.assertNotIn("import requests",source)
        self.assertNotIn("import paramiko",source)
        self.assertNotIn("SSHClient",source)
        self.assertEqual(m.DEPLOYMENT_GATE,"HOLD")


if __name__ == "__main__":
    unittest.main()
