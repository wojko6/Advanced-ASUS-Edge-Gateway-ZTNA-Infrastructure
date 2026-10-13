# Reproducible edge benchmarks — ASUS TUF-AX5400 and future OPNsense

**Status:** PLANNED MEASUREMENT METHODOLOGY / NO HARDWARE PURCHASE OR MIGRATION  
**Decision:** 2026-10-13  
**Tracking:** [#194](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/194)  
**Historical source:** [PR #195](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/195) (original RT-BE88U plan, not a current purchase)  
**Platform authority:** [2026-10-12 decision](../architecture/platform-direction-2026-10-12.md)

This is a **reusable test procedure**, not a claim that measurements have already been
performed. The ASUS TUF-AX5400 is the existing production baseline. The eventual
comparison platform, **if obtained and explicitly approved**, is a separate x86
device running OPNsense. Its model, CPU, NICs, storage, version, network topology
and purchase date remain undecided. A preliminary virtual OPNsense lab may prove
configuration and test methodology, **not comparable physical forwarding capacity**.

## 1. Ground rules and test equivalence

- Do not migrate, reboot, fault-inject, replace DNS, disable firewall protections
  or alter production WAN/VPN routes solely to collect results. Live measurements
  require a separate approved maintenance window where they may disrupt service.
- Prefer an isolated wired testbed with independent endpoints and constrained
  routing; preserve a known-good ASUS configuration and rollback path.
- Run each comparable case at least **three times** in each direction. Report
  median, range, relevant high percentiles, failures and confidence limitations.
  Warm-up runs should be marked separately from measured runs.
- Hold constant the client NIC, cable, tested service, external peer, transport,
  MTU, stream count, duration, DNS query list and normal workload where possible.
- Clearly label different firewall engines (ASUS/Linux netfilter vs OPNsense/PF),
  cryptographic implementations, routing policies and hardware offload paths.
  A mismatch is a **different scenario**, not a like-for-like performance delta.
- Compare **service outcomes**, not merely command availability: neither an
  ASUS-specific JFFS shell hook nor DNS Guard metrics must be assumed to exist
  on OPNsense.
- Never publish unsanitized addresses, tailnet identity, credentials, household
  DNS query history or raw router backups.

## 2. Session metadata and evidence

Record for each endpoint/measurement:

```text
DATE_UTC=
TEST_ID=
PLATFORM=ASUS_TUF_AX5400 | FUTURE_OPNSENSE
HARDWARE_CPU_RAM_NICS=
FIRMWARE_OR_OPNSENSE_VERSION=
KERNEL_AND_PACKAGE_VERSIONS=
UPTIME=
WAN_LINK_AND_BANDWIDTH=
LAN_LINK_AND_DUPLEX=
CLIENT_OS_NIC_DRIVER=
TEST_SERVER_AND_PATH=
MTU_AND_VLAN_CONFIGURATION=
FIREWALL_OFFLOAD_AND_QOS=
TAILSCALE_VERSION_PATH=
VPN_PROTOCOL_PEER=
DNS_TOPOLOGY_AND_FILTERING=
ROUTERCLOUD_OR_STORAGE_TOPOLOGY=
NORMAL_SERVICE_LOAD=
DURATION_SECONDS=
STREAMS=
REPETITIONS=
RESULTS_AND_LIMITATIONS=
```

Save sanitized before/during/after CPU, load, RAM, interface counters, link
rates, dropped packets, temperature (when accessible), DNS health and application
responsiveness. Record the collection tools and versions. Measure probe overhead.

### Existing ASUS-specific snapshot (read-only)

These are *examples only*, not commands to run on OPNsense:

```sh
uptime
free
cat /proc/loadavg
cat /proc/meminfo | grep -E 'MemAvailable|SwapFree'
/jffs/addons/asus-edge/bin/dns-guard status
/jffs/addons/asus-edge/bin/dns-guard metrics
```

For future OPNsense, use supported FreeBSD/PF/OPNsense interface statistics,
CPU and memory observability, and its own DNS/service health checks. Document
exact commands only after they have been verified against the chosen version.
Do not copy Entware, iptables or JFFS commands across platforms.

## 3. Wired routing, NAT and firewall

With two controlled wired endpoints, collect LAN-to-WAN-routed results in
both directions and where possible a routed inter-subnet scenario. Avoid
measuring only the ISP cap or a shared switch path.

```sh
iperf3 -c <TEST_SERVER_IP> -t 60
iperf3 -c <TEST_SERVER_IP> -t 60 -R
iperf3 -c <TEST_SERVER_IP> -t 60 -P 4
iperf3 -c <TEST_SERVER_IP> -t 60 -P 4 -R
```

Record throughput, TCP retransmissions, RTT/loss if separately measured,
link utilization, CPU/core saturation, firewall drops and memory pressure.
Optional 180-second saturation runs require a safe change window. Record the
same set again with the normal filtering and monitoring services enabled.

## 4. VPN and encrypted overlays

Test independent cases rather than treating all VPNs as equivalent:

- Native WireGuard (only where both installations support materially comparable
  settings and both endpoints are controlled).
- Tailscale **direct path** with `tailscale ping <PEER>` and controlled iperf3
  over tailnet addresses (if configured and supported on that platform).
- Tailscale **Exit Node** only if that role is deliberately configured; mark
  DERP-relayed sessions as not directly comparable with direct sessions.
- Optional router-wide commercial VPN using the **same actual protocol and
  comparable endpoint region**. Do not equate OpenVPN to WireGuard/NordLynx.

Report both directions, encryption overhead, peer transport, CPU/core,
available RAM, DNS latency while VPN traffic saturates the path, and
critical-management responsiveness. Do not use a new VPN policy on production
without a separate approved plan.

## 5. DNS: latency, filtering and failure domains

The current ASUS reference has Pi-hole on-router, firmware dnsmasq for selected
local duties and **shared Unbound** upstream. DNS Guard v3.2 addresses the
**router-system resolver only**, not independent LAN-client failover.

For each platform, first document the actual DNS topology (client DHCP options,
listener, filtration, recursive upstream, network boundaries). Compare a fixed
set of end-to-end **client** queries over UDP and TCP; report warm/cold cache
separately, median/P95/P99 latency, SERVFAIL/timeout, DNSSEC validation, local
names and filtering parity. Keep a distinct direct-backend metric if applicable.

On ASUS, only when authorized and reachable, read-only examples are:

```sh
dig @<PIHOLE_IP> example.com A
dig @127.0.0.1 -p 53535 example.com A
```

These examples **must not** be run unchanged on OPNsense. A future independent
Pi-hole/Unbound pair or OPNsense Unbound may have different paths and failure
domains. No failover/redundancy result may be claimed from ordinary latency
measurements; outages and rollback need **separate isolated tests**. Issue
[#212](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212)
is **PAUSED pending suitable independent hardware**, with the previously found
direct-sidecar security bypass unresolved.

## 6. Storage and RouterCloud

On the ASUS, measure RouterCloud/SSD read, write and responsiveness with large
test files (> cache where practical), while recording USB mode, filesystem,
simultaneous network load and service state. An x86 OPNsense gateway is **not
assumed to host RouterCloud**: if it is relocated to an independent host,
compare the user-visible end-to-end service path and **separately** document
the different service placement. Do not infer an equivalent internal SSD test.

## 7. Wi-Fi and access-point boundary

The current ASUS provides Wi-Fi. A future OPNsense x86 firewall may provide
**no access point at all**; the ASUS might remain an AP or a different AP
might be used. Therefore Wi-Fi is its **own AP/radio benchmark**, not a direct
comparison of ASUS Wi-Fi against an OPNsense firewall.

At near/mid/far fixed client locations, record band, channel, width, RSSI,
negotiated PHY, measured throughput in both directions, retry/loss and
interference. Use unchanged wireless client and wired iperf3 server. Mark
80 MHz and 160 MHz results as different configurations rather than hiding
the difference. Do not imply 6 GHz or Wi-Fi 7 is supported on TUF-AX5400.

## 8. Normal-service coexistence, recovery and power

Repeat key wired, DNS and VPN cases with ordinary policy, Pi-hole, Unbound,
Tailscale, syslog, monitoring and RouterCloud workloads active **where actually
installed**. Measure remaining RAM, CPU, latency, drops and app health.

Reliability requires separate evidence: power-failure domain, reboot startup,
log/metrics continuity, validated restore, DNS availability and expected RTO/RPO.
A single current ASUS with backups is **recoverable**, not highly available.
For future OPNsense, measured restoration and stable operation are acceptance
gates, not assumptions based on higher hardware specifications.

## 9. Blank comparison table (results not yet collected)

| Scenario | ASUS baseline | Future OPNsense | Comparable? / reason |
| --- | --- | --- | --- |
| Wired NAT up/down — one TCP stream | TBD | NOT TESTED | |
| Wired NAT up/down — four TCP streams | TBD | NOT TESTED | |
| Routed inter-zone throughput | TBD | NOT TESTED | |
| Native WireGuard up/down | TBD | NOT TESTED | |
| Tailscale direct path | TBD | NOT TESTED | |
| Tailscale Exit Node | TBD | NOT TESTED | |
| Commercial VPN (same protocol/peer) | TBD | NOT TESTED | |
| Client cached DNS UDP/TCP median/P95/P99 | TBD | NOT TESTED | |
| Client uncached DNS, validation and filtering | TBD | NOT TESTED | |
| RouterCloud user-visible transfer | TBD | NOT TESTED | |
| CPU and MemAvailable under ordinary workload | TBD | NOT TESTED | |
| Full rebuild/restore time (separate validation) | TBD | NOT TESTED | |
| Wi-Fi/AP near/mid/far | TBD | N/A without separate AP | Different device role |

Provide units, three-run medians, absolute/percentage change **only when
comparable** and annotations of bottlenecks: ISP/link, CPU/core, encrypted
tunnel, DNS upstream, AP/RF, disk/USB or memory.

## 10. Acceptance, provenance and privacy

A future platform should be considered only if measured security, reliability,
operational maintainability and real workload benefits outweigh migration cost.
A higher throughput score alone does not authorize OPNsense deployment,
equipment purchase, ASUS decommissioning or DNS/DHCP/firewall cutover.

Preserve exact reproducible test commands, environment and **sanitized**
results. Historical RT-BE88U plans remain useful as an initial methodological
source, but **RT-BE88U migration is cancelled**. No live test, new hardware,
OPNsense VM or production change is claimed by this document.
