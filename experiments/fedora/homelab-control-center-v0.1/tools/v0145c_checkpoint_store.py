#!/usr/bin/env python3
"""HCC V0.14.5C: disposable checkpoint files for the offline snapshot model.

Only --self-test (memory only) and --lab (fresh disposable /tmp state). No
journal, service, network, real Alloy/Loki, production path or deletion of event
segments. Atomic replacement plus fsync is tested, not power-loss durability.
"""
from __future__ import annotations

import argparse
import os
import re
import stat
import tempfile

import v0145a_segment_spool as spool
import v0145b_segment_replay as replay

CHECKPOINT = 'checkpoint.json'
TEMP_RE = re.compile(r'\A\.checkpoint-[0-9a-f]{32}\.tmp\Z', re.ASCII)
FAILPOINTS = frozenset((None, 'after_ack_before_store',
                       'after_file_fsync_before_replace',
                       'after_replace_before_directory_fsync'))


def read_checkpoint(dirfd):
    """Missing state is allowed only in an otherwise empty private directory.

    Orphan temps always require review. Never silently restart at zero over a
    damaged/unknown state file. JSON/snapshot semantics are checked by replay.
    """
    spool.require_private_directory(dirfd)
    found = False
    with os.scandir(dirfd) as entries:
        for entry in entries:
            if TEMP_RE.fullmatch(entry.name):
                raise spool.Hold('ORPHAN_CHECKPOINT_REQUIRES_REVIEW')
            if entry.name != CHECKPOINT or found:
                raise spool.Hold('UNEXPECTED_CHECKPOINT_ENTRY')
            found = True
    if not found:
        return None
    fd = os.open(CHECKPOINT, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW |
                 os.O_CLOEXEC, dir_fd=dirfd)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid() or
                stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1 or
                not 0 < before.st_size <= replay.MAX_CHECKPOINT_BYTES):
            raise spool.Hold('UNSAFE_CHECKPOINT_METADATA')
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
            raise spool.Hold('CHECKPOINT_CHANGED_DURING_READ')
        return raw
    finally:
        os.close(fd)


def store_checkpoint(dirfd, raw, plan, expected, *, failpoint=None):
    """Compare current bytes, validate, fsync temp, replace, fsync directory.

    The caller holds the cooperative directory lock. This is not protection
    against root or an uncooperative same-UID process. Private temp names are
    cleaned on ordinary pre-replace errors; abrupt process exits may orphan
    them and then read_checkpoint refuses all further progress.
    """
    if failpoint not in (None, 'after_file_fsync_before_replace',
                         'after_replace_before_directory_fsync'):
        raise spool.Hold('UNSUPPORTED_FAILPOINT')
    if type(raw) is not bytes:
        raise spool.Hold('CHECKPOINT_BYTES_REQUIRED')
    replay.restore_checkpoint(raw, plan)
    current = read_checkpoint(dirfd)
    if current != expected:
        raise spool.Hold('CHECKPOINT_EXPECTATION_CHANGED')
    if current is not None:
        old_count = replay.restore_checkpoint(current, plan)
        new_count = replay.restore_checkpoint(raw, plan)
        if new_count not in (old_count, old_count + 1):
            raise spool.Hold('CHECKPOINT_PREFIX_STEP')
    elif replay.restore_checkpoint(raw, plan) != 0:
        raise spool.Hold('CHECKPOINT_INITIAL_PREFIX')
    if current == raw:
        os.fsync(dirfd)
        return
    temp = '.checkpoint-' + os.urandom(16).hex() + '.tmp'
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW |
                 os.O_CLOEXEC, 0o600, dir_fd=dirfd)
    replaced = False
    try:
        try:
            os.fchmod(fd, 0o600)
            spool.write_all(fd, raw)
            os.fsync(fd)
        finally:
            os.close(fd)
        if failpoint == 'after_file_fsync_before_replace':
            raise spool.SimulatedInterrupt('TEST_CHECKPOINT_BEFORE_REPLACE')
        os.replace(temp, CHECKPOINT, src_dir_fd=dirfd, dst_dir_fd=dirfd)
        replaced = True
        if failpoint == 'after_replace_before_directory_fsync':
            raise spool.SimulatedInterrupt('TEST_CHECKPOINT_REPLACED_SYNC_UNCERTAIN')
        os.fsync(dirfd)
    finally:
        if not replaced:
            os.unlink(temp, dir_fd=dirfd)
            os.fsync(dirfd)


