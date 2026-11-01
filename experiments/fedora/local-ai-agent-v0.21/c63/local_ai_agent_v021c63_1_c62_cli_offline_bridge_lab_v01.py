#!/usr/bin/env python3
"""C.63.1 — offline parser/assessment for C.62.9.3 bounded CLI summaries.

Self-tests and fixtures use synthetic text only. Optional --assess-stdin reads
one operator-supplied historical CLI summary from stdin, never host services.
No model, network, subprocess, router, procfs, journald, or config access.

This is deliberately NOT an importer of C.62 Python code. The CLI report's
self-declared SHA/pins and success status are NOT cryptographic attestation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import unittest

sys.dont_write_bytecode = True

HEADER = '=== V0.21C.62.9.3 / REAL VM + JOURNAL + DATED ACL EVIDENCE ==='
SOURCE = 'EIGHT_FIXED_VM_LOOPBACK_GETS_AND_TWO_BOUNDED_LOCAL_JOURNAL_READS'
RESULT_PASS = 'PASS_BOUNDED_CROSS_SOURCE_OBSERVATION_ONLY'
SCHEMA = 'local-ai-agent.c63.1.c62-cli-offline-assessment.v1'
ORIGIN_FIXTURE = 'SYNTHETIC_C62_CLI_FIXTURE'
ORIGIN_OPERATOR = 'OPERATOR_SUPPLIED_HISTORICAL_CLI_UNVERIFIED'
MAX_INPUT_BYTES = 12000
MAX_LINES = 80
MAX_GRID = 12
GRID_SECONDS = 300
ALLOWED_STATUS = frozenset({
    'VM_GAP_AND_JOURNAL_RECOVERY_CORRELATED_HISTORICAL_ACL_LEASE_MATCH',
    'VM_GAP_AND_JOURNAL_RECOVERY_CORRELATED_ACL_LEASE_UNVERIFIED',
    'JOURNAL_RECOVERY_VM_POST_WIFI_FRESH_MISSING',
    'JOURNAL_RECOVERY_VM_GAP_NOT_CORROBORATED',
    'INSUFFICIENT_CROSS_SOURCE_CORRELATION',
})
FIELD_KEYS = frozenset({
    'SOURCE', 'PARENT_SOURCE_SHA256_PINS', 'WINDOW_JOURNAL_CET', 'WINDOW_VM_CET',
    'VM_OBSERVATION_SLOTS', 'VM_FRESH_SLOTS', 'VM_GAP_SLOTS',
    'VM_GAPS_OVERLAP_SSH_WIFI_WINDOW', 'VM_FRESH_SLOTS_AFTER_WIFI',
    'JOURNAL_CLASSIFIED_SSH_TIMEOUTS', 'JOURNAL_COLLECTOR_FAILURES',
    'JOURNAL_WIFI_RECONNECT_EVENTS', 'JOURNAL_COLLECTOR_SUCCESS_EVENTS',
    'FIRST_SSH_TIMEOUT_LOCAL', 'WIFI_RECONNECT_LOCAL',
    'FIRST_SUCCESS_AFTER_WIFI_LOCAL',
    'HISTORICAL_ACCESS_RESTRICTION_SNAPSHOT_DATE',
    'HISTORICAL_ACCESS_RESTRICTION_ENABLED',
    'HISTORICAL_AUTHORIZED_DHCP_LEASE_MATCH',
    'LIVE_ROUTER_ACL_AT_INCIDENT', 'CAUSE_OF_ACCESS_RESTRICTION',
    'ROOT_CAUSE', 'RF_FREQUENCY_MEASURED', 'STATUS',
    'NETWORK_ASUS_HCC_LOKI_OLLAMA_EXECUTOR_PODMAN_CONTACTED',
    'VM_LOOPBACK_AND_LOCAL_JOURNAL_CONTACTED', 'RAW_IDENTIFIERS_PRINTED',
    'FILES_WRITTEN', 'MODEL_ACTION_AUTHORITY', 'REPORT_SHA256',
    'DEPLOYMENT_GATE', 'V021C6293_RESULT',
})
# Keep a rigid input contract. A CLI report with additional, unreviewed fields
# must fail closed until this parser has been reviewed for that newer format.
REQUIRED = FIELD_KEYS
VM_RE = re.compile(r'^VM_GRID_(\d\d:\d\d)$')
HASH_RE = re.compile(r'^[0-9a-f]{64}$')
DAY_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
WINDOW_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})T(\d\d:\d\d)\.\.(\d\d:\d\d)$')

class Hold(Exception):
    """Invalid/contradictory evidence. No health or remediation inference."""


def integer(s, name, max_value=100000):
    if not isinstance(s, str) or not re.fullmatch(r'(0|[1-9]\d{0,5})', s):
        raise Hold('INVALID_NUMBER_' + name)
    n = int(s)
    if n > max_value:
        raise Hold('NUMBER_OVER_LIMIT_' + name)
    return n


def local_time(text, name):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d\d:\d\d:\d\d[+-]\d{4}', text):
        raise Hold('TIMESTAMP_FORMAT_' + name)
    try:
        value = dt.datetime.strptime(text, '%Y-%m-%dT%H:%M:%S%z')
    except ValueError as e:
        raise Hold('TIMESTAMP_INVALID_' + name) from e
    if value.utcoffset() != dt.timedelta(hours=1):
        raise Hold('TIMESTAMP_NOT_CET_' + name)
    return value


def window(text, name):
    m = WINDOW_RE.fullmatch(text)
    if not m:
        raise Hold('WINDOW_FORMAT_' + name)
    try:
        day = dt.date.fromisoformat(m[1])
        s = dt.datetime.combine(day, dt.time.fromisoformat(m[2]))
        e = dt.datetime.combine(day, dt.time.fromisoformat(m[3]))
    except ValueError as exc:
        raise Hold('WINDOW_INVALID_' + name) from exc
    if not s < e or (e - s).total_seconds() > 3600:
        raise Hold('WINDOW_BOUNDS_' + name)
    return s, e


def parse_cli(blob: bytes, *, origin: str):
    if origin not in (ORIGIN_FIXTURE, ORIGIN_OPERATOR):
        raise Hold('ORIGIN_INVALID')
    if not isinstance(blob, bytes) or not 0 < len(blob) <= MAX_INPUT_BYTES:
        raise Hold('INPUT_SIZE_INVALID')
    try:
        text = blob.decode('ascii')
    except UnicodeDecodeError as exc:
        raise Hold('NON_ASCII_INPUT') from exc
    lines = text.splitlines()
    if not 1 < len(lines) <= MAX_LINES or lines[0] != HEADER:
        raise Hold('REPORT_HEADER_OR_LINE_COUNT_INVALID')
    fields = {}
    grid = {}
    for line in lines[1:]:
        if not line or line.count('=') != 1:
            raise Hold('UNEXPECTED_REPORT_LINE')
        key, value = line.split('=', 1)
        grid_match = VM_RE.fullmatch(key)
        if grid_match:
            if len(grid) >= MAX_GRID or grid_match[1] in grid:
                raise Hold('GRID_DUPLICATE_OR_LIMIT')
            if value not in ('GAP', 'FRESH/LOCAL', 'FRESH/BOOTSTRAP', 'FRESH/INVALID_STATE_SAMPLED'):
                raise Hold('GRID_VALUE_INVALID')
            grid[grid_match[1]] = value
        elif key in FIELD_KEYS:
            if key in fields or not 0 < len(value) <= 100:
                raise Hold('FIELD_DUPLICATE_OR_VALUE_INVALID')
            fields[key] = value
        else:
            raise Hold('UNREVIEWED_REPORT_FIELD')
    if set(fields) != REQUIRED:
        raise Hold('REPORT_FIELDS_INCOMPLETE')
    for k, v in {
        'SOURCE': SOURCE,
        'PARENT_SOURCE_SHA256_PINS': 'PASS',
        'NETWORK_ASUS_HCC_LOKI_OLLAMA_EXECUTOR_PODMAN_CONTACTED': 'NO',
        'VM_LOOPBACK_AND_LOCAL_JOURNAL_CONTACTED': 'YES',
        'RAW_IDENTIFIERS_PRINTED': 'NO',
        'FILES_WRITTEN': 'NO',
        'MODEL_ACTION_AUTHORITY': 'NONE',
        'DEPLOYMENT_GATE': 'HOLD',
        'ROOT_CAUSE': 'UNDETERMINED',
        'LIVE_ROUTER_ACL_AT_INCIDENT': 'NOT_VERIFIED',
        'CAUSE_OF_ACCESS_RESTRICTION': 'NOT_ISOLATED',
        'RF_FREQUENCY_MEASURED': 'NO',
        'HISTORICAL_ACCESS_RESTRICTION_ENABLED': 'RECORDED_TRUE_NOT_CURRENTLY_RECHECKED',
    }.items():
        if fields[k] != v:
            raise Hold('INVARIANT_' + k)
    if fields['HISTORICAL_AUTHORIZED_DHCP_LEASE_MATCH'] not in (
        'OBSERVED_MATCH_TO_DATED_SNAPSHOT', 'NOT_ESTABLISHED'
    ):
        raise Hold('HISTORICAL_LEASE_FLAG_INVALID')
    if not HASH_RE.fullmatch(fields['REPORT_SHA256']):
        raise Hold('HASH_FORMAT_INVALID')
    if fields['STATUS'] not in ALLOWED_STATUS:
        raise Hold('STATUS_UNKNOWN')
    if fields['V021C6293_RESULT'] not in (RESULT_PASS, 'HOLD_INSUFFICIENT_CROSS_SOURCE_EVIDENCE'):
        raise Hold('RESULT_UNKNOWN')
    if fields['V021C6293_RESULT'] == RESULT_PASS and not fields['STATUS'].startswith(
        'VM_GAP_AND_JOURNAL_RECOVERY_CORRELATED'
    ):
        raise Hold('STATUS_RESULT_CONTRADICTION')
    if fields['V021C6293_RESULT'] != RESULT_PASS and fields['STATUS'].startswith(
        'VM_GAP_AND_JOURNAL_RECOVERY_CORRELATED'
    ):
        raise Hold('STATUS_RESULT_CONTRADICTION')
    slots = integer(fields['VM_OBSERVATION_SLOTS'], 'SLOTS', MAX_GRID)
    fresh = integer(fields['VM_FRESH_SLOTS'], 'FRESH', MAX_GRID)
    gaps = integer(fields['VM_GAP_SLOTS'], 'GAPS', MAX_GRID)
    post = integer(fields['VM_FRESH_SLOTS_AFTER_WIFI'], 'AFTER_WIFI', MAX_GRID)
    ssh_count = integer(fields['JOURNAL_CLASSIFIED_SSH_TIMEOUTS'], 'SSH')
    wifi_count = integer(fields['JOURNAL_WIFI_RECONNECT_EVENTS'], 'WIFI')
    collector_fail = integer(fields['JOURNAL_COLLECTOR_FAILURES'], 'COLLECTOR_FAILURE')
    collector_success = integer(fields['JOURNAL_COLLECTOR_SUCCESS_EVENTS'], 'COLLECTOR_SUCCESS')
    if not 1 <= slots <= MAX_GRID or fresh+gaps != slots or len(grid) != slots:
        raise Hold('GRID_SLOT_COUNT_CONTRADICTION')
    if (sum(v.startswith('FRESH/') for v in grid.values()) != fresh or
            sum(v == 'GAP' for v in grid.values()) != gaps):
        raise Hold('GRID_KIND_COUNT_CONTRADICTION')
    if wifi_count > 1 or post > fresh:
        raise Hold('WIFI_OR_POST_COUNT_CONTRADICTION')
    win_start, win_end = window(fields['WINDOW_VM_CET'], 'VM')
    journal_start, journal_end = window(fields['WINDOW_JOURNAL_CET'], 'JOURNAL')
    if win_start.date() != journal_start.date() or win_start != journal_start or journal_end > win_end:
        raise Hold('WINDOW_RELATION_INVALID')
    duration = int((win_end - win_start).total_seconds())
    if duration != (slots - 1) * GRID_SECONDS:
        raise Hold('GRID_INTERVAL_INVALID')
    expected_times = [(win_start + dt.timedelta(seconds=GRID_SECONDS * i)).strftime('%H:%M')
                      for i in range(slots)]
    if set(grid) != set(expected_times):
        raise Hold('GRID_TIMES_INCONSISTENT')
    ssh = local_time(fields['FIRST_SSH_TIMEOUT_LOCAL'], 'SSH')
    wifi = local_time(fields['WIFI_RECONNECT_LOCAL'], 'WIFI')
    success = local_time(fields['FIRST_SUCCESS_AFTER_WIFI_LOCAL'], 'SUCCESS')
    if not ssh <= wifi < success:
        raise Hold('JOURNAL_CHRONOLOGY_CONTRADICTION')
    if not 1 <= ssh_count or wifi_count != 1 or collector_success < 1:
        raise Hold('JOURNAL_COUNTERS_CONTRADICTION')
    if ssh.date() != win_start.date() or wifi.date() != win_start.date() or success.date() != win_start.date():
        raise Hold('JOURNAL_DATE_INCONSISTENT')
    if not (win_start.time() <= ssh.time() <= journal_end.time() and
            win_start.time() <= wifi.time() <= journal_end.time() and
            win_start.time() <= success.time() <= win_end.time()):
        raise Hold('JOURNAL_TIME_OUTSIDE_WINDOWS')
    post_computed = sum(grid[t].startswith('FRESH/') and
                        t > wifi.strftime('%H:%M') for t in expected_times)
    if post != post_computed:
        raise Hold('POST_WIFI_GRID_COUNT_CONTRADICTION')
    actual_overlap = any(grid[t] == 'GAP' and
        ssh.replace(tzinfo=None) - dt.timedelta(seconds=GRID_SECONDS)
        <= dt.datetime.combine(win_start.date(), dt.time.fromisoformat(t))
        <= wifi.replace(tzinfo=None) for t in expected_times)
    overlap = fields['VM_GAPS_OVERLAP_SSH_WIFI_WINDOW']
    if overlap not in ('YES', 'NO') or (overlap == 'YES') != actual_overlap:
        raise Hold('OVERLAP_CONTRADICTION')
    if not DAY_RE.fullmatch(fields['HISTORICAL_ACCESS_RESTRICTION_SNAPSHOT_DATE']):
        raise Hold('POLICY_DATE_INVALID')
    try:
        policy_date = dt.date.fromisoformat(fields['HISTORICAL_ACCESS_RESTRICTION_SNAPSHOT_DATE'])
    except ValueError as exc:
        raise Hold('POLICY_DATE_INVALID') from exc
    if policy_date >= win_start.date():
        raise Hold('DATED_POLICY_NOT_HISTORICAL')
    correlated = actual_overlap and ssh_count > 0 and gaps > 0 and collector_success > 0
    status = ('CROSS_SOURCE_TEMPORAL_CORRELATION_ONLY' if correlated else
              'SAMPLED_OBSERVATION_GAP_ONLY' if gaps > 0 else
              'INSUFFICIENT_EVIDENCE')
    # We have fresh GRID labels but NO distinct raw VM sample timestamp values.
    # Never infer two distinct post-gap raw samples from grid occupancy alone.
    result = {
        'schema': SCHEMA,
        'evidence_origin': origin,
        'input_sha256': hashlib.sha256(blob).hexdigest(),
        'source_report_hash_claim': 'PRESENT_UNVERIFIED',
        'source_pin_claim': 'SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED',
        'source_report_status': fields['STATUS'],
        'source_report_result': fields['V021C6293_RESULT'],
        'assessment_status': status,
        'vm_observation_slots': slots,
        'vm_gap_slots': gaps,
        'vm_fresh_slots': fresh,
        'vm_fresh_grid_slots_after_wifi': post,
        'journal_ssh_timeout_count': ssh_count,
        'journal_collector_failure_count': collector_fail,
        'journal_collector_success_count': collector_success,
        'journal_wifi_reconnect_count': wifi_count,
        'historical_policy_match': fields['HISTORICAL_AUTHORIZED_DHCP_LEASE_MATCH'],
        'historical_policy_not_live_proof': True,
        'two_distinct_post_gap_raw_sample_timestamps': 'NOT_AVAILABLE_IN_C62_CLI',
        'sampled_collection_resumption': 'NOT_ESTABLISHED',
        'clock_and_source_provenance_attested': False,
        'dns_health': 'NOT_ESTABLISHED',
        'ssh_management_policy_enforcement': 'NOT_PROVEN',
        'root_cause': 'UNDETERMINED',
        'model_action_authority': 'NONE',
        'deployment_gate': 'HOLD',
        'model_contacted': False,
        'host_services_contacted_by_c63_1': False,
    }
    if origin == ORIGIN_FIXTURE:
        result['interpretation'] = 'SYNTHETIC_FIXTURE_ONLY'
    else:
        result['interpretation'] = 'HISTORICAL_OPERATOR_SUPPLIED_CLI_UNVERIFIED_NOT_CURRENT_HEALTH'
    return result


# This fixture is deliberately fictional, without host identifiers or the
# values/dates of the real 2026-10-30 incident. It uses the C.62.9.3 CLI shape.
def fixture():
    rows = {
        'SOURCE': SOURCE,
        'PARENT_SOURCE_SHA256_PINS': 'PASS',
        'WINDOW_JOURNAL_CET': '2030-02-13T09:00..09:30',
        'WINDOW_VM_CET': '2030-02-13T09:00..09:35',
        'VM_OBSERVATION_SLOTS': '8', 'VM_FRESH_SLOTS': '3', 'VM_GAP_SLOTS': '5',
        'VM_GAPS_OVERLAP_SSH_WIFI_WINDOW': 'YES', 'VM_FRESH_SLOTS_AFTER_WIFI': '2',
        'JOURNAL_CLASSIFIED_SSH_TIMEOUTS': '4', 'JOURNAL_COLLECTOR_FAILURES': '6',
        'JOURNAL_WIFI_RECONNECT_EVENTS': '1', 'JOURNAL_COLLECTOR_SUCCESS_EVENTS': '2',
        'FIRST_SSH_TIMEOUT_LOCAL': '2030-02-13T09:05:11+0100',
        'WIFI_RECONNECT_LOCAL': '2030-02-13T09:25:42+0100',
        'FIRST_SUCCESS_AFTER_WIFI_LOCAL': '2030-02-13T09:26:22+0100',
        'HISTORICAL_ACCESS_RESTRICTION_SNAPSHOT_DATE': '2030-01-01',
        'HISTORICAL_ACCESS_RESTRICTION_ENABLED': 'RECORDED_TRUE_NOT_CURRENTLY_RECHECKED',
        'HISTORICAL_AUTHORIZED_DHCP_LEASE_MATCH': 'OBSERVED_MATCH_TO_DATED_SNAPSHOT',
        'LIVE_ROUTER_ACL_AT_INCIDENT': 'NOT_VERIFIED',
        'CAUSE_OF_ACCESS_RESTRICTION': 'NOT_ISOLATED', 'ROOT_CAUSE': 'UNDETERMINED',
        'RF_FREQUENCY_MEASURED': 'NO',
        'STATUS': 'VM_GAP_AND_JOURNAL_RECOVERY_CORRELATED_HISTORICAL_ACL_LEASE_MATCH',
        'NETWORK_ASUS_HCC_LOKI_OLLAMA_EXECUTOR_PODMAN_CONTACTED': 'NO',
        'VM_LOOPBACK_AND_LOCAL_JOURNAL_CONTACTED': 'YES',
        'RAW_IDENTIFIERS_PRINTED': 'NO', 'FILES_WRITTEN': 'NO',
        'MODEL_ACTION_AUTHORITY': 'NONE', 'REPORT_SHA256': '0' * 64,
        'DEPLOYMENT_GATE': 'HOLD', 'V021C6293_RESULT': RESULT_PASS,
    }
    grid = {f'VM_GRID_09:{i:02d}': ('FRESH/LOCAL' if i in (0,30,35) else 'GAP')
            for i in range(0, 36, 5)}
    return (HEADER + '\n' + '\n'.join(f'{k}={v}' for k, v in rows.items()) + '\n' +
            '\n'.join(f'{k}={v}' for k, v in grid.items()) + '\n').encode('ascii')


def alter(key, value):
    lines = fixture().decode().splitlines()
    for i, line in enumerate(lines):
        if line.startswith(key + '='):
            lines[i] = key + '=' + value
            return ('\n'.join(lines) + '\n').encode('ascii')
    raise AssertionError('missing fixture key ' + key)


class Tests(unittest.TestCase):
    def h(self, raw, reason):
        with self.assertRaises(Hold) as caught:
            parse_cli(raw, origin=ORIGIN_FIXTURE)
        self.assertEqual(str(caught.exception), reason)

    def test_01_complete_synthetic(self):
        self.assertEqual(parse_cli(fixture(), origin=ORIGIN_FIXTURE)['assessment_status'],
                         'CROSS_SOURCE_TEMPORAL_CORRELATION_ONLY')
    def test_02_no_resumption_claim(self):
        self.assertEqual(parse_cli(fixture(), origin=ORIGIN_FIXTURE)['sampled_collection_resumption'],
                         'NOT_ESTABLISHED')
    def test_03_no_attestation(self):
        self.assertFalse(parse_cli(fixture(), origin=ORIGIN_FIXTURE)['clock_and_source_provenance_attested'])
    def test_04_no_dns_proof(self):
        self.assertEqual(parse_cli(fixture(), origin=ORIGIN_FIXTURE)['dns_health'],'NOT_ESTABLISHED')
    def test_05_no_acl_proof(self):
        self.assertTrue(parse_cli(fixture(), origin=ORIGIN_FIXTURE)['historical_policy_not_live_proof'])
    def test_06_no_model_authority(self):
        x=parse_cli(fixture(), origin=ORIGIN_FIXTURE)
        self.assertEqual((x['model_action_authority'],x['deployment_gate']),('NONE','HOLD'))
    def test_07_input_hash_consistent(self):
        self.assertEqual(parse_cli(fixture(), origin=ORIGIN_FIXTURE)['input_sha256'],
                         hashlib.sha256(fixture()).hexdigest())
    def test_08_strict_origin(self):
        self.h(fixture().replace(b'SOURCE=',b'BAD_SOURCE=',1),'UNREVIEWED_REPORT_FIELD')
    def test_09_wrong_header(self):
        self.h(fixture().replace(HEADER.encode(),b'OTHER',1),'REPORT_HEADER_OR_LINE_COUNT_INVALID')
    def test_10_private_extra_field_rejected(self):
        self.h(fixture()+b'WIFI_SSID=secret\n','UNREVIEWED_REPORT_FIELD')
    def test_11_duplicate_key(self):
        self.h(fixture()+b'VM_GAP_SLOTS=5\n','FIELD_DUPLICATE_OR_VALUE_INVALID')
    def test_12_missing_key(self):
        self.h(fixture().replace(b'ROOT_CAUSE=UNDETERMINED\n',b''),'REPORT_FIELDS_INCOMPLETE')
    def test_13_non_ascii(self):
        self.h(fixture()+bytes([0xff]),'NON_ASCII_INPUT')
    def test_14_oversized(self):
        self.h(fixture()+b'A'*MAX_INPUT_BYTES,'INPUT_SIZE_INVALID')
    def test_15_hash_format(self):
        self.h(alter('REPORT_SHA256','nope'),'HASH_FORMAT_INVALID')
    def test_16_live_acl_spoof(self):
        self.h(alter('LIVE_ROUTER_ACL_AT_INCIDENT','VERIFIED'),'INVARIANT_LIVE_ROUTER_ACL_AT_INCIDENT')
    def test_17_root_cause_spoof(self):
        self.h(alter('ROOT_CAUSE','KNOWN'),'INVARIANT_ROOT_CAUSE')
    def test_18_action_spoof(self):
        self.h(alter('MODEL_ACTION_AUTHORITY','ADMIN'),'INVARIANT_MODEL_ACTION_AUTHORITY')
    def test_19_deploy_spoof(self):
        self.h(alter('DEPLOYMENT_GATE','OPEN'),'INVARIANT_DEPLOYMENT_GATE')
    def test_20_grid_wrong_count(self):
        self.h(alter('VM_FRESH_SLOTS','4'),'GRID_SLOT_COUNT_CONTRADICTION')
    def test_21_invalid_grid_state(self):
        self.h(alter('VM_GRID_09:05','HEALTHY'),'GRID_VALUE_INVALID')
    def test_22_duplicate_grid(self):
        self.h(fixture()+b'VM_GRID_09:05=GAP\n','GRID_DUPLICATE_OR_LIMIT')
    def test_23_grid_times_bad(self):
        self.h(fixture().replace(b'VM_GRID_09:05=',b'VM_GRID_09:06='),'GRID_TIMES_INCONSISTENT')
    def test_24_grid_interval_bad(self):
        self.h(alter('WINDOW_VM_CET','2030-02-13T09:00..09:40'),'GRID_INTERVAL_INVALID')
    def test_25_overlap_contradiction(self):
        self.h(alter('VM_GAPS_OVERLAP_SSH_WIFI_WINDOW','NO'),'OVERLAP_CONTRADICTION')
    def test_26_post_count_contradiction(self):
        self.h(alter('VM_FRESH_SLOTS_AFTER_WIFI','1'),'POST_WIFI_GRID_COUNT_CONTRADICTION')
    def test_27_ssh_chronology(self):
        self.h(alter('FIRST_SSH_TIMEOUT_LOCAL','2030-02-13T09:27:11+0100'), 'JOURNAL_CHRONOLOGY_CONTRADICTION')
    def test_28_result_contradiction(self):
        self.h(alter('V021C6293_RESULT','HOLD_INSUFFICIENT_CROSS_SOURCE_EVIDENCE'),'STATUS_RESULT_CONTRADICTION')
    def test_29_broken_journal_time(self):
        self.h(alter('WIFI_RECONNECT_LOCAL','2030-02-13T99:25:42+0100'),'TIMESTAMP_INVALID_WIFI')
    def test_30_policy_date_invalid(self):
        self.h(alter('HISTORICAL_ACCESS_RESTRICTION_SNAPSHOT_DATE','2030-02-30'),'POLICY_DATE_INVALID')
    def test_31_policy_after_incident(self):
        self.h(alter('HISTORICAL_ACCESS_RESTRICTION_SNAPSHOT_DATE','2030-02-13'),'DATED_POLICY_NOT_HISTORICAL')
    def test_32_clock_origin_not_privileged(self):
        x=parse_cli(fixture(), origin=ORIGIN_OPERATOR)
        self.assertEqual(x['evidence_origin'],ORIGIN_OPERATOR)
        self.assertEqual(x['source_pin_claim'],'SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED')
    def test_33_no_raw_sample_timestamp_assertion(self):
        x=parse_cli(fixture(), origin=ORIGIN_OPERATOR)
        self.assertEqual(x['two_distinct_post_gap_raw_sample_timestamps'],'NOT_AVAILABLE_IN_C62_CLI')
    def test_34_no_network_or_service_contact(self):
        self.assertFalse(parse_cli(fixture(),origin=ORIGIN_FIXTURE)['host_services_contacted_by_c63_1'])
    def test_35_grid_overcount(self):
        self.h(alter('VM_OBSERVATION_SLOTS','9'),'GRID_SLOT_COUNT_CONTRADICTION')
    def test_36_report_claim_not_attestation(self):
        self.assertEqual(parse_cli(fixture(),origin=ORIGIN_FIXTURE)['source_report_hash_claim'],
                         'PRESENT_UNVERIFIED')
    def test_37_one_post_gap_fresh(self):
        raw=fixture().decode().replace('VM_GRID_09:35=FRESH/LOCAL','VM_GRID_09:35=GAP')
        raw=raw.replace('VM_FRESH_SLOTS=3','VM_FRESH_SLOTS=2').replace('VM_GAP_SLOTS=5','VM_GAP_SLOTS=6')
        raw=raw.replace('VM_FRESH_SLOTS_AFTER_WIFI=2','VM_FRESH_SLOTS_AFTER_WIFI=1')
        x=parse_cli(raw.encode(),origin=ORIGIN_FIXTURE)
        self.assertEqual(x['sampled_collection_resumption'],'NOT_ESTABLISHED')
    def test_38_reject_unsupported_report_status(self):
        self.h(alter('STATUS','DNS_OUTAGE_PROVEN'),'STATUS_UNKNOWN')
    def test_39_journal_missing_counter(self):
        self.h(alter('JOURNAL_WIFI_RECONNECT_EVENTS','0'),'JOURNAL_COUNTERS_CONTRADICTION')
    def test_40_no_historical_overreach(self):
        x=parse_cli(fixture(),origin=ORIGIN_OPERATOR)
        self.assertEqual(x['root_cause'],'UNDETERMINED')
        self.assertEqual(x['interpretation'],'HISTORICAL_OPERATOR_SUPPLIED_CLI_UNVERIFIED_NOT_CURRENT_HEALTH')
    def test_41_reject_wrong_timezone(self):
        self.h(alter('WIFI_RECONNECT_LOCAL','2030-02-13T09:25:42+0200'),'TIMESTAMP_NOT_CET_WIFI')
    def test_42_reject_unknown_origin(self):
        with self.assertRaisesRegex(Hold,'ORIGIN_INVALID'):
            parse_cli(fixture(),origin='TRUSTED_LIVE')
    def test_43_reject_crafted_raw_line(self):
        self.h(fixture()+b'VM_GRID_09:00=FRESH/LOCAL;rm -rf /\n','GRID_DUPLICATE_OR_LIMIT')
    def test_44_reject_missing_grid_slot(self):
        self.h(fixture().replace(b'VM_GRID_09:15=GAP\n',b''),'GRID_SLOT_COUNT_CONTRADICTION')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--self-test', action='store_true')
    group.add_argument('--fixture-matrix', action='store_true')
    group.add_argument('--assess-stdin',action='store_true',help='Operator-supplied C62.9.3 CLI text on stdin; no live reads')
    args=p.parse_args(argv)
    print('=== LOCAL AI AGENT C.63.1 / C62 CLI OFFLINE BRIDGE ===')
    print('NO_NETWORK=YES NO_HOST_SERVICES=YES NO_SUBPROCESS=YES MODEL_CONTACTED=NO')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    if args.self_test:
        res=unittest.TextTestRunner(verbosity=0).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        print(f'C631_SELFTESTS={res.testsRun-len(res.failures)-len(res.errors)}/{res.testsRun}')
        print('C631_RESULT='+('PASS_SYNTHETIC_ONLY' if res.wasSuccessful() and res.testsRun==44 else 'HOLD'))
        return 0 if res.wasSuccessful() and res.testsRun==44 else 1
    try:
        if args.fixture_matrix:
            report=parse_cli(fixture(), origin=ORIGIN_FIXTURE)
            print('FIXTURE=SYNTHETIC_C62_CLI_SHAPE')
        else:
            raw=sys.stdin.buffer.read(MAX_INPUT_BYTES+1)
            report=parse_cli(raw,origin=ORIGIN_OPERATOR)
        # Report includes no raw CLI timestamps/host identifiers, no hostname, IP or raw logs.
        print(json.dumps(report,sort_keys=True,ensure_ascii=True,indent=2))
        print('C631_RESULT=' + ('PASS_SYNTHETIC_C62_CLI_COMPAT_ONLY' if args.fixture_matrix else 'PASS_OPERATOR_HISTORICAL_CLI_UNVERIFIED_ONLY'))
        return 0
    except Hold as err:
        print('C631_RESULT=HOLD_'+str(err))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
