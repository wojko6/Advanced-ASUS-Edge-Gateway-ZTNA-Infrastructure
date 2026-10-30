#!/usr/bin/env python3
"""HCC V0.14.5A: standalone synthetic-only atomic immutable segment laboratory.

No real journald, production spool, systemd, Alloy/Loki or network access.
Writes only to a freshly created disposable tempfile.TemporaryDirectory
from an explicit --lab command. --self-test does not perform any I/O.

Inputs are the strictly whitelisted output format from the V0.14 sanitizer.
The four fixed fields are a SHAPE contract, not proof of event provenance.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import fcntl
import hashlib
import json
import os
import re
import stat
import tempfile

SCHEMA = 'hcc-v0145a-sanitized-event/1'
ALLOWED_KINDS = frozenset(('COLLECTOR_EXIT_255', 'SSH_TIMEOUT',
                           'SSH_AUTH_FAILURE', 'HTTP_IMPORT_TIMEOUT'))
EXPECTED_KEYS = frozenset(('time', 'kind', 'component', 'source'))
EXPECTED_COMPONENT = 'dns-guard-collector'
EXPECTED_SOURCE = 'fedora-user-journal'
TIMESTAMP_RE = re.compile(r'\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\Z', re.ASCII)
FINAL_RE = re.compile(r'\Asegment-([0-9a-f]{64})\.ndjson\Z', re.ASCII)
TEMP_RE = re.compile(r'\A\.tmp-([0-9a-f]{32})\Z', re.ASCII)
MAX_ROWS = 256
MAX_BYTES = 32768
MAX_SEGMENTS_REVIEWED = 128

class Hold(RuntimeError):
    """Fail-closed lab boundary: no deployment/ingestion permission."""

class SimulatedInterrupt(RuntimeError):
    pass


def require_private_directory(dirfd):
    """Recheck metadata and hold a nonblocking, cooperative Linux writer lock.

    The lock belongs to the open file description until the caller closes it.
    Do not share that description between concurrent threads/processes. This
    is not protection against an uncooperative process with the same UID.
    """
    st = os.fstat(dirfd)
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid() or
            stat.S_IMODE(st.st_mode) != 0o700):
        raise Hold('PRIVATE_DIRECTORY_REQUIRED')
    try:
        fcntl.flock(dirfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise Hold('DIRECTORY_BUSY') from exc


def no_duplicates(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise Hold('DUPLICATE_JSON_KEY')
        result[k] = v
    return result


def valid_timestamp(value):
    if type(value) is not str or not TIMESTAMP_RE.fullmatch(value):
        raise Hold('INVALID_TIMESTAMP_FORMAT')
    try:
        dt = datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError as exc:
        raise Hold('INVALID_TIMESTAMP') from exc
    if not 2000 <= dt.year <= 2100 or dt.utcoffset() is None:
        raise Hold('INVALID_TIMESTAMP_RANGE')
    return dt


def normalize_sanitized_jsonl(raw):
    """Strict, wholly bounded, canonical JSONL. Nothing from raw journald here."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise Hold('INVALID_INPUT_LENGTH')
    rows = raw.splitlines()
    if not 1 <= len(rows) <= MAX_ROWS or any(not row for row in rows):
        raise Hold('INVALID_INPUT_ROWS')
    canonical, seen = [], set()
    prior = None
    for line in rows:
        try:
            obj = json.loads(line.decode('utf-8'), object_pairs_hook=no_duplicates,
                             parse_constant=lambda _: (_ for _ in ()).throw(Hold('NONFINITE_JSON')))
        except (UnicodeDecodeError, ValueError, RecursionError) as exc:
            raise Hold('INVALID_JSON') from exc
        if type(obj) is not dict or set(obj) != EXPECTED_KEYS:
            raise Hold('INVALID_SCHEMA')
        if any(type(v) is not str for v in obj.values()):
            raise Hold('NONSTRING_FIELD')
        if (obj['kind'] not in ALLOWED_KINDS or
                obj['component'] != EXPECTED_COMPONENT or
                obj['source'] != EXPECTED_SOURCE):
            raise Hold('UNEXPECTED_EVENT_VALUE')
        t = valid_timestamp(obj['time'])
        if prior is not None and t < prior:
            raise Hold('EVENT_ORDER')
        prior = t
        normalized = json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        if normalized in seen:
            raise Hold('DUPLICATE_EVENT_IN_BATCH')
        seen.add(normalized)
        canonical.append(normalized)
    result = ('\n'.join(canonical) + '\n').encode('ascii')
    if len(result) > MAX_BYTES:
        raise Hold('CANONICAL_BYTES_LIMIT')
    return result


