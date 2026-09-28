# Diversion to Pi-hole on-router migration — ASUS TUF-AX5400

**Status:** adopted for the main LAN on 2026-09-28 after staged validation, controlled cutover, service cleanup and repeated reboot checks.

Tracking issue: #80.

## Executive summary

The reference ASUS TUF-AX5400 was migrated from Diversion-based DNS filtering to
Pi-hole running directly on the router through Entware. Unbound remains the
validating recursive resolver. Firmware dnsmasq remains responsible for DHCP,
local names and the existing project-owned classic-DNS interception path.

The migration was deliberately staged:

1. establish a dedicated Pi-hole listener without disturbing the known-good
   dnsmasq + Diversion path;
2. move one controlled client to Pi-hole;
3. compare blocking, latency, query visibility and resource use;
4. validate reboot persistence;
5. advertise Pi-hole to the main LAN through DHCP;
6. remove uiDivStats, Diversion, Stubby/DNS Privacy and an inactive NextDNS
   hook only after Pi-hole had passed functional checks;
7. correct a swap-startup regression discovered during the final reboot;
8. repeat the reboot and verify swap, Tailscale, Pi-hole, Unbound and DNS.

The final result is a simpler DNS/filtering stack with substantially better
per-client DNS observability while keeping Pi-hole FTL at roughly 10 MiB RSS in
the final post-reboot snapshot.

This case study is intentionally bounded. DHCP-managed main-LAN clients use
Pi-hole, but the existing project-owned interception of arbitrary external
classic DNS still terminates at firmware dnsmasq before Unbound. Equivalent
Pi-hole filtering for that interception path and for the existing Tailscale
classic-DNS redirect must be treated as a separate follow-up validation rather
than inferred from the LAN DHCP cutover.

## Before

```text
main-LAN clients
      |
      v
firmware dnsmasq :53 + Diversion
      |
      v
Unbound 127.0.0.1:53535
      |
      v
Internet
```

Supporting components included:

- uiDivStats for Diversion statistics;
- ASUS DNS Privacy / Stubby enabled even though the active dnsmasq upstream was
  already the local Unbound listener;
- an inactive historical NextDNS block in `dnsmasq.postconf`.

## After

```text
DHCP-managed main-LAN clients
      |
      v
Pi-hole FTL on a dedicated LAN alias :53
      |
      v
Unbound 127.0.0.1:53535
      |
      v
Internet

firmware dnsmasq
      |
      +-- DHCP
      +-- local names / reverse DNS
      +-- existing classic-DNS interception endpoint
      |
      v
Unbound 127.0.0.1:53535
```

Pi-hole DHCP remains disabled. The router continues to own DHCP and local
naming.

## Staging and socket ownership

A normal secondary IPv4 address on `br0` caused firmware dnsmasq to bind port
53 on that address automatically. The working staged design therefore used a
labelled alias dedicated to Pi-hole.

The validated ownership model was:

- Pi-hole FTL: dedicated LAN alias on TCP/UDP 53;
- Pi-hole web UI: dedicated LAN alias on a high local port;
- firmware dnsmasq: router LAN address and existing Tailscale listener on
  TCP/UDP 53;
- Unbound: loopback-only TCP/UDP 53535.

The alias is created by an Entware init script ordered immediately before the
Pi-hole FTL init script. A controlled reboot confirmed the alias appeared
before FTL started.

## Blocking-list parity

Both stacks were refreshed against the same OISD Big snapshot before the final
comparison.

Normalized domain counts:

| Dataset | Unique domains |
| --- | ---: |
| OISD source | 244,128 |
| Pi-hole Gravity | 244,128 |
| Diversion active blocking list | 244,126 |
| Common Diversion/Pi-hole | 244,126 |

The normalized Jaccard similarity was approximately **99.9992%**.

The two missing Diversion domains were not parser loss. Diversion's built-in
essential allowlist includes the corresponding parent domains
`sourceforge.net` and `openstreetmap.org`, so its final filtering pipeline
intentionally removes those two OISD entries. A live A/B lookup confirmed the
policy difference: Diversion resolved the two allowlisted subdomains while
Pi-hole returned its configured null-block response.

For the representative shared blocked names tested during the comparison,
Diversion returned `NXDOMAIN` while Pi-hole returned `NOERROR` with
`0.0.0.0`. Both outcomes prevented resolution to the real destination.

## Latency and functional comparison

The earlier corrected pilot benchmark used 200 queries per resolver per
scenario after removing a NAT-interception confounder:

| Scenario | Diversion mean / median | Pi-hole mean / median |
| --- | ---: | ---: |
| blocked test name | 0.54 / 0.50 ms | 0.87 / 1.00 ms |
| warmed clean name | 2.65 / 3.00 ms | 1.12 / 1.00 ms |

All 800 measured queries returned valid DNS responses. These measurements are
local, single-client results and are not a universal performance claim.

A separate normal-use Pi-hole window recorded 217 queries in roughly eleven
minutes:

- 154 forwarded to Unbound — 70.97%;
- 35 stale-cache answers — 16.13%;
- 18 normal cache answers — 8.29%;
- 6 Gravity blocks — 2.76%;
- 4 already-forwarded queries — 1.84%.

Local/cache/block handling averaged 0.201 ms in that window. Forwarded requests
averaged 65.693 ms, including upstream recursion and Internet latency.

A later Diversion normal-use window contained a different browsing workload and
therefore is **not** used as a direct block-rate comparison. It did, however,
confirm that the same representative blocklisted destinations were blocked by
both stacks.

## Query visibility

