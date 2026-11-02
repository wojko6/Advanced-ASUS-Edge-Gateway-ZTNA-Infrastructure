#!/usr/bin/env python3
"""C.64.2: explicit, unprivileged local listener preflight (NO HTTP REQUESTS).

Offline self-tests use injected fake /proc and unit data. The *separate*
--inspect-local-listener command reads only /proc/net/tcp{,6}, metadata of
the victoriaMetrics.service systemd unit, and the service MainPID's
/proc/<pid>/fd symlink targets. It opens no TCP/HTTP connection, writes files,
contacts the router, invokes a model, or authorizes a production read.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True

SCHEMA = 'local-ai-agent.v0.21.c64.2.local-listener-preflight.v1'
SERVICE = 'victoriametrics.service'
PORT = 8428
TARGET_HEX = f'{PORT:04X}'
MAX_PROC_BYTES = 1048576
MAX_FDS = 4096
MAX_SUMMARY_BYTES = 2300
SYSCTL_TIMEOUT = 3
TCP_TABLES = ('/proc/net/tcp', '/proc/net/tcp6')
SOCKET_RE = re.compile(r'socket:\[([0-9]{1,20})\]\Z')


class Hold(Exception):
    """Fixed, non-sensitive refusal code only."""


def address_from_hex(value, family):
    """Decode Linux /proc/net/tcp little-endian addresses, without sockets."""
    if family == 4:
        if len(value) != 8:
            raise Hold('PROC_ADDRESS_INVALID')
        try:
            data = bytes.fromhex(value)[::-1]
            return ipaddress.IPv4Address(data)
        except ValueError as exc:
            raise Hold('PROC_ADDRESS_INVALID') from exc
    if family == 6:
        if len(value) != 32:
            raise Hold('PROC_ADDRESS_INVALID')
        try:
            data = bytes.fromhex(value)
            data = b''.join(data[i:i+4][::-1] for i in range(0, 16, 4))
            return ipaddress.IPv6Address(data)
        except ValueError as exc:
            raise Hold('PROC_ADDRESS_INVALID') from exc
    raise Hold('PROC_FAMILY_INVALID')


def parse_proc_table(contents, family):
    """Only report LISTEN sockets for 8428; never copy source addresses out."""
    if type(contents) is not str or len(contents.encode('utf-8')) > MAX_PROC_BYTES:
        raise Hold('PROC_TABLE_INVALID')
    lines = contents.splitlines()
    if not lines or 'local_address' not in lines[0] or 'st' not in lines[0].split():
        raise Hold('PROC_HEADER_INVALID')
    results = []
    for line in lines[1:]:
        if not line.strip():
            continue  # A trailing empty /proc line is not a TCP socket row.
        parts = line.split()
        if len(parts) < 10:
            raise Hold('PROC_ROW_INVALID')
        try:
            address_hex, port_hex = parts[1].split(':', 1)
        except ValueError as exc:
            raise Hold('PROC_ROW_INVALID') from exc
        if port_hex.upper() != TARGET_HEX or parts[3] != '0A':
            continue
        ip = address_from_hex(address_hex, family)
        inode = parts[9]
        if not inode.isdecimal() or len(inode) > 20 or int(inode) < 1:
            raise Hold('PROC_INODE_INVALID')
        bind = ('LOOPBACK' if ip.is_loopback else
                'WILDCARD' if ip.is_unspecified else 'NONLOOPBACK')
        results.append((family, bind, inode))
        if len(results) > 32:
            raise Hold('TOO_MANY_LISTENERS')
    return results


def summarize_bindings(ipv4_text, ipv6_text):
    records = parse_proc_table(ipv4_text, 4) + parse_proc_table(ipv6_text, 6)
    if len(records) > 32:
        raise Hold('TOO_MANY_LISTENERS')
    return {
        'count': len(records),
        'loopback_ipv4_count': sum(f == 4 and b == 'LOOPBACK' for f, b, _ in records),
        'loopback_ipv6_count': sum(f == 6 and b == 'LOOPBACK' for f, b, _ in records),
        'wildcard_count': sum(b == 'WILDCARD' for _, b, _ in records),
        'nonloopback_count': sum(b == 'NONLOOPBACK' for _, b, _ in records),
        'socket_inodes': frozenset(inode for _, _, inode in records),
    }


def parse_unit_properties(raw):
    if type(raw) is not str or len(raw) > 1000:
        raise Hold('SYSTEMD_OUTPUT_INVALID')
    values = {}
    for line in raw.splitlines():
        if '=' not in line:
            raise Hold('SYSTEMD_OUTPUT_INVALID')
        key, value = line.split('=', 1)
        if key not in ('ActiveState', 'MainPID') or key in values:
            raise Hold('SYSTEMD_OUTPUT_INVALID')
        values[key] = value
    if set(values) != {'ActiveState', 'MainPID'}:
        raise Hold('SYSTEMD_OUTPUT_INVALID')
    state = values['ActiveState']
    if state not in ('active', 'inactive', 'failed', 'activating',
                     'deactivating', 'reloading'):
        raise Hold('SYSTEMD_STATE_INVALID')
    pid = values['MainPID']
    if not re.fullmatch(r'(?:0|[1-9][0-9]{0,9})', pid) or int(pid) >= 2**31:
        raise Hold('SYSTEMD_PID_INVALID')
    return state, int(pid)


def read_table(path):
    if path not in TCP_TABLES:
        raise Hold('UNAPPROVED_PROC_PATH')
    try:
        with open(path, 'rb') as fp:
            raw = fp.read(MAX_PROC_BYTES + 1)
        if len(raw) > MAX_PROC_BYTES:
            raise Hold('PROC_TABLE_TOO_LARGE')
        return raw.decode('ascii')
    except (OSError, UnicodeError) as exc:
        raise Hold('PROC_READ_UNAVAILABLE') from exc


def query_unit():
    """Fixed argv; systemd local IPC only, no HTTP, no shell, no sudo."""
    try:
        result = subprocess.run(
            ['systemctl', '--no-pager', 'show', '--property=MainPID',
             '--property=ActiveState', SERVICE],
            capture_output=True, text=True, timeout=SYSCTL_TIMEOUT,
            check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Hold('SYSTEMD_READ_UNAVAILABLE') from exc
    if result.returncode != 0:
        raise Hold('SYSTEMD_READ_UNAVAILABLE')
    return parse_unit_properties(result.stdout)


def check_main_pid_fds(pid, expected_inodes):
    """Positive match only if readable MainPID fd points at target inode."""
    if type(pid) is not int or not 1 <= pid < 2**31:
        return 'UNAVAILABLE'
    if type(expected_inodes) is not frozenset or not expected_inodes:
        return 'UNAVAILABLE'
    directory = f'/proc/{pid}/fd'
    try:
        fds = os.listdir(directory)
    except OSError:
        return 'UNAVAILABLE'
    if len(fds) > MAX_FDS:
        return 'UNAVAILABLE'
    incomplete = False
    for fd in fds:
        if not re.fullmatch(r'[0-9]{1,10}', fd):
            incomplete = True
            continue
        try:
            destination = os.readlink(f'{directory}/{fd}')
        except OSError:
            incomplete = True
            continue
        m = SOCKET_RE.fullmatch(destination)
        if m and m.group(1) in expected_inodes:
            return 'YES'
    return 'UNAVAILABLE' if incomplete else 'NO'


def evaluate(ipv4_text, ipv6_text, state, pid, owner_lookup):
    bound = summarize_bindings(ipv4_text, ipv6_text)
    if type(state) is not str or state not in ('active', 'inactive', 'failed',
                                               'activating', 'deactivating', 'reloading'):
        raise Hold('UNIT_STATE_INVALID')
    if type(pid) is not int or not 0 <= pid < 2**31:
        raise Hold('UNIT_PID_INVALID')
    matched = (owner_lookup(pid, bound['socket_inodes'])
               if pid and bound['count'] else 'UNAVAILABLE')
    if matched not in ('YES', 'NO', 'UNAVAILABLE'):
        raise Hold('OWNER_LOOKUP_INVALID')
    if bound['wildcard_count'] or bound['nonloopback_count']:
        outcome = 'HOLD_NONLOCAL_BIND_PRESENT'
    elif not bound['count']:
        outcome = 'HOLD_NO_LISTENER'
    elif state != 'active' or not pid:
        outcome = 'HOLD_SERVICE_NOT_ACTIVE'
    elif matched == 'YES':
        outcome = 'OBSERVED_LOOPBACK_MAINPID_SOCKET_MANUAL_REVIEW_ONLY'
    else:
        outcome = 'HOLD_LISTENER_OWNERSHIP_UNCONFIRMED'
    summary = {
        'schema': SCHEMA,
        'mode': 'EXPLICIT_LOCAL_PROCESS_METADATA_INSPECTION_NO_HTTP',
        'service_name': SERVICE,
        'target_port': PORT,
        'tcp_listeners_count': bound['count'],
        'loopback_ipv4_count': bound['loopback_ipv4_count'],
        'loopback_ipv6_count': bound['loopback_ipv6_count'],
        'wildcard_count': bound['wildcard_count'],
        'nonloopback_count': bound['nonloopback_count'],
        'systemd_active': state == 'active',
        'systemd_main_pid_present': pid > 0,
        'mainpid_socket_inode_match': matched,
        'preflight_result': outcome,
        'process_identity_cryptographically_attested': False,
        'localhost_service_authentication_established': False,
        'socket_was_opened_by_agent': False,
        'http_requests': 0,
        'model_requests': 0,
        'remediation_authorized': False,
        'model_action_authority': 'NONE',
        'deployment_gate': 'HOLD',
        'next_step': 'MANUAL_REVIEW_ONLY_NO_LIVE_QUERY_AUTHORIZED',
    }
    if len(json.dumps(summary, sort_keys=True).encode('ascii')) > MAX_SUMMARY_BYTES:
        raise Hold('SUMMARY_TOO_LARGE')
    return summary


def inspect_local():
    return evaluate(read_table(TCP_TABLES[0]), read_table(TCP_TABLES[1]),
                    *query_unit(), owner_lookup=check_main_pid_fds)


HEADER = '  sl local_address rem_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode'
def table(rows=()):
    return HEADER + '\n' + '\n'.join(rows) + '\n'

def mock_row(addr, port=TARGET_HEX, inode='12345', state='0A'):
    return (' 0: ' + addr + ':' + port + ' 00000000:0000 ' + state +
            ' 00000000:00000000 00:00000000 00000000 1000 0 ' + inode)


class Tests(unittest.TestCase):
    def local4(self):
        return table([mock_row('0100007F')])

    def local6(self):
        return table([mock_row('00000000000000000000000001000000')])

    def sample(self, v4=None, v6=None, state='active', pid=123,
               ownership='YES'):
        return evaluate(self.local4() if v4 is None else v4,
                        table() if v6 is None else v6,
                        state, pid, lambda *_: ownership)

    def holds(self, f, reason):
        with self.assertRaisesRegex(Hold, '^' + re.escape(reason) + '$'):
            f()

    def test_01_ipv4_loopback(self):
        self.assertEqual(str(address_from_hex('0100007F', 4)), '127.0.0.1')

    def test_02_ipv6_loopback(self):
        self.assertEqual(str(address_from_hex(
            '00000000000000000000000001000000', 6)), '::1')

    def test_03_ipv4_wildcard(self):
        self.assertTrue(address_from_hex('00000000', 4).is_unspecified)

    def test_04_ipv6_wildcard(self):
        self.assertTrue(address_from_hex('0'*32, 6).is_unspecified)

    def test_05_ipv4_positive_owner(self):
        self.assertEqual(self.sample()['preflight_result'],
                         'OBSERVED_LOOPBACK_MAINPID_SOCKET_MANUAL_REVIEW_ONLY')

    def test_06_ipv6_positive_owner(self):
        self.assertEqual(self.sample(v4=table(), v6=self.local6())['loopback_ipv6_count'], 1)

    def test_07_no_listener(self):
        self.assertEqual(self.sample(v4=table())['preflight_result'], 'HOLD_NO_LISTENER')

    def test_08_wildcard_hold(self):
        self.assertEqual(self.sample(v4=table([mock_row('00000000')]))['preflight_result'],
                         'HOLD_NONLOCAL_BIND_PRESENT')

    def test_09_nonlocal_hold(self):
        self.assertEqual(self.sample(v4=table([mock_row('0200A8C0')]))['preflight_result'],
                         'HOLD_NONLOCAL_BIND_PRESENT')

    def test_10_both_loopback_and_wildcard_hold(self):
        v4 = table([mock_row('0100007F'), mock_row('00000000', inode='12346')])
        self.assertEqual(self.sample(v4=v4)['preflight_result'], 'HOLD_NONLOCAL_BIND_PRESENT')

    def test_11_service_inactive_hold(self):
        self.assertEqual(self.sample(state='inactive')['preflight_result'], 'HOLD_SERVICE_NOT_ACTIVE')

    def test_12_no_mainpid_hold(self):
        self.assertEqual(self.sample(pid=0)['preflight_result'], 'HOLD_SERVICE_NOT_ACTIVE')

    def test_13_unreadable_fd_hold(self):
        self.assertEqual(self.sample(ownership='UNAVAILABLE')['preflight_result'],
                         'HOLD_LISTENER_OWNERSHIP_UNCONFIRMED')

    def test_14_wrong_owner_hold(self):
        self.assertEqual(self.sample(ownership='NO')['preflight_result'],
                         'HOLD_LISTENER_OWNERSHIP_UNCONFIRMED')

    def test_15_parse_unit_active(self):
        self.assertEqual(parse_unit_properties('MainPID=51\nActiveState=active\n'),
                         ('active', 51))

    def test_16_missing_unit_key_hold(self):
        self.holds(lambda: parse_unit_properties('MainPID=51\n'),
                   'SYSTEMD_OUTPUT_INVALID')

    def test_17_duplicate_unit_key_hold(self):
        self.holds(lambda: parse_unit_properties('MainPID=51\nMainPID=52\nActiveState=active'),
                   'SYSTEMD_OUTPUT_INVALID')

    def test_18_unexpected_unit_field_hold(self):
        self.holds(lambda: parse_unit_properties('MainPID=51\nActiveState=active\nExecStart=private'),
                   'SYSTEMD_OUTPUT_INVALID')

    def test_19_bad_pid_hold(self):
        self.holds(lambda: parse_unit_properties('MainPID=-1\nActiveState=active'),
                   'SYSTEMD_PID_INVALID')

    def test_20_bad_proc_header_hold(self):
        self.holds(lambda: parse_proc_table('bad\n', 4), 'PROC_HEADER_INVALID')

    def test_21_bad_proc_inode_hold(self):
        self.holds(lambda: parse_proc_table(table([mock_row('0100007F',inode='0')]), 4),
                   'PROC_INODE_INVALID')

    def test_22_invalid_ip_hold(self):
        self.holds(lambda: parse_proc_table(table([mock_row('ZZ00007F')]), 4),
                   'PROC_ADDRESS_INVALID')

    def test_23_non_listening_socket_ignored(self):
        x = table([mock_row('0100007F', state='01')])
        self.assertEqual(summarize_bindings(x,table())['count'], 0)

    def test_24_non_target_port_ignored(self):
        x = table([mock_row('0100007F', port='0016')])
        self.assertEqual(summarize_bindings(x,table())['count'], 0)

    def test_25_fd_matching_inode(self):
        with patch('os.listdir', return_value=['1','2']), patch('os.readlink',
                 side_effect=['pipe:[12]', 'socket:[12345]']):
            self.assertEqual(check_main_pid_fds(77, frozenset({'12345'})), 'YES')

    def test_26_fd_no_match(self):
        with patch('os.listdir', return_value=['1']), patch('os.readlink',
                 return_value='socket:[888]'):
            self.assertEqual(check_main_pid_fds(77, frozenset({'12345'})), 'NO')

    def test_27_fd_unavailable(self):
        with patch('os.listdir', side_effect=PermissionError):
            self.assertEqual(check_main_pid_fds(77, frozenset({'12345'})), 'UNAVAILABLE')

    def test_28_fd_too_many(self):
        with patch('os.listdir', return_value=['1']*(MAX_FDS+1)):
            self.assertEqual(check_main_pid_fds(77, frozenset({'12345'})), 'UNAVAILABLE')

    def test_29_fd_race(self):
        with patch('os.listdir', return_value=['1']), patch('os.readlink',
                 side_effect=FileNotFoundError):
            self.assertEqual(check_main_pid_fds(77, frozenset({'12345'})), 'UNAVAILABLE')

    def test_30_no_private_identity_in_output(self):
        result = json.dumps(self.sample())
        self.assertNotIn('12345', result)
        self.assertNotIn('MainPID=123', result)
        self.assertNotIn('192.168.', result)

    def test_31_no_http_or_model_authority(self):
        r = self.sample()
        self.assertEqual(r['http_requests'], 0)
        self.assertEqual(r['model_requests'], 0)
        self.assertFalse(r['remediation_authorized'])
        self.assertEqual(r['model_action_authority'], 'NONE')
        self.assertEqual(r['deployment_gate'], 'HOLD')

    def test_32_not_attested(self):
        r = self.sample()
        self.assertFalse(r['process_identity_cryptographically_attested'])
        self.assertFalse(r['localhost_service_authentication_established'])

    def test_33_reproducible_mock(self):
        self.assertEqual(self.sample(), self.sample())

    def test_34_no_real_host_reads_during_evaluation(self):
        with patch('builtins.open',side_effect=AssertionError('HOST_READ')), \
             patch('subprocess.run',side_effect=AssertionError('COMMAND')):
            self.assertEqual(self.sample()['http_requests'], 0)

    def test_35_evaluation_refuses_untrusted_owner_state(self):
        self.holds(lambda: self.sample(ownership='TRUSTED'), 'OWNER_LOOKUP_INVALID')

    def test_36_no_network_requests_from_inspection_injected(self):
        with patch('socket.socket',side_effect=AssertionError('SOCKET')), \
             patch('socket.create_connection',side_effect=AssertionError('SOCKET')), \
             patch('builtins.open',side_effect=AssertionError('HOST_READ')):
            self.assertEqual(self.sample()['preflight_result'],
                             'OBSERVED_LOOPBACK_MAINPID_SOCKET_MANUAL_REVIEW_ONLY')

    def test_37_unapproved_read_path(self):
        self.holds(lambda: read_table('/etc/shadow'), 'UNAPPROVED_PROC_PATH')

    def test_38_invalid_socket_family(self):
        self.holds(lambda: address_from_hex('0100007F', 5), 'PROC_FAMILY_INVALID')

    def test_39_excessive_input_hold(self):
        self.holds(lambda: parse_proc_table('X'*(MAX_PROC_BYTES+1),4),
                   'PROC_TABLE_INVALID')

    def test_40_socket_link_matching_is_strict(self):
        with patch('os.listdir',return_value=['1']), patch('os.readlink',
                 return_value='file:socket:[12345]'):
            self.assertEqual(check_main_pid_fds(77,frozenset({'12345'})), 'NO')

    def test_41_empty_proc_table_and_trailing_blank_line(self):
        self.assertEqual(summarize_bindings(table(), table())['count'], 0)
        self.assertEqual(summarize_bindings(self.local4(), table())['count'], 1)

    def test_42_inspect_local_uses_bounded_metadata_only(self):
        with patch(__name__ + '.read_table', side_effect=[self.local4(), table()]) as read, \
             patch(__name__ + '.query_unit', return_value=('active', 123)) as unit, \
             patch(__name__ + '.check_main_pid_fds', return_value='YES') as fds, \
             patch('socket.socket', side_effect=AssertionError('TCP_SOCKET')), \
             patch('subprocess.Popen', side_effect=AssertionError('PROCESS')):
            result = inspect_local()
        self.assertEqual(result['http_requests'], 0)
        self.assertEqual(result['preflight_result'],
                         'OBSERVED_LOOPBACK_MAINPID_SOCKET_MANUAL_REVIEW_ONLY')
        self.assertEqual(read.call_count, 2)
        unit.assert_called_once()
        fds.assert_called_once()

    def test_43_query_unit_uses_fixed_non_shell_argv(self):
        with patch('subprocess.run') as runner:
            runner.return_value.returncode = 0
            runner.return_value.stdout = 'MainPID=51\\nActiveState=active\\n'
            result = query_unit()
            runner.assert_called_once_with(
                ['systemctl', '--no-pager', 'show', '--property=MainPID',
                 '--property=ActiveState', SERVICE],
                capture_output=True, text=True, timeout=SYSCTL_TIMEOUT,
                check=False)
        self.assertEqual(result, ('active', 51))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--self-test', action='store_true')
    modes.add_argument('--inspect-local-listener', action='store_true',
                       help='Explicit /proc + systemctl metadata reads; NO HTTP, sudo or model')
    args = parser.parse_args(argv)
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        print('C642_TESTS=' + str(result.testsRun) + ' STATUS='
              + ('PASS_OFFLINE' if result.wasSuccessful() else 'HOLD_TEST_FAILED'))
        return 0 if result.wasSuccessful() else 1
    try:
        result = inspect_local()
        print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True))
        return 0
    except Hold as exc:
        print('C642_RESULT=HOLD_' + str(exc), file=sys.stderr)
        print('HTTP_REQUESTS=0 MODEL_REQUESTS=0 DEPLOYMENT_GATE=HOLD',
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
