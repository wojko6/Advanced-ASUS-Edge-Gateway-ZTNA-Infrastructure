# ASUS router platform benchmark plan

This document defines a reproducible benchmark for comparing the project's
current ASUS TUF-AX5400 edge gateway with a future ASUS RT-BE88U.

Tracking: #194

The purpose is not to chase synthetic peak numbers. The purpose is to measure
the workloads that matter to this repository: routed traffic, Tailscale /
WireGuard, DNS, storage-backed RouterCloud services, monitoring overhead and
real Wi-Fi behavior.

## 1. Comparison principle

The TUF-AX5400 result becomes the baseline. After the RT-BE88U is available,
repeat the same matrix with the same test endpoints and equivalent configuration.

A result is considered directly comparable only when these variables are
recorded and materially equivalent:

- router firmware and build;
- Tailscale version;
- test client and client NIC;
- remote/server endpoint;
- link speed and duplex;
- MTU;
- test duration and stream count;
- Wi-Fi channel, width and test location;
- normal project services enabled during the run.

Do not disable firewall, DNS enforcement, monitoring or other production
controls merely to improve a score.

## 2. Evidence header

Record this before every benchmark session.

```text
DATE=
ROUTER_MODEL=
ROUTER_FIRMWARE=
ROUTER_UPTIME=
TAILSCALE_VERSION=
WAN_LINK=
LAN_LINK=
CLIENT=
CLIENT_OS=
CLIENT_NIC=
IPERF3_VERSION=
TEST_TOPOLOGY=
NOTES=
```

On the router also capture a before/after snapshot:

```sh
uptime
free
cat /proc/meminfo | grep -E 'MemAvailable|SwapFree'
cat /proc/loadavg
/jffs/addons/asus-edge/bin/dns-guard status
/jffs/addons/asus-edge/bin/dns-guard metrics
/jffs/addons/asus-edge/bin/healthcheck.sh
```

## 3. Wired routing / NAT

### 3.1 Single stream

Use a controlled iperf3 endpoint whenever possible.

```sh
iperf3 -c <SERVER_IP> -t 60
iperf3 -c <SERVER_IP> -t 60 -R
```

Run each direction three times.

Record:

- throughput;
- retransmits;
- router load;
- available memory;
- interface/link speed.

### 3.2 Parallel streams

```sh
iperf3 -c <SERVER_IP> -t 60 -P 4
iperf3 -c <SERVER_IP> -t 60 -P 4 -R
```

If the platform is clearly saturated, extend one run to 180 seconds to look for
thermal or CPU-frequency related degradation.

## 4. Native WireGuard

Only use this section when both routers can be tested against the same peer and
with materially identical cryptographic/network settings.

Record:

- peer topology;
- endpoint link speed;
- MTU;
- upload/download throughput;
- router load and memory;
- whether hardware acceleration is relevant or bypassed by the tunnel path.

Do not compare a local peer test on one router with an Internet-limited peer on
the other.

## 5. Tailscale

Tailscale is a first-class project workload and must be tested separately from
generic WireGuard.

Before each run capture:

```sh
tailscale status
tailscale ping <PEER>
```

Record whether the path is direct or relayed.

### 5.1 Direct peer throughput

Run iperf3 through the Tailscale addresses:

```sh
iperf3 -c <TAILSCALE_PEER_IP> -t 60
iperf3 -c <TAILSCALE_PEER_IP> -t 60 -R
iperf3 -c <TAILSCALE_PEER_IP> -t 60 -P 4
```

### 5.2 Exit Node

With a controlled client using the router as Exit Node, record:

- downstream throughput;
- upstream throughput;
- latency;
- whether the Tailscale path is direct;
- router load/memory.

Internet speed-test results may be kept as secondary evidence, but a controlled
iperf3 path is preferred where possible.

## 6. DNS stack

The production DNS path is part of the benchmark because performance must not
come at the cost of DNS Guard reliability.

Before and after every DNS test require:

```sh
/jffs/addons/asus-edge/bin/dns-guard status
/jffs/addons/asus-edge/bin/dns-guard metrics
cat /tmp/resolv.conf
```

