# DNS Guard v3.2 post-audit live validation

**Scope:** bounded live validation for issue #196 / PR #197 only.\
**Do not run automatically.** Use a trusted LAN recovery session and a current
project backup.

This runbook validates recovery behavior introduced by the post-v3.2 audit. It
does not replace the original
[`dns-guard-v3.2-live-validation.md`](dns-guard-v3.2-live-validation.md).

## Preconditions

Before fault injection:

```sh
GUARD=/jffs/addons/asus-edge/bin/dns-guard
HEALTH=/jffs/addons/asus-edge/bin/healthcheck.sh
CONFIG=/jffs/configs/asus-edge.conf

. "$CONFIG"

"$GUARD" status
"$GUARD" metrics
"$HEALTH"
cru l | grep -F '#AsusEdgeDNSGuard#'
cat /tmp/resolv.conf
```

Acceptance before continuing:

- trusted LAN shell remains open;
- break-glass is inactive;
- watchdog entry is exact and once per minute;
- `asus_edge_dns_guard_watchdog_present 1` is present in DNS Guard metrics;
- local resolver configuration is valid;
- Pi-hole and Unbound are healthy;
- project healthcheck has no new failures;
- candidate files on the router match PR #197.

Create a shell helper for temporary router-originated DNS blocks:

```sh
dns_block_add() {
    target="$1"
    iptables -I OUTPUT 1 -d "$target" -p udp --dport 53 -j REJECT
    iptables -I OUTPUT 1 -d "$target" -p tcp --dport 53 -j REJECT
}

dns_block_del() {
    target="$1"
    while iptables -D OUTPUT -d "$target" -p udp --dport 53 -j REJECT 2>/dev/null; do :; done
    while iptables -D OUTPUT -d "$target" -p tcp --dport 53 -j REJECT 2>/dev/null; do :; done
}
```

Do not leave these temporary OUTPUT rules behind.

## Reference firmware compatibility gate (before installation)

A real TUF-AX5400 (GNUton 3004.388.11) uses firmware BusyBox v1.25.1
**without** `timeout`; firmware `nslookup` accepts no `-timeout`/`-retry`
arguments. Entware `/opt/bin/timeout` works only after `/opt` mounts. The
original candidate falsely failed `ready` on the healthy router.

Before any live file replacement, fetch the updated candidate at its **exact
approved commit SHA** into a private `/tmp` staging directory and verify its
GitHub-sourced SHA-256 hashes and shell syntax. Invoke staged DNS Guard through
`sh` (downloads have mode 0600):

```sh
STAGE=/tmp/your-verified-pr197-stage
EDGE_DNS_STATE_DIR="$STAGE/test-state" \
EDGE_DNS_RUNTIME_STATE_DIR="$STAGE/test-runtime" \
    sh "$STAGE/dns-guard" ready

EDGE_DNS_STATE_DIR="$STAGE/test-state" \
EDGE_DNS_RUNTIME_STATE_DIR="$STAGE/test-runtime" \
    sh "$STAGE/dns-guard" status
```

Require `READY=PASS` and PASS for NTP, Unbound, Pi-hole listener and query.
Confirm `/bin/busybox sleep 0` and `/bin/busybox kill -0 $` work.
Staging must not change `/tmp/resolv.conf`, NVRAM, WAN or the production
DNS Guard executable. Do not mistake CI PASS for real-firmware validation.

The portable timeout mechanism bounds direct children, not detached process
trees. Keep WAN-restart and break-glass live tests under local supervision.

## Test 1 — local DNS failure -> functional bootstrap

### Preconditions

Normal steady state is local DNS.

```sh
LOCAL_DNS="$EDGE_DNS_LOCAL_RESOLVER_IP"
cat /tmp/resolv.conf
"$GUARD" ready
```

### Fault

Block only router-originated access to the local Pi-hole target:

```sh
dns_block_add "$LOCAL_DNS"
"$GUARD" auto
rc=$?
echo "RC=$rc"
cat /tmp/resolv.conf
"$GUARD" metrics
```

### Expected

- local readiness fails;
- DNS Guard attempts fail-open immediately;
- `FALLBACK=PASS` or `FALLBACK=ALREADY_BOOTSTRAP`;
- `AUTO=BOOTSTRAP_UNHEALTHY`;
- bootstrap mode metric is 1;
- bootstrap health metric is 1;
- router can resolve a normal public name.

### Rollback

```sh
dns_block_del "$LOCAL_DNS"
"$GUARD" auto
"$GUARD" auto
"$GUARD" auto
cat /tmp/resolv.conf
```

### Acceptance

