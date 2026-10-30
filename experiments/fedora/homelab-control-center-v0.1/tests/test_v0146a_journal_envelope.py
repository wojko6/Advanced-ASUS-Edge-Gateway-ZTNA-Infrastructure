"""Supplied-metadata adapter tests; no live journal, key, file or transport."""
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
import v0146a_journal_envelope as adapter


def raw(*rows):
    return b''.join(identity.canonical(row) + b'\n' for row in rows)


class SuppliedJournalAdapter(unittest.TestCase):
    def adapt(self, data, **kwargs):
        return adapter.adapt_snapshot(data, expected_uid=kwargs.get('expected_uid', 1000),
                                      key=kwargs.get('key', identity.SYNTHETIC_KEY))

    def events(self, result):
        return [json.loads(event) for event in handoff.decode_snapshot(result.snapshot).events]

    def test_fixture_bridges_to_canonical_e_without_legacy_identity_loss(self):
        result = self.adapt(adapter.fixture_inputs())
        self.assertEqual((result.input_records, result.classified_records, result.ignored_records,
                          result.accepted_events, result.duplicate_events), (5, 4, 1, 3, 1))
        events = self.events(result)
        self.assertEqual(len({event['event_id'] for event in events}), 3)
        self.assertTrue(all(event['schema'] == identity.SCHEMA for event in events))
        with self.assertRaises(spool.Hold):
            spool.normalize_sanitized_jsonl(result.snapshot)

    def test_distinct_same_time_kind_cursors_survive_with_exact_microseconds(self):
        result = self.adapt(raw(adapter.fixture_record('synthetic-001'), adapter.fixture_record('synthetic-002')))
        events = self.events(result)
        self.assertEqual(result.accepted_events, 2)
        self.assertEqual(len({event['event_id'] for event in events}), 2)
        self.assertEqual({event['time'] for event in events}, {'2026-10-30T09:00:00.000001Z'})

    def test_same_cursor_on_different_boot_has_distinct_identity(self):
        one = adapter.fixture_record()
        two = dict(one, _BOOT_ID='b' * 32)
        self.assertEqual(self.adapt(raw(one, two)).accepted_events, 2)

    def test_changed_time_or_kind_for_one_address_holds_whole_batch(self):
        one = adapter.fixture_record()
        for update in ({'__REALTIME_TIMESTAMP': '1793350800000002'},
                       {'MESSAGE': 'ssh: Permission denied'}):
            with self.subTest(update=update), self.assertRaisesRegex(spool.Hold, 'SAME_ADDRESS_CHANGED'):
                self.adapt(raw(one, dict(one, **update)))

    def test_same_address_changed_message_holds_even_when_hint_does_not_change(self):
        for first, second in (('ssh: timeout host-a', 'ssh: timeout host-b'),
                              ('collector finished', 'collector started')):
            row = adapter.fixture_record(message=first)
            with self.subTest(first=first), self.assertRaisesRegex(spool.Hold, 'SAME_ADDRESS_CHANGED'):
                self.adapt(raw(row, dict(row, MESSAGE=second)))

    def test_ignored_to_classified_address_change_cannot_silently_promote(self):
        one = adapter.fixture_record(message='collector finished')
        two = dict(one, MESSAGE='ssh: timeout')
        for rows in ((one, two), (two, one)):
            with self.subTest(rows=rows), self.assertRaisesRegex(spool.Hold, 'SAME_ADDRESS_CHANGED'):
                self.adapt(raw(*rows))

    def test_repeated_call_is_stateless_and_repeats_the_same_output(self):
        first = self.adapt(adapter.fixture_inputs())
        second = self.adapt(adapter.fixture_inputs())
        self.assertEqual(first, second)
        self.assertEqual(first.duplicate_events, 1)

    def test_unknown_messages_return_no_snapshot_after_metadata_validation(self):
        row = adapter.fixture_record(message='collector finished')
        with mock.patch.object(handoff, 'encode_snapshot', side_effect=AssertionError('snapshot')):
            result = self.adapt(raw(row))
        self.assertIsNone(result.snapshot)
        self.assertEqual((result.input_records, result.ignored_records, result.accepted_events), (1, 1, 0))

    def test_manager_exit_text_is_not_attributed_from_stdout(self):
        row = adapter.fixture_record(message=identity.UNIT + ': Main process exited, code=exited, status=255/EXCEPTION')
        self.assertEqual(self.adapt(raw(row)).ignored_records, 1)
        manager = dict(row, _SYSTEMD_USER_UNIT='init.scope', USER_UNIT=identity.UNIT)
        with self.assertRaises(spool.Hold):
            self.adapt(raw(manager))

    def test_only_narrow_text_hints_are_classified(self):
        for message, expected in (('ssh: Permission denied', 'SSH_AUTH_FAILURE'),
                                  ('curl: (28) Operation timed out', 'HTTP_IMPORT_TIMEOUT'),
                                  ('unrelated timed out', None), ('SSH: timeout', 'SSH_TIMEOUT')):
            with self.subTest(message=message):
                result = self.adapt(raw(adapter.fixture_record(message=message)))
                self.assertEqual(None if result.snapshot is None else self.events(result)[0]['kind'], expected)

    def test_wrong_declared_origin_is_rejected_even_with_matching_user_hints(self):
        for field, value in (('_SYSTEMD_USER_UNIT', 'other.service'), ('_UID', '1001'),
                             ('_SYSTEMD_OWNER_UID', '1001'), ('_TRANSPORT', 'journal'),
                             ('_TRANSPORT', 'syslog')):
            row = dict(adapter.fixture_record(), USER_UNIT=identity.UNIT, SYSLOG_IDENTIFIER=identity.UNIT)
            row[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(spool.Hold):
                self.adapt(raw(row))

    def test_required_fields_are_exact_strings_not_missing_arrays_or_null(self):
        for field in adapter.REQUIRED:
            missing = adapter.fixture_record()
            del missing[field]
            with self.subTest(field=field, missing=True), self.assertRaises(spool.Hold):
                self.adapt(raw(missing))
            for value in (None, [], ['1000'], 1000, True):
                row = adapter.fixture_record()
                row[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(spool.Hold):
                    self.adapt(raw(row))

    def test_expected_uid_has_strict_nonroot_integer_bounds(self):
        for uid in (True, 0, -1, 1000.0, '1000', None, adapter.MAX_UID + 1):
            with self.subTest(uid=uid), self.assertRaises(spool.Hold):
                self.adapt(adapter.fixture_inputs(), expected_uid=uid)
        for uid in (1, adapter.MAX_UID):
            row = dict(adapter.fixture_record(), _UID=str(uid), _SYSTEMD_OWNER_UID=str(uid))
            self.assertEqual(self.adapt(raw(row), expected_uid=uid).accepted_events, 1)

    def test_key_has_exact_bytes_and_size(self):
        for key in (None, b'', b'x' * 31, b'x' * 33, bytearray(32)):
            with self.subTest(key_type=type(key).__name__), self.assertRaises(spool.Hold):
                self.adapt(adapter.fixture_inputs(), key=key)

    def test_time_shape_and_range_are_strict_on_ignored_records_too(self):
        for stamp in ('0', '01793350800000001', '1793350800000001.0', '١٧٩٣٣٥٠٨٠٠٠٠٠٠٠١',
                      str(identity.MIN_US - 1), str(identity.MAX_US + 1)):
            row = dict(adapter.fixture_record(message='collector finished'), __REALTIME_TIMESTAMP=stamp)
            with self.subTest(stamp=stamp), self.assertRaises(spool.Hold):
                self.adapt(raw(row))

    def test_time_order_checks_unclassified_rows(self):
        one = adapter.fixture_record(stamp=1793350800000002)
        two = adapter.fixture_record('synthetic-other', 1793350800000001, 'collector finished')
        with self.assertRaisesRegex(spool.Hold, 'TIME_ORDER'):
            self.adapt(raw(one, two))

    def test_boot_and_cursor_shape_is_bounded_without_reinterpreting_cursor(self):
        for field, value in (('_BOOT_ID', 'A' * 32), ('_BOOT_ID', 'b' * 31),
                             ('__CURSOR', ''), ('__CURSOR', 'c' * 513), ('__CURSOR', 'line\nbreak')):
            row = adapter.fixture_record()
            row[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(spool.Hold):
                self.adapt(raw(row))

    def test_line_break_metadata_is_rejected_even_if_empty_or_eof(self):
        for value in ('nul', 'line-max', 'eof', 'pid-change', '', None):
            with self.subTest(value=value), self.assertRaises(spool.Hold):
                self.adapt(raw(dict(adapter.fixture_record(), _LINE_BREAK=value)))

    def test_message_controls_and_utf8_byte_limit(self):
        for message in ('', 'ssh:\ntimeout', 'ssh:\rtimeout', 'ssh:\x00timeout', 'ssh:\ttimeout',
                        'x' * 4097, 'é' * 2049):
            with self.subTest(size=len(message)), self.assertRaises(spool.Hold):
                self.adapt(raw(adapter.fixture_record(message=message)))
        self.assertEqual(self.adapt(raw(adapter.fixture_record(message='é' * 2048))).ignored_records, 1)

    def test_lone_surrogate_is_a_controlled_hold(self):
        with self.assertRaises(spool.Hold):
            self.adapt(raw(adapter.fixture_record(message='ssh: timeout \ud800')))

    def test_private_extra_metadata_is_ignored_without_affecting_snapshot(self):
        one = adapter.fixture_record()
        two = dict(one, _HOSTNAME='other.private.example', PRIVATE_FIELD=[None, {'SECRET': 'private-token'}])
        first, second = self.adapt(raw(one)), self.adapt(raw(two))
        self.assertEqual(first.snapshot, second.snapshot)
        for token in (b'private.example', b'private-token', b'synthetic-cursor-', b'"MESSAGE"', b'"_UID"'):
            self.assertNotIn(token, second.snapshot)

    def test_consistent_forged_fields_are_not_authenticated_by_this_model(self):
        forged = {'__CURSOR': 'made-up-cursor', '__REALTIME_TIMESTAMP': '1793350800000001',
                  '_BOOT_ID': '0' * 32, '_SYSTEMD_USER_UNIT': identity.UNIT,
                  '_UID': '1000', '_SYSTEMD_OWNER_UID': '1000', '_TRANSPORT': 'stdout',
                  'MESSAGE': 'ssh: timeout'}
        # No journal descriptor, authenticated transport or independent proof.
        self.assertEqual(self.adapt(raw(forged)).accepted_events, 1)

    def test_malformed_json_duplicates_nonfinite_and_wrong_top_level_hold(self):
        row = raw(adapter.fixture_record())
        for data in (b'', b'\n', b'{}', b'[]', b'null', b'1', b'not-json', b'\xff',
                     row.replace(b'"MESSAGE":', b'"MESSAGE":"duplicate","MESSAGE":'),
                     row.replace(b'"_HOSTNAME":"private.example"', b'"_HOSTNAME":NaN')):
            with self.subTest(data_prefix=data[:20]), self.assertRaises(spool.Hold):
                self.adapt(data)

    def test_input_bytes_row_bytes_and_field_budgets_hold_before_output(self):
        for data in (b'x' * (adapter.MAX_BYTES + 1), raw(dict(adapter.fixture_record(), EXTRA='x' * 17000)),
                     raw(dict(adapter.fixture_record(), **{f'EXTRA_{n}': 'x' for n in range(65)}))):
            with self.subTest(size=len(data)), self.assertRaises(spool.Hold):
                self.adapt(data)
        for field in ('lowercase', 'X' * 65):
            with self.subTest(field=field), self.assertRaises(spool.Hold):
                self.adapt(raw(dict(adapter.fixture_record(), **{field: 'x'})))

    def test_maximum_rows_retained_and_one_extra_is_rejected(self):
        rows = [adapter.fixture_record(f'synthetic-bound-{n:03d}') for n in range(adapter.MAX_ROWS)]
        self.assertEqual(self.adapt(raw(*rows)).accepted_events, adapter.MAX_ROWS)
        with self.assertRaisesRegex(spool.Hold, 'ROW_LIMIT'):
            self.adapt(raw(*rows, adapter.fixture_record('synthetic-extra')))

    def test_downstream_identity_budget_has_no_partial_snapshot(self):
        rows = [adapter.fixture_record('c' * 500 + str(n).zfill(12)) for n in range(adapter.MAX_ROWS)]
        with mock.patch.object(handoff, 'encode_snapshot', side_effect=AssertionError('partial snapshot')):
            with self.assertRaises(spool.Hold):
                self.adapt(raw(*rows))

    def test_invalid_late_row_refuses_whole_batch_without_output(self):
        rows = [adapter.fixture_record(), dict(adapter.fixture_record('synthetic-last'), _UID='1001')]
        with mock.patch.object(handoff, 'encode_snapshot', side_effect=AssertionError('partial snapshot')):
            with self.assertRaises(spool.Hold):
                self.adapt(raw(*rows))
        self.assertEqual(self.adapt(raw(rows[0])).accepted_events, 1)

    def test_selftest_and_lab_are_pure_and_print_no_raw_metadata(self):
        with mock.patch('builtins.open', side_effect=AssertionError('file')), \
             mock.patch.object(os, 'open', side_effect=AssertionError('os.open')), \
             mock.patch.object(socket, 'socket', side_effect=AssertionError('network')), \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('subprocess')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            adapter.self_test()
            adapter.run_lab()
        text = output.getvalue()
        self.assertIn('V0146A_RESULT=PASS_SUPPLIED_METADATA_MODEL_ONLY', text)
        self.assertIn('SOURCE_PROVENANCE=UNVERIFIED_SUPPLIED_BYTES', text)
        for token in ('private.example', 'synthetic-cursor-', identity.scope_for(identity.SYNTHETIC_KEY), 'MESSAGE'):
            self.assertNotIn(token, text)

    def test_cli_rejects_stdin_paths_urls_uids_and_ambiguous_modes(self):
        for args in ([], ['--lab', '--self-test'], ['--stdin'], ['--input', '/tmp/synthetic'],
                     ['--lab', '--uid', '1000'], ['--url', 'http://invalid.test/']):
            with mock.patch.object(sys, 'argv', ['v0146a.py', *args]), \
                 mock.patch.object(adapter, 'self_test', side_effect=AssertionError('action')), \
                 mock.patch.object(adapter, 'run_lab', side_effect=AssertionError('action')), \
                 contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    adapter.main()
            self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