Expected steady state:

```text
mode_local = 1
mode_bootstrap = 0
breakglass_active = 0
```

Test both the Pi-hole listener and Unbound directly where appropriate:

```sh
dig @<PIHOLE_IP> example.com A
dig @127.0.0.1 -p 53535 example.com A
```

For latency testing, use a fixed query list and separate cached from uncached
runs. Record median and high-percentile behavior rather than only one query.

A benchmark run is invalid if it accidentally triggers sustained DNS fail-open
unless the test is specifically designed to measure that behavior.

## 7. RouterCloud / USB storage

When the same USB SSD can be reused on both platforms, measure sequential
read/write through the actual service path used by the project.

Record:

- filesystem;
- USB link mode;
- file size;
- transfer direction;
- average throughput;
- router CPU/load;
- available RAM;
- whether RouterCloud remains responsive during the transfer.

Prefer a multi-gigabyte file to avoid measuring cache only.

## 8. Wi-Fi 5 GHz

Use the same wireless client, same iperf3 server and fixed physical test points.

Suggested locations:

1. near: same room;
2. mid: one typical interior barrier;
3. far: existing difficult/remote location used consistently for both routers.

For each point record:

- channel;
- channel width;
- negotiated PHY rate;
- RSSI if available;
- measured TCP throughput;
- packet loss/retries if available.

Run both upload and download directions.

Do not compare a 160 MHz clean-channel result against an 80 MHz congested result
without clearly marking the configuration difference.

## 9. Normal service-load test

The project router is not an empty benchmark appliance. Repeat one sustained
network test while the normal stack is active:

- Tailscale;
- Pi-hole;
- Unbound;
- DNS Guard;
- syslog-ng;
- RouterCloud;
- project firewall;
- normal monitoring hooks.

Capture process/memory/load snapshots during the run.

This test is especially important when comparing 512 MB-class and 2 GB-class
platforms because headroom and service coexistence matter as much as peak
throughput.

## 10. Result template

Use median values from at least three comparable runs.

| Scenario | TUF-AX5400 | RT-BE88U | Delta | Notes |
|---|---:|---:|---:|---|
| NAT single-stream down | TBD | TBD | TBD | |
| NAT single-stream up | TBD | TBD | TBD | |
| NAT 4-stream down | TBD | TBD | TBD | |
| NAT 4-stream up | TBD | TBD | TBD | |
| WireGuard down | TBD | TBD | TBD | |
| WireGuard up | TBD | TBD | TBD | |
| Tailscale direct down | TBD | TBD | TBD | |
| Tailscale direct up | TBD | TBD | TBD | |
| Tailscale Exit Node down | TBD | TBD | TBD | |
| Tailscale Exit Node up | TBD | TBD | TBD | |
| Pi-hole cached latency | TBD | TBD | TBD | |
| Unbound uncached latency | TBD | TBD | TBD | |
| RouterCloud/USB read | TBD | TBD | TBD | |
| RouterCloud/USB write | TBD | TBD | TBD | |
| Wi-Fi near down | TBD | TBD | TBD | |
| Wi-Fi mid down | TBD | TBD | TBD | |
| Wi-Fi far down | TBD | TBD | TBD | |
| MemAvailable under normal load | TBD | TBD | TBD | |

## 11. Acceptance / interpretation

The final comparison should identify the bottleneck for each platform instead of
only reporting that one number is larger.

Examples:

- 1 GbE link-limited;
- CPU-limited tunnel throughput;
- remote/ISP-limited;
- Wi-Fi RF/client-limited;
- storage/USB-limited;
- memory-headroom constrained.

The upgrade is considered architecturally meaningful when it moves one or more
project-relevant bottlenecks while preserving the security and reliability
baseline.

## 12. Public evidence rules

Do not commit:

- public/WAN IP addresses;
- Tailscale node identities or private account information;
- SSH keys or credentials;
- DNS query history containing household/client activity;
- router configuration secrets.

Sanitize hostnames and addresses where they are not necessary to reproduce the
methodology.

The final benchmark should preserve exact commands, versions, durations and
sanitized results so it can be reused as a migration case study.
