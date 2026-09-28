# Network DNS Visibility / Client Activity Analytics

**Status:** Phase 0 read-only preflight and Phase 1 Fedora collector live validation passed on 2026-09-28. Loki/Alloy ingestion, longer-term retention/storage validation and the Grafana DNS dashboard remain pending.

Tracking issue: #108.

## Goal

Extend the existing edge-gateway observability stack with privacy-conscious,
domain-level DNS activity analytics for the **Pi-hole-filtered main-LAN path**.

The primary source is no longer planned dnsmasq query logging. The adopted
main-LAN resolver already stores normalized query history in Pi-hole FTL, so the
preferred design is to reuse that data read-only and keep parsing, indexing,
retention and visualization on Fedora.

The module is intended to answer questions such as:

- which domains were queried;
- when queries occurred;
- which controlled local client generated them;
- which DNS record types are common;
- whether a request was blocked, cached or forwarded where Pi-hole records that state;
- which upstream handled an allowed query where that field is available;
- which clients or domains generate unusual query volume;
- where visibility disappears because traffic does not traverse Pi-hole.

This is **resolver visibility**, not complete browser history.

## Current source-of-truth boundary

The current reference DNS architecture is split:

```text
DHCP-managed main-LAN client
        |
        v
Pi-hole FTL :53
        |
        v
Unbound 127.0.0.1:53535
        |
        v
recursive / authoritative DNS

hard-coded external classic DNS on LAN
        |
        v
project interception
        |
        v
firmware dnsmasq :53
        |
        v
Unbound

Tailscale classic-DNS redirect
        |
        v
firmware dnsmasq :53
        |
        v
Unbound
```

The 2026-09-28 migration already validated that Pi-hole FTL stores query history
including client, domain, status, upstream and reply-time information in the
tested build.

Therefore the first analytics phase is intentionally scoped to the
**DHCP-managed main-LAN traffic that actually traverses Pi-hole**.

The project must not claim that the Pi-hole dataset automatically includes:

- hard-coded external classic-DNS queries currently intercepted to firmware dnsmasq;
- the existing Tailscale classic-DNS redirect;
- direct DoT attempts rejected by the firewall;
- DoH/HTTPS;
- DoQ/QUIC;
- VPN-carried resolver traffic;
- application-specific encrypted resolvers;
- unvalidated IPv6 resolver paths.

Those gaps are coverage facts, not failures of the analytics backend.

## Privacy boundary

DNS metadata can reveal sensitive browsing and application activity even though
it does not contain full HTTPS URLs.

The module must not rely on HTTPS interception.

Out of scope:

- TLS MITM;
- installing a traffic-decryption CA on household clients;
- full HTTPS URLs or URL paths;
- page contents;
- request bodies;
- cookies;
- credentials;
- routine payload capture.

Raw Pi-hole query history, real household client identifiers and personal
domain activity remain private operational data.

Public evidence must use controlled synthetic domains/clients, aggregates or
manually sanitized extracts. The live Pi-hole database must never be committed
to the public repository.

## Preferred architecture

```text
DHCP-managed main-LAN clients
        |
        v
Pi-hole FTL
        |
        v
Pi-hole query-history database on router SSD
        |
        | read-only, bounded extraction
        | no new public/network-facing analytics listener
        v
Fedora collector / normalizer
        |
        | local structured event file/stream
        v
Grafana Alloy
        |
        v
Loki
        |
        v
existing Grafana
```

The design deliberately keeps indexing, retention, querying and visualization
off the 512 MiB router.

The existing syslog-ng + Tailscale + mTLS pipeline remains the validated system
logging path. It is **not the preferred primary source for Pi-hole DNS activity
analytics** after the migration. It may later provide supplemental dnsmasq
interception-path evidence if a measured coverage gap justifies it.

## Acquisition design principles

The preferred collector should:

- read Pi-hole query history without modifying it;
- avoid copying the live database as a normal ingestion mechanism;
- avoid enabling broad dnsmasq query logging solely for analytics;
- avoid adding a second network-facing listener to the router;
- extract incrementally so the same query is not ingested repeatedly;
- retain a stable cursor/checkpoint on Fedora, not in the public repository;
- tolerate collector downtime and resume without silently duplicating large windows;
- keep router CPU, RAM and SSD I/O impact bounded and measured.

