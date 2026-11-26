#!/usr/bin/env python3
"""B3B2D: peer-aware guarded B2 subprocess, PROOF ONLY (not wired to HCC).

Only an explicit call can spawn a child. The fixed source CLI comes from B3B2A.
Automated tests monkeypatch its argv with synthetic Python children and never
access VictoriaMetrics, ASUS, production HCC or installed services.
"""
from __future__ import annotations

import json
import os
import selectors
import subprocess
import sys
import time

import v06_b3b2_source_supervisor as b3b2a
import v06_b3b2c_disconnect_lab as b3b2c

POLL_INTERVAL_SECONDS = b3b2c.POLL_INTERVAL_SECONDS
MAX_CHILD_SECONDS = b3b2a.MAX_CHILD_SECONDS
MAX_STDOUT_BYTES = b3b2a.MAX_STDOUT_BYTES
READ_BLOCK_BYTES = b3b2a.READ_BLOCK_BYTES


def read_b2_with_peer(window, peer):
    """One bounded, explicit fixed-B2 read that can be cancelled by peer loss.

    A detectable Linux TCP RDHUP/HUP/ERR/NVAL aborts the worker quickly.
    Cancellation is fail-closed UNKNOWN. No background read, polling task,
    persistent state, source caching, or caller-controlled command is added.
    """
    if type(window) is not str or window not in b3b2a.WINDOWS:
        return b3b2a.unknown()
    if b3b2c.disconnected(peer):
        return b3b2a.unknown()

    proc = None
    finished = False
    started = time.monotonic()
    try:
        argv = b3b2a._fixed_argv(window)
        proc = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            cwd=str(b3b2a.ROOT), start_new_session=True, close_fds=True,
            env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
        )
        if proc.stdout is None:
            raise ValueError("no source stdout")
        os.set_blocking(proc.stdout.fileno(), False)
        data = bytearray()
        deadline = started + MAX_CHILD_SECONDS
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            eof = False
            while not eof:
                if b3b2c.disconnected(peer):
                    raise ValueError("peer disconnected")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(argv, MAX_CHILD_SECONDS)
                for key, _ in selector.select(min(remaining, POLL_INTERVAL_SECONDS)):
                    # The source stdout can be ready as the peer closes.
                    # Never let readable source bytes outrank client cancellation.
                    if b3b2c.disconnected(peer):
                        raise ValueError("peer disconnected")
                    chunk = os.read(key.fileobj.fileno(), READ_BLOCK_BYTES)
                    if chunk:
                        if len(data) + len(chunk) > MAX_STDOUT_BYTES:
                            raise ValueError("too much source stdout")
                        data.extend(chunk)
                    else:
                        eof = True
                        selector.unregister(key.fileobj)
        if b3b2c.disconnected(peer):
            raise ValueError("peer disconnected at source EOF")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(argv, MAX_CHILD_SECONDS)
        # The B2 process is expected to exit immediately after stdout EOF;
        # poll/reap in short increments so disconnect still cancels the child.
        while proc.poll() is None:
            if b3b2c.disconnected(peer):
                raise ValueError("peer disconnected while waiting for source exit")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, MAX_CHILD_SECONDS)
            time.sleep(min(remaining, POLL_INTERVAL_SECONDS))
        if proc.returncode != 0:
            raise ValueError("source subprocess failed")
        # Revalidate exactly the same B1/B2 schema and interval constraints
        # as the merged source-only B3B2A module, not caller fields.
        outcome = b3b2a._project(bytes(data), window)
        if b3b2c.disconnected(peer):
            raise ValueError("peer disconnected during validation")
        finished = True
        return outcome
    except (OSError, ValueError, TypeError, UnicodeError,
            subprocess.SubprocessError):
        return b3b2a.unknown()
    finally:
        if proc is not None:
            if not finished:
                b3b2a._terminate_group(proc)
            if proc.stdout is not None:
                proc.stdout.close()


def inspect_contract():
    return {
        "mode": "INSPECT_ONLY_NO_NETWORK",
        "source_adapter": "FIXED_B2_WITH_PEER_ABORT_NOT_INVOKED",
        "peer_watch": "LINUX_POLLRDHUP_POLLHUP_POLLERR_POLLNVAL",
        "poll_interval_ms": round(POLL_INTERVAL_SECONDS * 1000),
        "max_child_seconds": MAX_CHILD_SECONDS,
        "max_stdout_bytes": MAX_STDOUT_BYTES,
        "http_endpoint": False, "autostart": False,
        "deployment_gate": "HOLD",
    }


if __name__ == "__main__":
    if sys.argv != [sys.argv[0], "--inspect"]:
        raise SystemExit("Only --inspect is available; source reads require explicit import")
    print(json.dumps(inspect_contract(), sort_keys=True))