After three consecutive healthy checks, the resolver returns to the configured
local target and the recovery streak resets.

## Test 2 — bootstrap selected but functionally dead

First record the candidate set:

```sh
"$GUARD" fallback
"$GUARD" status
```

Copy the addresses printed under `=== BOOTSTRAP DNS ===` into a temporary shell
variable:

```sh
BOOTSTRAP_DNS="resolver1 resolver2"
```

Use the actual addresses from the status output; do not paste public evidence
containing deployment-specific WAN details.

### Fault

```sh
for dns in $BOOTSTRAP_DNS; do
    dns_block_add "$dns"
done

set +e
"$GUARD" fallback
rc=$?
set -e
echo "RC=$rc"

"$GUARD" metrics
```

### Expected

- resolver remains in fail-open/bootstrap form;
- fallback returns non-zero;
- output contains `FALLBACK=UNHEALTHY_BOOTSTRAP`;
- `asus_edge_dns_guard_bootstrap_dns_healthy 0`;
- last bootstrap-health check timestamp is non-zero.

### Rollback

```sh
for dns in $BOOTSTRAP_DNS; do
    dns_block_del "$dns"
done

"$GUARD" fallback
"$GUARD" metrics
```

### Acceptance

A working bootstrap resolver is detected again without reboot and the bootstrap
health metric returns to 1.

## Test 3 — local and bootstrap fail simultaneously

### Fault

```sh
dns_block_add "$LOCAL_DNS"
for dns in $BOOTSTRAP_DNS; do
    dns_block_add "$dns"
done

set +e
"$GUARD" auto
rc=$?
set -e
echo "RC=$rc"
"$GUARD" status
"$GUARD" metrics
```

### Expected

- DNS Guard does not claim healthy recovery;
- watchdog/manual `auto` remains retryable;
- no hard-coded third-party resolver appears;
- bootstrap-health metric is 0 if bootstrap mode was selected.

### Partial recovery: bootstrap first

```sh
for dns in $BOOTSTRAP_DNS; do
    dns_block_del "$dns"
done

"$GUARD" auto
"$GUARD" metrics
```

Expected: functional bootstrap recovers without reboot.

### Final recovery: local path

```sh
dns_block_del "$LOCAL_DNS"

"$GUARD" auto
"$GUARD" auto
"$GUARD" auto
cat /tmp/resolv.conf
"$GUARD" status
```

Expected: normal hysteresis returns the router to local DNS.

## Test 4 — dead bootstrap is escaped immediately when local DNS is healthy

Start from functional bootstrap:

```sh
"$GUARD" fallback
```

Block only the bootstrap resolvers while leaving local Pi-hole/Unbound healthy:

```sh
for dns in $BOOTSTRAP_DNS; do
    dns_block_add "$dns"
done

"$GUARD" auto
cat /tmp/resolv.conf
```

Expected:

```text
AUTO=LOCAL_DNS_BOOTSTRAP_UNHEALTHY
```

and the resolver becomes the local Pi-hole immediately, without waiting for the
three-success hysteresis threshold.

Rollback:

```sh
for dns in $BOOTSTRAP_DNS; do
    dns_block_del "$dns"
done
```

## Test 5 — watchdog recovery

Force bootstrap while local DNS remains healthy:

```sh
"$GUARD" fallback
cat /tmp/resolv.conf
```

Do not run manual `auto` for the next few minutes.

Observe:

```sh
date
cat /tmp/resolv.conf
"$GUARD" status
"$GUARD" metrics
```

Expected:

- watchdog runs once per minute;
- recovery streak advances across healthy samples;
- final resolver returns to local DNS;
- no local/bootstrap flapping occurs.

## Test 6 — bounded helper behavior

The source-controlled regression suite injects hanging DNS helpers, a hanging
logger and a hanging break-glass WAN restart. Do not intentionally hang
production BusyBox/logger/service utilities.

Live acceptance is observational:

```sh
"$GUARD" status
"$GUARD" ready
"$GUARD" fallback
```

Each command must return within the configured bounds. If any command appears
stuck, stop live validation and use the trusted LAN rollback path.

## Test 7 — break-glass on/off

Activate:

```sh
/jffs/scripts/edge-dns-breakglass.sh on
```

Acceptance:

- WAN DNS mode snapshot exists and is valid before emergency WAN-DNS mutation;
- a corrupt pre-existing snapshot is rejected before NVRAM changes or WAN restart;
- sticky break-glass is active;
- WAN restart, WAN/IP validation and DNS validation are bounded;
- final result is PASS only if both IP and DNS checks succeed.

Clear only after local DNS is healthy:

