#!/usr/bin/env python3
"""HCC V0.14.5K: bounded sequential prefix of owned J fixture exchanges.

At most four selected requests, state revalidation before each, stop on the
first failure. No real Loki, receipt/ACK update, persistent state or retries.
--self-test is memory-only; --lab uses owned loopback peers and client children.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json

import v0145a_segment_spool as spool
import v0145e_atomic_handoff as handoff
import v0145f_delivery_ack as delivery
import v0145h_loki_request as encoding
import v0145i_batch_plan as planning
import v0145j_loopback_exchange as exchange

MAX_PREFIX_REQUESTS = 4
MAX_PREFIX_BYTES = 256 * 1024
EXCHANGE_OK = 'PASS_OWNED_FIXTURE_EXCHANGE_ONLY'


@dataclass(frozen=True)
class PrefixResult:
    outcome: str
    total_requests: int
    selected_requests: int
    send_calls: int
    matched_requests: int
    observed_posts: int
    uninvoked_requests: int
    stopped_index: int | None
    stop_phase: str | None
    plan_pending_records: int


def _state(plan, read_state):
    try:
        sample = read_state()
    except Exception as exc:
        raise spool.Hold('PREFIX_STATE_PROVIDER_FAILURE') from exc
    if type(sample) is not tuple or len(sample) != 2:
        raise spool.Hold('PREFIX_STATE_PROVIDER_SHAPE')
    planning.require_current(plan, sample[0], sample[1])
    return sample


def run_prefix(plan, read_state, *, limit=3, replies=None):
    """Run a selected prefix only; fixture matches never advance ACK/progress.

    read_state is trusted caller code and must provide fresh source/ACK bytes.
    This model supplies no live file locking or deadline for that callback.
    Script options are prevalidated before any listener/client is created.
    """
    if type(limit) is not int or not 1 <= limit <= MAX_PREFIX_REQUESTS or not callable(read_state):
        raise spool.Hold('PREFIX_OPTIONS')
    current = _state(plan, read_state)
    selected = plan.requests[:limit]
    if sum(len(request.body) for request in selected) > MAX_PREFIX_BYTES:
        raise spool.Hold('PREFIX_BODY_BUDGET')
    if replies is None:
        replies = tuple(exchange.Reply() for _ in selected)
    if type(replies) is not tuple or len(replies) != len(selected):
        raise spool.Hold('PREFIX_REPLY_COUNT')
    fixtures = tuple(exchange.LoopbackFixture(request, reply) for request, reply in zip(selected, replies))
    send_calls = matched = posts = 0
    stopped_index = stop_phase = None
    for index, fixture in enumerate(fixtures):
        if index:
            try:
                current = _state(plan, read_state)
            except Exception:
                stopped_index, stop_phase = index, 'STATE_REVALIDATION'
                break
        try:
            with fixture:
                send_calls += 1
                result = exchange.send_one(plan, current[0], current[1], fixture, index=index)
                if type(result) is not str or result != EXCHANGE_OK:
                    raise spool.Hold('PREFIX_UNEXPECTED_EXCHANGE_RESULT')
            # Count a match only after this peer's context cleanup succeeded.
            matched += 1
        except Exception:
            stopped_index, stop_phase = index, 'EXCHANGE_OR_CLEANUP'
            break
        finally:
            posts += fixture.total_posts
    if stopped_index is not None:
        outcome = 'HOLD_PREFIX_STOPPED'
    elif not selected:
        outcome = 'NO_PENDING_REQUESTS'
    else:
        outcome = 'PREFIX_MATCHED_OWNED_FIXTURES_ONLY'
    return PrefixResult(outcome, len(plan.requests), len(selected), send_calls, matched, posts,
                        len(plan.requests) - send_calls, stopped_index, stop_phase, len(plan.pending_ids))


def self_test():
    raw = encoding.fixture_snapshot()
    source = handoff.decode_snapshot(raw)
    pairs = tuple((json.loads(payload)['event_id'], delivery.payload_hash(payload)) for payload in source.events)
    ack = delivery.encode_state(delivery.AckState(source.scope, pairs))
    plan = planning.build_plan(raw, ack)
    result = run_prefix(plan, lambda: (raw, ack))
    assert result.outcome == 'NO_PENDING_REQUESTS' and result.send_calls == result.observed_posts == 0
    print('V0145K_SELFTEST=PASS_PURE_SYNTHETIC_ONLY')
    print('SELFTEST_NO_NETWORK_NO_SUBPROCESS_NO_FILE_WRITES=YES')
    print('DEPLOYMENT_GATE=HOLD')


def run_lab():
    raw, ack = planning.fixture_inputs()
    plan = planning.build_plan(raw, ack)
    result = run_prefix(plan, lambda: (raw, ack))
    assert result.outcome == 'PREFIX_MATCHED_OWNED_FIXTURES_ONLY'
    assert result.selected_requests == result.send_calls == result.matched_requests == result.observed_posts == 3
    assert result.uninvoked_requests == 0 and result.plan_pending_records == 33
    planning.require_current(plan, raw, ack)
    print('=== HCC V0.14.5K / BOUNDED OWNED HTTP PREFIX ===')
    print('SELECTED_PREFIX_REQUESTS=3 SEND_CALLS=3 MATCHED_FIXTURES=3')
    print('OBSERVED_HTTP_POSTS=3 REMAINING_UNINVOKED_REQUESTS=0')
    print('PENDING_RECORDS_AFTER_RUN=33 DECLARED_ACKS_AFTER_RUN=2')
    print('STATE_CHECKS=BEFORE_EACH_SELECTED_REQUEST')
    print('FAILED_BATCH_POLICY=STOP_NO_RETRY_NO_FOLLOWING_REQUEST')
    print('CLIENTS_REAPED=YES LISTENERS_CLOSED=YES')
    print('NETWORK=OWNED_EPHEMERAL_IPV4_LOOPBACK_ONLY')
    print('SUBPROCESS=ONE_BOUNDED_CLIENT_PER_SELECTED_REQUEST FILES_WRITTEN=NO')
    print('REAL_LOKI_ACCEPTANCE=NOT_TESTED ACK_OR_CHECKPOINT_ADVANCE=NO')
    print('RETENTION_ACTION=NO_DELETION')
    print('JOURNAL_READ=NO ALLOY_CONTACT=NO LOKI_CONTACT=NO ASUS_CONTACT=NO')
    print('PRODUCTION_CHANGES=NO')
    print('V0145K_RESULT=PASS_OWNED_PREFIX_FIXTURES_ONLY')
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
        print('V0145K_RESULT=HOLD_PREFIX_LAB_FAILURE')
        print('REASON=' + type(exc).__name__)
        print('DEPLOYMENT_GATE=HOLD')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
