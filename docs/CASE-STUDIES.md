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

## 3. Tailscale Android DNS and routing failure

**File:** [Tailscale Android DNS and Routing Troubleshooting](tailscale-android-dns-routing-case-study.md)

An Android/Tailscale troubleshooting case study covering:

- separation of IP connectivity from DNS resolution failure;
- an overlapping `192.168.50.0/24` local Wi-Fi and Tailscale subnet route;
- Android Private DNS state and `PrivateDnsBroken`;
- DNS Toggle automation using `WRITE_SECURE_SETTINGS`;
- conflict between strict NextDNS DoT and the router's intentional TCP/853 policy;
- direct `dig` testing to separate DNS transport from the Android system resolver;
- a reproducible side-by-side post-fix Tailscale Android build;
- controlled A/B handoff testing against official Tailscale 1.102.3;
- explicit rejection of an unproven attribution to upstream issue #21155.

The case demonstrates how multiple valid-looking network controls can interact and create a failure that initially resembles an upstream VPN client defect.

## 4. GeForce NOW Ethernet vs Wi-Fi 6 stability

**File:** [GeForce NOW Ethernet vs Wi-Fi 6 Stability](geforce-now-ethernet-vs-wifi6-case-study.md)

A real-time network stability case study covering:

- controlled removal of a Tailscale exit-node confounder before testing;
- Gigabit Ethernet versus 5 GHz 802.11ax/80 MHz from the same client and gateway;
- short matched latency/jitter baselines;
- a long Wi-Fi latency sample with rare local-path spikes but zero ICMP loss;
- GeForce NOW application statistics from the same Warsaw service location;
- packet-capture analysis of the dominant UDP stream on both transports;
- explicit truncation and claim boundaries for the recovered Wi-Fi capture.

The case distinguishes average latency from tail latency and does not
reinterpret interface counters as application packet loss.

## 5. Xbox Cloud Gaming in Microsoft Edge / WebRTC

**File:** [Xbox Cloud Gaming in Microsoft Edge — WebRTC](xbox-cloud-edge-webrtc-case-study.md)

A browser-native real-time streaming case study covering:

- WebRTC transport discovery from an actual Xbox Cloud Gaming browser session;
- H.264 1920 x 1080 inbound video and Opus audio;
- approximately 1000 seconds of WebRTC receiver statistics;
- RTP loss, frame-drop, freeze, jitter and bitrate analysis;
- selected ICE candidate-pair state, UDP transport and RTT;
- xCloud input/control/QoS WebRTC data channels;
- the distinction between generic browser hardware-decode capability and
  stream-specific decoder telemetry;
- privacy-driven sanitization of the raw WebRTC dump.

The case treats browser capability, per-stream RTP telemetry and ICE metrics as
separate evidence layers and does not convert WebRTC RTT into an input-latency
claim.

## How to read these cases

Where applicable, case studies separate:

1. **Observed evidence** — commands, process state, socket state, counters, or other directly recorded observations.
2. **Remediation** — changes made when the case involved a fault or configuration issue.
3. **Validation** — evidence collected after a change, or direct workload validation when no remediation was required.
4. **Interpretation and limitations** — what the evidence supports and what it does not prove.

These case studies are intended to demonstrate troubleshooting methodology, evidence handling, least-privilege/security reasoning, and disciplined distinction between observation and inference.

Raw deployment-specific evidence is intentionally excluded from the public repository when it contains private infrastructure identifiers.
