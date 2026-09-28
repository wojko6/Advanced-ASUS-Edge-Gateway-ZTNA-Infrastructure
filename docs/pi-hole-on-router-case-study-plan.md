# Diversion vs Pi-hole on-router — case study plan

**Status:** completed case study. Pi-hole was adopted for the reference main-LAN DHCP path on 2026-09-28 after staged validation, blocking-list parity analysis, controlled cutover, duplicate-service cleanup, swap/Tailscale recovery and a final successful reboot.

Tracking issue: #80.

Final result: [Diversion to Pi-hole on-router migration case study](pi-hole-on-router-case-study.md) and [sanitized main-LAN cutover evidence](../evidence/2026-09-28/pi-hole-main-lan-cutover-validation.md).

The accepted deployment keeps Pi-hole DHCP disabled, advertises only Pi-hole to the main LAN through firmware DHCP, keeps Unbound as the validating upstream, and retains firmware dnsmasq for DHCP/local naming and the existing classic-DNS interception endpoint. The case study does **not** claim that every hard-coded external classic-DNS or Tailscale-intercepted query is filtered by Pi-hole; those interception paths remain a separate follow-up validation.

## Research question

Can Pi-hole running directly on the ASUS TUF-AX5400 through Entware replace
Diversion while preserving the validated dnsmasq/Unbound/Tailscale/firewall
baseline and remaining healthy within a 512 MiB RAM router?

The case study must answer this with measured evidence rather than UI
preference.

## Current baseline

```text
clients
  -> firmware dnsmasq :53 + Diversion
  -> Unbound :53535
  -> Internet
```

The baseline already provides:

- DNSSEC through Unbound;
- project-owned DNS/firewall policy;
- Tailscale/exit-node integration;
- persistent SSD-backed Entware storage;
- swap;
- centralized logging;
- external observability and Grafana.

## Candidate architecture

```text
clients
  -> Pi-hole FTL :53
  -> Unbound :53535
  -> Internet

firmware dnsmasq
  -> DHCP / local names / reverse DNS
  -> moved away from :53 if the validated design requires it
```

The staged pilot uses a dedicated LAN alias for Pi-hole so the firmware
dnsmasq/Diversion path remains available for rollback. Exact listener ownership
was measured during the 2026-09-28 pilot: Pi-hole and firmware dnsmasq remained
on separate local addresses while both used port 53, with Unbound preserved on
loopback:53535.

## What Pi-hole would replace

Pi-hole is evaluated primarily as a replacement for **Diversion's DNS-filtering
role**.

It does not automatically replace:

- Unbound;
- router DHCP/local naming;
- Tailscale;
- project firewall policy;
- centralized logging;
- Grafana monitoring.

## Why test it on the router

Running Pi-hole on-router would keep DNS filtering available when the Fedora
workstation is powered off and could add:

- richer query history;
- per-client DNS visibility;
- groups and policies;
- API access;
- dedicated DNS administration UI;
- a possible data source for #108 Network DNS Visibility / Client Activity
  Analytics.

The trade-off is additional memory, CPU, database and maintenance load on the
512 MiB edge device.

## 2026-09-28 pilot checkpoint

Completed and live-validated:

- staged Pi-hole installation on a dedicated LAN alias;
- Pi-hole DHCP disabled;
- existing Unbound retained as upstream;
- Gravity populated from OISD Big;
- single Fedora client moved to Pi-hole;
- per-client query visibility confirmed;
- DNSSEC failure behavior preserved through the Unbound upstream;
- project LAN DNS enforcement updated with a configurable local-resolver
  bypass that is validated for ordering;
- managed firewall rebuild validated with 0 health-check failures/warnings;
- controlled router reboot validated Pi-hole alias, FTL, Gravity, firewall and
  resolver persistence;
- corrected 200-sample-per-scenario Diversion vs Pi-hole latency comparison
  completed after removing the NAT-interception confounder.

Initial corrected benchmark:

| Scenario | Diversion mean / median | Pi-hole mean / median |
| --- | ---: | ---: |
| blocked test name | 0.54 / 0.50 ms | 0.87 / 1.00 ms |
| warmed clean name | 2.65 / 3.00 ms | 1.12 / 1.00 ms |

All 800 measured queries returned a valid DNS response. These local
single-client results do not establish general resolver performance.

See [sanitized pilot evidence](../evidence/2026-09-28/pi-hole-single-client-pilot-validation.md).

