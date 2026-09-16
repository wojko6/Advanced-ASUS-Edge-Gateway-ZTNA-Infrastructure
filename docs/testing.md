# Testing and evidence collection

## Test boundaries

This repository uses separate validation tracks. A PASS in one track must not be promoted into a claim about another layer.

- **CI/static/mock** validates repository logic in an isolated test environment.
- **Router live** validates the deployed ASUS gateway at a point in time.
- **Remote client** validates end-to-end Tailscale, DNS, firewall, and reachability behaviour from defined client roles.
- **Endpoint filtering** validates workstation-local content filtering and DNS-path preservation.
- **Mobile telemetry** records device-specific traffic observations under defined scenarios.

During the 2026-09-11 through 2026-09-25 unchanged-state router observation window, endpoint tests may continue but router configuration, services, firewall, DNS settings, filtering lists, and startup hooks remain unchanged. Router-side corroboration during this period is read-only.

## Static and mock tests

```sh
sh tests/test-static.sh
```

Run this suite on a Linux workstation or CI runner with Python 3, not on the
router. Python is used only by the test harness; deployed scripts remain POSIX
shell. The suite performs shell syntax checks, optional ShellCheck analysis,
boot-path regression checks, a mocked firewall render test and isolated recovery
tests. Recovery tests exercise a backup/restore round trip, manifest rejection,
copy failures, full installer rollback, first-install cleanup, firewall bypass
detection and exact printer-port matching. The evidence test also checks that
private healthcheck diagnostics are omitted.

GitHub Actions runs the main static/recovery/evidence suite plus focused regression
checks for configuration validation and maintenance/recovery paths:

```sh
sh tests/test-services-config-validation.sh
sh tests/test-services-tailscale-policy-static.sh
sh tests/test-healthcheck-config-validation.sh
sh tests/test-update-tailscale-static.sh
sh tests/test-restore-validation.sh
sh tests/test-wan-event-handler.sh
sh tests/test-wan-config-validation.sh
sh tests/test-install-rollback.sh
```

The configuration-validation tests reject invalid startup, healthcheck, firewall,
and WAN-event inputs before those values can reach runtime commands. The
services-start Tailscale policy guard verifies that a failed `tailscale up`, an
unavailable/not-ready local API, or a missing required `tailscaled` binary cannot
be reduced to a warning-only successful startup. The Tailscale update guard test
verifies that the managed recovery and healthcheck hooks are required before
package mutation and that package/recovery failures remain fatal. The restore
archive test accepts a known-good dry-run and rejects checksum tampering, payload
files omitted from the manifest, and malformed manifest records before any
restore apply is attempted. The WAN tests cover the normal recovery path plus
invalid configuration, DNS-unavailable, missing `resolv.conf`, and failed
Tailscale-restart cases using mocks. The isolated install/rollback test creates a
temporary test root, installs the managed WAN hook there, injects a controlled
installer failure, and verifies that the previous hook is restored. These CI
checks operate only on repository or temporary test data; they do not connect to
or modify the router.

These checks do not prove the router kernel supports every match module; live
validation remains required. The healthcheck requires managed filter jumps to
be first in their parent chains and a terminal DROP in each managed chain. A
failure can therefore indicate another component changed rule ordering. Review
the active rules from LAN before reapplying the managed firewall. Packet tests
remain necessary to verify actual access decisions.

## Router and remote-client security matrix

| Source | Destination | Test | Expected |
|---|---|---|---|
| WAN | Router:8443 | `nmap -Pn -p 8443 PUBLIC_IP` | filtered/closed |
| Admin tailnet device | Router:8443 | `nc -vz ROUTER_MANAGEMENT_IP 8443` | allowed |
| User tailnet device | Router:8443 | same | denied |
| Tailnet device | Router:22 | same | denied by default |
| Approved user | NAS:443 | `curl -kI https://NAS_IP/` | allowed |
| Tailnet device | Unlisted host:445 | `nc -vz HOST 445` | denied |
| Tailnet device | `1.1.1.1:53` | `dig @1.1.1.1 example.com` | answer via local resolver after REDIRECT |
| Unauthorized exit user | Public IP | select exit node + `curl` | denied by Grants |

Run WAN scans only against addresses you own or are authorized to test.

## Packet capture

Packet capture is a live-router validation technique and is **not** part of endpoint-only testing during the unchanged-state observation window unless a capture was already planned and can be performed without altering the validated configuration. Prefer existing read-only logs for endpoint DNS-path corroboration during the stability gate.

On the router:

```sh
tcpdump -ni tailscale0 -w /tmp/ts-dns.pcap 'port 53'
tcpdump -ni br0 -w /tmp/lan-dns.pcap 'port 53'
tcpdump -ni "$(nvram get wan0_gw_ifname)" -w /tmp/wan-dns.pcap 'port 53'
```

From a remote client:

```sh
dig @1.1.1.1 example.com A
```

Expected evidence:

- the request enters `tailscale0` with its original destination;
- netfilter REDIRECT sends classic DNS to the router-local port 53 listener;
- no equivalent plaintext request to `1.1.1.1:53` exits WAN;
- resolver upstream traffic reflects recursive resolution (or configured forwarding), not the client's original packet.

Analyze captures offline:

