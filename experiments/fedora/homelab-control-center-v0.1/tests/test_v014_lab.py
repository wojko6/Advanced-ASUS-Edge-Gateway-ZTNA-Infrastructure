"""HCC V0.14 pure offline synthetic tests; no router/VM/Alloy access."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import v014_collector_event_sanitizer as sanitizer
import v014_manual_hcc_view as view


def journal(ms, text):
    return json.dumps({'__REALTIME_TIMESTAMP': str(ms*1000),
                       '_BOOT_ID': 'a'*32, 'MESSAGE': text}).encode()


def synthetic_report():
    s = '''=== HCC V0.13.2 / FEDORA HOST + COLLECTOR CORRELATION ===
MODE=FEDORA_OFFLINE_MANUAL_READ_ONLY
WINDOW=7d
TELEMETRY_GAPS=1
INVALID_SAMPLE_COUNT=0
--- GAP_1 ---
START_WARSAW=2026-10-28T17:04:26+01:00
END_WARSAW=2026-10-28T17:25:04+01:00
DURATION_SECONDS=1238.000
CLASS=COLLECTOR_EXIT_255_OBSERVED
HOST_RECORD_OVERLAP_PCT=0.0
RESIDUAL_NOT_MATCHED_SECONDS=1238.000
COLLECTOR_EXIT_255_EVENTS=18
'''
    for cl in view.CLASSES:
        s += f'COUNT_{cl}={int(cl == "COLLECTOR_EXIT_255_OBSERVED")}\n'
    return (s+'TELEMETRY_GAPS_NOT_EQ_DNS_OUTAGES=YES\n'
            'DEPLOYMENT_GATE=HOLD\nV0132_RESULT=PASS_CORRELATION_ONLY\n').encode()


class LabTests(unittest.TestCase):
    def test_sanitization_no_data_leak(self):
        payload = b'\n'.join([
            journal(1793260000000, 'ssh: connect to host 192.0.2.9 port 1122: Connection timed out'),
            journal(1793260001000, 'curl: (28) Operation timed out'),
            journal(1793260002000, 'dns-guard-monitoring.service: Main process exited, code=exited, status=255/EXCEPTION')])
        safe = sanitizer.sanitize(payload)
        self.assertEqual([x['kind'] for x in safe], ['SSH_TIMEOUT','HTTP_IMPORT_TIMEOUT','COLLECTOR_EXIT_255'])
        self.assertNotIn('192.0.2.9', str(safe))
        self.assertTrue(all(set(x) == {'time','kind','component','source'} for x in safe))

    def test_sanitizer_invalid_reject(self):
        with self.assertRaises(sanitizer.InputError):
            sanitizer.sanitize(b'not json')
        with self.assertRaises(sanitizer.InputError):
            sanitizer.sanitize(b'{"MESSAGE":"a","MESSAGE":"b"}')

    def test_view_renders_safe_static_page(self):
        rep = view.parse_report(synthetic_report())
        result = view.render(rep)
        self.assertEqual(len(rep['gaps']), 1)
        self.assertIn('Brak telemetrii', result)
        self.assertNotIn('<script', result.lower())
        self.assertNotIn('fetch(', result.lower())
        self.assertIn('Content-Security-Policy', result)

    def test_view_does_not_accept_unvalidated_result(self):
        with self.assertRaises(view.InvalidReport):
            view.parse_report(synthetic_report().replace(b'PASS_CORRELATION_ONLY', b'UNKNOWN'))

    def test_view_does_not_accept_forged_count(self):
        with self.assertRaises(view.InvalidReport):
            view.parse_report(synthetic_report().replace(b'COUNT_COLLECTOR_EXIT_255_OBSERVED=1', b'COUNT_COLLECTOR_EXIT_255_OBSERVED=2'))

    def test_alloy_fragment_not_direct_journal(self):
        config = (ROOT/'monitoring/v014-dns-guard-sanitized.alloy.fragment').read_text()
        self.assertIn('loki.source.file', config)
        self.assertNotIn('loki.source.journal', config)
        self.assertNotIn('loki.write "', config)
        self.assertIn('loki.write.local.receiver', config)
        self.assertIn('DO NOT APPLY', config)

if __name__ == '__main__':
    unittest.main()