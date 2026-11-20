#!/usr/bin/env python3
"""C.63.14: restricted Polish incident report from an already existing C.63.13 JSON.

No host telemetry reads, network, subprocesses, model or filesystem writes.
The bundled data is an artificial, reproducible synthetic example, NOT proof
of source provenance. Untrusted data only enters through strict schema validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import unittest
from copy import deepcopy

sys.dont_write_bytecode = True
MAX_BYTES = 16_384
SOURCE_SCHEMA = 'local-ai-agent.c63.13.bounded-historical-vm-journal-correlation.v1'
REPORT_SCHEMA = 'local-ai-agent.c63.14.offline-operator-report.v1'
BUNDLED_NAME = 'C63_13_SYNTHETIC_SNAPSHOT.json'
COUNTER_KEYS = frozenset({
    'DNS_COLLECTOR_FAILURE', 'DNS_COLLECTOR_SUCCESS', 'PIHOLE_TUNNEL_EXIT',
    'SSH_TIMEOUT_TARGET_UNVERIFIED', 'TAILSCALE_LINK_REBIND',
    'WIFI_PROFILE_TEXT_RECONNECT',
})
BOOL_KEYS = frozenset({
    'collector_success_after_single_wifi_marker',
    'journal_single_boot_in_classified_events', 'non_atomic_sources',
    'remediation_authorized', 'ssh_timeout_in_unqualified_vm_bucket',
    'telemetry_outage_proven', 'wifi_profile_marker_in_unqualified_vm_bucket',
    'wifi_profile_text_is_rf_measurement',
})
INT_KEYS = frozenset({
    'journal_rows_system', 'journal_rows_user', 'journalctl_invocations_max',
    'model_requests', 'vm_gets_max', 'vm_qualified_slots',
    'vm_unqualified_slots', 'wifi_profile_reconnect_count',
})
STR_KEYS = frozenset({
    'classification', 'deployment_gate', 'dns_health',
    'first_ssh_timeout_bucket', 'first_success_after_wifi_bucket',
    'model_action_authority', 'quality_gate_decision', 'root_cause',
    'router_acl_at_incident', 'sampling_recovered', 'schema',
    'source_authenticity', 'ssh_target_identity', 'vm_boundary_status',
    'vm_comparison', 'wifi_marker_bucket', 'window_journal', 'window_vm',
})
ROOT_KEYS = BOOL_KEYS | INT_KEYS | STR_KEYS | {'journal_event_counts'}


class Hold(Exception):
    """Safe, fixed-code parse/validation stop."""


def unique_keys(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise Hold('DUPLICATE_KEY')
        d[k] = v
    return d


def load_json_bytes(raw: bytes):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise Hold('INVALID_INPUT_SIZE')
    try:
        decoded = raw.decode('utf-8')
        return json.loads(decoded, object_pairs_hook=unique_keys,
                          parse_constant=lambda _: (_ for _ in ()).throw(Hold('NONFINITE')))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise Hold('INVALID_JSON') from exc


def require_code(d, key, value):
    if d[key] != value:
        raise Hold('UNSUPPORTED_'+key.upper())


def valid_bucket(s):
    return type(s) is str and len(s) == 5 and s[:2].isdigit() and s[3:].isdigit() and (
        s[2] == ':' and 0 <= int(s[:2]) <= 23 and int(s[3:]) in range(0, 60, 5))


def validate(r):
    if type(r) is not dict or set(r) != ROOT_KEYS:
        raise Hold('ROOT_SCHEMA_INVALID')
    for k in BOOL_KEYS:
        if type(r[k]) is not bool:
            raise Hold('BOOLEAN_INVALID')
    for k in INT_KEYS:
        if type(r[k]) is not int or not 0 <= r[k] <= 5000:
            raise Hold('INTEGER_INVALID')
    for k in STR_KEYS:
        if type(r[k]) is not str or not 0 < len(r[k]) <= 110 or any(ord(c) < 32 for c in r[k]):
            raise Hold('STRING_INVALID')
    c = r['journal_event_counts']
    if type(c) is not dict or set(c) != COUNTER_KEYS or any(
        type(x) is not int or not 0 <= x <= 5000 for x in c.values()
    ):
        raise Hold('COUNTERS_INVALID')
    for k, expected in (
        ('schema', SOURCE_SCHEMA), ('deployment_gate', 'HOLD'),
        ('model_action_authority', 'NONE'), ('quality_gate_decision', 'ABSTAIN_NO_MODEL_INFERENCE'),
        ('root_cause', 'UNDETERMINED'), ('dns_health', 'NOT_ESTABLISHED'),
        ('router_acl_at_incident', 'NOT_VERIFIED'), ('sampling_recovered', 'NOT_ESTABLISHED'),
        ('source_authenticity', 'NOT_CRYPTOGRAPHICALLY_ATTESTED'),
        ('ssh_target_identity', 'NOT_VERIFIED_BY_THIS_LAB'),
        ('vm_boundary_status', 'SAMPLED_OBSERVATION_RESUMPTION_BOUNDARY_UNATTESTED'),
        ('vm_comparison', 'PATTERN_MATCH_WITH_SYNTHETIC_REFERENCE_ONLY'),
        ('window_vm', '2030-02-13 09:00-09:35 CET'),
        ('window_journal', '2030-02-13 09:00-09:30 CET'),
    ):
        require_code(r, k, expected)
    if r['classification'] not in (
        'CROSS_SOURCE_TIME_BUCKET_CORRELATION_ONLY',
        'INSUFFICIENT_CROSS_SOURCE_EVIDENCE',
    ):
        raise Hold('CLASSIFICATION_INVALID')
    if not all(valid_bucket(r[k]) for k in (
        'first_ssh_timeout_bucket', 'wifi_marker_bucket', 'first_success_after_wifi_bucket'
    )):
        raise Hold('BUCKET_INVALID')
    if r['model_requests'] != 0 or r['remediation_authorized'] or r['telemetry_outage_proven'] or r['wifi_profile_text_is_rf_measurement']:
        raise Hold('UNSAFE_AUTHORITY_OR_CLAIM')
    if not r['non_atomic_sources'] or r['vm_gets_max'] != 8 or r['journalctl_invocations_max'] != 2:
        raise Hold('SOURCE_BOUNDARY_INVALID')
    if r['vm_qualified_slots'] + r['vm_unqualified_slots'] != 8:
        raise Hold('SLOT_TOTAL_INVALID')
    if r['wifi_profile_reconnect_count'] != c['WIFI_PROFILE_TEXT_RECONNECT']:
        raise Hold('WIFI_COUNT_MISMATCH')
    if r['classification'] == 'CROSS_SOURCE_TIME_BUCKET_CORRELATION_ONLY':
        if not (r['journal_single_boot_in_classified_events'] and
                r['ssh_timeout_in_unqualified_vm_bucket'] and
                r['wifi_profile_marker_in_unqualified_vm_bucket'] and
                r['collector_success_after_single_wifi_marker'] and
                r['wifi_profile_reconnect_count'] == 1 and
                c['SSH_TIMEOUT_TARGET_UNVERIFIED'] > 0 and
                c['DNS_COLLECTOR_SUCCESS'] > 0 and
                r['vm_unqualified_slots'] > 0):
            raise Hold('CORRELATION_INCONSISTENT')
    return r


def report_markdown(r, input_sha: str):
    validate(r)
    c = r['journal_event_counts']
    status = ('Zbieżność czasowa między źródłami w badanym oknie'
              if r['classification'] == 'CROSS_SOURCE_TIME_BUCKET_CORRELATION_ONLY'
              else 'Niewystarczające dowody korelacji między źródłami')
    lines = [
        '# Raport syntetyczny — Local AI Agent C.63.14',
        '',
        '**Scenariusz syntetyczny:** 13 lutego 2030 (Europe/Warsaw) — nie rzeczywisty incydent',
        '**Pochodzenie:** wymyślone dane testowe wygenerowane z C.63.13; nie są pomiarem i nie mają źródła produkcyjnego.',
        f'**SHA-256 wejścia:** `{input_sha}` (integralność tej kopii, nie atestacja źródła)',
        f'**Kontrakt:** `{REPORT_SCHEMA}`',
        '',
        '## Ocena',
        '',
        f'**{status}.** Nie ustalono przyczyny ani stanu usługi DNS.',
        '',
        '## Zaobserwowane dane',
        '',
        f'- VictoriaMetrics: **{r["vm_qualified_slots"]}/8** kwalifikujących się i **{r["vm_unqualified_slots"]}/8** niekwalifikujących się przedziałów (09:00–09:35 CET).',
        f'- Journald: **{r["journal_rows_user"]}** wierszy użytkownika i **{r["journal_rows_system"]}** systemowych (09:00–09:30 CET).',
        f'- SSH: **{c["SSH_TIMEOUT_TARGET_UNVERIFIED"]}** przekroczenia czasu połączenia; tożsamość celu niezweryfikowana.',
        f'- Kolektor DNS: **{c["DNS_COLLECTOR_FAILURE"]}** zdarzenia awarii i **{c["DNS_COLLECTOR_SUCCESS"]}** zdarzeń sukcesu.',
        f'- Wi-Fi: **{c["WIFI_PROFILE_TEXT_RECONNECT"]}** znacznik ponownego połączenia w dzienniku; nie jest pomiarem pasma radiowego.',
        f'- Pi-hole (tunel): **{c["PIHOLE_TUNNEL_EXIT"]}** zdarzeń zakończenia; Tailscale: **{c["TAILSCALE_LINK_REBIND"]}** zdarzenia zmiany/ponownego wiązania.',
        f'- Pierwszy przedział błędów SSH: **{r["first_ssh_timeout_bucket"]}**; znacznik Wi-Fi: **{r["wifi_marker_bucket"]}**; pierwsze powodzenie kolektora po znaczniku Wi-Fi: przedział **{r["first_success_after_wifi_bucket"]}**.',
        '',
        '## Granice interpretacji',
        '',
        '- Zgodność czasowa przedziałów pięciominutowych nie dowodzi przyczynowości ani dokładnej długości przerwy.',
        '- Dane pochodzą z nieatomowych odczytów i nie mają kryptograficznego poświadczenia pochodzenia.',
        '- Brakujących metryk nie wolno utożsamiać z niedostępnością DNS, routera lub sieci.',
        '- Nie zweryfikowano reguł ACL routera w chwili incydentu ani celu połączeń SSH.',
        '- Zaobserwowana granica widoczności próbek nie dowodzi pełnego wznowienia monitoringu.',
        '',
        '## Dalszy krok dla operatora',
        '',
        'Ręcznie porównać zatwierdzone dane o ścieżce administracyjnej i polityce dostępu z osią czasu, tylko jeśli wymaga tego dalsze dochodzenie. Bez automatycznej zmiany reguł lub restartów.',
        '',
        '## Ograniczenia bezpieczeństwa',
        '',
        '- `ROOT_CAUSE=UNDETERMINED`',
        '- `DNS_HEALTH=NOT_ESTABLISHED`',
        '- `QUALITY_GATE=ABSTAIN_NO_MODEL_INFERENCE`',
        '- `MODEL_ACTION_AUTHORITY=NONE`',
        '- `REMEDIATION_AUTHORIZED=false`',
        '- `DEPLOYMENT_GATE=HOLD`',
        '',
    ]
    return '\n'.join(lines)


def fixture():
    path = Path(__file__).resolve().with_name(BUNDLED_NAME)
    data = path.read_bytes()
    return validate(load_json_bytes(data)), hashlib.sha256(data).hexdigest()


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.digest = fixture()

    def test_baseline(self):
        self.assertIn('Zbieżność czasowa', report_markdown(self.original, self.digest))

    def test_source_hash_not_provenance(self):
        self.assertIn('nie atestacja źródła', report_markdown(self.original, self.digest))

    def test_no_private_log_content(self):
        s = report_markdown(self.original, self.digest)
        self.assertNotIn('192.168.', s)
        self.assertNotIn('sudo ', s)

    def test_public_operator_stdin_denied(self):
        import io,contextlib
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['--report-stdin']),2)
        self.assertIn('HOLD_PUBLIC_SYNTHETIC_ONLY_NO_OPERATOR_INPUT',output.getvalue())

    def test_duplicate_key(self):
        self.assertRaises(Hold, load_json_bytes, b'{"a":1,"a":2}')

    def test_invalid_json(self):
        self.assertRaises(Hold, load_json_bytes, b'{')

    def test_oversized(self):
        self.assertRaises(Hold, load_json_bytes, b'a'*(MAX_BYTES+1))

    def test_nonfinite(self):
        self.assertRaises(Hold, load_json_bytes, b'{"x":NaN}')

    def test_bad_utf8(self):
        self.assertRaises(Hold, load_json_bytes, b'\xff')


def _create_field_test(key, value):
    def test(self):
        x = deepcopy(self.original)
        x[key] = value
        self.assertRaises(Hold, validate, x)
    return test


BAD_FIELDS = {
    'model_action_authority': 'ADMIN',
    'deployment_gate': 'OPEN',
    'quality_gate_decision': 'READY_FOR_MODEL',
    'root_cause': 'DNS_OUTAGE',
    'dns_health': 'HEALTHY',
    'router_acl_at_incident': 'VERIFIED',
    'sampling_recovered': 'CONFIRMED',
    'source_authenticity': 'ATTESTED',
    'ssh_target_identity': 'ASUS_ROUTER',
    'telemetry_outage_proven': True,
    'remediation_authorized': True,
    'wifi_profile_text_is_rf_measurement': True,
    'model_requests': 1,
    'vm_gets_max': 100,
    'non_atomic_sources': False,
    'vm_qualified_slots': 8,
    'wifi_profile_reconnect_count': 2,
    'classification': 'DNS_OUTAGE_CAUSED_BY_WIFI',
    'journalctl_invocations_max': 10,
    'vm_comparison': 'INDEPENDENTLY_VERIFIED',
    'window_journal': '2030-02-14 09:00-09:30 CET',
    'first_ssh_timeout_bucket': '12:61',
    'journal_rows_user': True,
    'collector_success_after_single_wifi_marker': False,
    'ssh_timeout_in_unqualified_vm_bucket': False,
    'wifi_profile_marker_in_unqualified_vm_bucket': False,
}
for key, bad_value in BAD_FIELDS.items():
    setattr(Tests, 'test_reject_'+key, _create_field_test(key,bad_value))


def test_counter_mismatch(self):
    x=deepcopy(self.original)
    x['journal_event_counts']['WIFI_PROFILE_TEXT_RECONNECT']=2
    self.assertRaises(Hold,validate,x)


def test_unauthorized_extra_field(self):
    x=deepcopy(self.original)
    x['shell_command']='sudo reboot'
    self.assertRaises(Hold,validate,x)


def test_counters_missing(self):
    x=deepcopy(self.original)
    del x['journal_event_counts']['DNS_COLLECTOR_FAILURE']
    self.assertRaises(Hold,validate,x)


def test_counters_not_integers(self):
    x=deepcopy(self.original)
    x['journal_event_counts']['DNS_COLLECTOR_FAILURE']=True
    self.assertRaises(Hold,validate,x)

for name, fn in (
    ('test_counter_mismatch', test_counter_mismatch),
    ('test_unauthorized_extra_field',test_unauthorized_extra_field),
    ('test_counters_missing',test_counters_missing),
    ('test_counters_not_integers',test_counters_not_integers),
):
    setattr(Tests,name,fn)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    m=p.add_mutually_exclusive_group(required=True)
    m.add_argument('--self-test',action='store_true')
    m.add_argument('--report-bundled-snapshot',action='store_true')
    m.add_argument('--report-stdin',action='store_true')
    a=p.parse_args(argv)
    print('=== LOCAL AI AGENT / C.63.14 / OFFLINE OPERATOR INCIDENT REPORT ===')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    if a.self_test:
        print('MODE=OFFLINE_SELFTEST NETWORK=NO HOST_TELEMETRY=NO MODEL=NO')
        result=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        print(f'C6314_SELFTESTS={result.testsRun}/{result.testsRun}')
        print('C6314_RESULT='+('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_OFFLINE'))
        return 0 if result.wasSuccessful() else 1
    print('MODE=OFFLINE_PREEXISTING_JSON NO_NETWORK=YES NO_SUBPROCESS=YES NO_MODEL=YES')
    print('SOURCE_PROVENANCE=SYNTHETIC_UNATTESTED')
    if a.report_stdin:
        print('C6314_RESULT=HOLD_PUBLIC_SYNTHETIC_ONLY_NO_OPERATOR_INPUT')
        return 2
    try:
        if a.report_bundled_snapshot:
            r,digest=fixture()
        else:
            raw=sys.stdin.buffer.read(MAX_BYTES+1)
            r=validate(load_json_bytes(raw))
            digest=hashlib.sha256(raw).hexdigest()
        output=report_markdown(r,digest)
    except (Hold,OSError,ValueError) as exc:
        code=str(exc) if type(exc) is Hold and str(exc).replace('_','').isalnum() else 'INPUT_REJECTED'
        print('C6314_RESULT=HOLD_'+code)
        print('MODEL_REQUESTS=0 DEPLOYMENT_GATE=HOLD')
        return 2
    print(output)
    print('C6314_RESULT=PASS_SYNTHETIC_REPORT_NO_REAL_INCIDENT_DATA')
    return 0


if __name__=='__main__':
    sys.exit(main())
