#!/usr/bin/env python3
"""HCC V0.14.5E: atomic synthetic identity/payload handoff snapshot.

One canonical private file contains IDs and complete D-format event payloads.
CLI: --self-test (memory only), --lab (fresh disposable /tmp directory).
No real journal/key, receiver, network, service, A-C adapter or retention GC.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
import json
import os
import re
import stat
import tempfile

import v0145a_segment_spool as spool
import v0145d_event_identity as identity

SCHEMA = 'hcc-v0145e-handoff/1'
NAME = 'handoff.json'
TEMP_RE = re.compile(r'\A\.handoff-[0-9a-f]{32}\.tmp\Z', re.ASCII)
HASH_RE = re.compile(r'\A[0-9a-f]{64}\Z', re.ASCII)
TIME_RE = re.compile(r'\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z', re.ASCII)
EVENT_KEYS = frozenset(('schema', 'scope', 'event_id', 'time', 'kind', 'component', 'source'))
MAX_EVENTS = 1024
MAX_SNAPSHOT_BYTES = 512 * 1024
FAILPOINTS = frozenset((None, 'after_temp_fsync_before_replace',
                       'after_replace_before_dir_fsync', 'after_dir_fsync_before_return'))


@dataclass(frozen=True)
class Snapshot:
    scope: str
    events: tuple[bytes, ...]


@dataclass(frozen=True)
class Receipt:
    status: str
    accepted: int
    duplicates: int
    retained: int


def encode_snapshot(scope, events):
    """Internal encoder: rows arrive canonical from D or decode_snapshot."""
    body = {'schema': SCHEMA, 'scope': scope,
            'events': [json.loads(event) for event in events]}
    digest = hashlib.sha256(identity.canonical(body)).hexdigest()
    raw = identity.canonical(dict(body, digest=digest)) + b'\n'
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise spool.Hold('HANDOFF_BYTES_LIMIT')
    return raw


def decode_snapshot(raw):
    """Validate full payload before trusting any ID; digest is not authentication."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_SNAPSHOT_BYTES:
        raise spool.Hold('HANDOFF_BYTES_LIMIT')
    try:
        obj = json.loads(raw.decode('ascii'), object_pairs_hook=spool.no_duplicates,
                         parse_constant=lambda _: (_ for _ in ()).throw(spool.Hold('HANDOFF_NONFINITE')))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise spool.Hold('HANDOFF_JSON') from exc
    if type(obj) is not dict or set(obj) != {'schema', 'scope', 'events', 'digest'}:
        raise spool.Hold('HANDOFF_SCHEMA')
    if (obj['schema'] != SCHEMA or type(obj['scope']) is not str or
            not HASH_RE.fullmatch(obj['scope']) or type(obj['digest']) is not str or
            not HASH_RE.fullmatch(obj['digest']) or type(obj['events']) is not list or
            not 1 <= len(obj['events']) <= MAX_EVENTS):
        raise spool.Hold('HANDOFF_VALUE')
    events, prior = [], None
    for event in obj['events']:
        if type(event) is not dict or set(event) != EVENT_KEYS or any(type(v) is not str for v in event.values()):
            raise spool.Hold('HANDOFF_EVENT_SCHEMA')
        if (event['schema'] != identity.SCHEMA or event['source'] != identity.SOURCE or
                event['component'] != spool.EXPECTED_COMPONENT or event['scope'] != obj['scope'] or
                event['kind'] not in spool.ALLOWED_KINDS or not HASH_RE.fullmatch(event['event_id']) or
                not TIME_RE.fullmatch(event['time'])):
            raise spool.Hold('HANDOFF_EVENT_VALUE')
        try:
            stamp = datetime.fromisoformat(event['time'][:-1] + '+00:00')
        except ValueError as exc:
            raise spool.Hold('HANDOFF_EVENT_TIME') from exc
        if not 2000 <= stamp.year <= 2100:
            raise spool.Hold('HANDOFF_EVENT_TIME')
        if prior is not None and event['event_id'] <= prior:
            raise spool.Hold('HANDOFF_ID_ORDER_OR_DUPLICATE')
        prior = event['event_id']
        events.append(identity.canonical(event))
    body = {'schema': obj['schema'], 'scope': obj['scope'], 'events': obj['events']}
    digest = hashlib.sha256(identity.canonical(body)).hexdigest()
    if not hmac.compare_digest(digest, obj['digest']):
        raise spool.Hold('HANDOFF_DIGEST_MISMATCH')
    if encode_snapshot(obj['scope'], events) != raw:
        raise spool.Hold('HANDOFF_NONCANONICAL')
    return Snapshot(obj['scope'], tuple(events))


