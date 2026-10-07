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

## 6. Wi-Fi 6 HE160 interoperability – MediaTek MT7922 vs ASUS/Broadcom

**File:** [Wi-Fi 6 HE160 Interoperability](wifi6-he160-mt7922-interoperability-case-study.md)

A controlled Wi-Fi interoperability investigation covering:

- configured-versus-runtime HE160 verification on the ASUS 5 GHz radio;
- HE80 versus HE160 A/B testing on a MediaTek MT7922 client;
- two MT7922 driver revisions;
- both TCP traffic directions with 120-second, four-stream iperf3 runs;
- router-side `wl sta_info` PHY, RSSI and retry-related telemetry;
- an independent Android 2x2 HE160 reference client;
- separation of negotiated PHY rate from usable TCP throughput;
- explicit limits on interpreting Broadcom retry counters as application loss;
- bounded root-cause assessment without assigning an unproven vendor defect.

The case narrows severe HE160 degradation to the tested MT7922 ↔
ASUS/Broadcom interaction while preserving the distinction between observed
evidence and root-cause inference.


## 7. ASUS TUF-AX5400 external observability

**File:** [ASUS TUF-AX5400 External Observability](asus-tuf-ax5400-observability-case-study.md)

A read-only router observability integration covering:

- a Broadcom chanspec incompatibility discovered during live exporter collection;
- a bounded TUF-AX5400 channel parsing adaptation;
- external VictoriaMetrics storage and Grafana visualization;
- Blackbox HTTPS, ICMP and router-DNS probes;
- scheduled Traffic Analyzer history import;
- localhost-only service exposure and least-privilege Blackbox capabilities;
- a Fedora systemd/OpenSSH namespace interaction found during service hardening;
- real reboot/persistence validation of the complete monitoring stack.

The case keeps time-series and dashboard workloads off the 512 MiB router and
retains explicit limits around host downtime, remote exposure and cross-model
compatibility.

## 8. Diversion to Pi-hole on-router migration

**File:** [Diversion to Pi-hole on-router migration](pi-hole-on-router-case-study.md)

A staged DNS-filtering migration on the 512 MiB ASUS TUF-AX5400 covering:

- dedicated Pi-hole listener design without port-53 conflict with firmware dnsmasq;
- OISD blocking-list parity and the two-domain Diversion essential-allowlist delta;
- corrected latency A/B testing and normal-use query-history analysis;
- main-LAN DHCP cutover to Pi-hole while keeping firmware DHCP/local naming;
- conditional reverse DNS;
- removal of uiDivStats, Diversion, Stubby and stale NextDNS hook logic;
- a real reboot failure caused by missing swap activation and the resulting Tailscale Go-runtime OOM;
- restoration of pre-Entware swap activation and successful final reboot validation;
- explicit separation between the adopted DHCP path and classic-DNS interception paths that still terminate at firmware dnsmasq.

The case study treats the discovered startup failure as evidence and remediation,
not as a result to omit from the portfolio narrative.

## 9. syslog-ng local archive resilience under collector outage

**File:** [syslog-ng Local Archive Resilience](syslog-ng-flow-control-resilience-case-study.md)

A centralized-logging failure and recovery case covering:

- a live syslog-ng source that stopped advancing while Asuswrt continued writing;
- inode/FD-position analysis that ruled out a stale rotated-file handle;
- separation of transport/TLS health from source-consumption state;
- identification of hard flow-control as the architectural coupling between
  the remote collector and the local archive;
- removal of hard flow-control while retaining the remote reliable disk buffer;
- controlled collector outage proving that local archival continues;
- post-recovery delivery of the marker generated while the collector was down;
- a static regression guard preventing reintroduction of the blocking policy.

The case distinguishes directly observed source-position and delivery evidence
from the unmeasured internal queue depth at the moment of the original stall.

## 10. RouterCloud secure browser file service

**File:** [RouterCloud production checkpoint — 2026-10-03](routercloud-production-checkpoint-2026-10-03.md)

A constrained browser/file-service case covering:

- a dedicated LAN/Tailscale-only HTTPS service rooted at the Personal Cloud
  data directory rather than the router filesystem;
- custom login/session authentication and production-tested password recovery;
- backend-authorized rename/delete/edit/archive operations while generic Dufs
  delete remains disabled;
- WebDAV desktop integration;
- AJAX sorting and live search without full-page reloads;
- persistent favorites and recent-files UI;
- independent versioned encrypted backups through a read-only Fedora pull path;
- versioned external frontend assets, rollback copies and controlled deployment;
- explicit separation between repository CI, manual browser acceptance and
  dedicated production evidence.

The case is useful as an example of extending a lightweight upstream file server
without silently broadening its filesystem, network or authorization boundary.

