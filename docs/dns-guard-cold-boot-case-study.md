# DNS bootstrap deadlock and fail-open resolver recovery

## Summary

On 2026-10-06 the reference ASUS TUF-AX5400 deployment exposed a cold-boot
dependency cycle after the router's system resolver was changed to the local
Pi-hole listener.

The configuration worked while the router was already fully initialized, but a
full reboot produced working IP connectivity with failed DNS resolution. The
fault was traced to the interaction between firmware NTP bootstrap, Entware
Unbound startup, Pi-hole upstream selection, and the router's own system
resolver.

The remediation introduced **DNS Guard v3.1**, a fail-open runtime resolver
controller with a persistent watchdog and a sticky break-glass mode.

## Environment

Reference components involved in the incident:

- ASUS TUF-AX5400 running Asuswrt-Merlin/GNUton;
- firmware WAN resolver data generated from the ISP-provided DNS servers;
- Pi-hole FTL bound to a dedicated local alias on TCP/UDP 53;
- Unbound bound to loopback TCP/UDP 53535;
- Pi-hole upstream set to Unbound;
- Tailscale configured as a subnet router and exit node;
- project-managed WAN and services hooks under `/jffs/addons/asus-edge`.

The exact ISP/public addresses are deployment-specific and are not required to
understand the failure mode.

## Incident

A runtime test first showed that pointing `/tmp/resolv.conf` at Pi-hole allowed
Tailscale exit-node DNS to follow the intended local filtering path.

The same policy was then made persistent through the WAN DNS configuration and
the router was rebooted.

After the cold boot:

- Internet connectivity by IP was present;
- DNS queries failed;
- Pi-hole had no usable upstream path;
- the Unbound init script reported that it was waiting for NTP synchronization.

The critical startup relation was:

```text
router system resolver -> Pi-hole -> Unbound
                              ^
                              |
                         waits for NTP
                              ^
                              |
                       NTP hostname lookup
```

Because the router itself depended on Pi-hole before Unbound was available, and
Unbound intentionally waited for NTP before starting, the runtime configuration
created a boot-time circular dependency.

## Root-cause assessment

The directly observed facts support the following root cause:

1. the firmware NTP configuration used hostname-based NTP servers;
2. Unbound's Entware init script explicitly waited for `ntp_ready=1`;
3. Pi-hole used Unbound on `127.0.0.1:53535` as its upstream;
4. the router system resolver had been redirected to Pi-hole;
5. cold boot therefore required local DNS before the service providing the local
   DNS upstream was allowed to start.

This was an architecture/startup-order defect in the local deployment, not a
Tailscale regression.

## Design goals

The remediation used the following availability rules:

- firmware/WAN DNS remains the independent **bootstrap resolver**;
- Pi-hole becomes the router's runtime resolver only after the complete local
  DNS path is healthy;
- any local DNS failure restores bootstrap DNS instead of leaving the router
  without name resolution;
- emergency break-glass mode must survive WAN events and block automatic
  promotion back to Pi-hole;
- repeated watchdog runs must be idempotent;
- the policy must survive a full router reboot.

The design intentionally prefers DNS availability over filtering during a local
resolver outage.

## DNS Guard v3.1

`router/scripts/dns-guard` implements four relevant policy states.

### Healthy local path

Promotion requires all of the following:

- `ntp_ready=1`;
- Unbound process running;
- Unbound listener present on the configured loopback port;
- Pi-hole FTL running;
- Pi-hole listener present;
- a fresh functional DNS query through Pi-hole returning the expected test
  address.

When these checks pass, only the runtime resolver file is atomically promoted to
Pi-hole.

### Unhealthy local path

If any readiness or functional test fails, DNS Guard restores the current WAN
bootstrap resolvers from firmware NVRAM state.

The persistent WAN configuration itself is not changed by normal promotion.

### Sticky break-glass

`breakglass-on` creates a persistent state flag and immediately restores
bootstrap DNS. While that flag exists, `promote` is rejected.

The separate recovery script
`router/scripts/edge-dns-breakglass.sh` additionally ensures automatic WAN DNS
mode is enabled before restarting WAN.

### Idempotency

Writing the same resolver state returns a dedicated internal status instead of
rewriting the file. Both `PROMOTE=ALREADY_LOCAL` and
`FALLBACK=ALREADY_BOOTSTRAP` are treated as successful no-op states.

An early v3.1 test exposed an implementation bug where the internal
"already bootstrap" return value was incorrectly converted into
`FALLBACK=FAILED`. A shell trace isolated the branch and the wrapper logic was
corrected before reboot validation.

## WAN-event integration

The historical WAN handler wrote `nameserver 127.0.0.1` directly after seeing
dnsmasq and Unbound listeners.

