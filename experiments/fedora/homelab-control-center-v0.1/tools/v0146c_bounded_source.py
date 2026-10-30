#!/usr/bin/env python3
"""V0.14.6C: bounded owned Python source -> A/B disposable import.

The source is a fixed synthetic producer, NOT journalctl or a trusted journal
reader. CLI offers only --self-test / --lab; no command/path/UID/key input.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass, field
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time

import v0145a_segment_spool as spool
import v0145d_event_identity as identity
import v0145e_atomic_handoff as handoff
import v0146a_journal_envelope as adapter
import v0146b_disposable_import as importer

SOURCE_SECONDS = 2
REAP_SECONDS = 1
MAX_STDERR_BYTES = 1024
MAX_JOB_BYTES = 2 * adapter.MAX_BYTES
BLOCK_BYTES = 8192
MODES = ('normal', 'split', 'stall_before_output', 'stall_after_output', 'close_pipes_then_stall')

# Fixed trusted test code, not supplied code, a shell or a production command.
# Limits in the parent also apply while the child is still writing.
_FIXTURE_PROGRAM = r'''
import base64, json, os, sys, time
job = json.loads(sys.stdin.buffer.read(2097153))
out = base64.b64decode(job['stdout'], validate=True)
err = base64.b64decode(job['stderr'], validate=True)
def write_all(fd, data):
    while data:
        count = os.write(fd, data[:8192])
        data = data[count:]
if job['mode'] == 'stall_before_output':
    time.sleep(30)
if job['mode'] == 'close_pipes_then_stall':
    os.close(1)
    os.close(2)
    time.sleep(30)
if job['mode'] == 'split':
    middle = len(out) // 2
    write_all(1, out[:middle])
    write_all(2, err)
    write_all(1, out[middle:])
else:
    write_all(2, err)
    write_all(1, out)
if job['mode'] == 'stall_after_output':
    time.sleep(30)
sys.exit(job['exit_code'])
'''


@dataclass(frozen=True)
class SourceFixture:
    stdout: bytes = field(repr=False)
    stderr: bytes = field(default=b'', repr=False)
    exit_code: int = 0
    mode: str = 'normal'


@dataclass(frozen=True)
class SourceImportReceipt:
    source_bytes: int
    source_rows: int
    imported: importer.ImportReceipt


def _fixture_job(fixture):
    if (type(fixture) is not SourceFixture or type(fixture.stdout) is not bytes or
            len(fixture.stdout) > adapter.MAX_BYTES + 1 or type(fixture.stderr) is not bytes or
            len(fixture.stderr) > MAX_STDERR_BYTES + 1 or type(fixture.exit_code) is not int or
            not 0 <= fixture.exit_code <= 255 or type(fixture.mode) is not str or fixture.mode not in MODES):
        raise spool.Hold('SOURCE_FIXTURE_SHAPE')
    raw = identity.canonical({'stdout': base64.b64encode(fixture.stdout).decode('ascii'),
                              'stderr': base64.b64encode(fixture.stderr).decode('ascii'),
                              'exit_code': fixture.exit_code, 'mode': fixture.mode})
    if len(raw) > MAX_JOB_BYTES:
        raise spool.Hold('SOURCE_JOB_LIMIT')
    return raw


def _validate_framing(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= adapter.MAX_BYTES:
        raise spool.Hold('SOURCE_EMPTY_OR_OVERSIZED_BATCH')
    if not raw.endswith(b'\n') or raw.count(b'\n') > adapter.MAX_ROWS:
        raise spool.Hold('SOURCE_INCOMPLETE_OR_EXCESS_ROWS')
    # Required field types, blank rows, UTF-8 and full metadata are A's job.


def _kill_and_reap(proc):
    kill_error = None
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as exc:
            kill_error = exc
    try:
        proc.wait(timeout=REAP_SECONDS)
    except (OSError, subprocess.SubprocessError) as exc:
        raise spool.Hold('SOURCE_CLEANUP_UNCERTAIN') from exc
    if kill_error is not None:
        raise spool.Hold('SOURCE_CLEANUP_UNCERTAIN') from kill_error


def capture_fixture(fixture):
    """Return a complete bounded JSONL frame only after exit 0 and empty stderr.

    Deadline begins AFTER Popen returns; includes input, both outputs and wait.
    Fixed trusted Python has no descendants. This is not a hostile-code sandbox
    or an OS guarantee on process creation, scheduling, kill or filesystem time.
    """
    job = _fixture_job(fixture)  # Reject before creating a process.
    proc = None
    completed = False
    try:
        proc = subprocess.Popen([sys.executable, '-I', '-B', '-c', _FIXTURE_PROGRAM],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                shell=False, close_fds=True, start_new_session=True, bufsize=0,
                                env={'LC_ALL': 'C', 'LANG': 'C', 'TZ': 'UTC'})
        deadline = time.monotonic() + SOURCE_SECONDS
        if any(stream is None for stream in (proc.stdin, proc.stdout, proc.stderr)):
            raise spool.Hold('SOURCE_PIPE_SETUP')
        buffers = {'stdout': bytearray(), 'stderr': bytearray()}
        limits = {'stdout': adapter.MAX_BYTES, 'stderr': MAX_STDERR_BYTES}
        offset = rows = 0
        with selectors.DefaultSelector() as selector:
            for stream, name in ((proc.stdin, 'stdin'), (proc.stdout, 'stdout'), (proc.stderr, 'stderr')):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_WRITE if name == 'stdin' else selectors.EVENT_READ,
                                  name)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise spool.Hold('SOURCE_DEADLINE')
                for selected, _ in selector.select(min(remaining, 0.05)):
                    stream, name = selected.fileobj, selected.data
                    if name == 'stdin':
                        try:
                            count = os.write(stream.fileno(), job[offset:offset + BLOCK_BYTES])
                        except BlockingIOError:
                            continue
                        if count <= 0:
                            raise spool.Hold('SOURCE_INPUT_WRITE')
                        offset += count
                        if offset == len(job):
                            selector.unregister(stream)
                            stream.close()
                        continue
                    try:
                        part = os.read(stream.fileno(), min(BLOCK_BYTES, limits[name] + 1 - len(buffers[name])))
                    except BlockingIOError:
                        continue
                    if not part:
                        selector.unregister(stream)
                        continue
                    buffers[name].extend(part)
                    if len(buffers[name]) > limits[name]:
                        raise spool.Hold('SOURCE_' + name.upper() + '_LIMIT')
                    if name == 'stdout':
                        rows += part.count(b'\n')
                        if rows > adapter.MAX_ROWS:
                            raise spool.Hold('SOURCE_ROW_LIMIT')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise spool.Hold('SOURCE_DEADLINE')
        try:
            status = proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise spool.Hold('SOURCE_DEADLINE') from exc
        if status != 0:
            raise spool.Hold('SOURCE_NONZERO_EXIT')
        if buffers['stderr']:
            raise spool.Hold('SOURCE_STDERR_NOT_EMPTY')
        raw = bytes(buffers['stdout'])
        _validate_framing(raw)
        completed = True
        return raw
    except (OSError, subprocess.SubprocessError) as exc:
        raise spool.Hold('SOURCE_PROCESS_IO') from exc
    finally:
        if proc is not None:
            try:
                if not completed:
                    _kill_and_reap(proc)
            finally:
                for stream in (proc.stdin, proc.stdout, proc.stderr):
                    if stream is not None:
                        stream.close()


def import_fixture(dirfd, fixture, *, expected_uid, key):
    """No store read/write until successful source completion and A validation.

    B independently validates/locks the retained store and commits atomically.
    Source success alone grants no provenance, ACK or source-progress evidence.
    """
    importer.policy_key(expected_uid, key)  # Validate options before spawning.
    raw = capture_fixture(fixture)
    receipt = importer.import_batch(dirfd, raw, expected_uid=expected_uid, key=key)
    return SourceImportReceipt(len(raw), raw.count(b'\n'), receipt)


def self_test():
    fixture = SourceFixture(adapter.fixture_inputs())
    assert len(_fixture_job(fixture)) <= MAX_JOB_BYTES
    _validate_framing(fixture.stdout)
    result = adapter.adapt_snapshot(fixture.stdout, expected_uid=1000,
                                    key=importer.policy_key(1000, identity.SYNTHETIC_KEY))
    assert (result.accepted_events, result.duplicate_events) == (3, 1)
    print('V0146C_SELFTEST=PASS_PURE_SOURCE_CONTRACT_ONLY')
    print('NO_FILES_NO_NETWORK_NO_SUBPROCESS=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    with tempfile.TemporaryDirectory(prefix='hcc-v0146c-synthetic-', dir='/tmp') as folder:
        os.chmod(folder, 0o700)
        fd = spool.open_private_directory(folder)
        try:
            options = {'expected_uid': 1000, 'key': identity.SYNTHETIC_KEY}
            raw = adapter.fixture_inputs()
            first = import_fixture(fd, SourceFixture(raw, mode='split'), **options)
            assert (first.source_rows, first.imported.accepted_events) == (5, 3)
            repeated = import_fixture(fd, SourceFixture(raw), **options)
            assert repeated.imported.duplicate_events == 4
            before = handoff.read_handoff(fd)
            try:
                import_fixture(fd, SourceFixture(raw, exit_code=23), **options)
            except spool.Hold as exc:
                assert str(exc) == 'SOURCE_NONZERO_EXIT'
            else:
                raise AssertionError('FAILED_SOURCE_ACCEPTED')
            assert handoff.read_handoff(fd) == before
        finally:
            os.close(fd)
    print('=== HCC V0.14.6C / BOUNDED SYNTHETIC SOURCE IMPORT ===')
    print('SOURCE=FIXED_OWNED_PYTHON_FIXTURE JOURNALCTL_EXECUTED=NO')
    print('SOURCE_ROWS=5 INITIAL_RETAINED_EVENTS=3 REPLAY_DUPLICATES=4')
    print('LATE_NONZERO_EXIT=HOLD_NO_STORE_CHANGE')
    print('SOURCE_LIMITS=1MIB_128_ROWS_STDERR_1KIB')
    print('DEADLINE=2S_AFTER_POPEN CLEANUP=KILL_AND_REAP_1S')
    print('SOURCE_PROVENANCE=UNVERIFIED_SYNTHETIC_BYTES')
    print('TRUSTED_JOURNAL_READER=NOT_IMPLEMENTED')
    print('ACK_OR_SOURCE_CURSOR=NOT_IMPLEMENTED RETENTION_ACTION=NO_DELETION')
    print('POWER_LOSS_DURABILITY=NOT_TESTED')
    print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
    print('NETWORK=NO SUBPROCESS=OWNED_PYTHON_ONLY PRODUCTION_CHANGES=NO')
    print('TEMP_STATE_REMOVED=YES')
    print('V0146C_RESULT=PASS_BOUNDED_FIXTURE_IMPORT_ONLY')
    print('DEPLOYMENT_GATE=HOLD')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--self-test', action='store_true')
    mode.add_argument('--lab', action='store_true')
    args = parser.parse_args()
    try:
        self_test() if args.self_test else run_lab()
    except (spool.Hold, OSError, AssertionError) as exc:
        print('V0146C_RESULT=HOLD_BOUNDED_FIXTURE_IMPORT')
        # HOLD messages in these modules are fixed rejection codes, never
        # captured stdout/stderr or raw journal-like fields.
        print('REASON=' + (str(exc) if isinstance(exc, spool.Hold) else type(exc).__name__))
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