def digest_name(canonical):
    return 'segment-' + hashlib.sha256(canonical).hexdigest() + '.ndjson'


def open_private_directory(folder):
    """Protect the final dir component and use descriptor-relative operations."""
    fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        require_private_directory(fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def inspect_entries(dirfd):
    """No implicit recovery. Unknown or orphaned items block publication."""
    require_private_directory(dirfd)
    result = []
    with os.scandir(dirfd) as entries:
        for entry in entries:
            if len(result) >= MAX_SEGMENTS_REVIEWED:
                raise Hold('TOO_MANY_SEGMENTS')
            name = entry.name
            if TEMP_RE.fullmatch(name):
                raise Hold('ORPHAN_TEMP_REQUIRES_MANUAL_REVIEW')
            if not FINAL_RE.fullmatch(name):
                raise Hold('UNEXPECTED_DIRECTORY_ENTRY')
            result.append(name)
    return sorted(result)


def verified_segment(dirfd, name):
    require_private_directory(dirfd)
    m = FINAL_RE.fullmatch(name)
    if not m:
        raise Hold('BAD_SEGMENT_NAME')
    # A FIFO carrying a valid-looking segment name must never block os.open.
    fd = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC,
                 dir_fd=dirfd)
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or
                stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or
                not 0 < st.st_size <= MAX_BYTES):
            raise Hold('UNSAFE_SEGMENT_METADATA')
        chunks, remaining = [], st.st_size + 1
        while remaining:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b''.join(chunks)
        if len(content) != st.st_size or len(content) > MAX_BYTES:
            raise Hold('SEGMENT_SIZE_CHANGED')
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid',
                  'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if any(getattr(st, key) != getattr(after, key) for key in fields):
            raise Hold('SEGMENT_METADATA_CHANGED')
        if normalize_sanitized_jsonl(content) != content:
            raise Hold('NONCANONICAL_SEGMENT')
        if hashlib.sha256(content).hexdigest() != m.group(1):
            raise Hold('SEGMENT_HASH_MISMATCH')
        return content
    finally:
        os.close(fd)


def write_all(fd, content):
    view = memoryview(content)
    while len(view):
        n = os.write(fd, view)
        if n <= 0:
            raise Hold('SHORT_WRITE')
        view = view[n:]


def publish(dirfd, raw, *, failpoint=None):
    """fsync temp file, atomic hardlink-if-absent, unlink temp, fsync directory.

    This is immutable-batch publication, NOT a live single-file append writer.
    Duplicate exact batches are recognized; overlapping batches are NOT deduped.
    """
    if failpoint not in (None, 'after_fsync_before_publish'):
        raise Hold('UNSUPPORTED_FAILPOINT')
    canonical = normalize_sanitized_jsonl(raw)
    names = inspect_entries(dirfd)
    # Check the entire bounded backlog before *any* new file is created.
    # Valid names alone do not establish integrity of unrelated segments.
    existing = {name: verified_segment(dirfd, name) for name in names}
    final = digest_name(canonical)
    if final in names:
        if existing[final] != canonical:
            raise Hold('EXISTING_SEGMENT_CONFLICT')
        # Also retry the directory barrier after an earlier uncertain fsync.
        # This writes no new segment bytes and does not prove power-loss safety.
        os.fsync(dirfd)
        return 'DUPLICATE_BATCH_NO_WRITE', final
    if len(names) >= MAX_SEGMENTS_REVIEWED:
        raise Hold('SEGMENT_COUNT_LIMIT')
    tmp = '.tmp-' + os.urandom(16).hex()
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=dirfd)
    try:
        try:
            # Restrictive inherited umasks must not create an unreadable final
            # segment that this same validator would reject on the next call.
            os.fchmod(fd, 0o600)
            write_all(fd, canonical)
            os.fsync(fd)
        finally:
            os.close(fd)
        if failpoint is not None:
            raise SimulatedInterrupt('TEST_INTERRUPTION_BEFORE_PUBLICATION')
        try:
            os.link(tmp, final, src_dir_fd=dirfd, dst_dir_fd=dirfd,
                    follow_symlinks=False)
        except FileExistsError:
            if verified_segment(dirfd, final) != canonical:
                raise Hold('EXISTING_SEGMENT_CONFLICT')
            result = 'DUPLICATE_BATCH_NO_WRITE'
        else:
            result = 'PUBLISHED_ATOMIC_SEGMENT'
        return result, final
    finally:
        # Exception cleanup is tested; power-loss recovery remains a HOLD gate.
        os.unlink(tmp, dir_fd=dirfd)
        os.fsync(dirfd)


