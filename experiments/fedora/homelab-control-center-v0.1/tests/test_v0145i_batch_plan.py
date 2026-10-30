"""Frozen synthetic plans, declared ACK consistency and whole-plan refusal."""
import contextlib
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import v0145a_segment_spool as spool
import v0145d_event_identity as identity
import v0145e_atomic_handoff as handoff
import v0145f_delivery_ack as delivery
import v0145h_loki_request as encoding
import v0145i_batch_plan as planning

KEY = identity.SYNTHETIC_KEY
SCOPE = identity.scope_for(KEY)


def source(count, *, same_time=False):
    events = [identity.normalized_events(identity.envelope(f'synthetic-plan-{n:04d}',
                                                          1793350800123456 + (0 if same_time else n)), KEY)[0]
              for n in range(count)]
    events.sort(key=lambda payload: json.loads(payload)['event_id'])
    return handoff.encode_snapshot(SCOPE, events)


def declared_ack(raw, indexes):
    snapshot = handoff.decode_snapshot(raw)
    pairs = [(json.loads(snapshot.events[n])['event_id'], delivery.payload_hash(snapshot.events[n]))
             for n in indexes]
    return delivery.encode_state(delivery.AckState(snapshot.scope, tuple(sorted(pairs))))


def ordered_ids(raw, raw_ack=None):
    events = [json.loads(payload) for payload in handoff.decode_snapshot(raw).events]
    acknowledged = set() if raw_ack is None else {event_id for event_id, _ in delivery.decode_state(raw_ack).acknowledged}
    return tuple(event['event_id'] for event in sorted(events, key=lambda event: (event['time'], event['event_id']))
                 if event['event_id'] not in acknowledged)


