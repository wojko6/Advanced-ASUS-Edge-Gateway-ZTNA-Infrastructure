# DNS Guard v3.2 post-audit live validation

**Scope:** bounded live validation for issue #196 / PR #197 only.  
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

- WAN DNS mode snapshot exists;
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
silently leaving a half-restored state.

Partial NVRAM-write failure and hung-`restart_wan` fault injection are proven
by the source-controlled regression suite. Do **not** inject NVRAM commit/write
failures on the production router merely to reproduce those unit-test cases.

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