The updated handler delegates resolver selection to DNS Guard instead:

1. apply DNS Guard immediately when WAN reports connected;
2. keep bootstrap DNS if the local stack is not ready;
3. give Entware/Unbound a bounded opportunity to settle;
4. re-evaluate DNS Guard after the local path is available;
5. restart Tailscale only after DNS policy application.

This removes the hard-coded local resolver decision from the WAN event path.

## Persistent watchdog

`services-start` creates a named `cru` job:

```text
AsusEdgeDNSGuard
```

The job evaluates `dns-guard auto` once per minute.

The watchdog is controlled by:

```sh
EDGE_DNS_GUARD_WATCHDOG="1"
```

and is recreated by the managed startup path after reboot.

## Validation

The implementation was validated in stages rather than by moving directly to a
cold reboot.

### Read-only readiness

The initial status-only guard confirmed:

- NTP ready;
- Unbound process/listener healthy;
- Pi-hole process/listener healthy;
- fresh Pi-hole query successful;
- production resolver unchanged.

### Controlled promote/fallback

A live runtime cycle completed successfully:

```text
WAN bootstrap DNS -> Pi-hole -> functional DNS query -> WAN bootstrap DNS
```

No NVRAM or WAN restart was involved.

### Break-glass priority

A test break-glass flag blocked local promotion, returned a non-zero promote
status, and preserved bootstrap DNS.

### Isolated WAN-handler integration

The production WAN handler was tested with temporary resolver and break-glass
paths plus a non-mutating Tailscale init substitute.

Observed results:

- normal policy selected Pi-hole;
- break-glass policy selected bootstrap DNS;
- the real resolver remained unchanged;
- the real Tailscale daemon PID remained unchanged.

### Fail-open policy

A test configuration replaced the Pi-hole address with a documentation-only
unreachable address. `dns-guard auto` returned
`AUTO=BOOTSTRAP_UNHEALTHY` and restored both bootstrap resolver entries.

### Real watchdog failover and recovery

With the production watchdog active:

1. a test break-glass flag was created while Pi-hole was the current resolver;
2. the cron watchdog automatically restored WAN bootstrap DNS;
3. the test flag was removed;
4. the watchdog automatically promoted the resolver back to Pi-hole.

Both transitions completed without manually invoking DNS Guard.

### Cold boot

A full router reboot was then performed.

Approximately two minutes after boot:

- Internet by IP was working;
- `ntp_ready=1`;
- Unbound was running;
- Pi-hole FTL was running;
- Tailscale was running;
- the watchdog entry had been recreated;
- DNS Guard reported all health checks passing;
- the system resolver had automatically reached the Pi-hole steady state;
- a normal system lookup through Pi-hole succeeded.

This validated that the original cold-boot deadlock was no longer present.

### Tailscale exit-node DNS

The final Android LTE test used the ASUS router as the selected Tailscale exit
node. Android routing showed Internet traffic using the Tailscale TUN
interface, and a fresh unique hostname resolved successfully.

A capture on all router interfaces showed the unique DNS query locally:

```text
192.168.50.1 -> 192.168.50.253:53
A? exitdns-final-<timestamp>.1-1-1-1.sslip.io
```

Pi-hole returned:

```text
A 1.1.1.1
```

The exchange appeared on loopback rather than `br0`, because Pi-hole's
dedicated LAN alias belongs to the same router.

This validates the tested exit-node DNS path:

```text
Android LTE
  -> Tailscale exit node
  -> router-side Tailscale DNS handling
  -> ASUS system resolver
  -> Pi-hole local alias
  -> Unbound
  -> recursive DNS
```

## Operational limitations

The validated result has explicit boundaries:

- the watchdog interval is one minute, so automatic failover is not
  instantaneous;
- bootstrap/fail-open DNS intentionally bypasses Pi-hole filtering while the
  local resolver stack is unhealthy;
- exit-node DNS reaches Pi-hole as router-originated traffic, so the original
  Android identity is not preserved at that hop;
- this case does not claim interception of application-specific DoH, DoT, or
  other encrypted DNS;
- the tests validate the reference ASUS/Entware deployment and do not claim
  identical startup ordering on other firmware or router models.

## Result

The incident changed the architecture from a fragile permanent dependency:

```text
router -> Pi-hole -> Unbound
```

into a two-phase resolver model:

```text
BOOT:
router -> independent WAN DNS

STEADY STATE:
router -> Pi-hole -> Unbound

LOCAL DNS FAILURE:
router -> independent WAN DNS

BREAK-GLASS:
router -> independent WAN DNS, automatic promotion blocked
```

DNS Guard v3.1 was production-validated through controlled failover, automatic
recovery, persistent watchdog recreation, full cold boot, and Android
Tailscale-exit-node DNS testing.