class BatchPlanning(unittest.TestCase):
    def setUp(self):
        self.raw, self.ack = planning.fixture_inputs()
        self.snapshot = handoff.decode_snapshot(self.raw)

    def encode_events(self, events):
        events.sort(key=lambda event: event['event_id'])
        return handoff.encode_snapshot(SCOPE, [identity.canonical(event) for event in events])

    def test_one_batch_matches_h_exact_request(self):
        raw = encoding.fixture_snapshot()
        plan = planning.build_plan(raw)
        self.assertEqual(plan.requests, (encoding.build_request(raw),))
        self.assertEqual(plan.pending_ids, plan.requests[0].event_ids)
        self.assertEqual(plan.declared_acks, 0)
        self.assertEqual(plan.source_events, 3)

    def test_thirty_five_records_have_complete_disjoint_time_ordered_batches(self):
        plan = planning.build_plan(self.raw)
        self.assertEqual([len(request.event_ids) for request in plan.requests], [16, 16, 3])
        self.assertEqual(plan.pending_ids, ordered_ids(self.raw))
        self.assertEqual(len(set(plan.pending_ids)), 35)
        self.assertEqual(plan.body_bytes, sum(len(request.body) for request in plan.requests))
        for request in plan.requests:
            self.assertLessEqual(len(request.body), encoding.MAX_BODY_BYTES)
            values = json.loads(request.body)['streams'][0]['values']
            self.assertEqual(tuple(json.loads(value[1])['event_id'] for value in values), request.event_ids)

    def test_declared_two_acks_produce_sixteen_sixteen_one(self):
        plan = planning.build_plan(self.raw, self.ack)
        self.assertEqual([len(request.event_ids) for request in plan.requests], [16, 16, 1])
        self.assertEqual(plan.pending_ids, ordered_ids(self.raw, self.ack))
        self.assertEqual(plan.source_events, 35)
        self.assertEqual(plan.declared_acks, 2)

    def test_maximum_source_has_sixty_four_complete_requests(self):
        raw = source(1024)
        plan = planning.build_plan(raw)
        self.assertEqual(len(plan.requests), 64)
        self.assertTrue(all(len(request.event_ids) == 16 for request in plan.requests))
        self.assertEqual(plan.pending_ids, ordered_ids(raw))
        self.assertEqual(len(set(plan.pending_ids)), 1024)
        self.assertLessEqual(plan.body_bytes, planning.MAX_TOTAL_BODY_BYTES)

    def test_nonprefix_ack_set_skips_only_exact_acknowledged_ids(self):
        ack = declared_ack(self.raw, (2, 17, 33))
        plan = planning.build_plan(self.raw, ack)
        self.assertEqual(plan.pending_ids, ordered_ids(self.raw, ack))
        self.assertEqual(len(plan.pending_ids), 32)

    def test_all_acknowledged_returns_empty_plan_without_calling_formatter(self):
        ack = declared_ack(self.raw, range(35))
        with mock.patch.object(encoding, 'build_request', side_effect=AssertionError('no body expected')):
            plan = planning.build_plan(self.raw, ack)
        self.assertEqual(plan.requests, ())
        self.assertEqual(plan.pending_ids, ())
        self.assertEqual(plan.body_bytes, 0)
        self.assertEqual(plan.declared_acks, 35)
        planning.require_current(plan, self.raw, ack)

    def test_none_and_explicit_empty_ack_are_different_frozen_bases(self):
        empty = declared_ack(self.raw, ())
        first, second = planning.build_plan(self.raw), planning.build_plan(self.raw, empty)
        self.assertEqual(first.requests, second.requests)
        self.assertIsNone(first.ack_sha256)
        self.assertEqual(second.ack_sha256, hashlib.sha256(empty).hexdigest())
        with self.assertRaisesRegex(spool.Hold, 'PLAN_OR_INPUT_CHANGED'):
            planning.require_current(first, self.raw, empty)

    def test_source_and_ack_fingerprints_bind_exact_input_bytes(self):
        plan = planning.build_plan(self.raw, self.ack)
        self.assertEqual(plan.source_sha256, hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(plan.ack_sha256, hashlib.sha256(self.ack).hexdigest())
        self.assertEqual(plan.scope, SCOPE)
        self.assertEqual(planning.build_plan(self.raw, self.ack), plan)

    def test_unknown_ack_id_holds_before_any_request_is_built(self):
        ack = delivery.encode_state(delivery.AckState(SCOPE, (('a' * 64, 'b' * 64),)))
        with mock.patch.object(encoding, 'build_request', side_effect=AssertionError('formatting started')):
            with self.assertRaisesRegex(spool.Hold, 'PLAN_ACK_RECORD_MISSING_OR_CHANGED'):
                planning.build_plan(self.raw, ack)

    def test_wrong_ack_payload_hash_holds_before_any_request_is_built(self):
        event_id = json.loads(self.snapshot.events[0])['event_id']
        ack = delivery.encode_state(delivery.AckState(SCOPE, ((event_id, 'b' * 64),)))
        with mock.patch.object(encoding, 'build_request', side_effect=AssertionError('formatting started')):
            with self.assertRaisesRegex(spool.Hold, 'PLAN_ACK_RECORD_MISSING_OR_CHANGED'):
                planning.build_plan(self.raw, ack)

    def test_wrong_ack_scope_holds_before_any_request_is_built(self):
        ack = delivery.encode_state(delivery.AckState('b' * 64, ()))
        with mock.patch.object(encoding, 'build_request', side_effect=AssertionError('formatting started')):
            with self.assertRaisesRegex(spool.Hold, 'PLAN_ACK_SCOPE_MISMATCH'):
                planning.build_plan(self.raw, ack)

    def test_corrupt_ack_never_falls_back_to_no_ack(self):
        for ack in (b'', b'corrupt', b'null', bytearray(self.ack), {}, self.ack.decode(),
                    self.ack.replace(b'"digest":', b'"digest":"wrong","digest":', 1)):
            with self.assertRaises(spool.Hold):
                planning.build_plan(self.raw, ack)

    def test_late_corrupt_source_holds_before_any_request_is_built(self):
        events = [json.loads(payload) for payload in self.snapshot.events]
        events[-1]['MESSAGE'] = 'synthetic-private-tail'
        raw = self.encode_events(events)
        with mock.patch.object(encoding, 'build_request', side_effect=AssertionError('formatting started')):
            with self.assertRaisesRegex(spool.Hold, 'HANDOFF_EVENT_SCHEMA'):
                planning.build_plan(raw, self.ack)

    def test_unsorted_duplicate_and_bad_digest_source_are_not_repaired(self):
        obj = json.loads(self.raw)
        obj['digest'] = 'b' * 64
        invalid = (identity.canonical(obj) + b'\n',
                   handoff.encode_snapshot(SCOPE, tuple(reversed(self.snapshot.events))),
                   handoff.encode_snapshot(SCOPE, (self.snapshot.events[0], self.snapshot.events[0])))
        for raw in invalid:
            with self.assertRaises(spool.Hold):
                planning.build_plan(raw)

    def test_source_input_is_bounded_exact_bytes_not_paths_or_legacy_records(self):
        for raw in (None, '', '/tmp/synthetic.json', {}, bytearray(self.raw),
                    identity.envelope('synthetic-raw'), b'x' * (handoff.MAX_SNAPSHOT_BYTES + 1)):
            with self.assertRaises(spool.Hold):
                planning.build_plan(raw)

    def test_changed_payload_under_declared_ack_is_not_silently_skipped(self):
        events = [json.loads(payload) for payload in self.snapshot.events]
        events[0]['kind'] = 'HTTP_IMPORT_TIMEOUT'
        with self.assertRaisesRegex(spool.Hold, 'PLAN_ACK_RECORD_MISSING_OR_CHANGED'):
            planning.build_plan(self.encode_events(events), self.ack)

    def test_old_plan_rejects_source_append(self):
        plan = planning.build_plan(self.raw, self.ack)
        with self.assertRaisesRegex(spool.Hold, 'PLAN_OR_INPUT_CHANGED'):
            planning.require_current(plan, source(36), self.ack)

    def test_old_plan_rejects_ack_advance(self):
        plan = planning.build_plan(self.raw, self.ack)
        advanced = declared_ack(self.raw, (0, 1, 34))
        with self.assertRaisesRegex(spool.Hold, 'PLAN_OR_INPUT_CHANGED'):
            planning.require_current(plan, self.raw, advanced)

    def test_recompute_rejects_body_checksum_membership_and_plan_metadata_changes(self):
        plan = planning.build_plan(self.raw, self.ack)
        first = plan.requests[0]
        altered = (replace(first, body=first.body + b' '), replace(first, sha256='b' * 64),
                   replace(first, event_ids=('a' * 64,)), replace(first, scope='b' * 64))
        plans = [replace(plan, requests=(request, *plan.requests[1:])) for request in altered]
        plans += [replace(plan, requests=plan.requests[:-1]), replace(plan, declared_acks=3),
                  replace(plan, source_sha256='b' * 64), replace(plan, scope='b' * 64)]
        for changed in plans:
            with self.assertRaisesRegex(spool.Hold, 'PLAN_OR_INPUT_CHANGED'):
                planning.require_current(changed, self.raw, self.ack)

    def test_current_check_rejects_invalid_plan_or_fresh_corrupt_inputs(self):
        for value in (None, {}, []):
            with self.assertRaises(spool.Hold):
                planning.require_current(value, self.raw, self.ack)
        plan = planning.build_plan(self.raw, self.ack)
        for raw, ack in ((b'corrupt', self.ack), (self.raw, b'corrupt')):
            with self.assertRaises(spool.Hold):
                planning.require_current(plan, raw, ack)

    def test_recompute_rejects_equality_coercion_and_mutable_request_bytes(self):
        raw = source(1)
        plan = planning.build_plan(raw)
        altered = (replace(plan, source_events=True), replace(plan, source_events=1.0),
                   replace(plan, declared_acks=False),
                   replace(plan, requests=(replace(plan.requests[0], body=bytearray(plan.requests[0].body)),)))
        for index, changed in enumerate(altered):
            with self.subTest(index=index):
                with self.assertRaises(spool.Hold):
                    planning.require_current(changed, raw)

    def test_append_lower_id_after_all_declared_acks_is_still_pending(self):
        all_ack = declared_ack(self.raw, range(35))
        old_plan = planning.build_plan(self.raw, all_ack)
        prior_min = json.loads(self.snapshot.events[0])['event_id']
        candidate = next(payload for n in range(35, 1024)
                         if (payload := identity.normalized_events(identity.envelope(f'synthetic-new-{n:04d}',
                                                                                    1793350800123455), KEY)[0])
                         and json.loads(payload)['event_id'] < prior_min)
        events = sorted((*self.snapshot.events, candidate), key=lambda payload: json.loads(payload)['event_id'])
        raw = handoff.encode_snapshot(SCOPE, events)
        with self.assertRaises(spool.Hold):
            planning.require_current(old_plan, raw, all_ack)
        new_plan = planning.build_plan(raw, all_ack)
        self.assertEqual(new_plan.pending_ids, (json.loads(candidate)['event_id'],))

    def test_same_timestamp_ids_are_globally_ordered_across_request_boundaries(self):
        raw = source(35, same_time=True)
        plan = planning.build_plan(raw)
        self.assertEqual(plan.pending_ids, tuple(sorted(plan.pending_ids)))
        self.assertEqual(len(set(plan.pending_ids)), 35)

    def test_request_count_limit_holds_before_building_any_prefix(self):
        with mock.patch.object(planning, 'MAX_REQUESTS', 1), \
             mock.patch.object(encoding, 'build_request', side_effect=AssertionError('formatting started')):
            with self.assertRaisesRegex(spool.Hold, 'PLAN_REQUEST_COUNT_LIMIT'):
                planning.build_plan(self.raw)

    def test_total_body_budget_accepts_exact_boundary_and_rejects_less(self):
        expected = planning.build_plan(self.raw, self.ack)
        with mock.patch.object(planning, 'MAX_TOTAL_BODY_BYTES', expected.body_bytes):
            self.assertEqual(planning.build_plan(self.raw, self.ack), expected)
        with mock.patch.object(planning, 'MAX_TOTAL_BODY_BYTES', expected.body_bytes - 1):
            with self.assertRaisesRegex(spool.Hold, 'PLAN_TOTAL_BYTES_LIMIT'):
                planning.build_plan(self.raw, self.ack)

    def test_later_formatter_failure_does_not_return_or_print_partial_plan(self):
        original = encoding.build_request
        calls = 0
        def fail_second(raw):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise spool.Hold('SYNTHETIC_SECOND_REQUEST_FAILURE')
            return original(raw)
        with mock.patch.object(encoding, 'build_request', side_effect=fail_second), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaisesRegex(spool.Hold, 'SYNTHETIC_SECOND_REQUEST_FAILURE'):
                planning.build_plan(self.raw, self.ack)
        self.assertEqual(calls, 2)
        self.assertEqual(output.getvalue(), '')

    def test_mutually_consistent_forged_source_and_ack_are_not_authentication(self):
        event = dict(json.loads(self.snapshot.events[0]), event_id='a' * 64)
        raw = self.encode_events([event])
        ack = declared_ack(raw, (0,))
        plan = planning.build_plan(raw, ack)
        self.assertEqual(plan.pending_ids, ())
        self.assertEqual(plan.declared_acks, 1)  # Declared, not an observed receipt.

    def guarded_cli(self, action, marker):
        with mock.patch('builtins.open', side_effect=AssertionError('file')), \
             mock.patch.object(os, 'open', side_effect=AssertionError('os.open')), \
             mock.patch.object(socket, 'socket', side_effect=AssertionError('network')), \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('subprocess')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            action()
        text = output.getvalue()
        self.assertIn(marker, text)
        self.assertIn('DEPLOYMENT_GATE=HOLD', text)
        self.assertNotIn(SCOPE, text)
        for payload in self.snapshot.events:
            self.assertNotIn(json.loads(payload)['event_id'], text)
            self.assertNotIn(payload.decode('ascii'), text)

    def test_self_test_is_memory_only_with_counts_only_output(self):
        self.guarded_cli(planning.self_test, 'V0145I_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')

    def test_lab_is_memory_only_with_counts_only_output(self):
        self.guarded_cli(planning.run_lab, 'V0145I_RESULT=PASS_OFFLINE_BATCH_PLAN_ONLY')

    def test_cli_rejects_paths_urls_budget_overrides_and_ambiguous_modes(self):
        for args in ([], ['--lab', '--self-test'], ['--lab', '--input', 'synthetic.json'],
                     ['--url', 'http://invalid.test/'], ['--lab', '--max-events', '100'], ['--serve']):
            with mock.patch.object(sys, 'argv', ['v0145i_batch_plan.py', *args]), \
                 mock.patch.object(planning, 'self_test', side_effect=AssertionError('unexpected action')), \
                 mock.patch.object(planning, 'run_lab', side_effect=AssertionError('unexpected action')), \
                 contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    planning.main()
            self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
