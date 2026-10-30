"""Synthetic in-memory identity/consistency tests, no actual journal source."""
import contextlib
from datetime import datetime, timezone
import hashlib
import hmac
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import v0145a_segment_spool as spool
import v0145d_event_identity as identity


KEY = bytes(range(32))
STAMP = 1793350800000000


def row(cursor='synthetic-cursor-001', stamp=STAMP, *, boot='a'*32, kind='SSH_TIMEOUT'):
    return identity.envelope(cursor, stamp, boot=boot, kind=kind)


def changed(**updates):
    obj = json.loads(row())
    obj.update(updates)
    return identity.canonical(obj) + b'\n'


class EnvelopeContract(unittest.TestCase):
    def reject(self, raw, key=KEY):
        with self.assertRaises(spool.Hold):
            identity.normalized_events(raw, key)

    def test_exact_output_schema_and_fixed_source(self):
        obj = json.loads(identity.normalized_events(row(), KEY)[0])
        self.assertEqual(set(obj), {'schema','scope','event_id','time','kind','component','source'})
        self.assertEqual(obj['source'], 'synthetic-unit-envelope')
        self.assertEqual(obj['component'], 'dns-guard-collector')
        self.assertEqual(obj['schema'], identity.SCHEMA)
        self.assertEqual(len(obj['event_id']), 64)
        self.assertEqual(len(obj['scope']), 64)

    def test_integer_microseconds_do_not_collapse(self):
        events = identity.normalized_events(row('cursor-1', STAMP+1)+row('cursor-2', STAMP+2), KEY)
        times = [json.loads(event)['time'] for event in events]
        self.assertTrue(times[0].endswith('.000001Z'))
        self.assertTrue(times[1].endswith('.000002Z'))
        self.assertNotEqual(times[0], times[1])

    def test_same_time_same_kind_different_cursor_preserves_two_ids(self):
        events = identity.normalized_events(row('cursor-1')+row('cursor-2'), KEY)
        self.assertEqual(len(events), 2)
        self.assertNotEqual(json.loads(events[0])['event_id'], json.loads(events[1])['event_id'])

    def test_same_cursor_different_boot_is_distinct(self):
        events = identity.normalized_events(row()+row(boot='b'*32), KEY)
        self.assertNotEqual(json.loads(events[0])['event_id'], json.loads(events[1])['event_id'])

    def test_id_and_scope_are_stable_across_json_encoding(self):
        obj = json.loads(row())
        alternate = json.dumps(dict(reversed(list(obj.items()))), indent=None).encode() + b'\n'
        self.assertEqual(identity.normalized_events(row(), KEY), identity.normalized_events(alternate, KEY))

    def test_known_domain_separated_hmac_identity(self):
        # Independent construction of the exact identity wire message.
        message = ('{"boot":"'+'a'*32+'","cursor":"synthetic-cursor-001",'
                   '"domain":"hcc-v0145d/synthetic-identity/1",'
                   '"unit":"dns-guard-monitoring.service"}').encode()
        expected = hmac.new(KEY, message, hashlib.sha256).hexdigest()
        self.assertEqual(json.loads(identity.normalized_events(row(), KEY)[0])['event_id'], expected)
        self.assertNotEqual(expected, hmac.new(KEY, b'hcc-v0145d/synthetic-scope/1', hashlib.sha256).hexdigest())

    def test_utc_range_edges_and_leap_day(self):
        for stamp, expected in ((identity.MIN_US,'2000-01-01T00:00:00.000000Z'),
                                (identity.MAX_US,'2100-12-31T23:59:59.999999Z')):
            with self.subTest(stamp=stamp):
                event = identity.normalized_events(row(stamp=stamp), KEY)[0]
                self.assertEqual(json.loads(event)['time'], expected)
        for stamp in (identity.MIN_US-1, identity.MAX_US+1):
            self.reject(row(stamp=stamp))
        stamp = int(datetime(2024,2,29,tzinfo=timezone.utc).timestamp())*1000000+123456
        self.assertEqual(json.loads(identity.normalized_events(row(stamp=stamp), KEY)[0])['time'],
                         '2024-02-29T00:00:00.123456Z')

    def test_reject_bad_key_type_or_length(self):
        for key in (None, 'x'*32, b'x'*31, b'x'*33, bytearray(32), True):
            with self.subTest(type=type(key).__name__):
                self.reject(row(), key)

    def test_reject_extra_missing_duplicate_and_nonobject_json(self):
        self.reject(changed(MESSAGE='raw private text'))
        obj = json.loads(row())
        del obj['boot']
        self.reject(identity.canonical(obj))
        self.reject(row().replace(b'"unit":', b'"unit":"other.service","unit":'))
        for raw in (b'null\n', b'[]\n', b'1\n', b'"string"\n', b'{'):
            self.reject(raw)

    def test_reject_nonstring_and_nonfinite_fields(self):
        for key in identity.ENVELOPE_KEYS:
            for value in (None, True, 1, [], {}):
                self.reject(changed(**{key:value}))
        self.reject(row().replace(b'"kind":"SSH_TIMEOUT"', b'"kind":NaN'))

    def test_reject_wrong_unit_unknown_kind_and_invalid_boot(self):
        for updates in ({'unit':'other.service'}, {'kind':'RAW_SSH_MESSAGE'},
                        {'boot':'A'*32}, {'boot':'a'*31}, {'boot':'a'*33}):
            self.reject(changed(**updates))

    def test_cursor_is_bounded_ascii_and_not_a_journal_parser(self):
        for cursor in ('', 'x'*513, 'cursor with spaces', 'cursor\nnext', 'żółw', '\x00'):
            self.reject(changed(cursor=cursor))
        self.assertEqual(len(identity.normalized_events(changed(cursor='x'*512), KEY)), 1)
        # Opaque token shape is allowed, no journald provenance is implied.
        self.assertEqual(len(identity.normalized_events(changed(cursor='synthetic-only'), KEY)), 1)

    def test_timestamp_requires_bounded_ascii_decimal(self):
        for stamp in ('0'+str(STAMP), '0'+str(identity.MIN_US), '+'+str(STAMP), str(STAMP)+'.0', '١'*16,
                      ' '+str(STAMP), str(STAMP)+' ', 'not-a-time'):
            self.reject(changed(time_us=stamp))

    def test_out_of_order_batch_and_blank_lines_reject(self):
        self.reject(row('cursor-2',STAMP+1)+row('cursor-1',STAMP))
        self.reject(row()+b'\n'+row('cursor-2'))

    def test_input_size_type_encoding_and_row_limits(self):
        for raw in (b'', b'\n', 'text', bytearray(row()), b'\xff\n', b'x'*(identity.MAX_BYTES+1)):
            self.reject(raw)
        self.reject(row()*(identity.MAX_ROWS+1))
        self.assertEqual(len(identity.normalized_events(row()*identity.MAX_ROWS, KEY)), identity.MAX_ROWS)

    def test_canonical_output_byte_limit_is_independent(self):
        # A raw envelope can fit while its additional identity fields cannot.
        self.assertLess(len(row()), len(identity.normalized_events(row(), KEY)[0]))
        with mock.patch.object(identity, 'MAX_BYTES', len(row())):
            with self.assertRaisesRegex(spool.Hold, 'OUTPUT_BYTES_LIMIT'):
                identity.normalized_events(row(), KEY)

    def test_output_does_not_copy_raw_identity_or_key(self):
        event = identity.normalized_events(row(cursor='private.cursor.SENTINEL.0199',boot='1234567890abcdef'*2),KEY)[0]
        for forbidden in (b'private.cursor.SENTINEL.0199', b'1234567890abcdef'*2, KEY, b'boot', b'cursor', b'time_us'):
            self.assertNotIn(forbidden, event)

    def test_new_schema_is_rejected_by_a_c_spool(self):
        event = identity.normalized_events(row(),KEY)[0]+b'\n'
        with self.assertRaises(spool.Hold):
            spool.normalize_sanitized_jsonl(event)


