"""Issue #319: seven-stream offline source contract, negative fixtures."""
import importlib.util
import json
import sys
from pathlib import Path
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
SCRIPT = TOOLS / "dns_guard_history_join_v01.py"
SPEC = importlib.util.spec_from_file_location("dns_guard_history_join_v01", SCRIPT)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
FIRST = 1793112063000
STEP = 63000


def snapshot(n=9, mode=(0, 0, 0, 1, 1, 1, 0, 0, 0), *, skew=100):
    assert len(mode) == n
    counter, last_transition, fallback_since = 0, 0, 0
    transitions = []
    last_mode = mode[0]
    for i, val in enumerate(mode):
        ts = FIRST + i * STEP
        if i and val != last_mode:
            last_transition = ts // 1000
            if val:
                counter += 1
                fallback_since = last_transition
            else:
                fallback_since = 0
        transitions.append((ts, {
            "mode_local": 0 if val else 1,
            "mode_bootstrap": val,
            "state_valid": 1,
            "last_transition_timestamp_seconds": last_transition,
            "fallback_since_timestamp_seconds": fallback_since,
            "fallback_transitions_runtime_total": counter,
            "collection_timestamp_seconds": ts // 1000,
        }))
        last_mode = val
    data = {}
    for k, metric in enumerate(m.METRICS):
        suffix = metric.removeprefix(m.PREFIX)
        data[metric] = (json.dumps({
            "metric": {"__name__": metric},
            "timestamps": [ts + skew * k for ts, _ in transitions],
            "values": [item[suffix] for _, item in transitions],
        }) + "\n").encode()
    return data


def replace(raw, metric, **kwargs):
    data = dict(raw)
    item = json.loads(data[metric])
    item.update(kwargs)
    data[metric] = (json.dumps(item) + "\n").encode()
    return data


