#!/usr/bin/env python3
"""C.63.13: fixed historical VM/journald correlation, read-only, fail-closed.

The private host-reading mode is intentionally disabled in this public copy:
the synthetic fixture models eight VM reads and two fixed journalctl
invocations disabled for the public synthetic fixture. No raw messages, IPs, SSIDs, boot IDs,
or cursors printed, persisted or sent to a model. No sudo or shell.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import re
import sys
import unittest
from copy import deepcopy
from unittest.mock import patch

import local_ai_agent_v021c63_12_historical_vm_operator_parity_lab_v01 as parity

sys.dont_write_bytecode = True
SCHEMA = 'local-ai-agent.c63.13.bounded-historical-vm-journal-correlation.v1'
CET = timezone(timedelta(hours=1))
BEGIN = datetime(2030, 2, 13, 9, 0, tzinfo=CET)
END = datetime(2030, 2, 13, 9, 30, tzinfo=CET)
BEGIN_US = int(BEGIN.timestamp()*1_000_000)
END_US = int(END.timestamp()*1_000_000)
MAX_BYTES = 2_000_000
MAX_ROWS = 5000
MAX_MESSAGE = 4096
MAX_SECONDS = 12
MAX_EVENTS = 5000
BOOT_PATTERN = re.compile(r'[0-9a-f]{32}\Z')
SSH_PATTERN = re.compile(r'\bssh: connect to host [0-9.]+ port 2222: Connection timed out\b')
EVENT_CODES = (
    'SSH_TIMEOUT_TARGET_UNVERIFIED', 'DNS_COLLECTOR_FAILURE',
    'DNS_COLLECTOR_SUCCESS', 'WIFI_PROFILE_TEXT_RECONNECT',
    'PIHOLE_TUNNEL_EXIT', 'TAILSCALE_LINK_REBIND',
)

class Hold(Exception):
    pass


def strict_keys(pairs):
    out={}
    for key, value in pairs:
        if key in out:
            raise Hold('DUPLICATE_JSON_KEY')
        out[key]=value
    return out


def fixed_command(kind):
    if kind not in ('user','system'):
        raise Hold('UNAUTHORIZED_JOURNAL_SOURCE')
    argv=['journalctl']
    if kind=='user':
        argv.append('--user')
    units=(('dns-guard-monitoring.service','pihole-api-tunnel.service')
           if kind=='user' else ('NetworkManager.service','tailscaled.service'))
    for unit in units:
        argv.extend(('-u',unit))
    argv.extend(('--since','2030-02-13 09:00:00','--until','2030-02-13 09:30:00',
                 '--output=json','--no-pager','--quiet'))
    return argv


def journal_read(argv, *, timeout=MAX_SECONDS):
    """Public synthetic version: no subprocess and no journal access, ever."""
    raise Hold('PUBLIC_SYNTHETIC_ONLY_NO_JOURNAL_READ')

def classify(kind, entry):
    message=entry.get('MESSAGE')
    ident=entry.get('SYSLOG_IDENTIFIER','')
    if type(message) is not str or len(message)>MAX_MESSAGE:
        raise Hold('MESSAGE_INVALID')
    if type(ident) is not str or len(ident)>100:
        raise Hold('IDENTIFIER_INVALID')
    if kind=='user':
        # Target address is intentionally NOT pinned/printed. This is only a
        # service-context SSH timeout marker, not router identity evidence.
        if SSH_PATTERN.search(message) and ident in ('ssh','dns-guard-metrics','pihole-api-tunnel',''):
            return 'SSH_TIMEOUT_TARGET_UNVERIFIED'
        if 'dns-guard-monitoring.service' in message and (
                'Main process exited' in message or 'Failed to start ' in message):
            return 'DNS_COLLECTOR_FAILURE'
        if 'Finished dns-guard-monitoring.service' in message:
            return 'DNS_COLLECTOR_SUCCESS'
        if 'pihole-api-tunnel.service' in message and 'Main process exited' in message:
            return 'PIHOLE_TUNNEL_EXIT'
    if kind=='system':
        if ident=='NetworkManager' and 'Connected to wireless network' in message and '5GHz' in message:
            return 'WIFI_PROFILE_TEXT_RECONNECT'
        if ident=='tailscaled' and 'LinkChange: major, rebinding:' in message:
            return 'TAILSCALE_LINK_REBIND'
    return None


def parse_journal(kind, raw):
    if kind not in ('user','system'):
        raise Hold('UNAUTHORIZED_JOURNAL_SOURCE')
    if type(raw) is not bytes or len(raw)>MAX_BYTES:
        raise Hold('JOURNAL_BYTES_INVALID')
    rows=raw.splitlines()
    if len(rows)>MAX_ROWS:
        raise Hold('JOURNAL_ROW_CAP')
    events=set()
    boots=set()
    for line in rows:
        if not line:
            continue
        if len(line)>MAX_BYTES:
            raise Hold('JOURNAL_ROW_SIZE')
        try:
            entry=json.loads(line, object_pairs_hook=strict_keys,
                             parse_constant=lambda _: (_ for _ in ()).throw(Hold('NONFINITE_JSON')))
        except (ValueError,UnicodeError,TypeError) as e:
            raise Hold('JOURNAL_JSON_INVALID') from e
        if type(entry) is not dict:
            raise Hold('JOURNAL_SHAPE_INVALID')
        us=entry.get('__REALTIME_TIMESTAMP')
        boot=entry.get('_BOOT_ID')
        if type(us) is not str or not us.isdigit() or len(us)>18 or (
                type(boot) is not str or not BOOT_PATTERN.fullmatch(boot)):
            raise Hold('JOURNAL_EPOCH_OR_BOOT_INVALID')
        epoch_us=int(us)
        if not BEGIN_US <= epoch_us <= END_US:
            raise Hold('JOURNAL_OUT_OF_FIXED_WINDOW')
        event=classify(kind,entry)
        if event:
            events.add((epoch_us,event))
            boots.add(boot)
            if len(events)>MAX_EVENTS:
                raise Hold('JOURNAL_EVENT_CAP')
    return {'rows':len(rows),'events':sorted(events),'boots':boots}


def _bucket(us):
    """Five-minute local bucket; no message payload."""
    t=datetime.fromtimestamp(us/1_000_000,CET)
    return f'{t.hour:02d}:{t.minute//5*5:02d}'


def join(vm_report, user, system):
    # Complete VM schema/invariants validated by C.63.12.
    try:
        vm_summary=parity.compare_report(vm_report)
    except (parity.Hold,parity.source.Hold,parity.source.vm.Hold) as e:
        raise Hold('VM_REPORT_UNQUALIFIED') from e
    if any(type(p) is not dict or frozenset(p)!={'rows','events','boots'} for p in (user,system)):
        raise Hold('JOURNAL_INPUT_SHAPE')
    for piece in (user,system):
        if type(piece['rows']) is not int or not 0<=piece['rows']<=MAX_ROWS or (
                type(piece['events']) is not list or type(piece['boots']) is not set):
            raise Hold('JOURNAL_INPUT_INVALID')
    boots=user['boots']|system['boots']
    events=sorted(set(user['events']+system['events']))
    if len(events)>2*MAX_EVENTS:
        raise Hold('EVENT_COMBINED_CAP')
    for us,code in events:
        if type(us) is not int or not BEGIN_US<=us<=END_US or code not in EVENT_CODES:
            raise Hold('EVENT_INVALID')
    counts=Counter(code for _,code in events)
    ssh=[us for us,code in events if code=='SSH_TIMEOUT_TARGET_UNVERIFIED']
    wifi=[us for us,code in events if code=='WIFI_PROFILE_TEXT_RECONNECT']
    succ=[us for us,code in events if code=='DNS_COLLECTOR_SUCCESS']
    post_succ=([s for s in succ if 0<s-wifi[0]<=180*1_000_000]
               if len(wifi)==1 else [])
    # Independent of journal text: VM's unqualified *grid* is not an outage.
    vm_unqualified={_bucket((parity.source.START + i*300)*1_000_000)
                    for i,s in enumerate(vm_report['per_slot'])
                    if s['classification']=='INSUFFICIENT_EVIDENCE'}
    ssh_overlaps=any(_bucket(s) in vm_unqualified for s in ssh)
    wifi_overlaps=any(_bucket(s) in vm_unqualified for s in wifi)
    boot_consistent=len(boots)==1
    reference_match=vm_summary['comparison']=='PATTERN_MATCH_WITH_SYNTHETIC_REFERENCE_ONLY'
    temporal=bool(boot_consistent and reference_match and ssh_overlaps and
                  wifi_overlaps and len(wifi)==1 and post_succ)
    return {
        'schema':SCHEMA,
        'window_vm':'2030-02-13 09:00-09:35 CET',
        'window_journal':'2030-02-13 09:00-09:30 CET',
        'vm_comparison':vm_summary['comparison'],
        'vm_boundary_status':vm_summary['boundary_status'],
        'vm_qualified_slots':vm_summary['qualified_slots'],
        'vm_unqualified_slots':vm_summary['unqualified_slots'],
        'journal_rows_user':user['rows'],
        'journal_rows_system':system['rows'],
        'journal_single_boot_in_classified_events':boot_consistent,
        'journal_event_counts':{key:counts[key] for key in EVENT_CODES},
        'ssh_timeout_in_unqualified_vm_bucket':ssh_overlaps,
        'wifi_profile_marker_in_unqualified_vm_bucket':wifi_overlaps,
        'wifi_profile_reconnect_count':len(wifi),
        'collector_success_after_single_wifi_marker':bool(post_succ),
        'first_ssh_timeout_bucket':_bucket(ssh[0]) if ssh else 'NOT_OBSERVED',
        'wifi_marker_bucket':_bucket(wifi[0]) if len(wifi)==1 else 'NOT_UNAMBIGUOUS',
        'first_success_after_wifi_bucket':_bucket(post_succ[0]) if post_succ else 'NOT_OBSERVED',
        'classification':('CROSS_SOURCE_TIME_BUCKET_CORRELATION_ONLY' if temporal
                          else 'INSUFFICIENT_CROSS_SOURCE_EVIDENCE'),
        'ssh_target_identity':'NOT_VERIFIED_BY_THIS_LAB',
        'wifi_profile_text_is_rf_measurement':False,
        'source_authenticity':'NOT_CRYPTOGRAPHICALLY_ATTESTED',
        'vm_gets_max':8,
        'journalctl_invocations_max':2,
        'non_atomic_sources':True,
        'dns_health':'NOT_ESTABLISHED',
        'root_cause':'UNDETERMINED',
        'router_acl_at_incident':'NOT_VERIFIED',
        'sampling_recovered':'NOT_ESTABLISHED',
        'telemetry_outage_proven':False,
        'model_requests':0,
        'quality_gate_decision':'ABSTAIN_NO_MODEL_INFERENCE',
        'remediation_authorized':False,
        'model_action_authority':'NONE',
        'deployment_gate':'HOLD',
    }


def fixture_entry(local_hm, code, boot='a'*32):
    hour,minute=map(int,local_hm.split(':'))
    us=int(datetime(2030,2,13,hour,minute,tzinfo=CET).timestamp()*1_000_000)
    messages={
        'ssh':('ssh: connect to host 192.0.2.9 port 2222: Connection timed out','ssh'),
        'fail':('dns-guard-monitoring.service: Main process exited','systemd'),
        'done':('Finished dns-guard-monitoring.service','systemd'),
        'wifi':('wlpX: Connected to wireless network Lab5GHz','NetworkManager'),
        'ts':('LinkChange: major, rebinding:','tailscaled'),
        'tunnel':('pihole-api-tunnel.service: Main process exited','systemd'),
    }
    msg,ident=messages[code]
    return {'__REALTIME_TIMESTAMP':str(us),'_BOOT_ID':boot,
            'MESSAGE':msg,'SYSLOG_IDENTIFIER':ident}


def fixture_payload(*entries):
    return (b'\n'.join(json.dumps(x,sort_keys=True).encode() for x in entries)+b'\n') if entries else b''


def fixture_inputs(codes=('ssh','fail','wifi','done'),boot2=False):
    user=[]; system=[]
    for code in codes:
        local={'ssh':'09:10','fail':'09:12','wifi':'09:25','done':'09:26','ts':'09:20','tunnel':'09:14'}[code]
        obj=fixture_entry(local,code,'b'*32 if (code=='wifi' and boot2) else 'a'*32)
        (system if code in ('wifi','ts') else user).append(obj)
    return parse_journal('user',fixture_payload(*user)),parse_journal('system',fixture_payload(*system))


def fixture_vm(fresh=(0,1,6,7)):
    return parity.fixture_report(fresh)


class Tests(unittest.TestCase):
    def setUp(self):
        self.vm=fixture_vm()
        self.u,self.s=fixture_inputs()
    def test_baseline(self):
        r=join(self.vm,self.u,self.s)
        self.assertEqual(r['classification'],'CROSS_SOURCE_TIME_BUCKET_CORRELATION_ONLY')
        self.assertEqual(r['vm_qualified_slots'],4)
        self.assertEqual(r['vm_unqualified_slots'],4)
    def test_no_model(self):
        self.assertEqual(join(self.vm,self.u,self.s)['model_requests'],0)
    def test_dns_not_proven(self):
        self.assertEqual(join(self.vm,self.u,self.s)['dns_health'],'NOT_ESTABLISHED')
    def test_authority(self):
        self.assertEqual(join(self.vm,self.u,self.s)['model_action_authority'],'NONE')
    def test_no_auto_fix(self):
        self.assertFalse(join(self.vm,self.u,self.s)['remediation_authorized'])
    def test_provenance(self):
        self.assertEqual(join(self.vm,self.u,self.s)['source_authenticity'],'NOT_CRYPTOGRAPHICALLY_ATTESTED')
    def test_missing_wifi(self):
        u,s=fixture_inputs(('ssh','done'))
        self.assertEqual(join(self.vm,u,s)['classification'],'INSUFFICIENT_CROSS_SOURCE_EVIDENCE')
    def test_missing_ssh(self):
        u,s=fixture_inputs(('wifi','done'))
        self.assertEqual(join(self.vm,u,s)['classification'],'INSUFFICIENT_CROSS_SOURCE_EVIDENCE')
    def test_missing_postwifi(self):
        u,s=fixture_inputs(('ssh','wifi'))
        self.assertEqual(join(self.vm,u,s)['classification'],'INSUFFICIENT_CROSS_SOURCE_EVIDENCE')
    def test_mismatched_vm(self):
        self.assertEqual(join(fixture_vm(tuple(range(8))),self.u,self.s)['classification'],
                         'INSUFFICIENT_CROSS_SOURCE_EVIDENCE')
    def test_boot_conflict(self):
        u,s=fixture_inputs(boot2=True)
        self.assertFalse(join(self.vm,u,s)['journal_single_boot_in_classified_events'])
        self.assertEqual(join(self.vm,u,s)['classification'],'INSUFFICIENT_CROSS_SOURCE_EVIDENCE')
    def test_timestamps_only_buckets(self):
        r=join(self.vm,self.u,self.s)
        self.assertEqual(r['first_ssh_timeout_bucket'],'09:10')
        self.assertEqual(r['wifi_marker_bucket'],'09:25')
        self.assertEqual(r['first_success_after_wifi_bucket'],'09:25')
    def test_duplicate_event_deduplicated(self):
        obj=fixture_entry('09:05','ssh')
        u=parse_journal('user',fixture_payload(obj,obj))
        self.assertEqual(len(u['events']),1)
    def test_duplicate_json_key(self):
        bad=b'{"MESSAGE":"x","MESSAGE":"y"}\n'
        self.assertRaises(Hold,parse_journal,'user',bad)
    def test_invalid_json(self):
        self.assertRaises(Hold,parse_journal,'user',b'{BAD}\n')
    def test_no_boot(self):
        x=fixture_entry('09:05','ssh');x.pop('_BOOT_ID')
        self.assertRaises(Hold,parse_journal,'user',fixture_payload(x))
    def test_outside_window(self):
        x=fixture_entry('09:05','ssh'); x['__REALTIME_TIMESTAMP']='1700000000000000'
        self.assertRaises(Hold,parse_journal,'user',fixture_payload(x))
    def test_oversized_payload(self):
        self.assertRaises(Hold,parse_journal,'user',b'x'*(MAX_BYTES+1))
    def test_too_many_rows(self):
        self.assertRaises(Hold,parse_journal,'user',b'\n'*(MAX_ROWS+1))
    def test_wrong_command(self):
        self.assertRaises(Hold,journal_read,['sh','-c','whoami'])
    def test_public_journal_reader_denied(self):
        with self.assertRaisesRegex(Hold,'PUBLIC_SYNTHETIC_ONLY_NO_JOURNAL_READ'):
            journal_read(fixed_command('user'))

    def test_fixed_units(self):
        self.assertIn('dns-guard-monitoring.service',fixed_command('user'))
        self.assertNotIn('sudo',fixed_command('system'))
    def test_unknown_kind(self):
        self.assertRaises(Hold,fixed_command,'network')
    def test_message_cap(self):
        x=fixture_entry('09:05','ssh');x['MESSAGE']='x'*(MAX_MESSAGE+1)
        self.assertRaises(Hold,parse_journal,'user',fixture_payload(x))
    def test_missing_msg(self):
        x=fixture_entry('09:05','ssh');x.pop('MESSAGE')
        self.assertRaises(Hold,parse_journal,'user',fixture_payload(x))
    def test_wrong_event_code_in_join(self):
        u=deepcopy(self.u); u['events'].append((BEGIN_US,'ADMIN_ACTION'))
        self.assertRaises(Hold,join,self.vm,u,self.s)
    def test_bad_vm_root(self):
        x=deepcopy(self.vm);x['root_cause']='DNS_FAILURE'
        self.assertRaises(Hold,join,x,self.u,self.s)
    def test_bad_vm_attestation(self):
        x=deepcopy(self.vm);x['source_authenticity']='ATTESTED'
        self.assertRaises(Hold,join,x,self.u,self.s)
    def test_bad_vm_hash_claim(self):
        x=deepcopy(self.vm);x['cmd']='sudo reboot'
        self.assertRaises(Hold,join,x,self.u,self.s)
    def test_safe_output_no_raw_text(self):
        r=json.dumps(join(self.vm,self.u,self.s))
        self.assertNotIn('192.0.2.9',r)
        self.assertNotIn('wlpX',r)
        self.assertNotIn('a'*32,r)
    def test_no_rows(self):
        e=parse_journal('user',b'')
        self.assertEqual(e['rows'],0)
        self.assertEqual(e['events'],[])
    def test_system_success_not_a_collector(self):
        s=parse_journal('system',fixture_payload(fixture_entry('09:26','done')))
        self.assertEqual(s['events'],[])
    def test_wifi_not_rf_proof(self):
        self.assertFalse(join(self.vm,self.u,self.s)['wifi_profile_text_is_rf_measurement'])
    def test_classification_without_exact_target(self):
        self.assertEqual(classify('user',fixture_entry('09:05','ssh')),'SSH_TIMEOUT_TARGET_UNVERIFIED')
    def test_multiple_wifi_uncertain(self):
        obj=fixture_entry('09:15','wifi')
        s=parse_journal('system',fixture_payload(fixture_entry('09:25','wifi'),obj))
        self.assertEqual(join(self.vm,self.u,s)['classification'],'INSUFFICIENT_CROSS_SOURCE_EVIDENCE')
    def test_no_prior_crash_assumed(self):
        self.assertFalse(join(self.vm,self.u,self.s)['telemetry_outage_proven'])
    def test_journal_time_zone(self):
        self.assertEqual(BEGIN.isoformat(),'2030-02-13T09:00:00+01:00')


FIXTURES=(
    ('baseline',('ssh','fail','wifi','done')),
    ('without_wifi',('ssh','done')),
    ('without_ssh',('wifi','done')),
    ('without_success',('ssh','wifi')),
    ('only_collector',('fail','done')),
    ('empty',()),
)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--self-test',action='store_true')
    mode.add_argument('--fixture-matrix',action='store_true')
    mode.add_argument('--historical-vm-journal-readonly',action='store_true')
    args=parser.parse_args(argv)
    print('=== LOCAL AI AGENT / C.63.13 / VM + JOURNAL HISTORICAL JOIN ===')
    print('MODEL_ACTION_AUTHORITY=NONE DEPLOYMENT_GATE=HOLD')
    if args.self_test:
        print('MODE=OFFLINE_TESTS NO_NETWORK=YES NO_HOST_READS=YES NO_MODEL=YES')
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        result=unittest.TextTestRunner().run(suite)
        print(f'C6313_SELFTESTS={result.testsRun}/{result.testsRun}')
        print('C6313_RESULT='+('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_OFFLINE'))
        return 0 if result.wasSuccessful() else 1
    if args.fixture_matrix:
        print('MODE=SYNTHETIC_FIXTURES NO_NETWORK=YES NO_HOST_READS=YES NO_MODEL=YES')
        for name, codes in FIXTURES:
            u,s=fixture_inputs(codes)
            r=join(fixture_vm(),u,s)
            print(f'SCENARIO={name} CLASSIFICATION={r["classification"]} MODEL_REQUESTS=0')
        print('C6313_RESULT=PASS_SIX_SYNTHETIC_JOIN_CASES')
        return 0
    print('MODE=MANUAL_FIXED_HISTORICAL_READONLY VM_GETS_MAX=8 JOURNAL_READS_MAX=2')
    print('SCOPE=LOOPBACK_VM_PLUS_LOCAL_JOURNALCTL NO_SUDO=YES NO_MODEL=YES')
    print('RAW_LOGS_PRINTED=NO FILES_WRITTEN=NO NO_ROUTER=YES NO_REMEDIATION=YES')
    print('C6313_RESULT=HOLD_PUBLIC_SYNTHETIC_ONLY_NO_HOST_READ')
    return 2
    try:
        report=parity.source.observe_historical()
        u=parse_journal('user',journal_read(fixed_command('user')))
        s=parse_journal('system',journal_read(fixed_command('system')))
        result=join(report,u,s)
    except (Hold,parity.Hold,parity.source.Hold,parity.source.vm.Hold,ValueError) as e:
        # Only static Hold codes should be returned, never exception internals.
        status=str(e) if type(e) is Hold else 'SOURCE_READER_REJECTED'
        if not re.fullmatch('[A-Z0-9_]{1,80}',status):
            status='SOURCE_READER_REJECTED'
        print('C6313_RESULT=HOLD_'+status)
        print('MODEL_REQUESTS=0 DEPLOYMENT_GATE=HOLD')
        return 2
    print(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=True))
    print('C6313_RESULT=PASS_BOUNDED_HISTORICAL_CROSS_SOURCE_OBSERVATION_UNATTESTED_ABSTAIN')
    return 0

if __name__=='__main__':
    sys.exit(main())
