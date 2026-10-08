# DNS Guard v3.2 recovery audit

**Status:** source-controlled hardening candidate for issue #196 / PR #197.\
**Production baseline:** `main` at DNS Guard v3.2 after #193.\
**Live deployment:** not performed by this audit.

This audit follows the historical
[`dns-bootstrap-deadlock-dns-guard-v3.1.md`](case-studies/dns-bootstrap-deadlock-dns-guard-v3.1.md)
incident and the accepted
[`dns-guard-v3.2-live-validation.md`](dns-guard-v3.2-live-validation.md)
baseline.

## Executive verdict

```text
DNS GUARD RECOVERY = ROBUST WITH GAPS
```

The v3.2 baseline already prevents the original NTP/Pi-hole/Unbound bootstrap
deadlock, but the post-v3.2 audit reproduced several narrower recovery gaps.

The candidate branch closes the confirmed source-level gaps without adding a
hard-coded public emergency resolver and without changing the normal
Pi-hole -> Unbound steady-state architecture.

The remaining material gap is the local readiness oracle: fixed probe names can
be answered from cache/stale cache, so a successful probe does not prove that
fresh recursive resolution is currently possible. This is documented as a
residual design risk rather than silently reintroducing unique public probe
names.

## Findings

| ID | Severity | Failure mode | Baseline evidence | Candidate result |
| --- | --- | --- | --- | --- |
| DG-R01 | P1 | A stalled DNS/helper or logging call can hold the global DNS Guard lock and delay later watchdog runs. | UDP readiness used unbounded BusyBox `nslookup`; lock acquisition and `logger` execution were unbounded. | DNS/helper and logger execution are bounded; lock acquisition has a finite wait. |
| DG-R02 | P1 | Fallback can write syntactically valid WAN DNS and report success even when no selected bootstrap resolver answers. | Baseline `fallback_bootstrap()` validated resolver addresses but not DNS function. | Fallback keeps fail-open resolver selection but returns `FALLBACK=UNHEALTHY_BOOTSTRAP` if functional bootstrap validation fails. |
| DG-R03 | P1 | A stale but syntactically valid higher-priority WAN DNS source can hide a later valid resolver source. | Baseline `bootstrap_dns()` returned after the first key containing accepted candidates. | Valid unique candidates are aggregated across known WAN DNS keys, capped at three nameservers. |
| DG-R04 | P1 | If bootstrap DNS is dead while the complete local path has recovered, normal failback hysteresis can unnecessarily extend the outage. | Healthy local path plus broken bootstrap still entered the normal recovery-streak path. | Broken bootstrap is escaped immediately to a healthy local resolver; hysteresis remains for healthy bootstrap -> local failback. |
| DG-R05 | P1 | The watchdog could be scheduled only after a long/failing Entware startup path. | `services-start` configured the watchdog after `/opt` recovery. | The watchdog is scheduled before waiting for `/opt` and before Entware service recovery. |
| DG-R06 | P1 | Break-glass can hang during DNS/WAN recovery or leave partially changed WAN DNS NVRAM after a mid-activation failure. | DNS validation and `service restart_wan` were unbounded; failure of the second WAN-DNS NVRAM write could leave the first write applied. | DNS validation and WAN restart are bounded; activation restores the pre-break-glass WAN DNS snapshot if safe-mode NVRAM mutation fails part-way through. |
| DG-R07 | P2 | Corrupted oversized runtime counters can reach shell arithmetic/telemetry paths. | Runtime numeric state accepted arbitrary digit strings, and the same 10-digit allowance needed for epoch timestamps could also admit an implausible transition counter. | Recovery streak is clamped/reset safely; epoch timestamps retain a 10-digit allowance while the transition counter uses a tighter bound before arithmetic/telemetry. |
| DG-R08 | P2 | `mode_bootstrap=1` does not distinguish working bootstrap DNS from selected-but-broken bootstrap DNS. | Baseline had resolver-mode telemetry only. | Added bootstrap-health and last-check metrics plus a Grafana alert. |
| DG-R09 | P2 | Loss of the Fedora DNS Guard collector can hide state changes. | Sustained fail-open alert required fresh telemetry but there was no dedicated stale-collector alert. | Added a stale DNS Guard telemetry alert. |
| DG-R13 | P2 | Monitoring did not distinguish persistent UNKNOWN resolver state, missing watchdog scheduling, and repeated recovery flapping. | Existing metrics exposed `state_valid` and transition count, while watchdog drift was visible only to local healthcheck. | Added watchdog-presence telemetry plus dedicated Grafana conditions for UNKNOWN state, watchdog loss and repeated fail-open transitions. |
| DG-R14 | P2 | Break-glass recovery rearm could report `BREAKGLASS_REARMED=YES` even when one or more rearm steps failed. | The helper swallowed failures from sticky re-arm, safe WAN-DNS mode, bounded WAN restart and fallback reassertion, then emitted unconditional success. | Rearm now counts failed recovery steps, reports `BREAKGLASS_REARMED=PARTIAL` plus a failure count, and returns non-zero instead of claiming full recovery. |
| DG-R15 | P2 | A pre-existing corrupt break-glass WAN-DNS snapshot could be trusted as `EXISTING`, allowing emergency NVRAM mutation without a valid rollback source. | Snapshot reuse checked only for file existence. | Existing snapshots are now schema/token validated before any WAN-DNS mutation; corrupt snapshots return `WAN_DNS_SNAPSHOT=INVALID` and activation stops before restart or NVRAM change. |
| DG-R16 | P1 | The exact reference Merlin/GNUton firmware lacks the BusyBox `timeout` applet; candidate readiness falsely failed for healthy NTP/Unbound/Pi-hole, risking incorrect fail-open. | 2026-10-08 read-only live preflight: production `ready=PASS`, candidate `ready=FAIL`, `/bin/busybox timeout` exits 127; firmware has `sleep` and `kill` and Entware has `/opt/bin/timeout` only after mount. Firmware BusyBox `nslookup` has no timeout flags. | Candidate now bounds direct child commands using firmware sleep/kill, with no dependency on the Entware mount; healthcheck validates those primitives; regressions simulate missing BusyBox timeout. Pending actual router staging acceptance. |
| DG-R10 | P1 residual | Fixed local probe names can be answered from cached/stale data and may not prove fresh recursion. | Pi-hole/Unbound readiness uses stable names; the project Unbound config enables `serve-expired`. | Not changed automatically. Requires a separate design decision for a cache-resistant recursion oracle. |
| DG-R11 | P2 residual | Bootstrap functional validation primarily proves a normal small DNS lookup, not every TCP/truncation case. | BusyBox `nslookup` is the mandatory low-dependency probe. | Retained as a bounded availability probe; TCP-specific bootstrap proof remains a live/design follow-up. |
| DG-R12 | P1 residual | If the managed watchdog cron entry disappears after boot, DNS Guard cannot recreate that scheduler from inside the missing scheduler path. | `healthcheck.sh` detects exact cron drift, but there is no independent on-router supervisor for the watchdog itself. | DNS Guard now exports exact watchdog-presence telemetry and Grafana alerts on a missing/drifted scheduler while telemetry is fresh. Self-repair still requires an independent supervisor or operator/reboot action and remains intentionally out of scope. |