def read_handoff(dirfd):
    """No missing-state reset if any unknown/orphan entry is present."""
    spool.require_private_directory(dirfd)
    found = False
    with os.scandir(dirfd) as entries:
        for entry in entries:
            if TEMP_RE.fullmatch(entry.name):
                raise spool.Hold('ORPHAN_HANDOFF_REQUIRES_REVIEW')
            if entry.name != NAME or found:
                raise spool.Hold('UNEXPECTED_HANDOFF_ENTRY')
            found = True
    if not found:
        return None
    fd = os.open(NAME, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=dirfd)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid() or
                stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1 or
                not 0 < before.st_size <= MAX_SNAPSHOT_BYTES):
            raise spool.Hold('UNSAFE_HANDOFF_METADATA')
        chunks, remaining = [], before.st_size + 1
        while remaining:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b''.join(chunks)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if len(raw) != before.st_size or any(getattr(before, k) != getattr(after, k) for k in fields):
            raise spool.Hold('HANDOFF_CHANGED_DURING_READ')
        return decode_snapshot(raw)
    finally:
        os.close(fd)


def publish_handoff(dirfd, raw, key, *, failpoint=None):
    """Store event ID and its payload together; no separate precommitted ledger.

    A receipt is not a receiver ACK. Previously committed payload remains readable
    even if the caller loses the receipt or fails a later delivery attempt.
    """
    if failpoint not in FAILPOINTS:
        raise spool.Hold('UNSUPPORTED_FAILPOINT')
    events = identity.normalized_events(raw, key)
    scope = identity.scope_for(key)
    current = read_handoff(dirfd)
    if current is not None and not hmac.compare_digest(current.scope, scope):
        raise spool.Hold('HANDOFF_SCOPE_CHANGED')
    previous = {} if current is None else {json.loads(e)['event_id']: e for e in current.events}
    combined, accepted, duplicates = dict(previous), 0, 0
    for event in events:
        event_id = json.loads(event)['event_id']
        existing = combined.get(event_id)
        if existing is not None:
            if existing != event:
                raise spool.Hold('SAME_ID_DIFFERENT_PAYLOAD')
            duplicates += 1
        else:
            combined[event_id] = event
            accepted += 1
    if len(combined) > MAX_EVENTS:
        raise spool.Hold('HANDOFF_EVENT_LIMIT')
    if not accepted:
        # Re-establish a possibly uncertain directory barrier without new data.
        os.fsync(dirfd)
        return Receipt('DUPLICATE_HANDOFF_NO_WRITE', 0, duplicates, len(combined))
    content = encode_snapshot(scope, [combined[k] for k in sorted(combined)])
    # Verify the complete prospective snapshot before any temporary file exists.
    decode_snapshot(content)
    temp = '.handoff-' + os.urandom(16).hex() + '.tmp'
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=dirfd)
    replaced = False
    try:
        try:
            os.fchmod(fd, 0o600)
            spool.write_all(fd, content)
            os.fsync(fd)
        finally:
            os.close(fd)
        if failpoint == 'after_temp_fsync_before_replace':
            raise spool.SimulatedInterrupt('TEST_HANDOFF_BEFORE_REPLACE')
        os.replace(temp, NAME, src_dir_fd=dirfd, dst_dir_fd=dirfd)
        replaced = True
        if failpoint == 'after_replace_before_dir_fsync':
            raise spool.SimulatedInterrupt('TEST_HANDOFF_REPLACED_SYNC_UNCERTAIN')
        os.fsync(dirfd)
        if failpoint == 'after_dir_fsync_before_return':
            raise spool.SimulatedInterrupt('TEST_HANDOFF_RECEIPT_LOST')
        return Receipt('PUBLISHED_HANDOFF_SNAPSHOT', accepted, duplicates, len(combined))
    finally:
        if not replaced:
            os.unlink(temp, dir_fd=dirfd)
            os.fsync(dirfd)


