#!/usr/bin/env python3
"""V0.21C.48: local VM seven-series vs pinned HCC offline-event-model diagnostics.

READ-ONLY manual lab. C47 and all earlier sources are SHA256-pinned, unchanged.
Host-only six fixed instant plus seven fixed range metric GET requests to local
VictoriaMetrics. No model, Ollama, shell, Podman, HCC server, router, writes,
executor, ACK, or automatic deploy. Embedded original HCC offline model is a
frozen exact Git blob snapshot, not proof of parity with deployed HCC or of
unobserved transitions. Duplicated scrapes may be deduplicated only if all
seven fields agree; missing/conflicting samples fail closed.
"""
from __future__ import annotations
import argparse
import contextlib
import datetime as dt
import hashlib
import io
import os
from pathlib import Path
import stat
import sys
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
C47_NAME = 'local_ai_agent_v021c47_seven_series_vm_history_host_audit_v01.py'
C47_SHA256 = '207c025905f4ccc004bbc793fcf0aa7bc61ca5f2ec6904851ccf0a56a9f7895f'
HCC_GITHUB_BLOB_SHA1 = '03442de09a6492a20184f3b5f3d60caa18e8ae3e'
HCC_SOURCE_SHA256 = '0f15f733d9ebbf087b3ba27ba0ca3a073606cb0c85191f5181316ee500511772'
HCC_SOURCE = r'''#!/usr/bin/env python3
"""Issue #319: pure OFFLINE evidence model for sampled DNS Guard transitions.

No runtime collector, PromQL, HTTP, router access, filesystem I/O, notification,
service installation, browser endpoint or alert action. Input is synthetic,
prevalidated-only-like coarse exporter rows with exact allowlisted keys.
A gap or contradiction cannot become a confident transition.
"""
from __future__ import annotations

from datetime import datetime, timezone

SOURCE = "DNS_GUARD_COARSE_FEDORA_EXPORTER"
SCHEMA = "dns-guard-events-offline/0.1"
MAX_ROWS = 256
MAX_GAP_SECONDS = 180  # provisional, not a guaranteed source interval
MIN_EPOCH = 946684800  # 2000-01-01; reject nonsense clocks
MAX_EPOCH = 4102444800  # 2100-01-01
FIELDS = frozenset({
    "collection_epoch", "mode_local", "mode_bootstrap", "state_valid",
    "last_transition_epoch", "fallback_since_epoch", "fallback_transitions_total",
})
BOOT = "DNS_GUARD_BOOTSTRAP_OBSERVED"
LOCAL = "DNS_GUARD_LOCAL_RESTORED"
UNKNOWN = "DNS_GUARD_STATE_UNKNOWN"
STALE = "DNS_GUARD_TELEMETRY_STALE"


def _utc(epoch: int | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z")


def _int(value: object, lower: int, upper: int) -> bool:
    return type(value) is int and lower <= value <= upper


def _sample(row: object) -> tuple[dict | None, str]:
    if not isinstance(row, dict) or set(row) != FIELDS:
        return None, "MISSING_EXTRA_OR_NONOBJECT_FIELDS"
    c = row["collection_epoch"]
    if not _int(c, MIN_EPOCH, MAX_EPOCH):
        return None, "INVALID_COLLECTION_CLOCK"
    if not all(_int(row[k], 0, 1) for k in
               ("mode_local", "mode_bootstrap", "state_valid")):
        return None, "INVALID_MODE_FLAGS"
    if row["state_valid"] != 1 or row["mode_local"] + row["mode_bootstrap"] != 1:
        return None, "STATE_INVALID_OR_CONTRADICTORY"
    for k in ("last_transition_epoch", "fallback_since_epoch"):
        if not _int(row[k], 0, MAX_EPOCH):
            return None, "INVALID_REPORTED_TIMESTAMP"
        if row[k] > c + 5:
            return None, "FUTURE_REPORTED_TIMESTAMP"
    if not _int(row["fallback_transitions_total"], 0, 999999999):
        return None, "INVALID_FALLBACK_COUNTER"
    if row["mode_local"] == 1 and row["fallback_since_epoch"] != 0:
        return None, "LOCAL_WITH_ACTIVE_FALLBACK_MARKER"
    return dict(row), ""


def _event(kind: str, at: int | None, code: str, ordinal: int, *,
           lower_window: int | None = None, reported: int | None = None,
           duration_lower: int | None = None, duration_upper: int | None = None,
           confidence: str = "LIMITED") -> dict:
    return {
        "event_type": kind,
        "observed_at": _utc(at),
        "source": SOURCE,
        "status": "OBSERVED" if kind in (BOOT, LOCAL) else "UNVERIFIED",
        "confidence": confidence,
        "coverage": "SAMPLED_ONLY" if kind in (BOOT, LOCAL) else "INCOMPLETE",
        "reason_code": code,
        "effective_time_source": "FEDORA_COLLECTION_INTERVAL",
        "window_start": _utc(lower_window),
        "window_end": _utc(at),
        # Router-maintained timestamps can be reconciled by metrics collection;
        # show as reported, never claim this is an exact wire-level event time.
        "reported_transition_at": _utc(reported),
        "duration_lower_seconds": duration_lower,
        "duration_upper_seconds": duration_upper,
        "dedupe_key": f"{kind}:{at}" if at is not None else f"{kind}:unknown:{ordinal}",
    }


def timeline(rows: object) -> dict:
    """Reconstruct only observed transitions, never complete DNS outage history.

    Input order is source order. Out-of-order rows are not silently sorted:
    this refuses to invent causal order after late or conflicting data.
    """
    if not isinstance(rows, (tuple, list)) or len(rows) > MAX_ROWS:
        raise ValueError("bounded list/tuple required, max 256 samples")
    events = []
    previous = None
    # Bootstrap observed window: (last LOCAL before fallback or None,
    #                            first BOOT observation, last BOOT observation).
    boot_window = None

    for ordinal, row in enumerate(rows):
        current, reason = _sample(row)
        if current is None:
            events.append(_event(UNKNOWN, None, reason, ordinal))
            previous, boot_window = None, None
            continue

        at = current["collection_epoch"]
        mode = "LOCAL" if current["mode_local"] == 1 else "BOOTSTRAP"
        if previous is None:
            previous = current
            boot_window = (None, at, at) if mode == "BOOTSTRAP" else None
            continue

        previous_at = previous["collection_epoch"]
        previous_mode = "LOCAL" if previous["mode_local"] == 1 else "BOOTSTRAP"
        if at == previous_at:
            if current == previous:  # identical scrape/collector replay
                continue
            events.append(_event(UNKNOWN, at, "CONTRADICTORY_SAME_COLLECTION", ordinal))
            previous, boot_window = None, None
            continue

        if at < previous_at:
            events.append(_event(UNKNOWN, at, "OUT_OF_ORDER_SAMPLE", ordinal))
            previous, boot_window = None, None
            continue

        delta = current["fallback_transitions_total"] - previous["fallback_transitions_total"]
        if delta < 0:
            events.append(_event(UNKNOWN, at, "COUNTER_RESET_OR_REBOOT", ordinal))
            previous = current
            boot_window = (None, at, at) if mode == "BOOTSTRAP" else None
            continue

        if at - previous_at > MAX_GAP_SECONDS:
            events.append(_event(STALE, at, "COLLECTION_GAP", ordinal,
                                 lower_window=previous_at))
            previous = current
            boot_window = (None, at, at) if mode == "BOOTSTRAP" else None
            continue

        if delta > 1 or (mode == previous_mode and delta > 0) or (mode == "LOCAL" and delta > 0):
            events.append(_event(UNKNOWN, at, "COUNTER_SUGGESTS_MISSED_TRANSITION",
                                 ordinal, lower_window=previous_at))
            previous = current
            boot_window = (None, at, at) if mode == "BOOTSTRAP" else None
            continue

        if mode != previous_mode:
            reported = current["last_transition_epoch"]
            if not previous_at < reported <= at:
                reported = None
            if mode == "BOOTSTRAP":
                code = "MODE_CHANGE_OBSERVED"
                if delta != 1:
                    code = "MODE_CHANGE_COUNTER_UNCORROBORATED"
                elif current["fallback_since_epoch"] == 0:
                    code = "MODE_CHANGE_FALLBACK_START_UNRECORDED"
                events.append(_event(BOOT, at, code, ordinal,
                                     lower_window=previous_at, reported=reported,
                                     confidence="BOUNDED_OBSERVATION"))
                boot_window = (previous_at, at, at)
            else:
                # Exact fallback duration is impossible at this cadence.
                # min = span of positively observed BOOT samples;
                # max = last pre-fallback LOCAL to first restored LOCAL.
                if boot_window is None:
                    bounds = (None, None)
                else:
                    before, first_boot, last_boot = boot_window
                    bounds = (last_boot - first_boot,
                              at - before if before is not None else None)
                events.append(_event(LOCAL, at, "LOCAL_AFTER_BOOTSTRAP_OBSERVED",
                                     ordinal, lower_window=previous_at,
                                     reported=reported,
                                     duration_lower=bounds[0],
                                     duration_upper=bounds[1],
                                     confidence="BOUNDED_OBSERVATION"))
                boot_window = None
        elif mode == "BOOTSTRAP":
            if boot_window is None:
                boot_window = (None, previous_at, at)
            else:
                boot_window = (boot_window[0], boot_window[1], at)

        previous = current

    return {
        "schema_version": SCHEMA,
        "mode": "OFFLINE_FIXTURES_ONLY",
        "source": SOURCE,
        "event_count": len(events),
        "events": events,
        "input_count": len(rows),
        "limitations": "Sampled transitions only; no proof of every transition or exact outage duration.",
        "deployment_gate": "HOLD",
    }
'''
_C47 = None
_HCC = None