```sh
tshark -r ts-dns.pcap -Y 'dns' -T fields \
  -e frame.number -e frame.time_relative -e ip.src -e ip.dst -e dns.qry.name
```

Validate Unbound directly on its configured loopback port:

```sh
dig +dnssec -p 53535 @127.0.0.1 cloudflare.com A
```

### Android/Fedora exit-node DNS datapath comparison

A previous Android validation observed behaviour consistent with the intended
router DNS path, while later read-only observations raised an unresolved question
about the resolver path used by an Android exit-node client. Do not generalize
either observation into a universal claim. The controlled comparison below is
reserved for after the reference-router stability gate unless an equivalent
read-only observation can answer the question without changing router state.

Use the **same router configuration and exit node** for both clients. Record the
client OS/version, Tailscale version, transport (for example cellular or external
Wi-Fi), whether Android Private DNS or another encrypted resolver is enabled,
and whether Tailscale DNS is enabled. Change only one client-side variable at a
time.

For each Fedora and Android case, perform three distinct DNS probes:

1. a normal OS resolver lookup;
2. an explicit classic DNS query to a known external resolver address on port 53;
3. a query intended for the router resolver when the client configuration exposes
   that resolver path.

Correlate each probe with router-side observations on `tailscale0`, local dnsmasq
logging/counters where already available, the Unbound loopback listener, and WAN.
The goal is to distinguish these possibilities rather than assume one in advance:

- classic DNS enters `tailscale0` and is redirected to router dnsmasq, then Unbound;
- the client is using a different resolver supplied through Tailscale or the OS;
- Android Private DNS / DoT, application DoH/DoQ, another VPN, or proxy bypasses
  the classic port-53 path;
- a client-specific configuration difference explains the Fedora/Android result.

Acceptance evidence for the intended classic path requires correlation, not just
a successful lookup: the query must be observable entering through Tailscale,
the corresponding router-local resolver path must be observable, and the
client's original plaintext DNS packet must not simply leave WAN unchanged.
Encrypted DNS should be reported separately; the project's port-53 REDIRECT does
not claim to intercept DoT, DoH, or DoQ.

Do not publish raw packet captures, Tailscale addresses, real private hostnames,
resolver account identifiers, or unrelated queried domains. Keep raw evidence
private and publish only a sanitized result matrix with timestamps/scenario IDs
sufficient to correlate the observations.

## Firewall counters

Capture counters before and after each live-router test:

```sh
iptables -nvL EDGE_TS_INPUT --line-numbers
iptables -nvL EDGE_TS_FORWARD --line-numbers
iptables -t nat -nvL EDGE_TS_PREROUTING --line-numbers
```

If test evidence is published, sanitize counters and captures first. Never commit public IPs, auth material, or sensitive internal hostnames.

Use `scripts/collect-evidence.sh` for a router-side snapshot and complete the remote results in the [live-validation template](../evidence/live-validation-template.md). The collector cannot prove WAN reachability or Tailscale identity decisions; those require separate clients. Follow the [publication checklist](evidence-collection.md) before committing any output.

## Endpoint-filtering matrix

Use the detailed procedure in [endpoint-filtering-validation.md](endpoint-filtering-validation.md). The minimum matrix for Zen, and later AdGuard for Windows if tested, is:

| Test | Baseline | Filter enabled | Acceptance condition |
|---|---|---|---|
| Windows DNS resolver | record | record | expected router resolver remains authoritative |
| Normal DNS lookup | record | record | succeeds without unintended external DNS takeover |
| Normal HTTPS browsing | record | record | no unexpected certificate errors |
| Defined YouTube session | record observations | record observations | report only what was observed in the defined window |
| Representative websites | record | record | no unacceptable false positives/breakage |
| CPU/RAM | record when measured | record when measured | report measured delta, not an estimate |
| Disable/uninstall | n/a | verify | expected endpoint state/trust-store cleanup |

Do not run Zen and AdGuard simultaneously in a comparison unless interaction between them is the explicit test question. Otherwise the result is confounded.

## Mobile-telemetry matrix

Each phone is its own case study. Suggested scenarios:

| Scenario | Minimum record |
|---|---|
| Idle | duration, network state, relevant sanitized destinations/counts |
| Reboot/startup | observation window and startup-related destinations |
| Selected system app | app/action, duration, relevant destinations |
| Normal use | defined actions, duration, relevant destinations/counts |

Record model, OS/version, hardening/debloat state, network path, observation method, and limitations. Two Xiaomi devices with different OS versions are comparative cases, not a controlled before/after debloat experiment.

## Performance baseline

Measure router performance at idle and under three flows only when live-router performance testing is scheduled outside the unchanged-state stability gate: direct WAN, Tailscale subnet routing, and exit-node routing.

```sh
top -b -n 1
free
ping -c 30 TARGET
iperf3 -c TARGET -t 30 -P 1
iperf3 -c TARGET -t 30 -P 4
```

Record median/p95 latency, loss, one/four-stream throughput, CPU, RAM, temperature, firmware, Tailscale version, and test direction. Consumer router CPU is expected to be the exit-node bottleneck; measure rather than estimate.

Endpoint performance observations belong to the endpoint-filtering test and should be recorded separately from router throughput measurements.