Phase 0 selected the supported Pi-hole v6 HTTP API instead of direct SQLite
access. The API is reached from Fedora through a loopback-only SSH local
forward, so the application password and session ID are not sent as cleartext
HTTP across the LAN. No new Pi-hole listener was added.

The validated collector model uses the first query ID actually returned by each
source as that source's frozen pagination cursor. This is important for
`disk=true`: the response-level cursor is global and can be newer than the
latest row already flushed to disk. The collector therefore unions the
source-local disk snapshot with the current in-memory snapshot and deduplicates
by query ID before advancing its Fedora-side checkpoint.

## Phase 0 — read-only Pi-hole preflight

Before installing Loki/Alloy or changing router configuration, complete this phase against the deployed Pi-hole build and record sanitized evidence:

1. identify the exact Pi-hole FTL database location and owner/mode;
2. confirm the live schema/view needed for timestamp, client, domain, query
   type, status, upstream and reply time;
3. verify a read-only query method while FTL is active;
4. measure the query rate and approximate extraction volume during a bounded
   normal-use window;
5. verify that at least two controlled main-LAN clients are distinguishable;
6. measure CPU/RAM/latency impact of a small read-only extraction;
7. define a monotonic cursor or equivalent incremental-ingestion key;
8. confirm which fields can be normalized without publishing private data.

No Loki, Alloy or router-side logging change is required to complete this phase. A failed or ambiguous schema/read-safety preflight blocks later analytics deployment rather than being worked around with broad router query logging.

### Phase 0 result — PASS

Sanitized live evidence is published in
[`evidence/2026-09-28/pi-hole-api-phase0-preflight.md`](../evidence/2026-09-28/pi-hole-api-phase0-preflight.md).

The deployed Pi-hole v6 API exposed the required timestamp, client, domain,
query type, status, upstream and reply-time fields. A dedicated application
password authenticated successfully with `webserver.api.app_sudo=false`.

A 100-row read from memory completed in about 15.6 ms wall time and a 100-row
`disk=true` read in about 15.2 ms. FTL process swap remained zero and the
bounded test changed FTL CPU accounting by two ticks. This is evidence for the
tested sample only, not a long-running performance claim.

The preflight also reproduced a 13-query RAM/disk head gap and demonstrated why
the global response cursor cannot be used blindly as the first disk checkpoint.


## Phase 1 — bounded Fedora collector

A reference implementation now exists at
[`monitoring/pihole-dns-collector.py`](../monitoring/pihole-dns-collector.py),
with systemd user units and a sanitized configuration example under
`monitoring/`. Repository tests cover the RAM/disk cursor edge case,
deduplication and prepared-batch crash recovery.

Live Fedora deployment and short transport-outage recovery have now been
validated. The collector recovered a real prepared batch after the first-run
bug fixed by PR #120, then maintained a duplicate-free strictly ascending event
stream through manual and timer-driven runs.

During a controlled SSH-tunnel outage, the collector returned non-zero without
advancing the accepted event file. After transport restoration it caught up
from the Pi-hole disk and memory views. The final integrity checkpoint reported
10,414 events, 10,414 unique IDs, zero duplicates and a local checkpoint equal
to the maximum event ID.

Sanitized evidence is published in
[`evidence/2026-09-28/pi-hole-dns-collector-live-validation.md`](../evidence/2026-09-28/pi-hole-dns-collector-live-validation.md).

Implement the smallest practical collector on Fedora.

Responsibilities:

- execute the approved read-only Pi-hole query;
- request only records newer than the saved checkpoint;
- normalize timestamps and selected fields;
- write structured local events suitable for Alloy;
- update the checkpoint only after successful local persistence;
- log collector health without logging unrelated household DNS activity;
- fail closed on schema mismatch rather than silently mis-parsing fields.

The collector must not modify Pi-hole configuration, Gravity, FTL state or the
query database.

## Phase 2 — Fedora analytics backend

Planned components:

- Grafana Alloy for local ingestion;
- Loki for local log storage/query;
- the existing Grafana instance for visualization.