```sh
/jffs/scripts/edge-dns-breakglass.sh off
```

Acceptance:

- local readiness is checked before clearing;
- saved WAN DNS mode is restored;
- WAN restart succeeds;
- bootstrap path is revalidated;
- local path is rechecked;
- sticky flag is cleared only before a successful local promotion;
- snapshot is removed only after the full transaction succeeds.

If any clear step fails, the helper must re-arm safe break-glass rather than
silently leaving a half-restored state. A complete rearm reports
`BREAKGLASS_REARMED=YES`. If any rearm step itself fails, the helper must
report `BREAKGLASS_REARMED=PARTIAL`, include a non-zero failure count and
return non-zero; it must never claim full recovery after a partial rearm.

Partial NVRAM-write/commit/unset failure, corrupt existing snapshot rejection,
interrupted-state retry convergence, hung-`restart_wan` handling and
partial-rearm reporting are proven by the source-controlled regression suite.
Do **not** inject NVRAM commit/write failures on the production router merely
to reproduce those unit-test cases.

## Test 8 — WAN restart

Record before state:

```sh
nvram get wan0_dns_r
nvram get wan0_dns
nvram get wan_dns_r
nvram get wan_dns
cat /tmp/resolv.conf
```

Then:

```sh
service restart_wan
```

Wait for IP connectivity and inspect:

```sh
"$GUARD" auto
"$GUARD" status
"$GUARD" metrics
```

Acceptance:

- DNS Guard rereads current WAN NVRAM resolver sources;
- no historical bootstrap set is permanently pinned;
- state converges to functional bootstrap or healthy local DNS.

A true "operator changed DNS" replacement test should only be performed in a
maintenance window where WAN DNS source changes can be controlled safely. Do
not persist synthetic WAN DNS values with `nvram commit` merely to satisfy
this runbook.

## Test 9 — repeated WAN reconnect

Run only with local console/trusted LAN recovery available.

Perform two bounded restart cycles, allowing WAN to return between them:

```sh
service restart_wan
# wait for WAN/IP recovery
"$GUARD" auto
"$GUARD" status

service restart_wan
# wait for WAN/IP recovery
"$GUARD" auto
"$GUARD" status
```

Acceptance:

- no permanent `UNKNOWN` resolver state;
- no duplicate/corrupt resolver entries;
- watchdog remains scheduled;
- Tailscale recovery is not used as proof of DNS recovery;
- DNS converges independently.

## Test 10 — cold reboot

Run only after Tests 1-9 are accepted.

Before reboot:

```sh
"$HEALTH"
"$GUARD" status
"$GUARD" metrics
cru l | grep -F '#AsusEdgeDNSGuard#'
sync
reboot
```

After the router returns:

```sh
uptime
nvram get ntp_ready
pidof unbound
pidof pihole-FTL
pidof tailscaled
cru l | grep -F '#AsusEdgeDNSGuard#'
cat /tmp/resolv.conf
"$GUARD" status
"$GUARD" metrics
"$HEALTH"
```

Acceptance:

- watchdog exists even if Entware startup is slow;
- no NTP/DNS bootstrap deadlock;
- bootstrap recovery is available before local promotion;
- Pi-hole and Unbound recover;
- final resolver converges to local DNS;
- break-glass remains inactive;
- project healthcheck is clean.

## Final cleanup

Always confirm no temporary OUTPUT rules remain:

```sh
iptables -S OUTPUT | grep -- '--dport 53' || true
```

Remove only the temporary rules created by this runbook if any remain.

Final evidence:

```sh
"$GUARD" status
"$GUARD" metrics
"$HEALTH"
cru l | grep -F '#AsusEdgeDNSGuard#'
cat /tmp/resolv.conf
```

Do not publish WAN DNS addresses, household DNS history, credentials, private
hostnames or Tailscale identities as public evidence.

## Merge gate

PR #197 must remain unmerged until:

- the current Validation suite is green;
- Tests 1-5 and 7-10 pass live or are explicitly waived with rationale;
- no temporary firewall fault-injection rule remains;
- Grafana receives bootstrap-health and watchdog-presence metrics;
- bootstrap-unhealthy, stale-telemetry, UNKNOWN-state, watchdog-missing and
  recovery-flapping alerts are provisioned;
- final project healthcheck is clean.


## Production verification addendum — 2026-10-08 (PR #197)

The earlier sections are the **test plan**, not a claim that all scenarios were
executed. Results below distinguish successful bounded production checks from
intentionally deferred disruptive tests. A subsequent real power-off/power-on
cold boot also passed with Entware storage available; that does **not** prove
the behavior with absent or unmountable Entware.