Pi-hole FTL stores normalized query history in SQLite and exposed, in the
tested build, client, domain, status, upstream and reply-time data through the
`queries` view.

This made it possible to answer operational questions directly:

```text
which client
  -> queried which domain
  -> when
  -> whether it was blocked, cached or forwarded
  -> which upstream handled it
  -> how long the answer took
```

The synthetic load tests also triggered Pi-hole's default per-client
1000-query/60-second rate limit. FTL logged the affected test client and later
ended rate limiting automatically. The limit was left unchanged for normal
operation.

## Resource observations

Representative final post-reboot process state:

| Process | RSS | Swap |
| --- | ---: | ---: |
| Pi-hole FTL | about 10 MiB | 0 |
| Unbound | about 17 MiB | 0 |
| tailscaled | about 37 MiB | 0 |

The same final checkpoint reported approximately 128 MiB memory available and
both configured swap files active, for about 2.5 GiB total swap capacity.

These values are point-in-time observations. They do not establish a universal
upper bound for future Gravity/database growth or every concurrent workload.

## Full-LAN DHCP cutover

The ASUS DHCP configuration initially appended the router itself as a secondary
DNS even when Pi-hole was configured as the preferred server. That would allow
clients to bypass Pi-hole.

The final design therefore uses a small managed `dnsmasq.postconf` override
that replaces the generated main-LAN DHCP option 6 with a single Pi-hole
address. A real Fedora DHCP renewal confirmed that only Pi-hole was learned by
the client.

The other router networks were left unchanged during this cutover.

## Local names and reverse DNS

Pi-hole keeps its own DHCP server disabled.

Conditional reverse DNS forwards the private LAN reverse zone to firmware
dnsmasq. A post-reboot test with an active DHCP lease returned the same local
hostname through both firmware dnsmasq and Pi-hole.

A previous test against an address whose lease no longer existed correctly
returned `NXDOMAIN`; this was not a Pi-hole failure.

## Removed duplicate services

After the main-LAN cutover was validated:

- uiDivStats background processing was disabled, its data was privately
  archived for rollback/evidence, and the addon was uninstalled;
- Diversion was uninstalled through its own supported removal path;
- ASUS DNS Privacy / Stubby was disabled after confirming the active resolver
  path did not use it;
- an inactive historical NextDNS block was removed from
  `dnsmasq.postconf`.

A reboot confirmed none of these components returned.

## Failure found during final reboot: swap ordering

The first post-cleanup reboot exposed a real startup regression:

- both swap files existed on the SSD;
- neither was active;
- the current `post-mount` hook only checked `/proc/swaps` but no longer
  executed `swapon`;
- Tailscale failed to start and the Go runtime reported an out-of-memory heap
  arena allocation failure.

Manually activating both existing swap files immediately allowed Tailscale to
start normally.

The persistent fix restored explicit per-volume `swapon` handling in
`post-mount` before the AMTM Entware startup path. A subsequent clean reboot
validated:

- both swap files active;
- Entware mounted;
- Tailscale started automatically;
- the Tailscale interface returned;
- the Pi-hole alias returned;
- Pi-hole FTL started;
- Unbound started;
- DHCP continued to advertise only Pi-hole;
- normal DNS resolution worked;
- the known blocked test returned the Pi-hole null block;
- the DNSSEC negative test returned `SERVFAIL`;
- reverse DNS worked for an active DHCP lease;
- removed services remained absent.

This failure/recovery sequence is part of the accepted case-study evidence,
rather than being hidden as an installation detail.

## Security and privacy boundaries

Public evidence does not include:

- real household query history;
- private client addresses or MAC addresses;
- private hostnames;
- Tailscale addresses or identities;
- WAN identifiers;
- raw router logs.

The Pi-hole UI is not exposed to WAN. The staged pilot initially used relaxed
UI authentication for a short controlled test; public documentation does not
treat that pilot condition as a general security recommendation.

Pi-hole does not solve DoH/DoQ/VPN-carried resolver bypass by itself. Issue #68
remains the measurement-first encrypted-DNS assessment.

## Known limitation: classic-DNS interception path

The migration changes the DNS server advertised to main-LAN DHCP clients.

The existing project firewall still has a separate classic-DNS enforcement
path. Queries intentionally sent to other TCP/UDP 53 destinations are
intercepted and delivered to firmware dnsmasq, which forwards to Unbound.

Therefore this case study **does not claim** that every hard-coded classic-DNS
query or the existing Tailscale DNS redirect is filtered by Pi-hole. A future
change may align those interception paths with Pi-hole, but it requires its own
firewall, listener, rollback and live datapath validation.

## Decision

Pi-hole was adopted for the reference main LAN because the tested deployment
provided:

- essentially identical OISD coverage to the previous Diversion stack;
- materially better per-client query visibility and history;
- acceptable observed memory use on the 512 MiB router;
- preserved Unbound/DNSSEC behavior;
- preserved firmware DHCP and local-name functions;
- clean reboot persistence after the swap-order regression was corrected;
- a simpler active service set after removing duplicated filtering/statistics
  components.

The decision is bounded to the validated main-LAN DHCP path and the observed
reference-router workload. It is not a claim of universal Pi-hole superiority,
perfect ad blocking, or complete encrypted-DNS enforcement.

## Related evidence

- [Single-client pilot validation](../evidence/2026-09-28/pi-hole-single-client-pilot-validation.md)
- [Main-LAN cutover and final reboot validation](../evidence/2026-09-28/pi-hole-main-lan-cutover-validation.md)
- [Case-study plan / acceptance criteria](pi-hole-on-router-case-study-plan.md)