Loki and Alloy remain off-router and should bind locally unless a separately
reviewed access requirement is introduced.

### Label-cardinality rule

Do **not** use full domain names, client IP addresses, hostnames or request IDs
as persistent Loki labels.

Prefer low-cardinality labels such as:

- source = `pihole`;
- job = `dns-activity`;
- resolver path / dataset role;
- DNS query type only if measured cardinality remains bounded;
- coarse status class where useful.

Client/domain values should remain parsed fields available at query time.

## Phase 3 — Grafana dashboard

Planned views for the Pi-hole-visible dataset:

- DNS queries over time;
- top queried domains;
- query volume by controlled client;
- DNS record types;
- blocked / cached / forwarded status;
- selected upstream distribution where available;
- reply-time distribution;
- clients with unusual query-rate spikes;
- recent DNS activity;
- an explicit coverage panel describing traffic not represented by Pi-hole.

The dashboard title and descriptions must make the scope obvious:
**Pi-hole-visible DNS activity**, not complete household web history.

## Phase 4 — coverage-gap correlation

After the Pi-hole-visible baseline works, correlate it with the actual resolver
architecture.

Required questions:

1. What happens when a LAN client deliberately sends classic DNS to another
   resolver and the firewall redirects it to firmware dnsmasq?
2. What happens on the existing Tailscale classic-DNS redirect?
3. Can those paths be represented safely as a supplemental dataset without
   enabling broad duplicate query logging?
4. Would moving those paths behind Pi-hole improve consistency enough to justify
   a firewall/listener change and new live revalidation?

This phase must remain separate from the initial analytics rollout. A dashboard
must not be used as justification to change a validated DNS datapath merely to
make the data easier to collect.

## Phase 5 — encrypted-DNS visibility assessment

This module is intentionally linked to issue #68.

The measurement-first bypass assessment should test:

- browser/application DoH;
- DoQ / QUIC;
- application-specific encrypted resolver paths;
- VPN-carried DNS;
- relevant IPv6 resolver paths.

If an event disappears from the Pi-hole-visible dataset because the application
uses an encrypted resolver, that absence is itself a useful finding when it is
demonstrated with a controlled test.

Enforcement, if ever adopted, is a later decision after measurement,
false-positive analysis and rollback planning.

## Phase 6 — retention and resilience

Before calling the module complete:

- define bounded local Loki retention for DNS activity separately from generic
  infrastructure metrics/logs;
- measure storage growth from real query volume;
- validate collector restart and host reboot persistence;
- validate checkpoint recovery after a short collector outage;
- confirm that duplicate ingestion remains bounded;
- document rollback/uninstall for the Fedora collector, Alloy and Loki changes;
- document any private client-to-alias mapping outside public evidence.

The first pilot should use deliberately short retention until storage growth and
privacy expectations are measured.

## Acceptance criteria

The module can be marked completed only when:

1. DNS events from at least two controlled DHCP-managed main-LAN clients are
   distinguishable in the Pi-hole-visible dataset.
2. Timestamp, client, domain and query type are parsed reliably.
3. Block/cache/forward status is represented only where the Pi-hole source
   supports it reliably.
4. Collection is read-only and does not require a new router-facing analytics
   listener.
5. Loki/Alloy storage and ingestion remain off-router.
6. Grafana can show time-series and client/domain activity from the controlled
   dataset.
7. High-cardinality domain/client values are not persistent Loki labels.
8. No HTTPS interception is used.
9. The dashboard explicitly documents dnsmasq interception, Tailscale and
   encrypted-DNS visibility gaps.
10. Public evidence is sanitized and does not include the live Pi-hole database
    or real household browsing history.
11. Router resource impact, Fedora storage growth and retention are documented.
12. Collector restart/outage recovery and rollback are tested.

## Portfolio value

The completed module would extend the project from infrastructure monitoring
into lightweight network-activity analytics:

```text
edge security
+ metrics
+ alerting
+ centralized system logs
+ Pi-hole DNS activity analytics
```

The portfolio claim must remain bounded: this is a home/SOHO resolver-telemetry
pipeline, not full web-history capture, TLS inspection, enterprise NDR or a
complete record of all client traffic.
