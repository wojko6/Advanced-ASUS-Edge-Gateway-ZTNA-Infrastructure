#!/usr/bin/env python3
"""HCC V0.14.5J: one HTTP exchange with an owned ephemeral loopback fixture.

No real Loki/Alloy/ASUS, journal, persistent state, ACK or progress change.
--self-test is memory-only. --lab starts its own 127.0.0.1:0 fixture and one
bounded Python client worker. No URL/port/input/credential CLI options.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import hashlib
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import socket
from socketserver import TCPServer
import subprocess
import sys
import threading

import v0145a_segment_spool as spool
import v0145d_event_identity as identity
import v0145h_loki_request as encoding
import v0145i_batch_plan as planning

CLIENT_SECONDS = 2
REAP_SECONDS = 1
MAX_RESPONSE_BYTES = 512
MAX_REPORT_BYTES = 1024
MAX_JOB_BYTES = 128 * 1024
TOKEN_RE = re.compile(r'\A[0-9a-f]{32}\Z', re.ASCII)
HASH_RE = re.compile(r'\A[0-9a-f]{64}\Z', re.ASCII)


@dataclass(frozen=True)
class Reply:
    status: int = 204
    body: bytes = b''
    mode: str = 'normal'
    headers: tuple[tuple[str, str], ...] = ()


class _Server(HTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        # HTTPServer's default server_bind calls getfqdn. This owned numeric
        # listener needs no reverse lookup or host-derived server name.
        TCPServer.server_bind(self)
        self.server_name = 'hcc-loopback-fixture'
        self.server_port = self.server_address[1]

    def handle_error(self, request, client_address):
        self.owner.server_error = True  # No raw traceback/body logging.


class LoopbackFixture:
    """Trusted test peer, not an authentication boundary against local users."""
    def __init__(self, request, reply=Reply()):
        if (type(request) is not encoding.PushRequest or type(request.body) is not bytes or
                not 0 < len(request.body) <= encoding.MAX_BODY_BYTES or
                hashlib.sha256(request.body).hexdigest() != request.sha256):
            raise spool.Hold('FIXTURE_REQUEST_SHAPE')
        if (type(reply) is not Reply or type(reply.status) is not int or not 200 <= reply.status <= 599 or
                type(reply.body) is not bytes or len(reply.body) > MAX_RESPONSE_BYTES + 1 or
                type(reply.mode) is not str or reply.mode not in ('normal', 'stall', 'disconnect', 'malformed') or
                type(reply.headers) is not tuple or len(reply.headers) > 4):
            raise spool.Hold('FIXTURE_REPLY_SHAPE')
        for pair in reply.headers:
            if (type(pair) is not tuple or len(pair) != 2 or
                    any(type(value) is not str or not value.isascii() or '\r' in value or '\n' in value
                        or len(value) > 64 for value in pair) or
                    pair[0] not in ('Content-Length', 'Transfer-Encoding', 'Location')):
                raise spool.Hold('FIXTURE_REPLY_HEADERS')
        self.request, self.reply = request, reply
        self._lock = threading.Lock()
        self._release = threading.Event()
        self._used = self._attempted = self.active = self.server_error = False
        self.seen = []
        self.total_posts = 0
        self.server = self.thread = self.connection = None

    def __enter__(self):
        if self._used:
            raise spool.Hold('FIXTURE_SINGLE_USE')
        self._used = True
        self.token = os.urandom(16).hex()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.0'

            def setup(self):
                super().setup()
                self.connection.settimeout(1)
                with owner._lock:
                    owner.connection = self.connection

            def log_message(self, *args):
                pass

            def do_POST(self):
                with owner._lock:
                    owner.total_posts += 1
                lengths = self.headers.get_all('Content-Length', [])
                valid = (self.path == encoding.PATH and
                         self.headers.get('Content-Type') == encoding.CONTENT_TYPE and
                         self.headers.get_all('X-HCC-Lab-Capability', []) == [owner.token] and
                         not self.headers.get_all('Transfer-Encoding', []) and len(lengths) == 1 and
                         lengths[0].isascii() and lengths[0].isdecimal() and
                         0 < int(lengths[0]) <= encoding.MAX_BODY_BYTES)
                if valid:
                    body = self.rfile.read(int(lengths[0]))
                    valid = hmac.compare_digest(body, owner.request.body)
                if not valid:
                    self.send_response(403)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                with owner._lock:
                    if owner.seen:
                        self.send_error(409)
                        return
                    owner.seen.append(body)
                if owner.reply.mode == 'stall':
                    owner._release.wait(CLIENT_SECONDS + REAP_SECONDS + 1)
                    return
                if owner.reply.mode == 'disconnect':
                    return
                if owner.reply.mode == 'malformed':
                    self.connection.sendall(b'NOT-HTTP\r\n\r\n')
                    return
                self.send_response(owner.reply.status)
                headers = list(owner.reply.headers)
                if not any(name == 'Content-Length' for name, _ in headers) and (owner.reply.body or owner.reply.status != 204):
                    headers.append(('Content-Length', str(len(owner.reply.body))))
                for name, value in headers:
                    self.send_header(name, value)
                self.send_header('Connection', 'close')
                self.end_headers()
                if owner.reply.body:
                    self.wfile.write(owner.reply.body)

        self.server = _Server(('127.0.0.1', 0), Handler)
        self.server.owner = self
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': 0.05}, daemon=True,
                                       name='hcc-v0145j-fixture')
        try:
            self.thread.start()
        except BaseException:
            self.server.server_close()
            raise
        self.active = True
        return self

    def __exit__(self, *args):
        self.active = False
        self._release.set()
        with self._lock:
            connection = self.connection
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        try:
            self.server.shutdown()
        finally:
            self.server.server_close()
            self.thread.join(timeout=REAP_SECONDS)
        if self.thread.is_alive():
            raise spool.Hold('FIXTURE_THREAD_NOT_STOPPED')


def _decode_job(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_JOB_BYTES:
        raise spool.Hold('WORKER_JOB_BYTES')
    try:
        obj = json.loads(raw.decode('ascii'), object_pairs_hook=spool.no_duplicates)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise spool.Hold('WORKER_JOB_JSON') from exc
    if (type(obj) is not dict or set(obj) != {'port', 'capability', 'body', 'sha256'} or
            type(obj['port']) is not int or not 1024 <= obj['port'] <= 65535 or
            type(obj['capability']) is not str or not TOKEN_RE.fullmatch(obj['capability']) or
            type(obj['sha256']) is not str or not HASH_RE.fullmatch(obj['sha256']) or
            type(obj['body']) is not str or len(obj['body']) > MAX_JOB_BYTES):
        raise spool.Hold('WORKER_JOB_SCHEMA')
    try:
        body = base64.b64decode(obj['body'], validate=True)
    except ValueError as exc:
        raise spool.Hold('WORKER_JOB_BASE64') from exc
    if not 0 < len(body) <= encoding.MAX_BODY_BYTES or hashlib.sha256(body).hexdigest() != obj['sha256']:
        raise spool.Hold('WORKER_JOB_BODY')
    return obj['port'], obj['capability'], body


def _worker():
    """Private fixed-host worker; parent deadline covers the complete exchange."""
    connection = None
    try:
        port, capability, body = _decode_job(sys.stdin.buffer.read(MAX_JOB_BYTES + 1))
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=CLIENT_SECONDS)
        connection.request('POST', encoding.PATH, body=body,
                           headers={'Content-Type': encoding.CONTENT_TYPE,
                                    'X-HCC-Lab-Capability': capability, 'Connection': 'close'})
        response = connection.getresponse()
        headers = response.getheaders()
        lengths = response.headers.get_all('Content-Length', [])
        framing = (len(headers) <= 16 and sum(len(name) + len(value) for name, value in headers) <= 4096 and
                   not response.headers.get_all('Transfer-Encoding', []) and len(lengths) <= 1 and
                   (not lengths or lengths == ['0']))
        payload = response.read(MAX_RESPONSE_BYTES + 1)
        report = {'status': response.status, 'body_bytes': len(payload), 'framing': bool(framing)}
    except Exception as exc:
        report = {'error': type(exc).__name__}
    finally:
        if connection is not None:
            connection.close()
    print(identity.canonical(report).decode('ascii'))
    return 0


def validate_report(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_REPORT_BYTES:
        raise spool.Hold('CLIENT_REPORT_BYTES')
    try:
        obj = json.loads(raw.decode('ascii'), object_pairs_hook=spool.no_duplicates)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise spool.Hold('CLIENT_REPORT_JSON') from exc
    if (type(obj) is not dict or set(obj) != {'status', 'body_bytes', 'framing'} or
            type(obj['status']) is not int or type(obj['body_bytes']) is not int or type(obj['framing']) is not bool):
        raise spool.Hold('CLIENT_REPORT_SCHEMA')
    # A deliberately narrow fixture result, never a real Loki receipt.
    if obj != {'status': 204, 'body_bytes': 0, 'framing': True}:
        raise spool.Hold('CLIENT_RESPONSE_REJECTED')


def _stop_worker(process):
    try:
        process.kill()
    except ProcessLookupError:
        pass
    try:
        process.communicate(timeout=REAP_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise spool.Hold('CLIENT_REAP_TIMEOUT') from exc


def _run_worker(job):
    program = 'import v0145j_loopback_exchange as j; raise SystemExit(j._worker())'
    process = subprocess.Popen([sys.executable, '-B', '-c', program],
                               cwd=str(Path(__file__).resolve().parent), close_fds=True,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        output, errors = process.communicate(identity.canonical(job), timeout=CLIENT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        _stop_worker(process)
        raise spool.Hold('CLIENT_DEADLINE_EXPIRED') from exc
    except BaseException:
        _stop_worker(process)
        raise
    if process.returncode != 0 or errors:
        raise spool.Hold('CLIENT_WORKER_FAILURE')
    validate_report(output)


def send_one(plan, raw_source, raw_ack, fixture, *, index=0):
    """One owned-fixture exchange; no retries, real endpoint or progress change."""
    planning.require_current(plan, raw_source, raw_ack)
    if type(index) is not int or not 0 <= index < len(plan.requests):
        raise spool.Hold('REQUEST_INDEX')
    request = plan.requests[index]
    if type(fixture) is not LoopbackFixture or not fixture.active or fixture.request != request:
        raise spool.Hold('ACTIVE_MATCHING_FIXTURE_REQUIRED')
    with fixture._lock:
        if fixture._attempted:
            raise spool.Hold('FIXTURE_ATTEMPT_ALREADY_CONSUMED')
        fixture._attempted = True
    host, port = fixture.server.socket.getsockname()
    if host != '127.0.0.1' or not fixture.thread.is_alive():
        raise spool.Hold('OWNED_LOOPBACK_LISTENER_REQUIRED')
    job = {'port': port, 'capability': fixture.token, 'sha256': request.sha256,
           'body': base64.b64encode(request.body).decode('ascii')}
    _run_worker(job)
    with fixture._lock:
        if (fixture.reply.status != 204 or fixture.reply.body != b'' or fixture.reply.mode != 'normal' or
                fixture.server_error or fixture.total_posts != 1 or fixture.seen != [request.body]):
            raise spool.Hold('FIXTURE_OBSERVATION_MISMATCH')
    return 'PASS_OWNED_FIXTURE_EXCHANGE_ONLY'


def self_test():
    validate_report(b'{"status":204,"body_bytes":0,"framing":true}')
    for status in (200, 260, 301, 400, 429, 500):
        try:
            validate_report(identity.canonical({'status': status, 'body_bytes': 0, 'framing': True}))
        except spool.Hold:
            pass
        else:
            raise AssertionError('UNEXPECTED_STATUS_ACCEPTED')
    print('V0145J_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')
    print('SELFTEST_NO_NETWORK_NO_SUBPROCESS_NO_FILE_WRITES=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    raw_source, raw_ack = planning.fixture_inputs()
    plan = planning.build_plan(raw_source, raw_ack)
    with LoopbackFixture(plan.requests[0]) as fixture:
        assert send_one(plan, raw_source, raw_ack, fixture) == 'PASS_OWNED_FIXTURE_EXCHANGE_ONLY'
        assert fixture.seen == [plan.requests[0].body] and fixture.total_posts == 1
    assert not fixture.active and not fixture.thread.is_alive() and fixture.server.socket.fileno() == -1
    planning.require_current(plan, raw_source, raw_ack)
    print('=== HCC V0.14.5J / OWNED LOOPBACK HTTP EXCHANGE ===')
    print('SYNTHETIC_REQUESTS_SENT=1 RECORDS_IN_REQUEST=16')
    print('HTTP_STATUS=204 FIXTURE_BODY_MATCH=YES')
    print('CLIENT_ATTEMPTS=1 AUTOMATIC_RETRY=NO')
    print('CLIENT_WORKER=EXITED_AND_REAPED FIXTURE_LISTENER=CLOSED')
    print('NETWORK=OWNED_EPHEMERAL_IPV4_LOOPBACK_ONLY')
    print('SUBPROCESS=BOUNDED_CLIENT_WORKER FILES_WRITTEN=NO')
    print('REAL_LOKI_ACCEPTANCE=NOT_TESTED ACK_OR_CHECKPOINT_ADVANCE=NO')
    print('PLAN_PENDING_AFTER_EXCHANGE=33 DECLARED_ACKS_AFTER_EXCHANGE=2')
    print('RETENTION_ACTION=NO_DELETION')
    print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
    print('PRODUCTION_CHANGES=NO')
    print('V0145J_RESULT=PASS_OWNED_LOOPBACK_FIXTURE_ONLY')
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
        print('V0145J_RESULT=HOLD_LOOPBACK_EXCHANGE_FAILURE')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
