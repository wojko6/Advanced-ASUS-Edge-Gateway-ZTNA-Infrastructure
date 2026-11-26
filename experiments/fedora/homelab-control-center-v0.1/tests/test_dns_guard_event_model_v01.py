"""Issue #319: no-I/O, deterministic event replay for HCC DNS Guard history."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "tools" / "dns_guard_event_model_v01.py"
SPEC = importlib.util.spec_from_file_location("dns_guard_event_model_v01", SOURCE)
assert SPEC and SPEC.loader
model = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model)

BASE = 1793100000  # synthetic epoch, not operator incident evidence


def row(offset=0, *, boot=False, counter=0, transition=0, since=0, **change):
    v = {
        "collection_epoch": BASE + offset,
        "mode_local": 0 if boot else 1,
        "mode_bootstrap": 1 if boot else 0,
        "state_valid": 1,
        "last_transition_epoch": BASE + transition if transition else 0,
        "fallback_since_epoch": BASE + since if since else 0,
        "fallback_transitions_total": counter,
    }
    v.update(change)
    return v


def event_types(samples):
    return [x["event_type"] for x in model.timeline(samples)["events"]]


class EventHistory(unittest.TestCase):
    def test_local_bootstrap_local_has_two_events_and_bounded_duration(self):
        samples = [
            row(0), row(60, boot=True, counter=1, transition=60, since=60),
            row(120, boot=True, counter=1, transition=60, since=60),
            row(180, counter=1, transition=180),
        ]
        output = model.timeline(samples)
        self.assertEqual(output["mode"], "OFFLINE_FIXTURES_ONLY")
        self.assertEqual(output["event_count"], 2)
        start, end = output["events"]
        self.assertEqual([start["event_type"], end["event_type"]],
                         [model.BOOT, model.LOCAL])
        self.assertEqual(start["confidence"], "BOUNDED_OBSERVATION")
        self.assertEqual(start["reason_code"], "MODE_CHANGE_OBSERVED")
        self.assertEqual(end["duration_lower_seconds"], 60)
        self.assertEqual(end["duration_upper_seconds"], 180)
        self.assertEqual(start["window_start"], model._utc(BASE))
        self.assertEqual(start["window_end"], model._utc(BASE + 60))
        self.assertEqual(end["reported_transition_at"], model._utc(BASE + 180))
        self.assertNotEqual(start["dedupe_key"], end["dedupe_key"])

    def test_repeated_identical_and_stable_mode_do_not_spam(self):
        local = row(0)
        self.assertEqual(event_types([local, local, row(60), row(120)]), [])
        boot = row(60, boot=True, counter=1, transition=60, since=60)
        self.assertEqual(event_types([row(0), boot, boot, row(120, boot=True,
                             counter=1, transition=60, since=60)]), [model.BOOT])

    def test_unknown_initial_baseline_is_not_fabricated_transition(self):
        self.assertEqual(event_types([row(0,boot=True,counter=1,since=0)]), [])
        output=model.timeline([row(0,boot=True,counter=1,since=0),row(60,counter=1)])
        self.assertEqual(event_types([row(0,boot=True,counter=1,since=0),row(60,counter=1)]),
                         [model.LOCAL])
        end=output["events"][0]
        self.assertEqual(end["duration_lower_seconds"],0)
        self.assertIsNone(end["duration_upper_seconds"])

    def test_bootstrap_timestamp_not_recorded_remains_observed_only(self):
        events=model.timeline([row(0),row(60,boot=True,counter=1,since=0)])["events"]
        self.assertEqual(events[0]["event_type"],model.BOOT)
        self.assertEqual(events[0]["reason_code"],"MODE_CHANGE_FALLBACK_START_UNRECORDED")
        self.assertEqual(events[0]["coverage"],"SAMPLED_ONLY")

    def test_uncorroborated_counter_does_not_claim_exact_transition(self):
        result=model.timeline([row(0),row(60,boot=True,counter=0)])["events"][0]
        self.assertEqual(result["event_type"],model.BOOT)
        self.assertEqual(result["reason_code"],"MODE_CHANGE_COUNTER_UNCORROBORATED")
        self.assertEqual(result["effective_time_source"],"FEDORA_COLLECTION_INTERVAL")

    def test_gaps_break_continuity_no_invented_transition(self):
        output=model.timeline([row(0),row(240,boot=True,counter=1),
                               row(300,boot=True,counter=1)])["events"]
        self.assertEqual([e["event_type"] for e in output],[model.STALE])
        self.assertEqual(output[0]["reason_code"],"COLLECTION_GAP")
        self.assertIsNone(output[0]["duration_lower_seconds"])

    def test_counter_reset_is_not_silent(self):
        events=model.timeline([row(0,counter=4),row(60,boot=True,counter=0),
                               row(120,boot=True,counter=0)])["events"]
        self.assertEqual([e["event_type"] for e in events],[model.UNKNOWN])
        self.assertEqual(events[0]["reason_code"],"COUNTER_RESET_OR_REBOOT")

    def test_counter_implies_hidden_transitions(self):
        for samples in (
            [row(0,counter=0),row(60,counter=1)],
            [row(0,counter=0),row(60,boot=True,counter=3)],
            [row(0,boot=True,counter=1),row(60,counter=2)],
        ):
            with self.subTest(samples=samples):
                events=model.timeline(samples)["events"]
                self.assertEqual(events[0]["event_type"],model.UNKNOWN)
                self.assertEqual(events[0]["reason_code"],
                                 "COUNTER_SUGGESTS_MISSED_TRANSITION")

    def test_out_of_order_sample_is_unknown_and_reset(self):
        samples=[row(0),row(60,boot=True,counter=1),
                 row(30,boot=True,counter=1),row(90,counter=1)]
        types=event_types(samples)
        self.assertEqual(types,[model.BOOT,model.UNKNOWN])
        self.assertEqual(model.timeline(samples)["events"][1]["reason_code"],
                         "OUT_OF_ORDER_SAMPLE")

    def test_conflicting_same_collection_never_chooses_winner(self):
        samples=[row(0),row(60,boot=True,counter=1),
                 row(60,boot=False,counter=1),row(120,boot=False,counter=1)]
        out=model.timeline(samples)["events"]
        self.assertEqual([e["event_type"] for e in out],[model.BOOT,model.UNKNOWN])
        self.assertEqual(out[-1]["reason_code"],"CONTRADICTORY_SAME_COLLECTION")

    def test_missing_invalid_and_extra_labels_do_not_leak(self):
        for invalid in (
            None, {}, {"collection_epoch":BASE},
            {**row(0),"instance":"PRIVATE-HOST"},
            {**row(0),"client":"SENSITIVE"},
            {**row(0),"state_valid":0},
            {**row(0),"mode_bootstrap":1},
            {**row(0),"mode_local":True},
            {**row(0),"collection_epoch":"1793100000"},
            {**row(0),"last_transition_epoch":BASE+100},
            {**row(0),"fallback_since_epoch":BASE+1},
            {**row(0),"fallback_transitions_total":-1},
        ):
            with self.subTest(invalid=str(invalid)[:30]):
                result=model.timeline([row(-60),invalid,row(60,boot=True,counter=1)])
                self.assertEqual(event_types([row(-60),invalid,row(60,boot=True,counter=1)]),
                                 [model.UNKNOWN])
                self.assertNotIn("SENSITIVE",str(result))
                self.assertNotIn("PRIVATE-HOST",str(result))

    def test_bounded_input_and_no_implicit_network(self):
        with self.assertRaises(ValueError):
            model.timeline([row(0)]*257)
        with self.assertRaises(ValueError):
            model.timeline({"unexpected":"shape"})
        self.assertEqual(model.timeline([])["event_count"],0)
        source=SOURCE.read_text(encoding="utf-8")
        for command in ("import subprocess","import socket","import requests",
                        "http.client","urllib.request","open(","os.system"):
            self.assertNotIn(command,source)
        self.assertEqual(model.timeline([row(0)])["deployment_gate"],"HOLD")

    def test_transition_time_conflict_is_not_reported_exact(self):
        samples=[row(0),row(60,boot=True,counter=1,
                           transition=-10,since=60)]
        ev=model.timeline(samples)["events"][0]
        self.assertEqual(ev["event_type"],model.BOOT)
        self.assertIsNone(ev["reported_transition_at"])
        self.assertEqual(ev["window_start"],model._utc(BASE))
        self.assertEqual(ev["window_end"],model._utc(BASE+60))

    def test_non_atomic_short_flap_cannot_be_invented(self):
        # LOCAL at 0 and LOCAL at 60: a short fallback may have occurred,
        # but coarse samples alone cannot prove it.
        self.assertEqual(event_types([row(0),row(60)]),[])
        # Counter advanced: model warns about a missed transition,
        # not a fabricated transition timestamp or recovered event.
        e=model.timeline([row(0),row(60,counter=1)])["events"][0]
        self.assertEqual(e["event_type"],model.UNKNOWN)
        self.assertIsNone(e["reported_transition_at"])

    def test_second_bootstrap_after_recovery_is_distinct(self):
        samples=[
            row(0), row(60,boot=True,counter=1,transition=60,since=60),
            row(120,counter=1,transition=120),
            row(180,boot=True,counter=2,transition=180,since=180),
            row(240,counter=2,transition=240),
        ]
        events=model.timeline(samples)["events"]
        self.assertEqual([e["event_type"] for e in events],
                         [model.BOOT,model.LOCAL,model.BOOT,model.LOCAL])
        self.assertEqual(len({e["dedupe_key"] for e in events}),4)


if __name__ == "__main__":
    unittest.main()
