# Grafana alerting validation — 2026-09-27

## Scope

Live validation on the Fedora monitoring host for the provisioned Grafana rules
used with the ASUS TUF-AX5400 observability stack.

No router configuration, WAN policy, firewall rule or DNS service was changed
for this test.

## Provisioned rules

Four rules were loaded in the Grafana `Network` folder:

- `tuf_collector_down` — SSH collector unavailable;
- `tuf_wan_down` — router-reported WAN link down;
- `tuf_probe_failed` — failed HTTPS, ICMP or router-DNS blackbox probe;
- `tuf_telemetry_stale` — last successful router collection older than 90 seconds.

All rules use a one-minute evaluation interval and a two-minute pending period.

## Controlled fault test

The Fedora user service for the read-only SSH collector was intentionally
stopped. The router and Internet connection remained untouched.

Observed behavior:

```text
collector rule:  Normal -> Pending -> Firing
telemetry rule:  Normal -> Pending -> Firing
blackbox rule:   remained Normal
WAN rule:        entered a no-data/indeterminate state while collector data was absent
```

The independent blackbox rule staying healthy demonstrated that Internet/DNS
probing continued separately from the SSH collector.

The collector was then started again. After fresh samples arrived, all four
rules returned to the normal/green state.

## WAN no-data policy correction

The controlled outage exposed an alert-quality issue: missing collector data
must not be presented as a WAN outage.

The WAN rule was therefore changed from:

```text
noDataState: NoData
```

to:

```text
noDataState: OK
```

Collector availability and telemetry freshness already have dedicated alerts.
The WAN rule now represents an observed router-reported WAN-down condition
rather than the absence of the metric itself.

## Post-change Grafana validation

Grafana was restarted after the provisioning change.

Observed health:

```json
{
  "database": "ok",
  "version": "13.2.2"
}
```

A journal query beginning after the new Grafana process started returned no
matching `level=error`, `failed` or provisioning-error entries.

Errors seen during the earlier controlled restart were plugin termination and
context-cancellation messages from the old process while systemd was stopping
it; they were not repeated after the new process started.

## Current boundary

This validates local rule evaluation and recovery. No external notification
contact point (email, mobile push, chat service or webhook) is claimed or
configured by this artifact.