## State machine

| State | Resolver state | `dns-guard auto` behavior | Automatic exit |
| --- | --- | --- | --- |
| LOCAL | configured local Pi-hole only | verifies complete local readiness; stays local when healthy, fails open when unhealthy | yes |
| BOOTSTRAP | validated WAN resolver set | verifies local path and bootstrap function; applies hysteresis only when bootstrap itself is usable | yes |
| BOOTSTRAP_UNHEALTHY | WAN resolver selected but functional probe fails | retries bootstrap while local is unhealthy; immediately selects local once the complete local path is healthy | yes, if either path recovers |
| UNKNOWN | missing/empty/foreign/mixed resolver state | evaluates local health, then converges to bootstrap or local according to current health | yes |
| LOCAL_UNHEALTHY | local target selected but Pi-hole/Unbound/NTP/query path fails | immediate fail-open attempt | yes if a bootstrap resolver becomes usable |
| BOOTSTRAP_UNAVAILABLE | no independent usable WAN candidate exists | returns non-zero and retries on later watchdog/WAN events | yes if NVRAM later supplies a usable resolver or local path recovers |
| RECOVERY_PENDING | local healthy, bootstrap healthy, streak below threshold | keeps/reasserts functional bootstrap until the configured success threshold | yes |
| CONFIG_INVALID | local resolver target missing/invalid | keeps attempting independent bootstrap DNS | yes after config correction or available bootstrap |
| BREAKGLASS | persistent break-glass flag exists | keeps the router on bootstrap and blocks automatic local promotion | operator-controlled by design |