class LedgerContract(unittest.TestCase):
    def setUp(self):
        self.ledger = identity.IdentityLedger()

    def test_exact_replay_and_batch_overlap_emit_only_new_ids(self):
        first = self.ledger.accept(row('cursor-1')+row('cursor-2'),KEY)
        self.assertEqual((first.accepted,first.duplicates),(2,0))
        second = self.ledger.accept(row('cursor-2')+row('cursor-3'),KEY)
        self.assertEqual((second.accepted,second.duplicates),(1,1))
        repeated = self.ledger.accept(row('cursor-1'),KEY)
        self.assertEqual((repeated.accepted,repeated.duplicates,repeated.events),(0,1,b''))
        self.assertEqual(self.ledger.size,3)

    def test_repeated_identical_envelope_within_batch_is_one_record(self):
        result = self.ledger.accept(row()+row()+row(),KEY)
        self.assertEqual((result.accepted,result.duplicates),(1,2))
        self.assertEqual(len(result.events.splitlines()),1)

    def test_same_id_changed_kind_is_hold(self):
        self.ledger.accept(row(),KEY)
        with self.assertRaisesRegex(spool.Hold, 'SAME_ID_DIFFERENT_PAYLOAD'):
            self.ledger.accept(row(kind='COLLECTOR_EXIT_255'),KEY)
        self.assertEqual(self.ledger.accept(row(),KEY).duplicates,1)

    def test_same_id_changed_microsecond_is_hold(self):
        self.ledger.accept(row(),KEY)
        with self.assertRaisesRegex(spool.Hold, 'SAME_ID_DIFFERENT_PAYLOAD'):
            self.ledger.accept(row(stamp=STAMP+1),KEY)
        self.assertEqual(self.ledger.size,1)

    def test_conflicting_batch_is_atomic_even_with_valid_new_prefix(self):
        self.ledger.accept(row('cursor-old'),KEY)
        with self.assertRaisesRegex(spool.Hold, 'SAME_ID_DIFFERENT_PAYLOAD'):
            self.ledger.accept(row('cursor-new')+row('cursor-old',kind='COLLECTOR_EXIT_255'),KEY)
        self.assertEqual(self.ledger.size,1)
        self.assertEqual(self.ledger.accept(row('cursor-new'),KEY).accepted,1)

    def test_within_batch_conflict_does_not_initialize_ledger(self):
        with self.assertRaisesRegex(spool.Hold, 'SAME_ID_DIFFERENT_PAYLOAD'):
            self.ledger.accept(row()+row(kind='COLLECTOR_EXIT_255'),KEY)
        self.assertEqual(self.ledger.size,0)
        # Failed first batch must not bind a key scope.
        self.assertEqual(self.ledger.accept(row(),b'b'*32).accepted,1)

    def test_malformed_later_row_does_not_partially_commit(self):
        with self.assertRaises(spool.Hold):
            self.ledger.accept(row()+b'{}\n',KEY)
        self.assertEqual(self.ledger.size,0)

    def test_changed_key_scope_is_hold_not_silent_reingestion(self):
        self.ledger.accept(row(),KEY)
        with self.assertRaisesRegex(spool.Hold, 'IDENTITY_SCOPE_CHANGED'):
            self.ledger.accept(row('cursor-new'),b'b'*32)
        self.assertEqual(self.ledger.size,1)
        self.assertEqual(self.ledger.accept(row(),KEY).duplicates,1)

    def test_capacity_blocks_new_ids_but_allows_known_replay(self):
        with mock.patch.object(identity,'MAX_IDENTITIES',2):
            self.ledger.accept(row('cursor-1')+row('cursor-2'),KEY)
            with self.assertRaisesRegex(spool.Hold,'IDENTITY_LEDGER_FULL'):
                self.ledger.accept(row('cursor-3'),KEY)
            self.assertEqual(self.ledger.size,2)
            self.assertEqual(self.ledger.accept(row('cursor-1'),KEY).duplicates,1)

    def test_capacity_rejection_does_not_bind_new_scope(self):
        with mock.patch.object(identity,'MAX_IDENTITIES',1):
            with self.assertRaisesRegex(spool.Hold,'IDENTITY_LEDGER_FULL'):
                self.ledger.accept(row('cursor-1')+row('cursor-2'),KEY)
        self.assertEqual(self.ledger.size,0)
        self.assertEqual(self.ledger.accept(row(),b'b'*32).accepted,1)

    def test_lost_ledger_reaccepts_prior_ids(self):
        self.ledger.accept(row(),KEY)
        fresh = identity.IdentityLedger()
        self.assertEqual(fresh.accept(row(),KEY).accepted,1)

    def test_scope_changed_by_key_not_payload_and_cursor_not_incident_identity(self):
        first = json.loads(identity.normalized_events(row(),KEY)[0])
        changed_payload = json.loads(identity.normalized_events(row(kind='HTTP_IMPORT_TIMEOUT'),KEY)[0])
        other_key = json.loads(identity.normalized_events(row(),b'b'*32)[0])
        self.assertEqual(first['event_id'],changed_payload['event_id'])
        self.assertNotEqual(first['event_id'],other_key['event_id'])
        self.assertNotEqual(first['scope'],other_key['scope'])
        # Two messages about one possible failure are still two source records.
        self.assertEqual(self.ledger.accept(row('cursor-1')+row('cursor-2'),KEY).accepted,2)

    def test_self_test_and_lab_perform_no_files_network_or_subprocess(self):
        output = io.StringIO()
        with mock.patch('builtins.open',side_effect=AssertionError('file I/O')), \
             mock.patch.object(socket,'socket',side_effect=AssertionError('network')), \
             mock.patch.object(subprocess,'Popen',side_effect=AssertionError('subprocess')), \
             mock.patch.object(spool.os,'open',side_effect=AssertionError('os.open')), \
             contextlib.redirect_stdout(output):
            identity.self_test()
            identity.run_lab()
        text = output.getvalue()
        self.assertIn('V0145D_SELFTEST=PASS_PURE_SYNTHETIC_ONLY',text)
        self.assertIn('V0145D_RESULT=PASS_SYNTHETIC_IDENTITY_ONLY',text)
        self.assertIn('SOURCE_PROVENANCE=DECLARED_SYNTHETIC_NOT_AUTHENTICATED',text)


if __name__ == '__main__':
    unittest.main()
