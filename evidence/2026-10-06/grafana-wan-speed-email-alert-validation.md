# Grafana WAN-speed email alert validation — 2026-10-06

## Scope

Live validation on the Fedora monitoring host for a Grafana alert that detects a
degraded negotiated WAN link speed without changing the real WAN link.

The production rule is provisioned as `tuf_wan_speed_degraded` in the
`Network` folder.

## Production rule

The rule evaluates:

```promql
max(asus_router_wan_speed_bps{job="asus_wifi_clients"})
```

and fires when the negotiated WAN speed remains below 900,000,000 bit/s for
three minutes.

The production safety boundary is:

```text
noDataState: OK
```

Missing collector data is handled by dedicated collector and telemetry-freshness
alerts and must not be misreported as WAN-speed degradation.

## Notification path

Grafana SMTP is configured locally through a root-owned environment file outside
the repository. The repository contains only the contact-point definition and
references `$GF_SMTP_USER`; no mailbox password or application password is
stored in Git.

The contact point is named:

```text
ASUS Edge Gateway Email
```

Resolved notifications are enabled.

## Controlled firing test

The threshold was temporarily raised from 900,000,000 bit/s to 1,100,000,000
bit/s while the live negotiated WAN speed remained 1,000,000,000 bit/s.

Observed behavior:

```text
Normal -> Pending -> Firing
```

Grafana delivered a real email notification titled `Prędkość WAN obniżona`.

The live value in the notification was approximately:

```text
A = 1e+09
C = 1
```

No physical WAN renegotiation or Internet outage was introduced for this test.

## Recovery test

The production threshold of 900,000,000 bit/s was restored.

With the WAN metric still reporting 1,000,000,000 bit/s, the rule recovered and
Grafana delivered a resolved email notification.

Observed recovery:

```text
Firing -> Resolved
A = 1e+09
C = 0
```

## Result

The full path is validated:

```text
ASUS WAN link-speed telemetry
        |
        v
VictoriaMetrics
        |
        v
Grafana rule evaluation
        |
        v
ASUS Edge Gateway Email contact point
        |
        v
SMTP notification: Firing + Resolved
```

The production threshold after validation is 900,000,000 bit/s.
