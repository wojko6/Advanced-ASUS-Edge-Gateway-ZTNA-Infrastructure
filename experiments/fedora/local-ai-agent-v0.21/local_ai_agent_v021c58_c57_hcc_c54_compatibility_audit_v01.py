#!/usr/bin/env python3
"""Local AI Agent V0.21C.58: isolated C57/HCC/C54 compatibility audit.

Standalone OPTIONAL verification script; C57 runtime stays consolidated.
Loads exactly three SHA256-pinned local sources: C57, C54, C48. Runs
frozen HCC *offline* model embedded in C48, not deployed HCC. C54 normalizes
host-constructed summary. Live mode uses C57's seven fixed VM loopback
historical GETs and one fixed Loki aggregate GET; no writes/model/executor.
Fail closed on mismatches; no proof of cryptographic source provenance.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import os
from pathlib import Path
import stat
import sys
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HOME = Path(__file__).absolute().parent
EXPECTED = {
    'c57': ('local_ai_agent_v021c57_consolidated_vm_loki_readonly_lab_v01.py',
            '758e5155c72136bca98371f59e3df01c3655d22401d9faada818b33934ef3115'),
    'c54': ('local_ai_agent_v021c54_minimal_host_evidence_contract_v01.py',
            '18e1274a050aa30a74ce8fff9d4f85f048964876f8dbb733ec7bce8369f28cca'),
    'c48': ('local_ai_agent_v021c48_frozen_hcc_event_model_parity_lab_v01.py',
            '2b6041ba6ceb50ce7df16e4ad496eae2b5cb2deb2424ed5196442cea55413e55'),
}
C55_EVIDENCE_SHA256 = '6855974fed1bdd9294893d18b2538b2e7713a78e2efa257e85a2d79cbb61c14d'
C57_JOINT_SHA256 = '557914157204f5b888459efacb4f0e6f13489ad6b21a91042c3be7e76c675b83'
HCC_BLOB_SHA1 = '03442de09a6492a20184f3b5f3d60caa18e8ae3e'

class Hold(Exception): pass

def load_one(key, *, root=HOME):
    name, pinned = EXPECTED[key]
    path = root/name
    try:
        if path.is_symlink():raise Hold('SOURCE_SYMLINK')
        st=path.lstat()
        if (not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_nlink!=1
            or st.st_mode&0o022 or not 100<=st.st_size<=100000):
            raise Hold('SOURCE_OWNER_MODE_SIZE')
        fd=os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            fs=os.fstat(fd)
            if (fs.st_ino,fs.st_dev,fs.st_size,fs.st_uid,fs.st_mode)!=(st.st_ino,st.st_dev,st.st_size,st.st_uid,st.st_mode):
                raise Hold('SOURCE_RACE')
            with os.fdopen(fd,'rb',closefd=False) as fh:source=fh.read(100001)
        finally:
            os.close(fd)
        if hashlib.sha256(source).hexdigest()!=pinned:raise Hold('PIN_SHA256_MISMATCH_'+key.upper())
        module=types.ModuleType('audit_pinned_'+key)
        module.__file__=str(path)
        exec(compile(source,str(path),'exec'),module.__dict__)
        return module
    except (OSError,UnicodeError,ValueError) as exc:
        raise Hold('PINNED_SOURCE_UNAVAILABLE_'+key.upper()) from exc

def load_all():
    return load_one('c57'),load_one('c54'),load_one('c48')

def as_hcc_rows(c57, metrics):
    """Convert already-validated C57 grid to HCC's seven-field collection records.

    Crucially deduplicate by collection timestamp after validating the full
    seven-field equality; never synthesize additional collection observations.
    """
    derived=c57.derive_vm(metrics)
    output=[]
    prev=None
    for t in range(c57.VM_START,c57.VM_END+1,c57.STEP):
        raw=tuple(metrics[name][t] for name in c57.VM_NAMES)
        if prev is not None and raw[0]==prev[0]:
            if raw!=prev:raise Hold('CONFLICTING_COLLECTION_REPLAY')
            continue
        col, valid, loc, boot, change, since, counter=raw
        output.append({'collection_epoch':col,'state_valid':valid,'mode_local':loc,
                       'mode_bootstrap':boot,'last_transition_epoch':change,
                       'fallback_since_epoch':since,'fallback_transitions_total':counter})
        prev=raw
    if len(output)!=derived['distinct_collections']:raise Hold('HCC_ROW_COUNT_MISMATCH')
    return derived,output

def event_windows(c57,c48,model,rows):
    if c48.HCC_GITHUB_BLOB_SHA1!=HCC_BLOB_SHA1:raise Hold('HCC_FROZEN_BLOB_MISMATCH')
    result=model.timeline(rows)
    if (type(result) is not dict or result.get('schema_version')!='dns-guard-events-offline/0.1'
        or result.get('deployment_gate')!='HOLD' or type(result.get('events')) is not list
        or result.get('event_count')!=len(result['events'])):
        raise Hold('HCC_MODEL_RESULT_INVALID')
    if len(result['events'])!=2:raise Hold('HCC_EVENT_COUNT_MISMATCH')
    accepted={model.BOOT:'BOOTSTRAP_OBSERVED',model.LOCAL:'LOCAL_RESTORED'}
    output=[]
    for event in result['events']:
        if (type(event) is not dict or event.get('event_type') not in accepted
            or event.get('status')!='OBSERVED' or event.get('confidence')!='BOUNDED_OBSERVATION'
            or event.get('coverage')!='SAMPLED_ONLY'):
            raise Hold('HCC_UNEXPECTED_OR_UNKNOWN_EVENT')
        def cet(s):
            if not isinstance(s,str) or not s.endswith('Z'):raise Hold('HCC_TIME_INVALID')
            return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(c57.WARSAW).isoformat(timespec='seconds')
        output.append((accepted[event['event_type']],cet(event['window_start']),cet(event['window_end'])))
    return tuple(output)

def c54_summary(c57,c54,vm,observed):
    # C54 is a separate strict validator; the summary is constructed by host,
    # not copied from C54's reference fixture.
    return {
        'schema':c54.INPUT_SCHEMA,
        'window_start_utc':'2026-10-27T15:40:00Z',
        'window_end_utc':'2026-10-27T16:40:00Z',
        'grid_step_seconds':c57.STEP,
        'grid_rows':vm['grid_rows'],
        'seven_metric_names':list(c54.METRICS),
        'seven_series_present_rows':vm['grid_rows'],
        'distinct_collections':vm['distinct_collections'],
        'repeated_collections':vm['repeated_collections'],
        'valid_local':vm['local_rows'],
        'valid_bootstrap':vm['bootstrap_rows'],
        'invalid':0,'stale':0,'missing':0,
        'observed_adjacent_changes':len(observed),
        'hcc_observed_events':len(observed),
        'hcc_unknown_events':0,'hcc_stale_events':0,
        'observed_event_order':[x[0] for x in observed],
    }

def audit(c57,c54,c48,metrics,counts):
    vm, rows=as_hcc_rows(c57,metrics)
    model=c48.verified_hcc_model()
    observed=event_windows(c57,c48,model,rows)
    if observed!=vm['windows']:raise Hold('C57_HCC_WINDOW_PARITY_FAIL')
    if c57.VM_START!=int(datetime.fromisoformat(c54.WINDOW_START.replace('Z','+00:00')).timestamp()):
        raise Hold('WINDOW_C54_MISMATCH')
    if c57.VM_END!=int(datetime.fromisoformat(c54.WINDOW_END.replace('Z','+00:00')).timestamp()):
        raise Hold('WINDOW_C54_MISMATCH')
    if set(c57.VM_NAMES)!=set(c54.METRICS):raise Hold('VM_METRIC_ALLOWLIST_MISMATCH')
    if observed!=c57.WINDOWS_GOLDEN:raise Hold('HCC_REFERENCE_WINDOWS_MISMATCH')
    summary=c54_summary(c57,c54,vm,observed)
    evidence=c54.normalize(summary,provenance_kind='CALLER_SUPPLIED_UNVERIFIED')
    if evidence.get('schema')!=c54.SCHEMA or evidence.get('deployment_gate')!='HOLD':
        raise Hold('C54_SCHEMA_RESULT_INVALID')
    if evidence.get('classification')!='FALLBACK_THEN_LOCAL_RESTORED_SAMPLED':
        raise Hold('C54_CLASSIFICATION_MISMATCH')
    eraw=c54.canonical(evidence)
    esha=hashlib.sha256(eraw).hexdigest()
    if esha!=C55_EVIDENCE_SHA256:raise Hold('C54_C55_EVIDENCE_PARITY_FAIL')
    joint,jraw=c57.align(vm,counts)
    jsha=hashlib.sha256(jraw).hexdigest()
    if jsha!=C57_JOINT_SHA256:raise Hold('C57_JOINT_BASELINE_FAIL')
    if joint['source']['hcc_event_model_executed'] is not False:
        raise Hold('C57_PROVENANCE_CONTRACT_CHANGED')
    if evidence['source']['source_authenticated_by_this_module'] is not False:
        raise Hold('SOURCE_AUTHORITY_ESCALATION')
    return {'vm':vm,'counts':counts,'windows':observed,'evidence_sha256':esha,
            'joint_sha256':jsha,'hcc_blob':HCC_BLOB_SHA1,
            'hcc_parity':'FROZEN_MODEL_SAMPLED_WINDOWS_CONCORDANT',
            'c54_contract':'INCIDENT_EVIDENCE_V1_VALIDATED_UNVERIFIED_PROVENANCE'}

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c57,cls.c54,cls.c48=load_all()
    def fixture(self):return self.c57.synthetic_vm(),self.c57.COUNTS_GOLDEN
    def check(self,metrics=None,counts=None):
        x,y=self.fixture()
        return audit(self.c57,self.c54,self.c48,x if metrics is None else metrics,y if counts is None else counts)
    def test_01_pins(self):self.assertEqual(len(EXPECTED),3)
    def test_02_frozen_model_blob(self):self.assertEqual(self.c48.HCC_GITHUB_BLOB_SHA1,HCC_BLOB_SHA1)
    def test_03_frozen_model_schema(self):self.assertEqual(self.c48.verified_hcc_model().SCHEMA,'dns-guard-events-offline/0.1')
    def test_04_hcc_collection_count(self):self.assertEqual(len(as_hcc_rows(self.c57,self.fixture()[0])[1]),56)
    def test_05_hcc_event_kind(self):self.assertEqual([x[0] for x in self.check()['windows']],['BOOTSTRAP_OBSERVED','LOCAL_RESTORED'])
    def test_06_c57_hcc_parity(self):self.assertEqual(self.check()['hcc_parity'],'FROZEN_MODEL_SAMPLED_WINDOWS_CONCORDANT')
    def test_07_c54_schema(self):self.assertEqual(self.check()['c54_contract'],'INCIDENT_EVIDENCE_V1_VALIDATED_UNVERIFIED_PROVENANCE')
    def test_08_c55_evidence_hash(self):self.assertEqual(self.check()['evidence_sha256'],C55_EVIDENCE_SHA256)
    def test_09_c57_joint_hash(self):self.assertEqual(self.check()['joint_sha256'],C57_JOINT_SHA256)
    def test_10_c54_provenance(self):
        d,c=self.fixture();v,_=as_hcc_rows(self.c57,d)
        r=self.c54.normalize(c54_summary(self.c57,self.c54,v,self.c57.WINDOWS_GOLDEN),provenance_kind='CALLER_SUPPLIED_UNVERIFIED')
        self.assertFalse(r['source']['source_authenticated_by_this_module'])
    def test_11_changed_loki_hold(self):
        x=list(self.fixture()[1]);x[0]+=1
        with self.assertRaises((Hold,self.c57.Hold)):self.check(counts=tuple(x))
    def test_12_missing_vm_hold(self):
        x,_=self.fixture();del x[self.c57.VM_NAMES[0]][self.c57.VM_START]
        with self.assertRaises(self.c57.Hold):self.check(metrics=x)
    def test_13_vm_mode_conflict_hold(self):
        x,_=self.fixture();x[self.c57.VM_NAMES[2]][self.c57.VM_START]=0
        with self.assertRaises(self.c57.Hold):self.check(metrics=x)
    def test_14_bad_replay_hold(self):
        x,_=self.fixture();t=self.c57.VM_START+3*60;x[self.c57.VM_NAMES[-1]][t]=1
        with self.assertRaises(self.c57.Hold):self.check(metrics=x)
    def test_15_hcc_windows_mismatch_hold(self):
        x,_=self.fixture();t=self.c57.VM_START+23*60;x[self.c57.VM_NAMES[0]][t]-=1
        with self.assertRaises(Hold):self.check(metrics=x)
    def test_16_hcc_unknown_rejected(self):
        m=self.c48.verified_hcc_model()
        with self.assertRaises(Hold):event_windows(self.c57,self.c48,m,[])
    def test_17_unexpected_c54_fields(self):
        x,_=self.fixture();v,_=as_hcc_rows(self.c57,x)
        d=c54_summary(self.c57,self.c54,v,self.c57.WINDOWS_GOLDEN);d['extra']='anything'
        with self.assertRaises(self.c54.Hold):self.c54.normalize(d,provenance_kind='CALLER_SUPPLIED_UNVERIFIED')
    def test_18_no_network_in_fixture(self):
        with patch('http.client.HTTPConnection',side_effect=AssertionError('OFFLINE_NETWORK')):
            self.check()
    def test_19_request_allowlist_offline(self):
        x,y=self.fixture();called=[]
        def fake(port,path):
            called.append((port,path))
            for n in self.c57.VM_NAMES:
                if port==self.c57.VM_PORT and path==self.c57.vm_path(n):return self.c57.vm_payload(n,x[n])
            if port==self.c57.LOKI_PORT and path==self.c57.loki_path():return self.c57.loki_payload(y)
            raise AssertionError('UNEXPECTED_GET')
        out=self.c57.vm_read(fake)
        counts=self.c57.loki_parse(fake(self.c57.LOKI_PORT,self.c57.loki_path()))
        self.assertEqual(len(called),8)
        audit(self.c57,self.c54,self.c48,out,counts)
    def test_20_report_not_auto_deploy(self):
        self.assertEqual(self.c54.normalize(self.c54.fixture(),provenance_kind='CALLER_SUPPLIED_UNVERIFIED')['deployment_gate'],'HOLD')

def selftest():
    with patch('http.client.HTTPConnection',side_effect=AssertionError('NETWORK_IN_SELFTEST')):
        result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    ok=result.wasSuccessful() and result.testsRun==20
    success=result.testsRun-len(result.errors)-len(result.failures)
    print(f'V021C58_SELFTESTS={success}/{result.testsRun}')
    print('NO_NETWORK_DURING_SELFTEST=YES')
    print('V021C58_SELFTEST_RESULT='+('PASS_OFFLINE_ONLY' if ok else 'HOLD'))
    return ok

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    opts=ap.add_mutually_exclusive_group(required=True)
    opts.add_argument('--self-test',action='store_true')
    opts.add_argument('--audit-live',action='store_true')
    args=ap.parse_args()
    if os.geteuid()==0:
        print('V021C58_RESULT=HOLD_ROOT_REFUSED');return 1
    if not selftest():
        print('DEPLOYMENT_GATE=HOLD');print('V021C58_RESULT=HOLD_NOT_APPROVED');return 1
    if args.self_test:
        print('DEPLOYMENT_GATE=HOLD');print('V021C58_RESULT=PASS_OFFLINE_COMPATIBILITY_TEST_ONLY');return 0
    try:
        c57,c54,c48=load_all()
        metrics=c57.vm_read()
        counts=c57.loki_parse(c57.bounded_get(c57.LOKI_PORT,c57.loki_path()))
        report=audit(c57,c54,c48,metrics,counts)
        print('=== V0.21C.58 / C57 FROZEN HCC + C54 COMPATIBILITY AUDIT ===')
        print('SOURCE_READ=PINNED_C57_SEVEN_VM_ONE_LOKI_FIXED_LOOPBACK_GETS')
        print('PINNED_LOCAL_SOURCES=C57,C54,C48')
        print('VM_GRID_ROWS='+str(report['vm']['grid_rows']))
        print('VM_LOCAL_ROWS='+str(report['vm']['local_rows']))
        print('VM_BOOTSTRAP_ROWS='+str(report['vm']['bootstrap_rows']))
        print('VM_DISTINCT_COLLECTIONS='+str(report['vm']['distinct_collections']))
        print('LOKI_AGGREGATE_MINUTES='+str(len(report['counts']))+'/15')
        print('LOKI_COUNT_TOTAL='+str(sum(report['counts'])))
        print('HCC_FROZEN_GIT_BLOB_SHA1='+report['hcc_blob'])
        print('HCC_SAMPLED_PARITY='+report['hcc_parity'])
        print('HCC_DEPLOYED_PARITY=NOT_TESTED')
        print('C54_EVIDENCE_SCHEMA=incident-evidence.v1')
        print('C54_VALIDATION='+report['c54_contract'])
        print('C54_EVIDENCE_SHA256='+report['evidence_sha256'])
        print('C57_JOINT_SHA256='+report['joint_sha256'])
        print('SOURCE_CRYPTOGRAPHIC_ATTESTATION=NO')
        print('RAW_LOG_LINES_READ=NO')
        print('OLLAMA_EXECUTOR_HCC_ASUS_CONTACTED=NO')
        print('FILES_WRITTEN=NO')
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C58_RESULT=PASS_C57_FROZEN_HCC_C54_COMPATIBILITY_AUDIT_ONLY')
        return 0
    except Exception as exc:
        # Pinned C57/C54/C48 each define their own Hold class. Fail closed
        # without traceback or source details on *any* dependency error.
        print('HOLD_REASON='+str(exc) if isinstance(exc,Hold) else 'HOLD_REASON=DEPENDENCY_OR_SOURCE_FAILED')
        print('DEPLOYMENT_GATE=HOLD')
        print('V021C58_RESULT=HOLD_NOT_APPROVED')
        return 1

if __name__=='__main__':sys.exit(main())