def self_test():
    events = identity.normalized_events(identity.envelope('synthetic-cursor-001'), identity.SYNTHETIC_KEY)
    content = encode_snapshot(identity.scope_for(identity.SYNTHETIC_KEY), events)
    assert decode_snapshot(content).events == events
    try:
        decode_snapshot(content.replace(b'SSH_TIMEOUT', b'HTTP_IMPORT_TIMEOUT'))
    except spool.Hold:
        pass
    else:
        raise AssertionError('CORRUPT_PAYLOAD_ACCEPTED')
    print('V0145E_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')
    print('SELFTEST_NO_NETWORK_NO_SUBPROCESS_NO_FILE_WRITES=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    with tempfile.TemporaryDirectory(prefix='hcc-v0145e-synthetic-', dir='/tmp') as folder:
        os.chmod(folder, 0o700)
        fd = spool.open_private_directory(folder)
        try:
            key = identity.SYNTHETIC_KEY
            first = identity.envelope('synthetic-cursor-001')
            second = identity.envelope('synthetic-cursor-002')
            third = identity.envelope('synthetic-cursor-003')
            publish_handoff(fd, first + second, key)  # Caller discards receipt.
            os.close(fd)
            fd = None
            fd = spool.open_private_directory(folder)
            repeated = publish_handoff(fd, first + second, key)
            assert repeated.accepted == 0 and repeated.duplicates == 2
            assert len(read_handoff(fd).events) == 2  # Data did not disappear.
            try:
                publish_handoff(fd, third, key, failpoint='after_dir_fsync_before_return')
            except spool.SimulatedInterrupt:
                pass
            else:
                raise AssertionError('INTERRUPT_NOT_OBSERVED')
            assert publish_handoff(fd, third, key).duplicates == 1
            assert len(read_handoff(fd).events) == 3
            print('=== HCC V0.14.5E / ATOMIC IDENTITY-PAYLOAD HANDOFF ===')
            print('INITIAL_IDENTITIES_AND_PAYLOADS=2')
            print('REOPEN_REPLAY_NEW_EVENTS=0')
            print('REOPEN_REPLAY_RETAINED_PAYLOADS=2')
            print('LOST_COMMIT_RECEIPT=REPLAY_FOUND_EXISTING_PAYLOAD')
            print('FINAL_IDENTITIES_AND_PAYLOADS=3')
            print('STORE=ONE_CANONICAL_PRIVATE_SNAPSHOT_WITH_FSYNC')
            print('DIGEST_AUTHENTICATION=NO_CORRUPTION_CHECK_ONLY')
            print('RECEIVER_ACK=NOT_IMPLEMENTED')
            print('POWER_LOSS_DURABILITY=NOT_TESTED')
            print('RETENTION_ACTION=NO_DELETION')
            print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
            print('NETWORK=NO PRODUCTION_CHANGES=NO')
            print('V0145E_RESULT=PASS_DISPOSABLE_ATOMIC_HANDOFF_ONLY')
        finally:
            if fd is not None:
                os.close(fd)
    print('TEMP_STATE_REMOVED=YES')
    print('DEPLOYMENT_GATE=HOLD')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--self-test', action='store_true')
    modes.add_argument('--lab', action='store_true')
    args = parser.parse_args()
    try:
        self_test() if args.self_test else run_lab()
    except (spool.Hold, OSError, AssertionError) as exc:
        print('V0145E_RESULT=HOLD_HANDOFF_FAILURE')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
