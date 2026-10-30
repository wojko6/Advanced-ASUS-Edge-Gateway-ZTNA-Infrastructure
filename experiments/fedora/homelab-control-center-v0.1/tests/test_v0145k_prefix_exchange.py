"""Bounded owned-peer prefix execution; no actual Loki/ACK advancement."""
import contextlib
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
import v0145j_loopback_exchange as exchange
import v0145k_prefix_exchange as prefix


class PrefixExchange(unittest.TestCase):
    def setUp(self):
        self.raw, self.ack = planning.fixture_inputs()
        self.plan = planning.build_plan(self.raw, self.ack)
        self.read = mock.Mock(return_value=(self.raw, self.ack))
        self.created = []
        original = exchange.LoopbackFixture.__init__
        created = self.created
        def track(fixture, request, reply=exchange.Reply()):
            original(fixture, request, reply)
            created.append(fixture)
        patcher = mock.patch.object(exchange.LoopbackFixture, '__init__', new=track)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_prefix(self, **kwargs):
        return prefix.run_prefix(self.plan, self.read, **kwargs)

    def assert_closed(self, fixtures=None):
        for fixture in self.created if fixtures is None else fixtures:
            if fixture._used:
                self.assertFalse(fixture.active)
                self.assertFalse(fixture.thread.is_alive())
                self.assertEqual(fixture.server.socket.fileno(), -1)
            else:
                self.assertIsNone(fixture.server)
                self.assertIsNone(fixture.thread)

    def test_all_three_batches_match_and_keep_source_ack_plan_unchanged(self):
        result = self.run_prefix()
        self.assertEqual(result.outcome, 'PREFIX_MATCHED_OWNED_FIXTURES_ONLY')
        self.assertEqual((result.total_requests, result.selected_requests, result.send_calls,
                          result.matched_requests, result.observed_posts, result.uninvoked_requests),
                         (3, 3, 3, 3, 3, 0))
        self.assertEqual(result.plan_pending_records, 33)
        self.assertIsNone(result.stopped_index)
        self.assertIsNone(result.stop_phase)
        self.assertEqual([fixture.seen for fixture in self.created],
                         [[request.body] for request in self.plan.requests])
        planning.require_current(self.plan, self.raw, self.ack)
        self.assertEqual(self.plan.declared_acks, 2)
        self.assert_closed()

    def test_explicit_one_request_prefix_does_not_drain_remaining_requests(self):
        result = self.run_prefix(limit=1)
        self.assertEqual(result.selected_requests, 1)
        self.assertEqual(result.matched_requests, 1)
        self.assertEqual(result.uninvoked_requests, 2)
        self.assertEqual(result.plan_pending_records, 33)
        self.assertEqual(len(self.created), 1)
        self.assertEqual(self.read.call_count, 1)
        self.assert_closed()

    def test_maximum_four_request_prefix_leaves_larger_plan_uninvoked(self):
        events = [identity.normalized_events(identity.envelope(f'synthetic-prefix-{n:04d}'),
                                             identity.SYNTHETIC_KEY)[0] for n in range(65)]
        events.sort(key=lambda payload: json.loads(payload)['event_id'])
        raw = handoff.encode_snapshot(identity.scope_for(identity.SYNTHETIC_KEY), events)
        plan = planning.build_plan(raw)
        read = mock.Mock(return_value=(raw, None))
        result = prefix.run_prefix(plan, read, limit=4)
        self.assertEqual((result.total_requests, result.selected_requests, result.send_calls,
                          result.matched_requests, result.uninvoked_requests, result.plan_pending_records),
                         (5, 4, 4, 4, 1, 65))
        self.assertEqual(read.call_count, 4)
        self.assert_closed()

    def test_state_recheck_occurs_after_previous_peer_has_closed(self):
        calls = 0
        def current():
            nonlocal calls
            for fixture in self.created[:calls]:
                self.assertFalse(fixture.active)
                self.assertFalse(fixture.thread.is_alive())
                self.assertEqual(fixture.server.socket.fileno(), -1)
            calls += 1
            return self.raw, self.ack
        result = prefix.run_prefix(self.plan, current)
        self.assertEqual(result.matched_requests, 3)
        self.assertEqual(calls, 3)

    def test_second_http_500_stops_without_third_listener_or_retry(self):
        replies = (exchange.Reply(), exchange.Reply(status=500), exchange.Reply())
        result = self.run_prefix(replies=replies)
        self.assertEqual(result.outcome, 'HOLD_PREFIX_STOPPED')
        self.assertEqual((result.send_calls, result.matched_requests, result.observed_posts,
                          result.uninvoked_requests, result.stopped_index), (2, 1, 2, 1, 1))
        self.assertEqual(result.stop_phase, 'EXCHANGE_OR_CLEANUP')
        self.assertEqual(self.read.call_count, 2)
        self.assertTrue(self.created[0]._used and self.created[1]._used)
        self.assertFalse(self.created[2]._used)
        self.assertEqual(result.plan_pending_records, 33)
        self.assert_closed()

    def test_first_429_does_not_invoke_second_or_third_request(self):
        result = self.run_prefix(replies=(exchange.Reply(status=429), exchange.Reply(), exchange.Reply()))
        self.assertEqual((result.send_calls, result.matched_requests, result.observed_posts,
                          result.stopped_index, result.uninvoked_requests), (1, 0, 1, 0, 2))
        self.assertEqual(self.read.call_count, 1)
        self.assertFalse(self.created[1]._used or self.created[2]._used)
        self.assert_closed()

    def test_changed_ack_before_second_request_stops_before_listener_creation(self):
        self.read.side_effect = [(self.raw, self.ack), (self.raw, None), AssertionError('third read')]
        result = self.run_prefix()
        self.assertEqual(result.outcome, 'HOLD_PREFIX_STOPPED')
        self.assertEqual(result.stop_phase, 'STATE_REVALIDATION')
        self.assertEqual((result.send_calls, result.matched_requests, result.observed_posts,
                          result.stopped_index, result.uninvoked_requests), (1, 1, 1, 1, 2))
        self.assertEqual(self.read.call_count, 2)
        self.assertFalse(self.created[1]._used or self.created[2]._used)
        self.assert_closed()

    def test_corrupt_source_before_second_request_stops_all_following_calls(self):
        self.read.side_effect = [(self.raw, self.ack), (b'corrupt', self.ack)]
        result = self.run_prefix()
        self.assertEqual(result.stop_phase, 'STATE_REVALIDATION')
        self.assertEqual((result.send_calls, result.matched_requests, result.stopped_index), (1, 1, 1))
        self.assertEqual(self.read.call_count, 2)
        self.assert_closed()

    def test_state_provider_error_after_first_is_sanitized_and_stops(self):
        self.read.side_effect = [(self.raw, self.ack), RuntimeError('synthetic-private-state')]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            result = self.run_prefix()
        self.assertEqual(result.stop_phase, 'STATE_REVALIDATION')
        self.assertNotIn('synthetic-private-state', repr(result))
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(self.read.call_count, 2)
        self.assert_closed()

    def test_bad_initial_state_or_plan_creates_no_fixture(self):
        for sample in ((b'corrupt', self.ack), (self.raw, b'corrupt'), (self.raw, None)):
            self.read.return_value = sample
            with self.assertRaises(spool.Hold):
                self.run_prefix()
        with self.assertRaises(spool.Hold):
            prefix.run_prefix(None, lambda: (self.raw, self.ack))
        self.assertEqual(self.created, [])

    def test_bad_initial_provider_shape_or_error_creates_no_fixture(self):
        for sample in (None, [self.raw, self.ack], (self.raw,), (self.raw, self.ack, None)):
            with self.assertRaises(spool.Hold):
                prefix.run_prefix(self.plan, lambda: sample)
        with self.assertRaisesRegex(spool.Hold, 'PREFIX_STATE_PROVIDER_FAILURE'):
            prefix.run_prefix(self.plan, mock.Mock(side_effect=RuntimeError('synthetic-provider')))
        self.assertEqual(self.created, [])

    def test_invalid_limit_or_provider_does_not_call_state_reader(self):
        for value in (True, 0, -1, 5, 3.0, '3', None):
            with self.assertRaisesRegex(spool.Hold, 'PREFIX_OPTIONS'):
                self.run_prefix(limit=value)
        for provider in (None, {}, (self.raw, self.ack)):
            with self.assertRaisesRegex(spool.Hold, 'PREFIX_OPTIONS'):
                prefix.run_prefix(self.plan, provider)
        self.assertEqual(self.read.call_count, 0)
        self.assertEqual(self.created, [])

    def test_reply_script_count_and_container_reject_before_listener_creation(self):
        for replies in ((), (exchange.Reply(),), [], 'script', (exchange.Reply(),) * 4):
            with self.assertRaisesRegex(spool.Hold, 'PREFIX_REPLY_COUNT'):
                self.run_prefix(replies=replies)
        self.assertEqual(self.created, [])

    def test_invalid_late_reply_is_prevalidated_before_any_network(self):
        replies = (exchange.Reply(), exchange.Reply(), exchange.Reply(mode='unknown'))
        with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('client started')):
            with self.assertRaises(spool.Hold):
                self.run_prefix(replies=replies)
        self.assertEqual(len(self.created), 2)
        self.assertTrue(all(not fixture._used and fixture.server is None for fixture in self.created))

    def test_prefix_byte_budget_exact_boundary_and_rejection_before_network(self):
        size = len(self.plan.requests[0].body)
        with mock.patch.object(prefix, 'MAX_PREFIX_BYTES', size):
            result = self.run_prefix(limit=1)
        self.assertEqual(result.matched_requests, 1)
        created = len(self.created)
        with mock.patch.object(prefix, 'MAX_PREFIX_BYTES', size - 1):
            with self.assertRaisesRegex(spool.Hold, 'PREFIX_BODY_BUDGET'):
                self.run_prefix(limit=1)
        self.assertEqual(len(self.created), created)
        self.assert_closed()

    def test_unexpected_result_marker_is_not_counted_as_a_match(self):
        with mock.patch.object(exchange, 'send_one', return_value=True) as send:
            result = self.run_prefix()
        self.assertEqual((result.send_calls, result.matched_requests, result.observed_posts), (1, 0, 0))
        self.assertEqual(result.stop_phase, 'EXCHANGE_OR_CLEANUP')
        self.assertEqual(send.call_count, 1)
        self.assert_closed()

    def test_cleanup_failure_after_positive_exchange_is_not_counted_as_a_match(self):
        original = exchange.LoopbackFixture.__exit__
        def failed_cleanup(fixture, *args):
            original(fixture, *args)
            raise OSError('synthetic cleanup failure after close')
        with mock.patch.object(exchange.LoopbackFixture, '__exit__', new=failed_cleanup):
            result = self.run_prefix()
        self.assertEqual((result.send_calls, result.matched_requests, result.observed_posts), (1, 0, 1))
        self.assertEqual(result.stopped_index, 0)
        self.assertFalse(self.created[1]._used or self.created[2]._used)
        self.assert_closed()

    def test_worker_creation_error_stops_and_closes_current_listener(self):
        with mock.patch.object(subprocess, 'Popen', side_effect=OSError('synthetic spawn failure')) as start:
            result = self.run_prefix()
        self.assertEqual((result.send_calls, result.matched_requests, result.observed_posts), (1, 0, 0))
        self.assertEqual(start.call_count, 1)
        self.assertEqual(result.stopped_index, 0)
        self.assert_closed()

    def test_real_second_stalled_peer_reaps_clients_and_never_starts_third(self):
        original = subprocess.Popen
        children = []
        def tracked(*args, **kwargs):
            child = original(*args, **kwargs)
            children.append(child)
            return child
        replies = (exchange.Reply(), exchange.Reply(mode='stall'), exchange.Reply())
        with mock.patch.object(subprocess, 'Popen', side_effect=tracked):
            result = self.run_prefix(replies=replies)
        self.assertEqual(result.outcome, 'HOLD_PREFIX_STOPPED')
        self.assertEqual((result.send_calls, result.matched_requests, result.stopped_index), (2, 1, 1))
        self.assertEqual(len(children), 2)
        self.assertTrue(all(child.poll() is not None for child in children))
        self.assertFalse(self.created[2]._used)
        self.assert_closed()

    def test_exchange_interrupt_propagates_after_current_peer_cleanup(self):
        original = exchange.send_one
        def interrupted(*args, **kwargs):
            if kwargs.get('index') == 1:
                raise KeyboardInterrupt()
            return original(*args, **kwargs)
        with mock.patch.object(exchange, 'send_one', side_effect=interrupted) as send:
            with self.assertRaises(KeyboardInterrupt):
                self.run_prefix()
        self.assertEqual(send.call_count, 2)
        self.assertEqual(self.read.call_count, 2)
        self.assertFalse(self.created[2]._used)
        self.assert_closed()

    def test_provider_interrupt_propagates_before_next_peer_opens(self):
        self.read.side_effect = [(self.raw, self.ack), KeyboardInterrupt()]
        with self.assertRaises(KeyboardInterrupt):
            self.run_prefix()
        self.assertEqual(self.read.call_count, 2)
        self.assertFalse(self.created[1]._used or self.created[2]._used)
        self.assert_closed()

    def test_all_declared_acked_has_no_fixture_or_client(self):
        raw = encoding.fixture_snapshot()
        source = handoff.decode_snapshot(raw)
        pairs = tuple((json.loads(payload)['event_id'], delivery.payload_hash(payload)) for payload in source.events)
        ack = delivery.encode_state(delivery.AckState(source.scope, pairs))
        plan = planning.build_plan(raw, ack)
        with mock.patch.object(socket, 'socket', side_effect=AssertionError('socket')), \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('client')):
            result = prefix.run_prefix(plan, lambda: (raw, ack))
        self.assertEqual(result.outcome, 'NO_PENDING_REQUESTS')
        self.assertEqual(result.selected_requests, 0)
        self.assertEqual(result.send_calls, 0)
        self.assertEqual(result.plan_pending_records, 0)
        self.assertEqual(self.created, [])

    def test_self_test_is_memory_only(self):
        with mock.patch('builtins.open', side_effect=AssertionError('file')), \
             mock.patch.object(os, 'open', side_effect=AssertionError('os.open')), \
             mock.patch.object(socket, 'socket', side_effect=AssertionError('network')), \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('client')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            prefix.self_test()
        self.assertIn('V0145K_SELFTEST=PASS_PURE_SYNTHETIC_ONLY', output.getvalue())
        self.assertIn('DEPLOYMENT_GATE=HOLD', output.getvalue())

    def test_lab_closes_all_peers_and_prints_counts_only(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            prefix.run_lab()
        text = output.getvalue()
        self.assertIn('V0145K_RESULT=PASS_OWNED_PREFIX_FIXTURES_ONLY', text)
        self.assertIn('PENDING_RECORDS_AFTER_RUN=33 DECLARED_ACKS_AFTER_RUN=2', text)
        self.assertNotIn(self.plan.scope, text)
        for request in self.plan.requests:
            self.assertNotIn(request.body.decode(), text)
            for event_id in request.event_ids:
                self.assertNotIn(event_id, text)
        for fixture in self.created:
            self.assertNotIn(fixture.token, text)
        self.assert_closed()

    def test_cli_rejects_urls_limits_ports_and_ambiguous_modes(self):
        for args in ([], ['--lab', '--self-test'], ['--lab', '--url', 'http://invalid.test/'],
                     ['--lab', '--limit', '64'], ['--port', '3100'], ['--input', 'synthetic.json']):
            with mock.patch.object(sys, 'argv', ['v0145k_prefix_exchange.py', *args]), \
                 mock.patch.object(prefix, 'self_test', side_effect=AssertionError('unexpected action')), \
                 mock.patch.object(prefix, 'run_lab', side_effect=AssertionError('unexpected action')), \
                 contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    prefix.main()
            self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
