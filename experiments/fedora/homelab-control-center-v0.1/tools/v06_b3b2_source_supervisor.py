#!/usr/bin/env python3
"""HCC V0.6-B3B2A isolated source subprocess guard, NOT an HTTP endpoint.

This source-only module has no import-time side effects or active reader.
The sole default child is the pinned B2 local VM CLI. Tests replace the fixed
argv with harmless synthetic subprocesses and never contact a real source.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time

import v06_coverage_model as coverage
import v06_history_source as b2

WINDOWS = tuple(coverage.WINDOWS_MS)
MAX_CHILD_SECONDS = 12.0  # provisional TOTAL child lifecycle, not an HTTP SLO
MAX_STDOUT_BYTES = 65536  # checked while reading, not after buffering
READ_BLOCK_BYTES = 4096
ROOT = Path(__file__).resolve().parent
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")

def unknown():
    result = coverage.unknown("SOURCE_UNAVAILABLE_OR_INVALID")
    result["source_adapter"] = b2.SCHEMA
    return result

def _object_no_dupes(pairs):
    out = {}
    for key, val in pairs:
        if key in out:
            raise ValueError("duplicate key")
        out[key] = val
    return out

def _reject_constant(_):
    raise ValueError("nonfinite JSON")

def _instant(s):
    if type(s) is not str or not ISO.fullmatch(s):
        raise ValueError("invalid time")
    parsed = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    if coverage.utc(int(parsed.timestamp() * 1000)) != s:
        raise ValueError("noncanonical time")
    return int(parsed.timestamp() * 1000)

def _whole(x, lower, upper):
    if type(x) is not int or x < lower or x > upper:
        raise ValueError("bad integer")
    return x

def _project(raw, requested_window):
    """Whitelisted B1/B2 shape only; never copy arbitrary child fields."""
    data = json.loads(raw.decode("ascii"), object_pairs_hook=_object_no_dupes,
                      parse_constant=_reject_constant)
    if type(data) is not dict or type(requested_window) is not str or requested_window not in WINDOWS:
        raise ValueError("invalid source")
    if (data.get("schema_version") != coverage.SCHEMA or
        data.get("source_adapter") != b2.SCHEMA or
        data.get("source") != coverage.SOURCE or
        data.get("mode") != "OFFLINE_EVIDENCE_ONLY" or
        data.get("deployment_gate") != "HOLD" or
        data.get("window") != requested_window or
        data.get("reason_code") != "SAMPLED_COVERAGE_ONLY" or
        data.get("status") not in ("COVERAGE_OBSERVED", "COVERAGE_OBSERVED_WITH_UNCERTAINTY")):
        raise ValueError("invalid evidence provenance")
    start, end = _instant(data.get("window_start_utc")), _instant(data.get("window_end_utc"))
    if end-start != coverage.WINDOWS_MS[requested_window]:
        raise ValueError("wrong window")
    count = _whole(data.get("sample_count"), 1, coverage.MAX_SAMPLES)
    invalid = _whole(data.get("invalid_sample_count"), 0, count)
    skew = _whole(data.get("max_cross_series_skew_ms"), 0, coverage.MAX_SKEW_MS)
    gap_input, seg_input = data.get("gaps"), data.get("segments")
    if (type(gap_input) is not list or type(seg_input) is not list or
        len(gap_input) > coverage.MAX_OUTPUT_ITEMS or
        len(seg_input) > coverage.MAX_OUTPUT_ITEMS):
        raise ValueError("too many intervals")
    gaps, segments = [], []
    previous = -1
    for g in gap_input:
        if (type(g) is not dict or g.get("kind") != "TELEMETRY_GAP" or
            g.get("cause") != "NOT_DETERMINED" or
            g.get("position") not in ("LEADING", "INTERNAL", "TRAILING")):
            raise ValueError("invalid gap")
        a, z = _instant(g.get("start_utc")), _instant(g.get("end_utc"))
        duration = g.get("duration_seconds")
        if (a < start or z > end or z-a <= coverage.GAP_THRESHOLD_MS or
            a < previous or type(duration) not in (int, float) or
            not math.isfinite(duration) or abs((z-a)/1000 - duration) > .001):
            raise ValueError("invalid gap timing")
        gaps.append({"kind": "TELEMETRY_GAP", "position": g["position"],
                     "start_utc": g["start_utc"], "end_utc": g["end_utc"],
                     "duration_seconds": duration, "cause": "NOT_DETERMINED"})
        previous = z
    previous = -1
    valid_sum = 0
    for s in seg_input:
        if (type(s) is not dict or s.get("kind") != "OBSERVED_TELEMETRY_SEGMENT" or
            s.get("interpretation") != "SAMPLED_TELEMETRY_NOT_DNS_UPTIME"):
            raise ValueError("invalid observed segment")
        a, z = _instant(s.get("start_utc")), _instant(s.get("end_utc"))
        n = _whole(s.get("sample_count"), 1, count)
        if (a < start or z > end or a > z or a <= previous or
            any(_instant(g["start_utc"]) < z and a < _instant(g["end_utc"]) for g in gaps)):
            raise ValueError("invalid segment timing")
        valid_sum += n
        if valid_sum > count:
            raise ValueError("invalid count")
        segments.append({"kind": "OBSERVED_TELEMETRY_SEGMENT", "start_utc": s["start_utc"],
                         "end_utc": s["end_utc"], "sample_count": n,
                         "interpretation": "SAMPLED_TELEMETRY_NOT_DNS_UPTIME"})
        previous = z
    if valid_sum != count-invalid:
        raise ValueError("count mismatch")
    if data["status"] != ("COVERAGE_OBSERVED_WITH_UNCERTAINTY" if gaps or invalid
                          else "COVERAGE_OBSERVED"):
        raise ValueError("contradictory status")
    # Align the Python source boundary with the B3A browser contract.
    # Do not forward a sample-continuity claim with missing or forged gaps.
    positions = [g["position"] for g in gaps]
    if (positions.count("LEADING") > 1 or positions.count("TRAILING") > 1 or
        "LEADING" in positions[1:] or "TRAILING" in positions[:-1]):
        raise ValueError("invalid gap position ordering")
    if invalid == 0:
        internal = [g for g in gaps if g["position"] == "INTERNAL"]
        if len(segments) != len(internal) + 1:
            raise ValueError("internal gaps and segment count mismatch")
        first = _instant(segments[0]["start_utc"])
        last = _instant(segments[-1]["end_utc"])
        leading = gaps[0] if positions and positions[0] == "LEADING" else None
        trailing = gaps[-1] if positions and positions[-1] == "TRAILING" else None
        if leading is not None:
            if _instant(leading["start_utc"]) != start or _instant(leading["end_utc"]) != first:
                raise ValueError("incorrect leading gap")
        elif first - start > coverage.GAP_THRESHOLD_MS:
            raise ValueError("missing leading gap")
        if trailing is not None:
            if _instant(trailing["start_utc"]) != last or _instant(trailing["end_utc"]) != end:
                raise ValueError("incorrect trailing gap")
        elif end - last > coverage.GAP_THRESHOLD_MS:
            raise ValueError("missing trailing gap")
        for idx, gap in enumerate(internal):
            if (_instant(gap["start_utc"]) != _instant(segments[idx]["end_utc"]) or
                _instant(gap["end_utc"]) != _instant(segments[idx + 1]["start_utc"])):
                raise ValueError("misaligned internal gap")
        for seg in segments:
            duration = _instant(seg["end_utc"]) - _instant(seg["start_utc"])
            rows = seg["sample_count"]
            if duration < rows - 1 or duration > (rows - 1) * coverage.GAP_THRESHOLD_MS:
                raise ValueError("impossible sampled segment duration")
    return {"schema_version": coverage.SCHEMA, "source_adapter": b2.SCHEMA,
            "source": coverage.SOURCE, "mode": "OFFLINE_EVIDENCE_ONLY",
            "deployment_gate": "HOLD", "reason_code": "SAMPLED_COVERAGE_ONLY",
            "window": requested_window, "window_start_utc": data["window_start_utc"],
            "window_end_utc": data["window_end_utc"], "status": data["status"],
            "sample_count": count, "invalid_sample_count": invalid,
            "max_cross_series_skew_ms": skew, "segments": segments, "gaps": gaps,
            "limitations": "SAMPLED_TELEMETRY_NOT_DNS_UPTIME_OR_POWER_STATE"}

def _fixed_argv(window):
    if window not in WINDOWS:
        raise ValueError("unsupported window")
    return [sys.executable, "-B", str(ROOT / "v06_history_source.py"),
            "--read-local", "--window", window]

def _terminate_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=1)
    except (subprocess.SubprocessError, OSError):
        pass

def read_b2_supervised(window):
    """Explicit caller only. Bound elapsed child lifetime and stdout IN FLIGHT."""
    if type(window) is not str or window not in WINDOWS:
        return unknown()
    proc = None
    completed = False
    started = time.monotonic()
    try:
        argv = _fixed_argv(window)
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            cwd=str(ROOT), start_new_session=True, close_fds=True,
            env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"})
        if proc.stdout is None:
            raise ValueError("no stdout")
        os.set_blocking(proc.stdout.fileno(), False)
        chunks = bytearray()
        deadline = started + MAX_CHILD_SECONDS
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            eof = False
            while not eof:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(argv, MAX_CHILD_SECONDS)
                for key, _ in selector.select(min(remaining, 0.2)):
                    part = os.read(key.fileobj.fileno(), READ_BLOCK_BYTES)
                    if part:
                        if len(chunks) + len(part) > MAX_STDOUT_BYTES:
                            raise ValueError("oversized stdout")
                        chunks.extend(part)
                    else:
                        eof = True
                        selector.unregister(key.fileobj)
        remaining = deadline - time.monotonic()
        if remaining <= 0 or proc.wait(timeout=remaining) != 0:
            raise ValueError("source failure or deadline")
        result = _project(bytes(chunks), window)
        completed = True
        return result
    except (OSError, ValueError, TypeError, UnicodeError,
            subprocess.SubprocessError):
        return unknown()
    finally:
        if proc is not None:
            if not completed:
                _terminate_group(proc)
            if proc.stdout is not None:
                proc.stdout.close()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", action="store_true", required=True)
    args = parser.parse_args()
    if args.inspect:
        print(json.dumps({"mode": "INSPECT_ONLY_NO_NETWORK",
                          "source": "FIXED_B2_CLI_SUPERVISOR_NOT_INVOKED",
                          "allowed_windows": WINDOWS,
                          "max_child_seconds": MAX_CHILD_SECONDS,
                          "max_stdout_bytes": MAX_STDOUT_BYTES,
                          "auto_start": False, "http_endpoint": False,
                          "deployment_gate": "HOLD"}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
