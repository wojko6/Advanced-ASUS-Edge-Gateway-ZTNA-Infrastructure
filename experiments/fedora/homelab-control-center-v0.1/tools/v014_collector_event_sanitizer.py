#!/usr/bin/env python3
"""HCC V0.14 optional offline sanitizer. JSON journal stdin -> safe NDJSON stdout.

No network, subprocess, router access, state changes or raw journal content output.
Only operator-supplied unit-scoped journal; no direct systemd journal access.
"""
import argparse
from datetime import datetime, timezone
import json
import re
import sys

MAX_BYTES = 4 * 1024 * 1024
MAX_ROWS = 5000
MAX_MESSAGE = 4096
BOOT_RE = re.compile(r'[0-9a-f]{32}\Z')
EXIT_RE = re.compile(r'^dns-guard-monitoring\.service: Main process exited, code=exited, status=(\d+)(?:/|\b)')
ALLOWED = {'COLLECTOR_EXIT_255', 'SSH_TIMEOUT', 'SSH_AUTH_FAILURE', 'HTTP_IMPORT_TIMEOUT'}

class InputError(ValueError):
    pass


def unique_json(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise InputError('DUPLICATE_JSON_KEY')
        obj[k] = v
    return obj


def sanitize(blob):
    if not isinstance(blob, bytes) or len(blob) > MAX_BYTES:
        raise InputError('INPUT_SIZE_LIMIT')
    lines = [line for line in blob.splitlines() if line.strip()]
    if len(lines) > MAX_ROWS:
        raise InputError('ROW_LIMIT')
    result, seen = [], set()
    last_us = -1
    for line in lines:
        try:
            obj = json.loads(line.decode('utf-8'), object_pairs_hook=unique_json,
                             parse_constant=lambda _: (_ for _ in ()).throw(InputError('NONFINITE')))
        except (UnicodeError, ValueError) as exc:
            raise InputError('INVALID_JOURNAL_JSON') from exc
        if type(obj) is not dict:
            raise InputError('INVALID_ROW')
        stamp, boot, msg = obj.get('__REALTIME_TIMESTAMP'), obj.get('_BOOT_ID'), obj.get('MESSAGE')
        if (type(stamp) is not str or not stamp.isdecimal() or not 15 <= len(stamp) <= 17
                or type(boot) is not str or not BOOT_RE.fullmatch(boot)
                or type(msg) is not str or len(msg) > MAX_MESSAGE):
            raise InputError('INVALID_JOURNAL_FIELDS')
        us = int(stamp)
        if us < last_us:
            raise InputError('OUT_OF_ORDER')
        last_us = us
        kind = None
        m = EXIT_RE.match(msg)
        low = msg.lower()
        if m and m.group(1) == '255':
            kind = 'COLLECTOR_EXIT_255'
        elif low.startswith('ssh:') and ('timed out' in low or 'timeout' in low):
            kind = 'SSH_TIMEOUT'
        elif low.startswith('ssh:') and 'permission denied' in low:
            kind = 'SSH_AUTH_FAILURE'
        elif low.startswith('curl:') and ('timed out' in low or 'timeout' in low):
            kind = 'HTTP_IMPORT_TIMEOUT'
        if kind is None:
            continue
        key = (boot, us, kind)
        if key in seen:
            continue
        seen.add(key)
        timestamp = datetime.fromtimestamp(us / 1_000_000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        result.append({'time': timestamp, 'kind': kind, 'component': 'dns-guard-collector', 'source': 'fedora-user-journal'})
    return result


def self_test():
    boot = 'a' * 32
    def row(us, msg):
        return json.dumps({'__REALTIME_TIMESTAMP': str(us), '_BOOT_ID': boot, 'MESSAGE': msg}).encode()
    t = 1793260000000000
    blob = b'\n'.join([
        row(t, 'dns-guard-monitoring.service: Main process exited, code=exited, status=255/EXCEPTION'),
        row(t, 'dns-guard-monitoring.service: Failed with result exit-code.'),
        row(t+1, 'ssh: connect to host private.example port 1122: Connection timed out'),
        row(t+2, 'curl: (28) Operation timed out with 0 bytes received'),
    ])
    safe = sanitize(blob)
    assert [r['kind'] for r in safe] == ['COLLECTOR_EXIT_255', 'SSH_TIMEOUT', 'HTTP_IMPORT_TIMEOUT']
    assert 'private.example' not in json.dumps(safe)
    assert all(set(r) == {'time','kind','component','source'} and r['kind'] in ALLOWED for r in safe)
    assert sanitize(blob + b'\n' + row(t+2, 'curl: (28) Operation timed out')) == safe
    for bad in [b'{bad}', b'"text"', b'{"MESSAGE":"data"}', b'\xff', b'{' + b'x' * (MAX_BYTES+1)]:
        try:
            sanitize(bad)
        except InputError:
            pass
        else:
            raise AssertionError('INVALID_NOT_REJECTED')
    try:
        sanitize(row(t+1, 'ssh: timeout') + b'\n' + row(t, 'ssh: timeout'))
    except InputError:
        pass
    else:
        raise AssertionError('REORDERED_NOT_REJECTED')
    print('V014_SANITIZER_SELFTEST=PASS')
    print('NO_NETWORK_NO_SUBPROCESS_NO_FILES_WRITTEN=YES')
    print('ASUS_CONTACT=NO')
    print('PRODUCTION_CHANGES=NO')
    print('DEPLOYMENT_GATE=HOLD')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--self-test', action='store_true')
    mode.add_argument('--sanitize-stdin', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    try:
        data = sys.stdin.buffer.read(MAX_BYTES + 1)
        output = sanitize(data)
    except (InputError, OverflowError, OSError):
        print('V014_RESULT=REJECTED_INPUT', file=sys.stderr)
        return 2
    for row in output:
        print(json.dumps(row, sort_keys=True, separators=(',', ':')))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())