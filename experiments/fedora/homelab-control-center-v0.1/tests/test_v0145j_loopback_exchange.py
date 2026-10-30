"""One owned IPv4 fixture, bounded child client, never a real Loki receipt."""
import base64
import contextlib
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
import v0145h_loki_request as encoding
import v0145i_batch_plan as planning
import v0145j_loopback_exchange as exchange


class PureContract(unittest.TestCase):
    def test_only_exact_empty_204_fixture_report_passes(self):
        exchange.validate_report(b'{"status":204,"body_bytes":0,"framing":true}')
        for value in ({'status': 204.0, 'body_bytes': 0, 'framing': True},
                      {'status': 204, 'body_bytes': False, 'framing': True},
                      {'status': 204, 'body_bytes': 0, 'framing': 1},
                      {'status': 204, 'body_bytes': 1, 'framing': True},
                      {'status': 204, 'body_bytes': 0, 'framing': False}):
            with self.assertRaises(spool.Hold):
                exchange.validate_report(identity.canonical(value))

    def test_other_success_blocked_redirect_and_error_statuses_hold(self):
        for status in (200, 201, 202, 206, 260, 301, 307, 400, 429, 500, 503):
            with self.assertRaisesRegex(spool.Hold, 'CLIENT_RESPONSE_REJECTED'):
                exchange.validate_report(identity.canonical({'status': status, 'body_bytes': 0, 'framing': True}))

    def test_report_schema_bounds_and_errors_never_echo_response_data(self):
        for raw in (None, b'', b'\xff', b'null', b'NaN', b'{}',
                    b'{"error":"synthetic-private-response"}',
                    b'{"status":204,"status":204,"body_bytes":0,"framing":true}',
                    b'x' * (exchange.MAX_REPORT_BYTES + 1)):
            with self.assertRaises(spool.Hold) as caught:
                exchange.validate_report(raw)
            self.assertNotIn('synthetic-private-response', str(caught.exception))

    def make_job(self, body=b'synthetic'):
        return {'port': 40000, 'capability': 'a' * 32,
                'body': base64.b64encode(body).decode('ascii'), 'sha256': hashlib.sha256(body).hexdigest()}

    def test_worker_job_roundtrip_and_body_bound(self):
        job = self.make_job()
        self.assertEqual(exchange._decode_job(identity.canonical(job)), (40000, 'a' * 32, b'synthetic'))
        job = self.make_job(b'x' * encoding.MAX_BODY_BYTES)
        self.assertEqual(len(exchange._decode_job(identity.canonical(job))[2]), encoding.MAX_BODY_BYTES)
        with self.assertRaises(spool.Hold):
            exchange._decode_job(identity.canonical(self.make_job(b'x' * (encoding.MAX_BODY_BYTES + 1))))

    def test_worker_job_rejects_url_host_port_coercion_bad_token_hash_and_base64(self):
        changes = ({'host': 'external.invalid'}, {'url': 'http://external.invalid/'}, {'port': True},
                   {'port': 0}, {'port': 65536}, {'capability': 'not-a-capability'},
                   {'sha256': 'b' * 64}, {'body': '%%%'}, {'body': ''}, {'body': '非ASCII'})
        for change in changes:
            with self.assertRaises(spool.Hold):
                exchange._decode_job(identity.canonical(dict(self.make_job(), **change)))
        for raw in (None, b'', b'null', b'\xff', b'x' * (exchange.MAX_JOB_BYTES + 1)):
            with self.assertRaises(spool.Hold):
                exchange._decode_job(raw)

    def test_timeout_kills_and_reaps_client_without_retry(self):
        process = mock.Mock()
        process.communicate.side_effect = [subprocess.TimeoutExpired('synthetic', 2), (b'', b'')]
        with mock.patch.object(exchange.subprocess, 'Popen', return_value=process) as start:
            with self.assertRaisesRegex(spool.Hold, 'CLIENT_DEADLINE_EXPIRED'):
                exchange._run_worker(self.make_job())
        self.assertEqual(start.call_count, 1)
        process.kill.assert_called_once()
        self.assertEqual(process.communicate.call_count, 2)
        self.assertEqual(process.communicate.call_args.kwargs['timeout'], exchange.REAP_SECONDS)

    def test_unexpected_client_interrupt_also_kills_and_reaps(self):
        for error in (KeyboardInterrupt, OSError):
            process = mock.Mock()
            process.communicate.side_effect = [error(), (b'', b'')]
            with mock.patch.object(exchange.subprocess, 'Popen', return_value=process):
                with self.assertRaises(error):
                    exchange._run_worker(self.make_job())
            process.kill.assert_called_once()
            self.assertEqual(process.communicate.call_count, 2)

    def test_nonzero_stderr_and_malformed_worker_output_hold(self):
        for code, out, error in ((1, b'', b''), (0, b'', b'synthetic-stderr'), (0, b'invalid', b'')):
            process = mock.Mock(returncode=code)
            process.communicate.return_value = (out, error)
            with mock.patch.object(exchange.subprocess, 'Popen', return_value=process) as start:
                with self.assertRaises(spool.Hold):
                    exchange._run_worker(self.make_job())
            self.assertEqual(start.call_count, 1)

    def test_reap_timeout_cannot_be_reported_as_success(self):
        process = mock.Mock()
        process.communicate.side_effect = subprocess.TimeoutExpired('synthetic', 2)
        with mock.patch.object(exchange.subprocess, 'Popen', return_value=process):
            with self.assertRaisesRegex(spool.Hold, 'CLIENT_REAP_TIMEOUT'):
                exchange._run_worker(self.make_job())

    def test_self_test_is_memory_only_and_counts_only(self):
        with mock.patch('builtins.open', side_effect=AssertionError('file')), \
             mock.patch.object(os, 'open', side_effect=AssertionError('os.open')), \
             mock.patch.object(socket, 'socket', side_effect=AssertionError('network')), \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('subprocess')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            exchange.self_test()
        self.assertIn('V0145J_SELFTEST=PASS_PURE_SYNTHETIC_ONLY', output.getvalue())
        self.assertIn('DEPLOYMENT_GATE=HOLD', output.getvalue())

    def test_cli_rejects_paths_urls_ports_workers_and_ambiguous_modes(self):
        for args in ([], ['--lab', '--self-test'], ['--lab', '--url', 'http://invalid.test/'],
                     ['--lab', '--port', '3100'], ['--worker'], ['--input', 'synthetic.json']):
            with mock.patch.object(sys, 'argv', ['v0145j_loopback_exchange.py', *args]), \
                 mock.patch.object(exchange, 'self_test', side_effect=AssertionError('unexpected action')), \
                 mock.patch.object(exchange, 'run_lab', side_effect=AssertionError('unexpected action')), \
                 contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    exchange.main()
            self.assertEqual(caught.exception.code, 2)