class Hold(Exception):
    pass


def verified_hcc_model():
    global _HCC
    data = HCC_SOURCE.encode('utf-8')
    gitblob = hashlib.sha1(('blob %s\0' % len(data)).encode() + data).hexdigest()
    if hashlib.sha256(data).hexdigest() != HCC_SOURCE_SHA256 or gitblob != HCC_GITHUB_BLOB_SHA1:
        raise Hold('HCC_FROZEN_SOURCE_MISMATCH')
    if _HCC is None:
        module = types.ModuleType('original_hcc_dns_guard_event_model_v01_frozen_c48')
        exec(compile(data, 'hcc_dns_guard_event_model_v01_frozen.py', 'exec'), module.__dict__)
        if module.SCHEMA != 'dns-guard-events-offline/0.1' or module.MAX_ROWS != 256:
            raise Hold('HCC_MODEL_CONTRACT_CHANGED')
        _HCC = module
    return _HCC


def original_c47():
    global _C47
    path = HERE / C47_NAME
    try:
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
            or before.st_nlink != 1 or before.st_mode & 0o022
            or not 1 <= before.st_size <= 65536):
            raise Hold('C47_OWNER_MODE_SIZE')
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            s = os.fstat(fd)
            identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns)
            if identity(s) != identity(before):
                raise Hold('C47_CHANGED_BEFORE_READ')
            data = os.read(fd, 65537)
            if len(data) != s.st_size or identity(s) != identity(os.fstat(fd)):
                raise Hold('C47_CHANGED_DURING_READ')
        finally:
            os.close(fd)
    except OSError as exc:
        raise Hold('C47_MISSING_OR_UNREADABLE') from exc
    if hashlib.sha256(data).hexdigest() != C47_SHA256:
        raise Hold('C47_SHA256_PIN_MISMATCH')
    if _C47 is None:
        module = types.ModuleType('pinned_c47_v021c48')
        module.__file__ = str(path)
        exec(compile(data,str(path),'exec'),module.__dict__)
        module.pinned_c46()
        _C47 = module
    return _C47