class SevenSeriesJoin(unittest.TestCase):
    def test_positive_transition_pair_with_full_source_support(self):
        result = m.reconcile(snapshot())
        self.assertEqual(result["sample_count"], 9)
        self.assertEqual(result["sampled_mode_change_count"], 2)
        self.assertEqual(result["model_observed_change_count"], 2)
        self.assertEqual(result["model_unknown_or_gap_count"], 0)
        self.assertTrue(result["corroborated_sampled_transitions"])
        self.assertEqual(result["transition_windows"][0]["type"], "LOCAL_TO_BOOTSTRAP")
        self.assertEqual(result["transition_windows"][1]["type"], "BOOTSTRAP_TO_LOCAL")
        self.assertIn("+01:00", result["transition_windows"][0]["previous_sample_local"])
        self.assertFalse(result["router_contact"])
        self.assertFalse(result["notification_sent"])
        self.assertFalse(result["production_changes"])
        self.assertEqual(result["deployment_gate"], "HOLD")

    def test_stable_local_does_not_fabricate_events(self):
        result = m.reconcile(snapshot(5, (0, 0, 0, 0, 0)))
        self.assertEqual(result["model_events"], [])
        self.assertTrue(result["corroborated_sampled_transitions"])

    def test_counter_restart_not_confirmed(self):
        data = snapshot()
        metric = m.PREFIX + "fallback_transitions_runtime_total"
        result = m.reconcile(replace(data, metric, values=[2, 2, 2, 3, 3, 3, 0, 0, 0]))
        self.assertFalse(result["corroborated_sampled_transitions"])
        self.assertGreater(result["model_unknown_or_gap_count"], 0)

    def test_missing_and_extra_series_are_rejected(self):
        data = snapshot()
        for invalid in ({}, {k:v for k,v in data.items() if k != m.METRICS[0]},
                        {**data,"unexpected":b"{}"}):
            with self.subTest(case=len(invalid)),self.assertRaises(ValueError):
                m.reconcile(invalid)

    def test_mismatched_counts_fail(self):
        data = snapshot()
        key = m.METRICS[0]
        item = json.loads(data[key])
        with self.assertRaisesRegex(ValueError, "SERIES_LENGTH_MISMATCH"):
            m.reconcile(replace(data, key, timestamps=item["timestamps"][:-1],
                                values=item["values"][:-1]))

    def test_cross_metric_timestamp_skew_over_5s_fails(self):
        with self.assertRaisesRegex(ValueError,"CROSS_SERIES_TIMESTAMP_MISALIGNMENT"):
            m.reconcile(snapshot(skew=900))

    def test_collection_to_import_clock_disagreement_fails(self):
        data = snapshot()
        key = m.PREFIX + "collection_timestamp_seconds"
        vals = json.loads(data[key])["values"]
        vals[5] -= 120
        with self.assertRaisesRegex(ValueError,"COLLECTION_TO_IMPORT_CLOCK_MISMATCH"):
            m.reconcile(replace(data, key, values=vals))

    def test_contradictory_mode_flags_do_not_claim_verified_history(self):
        data = snapshot()
        key = m.PREFIX + "mode_local"
        vals = json.loads(data[key])["values"]
        vals[3] = 1
        result = m.reconcile(replace(data, key, values=vals))
        self.assertFalse(result["corroborated_sampled_transitions"])
        self.assertGreater(result["model_unknown_or_gap_count"], 0)

    def test_counter_implies_unseen_change(self):
        data = snapshot(3, (0,0,0))
        key = m.PREFIX + "fallback_transitions_runtime_total"
        result = m.reconcile(replace(data, key, values=[0,1,1]))
        self.assertFalse(result["corroborated_sampled_transitions"])
        self.assertGreater(result["model_unknown_or_gap_count"], 0)

    def test_large_observation_gap_not_confirmed(self):
        data = snapshot(3, (0,1,1))
        for key in m.METRICS:
            payload = json.loads(data[key])
            payload["timestamps"][1] += 185000
            payload["timestamps"][2] += 185000
            if key.endswith("collection_timestamp_seconds"):
                payload["values"][1] += 185
                payload["values"][2] += 185
            data[key] = (json.dumps(payload) + "\n").encode()
        result = m.reconcile(data)
        self.assertFalse(result["corroborated_sampled_transitions"])
        self.assertGreater(result["model_unknown_or_gap_count"], 0)

    def test_unexpected_labels_values_duplicate_keys_times(self):
        for case in ("private_label","nonbinary","duplicate_json","unsorted","empty_values"):
            data = snapshot()
            key = m.METRICS[1]
            payload = json.loads(data[key])
            if case == "private_label":
                payload["metric"]["instance"] = "PRIVATE_IDENTIFIER"
            elif case == "nonbinary":
                payload["values"][4] = 2
            elif case == "unsorted":
                payload["timestamps"][2] = payload["timestamps"][1] - 1
            elif case == "empty_values":
                payload["values"] = []
            elif case == "duplicate_json":
                data[key] = data[key].replace(
                    b'"timestamps": ',b'"extra": 1, "extra": 1, "timestamps": ')
                with self.subTest(case=case), self.assertRaises(ValueError):
                    m.reconcile(data)
                continue
            data[key] = (json.dumps(payload) + "\n").encode()
            with self.subTest(case=case),self.assertRaises(ValueError):
                m.reconcile(data)

    def test_nan_infinity_boolean_strings_and_negative_rejected(self):
        for value in (float("nan"),float("inf"),True,"1",-2):
            data = snapshot()
            key = m.METRICS[0]
            values = json.loads(data[key])["values"]
            values[2] = value
            with self.subTest(value=str(value)),self.assertRaises(ValueError):
                m.reconcile(replace(data,key,values=values))

    def test_overlong_and_multiline_export_rejected(self):
        data = snapshot()
        key = m.METRICS[0]
        for bad in (data[key]+data[key], b"x"*(m.MAX_BYTES_PER_SERIES+1)):
            with self.subTest(bytes=len(bad)),self.assertRaises(ValueError):
                m.parse_one(key,bad)

    def test_zero_and_overlimit_samples_rejected(self):
        for n in (0,201):
            key=m.METRICS[0]
            raw=(json.dumps({
                "metric":{"__name__":key},
                "timestamps":list(range(m.MIN_MS,m.MIN_MS+n)),
                "values":[0]*n
            })+"\n").encode()
            with self.subTest(n=n),self.assertRaises(ValueError):
                m.parse_one(key,raw)

    def test_fixed_uris_only(self):
        for metric in m.METRICS:
            url=m.fixed_uri(metric)
            self.assertIn("match%5B%5D="+metric,url)
            self.assertIn("2026-10-27T14%3A40%3A00Z",url)
        with self.assertRaises(ValueError):
            m.fixed_uri("arbitrary_query")

    def test_bounded_local_http_mock(self):
        data=snapshot(4,(0,1,1,0))
        calls=[]
        class FakeResponse:
            status=200
            def __init__(self,raw): self.raw=raw
            def read(self,n):
                calls.append(("read",n))
                return self.raw
        class FakeConn:
            def __init__(self,host,port,timeout):
                calls.append(("open",host,port,timeout))
            def request(self,method,uri):
                self.metric=next(key for key in m.METRICS if key in uri)
                calls.append(("request",method,uri))
            def getresponse(self): return FakeResponse(data[self.metric])
            def close(self): calls.append(("close",))
        result=m.read_local(connector=FakeConn)
        self.assertEqual(result["sample_count"],4)
        self.assertEqual(sum(x[0]=="request" for x in calls),7)
        self.assertEqual(sum(x[0]=="close" for x in calls),7)
        self.assertTrue(all(x[1:]==("127.0.0.1",8428,5) for x in calls if x[0]=="open"))
        self.assertTrue(all(x[1]==m.MAX_BYTES_PER_SERIES+1
                            for x in calls if x[0]=="read"))

    def test_manual_execution_only(self):
        source=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("required=True",source)
        for forbidden in ("import subprocess","import smtplib","import paramiko"):
            self.assertNotIn(forbidden,source)


if __name__ == "__main__":
    unittest.main()
