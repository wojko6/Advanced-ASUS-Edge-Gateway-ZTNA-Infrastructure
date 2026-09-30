# Issue #141 — Edge Gateway service portal live validation

**Status:** PASS  
**Date:** 2026-09-30  
**Evidence class:** Live functional validation / sanitized  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton

## Purpose

Validate the read-only Edge Gateway service portal introduced by PR #146.

The portal is intended to provide one project-native entry point for operational
services without embedding credentials, changing authentication boundaries or
exposing additional WAN services.

## Scope validated

The live deployment was configured with links for:

- Grafana home;
- network observability dashboard;
- Engineering / CI dashboard;
- DNS Activity dashboard;
- Pi-hole administration.

Personal Cloud intentionally remains unconfigured and is rendered as unavailable.

Deployment-specific URLs are stored only in the private router configuration.
The public example configuration keeps all portal URL values empty.

## Staged collector validation

The Phase 4 status collector was staged under `/tmp` before persistent
replacement.

Shell syntax validation passed:

```text
STATUS_SCRIPT_SYNTAX=PASS
```

The collector generated a sanitized portal snapshot successfully:

```text
COLLECTOR_RC=0
```

Four Grafana-related targets were initially populated for staged validation.
Pi-hole and Personal Cloud were intentionally left empty at this stage.

## Runtime preview

The new `EdgeGateway.asp` and generated `status.js` were previewed only in the
runtime WebUI before persistent installation.

Runtime validation reported:

```text
RUNTIME_PREVIEW=PASS
```

Browser validation confirmed:

- the new **Portal usług** section rendered correctly;
- configured services showed an `Otwórz` action;
- Pi-hole showed its runtime process state independently of portal-link
  configuration;
- Personal Cloud correctly showed an unconfigured state;
- the rest of the Edge Gateway dashboard continued to render normally.

The portal table header was refined during live review from `Stan` to
`Stan / konfiguracja`, with the third column header intentionally left blank
because the per-row `Otwórz` actions are self-explanatory.

## Persistent deployment

Before persistent replacement, the existing router configuration, WebUI source
and status collector were backed up under the project backup directory.

The Phase 4 ASP and status collector were then installed persistently.

Validation completed with:

```text
PERSISTENT_ASP=PASS
PERSISTENT_COLLECTOR=PASS
Summary: 0 failure(s), 0 warning(s)
```

## Pi-hole portal and session behavior

The Pi-hole portal target was added to the private router configuration after
its HTTPS hostname was confirmed live.

Pi-hole authentication was intentionally **not** embedded into the Edge Gateway
portal. No password, session identifier or authentication token is stored in
the portal URL.

Instead, the Pi-hole WebUI session policy was adjusted locally to:

```text
webserver.session.timeout = 604800
webserver.session.restore = true
```

Effective values were verified directly through `pihole-FTL --config`.

Functional browser validation confirmed that, after a normal Pi-hole login, the
Edge Gateway portal link reused the existing browser session rather than
requiring credentials to be stored in Edge Gateway.

Grafana uses the same architectural model: portal links rely on the existing
browser session managed by Grafana itself.

## Controlled reboot validation

After a controlled router reboot, the following persisted successfully:

- Edge Gateway mounted as `user1.asp`;
- Portal services configuration;
- sanitized portal snapshot;
- `AsusEdgeWebUIStatus` one-minute refresh schedule;
- Polish WebUI overlay;
- Pi-hole session timeout and restore settings.

The post-reboot portal snapshot contained the configured Grafana and Pi-hole
targets while Personal Cloud remained intentionally empty.

Pi-hole effective session values after reboot:

```text
timeout=604800
restore=true
```

The final project health check completed with:

```text
Summary: 0 failure(s), 0 warning(s)
```

The accepted health set included firewall serialization, project-owned
Tailscale chains, exit-node prerequisites, classic-DNS and DoT enforcement,
IPv6 fail-closed guards, printer exposure controls, Unbound runtime/control and
DNSSEC validation, and syslog-ng runtime state.

## Security properties

**PASS.**

The validated portal:

- remains read-only;
- keeps credentials and session identifiers out of portal configuration;
- sanitizes allowed portal URLs before publishing them in `status.js`;
- does not change service authentication;
- does not change LAN/Tailscale/WAN exposure rules;
- opens external service targets in a new tab with `noopener noreferrer`;
- degrades safely when an optional portal URL is not configured;
- preserves the existing project health state after reboot.

## Claim boundary

This validation covers the service-portal entry points and their persistence.

It does not claim active reachability monitoring for each portal target.
A configured portal URL currently means that a target is configured, not that
the target has passed a synthetic health probe. Client-side synthetic checks and
SLO monitoring remain a separate observability workstream.
