# Case Studies

This directory contains incident and integration case studies based on observed project evidence.

## 1. uiDivStats high-load incident

**File:** [uiDivStats High Load Incident](uidivstats-high-load-case-study.md)

A router troubleshooting case study covering:

- unusually high load averages despite substantial CPU idle time;
- process-state, PPID, and wait-channel analysis;
- identification of approximately 100 orphaned uiDivStats `flushtodb`/`querylog` processes;
- migration from uiDivStats v3.0.2 to v4.0.16;
- SQLite database preservation and migration;
- controlled stale-process cleanup;
- before/after resource validation.

The case study deliberately distinguishes a strongly supported operational root-cause assessment from proof of a specific upstream software defect.

## 2. Zen Linux proxy integration

**File:** [Zen Linux Proxy Integration](zen-linux-proxy-integration-case-study.md)

A Fedora/GNOME endpoint validation covering:

- system-proxy and PAC integration;
- dynamic localhost proxy ports;
- Start/Stop lifecycle and configuration cleanup;
- LAN exposure testing;
- PAC routing and exclusions;
- the boundary between GNOME-aware applications and applications that ignore desktop proxy settings;
- the observed Fedora/Tailscale DNS path.

This case study is observational and does not claim that every Linux application is intercepted by Zen.

## How to read these cases

Each case separates:

1. **Observed evidence** — commands, process state, socket state, counters, or other directly recorded observations.
2. **Remediation** — changes actually made after the observation.
3. **Validation** — evidence collected after the change.
4. **Interpretation and limitations** — what the evidence supports and what it does not prove.

These case studies are intended to demonstrate troubleshooting methodology, evidence handling, least-privilege/security reasoning, and disciplined distinction between observation and inference.

Raw deployment-specific evidence is intentionally excluded from the public repository when it contains private infrastructure identifiers.
