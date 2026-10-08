> **COMPLETED / HISTORICAL — 2026-10-06.** This case study preserves
> the original v3.1 incident and test results. Current DNS Guard v3.2 was
> merged in [PR #197](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/197)
> on 2026-10-08. See [v3.2 live acceptance and remaining limitations](../dns-guard-v3.2-recovery-audit-live-validation.md).
> Do not interpret the dated v3.1 tests as coverage of v3.2 fault branches.

# Case study: DNS bootstrap deadlock on Asuswrt-Merlin and recovery with DNS Guard v3.1

**Incident date:** 2026-10-06  
**Platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton  
**Scope:** router system DNS, Pi-hole, Unbound, NTP bootstrap, Tailscale exit-node DNS  
**Outcome:** resolved and production-validated

## Executive summary

A resolver change that worked correctly on an already initialized router caused
a real cold-boot outage after reboot.

The ASUS system resolver had been pointed at the local Pi-hole instance so
Tailscale exit-node DNS would follow the intended filtered path. At runtime the
design worked. After reboot, however, normal websites stopped opening because
new hostname lookups failed even though basic IP connectivity remained
available.

The failure was not a Tailscale regression. It was a boot-time dependency cycle:

~~~text
router system resolver
        |
        v
     Pi-hole
        |
        v
     Unbound
        |
        +---- waits for NTP readiness
                    |
                    v
              NTP needs DNS
~~~

The remediation was **DNS Guard v3.1**, which separates bootstrap DNS from the
steady-state filtered resolver path.

The final model is:

~~~text
BOOT / LOCAL DNS FAILURE / BREAK-GLASS
router -> independent WAN DNS

HEALTHY STEADY STATE
router -> Pi-hole -> Unbound
~~~

The implementation was validated through controlled promotion and fallback,
sticky break-glass, watchdog recovery, a full cold reboot, and an Android LTE
Tailscale exit-node DNS test captured on the router.

## Why this incident mattered

The failure was operationally significant because the router still had network
connectivity by IP while DNS was unavailable.

From a user perspective the effect was simple:

- websites did not open normally;
- applications that required fresh hostname resolution failed or appeared to
  have no Internet access;
- the underlying WAN/IP path was not the primary fault.

This distinction mattered during troubleshooting. A successful ping to an IP
address would not prove the browsing path was healthy.

The incident also exposed an important architecture lesson: a resolver that is
safe as a **steady-state dependency** is not automatically safe as a
**bootstrap dependency**.

## Environment

The incident involved the following reference components:

- ASUS TUF-AX5400 running Asuswrt-Merlin/GNUton;
- Entware on external SSD storage;
- Pi-hole FTL on a dedicated local LAN alias, TCP/UDP 53;
- Unbound on 127.0.0.1:53535;
- Pi-hole using Unbound as its upstream resolver;
- firmware NTP using hostname-based servers;
- Tailscale configured as a subnet router and exit node;
- project-owned service/WAN hooks under /jffs/addons/asus-edge;
- Tailscale running with netfilter-mode=off, leaving firewall ownership to
  the project.

Deployment-specific public addresses and credentials are intentionally omitted.

## Change that triggered the outage

The project was validating the DNS path used by an Android client on LTE while
the ASUS router was selected as the Tailscale exit node.

A runtime experiment showed that making the router system resolver use Pi-hole
produced the desired path:

~~~text
Android LTE
  -> Tailscale exit node
  -> router-side Tailscale DNS handling
  -> ASUS system resolver
  -> Pi-hole
  -> Unbound
~~~

Because the runtime result was correct, the resolver policy was then made
persistent and the router was rebooted.

The mistake was assuming that a configuration proven after all services were
healthy would also be safe during cold-start ordering.

## Incident symptoms

After the reboot the reference environment showed:

- working IP connectivity;
- failed DNS resolution;
- normal websites not opening because names could not be resolved;
- Pi-hole without a usable upstream resolver;
- Unbound waiting for firmware NTP readiness.

The outage was therefore not a complete WAN failure. It was a name-resolution
failure caused by startup ordering.

## Diagnosis

The troubleshooting sequence separated network reachability from DNS
availability.

### 1. Verify that the WAN/IP dataplane still exists

The router retained basic IP connectivity. That ruled out a generic WAN outage
as the primary cause.

### 2. Inspect the router resolver path

The router had been configured to depend on Pi-hole for its own DNS.

That meant firmware services required the local DNS stack to be available before
they could resolve external hostnames.

### 3. Inspect Pi-hole upstream ownership

Pi-hole was configured to forward ordinary external queries to:

~~~text
127.0.0.1:53535
~~~

which is the local Unbound instance.

### 4. Inspect Unbound startup behavior

The Entware Unbound startup path deliberately waited until:

~~~text
ntp_ready=1
~~~

before completing startup.

### 5. Inspect NTP bootstrap requirements

Firmware NTP used hostname-based servers.

Therefore NTP itself required working DNS before the condition needed by
Unbound could become true.

## Root cause

The directly observed dependency chain was:

~~~text
router DNS
   |
   v
Pi-hole
   |
   v
Unbound
   |
   +---- waits for NTP
               |
               v
          NTP requires DNS
~~~

This created a circular boot dependency:

1. the router needed DNS to resolve the NTP host;
2. the router sent DNS to Pi-hole;
3. Pi-hole needed Unbound;
4. Unbound waited for NTP;
5. NTP could not complete because DNS was not usable.

The root cause was therefore an **architecture and startup-order defect in the
local resolver design**, not a failure in the Tailscale upgrade.

## Immediate recovery

The emergency recovery restored independent WAN DNS for the router bootstrap
path.

That broke the cycle:

~~~text
router -> WAN DNS -> NTP ready -> Unbound starts -> Pi-hole gets upstream
~~~

Once the local stack was healthy again, Pi-hole could safely become the
router's steady-state resolver.

The recovery also established the core design rule used in the permanent fix:

> Bootstrap DNS must not depend on services whose own startup depends on DNS or
> time synchronization.

## Permanent remediation: DNS Guard v3.1

The final design separates the router resolver into two phases.

### Bootstrap phase

During cold boot, local resolver failure, or explicit break-glass:

~~~text
router -> current WAN DNS
~~~

This path is independent of Pi-hole and Unbound.

### Healthy steady state

Only after the complete local stack is ready:

~~~text
router -> Pi-hole -> Unbound
~~~

DNS Guard therefore changes only the **runtime resolver state**. It does not
make Pi-hole the unavoidable bootstrap dependency.

## Promotion health contract

DNS Guard promotes the router to Pi-hole only when all required conditions are
true:

- firmware reports ntp_ready=1;
- the Unbound process is running;
- Unbound is listening on the expected loopback port;
- Pi-hole FTL is running;
- the Pi-hole listener exists;
- a fresh functional query through Pi-hole returns the expected result.

A running process alone is not treated as proof that the resolver path works.

## Fail-open behavior

If any health condition fails, DNS Guard restores current WAN bootstrap DNS.

This is an intentional availability decision:

~~~text
local filtering unavailable
        |
        v
keep DNS working through WAN bootstrap resolvers
~~~

The design therefore fails open for DNS availability rather than failing dead
and making ordinary browsing impossible.

The trade-off is explicit: while fail-open is active, router-originated DNS
does not receive Pi-hole filtering.

## Sticky break-glass

DNS Guard includes a persistent emergency state.

breakglass-on:

- creates a sticky state flag;
- restores WAN bootstrap DNS;
- prevents automatic promotion back to Pi-hole.

breakglass-off:

- clears the operator override;
- allows normal automatic health-based promotion again.

The separate recovery helper router/scripts/edge-dns-breakglass.sh also ensures
automatic WAN DNS mode is available before recovery proceeds.

## Idempotency defect found during implementation

Testing DNS Guard v3.1 exposed a second, smaller bug before production reboot
validation.

When the resolver was already in bootstrap state, the internal write helper
returned a dedicated no-change status. The wrapper incorrectly converted that
into:

~~~text
FALLBACK=FAILED
~~~

even though the system was already in the requested safe state.

The implementation was corrected so that both states are successful no-ops:

~~~text
PROMOTE=ALREADY_LOCAL
FALLBACK=ALREADY_BOOTSTRAP
~~~

This matters because watchdog-style control loops must be idempotent.

## WAN-event integration

The historical WAN handler directly wrote a local resolver decision after
seeing dnsmasq and Unbound listeners.

The corrected sequence delegates policy to DNS Guard:

~~~text
WAN connected
   |
   v
DNS Guard auto
   |
   +-- local stack not ready -> keep WAN bootstrap DNS
   |
   +-- local stack healthy   -> use Pi-hole
   |
   v
bounded settle/re-evaluation
   |
   v
restart/recover Tailscale after DNS policy
~~~

This removes resolver policy from ad-hoc WAN hook logic.

## Persistent watchdog

services-start recreates the named cron job:

~~~text
AsusEdgeDNSGuard
~~~

The production watchdog evaluates:

~~~sh
/jffs/addons/asus-edge/bin/dns-guard auto
~~~

once per minute.

This provides automatic fallback and recovery after boot as well as during
later local DNS failures.

## Validation strategy

The fix was not accepted after a single successful lookup. It was validated in
stages.

| Test | Expected result | Outcome |
| --- | --- | --- |
| Read-only readiness | observe health without mutating resolver | PASS |
| Promote | WAN bootstrap -> Pi-hole | PASS |
| Idempotent promote | already-local is a safe no-op | PASS |
| Fallback | Pi-hole -> WAN bootstrap | PASS |
| Idempotent fallback | already-bootstrap is a safe no-op | PASS |
| Break-glass | block automatic promotion | PASS |
| Unhealthy Pi-hole simulation | fail open to WAN DNS | PASS |
| WAN-handler integration | preserve the same policy | PASS |
| Real watchdog fallback | automatic recovery to WAN DNS | PASS |
| Real watchdog recovery | automatic return to Pi-hole | PASS |
| Full cold reboot | no DNS/NTP/Unbound deadlock | PASS |
| Android LTE + ASUS Exit Node DNS | router DNS reaches Pi-hole | PASS |

## Full cold-boot acceptance

A complete router reboot was the decisive test.

At approximately two minutes after boot:

~~~text
ntp_ready=1
UNBOUND=RUNNING
PIHOLE=RUNNING
TAILSCALE=RUNNING
BREAKGLASS=INACTIVE
NTP=PASS
UNBOUND=PASS
PIHOLE_LISTENER=PASS
PIHOLE_QUERY=PASS
DECISION=LOCAL_DNS_READY
~~~

The watchdog had been recreated and the router had automatically reached the
Pi-hole steady-state resolver.

Normal DNS resolution worked again after reboot, so the original condition in
which ordinary websites failed to open was no longer present.

## End-to-end Tailscale exit-node DNS proof

The final validation used an Android client with:

~~~text
Wi-Fi:      OFF
LTE/5G:     ON
Tailscale:  ON
Exit node:  ASUS
~~~

A fresh unique hostname was generated to avoid relying on a stale cache.

A capture on all router interfaces showed:

~~~text
192.168.50.1 -> 192.168.50.253:53
A? exitdns-final-<timestamp>.1-1-1-1.sslip.io
~~~

Pi-hole returned:

~~~text
A 1.1.1.1
~~~

The exchange appeared on loopback because the Pi-hole alias is local to the
same router.

This validated the tested path:

~~~text
Android LTE
  -> Tailscale
  -> ASUS exit node
  -> router-side Tailscale DNS handling
  -> ASUS system resolver
  -> Pi-hole
  -> Unbound
  -> recursive DNS
~~~

## Before and after

### Before

~~~text
COLD BOOT
router system DNS -> Pi-hole -> Unbound
                              |
                              +--> waits for NTP
                                      |
                                      +--> requires DNS

Result:
IP connectivity available
DNS unavailable
normal websites fail to open
~~~

### After

~~~text
COLD BOOT
router -> independent WAN DNS
            |
            +--> NTP becomes ready
                    |
                    +--> Unbound starts
                            |
                            +--> Pi-hole becomes healthy
                                    |
                                    +--> DNS Guard promotes router to Pi-hole
~~~

Failure state:

~~~text
Pi-hole / Unbound unhealthy
        |
        v
DNS Guard -> WAN bootstrap DNS
~~~

Manual emergency state:

~~~text
break-glass active
        |
        v
WAN bootstrap DNS
automatic Pi-hole promotion blocked
~~~

## Engineering lessons learned

### 1. Runtime success does not prove boot safety

The original Pi-hole resolver configuration worked when NTP, Unbound and
Pi-hole were already healthy.

The failure appeared only after a true cold reboot.

Any infrastructure change that affects DNS, storage, time, authentication or
service ordering needs a reboot-path test before being treated as production
safe.

### 2. Bootstrap dependencies must remain independent

A bootstrap resolver should not depend on services that themselves need DNS,
time synchronization, mounted storage, or network identity to start.

The project now treats WAN DNS as a separate bootstrap dependency instead of a
fallback added after the fact.

### 3. Health must test function, not only process presence

A process existing or a port being open is not sufficient proof that the whole
DNS chain works.

The final promotion contract requires a fresh successful query through Pi-hole.

### 4. Recovery loops must be idempotent

Periodic automation will encounter states that are already correct.

ALREADY_LOCAL and ALREADY_BOOTSTRAP are normal success states, not errors.

### 5. Fail-open versus fail-closed must be an explicit design decision

For router-originated bootstrap DNS, availability was prioritized:

~~~text
local DNS failure -> WAN DNS
~~~

For firewall authorization, the project may make the opposite decision and fail
closed.

The desired failure mode depends on the security property being protected.

### 6. Packet capture should follow the actual ownership boundary

The final Pi-hole exchange was visible on loopback, not on br0.

The reason was architectural rather than anomalous: both the system resolver and
Pi-hole alias were local to the ASUS router.

### 7. User-visible symptoms matter in incident documentation

The incident was not merely "Pi-hole unhealthy".

Its practical symptom was that **normal websites stopped opening** even though
the underlying IP path remained available.

Recording the user-visible impact makes the technical root cause easier to
understand and prevents later documentation from understating the outage.

## Operational trade-offs and limitations

The final design has known boundaries:

- the watchdog runs once per minute, so automatic failover is not instantaneous;
- fail-open WAN DNS intentionally bypasses Pi-hole filtering while the local DNS
  stack is unhealthy;
- exit-node DNS reaches Pi-hole as router-originated traffic, so the original
  Android source identity is not preserved at that hop;
- this case study does not claim interception of arbitrary application DoH,
  DoT, DoQ or VPN-carried DNS;
- the validation applies to the reference ASUS/Entware environment and does not
  prove identical service ordering on another router or firmware family;
- future migration to RT-BE88U / Asuswrt-Merlin 3006.x requires this boot
  contract to be revalidated rather than assumed.

## Result

The incident changed the DNS architecture from a fragile circular dependency
into a two-phase resolver state machine with automated recovery.

Final policy:

~~~text
BOOT:
router -> independent WAN DNS

STEADY STATE:
router -> Pi-hole -> Unbound

LOCAL DNS FAILURE:
router -> independent WAN DNS

BREAK-GLASS:
router -> independent WAN DNS
automatic Pi-hole promotion blocked
~~~

The fix was accepted only after controlled fault injection, real watchdog
transitions, a full cold reboot and end-to-end Android Tailscale exit-node DNS
validation.

## Traceability

Implementation and evidence:

- [DNS Guard implementation](../../router/scripts/dns-guard)
- [Boot and service dependency flow](../architecture/boot-service-dependency-flow.md)
- [DNS enforcement flow](../architecture/dns-enforcement-flow.md)
- [DNS Guard v3.1 production validation](../../evidence/2026-10-06/dns-guard-v3.1-production-validation.md)
- [2026-10-06 worklog](../worklog/2026-10-06.md)