def make_rows(base, extra, start, end, c47):
    """Gate grid integrity, then pass distinct *collection* records to HCC model.

    HCC timeline() has no query_range awareness; it expects original collections,
    so repeated scrape grid points must not masquerade as new observations.
    """
    c46 = c47.pinned_c46()
    c45 = c46.original_c45()
    base_counts, last, ext_counts, coverage = c47.evaluate(base,extra,start,end,c45)
    if coverage != 'COMPLETE_SAMPLED_SEVEN_SERIES':
        raise Hold('C47_COVERAGE_LIMITED')
    result=[]
    duplicates=0
    for t in range(start,end+1,c47.STEP):
        fields = {metric: base[metric][t] for metric in c47.METRICS[:4]}
        fields.update({metric: extra[metric][t] for metric in c47.EXTRA_NAMES})
        collection = fields[c47.METRICS[0]]
        if type(collection) not in (int,float) or int(collection)!=collection:
            raise Hold('COLLECTION_NOT_INTEGER')
        row = {
            'collection_epoch': int(collection),
            'state_valid': int(fields[c47.METRICS[1]]),
            'mode_local': int(fields[c47.METRICS[2]]),
            'mode_bootstrap': int(fields[c47.METRICS[3]]),
            'last_transition_epoch': int(fields[c47.EXTRA_NAMES[0]]),
            'fallback_since_epoch': int(fields[c47.EXTRA_NAMES[1]]),
            'fallback_transitions_total': int(fields[c47.EXTRA_NAMES[2]]),
        }
        if result:
            if row['collection_epoch'] == result[-1]['collection_epoch']:
                if row != result[-1]:
                    raise Hold('CONTRADICTORY_SAME_COLLECTION')
                duplicates+=1
                continue
            if row['collection_epoch'] < result[-1]['collection_epoch']:
                raise Hold('OUT_OF_ORDER_COLLECTION')
        result.append(row)
    if (len(result)+duplicates != c47.ROWS or
        duplicates != base_counts['same_collection_as_previous']):
        raise Hold('COLLECTION_DEDUP_INVARIANT')
    if not result or len(result)>256:
        raise Hold('BOUNDED_COLLECTION_ROWS')
    return result, base_counts, ext_counts, coverage, duplicates, last


