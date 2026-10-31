#!/usr/bin/env python3
"""Local AI Agent V0.21C.61.1 — bounded historical real-source bridge.

Offline contract and optional manual C57 read-only historical preflight. Never
casts historical records as fresh C61 synthetic fixtures. No Qwen, executor,
ASUS or deployed HCC contact; no output files. Source identity is SHA-pinned;
VM/Loki origin is NOT cryptographically authenticated.
"""
from __future__ import annotations
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import stat
import sys
import types
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

sys.dont_write_bytecode = True
HERE = Path(__file__).absolute().parent
EXPECTED = {
    'c57': ('local_ai_agent_v021c57_consolidated_vm_loki_readonly_lab_v01.py',
            '758e5155c72136bca98371f59e3df01c3655d22401d9faada818b33934ef3115'),
    'c61': ('local_ai_agent_v021c61_multi_incident_host_fixture_lab_v01.py',
            'fcc6a5bbc526f4f49700411a133a8657976d80371f575b1ca17ae7d9c5dfa024'),
}
JOINT_SHA256 = '557914157204f5b888459efacb4f0e6f13489ad6b21a91042c3be7e76c675b83'
SCHEMA = 'local-ai-agent.multi-incident.historical-vm-loki-bridge.v1'
ORIGIN = 'LOOPBACK_HISTORICAL_C57_UNAUTHENTICATED'
CATEGORIES = ('dns_guard','pihole','unbound','tailscale','fedora')
GAPS = ('unbound','tailscale','fedora')
MAX_JSON = 4096
MAX_PIN_BYTES = 100000

class Hold(Exception):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii')


def load_pinned(label, root=HERE):
    if label not in EXPECTED:
        raise Hold('SOURCE_NOT_ALLOWLISTED')
    filename, sha = EXPECTED[label]
    path = root / filename
    try:
        meta = path.lstat()
        if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.getuid() or
                meta.st_mode & 0o022 or meta.st_nlink != 1 or
                not 100 <= meta.st_size <= MAX_PIN_BYTES):
            raise Hold('PINNED_SOURCE_OWNER_MODE_SIZE')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            meta2 = os.fstat(fd)
            def identity(m):
                return (m.st_dev, m.st_ino, m.st_size, m.st_uid,
                        m.st_mode, m.st_mtime_ns)
            if identity(meta) != identity(meta2):
                raise Hold('PINNED_SOURCE_RACE')
            raw = os.read(fd, MAX_PIN_BYTES + 1)
            if len(raw) != meta2.st_size or identity(meta2) != identity(os.fstat(fd)):
                raise Hold('PINNED_SOURCE_CHANGED')
        finally:
            os.close(fd)
    except OSError as exc:
        raise Hold('PINNED_SOURCE_UNAVAILABLE') from exc
    if hashlib.sha256(raw).hexdigest() != sha:
        raise Hold('PINNED_SOURCE_SHA256_MISMATCH_' + label.upper())
    module = types.ModuleType('c611_pinned_' + label)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def load_sources():
    return load_pinned('c57'), load_pinned('c61')