See also the
[2026-10-03 UI validation](../evidence/2026-10-03/routercloud-ui-production-validation.md)
and
[password-recovery production validation](../evidence/2026-10-03/routercloud-password-recovery-production-validation.md).

## 11. Android Pi-hole enforcement and remote management over Tailscale

**File:** [Android DNS Enforcement and Remote Management over Tailscale](case-studies/android-tailscale-pihole-debugging.md)

A multi-layer Android/Tailscale troubleshooting and hardening case covering:

- source-scoped Pi-hole DNS enforcement for a remote Android client;
- LTE/5G operation without consuming a second Android VPN slot;
- preservation of internal `home.arpa` resolution and normal cellular Internet access;
- diagnosis of exit-node-specific DNS behaviour using packet capture and NAT counters;
- RouterCloud reachability through a router-local IPv4 alias and INPUT rather than FORWARD;
- stale administrative Tailscale source cleanup;
- separation of the external router-management port from the actual ASUS WebUI listener;
- correction of the management path from `8443 -> 8443` to `8443 -> 443`;
- runtime health checks for the target listener, DNAT and post-DNAT INPUT policy;
- dedicated negative contract tests for wrong source, port, destination and missing listener;
- end-to-end validation using ADB, iptables counters, Pi-hole analytics, `tcpdump`, `netstat`, and staged SHA-256 deployment verification.

The case demonstrates how DNS, routing, NAT, firewall and application-listener
failures can produce similar client-side symptoms, and why each layer should be
validated independently before changing the architecture.

The documented result is intentionally limited to the validated transport, DNS and
remote-management path. Stronger per-device Pi-hole policy and application
compatibility testing remain separate follow-up work.


## 12. DNS bootstrap deadlock and fail-open resolver recovery

**File:** [DNS bootstrap deadlock and fail-open resolver recovery](dns-guard-cold-boot-case-study.md)

A resolver-startup resilience case covering:

- a cold-boot dependency cycle between hostname-based NTP bootstrap, Pi-hole,
  and an Unbound instance that intentionally waits for NTP readiness;
- separation of independent WAN/bootstrap DNS from the steady-state local
  Pi-hole -> Unbound path;
- DNS Guard v3.1 health gating, atomic runtime promotion and fail-open fallback;
- sticky break-glass state that blocks automatic promotion during emergency
  recovery;
- an idempotency defect found by shell tracing and fixed before reboot
  validation;
- persistent one-minute watchdog recreation from `services-start`;
- real watchdog fallback/recovery and full cold-boot validation;
- Android LTE Tailscale exit-node DNS observed reaching the local Pi-hole alias
  over loopback after reboot.

The case makes the availability trade-off explicit: during local DNS failure,
the router deliberately uses independent bootstrap DNS rather than preserving
filtering at the cost of losing name resolution.

## 13. Port exposure and trust-boundary audit

**File:** [Port Exposure and Trust-Boundary Audit](case-studies/port-exposure-trust-boundary-audit-2026-10-07.md)

A multi-vantage security exposure audit covering:

- full TCP 1-65535 LAN scanning of the router and service aliases;
- correlation of scanner results with local listeners, firewall chains, NAT policy,
  and process ownership;
- authorized versus non-authorized Tailscale peer testing for management access;
- positive/negative source-restriction validation for Fedora syslog-ng;
- correction of a false-negative Fedora LAN result caused by a preferred
  Tailscale subnet route;
- WAN firewall, NAT, virtual-server and UPnP runtime review;
- public-IPv4 confirmation without publishing the address;
- invalidation of an initially misleading "WAN" test after route diagnostics
  showed that it had actually used an internal/Tailscale path;
- corrected LTE/5G external validation after independent DNS-over-HTTPS resolution
  and route verification;
- native WAN IPv6 state validation;
- explicit review findings and bounded claims for external UDP coverage.

The case study is intentionally sanitized: deployment-specific public addresses,
DDNS names, tailnet addresses, device identifiers, MAC addresses, credentials,
and exact administrative source allowlists are excluded. It preserves the
methodology and decision trail, including tests that were rejected as invalid.

## How to read these cases

Where applicable, case studies separate:

1. **Observed evidence** — commands, process state, socket state, counters, or other directly recorded observations.
2. **Remediation** — changes made when the case involved a fault or configuration issue.
3. **Validation** — evidence collected after a change, or direct workload validation when no remediation was required.
4. **Interpretation and limitations** — what the evidence supports and what it does not prove.

These case studies are intended to demonstrate troubleshooting methodology, evidence handling, least-privilege/security reasoning, and disciplined distinction between observation and inference.

Raw deployment-specific evidence is intentionally excluded from the public repository when it contains private infrastructure identifiers.