### Evidence verified on the actual ASUS router

- PR code revision verified before review: `233cf09046e17662a1c9cf905bc031534b9af531`;
  GitHub Validation suite run `37795542492` completed successfully with four
  successful jobs. Later documentation-only commits require fresh CI evidence.
- Native ARMv7 supervisor staging and bounded cleanup/lock tests passed. A
  limited **two-file** production deployment exercised the supervisor and
  `edge-dns-breakglass.sh`; it was not a full installer deployment.
- Live manual break-glass **ON**: `ON_EXIT_CODE=0`,
  `BREAKGLASS_RESULT=PASS`, sticky flag and WAN DNS snapshot present,
  bootstrap resolver selected, WAN restart **dispatch** accepted and
  functional WAN IP/internet IP/DNS checks passed.
- Live manual break-glass **OFF**: `OFF_EXIT_CODE=0`,
  `BREAKGLASS_CLEAR_RESULT=PASS`, local readiness verified before and after
  WAN dispatch, Pi-hole resolver promoted, flag inactive, snapshot removed,
  original WAN DNS NVRAM mode unchanged (`1/1`).
- After OFF, a follow-up sample briefly found bootstrap DNS while break-glass
  was inactive. Local DNS subsequently recovered automatically; six read-only
  samples between **18:01:40 and 18:06:41 CEST** all reported `mode=local`,
  unchanged fallback counter/transition timestamp, inactive break-glass and
  no snapshot. Do not attribute the transient to a particular mechanism
  without event evidence; sampled checks do not exclude sub-minute transitions.
- Project healthcheck: **0 failures, 0 warnings**; runtime DNS Guard metrics:
  `mode_local=1`, `state_valid=1`, `breakglass_active=0`,
  `bootstrap_dns_healthy=1`, `watchdog_present=1`. Watchdog cron present
  at its expected one-minute cadence; direct local Pi-hole DNS and
  bootstrap DNS probes passed; Tailscale recovered after the WAN operations.
- VictoriaMetrics returned actual bootstrap-health, watchdog-presence and
  collection-timestamp series. All five new DNS Guard alert rule UIDs were
  verified **loaded** in Grafana's read-only SQLite database, not merely
  present in the provisioning YAML. Provisioned alert file and PR source
  SHA-256 matched.
- Active Merlin hook `/jffs/scripts/services-start` SHA-256 matched the PR
  source (`026b3c18a950abd70ec86046b04c0015832289ec3ec886bcf4d25298aebf5616`).
  Its watchdog setup executes at line 325, **before** the `/opt` readiness
  wait at line 328; `jffs2_scripts=1`. A separate, older copy under
  `/jffs/addons/asus-edge/bin/services-start` did **not** match the PR;
  no overwrite was performed. Keep this split-path drift visible for future
  installer/boot-hook maintenance. The earlier assumption that the active
  hook simply `exec`s the add-on copy was false for this deployment.
- A final SHA comparison also matched the production `dns-guard` and
  `healthcheck.sh` scripts to this PR. No additional WAN restart, full
  installation, or file changes were performed during final checks.


### Production cold boot — 2026-10-08, 18:51–18:53 CEST — PASS (with Entware)

Operator completed a **real power-off/power-on cold boot**, not factory
reset, following a clean, read-only preflight at 18:43:01 CEST:
`REBOOT_PREFLIGHT=PASS`, local resolver `192.168.50.253`,
`READY=PASS`, break-glass inactive and no WAN snapshot; original
start-hook SHA-256 and watchdog cron verified.

**Startup evidence, before NTP synchronization (log time shown as Jan 1):**
- `01:00:40 asus-edge: DNS Guard watchdog scheduled`
- `01:00:44 usb: USB ext4 fs at /dev/sda1 mounted on /tmp/mnt/ENTWARE`
- `01:00:44 asus-edge: DNS Guard policy applied during WAN initial phase`
- Entware services then started; NTP was initially pending.
- After NTP synchronization, Unbound and Pi-hole FTL started normally
  (18:51:35–18:51:38 CEST), Tailscale and syslog-ng became RUNNING.
  The unsynchronized clock explains the initial Jan 1 log date; the
  source log sequence confirms watchdog was scheduled before USB mount.

**Post-boot observation at 18:52:04 CEST (approximately one minute uptime):**
- `ENTWARE=READY`; `unbound`, `pihole-FTL`, `tailscaled`,
  `syslog-ng` RUNNING; internet connectivity PASS.
- DNS Guard readiness `READY=PASS`, bootstrap mode still selected:
  `mode_bootstrap=1`, `mode_local=0`,
  `bootstrap_dns_healthy=1`, `watchdog_present=1`,
  `breakglass_active=0`.