def advance_one(spoolfd, statefd, receiver, *, failpoint=None):
    """Freeze/validate all inputs before sending; persist only after exact ACK.

    Missing initial state is written at prefix zero before the first send.
    A saved checkpoint fixes the snapshot even if that first receiver rejects.
    At completion, retry directory fsync without sending or deleting anything.
    """
    if failpoint not in FAILPOINTS:
        raise spool.Hold('UNSUPPORTED_FAILPOINT')
    spool.require_private_directory(spoolfd)
    spool.require_private_directory(statefd)
    left, right = os.fstat(spoolfd), os.fstat(statefd)
    if (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino):
        raise spool.Hold('SEPARATE_STATE_DIRECTORY_REQUIRED')
    plan = replay.snapshot(spoolfd)
    current = read_checkpoint(statefd)
    prefix = replay.restore_checkpoint(current, plan)
    if current is None:
        current = replay.checkpoint_bytes(plan.digest, 0)
        store_checkpoint(statefd, current, plan, None)
    # Retry a previous uncertain directory barrier before any new receive.
    os.fsync(statefd)
    if prefix == len(plan.segments):
        return 'COMPLETE_NO_SEND'
    item = plan.segments[prefix]
    if receiver(item.name, item.content) != item.name:
        raise spool.Hold('RECEIVER_ACK_MISMATCH')
    if failpoint == 'after_ack_before_store':
        raise spool.SimulatedInterrupt('TEST_ACK_WITHOUT_CHECKPOINT_STORE')
    updated = replay.checkpoint_bytes(plan.digest, prefix + 1)
    store_checkpoint(statefd, updated, plan, current, failpoint=failpoint)
    return 'ACKNOWLEDGED_CHECKPOINT_FILE'


def self_test():
    plan = replay.Snapshot('a' * 64, ())
    assert replay.restore_checkpoint(replay.checkpoint_bytes(plan.digest, 0), plan) == 0
    assert TEMP_RE.fullmatch('.checkpoint-' + 'a' * 32 + '.tmp')
    assert not TEMP_RE.fullmatch('../checkpoint.json')
    print('V0145C_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')
    print('SELFTEST_NO_NETWORK_NO_SUBPROCESS_NO_FILE_WRITES=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    with tempfile.TemporaryDirectory(prefix='hcc-v0145c-synthetic-', dir='/tmp') as folder:
        os.chmod(folder, 0o700)
        spool_path, state_path = os.path.join(folder, 'segments'), os.path.join(folder, 'state')
        os.mkdir(spool_path, 0o700)
        os.mkdir(state_path, 0o700)
        spoolfd, statefd = spool.open_private_directory(spool_path), None
        try:
            statefd = spool.open_private_directory(state_path)
            for minute in ('00', '01'):
                spool.publish(spoolfd, spool.event('2026-10-30T09:' + minute + ':00.000Z', 'SSH_TIMEOUT'))
            sink = replay.FakeReceiver()
            assert advance_one(spoolfd, statefd, sink) == 'ACKNOWLEDGED_CHECKPOINT_FILE'
            os.close(statefd)
            statefd = None
            os.close(spoolfd)
            spoolfd = None
            spoolfd = spool.open_private_directory(spool_path)
            statefd = spool.open_private_directory(state_path)
            assert replay.restore_checkpoint(read_checkpoint(statefd), replay.snapshot(spoolfd)) == 1
            try:
                advance_one(spoolfd, statefd, sink, failpoint='after_ack_before_store')
            except spool.SimulatedInterrupt:
                pass
            else:
                raise AssertionError('INTERRUPT_NOT_OBSERVED')
            assert advance_one(spoolfd, statefd, sink) == 'ACKNOWLEDGED_CHECKPOINT_FILE'
            assert advance_one(spoolfd, statefd, sink) == 'COMPLETE_NO_SEND'
            assert len(sink.received) == 3 and sink.received[1] == sink.received[2]
            assert replay.restore_checkpoint(read_checkpoint(statefd), replay.snapshot(spoolfd)) == 2
            print('=== HCC V0.14.5C / DISPOSABLE CHECKPOINT FILE ===')
            print('CHECKPOINT_PREFIX_AFTER_REOPEN=1')
            print('CHECKPOINT_FINAL_PREFIX=2')
            print('SYNTHETIC_RECEIVE_ATTEMPTS=3')
            print('ACK_WITHOUT_STORE_REPLAY=OBSERVED_DUPLICATE_ATTEMPT')
            print('CHECKPOINT_FILE=PRIVATE_ATOMIC_REPLACE_WITH_FSYNC')
            print('REOPEN_TEST=SAME_PROCESS_NEW_DESCRIPTORS')
            print('POWER_LOSS_DURABILITY=NOT_TESTED')
            print('RETENTION_ACTION=NO_DELETION')
            print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
            print('NETWORK=NO PRODUCTION_CHANGES=NO')
            print('V0145C_RESULT=PASS_DISPOSABLE_CHECKPOINT_ONLY')
        finally:
            if statefd is not None:
                os.close(statefd)
            if spoolfd is not None:
                os.close(spoolfd)
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
        print('V0145C_RESULT=HOLD_LAB_FAILURE')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
