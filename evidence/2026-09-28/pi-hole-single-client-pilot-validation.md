# Pi-hole single-client pilot validation — 2026-09-28

## Scope

This artifact records a controlled **single-client Pi-hole pilot** on the
reference ASUS TUF-AX5400. It does not claim a full-LAN migration or Diversion
replacement.

Public evidence intentionally omits the controlled client's address, raw
household DNS history, private hostnames and Tailscale identity data.

## Staged architecture

```text
controlled Fedora client
        |
        v
dedicated Pi-hole LAN alias :53
        |
        v
Pi-hole FTL / Gravity
        |
        v
Unbound 127.0.0.1:53535
        |
        v
Internet

router LAN address :53
        |
        v
firmware dnsmasq + Diversion
        |
        v
Unbound 127.0.0.1:53535
```

Pi-hole DHCP remained disabled. The existing firmware dnsmasq/Diversion path
remained available for rollback and for clients not explicitly moved to the
pilot.

## Firewall integration finding

The existing project-owned LAN classic-DNS enforcement chain redirected
arbitrary TCP/UDP 53 traffic to the router-local resolver. That also intercepted
traffic intentionally addressed to the staged Pi-hole listener.

The pilot therefore introduced a configurable
`EDGE_LAN_DNS_BYPASS_IPS` allowlist. Matching UDP/TCP 53 destinations return
from the project NAT chain **before** the generic redirect rule. The health
check validates both the exact rule count and the required rule ordering.

This preserves classic-DNS enforcement for arbitrary external resolver
destinations while allowing explicitly configured local resolver aliases.

## Reboot / persistence validation

A controlled router reboot validated that:

- the dedicated Pi-hole LAN alias returned automatically;
- Pi-hole FTL returned automatically;
- Pi-hole owned only the dedicated alias on TCP/UDP 53;
- the Pi-hole web listener returned on the dedicated alias and its configured
  high port;
- firmware dnsmasq continued to own the router LAN address on TCP/UDP 53;
- Unbound remained on `127.0.0.1:53535`;
- the Gravity database remained populated with the selected OISD list;
- the six-rule managed LAN DNS policy returned automatically;
- the project health check completed with **0 failures and 0 warnings**;
- the controlled Fedora client was observed in the Pi-hole query log after the
  reboot;
- a blocked test domain returned the Pi-hole null-block response;
- an allowed unique test name was forwarded by Pi-hole to Unbound.

The Pi-hole administration UI was reachable only on the staged LAN listener
during this pilot. Authentication was intentionally left disabled for the
short controlled test; that is a pilot limitation and is **not** an accepted
broader-deployment posture.

## Corrected Diversion vs Pi-hole latency benchmark

The first exploratory Fedora comparison was discarded because the project NAT
redirect transparently intercepted the intended Pi-hole destination. The
benchmark below was run only after the explicit local-resolver bypass was
validated.

Method:

- 200 queries per resolver per scenario;
- blocked-domain scenario used the same known blocklist test name on both
  resolvers;
- clean scenario used `example.com`;
- query order alternated to reduce ordering bias;
- both clean paths were warmed before the cached clean run;
- all 800 measured queries returned a valid DNS response.

| Scenario | Resolver | Valid | Mean | Median | p95 | p99 | Max | DNS status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| blocked | Diversion | 200 | 0.54 ms | 0.50 ms | 1 ms | 3 ms | 3 ms | NXDOMAIN |
| blocked | Pi-hole | 200 | 0.87 ms | 1.00 ms | 1 ms | 3 ms | 3 ms | NOERROR / null block |
| clean cached | Diversion | 200 | 2.65 ms | 3.00 ms | 3 ms | 4 ms | 9 ms | NOERROR |
| clean cached | Pi-hole | 200 | 1.12 ms | 1.00 ms | 2 ms | 2 ms | 3 ms | NOERROR |

Observed interpretation is intentionally narrow:

- both stacks completed all measured queries successfully;
- Diversion was lower-latency for the selected blocked-name test;
- Pi-hole was lower-latency for the selected warmed clean-name test;
- these figures are local single-client measurements, not proof of universal
  resolver performance;
- they do not cover uncached random-name resolution, concurrent multi-client
  load, WAN reconnect, database-write cost, or sustained stress.

## Post-benchmark resource snapshot

After the benchmark:

| Process | RSS | Swap | Threads |
| --- | ---: | ---: | ---: |
| Pi-hole FTL | 10,948 kB | 0 kB | 16 |
| Unbound | 17,332 kB | 0 kB | 1 |
| dnsmasq process A | 11,752 kB | 0 kB | 1 |
| dnsmasq process B | 12,964 kB | 0 kB | 1 |
| tailscaled | 36,520 kB | 0 kB | 9 |

Router memory snapshot after the run:

- free: 29,856 kB;
- available after buffers/cache: 167,008 kB;
- swap in use: 868 kB of 2,621,432 kB;
- Pi-hole FTL itself had **0 kB swap**.

The retained transcript for this artifact contains the post-run resource
snapshot but not the immediately preceding resource table, so this artifact
does **not** claim an exact benchmark-induced memory delta.

## Health result

The final project health check after the benchmark reported:

```text
Summary: 0 failure(s), 0 warning(s)
```

The validated checks included Tailscale ownership, exit-node forwarding
prerequisites, dnsmasq interface configuration, project firewall chains,
LAN classic-DNS enforcement, LAN DoT blocking, Unbound reachability/DNSSEC,
IPv6 guards and syslog-ng.

## Current decision boundary

The single-client pilot and reboot persistence test pass.

This is **not yet** approval for a full-LAN cutover. Remaining case-study work
includes at minimum:

- multi-client / concurrent-load testing;
- Gravity/update peak-resource observation;
- query-database growth / storage-write observation;
- WAN reconnect validation;
- local-name and reverse-DNS behavior under the final design;
- IPv6 and Tailscale behavior for the candidate listener design;
- explicit rollback rehearsal;
- broader normal-use / false-positive evaluation.

Issue #80 remains the tracking item for the final Diversion-vs-Pi-hole decision.