def bridge(c57, c61, metrics, counts):
    """Accept only C57-validated historic observations; NEVER call C61.classify()."""
    if (c61.ORIGIN != 'SYNTHETIC_FIXTURE_ONLY' or
        c61.SCHEMA_OUT != 'local-ai-agent.multi-incident.host-observation.v1' or
        c61.ALLOWED.get('dns_guard.mode') != ('enum', ('LOCAL','BOOTSTRAP','UNKNOWN')) or
        c61.ALLOWED.get('pihole.log_entries_1m') != ('count', None) or
        c61.CONDITIONS.get(('dns_guard.mode','BOOTSTRAP')) != 'DNS_GUARD_BOOTSTRAP_SAMPLED'):
        raise Hold('C61_SYNTHETIC_CONTRACT_DRIFT')
    vm = c57.derive_vm(metrics)
    obj, raw = c57.align(vm, counts)
    if hashlib.sha256(raw).hexdigest() != JOINT_SHA256:
        raise Hold('C57_BASELINE_HASH_MISMATCH')
    if (obj.get('schema') != c57.SCHEMA or obj.get('deployment_gate') != 'HOLD' or
        obj['source']['source_authenticated'] is not False or
        obj['source']['hcc_deployed_instance_contacted'] is not False or
        obj['source']['raw_log_lines_read'] is not False or
        obj['source']['model_or_executor_contacted'] is not False):
        raise Hold('C57_PROVENANCE_OR_SCHEMA')
    if (len(obj['transitions']) != 2 or
        tuple(e['event'] for e in obj['transitions']) !=
        ('BOOTSTRAP_OBSERVED','LOCAL_RESTORED') or
        obj['loki']['minute_bins'] != 15 or
        obj['loki']['minute_counts_sum'] != 726):
        raise Hold('HISTORICAL_EVENT_OR_COUNTS_INVALID')
    # Bound to the precise C57 aggregate bin, labelled by its END timestamp.
    bin_end = int(datetime(2026,10,27,16,2,tzinfo=timezone.utc).timestamp())
    idx = (bin_end - c57.LOKI_START) // 60
    if idx != 6 or c57.LOKI_START + idx*60 != bin_end:
        raise Hold('HISTORICAL_MINUTE_ALIGNMENT_CHANGED')
    count = counts[idx]
    if type(count) is not int or count != 141:
        raise Hold('HISTORICAL_MINUTE_COUNT_CHANGED')
    observations = [
        {'category':'dns_guard', 'signal':'dns_guard.mode',
         'condition':'DNS_GUARD_BOOTSTRAP_SAMPLED',
         'time_kind':'SAMPLED_TRANSITION_UNCERTAINTY_WINDOW',
         'start_cet':obj['transitions'][0]['uncertainty_window_start_cet'],
         'end_cet':obj['transitions'][0]['uncertainty_window_end_cet']},
        {'category':'dns_guard', 'signal':'dns_guard.mode',
         'condition':'DNS_GUARD_LOCAL_RESTORED_SAMPLED',
         'time_kind':'SAMPLED_TRANSITION_UNCERTAINTY_WINDOW',
         'start_cet':obj['transitions'][1]['uncertainty_window_start_cet'],
         'end_cet':obj['transitions'][1]['uncertainty_window_end_cet']},
        {'category':'pihole','signal':'pihole.log_entries_1m',
         'condition':'PIHOLE_LOG_ACTIVITY_SAMPLED_NOT_DNS_SUCCESS',
         'time_kind':'ONE_MINUTE_AGGREGATE_END',
         'end_cet':datetime.fromtimestamp(bin_end, timezone.utc).astimezone(c57.WARSAW).isoformat(timespec='seconds'),
         'count':count},
    ]
    record = {
        'schema':SCHEMA,
        'source_origin':ORIGIN,
        'source_authentication':'NOT_CRYPTOGRAPHICALLY_ATTESTED',
        'current_health_state':'NOT_EVALUATED_HISTORICAL_ONLY',
        'source_window_utc':obj['vm']['window_utc'],
        'source_joint_schema':c57.SCHEMA,
        'source_joint_sha256':JOINT_SHA256,
        'observed_categories':['dns_guard','pihole'],
        'unsupported_categories':[{'category':name,'reason':'NO_REAL_SOURCE_ADAPTER'} for name in GAPS],
        'observations':observations,
        'limits':['HISTORICAL_ONLY_NOT_CURRENT_TELEMETRY',
                  'C61_SYNTHETIC_CLASSIFIER_NOT_RUN_WITH_REAL_DATA',
                  'SAMPLED_TRANSITION_WINDOW_NOT_SWITCH_INSTANT',
                  'PIHOLE_COUNT_IS_FULL_MINUTE_NOT_SUCCESSFUL_DNS',
                  'NO_CAUSAL_LINK_OR_DNS_PATH_HEALTH_PROOF',
                  'NO_BASELINE_OR_CONTROL_PERIOD',
                  'NO_UNBOUND_TAILSCALE_FEDORA_MEASUREMENTS',
                  'NO_ATOMIC_SNAPSHOT_OR_SOURCE_ATTESTATION',
                  'FROZEN_HCC_OR_DEPLOYED_HCC_NOT_RUN'],
        'model_action_authority':'NONE',
        'deployment_gate':'HOLD',
    }
    payload = canonical(record)
    if len(payload) > MAX_JSON:
        raise Hold('BRIDGE_OUTPUT_TOO_LARGE')
    if list(record) != ['schema','source_origin','source_authentication','current_health_state',
                        'source_window_utc','source_joint_schema','source_joint_sha256',
                        'observed_categories','unsupported_categories','observations','limits',
                        'model_action_authority','deployment_gate']:
        raise Hold('BRIDGE_SCHEMA_KEY_DRIFT')
    return record, payload


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c57, cls.c61 = load_sources()

    def fixture(self):
        return self.c57.synthetic_vm(), self.c57.COUNTS_GOLDEN

    def validated(self):
        m,c=self.fixture()
        return bridge(self.c57,self.c61,m,c)

    def test_01_pin_source_57(self):
        self.assertEqual(EXPECTED['c57'][1],hashlib.sha256((HERE/EXPECTED['c57'][0]).read_bytes()).hexdigest())
    def test_02_pin_source_61(self):
        self.assertEqual(EXPECTED['c61'][1],hashlib.sha256((HERE/EXPECTED['c61'][0]).read_bytes()).hexdigest())
    def test_03_bridge_schema(self):self.assertEqual(self.validated()[0]['schema'],SCHEMA)
    def test_04_no_current_health(self):self.assertEqual(self.validated()[0]['current_health_state'],'NOT_EVALUATED_HISTORICAL_ONLY')
    def test_05_not_synthetic_origin(self):self.assertNotEqual(self.validated()[0]['source_origin'],self.c61.ORIGIN)
    def test_06_observed_only_two_categories(self):self.assertEqual(self.validated()[0]['observed_categories'],['dns_guard','pihole'])
    def test_07_unobserved_three_categories(self):self.assertEqual([x['category'] for x in self.validated()[0]['unsupported_categories']],list(GAPS))
    def test_08_three_records(self):self.assertEqual(len(self.validated()[0]['observations']),3)
    def test_09_first_window(self):self.assertEqual(self.validated()[0]['observations'][0]['start_cet'],'2026-10-27T17:01:35+01:00')
    def test_10_restore_window(self):self.assertEqual(self.validated()[0]['observations'][1]['end_cet'],'2026-10-27T17:05:55+01:00')
    def test_11_minute_count(self):self.assertEqual(self.validated()[0]['observations'][2]['count'],141)
    def test_12_minute_ended(self):self.assertEqual(self.validated()[0]['observations'][2]['end_cet'],'2026-10-27T17:02:00+01:00')
    def test_13_non_crypto(self):self.assertEqual(self.validated()[0]['source_authentication'],'NOT_CRYPTOGRAPHICALLY_ATTESTED')
    def test_14_action_none(self):self.assertEqual(self.validated()[0]['model_action_authority'],'NONE')
    def test_15_gate_hold(self):self.assertEqual(self.validated()[0]['deployment_gate'],'HOLD')
    def test_16_raw_hash(self):self.assertEqual(len(self.validated()[0]['source_joint_sha256']),64)
    def test_17_stable_canonical(self):
        obj, raw = self.validated()
        self.assertEqual(canonical(dict(reversed(list(obj.items())))), raw)
    def test_18_c61_not_used_as_live(self):
        m,c=self.fixture()
        with patch.object(self.c61,'classify',side_effect=AssertionError('NO_REAL_DATA_TO_SYNTHETIC')):
            self.assertEqual(bridge(self.c57,self.c61,m,c)[0]['schema'],SCHEMA)
    def test_19_no_model_on_bridge(self):
        m,c=self.fixture()
        with patch('http.client.HTTPConnection',side_effect=AssertionError('NO_NETWORK')):
            bridge(self.c57,self.c61,m,c)
    def test_20_missing_vm_held(self):
        m,c=self.fixture();del m[self.c57.VM_NAMES[0]][self.c57.VM_START]
        with self.assertRaises(self.c57.Hold):bridge(self.c57,self.c61,m,c)
    def test_21_invalid_vm_held(self):
        m,c=self.fixture();m[self.c57.VM_NAMES[1]][self.c57.VM_START]=0
        with self.assertRaises(self.c57.Hold):bridge(self.c57,self.c61,m,c)
    def test_22_loki_mutation_held(self):
        m,c=self.fixture();c=list(c);c[6]=142
        with self.assertRaises(self.c57.Hold):bridge(self.c57,self.c61,m,tuple(c))
    def test_23_loki_missing_held(self):
        m,c=self.fixture()
        with self.assertRaises(self.c57.Hold):bridge(self.c57,self.c61,m,c[:-1])
    def test_24_c61_drift_held(self):
        m,c=self.fixture()
        with patch.dict(self.c61.ALLOWED,{'dns_guard.mode':('enum',('LOCAL',))}):
            with self.assertRaises(Hold):bridge(self.c57,self.c61,m,c)
    def test_25_c61_origin_drift_held(self):
        m,c=self.fixture()
        with patch.object(self.c61,'ORIGIN','REAL_PROVENANCE'):
            with self.assertRaises(Hold):bridge(self.c57,self.c61,m,c)
    def test_26_c57_claim_drift_held(self):
        m,c=self.fixture()
        with patch.object(self.c57,'SCHEMA','SPOOFED'):
            with self.assertRaises(Hold):bridge(self.c57,self.c61,m,c)
    def test_27_loader_missing_held(self):
        with self.assertRaises(Hold):load_pinned('unexpected')
    def test_28_source_invalid_owner_or_size(self):
        with patch('os.getuid',return_value=-100):
            with self.assertRaises(Hold):load_pinned('c61')
    def test_29_source_tamper_held(self):
        class BadDigest:
            def hexdigest(self):return '0'*64
        with patch('hashlib.sha256',return_value=BadDigest()):
            with self.assertRaisesRegex(Hold,'PINNED_SOURCE_SHA256_MISMATCH_C61'):
                load_pinned('c61')
    def test_30_bad_json_from_vm_held(self):
        m,c=self.fixture()
        fake=lambda port,path:b'{' if port==self.c57.VM_PORT else self.c57.loki_payload(c)
        with self.assertRaises(self.c57.Hold):self.c57.vm_read(get=fake)
    def test_31_offline_bounded_read_gets(self):
        m,c=self.fixture();calls=[]
        def get(port,path):
            calls.append((port,path))
            if port==self.c57.VM_PORT:
                for name in self.c57.VM_NAMES:
                    if path==self.c57.vm_path(name):return self.c57.vm_payload(name,m[name])
            if port==self.c57.LOKI_PORT and path==self.c57.loki_path():return self.c57.loki_payload(c)
            raise AssertionError('UNEXPECTED_PATH')
        with patch('http.client.HTTPConnection',side_effect=AssertionError('NO_NETWORK')):
            mm=self.c57.vm_read(get=get)
            cc=self.c57.loki_parse(get(self.c57.LOKI_PORT,self.c57.loki_path()))
            o,_=bridge(self.c57,self.c61,mm,cc)
        self.assertEqual(len(calls),8)
        self.assertEqual(len(set(calls)),8)
        self.assertEqual(o['observations'][2]['count'],141)
    def test_32_json_length(self):self.assertLess(len(self.validated()[1]),MAX_JSON)
    def test_33_no_host_time_conversion(self):self.assertIn('2026-10-27',self.validated()[0]['source_window_utc'])
    def test_34_old_infrastructure_does_not_mean_power_off(self):self.assertIn('NO_UNBOUND_TAILSCALE_FEDORA_MEASUREMENTS',self.validated()[0]['limits'])
    def test_35_frozen_parity_not_claimed(self):self.assertIn('FROZEN_HCC_OR_DEPLOYED_HCC_NOT_RUN',self.validated()[0]['limits'])
    def test_36_causality_not_claimed(self):self.assertIn('NO_CAUSAL_LINK_OR_DNS_PATH_HEALTH_PROOF',self.validated()[0]['limits'])
    def test_37_bad_vm_http_payload_held(self):
        m,c=self.fixture()
        def get(port,path):raise self.c57.Hold('HTTP_UNAVAILABLE')
        with self.assertRaises(self.c57.Hold):self.c57.vm_read(get=get)
    def test_38_bad_loki_http_payload_held(self):
        with self.assertRaises(self.c57.Hold):self.c57.loki_parse(b'not json')
    def test_39_history_not_fresh_c61_fixture(self):
        hist=self.validated()[0]
        with self.assertRaises(self.c61.Hold):self.c61.classify(hist)
    def test_40_window_aggregate_not_event_count(self):
        hist=self.validated()[0]
        self.assertEqual(hist['observations'][2]['time_kind'],'ONE_MINUTE_AGGREGATE_END')
        self.assertNotIn('event_count',hist['observations'][2])