The adoption decision was made after the later same-day main-LAN cutover and
reboot/recovery work. The final evidence additionally covers DHCP-only Pi-hole
advertisement, reverse DNS through firmware dnsmasq, removal of duplicate
services, a swap-startup regression that prevented Tailscale from starting,
and the successful reboot after restoring pre-Entware swap activation.

Longer-duration database growth, broader concurrent-client stress and alignment
of the existing classic-DNS interception path with Pi-hole remain follow-up
engineering work rather than hidden acceptance assumptions.

## Test phases

### 0. Read-only baseline

Record before installing Pi-hole:

- RAM/available memory;
- swap usage and swap activity;
- CPU/load;
- per-process memory;
- storage free space and writes;
- current dnsmasq/Diversion/Unbound footprint;
- port-53 listener ownership;
- cached/uncached DNS latency;
- DNSSEC;
- IPv4 and IPv6 resolver paths;
- LAN and Tailscale DNS behavior;
- current firewall/DNS-enforcement state.

Create rollback backups before any service change.

### 1. Staged installation

Install the reviewed Entware Pi-hole candidate without immediately replacing
the household DNS path.

Keep:

- Pi-hole DHCP disabled;
- Unbound as the candidate upstream;
- data on SSD-backed Entware;
- current DNS path available for rollback;
- management UI restricted to trusted local/explicitly authorized paths.

Disable unnecessary duplicate functions where appropriate, for example a
second time service if the router already owns that role.

### 2. Single-client trial

Move only one controlled test client.

Validate:

- A/AAAA resolution;
- DNSSEC;
- local/reverse names;
- blocking;
- allow/deny behavior;
- query history;
- DNS latency;
- IPv6;
- Tailscale where applicable.

### 3. Diversion vs Pi-hole comparison

Use equivalent test conditions for both stacks.

Measure:

- idle and peak RAM;
- FTL RSS;
- free/available memory;
- swap and swap-in/out behavior;
- CPU/load;
- SSD/database growth;
- cached/uncached DNS latency;
- blocking effectiveness;
- false positives;
- Android app/WebView/Custom Tab behavior;
- browser behavior;
- local-name resolution;
- IPv4/IPv6;
- Tailscale DNS;
- operational complexity.

### 4. Maintenance/stress test

Observe the candidate during:

- Gravity/list update;
- FTL restart;
- database maintenance;
- multiple simultaneous DNS clients;
- high router network load at the same time.

Record peak resource pressure and DNS responsiveness.

An acceptable idle footprint is not enough by itself.

### 5. Controlled LAN cutover

Only after the single-client test passes:

- move intended LAN DNS to Pi-hole;
- preserve Unbound upstream;
- disable Diversion only after Pi-hole has demonstrated equivalent/better
  DNS-layer coverage;
- verify DNS Director/project firewall/Tailscale interaction;
- verify there is no unintended alternate resolver path.

### 6. Persistence/recovery

Validate:

- clean router restart;
- repeated cold/start cycles;
- Entware SSD mount ordering;
- Pi-hole/FTL startup;
- Unbound availability;
- WAN reconnect;
- Gravity maintenance;
- rollback to Diversion + dnsmasq + Unbound.

## Resource acceptance boundary

No fixed RAM number is pre-declared as automatically safe.

Reject or redesign the on-router candidate if testing shows:

- OOM events;
- sustained swap churn;
- noticeable DNS instability;
- material routing/Wi-Fi regression;
- excessive SSD writes;
- unreliable startup/recovery;
- rollback that is too fragile for the edge gateway.

## Security and privacy

- no WAN exposure of the Pi-hole admin UI;
- management only from trusted paths;
- no publication of real household DNS history;
- sanitize client IPs, hostnames, Tailscale identities and queried domains in
  public evidence;
- no assumption that Pi-hole solves DoH/DoQ bypasses;
- #68 encrypted-DNS assessment remains required.

## Relationship to #108

If Pi-hole is adopted, its query log/API can become a major input to Network
DNS Visibility / Client Activity Analytics.

If the on-router design is rejected, #108 still proceeds through the existing
centralized logging + Loki/Alloy design.

## Final deliverable

A portfolio case study:

**Diversion vs Pi-hole on ASUS TUF-AX5400 / Asuswrt-Merlin GNUton**

containing:

- before/after architecture;
- reproducible methodology;
- resource measurements;
- DNS latency/function results;
- sanitized UI/dashboard evidence;
- failure and recovery tests;
- security exposure checks;
- adoption or rejection rationale;
- tested rollback procedure.