def compare(base,extra,start,end,c47):
    rows,base_counts,ext_counts,coverage,duplicates,last=make_rows(base,extra,start,end,c47)
    model = verified_hcc_model()
    result=model.timeline(rows)
    if (result.get('event_count')!=len(result['events']) or
        result.get('input_count')!=len(rows) or result.get('schema_version')!=model.SCHEMA):
        raise Hold('HCC_EVENT_MODEL_RESPONSE_INVALID')
    types_=[event['event_type'] for event in result['events']]
    unknown=sum(x==model.UNKNOWN for x in types_)
    stale=sum(x==model.STALE for x in types_)
    observed=sum(x in (model.BOOT,model.LOCAL) for x in types_)
    transitions=base_counts['observed_adjacent_mode_changes']
    if unknown or stale:
        assessment='LIMITED_HCC_UNKNOWN_OR_GAP'
    elif observed != transitions:
        assessment='LIMITED_OBSERVED_EVENT_COUNT_MISMATCH'
    elif transitions==0:
        assessment='NO_TRANSITIONS_TO_COMPARE'
    else:
        assessment='SAMPLED_TRANSITION_EVENTS_CONCORDANT'
    return {'rows':len(rows),'duplicates':duplicates,'grid':c47.ROWS,
            'observed_transitions':transitions,'hcc_events':len(types_),
            'hcc_observed_events':observed,'hcc_unknown':unknown,'hcc_stale':stale,
            'assessment':assessment,'coverage':coverage,'last':last,
            'counter_decreases':ext_counts['transition_counter_decreases']}


