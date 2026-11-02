#!/usr/bin/env python3
"""Read-only, synthetic-only diagnostic entrypoint for Local AI Agent v0.21.

Composes existing C.63.14 incident reporting with a SEPARATE C.63.6 synthetic
pre-model gate demonstration. These fixtures are independent: gate eligibility
is NOT an evaluation of the incident report and cannot authorize a model call.

No network, model invocation, subprocess, service/host telemetry, or filesystem
writes. Only the pinned bundled C.63.13 artificial fixture is read.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
# Explicit sibling import: no packages, pip installs, or dynamic plugin loading.
_C63 = Path(__file__).resolve().parent.parent / 'c63'
sys.path.insert(0, str(_C63))

import local_ai_agent_v021c63_6_pre_model_evidence_gate_shadow_lab_v01 as gate
import local_ai_agent_v021c63_14_operator_incident_report_offline_lab_v01 as report

SCHEMA = 'local-ai-agent.v0.21.operator-diagnostic-synthetic.v1'
FIXTURE_NAME = 'C63_13_SYNTHETIC_SNAPSHOT.json'
REQUIRED_GATE_RESULT = {
    'scenario': 'baseline',
    'gate_decision': gate.evidence.READY,
    'reason_code': 'NONE',
    'model_requests': 0,
    'model_invoked': False,
    'response_gate': 'NOT_INVOKED_OFFLINE',
    'assessment_code': 'TEMPORAL_CORRELATION_ONLY',
    'next_check_code': 'NOT_ISSUED',
    'root_cause': 'UNDETERMINED',
    'deployment_gate': 'HOLD',
    'model_action_authority': 'NONE',
}


class Hold(Exception):
    """Refuse publication of an invalid or authority-escalating assessment."""


def collect(*, load_fixture=None, run_gate=None):
    """Build a bounded public operator view, using separate fixed fixtures.

    Injectable callables are used by the offline unit tests only. The CLI always
    uses the fixed C.63 methods, never paths, URLs or caller-provided payloads.
    """
    load_fixture = report.fixture if load_fixture is None else load_fixture
    run_gate = gate.process_case if run_gate is None else run_gate
    try:
        incident, digest = load_fixture()
        report.validate(incident)
    except (report.Hold, OSError, ValueError, TypeError) as exc:
        raise Hold('INCIDENT_FIXTURE_REJECTED') from exc
    if type(digest) is not str or re.fullmatch(r'[0-9a-f]{64}', digest) is None:
        raise Hold('SOURCE_DIGEST_INVALID')
    # The fixed source must not turn into a generic incident or live-data adapter.
    if (incident['schema'] != report.SOURCE_SCHEMA
            or incident['window_vm'] != '2030-02-13 09:00-09:35 CET'
            or incident['quality_gate_decision'] != 'ABSTAIN_NO_MODEL_INFERENCE'
            or incident['model_requests'] != 0
            or incident['deployment_gate'] != 'HOLD'
            or incident['model_action_authority'] != 'NONE'
            or incident['remediation_authorized'] is not False
            or incident['root_cause'] != 'UNDETERMINED'
            or incident['dns_health'] != 'NOT_ESTABLISHED'):
        raise Hold('INCIDENT_SAFETY_BOUNDARY')
    try:
        # No send callback. C.63.6 will never construct an HTTP client.
        gate_result = run_gate('baseline')
    except Exception as exc:
        raise Hold('SYNTHETIC_GATE_FAILED') from exc
    if type(gate_result) is not dict or gate_result != {
            'schema': gate.SCHEMA, **REQUIRED_GATE_RESULT}:
        raise Hold('GATE_INVARIANT_FAILED')
    return {
        'schema': SCHEMA,
        'mode': 'PUBLIC_SYNTHETIC_OFFLINE_ONLY',
        'incident_fixture': FIXTURE_NAME,
        'incident_fixture_sha256': digest,
        'fixture_fingerprint_is_provenance_attestation': False,
        'incident_classification': incident['classification'],
        'incident_qualified_vm_slots': incident['vm_qualified_slots'],
        'incident_unqualified_vm_slots': incident['vm_unqualified_slots'],
        'incident_quality_gate': incident['quality_gate_decision'],
        'separate_synthetic_gate_scenario': 'baseline',
        'separate_synthetic_gate_decision': gate_result['gate_decision'],
        'gate_demo_and_incident_are_same_evidence': False,
        'gate_demo_authorizes_model_for_incident': False,
        'model_requests': 0,
        'model_invoked': False,
        'root_cause': 'UNDETERMINED',
        'dns_health': 'NOT_ESTABLISHED',
        'operator_next_step': 'MANUAL_REVIEW_ONLY',
        'remediation_authorized': False,
        'model_action_authority': 'NONE',
        'deployment_gate': 'HOLD',
    }


def operator_report(summary):
    """Create the human-facing report from the same fixed synthetic fixture."""
    if type(summary) is not dict or summary.get('schema') != SCHEMA:
        raise Hold('SUMMARY_INVALID')
    # Re-run and match the entire fixed bounded assessment before displaying it.
    fresh = collect()
    if summary != fresh:
        raise Hold('SUMMARY_CHANGED')
    incident, digest = report.fixture()
    return (report.report_markdown(incident, digest)
            + '\n## Oddzielna demonstracja bramki C.63.6\n\n'
            + '- Scenariusz \`baseline\` jest innym syntetycznym zestawem danych.\n'
            + '- Jego kwalifikacja nie dotyczy powyższego incydentu.\n'
            + '- Brak wywołań modelu i brak uprawnień do działania.\n'
            + '- Decyzja operatora: \`MANUAL_REVIEW_ONLY\`.\n'
            + '- \`DEPLOYMENT_GATE=HOLD\`, \`MODEL_ACTION_AUTHORITY=NONE\`.\n')


class Tests(unittest.TestCase):
    def test_baseline(self):
        result = collect()
        self.assertEqual(result['incident_qualified_vm_slots'], 4)
        self.assertEqual(result['incident_unqualified_vm_slots'], 4)
        self.assertEqual(result['model_requests'], 0)

    def test_no_model_authority(self):
        result = collect()
        self.assertEqual(result['model_action_authority'], 'NONE')
        self.assertEqual(result['deployment_gate'], 'HOLD')
        self.assertFalse(result['remediation_authorized'])
        self.assertFalse(result['model_invoked'])

    def test_evidence_independence(self):
        result = collect()
        self.assertFalse(result['gate_demo_and_incident_are_same_evidence'])
        self.assertFalse(result['gate_demo_authorizes_model_for_incident'])
        self.assertEqual(result['incident_quality_gate'], 'ABSTAIN_NO_MODEL_INFERENCE')

    def test_digest_not_attestation(self):
        result = collect()
        self.assertRegex(result['incident_fixture_sha256'], r'^[a-f0-9]{64}$')
        self.assertFalse(result['fixture_fingerprint_is_provenance_attestation'])

    def test_no_host_access_or_network(self):
        with patch('socket.socket', side_effect=AssertionError('NETWORK_CALL')):
            with patch('subprocess.Popen', side_effect=AssertionError('SUBPROCESS_CALL')):
                self.assertEqual(collect()['model_requests'], 0)

    def test_no_private_data_or_commands_in_summary(self):
        text = json.dumps(collect(), ensure_ascii=False)
        for forbidden in ('192.168.', '10.0.', 'SSH_PASSWORD', 'sudo ', 'reboot'):
            self.assertNotIn(forbidden, text)

    def test_fail_closed_with_malformed_fixture(self):
        original, digest = report.fixture()
        injected = deepcopy(original)
        injected['deployment_gate'] = 'OPEN'
        with self.assertRaisesRegex(Hold, 'INCIDENT_FIXTURE_REJECTED'):
            collect(load_fixture=lambda: (injected, digest))

    def test_fail_closed_with_extra_input(self):
        original, digest = report.fixture()
        injected = deepcopy(original)
        injected['raw_journal_line'] = 'private'
        with self.assertRaisesRegex(Hold, 'INCIDENT_FIXTURE_REJECTED'):
            collect(load_fixture=lambda: (injected, digest))

    def test_fail_closed_gate_escalation(self):
        baseline = gate.process_case('baseline')
        injected = dict(baseline, model_requests=1, model_invoked=True)
        with self.assertRaisesRegex(Hold, 'GATE_INVARIANT_FAILED'):
            collect(run_gate=lambda _: injected)

    def test_fail_closed_gate_unexpected_exception(self):
        def broken(_):
            raise RuntimeError('broken')
        with self.assertRaisesRegex(Hold, 'SYNTHETIC_GATE_FAILED'):
            collect(run_gate=broken)

    def test_fail_closed_invalid_digest(self):
        original, _ = report.fixture()
        with self.assertRaisesRegex(Hold, 'SOURCE_DIGEST_INVALID'):
            collect(load_fixture=lambda: (original, 'not-sha256'))

    def test_report_labels_synthetic_and_hold(self):
        result = operator_report(collect())
        self.assertIn('Scenariusz syntetyczny', result)
        self.assertIn('innym syntetycznym zestawem danych', result)
        self.assertIn('DEPLOYMENT_GATE=HOLD', result)

    def test_report_rejects_modified_summary(self):
        modified = dict(collect(), operator_next_step='RESTART_ROUTER')
        with self.assertRaisesRegex(Hold, 'SUMMARY_CHANGED'):
            operator_report(modified)

    def test_reproducible(self):
        self.assertEqual(collect(), collect())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_mutually_exclusive_group(required=True)
    commands.add_argument('--self-test', action='store_true')
    commands.add_argument('--summary-json', action='store_true')
    commands.add_argument('--operator-report', action='store_true')
    args = parser.parse_args(argv)
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        print(f'AGENT_DIAGNOSTIC_TESTS={result.testsRun} STATUS=' +
              ('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD'))
        return 0 if result.wasSuccessful() else 1
    try:
        summary = collect()
        if args.summary_json:
            print(json.dumps(summary, sort_keys=True, ensure_ascii=True, indent=2))
        else:
            print(operator_report(summary))
    except Hold as exc:
        # Only fixed, non-sensitive hold codes, never input, paths or tracebacks.
        print('AGENT_DIAGNOSTIC=HOLD_' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