def selftest():
    # All tests use built-in fixtures and pinned local source reads only.
    with patch('http.client.HTTPConnection',side_effect=AssertionError('NETWORK_DURING_SELFTEST')):
        result=unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests))
    n=result.testsRun-len(result.failures)-len(result.errors)
    passed=result.wasSuccessful() and result.testsRun==40
    print(f'V021C611_SELFTESTS={n}/{result.testsRun}')
    print('NO_NETWORK_DURING_SELFTEST=YES')
    print('C61_SYNTHETIC_CLASSIFIER_FOR_LIVE_DATA=NOT_USED')
    print('DEPLOYMENT_GATE=HOLD')
    print('V021C611_SELFTEST_RESULT='+('PASS_OFFLINE_ONLY' if passed else 'HOLD'))
    return passed


def preflight():
    c57,c61=load_sources()
    metrics=c57.vm_read()
    counts=c57.loki_parse(c57.bounded_get(c57.LOKI_PORT,c57.loki_path()))
    result,raw=bridge(c57,c61,metrics,counts)
    print('=== V0.21C.61.1 / HISTORICAL OBSERVATION ADAPTER ===')
    print('C57_PIN_SHA256='+EXPECTED['c57'][1])
    print('C61_PIN_SHA256='+EXPECTED['c61'][1])
    print('SOURCE=C57_SEVEN_VM_ONE_LOKI_FIXED_LOOPBACK_GETS')
    print('SOURCE_WINDOW='+result['source_window_utc'])
    print('SOURCE_AUTHENTICATION=NO')
    print('HISTORICAL_NOT_LIVE_HEALTH=YES')
    print('SOURCE_JOINT_SHA256='+result['source_joint_sha256'])
    print('OBSERVED_CATEGORIES='+','.join(result['observed_categories']))
    print('UNOBSERVED_CATEGORIES='+','.join(x['category'] for x in result['unsupported_categories']))
    print('OBSERVATIONS='+str(len(result['observations'])))
    print('PIHOLE_FULL_MINUTE_END_1702_COUNT='+str(result['observations'][2]['count']))
    print('BRIDGE_SCHEMA='+result['schema'])
    print('BRIDGE_SHA256='+hashlib.sha256(raw).hexdigest())
    print('BRIDGE_BYTES='+str(len(raw)))
    print('VM_LOKI_RAW_LOG_LINES_READ=NO')
    print('OLLAMA_ASUS_HCC_EXECUTOR_PODMAN_CONTACTED=NO')
    print('FILES_WRITTEN=NO')
    print('MODEL_ACTION_AUTHORITY=NONE')
    print('DEPLOYMENT_GATE=HOLD')
    print('V021C611_RESULT=PASS_HISTORICAL_VM_LOKI_ADAPTER_ONLY')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--self-test',action='store_true')
    g.add_argument('--historical-adapter-preflight',action='store_true')
    args=ap.parse_args()
    if os.geteuid()==0:
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C611_RESULT=HOLD_ROOT_REFUSED')
        return 1
    if not selftest():
        print('V021C611_RESULT=HOLD_NOT_APPROVED')
        return 1
    if args.self_test:
        print('V021C611_RESULT=PASS_OFFLINE_CONTRACT_ONLY')
        return 0
    try:
        preflight()
        return 0
    except (Hold,OSError,ValueError,TypeError,KeyError,OverflowError) as exc:
        print('HOLD_REASON='+str(exc) if isinstance(exc,Hold) else 'HOLD_REASON='+type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C611_RESULT=HOLD_NOT_APPROVED')
        return 1

if __name__=='__main__':
    raise SystemExit(main())