def run(*, epoch=None, live=None, live_fetch=None, fetch_base=None, fetch_extension=None):
    c47=original_c47()
    c46=c47.pinned_c46();c45=c46.original_c45();c44=c45.pinned_original()
    c43,_=c44.load_originals()
    if epoch is None:epoch=int(dt.datetime.now(dt.timezone.utc).timestamp())
    if type(epoch) is not int or epoch < c47.WINDOW+c47.STEP:
        raise Hold('CLOCK_INVALID')
    snapshot=(c43.collect(fetch=c43.vm_get if live_fetch is None else live_fetch)
              if live is None else live)
    host=c44.validate_snapshot(snapshot)
    start=(epoch//c47.STEP)*c47.STEP-c47.WINDOW
    end=start+c47.WINDOW
    names=c45.fixed_metrics(c44)
    if tuple(names[k] for k in c45.SELECTORS) != c47.METRICS[:4]:
        raise Hold('FIXED_METRIC_NAMES_CHANGED')
    bfetch=c45.range_get if fetch_base is None else fetch_base
    efetch=c47.fetch_extra if fetch_extension is None else fetch_extension
    base={}
    for key in c45.SELECTORS:
        metric=names[key]
        base[metric]=c45.parse_range(bfetch(metric,start,end),metric,start,end)
    extra={}
    for metric in c47.EXTRA_NAMES:
        extra[metric]=c47.parse_extra(metric,efetch(metric,start,end),start,end)
    report=compare(base,extra,start,end,c47)
    print('=== V0.21C.48 / FROZEN HCC EVENT-MODEL SEVEN-SERIES COMPARISON ===')
    print('VM=127.0.0.1:8428')
    print('HCC_EVENT_MODEL=ORIGINAL_FROZEN_GIT_BLOB_'+HCC_GITHUB_BLOB_SHA1)
    print('HCC_DEPLOYED_INSTANCE_CONTACTED=NO')
    print('C47_SOURCE_SHA256=PASS_PINNED_UNMODIFIED')
    print('HOST_LIVE_STATUS='+host['status'])
    print('HOST_LIVE_MODE='+host['dns_mode'])
    print('HISTORY_GRID_ROWS='+str(report['grid']))
    print('HISTORY_DISTINCT_COLLECTION_ROWS='+str(report['rows']))
    print('HISTORY_IDENTICAL_REPEATS_SKIPPED='+str(report['duplicates']))
    print('HISTORY_SEVEN_SERIES_COVERAGE='+report['coverage'])
    print('HISTORY_OBSERVED_ADJACENT_CHANGES='+str(report['observed_transitions']))
    print('HCC_MODEL_OBSERVED_MODE_EVENTS='+str(report['hcc_observed_events']))
    print('HCC_MODEL_UNKNOWN_EVENTS='+str(report['hcc_unknown']))
    print('HCC_MODEL_STALE_EVENTS='+str(report['hcc_stale']))
    print('HCC_MODEL_TOTAL_EVENTS='+str(report['hcc_events']))
    print('HCC_PARITY_ASSESSMENT='+report['assessment'])
    print('HCC_EVENT_MODEL_LIVE_PARITY=NOT_PROVEN_FROZEN_SNAPSHOT_ONLY')
    print('EXACT_SWITCH_TIME_ALL_HIDDEN_TRANSITIONS_DNS_HEALTH=NOT_PROVEN')
    print('MODEL_OLLAMA_EXECUTOR_CHECKPOINT_PODMAN=NOT_CONTACTED')
    print('NO_HCC_NO_ASUS_NO_ROUTERCLOUD_CHANGES=YES')
    print('DEPLOYMENT_GATE=HOLD')
    print('V021C48_RESULT=PASS_FROZEN_HCC_EVENT_MODEL_SAMPLED_GRID_DIAGNOSTIC_ONLY')
    return report


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c47=original_c47()
        cls.end=(1800000000//60)*60
        cls.start=cls.end-3600
    def fixture(self, mode='LOCAL'):
        times=list(range(self.start,self.end+1,60))
        b={self.c47.METRICS[0]:{t:t-40 for t in times},
           self.c47.METRICS[1]:{t:1 for t in times},
           self.c47.METRICS[2]:{t:int(mode=='LOCAL') for t in times},
           self.c47.METRICS[3]:{t:int(mode=='BOOTSTRAP') for t in times}}
        x={self.c47.EXTRA_NAMES[0]:{t:0 for t in times},
           self.c47.EXTRA_NAMES[1]:{t:0 for t in times},
           self.c47.EXTRA_NAMES[2]:{t:0 for t in times}}
        return b,x,times
    def live(self):
        return {'status':'OK','reason_code':'LOCAL_MODE_REPORTED','dns_mode':'LOCAL',
                'collection_age_seconds':60,'breakglass_active':False,'watchdog_present':True}
    def transitions(self):
        b,x,times=self.fixture()
        for i,t in enumerate(times):
            if 20<=i<35:
                b[self.c47.METRICS[2]][t]=0
                b[self.c47.METRICS[3]][t]=1
                x[self.c47.EXTRA_NAMES[2]][t]=1
                x[self.c47.EXTRA_NAMES[1]][t]=times[20]-45
                x[self.c47.EXTRA_NAMES[0]][t]=times[20]-45
            if i>=35:
                x[self.c47.EXTRA_NAMES[2]][t]=1
                x[self.c47.EXTRA_NAMES[0]][t]=times[35]-45
        return b,x,times
    def test_01_pinned_hcc_hash(self):
        self.assertEqual(hashlib.sha256(HCC_SOURCE.encode()).hexdigest(),HCC_SOURCE_SHA256)
    def test_02_pinned_git_blob(self):
        self.assertEqual(verified_hcc_model().SCHEMA,'dns-guard-events-offline/0.1')
    def test_03_c47_pin(self):
        self.assertEqual(hashlib.sha256((HERE/C47_NAME).read_bytes()).hexdigest(),C47_SHA256)
    def test_04_c47_chain(self):
        self.assertEqual(self.c47.pinned_c46().original_c45().POINTS,61)
    def test_05_no_nonlocal(self):
        self.assertEqual((self.c47.HOST,self.c47.PORT),('127.0.0.1',8428))
    def test_06_no_unbounded_model(self):
        self.assertEqual(verified_hcc_model().MAX_ROWS,256)
    def test_07_stable_local_zero_events(self):
        b,x,_=self.fixture();r=compare(b,x,self.start,self.end,self.c47)
        self.assertEqual((r['assessment'],r['hcc_events']),('NO_TRANSITIONS_TO_COMPARE',0))
    def test_08_stable_boot_zero_events(self):
        b,x,_=self.fixture('BOOTSTRAP');r=compare(b,x,self.start,self.end,self.c47)
        self.assertEqual(r['hcc_events'],0)
    def test_09_synthetic_boot_local(self):
        b,x,_=self.transitions();r=compare(b,x,self.start,self.end,self.c47)
        self.assertEqual((r['observed_transitions'],r['hcc_observed_events']), (2,2))
        self.assertEqual(r['assessment'],'SAMPLED_TRANSITION_EVENTS_CONCORDANT')
    def test_10_no_unknown_in_synthetic_transition(self):
        b,x,_=self.transitions();r=compare(b,x,self.start,self.end,self.c47)
        self.assertEqual(r['hcc_unknown'],0)
    def test_11_complete_grid(self):
        b,x,_=self.fixture();r=compare(b,x,self.start,self.end,self.c47)
        self.assertEqual(r['rows'],61)
    def test_12_repeated_complete_record(self):
        b,x,times=self.fixture();t=times[1];old=times[0]
        for m in self.c47.METRICS[:4]:b[m][t]=b[m][old]
        for m in self.c47.EXTRA_NAMES:x[m][t]=x[m][old]
        r=compare(b,x,self.start,self.end,self.c47)
        self.assertEqual((r['rows'],r['duplicates']),(60,1))
    def test_13_repeated_changed_flags_holds(self):
        b,x,times=self.fixture();t=times[1];old=times[0]
        b[self.c47.METRICS[0]][t]=b[self.c47.METRICS[0]][old]
        b[self.c47.METRICS[2]][t]=0;b[self.c47.METRICS[3]][t]=1
        with self.assertRaisesRegex(Hold,'CONTRADICTORY'):compare(b,x,self.start,self.end,self.c47)
    def test_14_repeated_changed_counter_holds(self):
        b,x,times=self.fixture();t=times[1];old=times[0]
        b[self.c47.METRICS[0]][t]=b[self.c47.METRICS[0]][old]
        for at in times[1:]:x[self.c47.EXTRA_NAMES[2]][at]=1
        with self.assertRaisesRegex(Hold,'CONTRADICTORY'):compare(b,x,self.start,self.end,self.c47)
    def test_15_missing_one_holds(self):
        b,x,times=self.fixture();x[self.c47.EXTRA_NAMES[0]].pop(times[0])
        with self.assertRaisesRegex(Hold,'C47_COVERAGE'):compare(b,x,self.start,self.end,self.c47)
    def test_16_stale_one_holds(self):
        b,x,times=self.fixture();b[self.c47.METRICS[0]][times[0]]=times[0]-500
        with self.assertRaisesRegex(Hold,'C47_COVERAGE'):compare(b,x,self.start,self.end,self.c47)
    def test_17_future_transition_holds(self):
        b,x,times=self.fixture();x[self.c47.EXTRA_NAMES[0]][times[0]]=times[0]+600
        with self.assertRaisesRegex(Hold,'C47_COVERAGE'):compare(b,x,self.start,self.end,self.c47)
    def test_18_counter_decrease_holds(self):
        b,x,times=self.fixture();x[self.c47.EXTRA_NAMES[2]][times[0]]=5
        with self.assertRaisesRegex(Hold,'C47_COVERAGE'):compare(b,x,self.start,self.end,self.c47)
    def test_19_local_fallback_marker_fails_model(self):
        b,x,times=self.fixture();x[self.c47.EXTRA_NAMES[1]][times[0]]=times[0]-100
        r=compare(b,x,self.start,self.end,self.c47)
        self.assertEqual(r['assessment'],'LIMITED_HCC_UNKNOWN_OR_GAP')
    def test_20_hidden_counter_delta_flags_unknown(self):
        b,x,times=self.fixture()
        for t in times[20:]:x[self.c47.EXTRA_NAMES[2]][t]=1
        r=compare(b,x,self.start,self.end,self.c47)
        self.assertEqual(r['assessment'],'LIMITED_HCC_UNKNOWN_OR_GAP')
    def test_21_fake_missing_base(self):
        b,x,_=self.fixture();b.pop(self.c47.METRICS[1])
        with self.assertRaises(self.c47.Hold):compare(b,x,self.start,self.end,self.c47)
    def test_22_fake_missing_extra(self):
        b,x,_=self.fixture();x.pop(self.c47.EXTRA_NAMES[2])
        with self.assertRaises(self.c47.Hold):compare(b,x,self.start,self.end,self.c47)
    def test_23_fallback_start_uncorroborated(self):
        b,x,times=self.transitions()
        for t in times:x[self.c47.EXTRA_NAMES[2]][t]=0
        r=compare(b,x,self.start,self.end,self.c47)
        self.assertEqual(r['hcc_observed_events'],2)
    def test_24_nontimestamp_fake(self):
        b,x,times=self.fixture();b[self.c47.METRICS[0]][times[0]]=1.5
        with self.assertRaises(Hold):compare(b,x,self.start,self.end,self.c47)
    def test_25_full_path_offline(self):
        b,x,_=self.fixture();c45=self.c47.pinned_c46().original_c45()
        bf=lambda n,s,e:c45.fixture(n,sorted(b[n].items()))
        ef=lambda n,s,e:self.c47.extra_fixture(n,sorted(x[n].items()))
        with patch('http.client.HTTPConnection',side_effect=AssertionError('NETWORK_FORBIDDEN')):
            out=io.StringIO()
            with contextlib.redirect_stdout(out):r=run(epoch=self.end,live=self.live(),fetch_base=bf,fetch_extension=ef)
        self.assertEqual(r['hcc_events'],0)
        self.assertIn('V021C48_RESULT=PASS_',out.getvalue())
    def test_26_full_path_transition(self):
        b,x,_=self.transitions();c45=self.c47.pinned_c46().original_c45()
        bf=lambda n,s,e:c45.fixture(n,sorted(b[n].items()))
        ef=lambda n,s,e:self.c47.extra_fixture(n,sorted(x[n].items()))
        with patch('http.client.HTTPConnection',side_effect=AssertionError('NETWORK_FORBIDDEN')):
            with contextlib.redirect_stdout(io.StringIO()):r=run(epoch=self.end,live=self.live(),fetch_base=bf,fetch_extension=ef)
        self.assertEqual(r['hcc_observed_events'],2)
    def test_27_stale_live_refuses_history(self):
        bad=self.live();bad['status']='STALE'
        def fail(*_):raise AssertionError('HISTORY_MUST_NOT_RUN')
        with self.assertRaises(Exception):run(epoch=self.end,live=bad,fetch_base=fail,fetch_extension=fail)
    def test_28_frozen_source_not_network(self):
        with patch('http.client.HTTPConnection',side_effect=AssertionError('NETWORK_FORBIDDEN')):
            self.assertEqual(verified_hcc_model().timeline([])['event_count'],0)
    def test_29_exact_fields(self):
        self.assertEqual(len(verified_hcc_model().FIELDS),7)
    def test_30_no_exact_time_claim(self):
        b,x,_=self.transitions();r=compare(b,x,self.start,self.end,self.c47)
        self.assertEqual(r['assessment'],'SAMPLED_TRANSITION_EVENTS_CONCORDANT')
    def test_31_no_changed_file_pin(self):
        self.assertEqual((HERE/C47_NAME).is_symlink(),False)
    def test_32_coverage_is_bounded(self):
        b,x,_=self.fixture();r=compare(b,x,self.start,self.end,self.c47)
        self.assertEqual(r['grid'],61)


def selftest():
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    passed=result.testsRun-len(result.failures)-len(result.errors)
    print(f'V021C48_SELFTESTS={passed}/{result.testsRun}')
    print('C47_C46_C45_C44_C43_AND_EARLIER=SHA256_PINNED_UNMODIFIED')
    print('HCC_MODEL_BLOB_SHA1='+HCC_GITHUB_BLOB_SHA1)
    print('HCC_MODEL_SOURCE=FROZEN_EXACT_REPOSITORY_BLOB_NOT_DEPLOYED_HCC')
    print('NETWORK_MODEL_EXECUTOR_DURING_SELFTEST=NO')
    print('DEPLOYMENT_GATE=HOLD')
    ok=result.wasSuccessful() and result.testsRun==32
    print('V021C48_SELFTEST_RESULT='+('PASS' if ok else 'FAIL'))
    return ok


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--self-test',action='store_true')
    group.add_argument('--hcc-parity-preflight',action='store_true')
    args=parser.parse_args()
    if os.geteuid()==0:raise Hold('ROOT_DENIED')
    original_c47();verified_hcc_model()
    if not selftest():raise Hold('SELFTEST_FAILED')
    if args.hcc_parity_preflight:run()

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('V021C48_RESULT=HOLD_NOT_APPROVED')
        print('V021C48_HOLD_REASON='+type(exc).__name__+':'+str(exc)[:100])
        print('DEPLOYMENT_GATE=HOLD')
        sys.exit(1)