def retention_preview(dirfd, keep=1):
    """Review-only retention proposal: NEVER delete event segments."""
    if type(keep) is not int or not 1 <= keep <= 64:
        raise Hold('INVALID_RETENTION_POLICY')
    items = []
    for name in inspect_entries(dirfd):
        content = verified_segment(dirfd, name)
        first = json.loads(content.splitlines()[0])['time']
        items.append((first, name))
    items.sort()
    candidates = [name for _, name in items[:max(0, len(items)-keep)]]
    return candidates


def event(time, kind):
    return json.dumps({'time': time, 'kind': kind,
                       'component': EXPECTED_COMPONENT, 'source': EXPECTED_SOURCE},
                      sort_keys=True, separators=(',', ':')).encode('ascii') + b'\n'


def self_test():
    a = event('2026-10-29T09:00:00.000Z', 'COLLECTOR_EXIT_255')
    assert normalize_sanitized_jsonl(a) == normalize_sanitized_jsonl(a)
    assert normalize_sanitized_jsonl(a).endswith(b'\n')
    assert digest_name(normalize_sanitized_jsonl(a)).startswith('segment-')
    bad = [b'', b'\n', b'{}\n', b'{"time": 1}\n', a+a,
           a.replace(b'COLLECTOR_EXIT_255', b'RAW_PRIVATE_SSH'),
           a.replace(b'2026-10-29T09:00:00.000Z', b'2026-02-29T09:00:00.000Z'),
           a + b' ' * MAX_BYTES]
    for raw in bad:
        try:
            normalize_sanitized_jsonl(raw)
        except Hold:
            pass
        else:
            raise AssertionError('NEGATIVE_INPUT_ACCEPTED')
    print('V0145A_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')
    print('SELFTEST_NO_NETWORK_NO_SUBPROCESS_NO_FILE_WRITES=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    first = event('2026-10-29T09:00:00.000Z', 'COLLECTOR_EXIT_255')
    second = event('2026-10-29T09:01:00.000Z', 'SSH_TIMEOUT')
    with tempfile.TemporaryDirectory(prefix='hcc-v0145a-synthetic-', dir='/tmp') as folder:
        os.chmod(folder, 0o700)
        fd = open_private_directory(folder)
        try:
            r1, n1 = publish(fd, first)
            same, _ = publish(fd, first)
            r2, n2 = publish(fd, second)
            names = inspect_entries(fd)
            assert r1 == 'PUBLISHED_ATOMIC_SEGMENT' and r2 == r1
            assert same == 'DUPLICATE_BATCH_NO_WRITE'
            assert len(names) == 2 and verified_segment(fd, n1) and verified_segment(fd, n2)
            preview = retention_preview(fd, keep=1)
            assert len(preview) == 1 and len(inspect_entries(fd)) == 2
            try:
                publish(fd, event('2026-10-29T09:02:00.000Z', 'HTTP_IMPORT_TIMEOUT'),
                        failpoint='after_fsync_before_publish')
            except SimulatedInterrupt:
                pass
            else:
                raise Hold('INTERRUPT_TEST_DID_NOT_RUN')
            assert inspect_entries(fd) == names
            print('=== HCC V0.14.5A / OFFLINE ATOMIC SEGMENT SPOOL ===')
            print('SYNTHETIC_SEGMENTS=2')
            print('EXACT_BATCH_DEDUP=PASS')
            print('SEGMENTS_CANONICAL_AND_HASH_VERIFIED=YES')
            print('ATOMIC_VISIBILITY_TEST=PASS')
            print('SIMULATED_EXCEPTION_BEFORE_PUBLISH=PASS_NO_PARTIAL_SEGMENT')
            print('RETENTION_CANDIDATES=1')
            print('RETENTION_ACTION=DRY_RUN_ONLY')
            print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
            print('PRODUCTION_CHANGES=NO')
            print('DEPLOYMENT_GATE=HOLD')
            print('V0145A_RESULT=PASS_SYNTHETIC_SEGMENTS_ONLY')
        finally:
            os.close(fd)
    print('TEMP_STATE_REMOVED=YES')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--self-test', action='store_true')
    g.add_argument('--lab', action='store_true')
    args = p.parse_args()
    try:
        if args.self_test:
            self_test()
        else:
            run_lab()
    except (Hold, OSError, AssertionError) as exc:
        print('V0145A_RESULT=HOLD_LAB_FAILURE')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