The only intentionally non-automatic state is `BREAKGLASS`. Sticky
break-glass is a manual override and is therefore not treated as a recovery
dead-end defect.

## Bootstrap failure matrix

The candidate behavior is:

| Condition | Expected behavior |
| --- | --- |
| all WAN DNS NVRAM keys empty | fallback fails non-zero; watchdog retries |
| invalid / loopback / `0.0.0.0` / local Pi-hole candidates | candidates rejected |
| duplicate candidates | deduplicated |
| first resolver dead, later resolver healthy | later resolver can satisfy functional bootstrap validation |
| higher-priority NVRAM key stale, later key valid | candidates from later known keys remain available |
| all syntactically valid candidates dead | resolver can still be written for fail-open recovery, but fallback is reported unhealthy rather than successful |
| DHCP/WAN later supplies new DNS | next watchdog/WAN invocation rereads NVRAM and can self-heal |
| local and bootstrap both fail | watchdog remains retrying; no hard-coded third-party resolver is injected |
| local recovers while bootstrap is dead | immediate local promotion |
| firmware rewrites resolver to an unknown set | watchdog reconverges on a legal local/bootstrap state if either path is usable |

## Hysteresis and concurrency

The normal threshold remains:

```text
EDGE_DNS_FAILBACK_SUCCESS_THRESHOLD=3
```

The candidate preserves the intended semantics:

```text
PASS PASS FAIL -> streak reset
PASS FAIL PASS -> no premature promotion
FAIL PASS PASS PASS -> promotion after three consecutive healthy checks
LOCAL failure -> immediate fail-open attempt
dead bootstrap + healthy local -> immediate local recovery
```

Concurrent state transitions remain serialized. Lock acquisition itself is now
bounded, so a second watchdog invocation cannot build an indefinite waiter
queue behind a stuck first invocation.

## State corruption

The following states converge safely or fail safe:

- textual recovery streak -> treated as zero;
- oversized recovery streak -> treated as zero;
- oversized runtime counters -> sanitized;
- invalid current-mode state -> reconciled from the observed resolver;
- missing runtime directory after reboot -> recreated;
- stale lock file without a live lock owner -> harmless because `flock`
  ownership is process-bound;
- empty/corrupt break-glass flag file -> treated as active, preserving the
  fail-safe manual override;
- interrupted atomic runtime-state write -> previous committed state remains
  usable; a temporary file may remain but is not authoritative.

A physically read-only or failed JFFS/`/tmp` filesystem remains outside what
DNS Guard can fully self-heal. That is a platform/storage failure, not a DNS
state-machine transition.

## Boot sequencing

The validated v3.2 architecture already performs immediate fail-open at WAN
events and periodic watchdog recovery. The candidate additionally schedules the
watchdog before waiting for Entware storage/services, reducing the chance that a
slow or failed `/opt` recovery removes the periodic DNS recovery path.

The following ordering is expected:

```text
services-start
  -> schedule DNS Guard watchdog
  -> wait for /opt
  -> recover Entware / Unbound / Tailscale
  -> local readiness becomes true
  -> watchdog counts stable checks
  -> promote to local DNS
```

A new cold-boot live test is still required before production rollout.

## Monitoring

New coarse metrics:

```text
asus_edge_dns_guard_bootstrap_dns_healthy
asus_edge_dns_guard_bootstrap_dns_last_check_timestamp_seconds
asus_edge_dns_guard_watchdog_present
```

Existing mode, transition and collection-timestamp metrics remain available.

Grafana conditions now distinguish:

- sustained fail-open with fresh telemetry;
- bootstrap selected but unhealthy/stale bootstrap health;
- stale DNS Guard telemetry;
- persistent UNKNOWN/invalid resolver state;
- missing or drifted managed watchdog scheduling while telemetry is still fresh;
- repeated fallback transitions consistent with recovery flapping.

The watchdog metric validates the exact managed cron entry. It improves external
detection but does not create a second on-router supervisor; if the scheduler
itself disappears, operator/reboot recovery is still required.

## Residual risk: cache-resistant recursion proof

The current local-path probe deliberately uses stable names from independent
providers rather than unique public names. That avoids turning the watchdog
into a high-rate public-query generator.

However, the project Unbound configuration enables `serve-expired`. Therefore
a fixed probe can still receive a stale answer while upstream recursion is
impaired. The current probe proves:

```text
Pi-hole listener + path can return an expected DNS answer
```

but it does not always prove:

```text
a previously uncached name can be recursively resolved right now
```

No automatic code change is made here because the alternatives introduce
trade-offs: cache flushing, an `unbound-control` dependency, a unique public
probe namespace, or a dedicated health-check zone.

This is the main reason the audit verdict is **ROBUST WITH GAPS** rather than
**ROBUST**.

## Reference firmware compatibility checkpoint (2026-10-08)

The on-device preflight identified firmware BusyBox v1.25.1 on the TUF-AX5400
without `timeout` or adjustable `nslookup` timeouts. The project must not
depend on `/opt/bin/timeout` for early boot because watchdog startup is
intentionally earlier than mounting Entware.

The proposed native watchdog uses firmware `sleep` plus `kill` to bound
individual direct-child commands. Its timer and worker close the inherited
DNS Guard flock fd. A force-killed worker returns a non-zero result rather than
healthy readiness. This is **not process-group cancellation**: an external
utility that forks/detaches descendants might leave such descendants alive,
so production WAN-restart recovery remains a separately gated test. Timeout
intervals are capped at 120 seconds.

Regression fixtures deliberately make BusyBox `timeout` unavailable while
requiring the guard and break-glass unit tests to run. This is source-level
evidence only; the new candidate must pass the isolated `ready` / `status` /
`metrics` check on the actual router before installation.

## Source-controlled validation

Regression coverage now includes:

- concurrent invocation serialization without a lock-timeout race in the test harness;
- bounded lock acquisition;
- bounded UDP DNS probe execution;
- real-firmware no-timeout BusyBox emulation and native sleep/kill watchdog operation without Entware dependency;
- bounded logger execution while the global guard lock is held;
- functional bootstrap validation;
- stale higher-priority WAN DNS with a later usable source;
- dead-bootstrap immediate escape to recovered local DNS;
- three-success failback hysteresis;
- recovery-streak reset on failure;
- oversized/corrupt runtime state, including distinct epoch/counter bounds;
- break-glass DNS timeout, bounded WAN restart, partial-NVRAM rollback, corrupt-snapshot rejection and explicit partial-rearm reporting;
- coarse bootstrap-health and watchdog-presence telemetry;
- Fedora exporter forwarding the new metrics;
- static guards for early watchdog scheduling and Grafana alerts for bootstrap
  health, stale telemetry, UNKNOWN resolver state, watchdog loss and flapping.

The project Validation suite must be green at the candidate head before live
testing.

## Live validation gate

Do not merge or deploy solely from source-level evidence.

Run the bounded live-validation runbook in
[`dns-guard-v3.2-recovery-audit-live-validation.md`](dns-guard-v3.2-recovery-audit-live-validation.md)
with a trusted LAN recovery session and an immediate rollback path.

Only after the live checkpoints pass should the candidate be considered for
merge into `main`.