class OwnedLoopback(unittest.TestCase):
    def setUp(self):
        self.raw, self.ack = planning.fixture_inputs()
        self.plan = planning.build_plan(self.raw, self.ack)

    def fixture(self, reply=exchange.Reply(), index=0):
        return exchange.LoopbackFixture(self.plan.requests[index], reply)

    def assert_closed(self, fixture):
        self.assertFalse(fixture.active)
        self.assertFalse(fixture.thread.is_alive())
        self.assertEqual(fixture.server.socket.fileno(), -1)

    def test_one_real_http_request_matches_body_and_keeps_plan_and_ack_unchanged(self):
        before = self.plan
        with self.fixture() as fixture:
            self.assertEqual(fixture.server.socket.getsockname()[0], '127.0.0.1')
            self.assertEqual(exchange.send_one(self.plan, self.raw, self.ack, fixture),
                             'PASS_OWNED_FIXTURE_EXCHANGE_ONLY')
            self.assertEqual(fixture.seen, [self.plan.requests[0].body])
            self.assertEqual(fixture.total_posts, 1)
        self.assert_closed(fixture)
        planning.require_current(before, self.raw, self.ack)
        self.assertEqual(len(self.plan.requests), 3)
        self.assertEqual(self.plan.declared_acks, 2)

    def test_owned_server_binding_does_not_resolve_host_names(self):
        with mock.patch.object(socket, 'getfqdn', side_effect=AssertionError('reverse lookup')), \
             mock.patch.object(socket, 'gethostbyaddr', side_effect=AssertionError('reverse lookup')):
            with self.fixture() as fixture:
                self.assertEqual(fixture.server.server_name, 'hcc-loopback-fixture')
                self.assertEqual(fixture.server.socket.getsockname()[0], '127.0.0.1')
        self.assert_closed(fixture)

    def test_single_attempt_cannot_be_repeated_with_same_fixture(self):
        with self.fixture() as fixture:
            exchange.send_one(self.plan, self.raw, self.ack, fixture)
            with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('retry')):
                with self.assertRaisesRegex(spool.Hold, 'ATTEMPT_ALREADY_CONSUMED'):
                    exchange.send_one(self.plan, self.raw, self.ack, fixture)
            self.assertEqual(fixture.total_posts, 1)

    def test_other_plan_index_needs_its_own_matching_fixture(self):
        with self.fixture(index=1) as fixture:
            with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('wrong body')):
                with self.assertRaisesRegex(spool.Hold, 'MATCHING_FIXTURE'):
                    exchange.send_one(self.plan, self.raw, self.ack, fixture)
            self.assertFalse(fixture._attempted)
            exchange.send_one(self.plan, self.raw, self.ack, fixture, index=1)
            self.assertEqual(fixture.seen, [self.plan.requests[1].body])

    def test_stale_plan_is_rejected_before_starting_client(self):
        with self.fixture() as fixture, \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('stale send')):
            with self.assertRaises(spool.Hold):
                exchange.send_one(self.plan, self.raw, None, fixture)
            self.assertEqual(fixture.total_posts, 0)
            self.assertFalse(fixture._attempted)

    def test_invalid_index_and_empty_plan_do_not_start_client(self):
        with self.fixture() as fixture, \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('bad index')):
            for index in (True, -1, 3, '0'):
                with self.assertRaisesRegex(spool.Hold, 'REQUEST_INDEX'):
                    exchange.send_one(self.plan, self.raw, self.ack, fixture, index=index)
            self.assertEqual(fixture.total_posts, 0)
            empty = planning.build_plan(encoding.fixture_snapshot(),
                                       self._all_ack(encoding.fixture_snapshot()))
            with self.assertRaisesRegex(spool.Hold, 'REQUEST_INDEX'):
                exchange.send_one(empty, encoding.fixture_snapshot(), self._all_ack(encoding.fixture_snapshot()), fixture)

    def _all_ack(self, raw):
        import v0145e_atomic_handoff as handoff
        import v0145f_delivery_ack as delivery
        source = handoff.decode_snapshot(raw)
        pairs = tuple((json.loads(payload)['event_id'], delivery.payload_hash(payload)) for payload in source.events)
        return delivery.encode_state(delivery.AckState(source.scope, pairs))

    def test_unopened_closed_foreign_fixture_and_reenter_hold(self):
        fixture = self.fixture()
        with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('no live fixture')):
            for value in (None, {}, ('127.0.0.1', 3100), fixture):
                with self.assertRaises(spool.Hold):
                    exchange.send_one(self.plan, self.raw, self.ack, value)
        with fixture:
            pass
        self.assert_closed(fixture)
        with self.assertRaises(spool.Hold):
            exchange.send_one(self.plan, self.raw, self.ack, fixture)
        with self.assertRaisesRegex(spool.Hold, 'FIXTURE_SINGLE_USE'):
            fixture.__enter__()

    def test_fixture_rejects_bad_response_options_before_binding(self):
        replies = (exchange.Reply(status=True), exchange.Reply(status=99),
                   exchange.Reply(body=bytearray(b'x')), exchange.Reply(body=b'x' * 514),
                   exchange.Reply(mode='unknown'), exchange.Reply(headers=[('Content-Length', '0')]),
                   exchange.Reply(headers=(('Location', 'value\r\ninjection'),)),
                   exchange.Reply(headers=(('X-Arbitrary', 'value'),)))
        with mock.patch.object(socket, 'socket', side_effect=AssertionError('binding')):
            for reply in replies:
                with self.assertRaises(spool.Hold):
                    self.fixture(reply)

    def test_fixture_bad_body_hash_or_mutability_cannot_bind(self):
        from dataclasses import replace
        first = self.plan.requests[0]
        with mock.patch.object(socket, 'socket', side_effect=AssertionError('binding')):
            for request in (None, replace(first, sha256='b' * 64), replace(first, body=bytearray(first.body))):
                with self.assertRaises(spool.Hold):
                    exchange.LoopbackFixture(request)

    def test_200_and_blocked_260_never_count_as_success_or_retry(self):
        for status in (200, 260):
            with self.subTest(status=status):
                with self.fixture(exchange.Reply(status=status)) as fixture:
                    with self.assertRaisesRegex(spool.Hold, 'CLIENT_RESPONSE_REJECTED'):
                        exchange.send_one(self.plan, self.raw, self.ack, fixture)
                    self.assertEqual(fixture.total_posts, 1)
                    with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('retry')):
                        with self.assertRaises(spool.Hold):
                            exchange.send_one(self.plan, self.raw, self.ack, fixture)
                self.assert_closed(fixture)

    def test_redirect_429_and_500_are_not_followed_or_retried(self):
        for reply in (exchange.Reply(status=301, headers=(('Location', 'http://invalid.test/'),)),
                      exchange.Reply(status=429), exchange.Reply(status=500)):
            with self.fixture(reply) as fixture:
                with self.assertRaisesRegex(spool.Hold, 'CLIENT_RESPONSE_REJECTED'):
                    exchange.send_one(self.plan, self.raw, self.ack, fixture)
                self.assertEqual(fixture.total_posts, 1)

    def test_204_nonempty_duplicate_length_and_transfer_encoding_hold(self):
        for reply in (exchange.Reply(body=b'unexpected'),
                      exchange.Reply(body=b'unexpected', headers=(('Content-Length', '0'),)),
                      exchange.Reply(headers=(('Content-Length', '0'), ('Content-Length', '0'))),
                      exchange.Reply(headers=(('Transfer-Encoding', 'chunked'),))):
            with self.fixture(reply) as fixture:
                with self.assertRaises(spool.Hold):
                    exchange.send_one(self.plan, self.raw, self.ack, fixture)
                self.assertEqual(fixture.total_posts, 1)

    def test_oversize_error_response_is_not_printed_or_accepted(self):
        with self.fixture(exchange.Reply(status=500, body=b'x' * (exchange.MAX_RESPONSE_BYTES + 1))) as fixture, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(spool.Hold):
                exchange.send_one(self.plan, self.raw, self.ack, fixture)
        self.assertEqual(output.getvalue(), '')

    def test_disconnect_and_malformed_status_withhold_success(self):
        for mode in ('disconnect', 'malformed'):
            with self.fixture(exchange.Reply(mode=mode)) as fixture:
                with self.assertRaises(spool.Hold):
                    exchange.send_one(self.plan, self.raw, self.ack, fixture)
                self.assertEqual(fixture.total_posts, 1)

    def test_real_stalled_peer_deadline_kills_worker_and_closes_fixture(self):
        original = subprocess.Popen
        children = []
        def track(*args, **kwargs):
            child = original(*args, **kwargs)
            children.append(child)
            return child
        with self.fixture(exchange.Reply(mode='stall')) as fixture:
            with mock.patch.object(exchange, 'CLIENT_SECONDS', 0.75), \
                 mock.patch.object(subprocess, 'Popen', side_effect=track):
                with self.assertRaisesRegex(spool.Hold, 'CLIENT_DEADLINE_EXPIRED'):
                    exchange.send_one(self.plan, self.raw, self.ack, fixture)
            self.assertEqual(len(children), 1)
            self.assertIsNotNone(children[0].poll())
            self.assertLessEqual(fixture.total_posts, 1)
        self.assert_closed(fixture)

    def test_private_fixture_rejects_wrong_capability_and_wrong_body(self):
        import http.client
        for token, body in (('wrong', self.plan.requests[0].body), (None, b'wrong body')):
            with self.fixture() as fixture:
                connection = http.client.HTTPConnection(*fixture.server.socket.getsockname(), timeout=1)
                try:
                    connection.request('POST', encoding.PATH, body=body,
                                       headers={'Content-Type': encoding.CONTENT_TYPE,
                                                'X-HCC-Lab-Capability': fixture.token if token is None else token})
                    response = connection.getresponse()
                    self.assertEqual(response.status, 403)
                    response.read()
                finally:
                    connection.close()
                self.assertEqual(fixture.seen, [])

    def test_no_validated_report_without_observed_request_can_pass(self):
        with self.fixture() as fixture, mock.patch.object(exchange, '_run_worker', return_value=None):
            with self.assertRaisesRegex(spool.Hold, 'FIXTURE_OBSERVATION_MISMATCH'):
                exchange.send_one(self.plan, self.raw, self.ack, fixture)
            self.assertEqual(fixture.total_posts, 0)

    def test_proxy_environment_cannot_redirect_owned_exchange(self):
        with self.fixture() as fixture, \
             mock.patch.dict(os.environ, {'HTTP_PROXY': 'http://invalid.test:9', 'HTTPS_PROXY': 'http://invalid.test:9',
                                          'ALL_PROXY': 'http://invalid.test:9', 'NO_PROXY': ''}):
            self.assertEqual(exchange.send_one(self.plan, self.raw, self.ack, fixture),
                             'PASS_OWNED_FIXTURE_EXCHANGE_ONLY')
            self.assertEqual(fixture.seen, [self.plan.requests[0].body])

    def test_lab_cleans_up_and_prints_no_bodies_ids_scope_or_capability(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            exchange.run_lab()
        text = output.getvalue()
        self.assertIn('V0145J_RESULT=PASS_OWNED_LOOPBACK_FIXTURE_ONLY', text)
        self.assertIn('FIXTURE_LISTENER=CLOSED', text)
        self.assertIn('ACK_OR_CHECKPOINT_ADVANCE=NO', text)
        self.assertNotIn(self.plan.scope, text)
        for request in self.plan.requests:
            for event_id in request.event_ids:
                self.assertNotIn(event_id, text)


if __name__ == '__main__':
    unittest.main()