- Router resolver still used configured ISP bootstrap DNS.
  Project healthcheck: **0 failures, 1 warning**, specifically temporary
  bootstrap/fail-open mode. This was an intermediate startup observation,
  **not** a failed final validation.

**Post-boot convergence at 18:53:35 CEST (approximately two minutes uptime):**
- `DECISION=LOCAL_DNS_READY`, `READY=PASS` components:
  `NTP=PASS`, `UNBOUND=PASS`, `PIHOLE_LISTENER=PASS`,
  `PIHOLE_QUERY=PASS`.
- `/tmp/resolv.conf`: `nameserver 192.168.50.253`;
  `mode_local=1`, `mode_bootstrap=0`, `state_valid=1`,
  `watchdog_present=1`, `recovery_streak=0/3`.
- Sticky break-glass remained INACTIVE; project healthcheck:
  **0 failures, 0 warnings**, exit code 0.
- Thus the actual boot sequence demonstrated fail-open bootstrap and
  autonomous return to local Pi-hole, with live service recovery and
  schedule creation before Entware mounted.

**Limitations:** Entware mounted successfully in this test, and a complete
disk-unavailable or persistent Entware-failure path was **not** tested.
These timestamps are sparse observations rather than a full trace of every
scheduler run or packet. Runtime transition counters are volatile across
reboots; do not compare post-boot values directly with the pre-boot value 9.
This test did not change NVRAM, inject firewall faults, or exercise the full
installer.

### Runbook coverage and bounded production waivers

| Test | Production outcome | Review gate disposition and residual |
|---|---|---|
| 1 — local DNS fault -> bootstrap | **Not injected** | Waived for this live exercise: blocking production Pi-hole on the router could disrupt household DNS. Covered by mock regression tests only; live failure injection remains unverified. |
| 2 — dead bootstrap | **Not injected** | Waived: intentionally blocking all independent WAN DNS sources could eliminate emergency DNS. Functional bootstrap was directly probed while healthy; dead-path behavior is regression-only. |
| 3 — simultaneous local/bootstrap failures | **Not injected** | Waived: would risk a full DNS outage. Dual-failure outcome is regression-only. |
| 4 — dead bootstrap while local ready | **Not injected** | Waived: disruptive temporary WAN DNS blocking. Immediate escape is regression-only. |
| 5 — watchdog automatic recovery | **Observed partial path** | Automatic convergence to local resolver and one-minute watchdog presence observed. Deliberate `fallback` forcing and isolated full hysteresis sequence were not run; full test waived for production risk. |
| 6 — bounded helpers | **Regression + observational** | Source-controlled hanging-helper simulations passed CI. Production break-glass operations were bounded and completed; no deliberate hanging services were injected. |
| 7 — manual ON/OFF | **PASS** | Full manual transition and reversal executed once. Partial-failure branches remain regression-only, without synthetic NVRAM failure injection. |
| 8 — WAN restart | **Partial** | ON and OFF each dispatched `restart_wan`; subsequent IP/DNS recovery passed. No separate standalone restart or direct WAN link-state instrumentation; waived extra disruption. |
| 9 — repeated WAN reconnect | **Partial** | Two separated WAN restart dispatches occurred during ON/OFF, with post-dispatch checks. Not a dedicated repeated-reconnect stress test; waived further restarts. |
| 10 — cold reboot | **PASS, available Entware** | Real power-off/power-on cold boot verified watchdog scheduling before USB Entware mount, bootstrap DNS during early startup, and automated return to Pi-hole. **Not tested:** boot with missing/unmountable Entware, persistent dependency failure, or exhaustive early-start race/fault injection. |

**Waiver scope:** these are engineering decisions to omit *additional
disruptive steps from this production exercise*, not claims of passing the
skipped cases or acceptance of their residual risks for every environment.
The reviewer/maintainer must explicitly decide whether the outstanding
Entware-unavailable cold-boot and failure-injection risks are acceptable
**before merging**. No
synthetic NVRAM values were committed and no runbook fault-injection OUTPUT
rules were deliberately installed as part of this exercise. The final
read-only firewall inspection found no matching direct destination-specific
DNS REJECT/DROP test rules; firmware-style OUTPUT DNS chain/string filters
were preserved without modification.

**Merge remains a separate decision:** passing CI and this bounded acceptance
exercise is sufficient to request code review, not automatic merge permission.
The installer's full end-to-end deployment on this specific live router has not
been exercised, and the original WAN mode already being `1/1` limited NVRAM
restore coverage. Related directory-permission scope is tracked in #200.
