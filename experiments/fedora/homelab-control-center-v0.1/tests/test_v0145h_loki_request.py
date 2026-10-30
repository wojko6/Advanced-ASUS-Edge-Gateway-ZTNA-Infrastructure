"""Pure synthetic request encoding; no HTTP or Loki acceptance claim."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import v0145a_segment_spool as spool
import v0145d_event_identity as identity
import v0145e_atomic_handoff as handoff
import v0145h_loki_request as encoding

KEY = identity.SYNTHETIC_KEY


def snapshot(raw, key=KEY):
    events = identity.normalized_events(raw, key)
    return handoff.encode_snapshot(identity.scope_for(key),
                                   sorted(events, key=lambda payload: json.loads(payload)['event_id']))


def stream(request):
    return json.loads(request.body)['streams'][0]


class RequestEncoding(unittest.TestCase):
    def setUp(self):
        self.raw = encoding.fixture_snapshot()
        self.source = handoff.decode_snapshot(self.raw)

    def mutated(self, events):
        return handoff.encode_snapshot(self.source.scope, [identity.canonical(event) for event in events])

    def test_documented_json_shape_one_stream_two_string_values(self):
        request = encoding.build_request(self.raw)
        body = json.loads(request.body)
        self.assertEqual(set(body), {'streams'})
        self.assertEqual(len(body['streams']), 1)
        item = body['streams'][0]
        self.assertEqual(set(item), {'stream', 'values'})
        self.assertEqual(item['stream'], {'component': 'dns-guard-collector', 'source': 'synthetic-unit-envelope'})
        self.assertEqual(len(item['values']), 3)
        for value in item['values']:
            self.assertEqual(len(value), 2)
            self.assertTrue(all(type(part) is str for part in value))
        self.assertEqual(encoding.PATH, '/loki/api/v1/push')
        self.assertEqual(encoding.CONTENT_TYPE, 'application/json')

    def test_integer_epoch_roundtrip_at_boundaries_leap_day_and_large_values(self):
        vectors = (identity.MIN_US, identity.MIN_US + 1, 1709164800000000,
                   1793350800123456, 1793350800123457, identity.MAX_US - 1, identity.MAX_US)
        for stamp in vectors:
            raw = snapshot(identity.envelope('synthetic-time-vector', stamp))
            value = stream(encoding.build_request(raw))['values'][0][0]
            self.assertEqual(value, str(stamp * 1000))
            self.assertTrue(value.isascii() and value.isdecimal())

    def test_time_helper_rejects_invalid_calendar_zone_precision_range_and_types(self):
        invalid = (None, True, 1793350800, b'2026-10-30T00:00:00.000000Z',
                   '2026-02-30T00:00:00.000000Z', '2026-10-30T00:00:60.000000Z',
                   '2026-10-30T00:00:00.000Z', '2026-10-30T00:00:00.000000001Z',
                   '2026-10-30T00:00:00.000000+00:00', '2026-10-30T00:00:00.000000',
                   '1999-12-31T23:59:59.999999Z', '2101-01-01T00:00:00.000000Z')
        for value in invalid:
            with self.assertRaises(spool.Hold):
                encoding.nanoseconds(value)

    def test_one_microsecond_difference_is_exactly_one_thousand_nanoseconds(self):
        stamp = 1793350800123456
        raw = snapshot(identity.envelope('synthetic-first', stamp) + identity.envelope('synthetic-next', stamp + 1))
        request = encoding.build_request(raw)
        values = stream(request)['values']
        self.assertEqual([value[0] for value in values], [str(stamp * 1000), str((stamp + 1) * 1000)])
        self.assertEqual(len(set(request.event_ids)), 2)

    def test_same_time_and_kind_preserves_distinct_record_ids(self):
        raw = snapshot(identity.envelope('synthetic-one') + identity.envelope('synthetic-two'))
        request = encoding.build_request(raw)
        values = stream(request)['values']
        self.assertEqual(values[0][0], values[1][0])
        self.assertNotEqual(values[0][1], values[1][1])
        self.assertEqual(request.event_ids, tuple(sorted(request.event_ids)))
        self.assertEqual(len(request.event_ids), 2)

    def test_request_time_order_is_independent_of_input_canonical_id_order(self):
        events = [json.loads(payload) for payload in self.source.events]
        for event, value in zip(events, ('2026-10-30T01:00:02.000000Z',
                                        '2026-10-30T01:00:01.000000Z', '2026-10-30T01:00:00.000000Z')):
            event['time'] = value
        raw = self.mutated(events)
        request = encoding.build_request(raw)
        self.assertEqual(request.event_ids, tuple(event['event_id'] for event in reversed(events)))
        self.assertEqual(handoff.decode_snapshot(raw).events, tuple(identity.canonical(event) for event in events))

    def test_full_canonical_event_lines_survive_json_string_escaping(self):
        request = encoding.build_request(self.raw)
        original = {json.loads(payload)['event_id']: payload for payload in self.source.events}
        for event_id, value in zip(request.event_ids, stream(request)['values']):
            self.assertEqual(value[1].encode('ascii'), original[event_id])
            self.assertEqual(json.loads(value[1])['scope'], self.source.scope)

    def test_labels_stay_fixed_across_kinds_keys_ids_and_time(self):
        for key in (KEY, bytes(reversed(KEY))):
            raw = b''.join(identity.envelope('synthetic-kind-' + str(index), kind=kind)
                           for index, kind in enumerate(sorted(spool.ALLOWED_KINDS)))
            request = encoding.build_request(snapshot(raw, key))
            labels = stream(request)['stream']
            self.assertEqual(labels, {'component': 'dns-guard-collector', 'source': 'synthetic-unit-envelope'})
            self.assertTrue(set(labels).isdisjoint({'event_id', 'scope', 'time', 'kind', 'boot', 'cursor'}))

    def test_repeat_is_deterministic_and_checksum_binds_exact_body(self):
        first = encoding.build_request(self.raw)
        self.assertEqual(encoding.build_request(self.raw), first)
        self.assertEqual(first.sha256, hashlib.sha256(first.body).hexdigest())
        self.assertFalse(first.body.endswith(b'\n'))
        self.assertEqual(first.scope, self.source.scope)

    def test_payload_change_changes_body_and_request_checksum(self):
        first = encoding.build_request(self.raw)
        events = [json.loads(payload) for payload in self.source.events]
        events[0]['kind'] = 'HTTP_IMPORT_TIMEOUT'
        changed = encoding.build_request(self.mutated(events))
        self.assertNotEqual(changed.body, first.body)
        self.assertNotEqual(changed.sha256, first.sha256)
        self.assertEqual(set(changed.event_ids), set(first.event_ids))

    def test_sixteen_records_fit_and_seventeen_are_not_silently_truncated(self):
        raw = b''.join(identity.envelope(f'synthetic-many-{n:04d}') for n in range(17))
        request = encoding.build_request(snapshot(b'\n'.join(raw.splitlines()[:16]) + b'\n'))
        self.assertEqual(len(request.event_ids), 16)
        with self.assertRaisesRegex(spool.Hold, 'REQUEST_EVENT_LIMIT'):
            encoding.build_request(snapshot(raw))

    def test_body_byte_limit_accepts_exact_boundary_and_rejects_one_byte_less(self):
        expected = encoding.build_request(self.raw)
        with mock.patch.object(encoding, 'MAX_BODY_BYTES', len(expected.body)):
            self.assertEqual(encoding.build_request(self.raw), expected)
        with mock.patch.object(encoding, 'MAX_BODY_BYTES', len(expected.body) - 1):
            with self.assertRaisesRegex(spool.Hold, 'REQUEST_BYTES_LIMIT'):
                encoding.build_request(self.raw)

    def test_source_input_is_exact_bounded_bytes_not_paths_or_objects(self):
        for value in (None, '', '/tmp/synthetic.json', {}, bytearray(self.raw), memoryview(self.raw), b''):
            with self.assertRaises(spool.Hold):
                encoding.build_request(value)
        with self.assertRaisesRegex(spool.Hold, 'HANDOFF_BYTES_LIMIT'):
            encoding.build_request(b'x' * (handoff.MAX_SNAPSHOT_BYTES + 1))

    def test_source_corruption_digest_is_verified_before_formatting(self):
        obj = json.loads(self.raw)
        obj['digest'] = 'a' * 64
        with self.assertRaisesRegex(spool.Hold, 'HANDOFF_DIGEST_MISMATCH'):
            encoding.build_request(identity.canonical(obj) + b'\n')

    def test_noncanonical_or_duplicate_key_source_is_not_normalized_away(self):
        for raw in (json.dumps(json.loads(self.raw), indent=2).encode(),
                    self.raw.replace(b'"scope":', b'"scope":"duplicate","scope":', 1)):
            with self.assertRaises(spool.Hold):
                encoding.build_request(raw)

    def test_late_invalid_record_is_checked_before_request_count_limit(self):
        raw = b''.join(identity.envelope(f'synthetic-late-{n:04d}') for n in range(17))
        source = handoff.decode_snapshot(snapshot(raw))
        events = [json.loads(payload) for payload in source.events]
        events[-1]['MESSAGE'] = 'synthetic-private-tail'
        invalid = handoff.encode_snapshot(source.scope, [identity.canonical(event) for event in events])
        with self.assertRaisesRegex(spool.Hold, 'HANDOFF_EVENT_SCHEMA'):
            encoding.build_request(invalid)

    def test_legacy_sanitized_rows_and_raw_envelopes_are_not_adapted(self):
        legacy = identity.canonical({'time': '2026-10-30T00:00:00.000Z', 'kind': 'SSH_TIMEOUT',
                                     'component': spool.EXPECTED_COMPONENT, 'source': spool.EXPECTED_SOURCE}) + b'\n'
        for raw in (legacy, identity.envelope('synthetic-raw-cursor')):
            with self.assertRaises(spool.Hold):
                encoding.build_request(raw)

    def test_forbidden_fields_hold_without_echoing_source_content(self):
        for name in ('MESSAGE', 'boot', 'cursor', 'time_us', 'unit', 'key'):
            events = [json.loads(payload) for payload in self.source.events]
            events[-1][name] = 'synthetic-private-marker'
            with self.assertRaises(spool.Hold) as caught:
                encoding.build_request(self.mutated(events))
            self.assertNotIn('synthetic-private-marker', str(caught.exception))

    def test_component_source_schema_and_kind_cannot_become_arbitrary_labels(self):
        for name, value in (('component', 'other'), ('source', 'real-journal'),
                            ('kind', 'OTHER'), ('schema', 'other'), ('time', 1793350800)):
            events = [json.loads(payload) for payload in self.source.events]
            events[0][name] = value
            with self.assertRaises(spool.Hold):
                encoding.build_request(self.mutated(events))

    def test_unsorted_or_duplicate_input_ids_hold_before_request_sorting(self):
        for payloads in (tuple(reversed(self.source.events)), (self.source.events[0], self.source.events[0])):
            with self.assertRaisesRegex(spool.Hold, 'HANDOFF_ID_ORDER_OR_DUPLICATE'):
                encoding.build_request(handoff.encode_snapshot(self.source.scope, payloads))

    def test_mixed_key_scopes_are_not_combined_into_one_request(self):
        events = [json.loads(payload) for payload in self.source.events]
        events[-1]['scope'] = identity.scope_for(bytes(reversed(KEY)))
        with self.assertRaisesRegex(spool.Hold, 'HANDOFF_EVENT_VALUE'):
            encoding.build_request(self.mutated(events))

    def test_forged_valid_snapshot_can_encode_and_is_not_source_authentication(self):
        events = [dict(json.loads(self.source.events[0]), event_id='a' * 64)]
        request = encoding.build_request(self.mutated(events))
        self.assertEqual(request.event_ids, ('a' * 64,))
        self.assertEqual(json.loads(stream(request)['values'][0][1])['event_id'], 'a' * 64)
        self.assertNotIn('event_id', stream(request)['stream'])

    def test_formatter_does_not_use_host_clock(self):
        with mock.patch.object(time, 'time', side_effect=AssertionError('clock')), \
             mock.patch.object(time, 'time_ns', side_effect=AssertionError('clock')):
            request = encoding.build_request(self.raw)
        self.assertEqual(stream(request)['values'][-1][0], '1793350800123457000')

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
        self.assertNotIn(self.source.scope, text)
        self.assertNotIn('synthetic-cursor-', text)
        for payload in self.source.events:
            self.assertNotIn(json.loads(payload)['event_id'], text)
            self.assertNotIn(payload.decode('ascii'), text)

    def test_self_test_is_memory_only_and_does_not_print_record_data(self):
        self.guarded_cli(encoding.self_test, 'V0145H_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')

    def test_lab_is_memory_only_and_does_not_print_record_data(self):
        self.guarded_cli(encoding.run_lab, 'V0145H_RESULT=PASS_OFFLINE_REQUEST_ENCODING_ONLY')

    def test_cli_rejects_paths_urls_serving_and_ambiguous_modes(self):
        for args in ([], ['--lab', '--self-test'], ['--lab', '--input', 'synthetic.json'],
                     ['--lab', '--url', 'http://invalid.test/'], ['--serve']):
            with mock.patch.object(sys, 'argv', ['v0145h_loki_request.py', *args]), \
                 mock.patch.object(encoding, 'self_test', side_effect=AssertionError('unexpected action')), \
                 mock.patch.object(encoding, 'run_lab', side_effect=AssertionError('unexpected action')), \
                 contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    encoding.main()
            self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
