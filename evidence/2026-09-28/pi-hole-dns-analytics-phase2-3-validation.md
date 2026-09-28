# Pi-hole DNS analytics Phase 2/3 live validation — 2026-09-28

## Scope

This evidence records the live Fedora deployment of the local Alloy/Loki
analytics backend and the first Grafana DNS-activity dashboard for issue #108.

The evidence is sanitized. It does not publish household domains, client IP
addresses, hostnames, raw NDJSON lines, credentials or screenshots containing
private DNS activity.

## Components

Validated Fedora packages:

```text
Loki  3.7.8 x86_64
Alloy 1.20.0 x86_64
Grafana 13.2.2
```

The validated listener boundary is loopback-only:

```text
127.0.0.1:12345 -> Alloy HTTP/UI
127.0.0.1:3100  -> Loki HTTP
127.0.0.1:9096  -> Loki gRPC
127.0.0.1:3000  -> Grafana
```

Loki uses local TSDB v13 + filesystem storage under `/var/lib/loki`,
seven-day retention and disabled analytics reporting.

## Alloy -> Loki ingestion

The private collector spool was moved to:

```text
/var/lib/pihole-dns-analytics/queries.ndjson
```

The spool remained owned by the Fedora operator and group-readable only by the
dedicated `alloy` group. A direct read test as the `alloy` service account
passed.

The first bounded end-to-end equality check reported:

```text
FILE_TOTAL=11116
FILE_7D=11116
LOKI_7D=11116
```

This demonstrated that the tested local file population was fully represented
in Loki for the tested seven-day window.

The Loki label audit reported only low-cardinality transport/dataset labels:

```text
__stream_shard__
dataset
filename
job
service_name
source
```

The following private/high-cardinality fields were confirmed absent as
persistent labels:

```text
domain
client_ip
client_name
id
upstream
```

## Pi-hole IN_PROGRESS semantics

A follow-up source check was performed because the first dashboard showed
persistent `IN_PROGRESS` rows.

RAM and on-disk Pi-hole API views matched:

```text
MEM_IN_PROGRESS=99
DISK_IN_PROGRESS=99
STATUS_MISMATCHES=0
```

None of those rows was younger than 60 seconds in the tested sample, and 70
were older than one hour.

This shows that the tested Pi-hole source itself can retain
`IN_PROGRESS` rows. The dashboard therefore presents that status separately
rather than reclassifying or rewriting it downstream.

## Grafana dashboard

A provisioned Loki datasource and the dashboard
`Pi-hole — Aktywność DNS v2` were live-validated.

The dashboard includes:

- total, blocked, cached, forwarded and unfinished query counts;
- blocked-query percentage;
- cache hit rate;
- mean and P95 DNS reply latency;
- query volume over time;
- query-status and record-type tables;
- top domains, clients, blocked domains and upstreams;
- recent DNS activity;
- an explicit Pi-hole-visible coverage disclaimer.

The public repository stores dashboard structure only. Live dashboard data and
screenshots containing real client/domain activity are intentionally excluded.

## Latency-query correction

The first P95 panel incorrectly reduced per-series quantiles using a maximum and
displayed the maximum observed latency as if it were P95.

A direct private NDJSON check over 11,508 numeric reply-time samples reported:

```text
MEAN_MS=18.909
P50_MS=0.166
P90_MS=48.519
P95_MS=104.821
P99_MS=310.246
MAX_MS=3511.879
```

The dashboard query was corrected to extract only the numeric
`reply_time_ms` field before `unwrap` and compute the quantile over the
single intended stream. A later live dashboard refresh showed a plausible
current P95 in the tens-of-milliseconds range instead of the prior multi-second
maximum.

Note: the collector field name `reply_time_ms` is historical. The Pi-hole API
value is in seconds; the dashboard multiplies it by 1000 for millisecond
display.

## Fedora reboot persistence

A controlled Fedora reboot was performed with the DNS analytics stack enabled.

Before reboot, the private spool contained 11,755 events. After reboot:

- Grafana, Loki, Alloy and Caddy returned to `active`;
- the Pi-hole SSH tunnel and collector timer returned to `active`;
- the expected HTTP/gRPC listeners remained bound to loopback;
- Alloy returned `Alloy is ready.`;
- Grafana returned `"database": "ok"`;
- Loki initially returned HTTP 503 while its internal ring/WAL recovery was
  still converging, then returned `ready` on the next health check;
- the collector resumed automatically and advanced the spool without manual
  intervention.

The post-reboot collector integrity check reported:

```text
EVENT_LINES=12119
UNIQUE_IDS=12119
DUPLICATE_IDS=0
STRICTLY_ASCENDING=True
FILE_MAX_ID=12119
CHECKPOINT=12119
CHECKPOINT_MATCH=True
```

A final end-to-end catch-up check after services settled reported:

```text
FILE_7D=12183
LOKI_7D=12183
```

This validates automatic recovery of the complete tested path:

```text
Pi-hole -> SSH tunnel -> collector -> NDJSON -> Alloy -> Loki -> Grafana
```

## Two-client acceptance and Tailscale coverage boundary

A controlled two-client test was performed with synthetic DNS markers.

The first Windows test was intentionally useful as a coverage check: with
Tailscale active, the synthetic query was visible on `tailscale0` but absent
from both Pi-hole memory/disk API history and the Fedora collector dataset.
This is consistent with the already documented Tailscale classic-DNS path that
terminates at firmware dnsmasq rather than Pi-hole.

After disabling Tailscale on that Windows client, both controlled main-LAN
clients were distinguishable in the Pi-hole-visible collector dataset:

```text
FEDORA7_EVENTS=1
WINDOWS7_EVENTS=4
DISTINCT_CLIENTS=2
CLIENTS_ARE_DISTINCT=True
```

The higher Windows event count is not treated as a defect; the acceptance
criterion is client distinguishability rather than an exact one-query/one-event
count.

The Tailscale capture was summarized without publishing client addresses or
private query history:

```text
WINDOWS_QUERY_ON_TAILSCALE0=True
WINDOWS_QUERY_PACKET_LINES=4
PIHOLE_ALIAS_BYPASS_CONFIGURED=True
```

This gives evidence-backed confirmation that the current Pi-hole analytics
dataset does not include the tested Tailscale classic-DNS path.

## Result

**PASS — Phase 2 Alloy/Loki ingestion, the Phase 3 Grafana dashboard, full
Fedora reboot persistence and controlled two-client main-LAN acceptance are
live-validated for the tested environment.**

Still outstanding before issue #108 can be considered complete:

- longer-term storage-growth measurement;
- proof that seven-day retention actually expires data as configured;
- rollback/uninstall validation;
- remaining coverage-gap correlation for the LAN hard-coded classic-DNS path
  and the separate encrypted-DNS work tracked under issue #68.
