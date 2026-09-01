# Testing and evidence collection

## Static and mock tests

```sh
sh tests/test-static.sh
```

This performs shell syntax checks, optional ShellCheck analysis, boot-path regression checks, and a mocked firewall render test. It does not prove the router kernel supports every match module; live validation remains required.

## Security test matrix

| Source | Destination | Test | Expected |
|---|---|---|---|
| WAN | Router:8443 | `nmap -Pn -p 8443 PUBLIC_IP` | filtered/closed |
| Admin tailnet device | Router:8443 | `nc -vz ROUTER_MANAGEMENT_IP 8443` | allowed |
| User tailnet device | Router:8443 | same | denied |
| Tailnet device | Router:22 | same | denied by default |
| Approved user | NAS:443 | `curl -kI https://NAS_IP/` | allowed |
| Tailnet device | Unlisted host:445 | `nc -vz HOST 445` | denied |
| Tailnet device | `1.1.1.1:53` | `dig @1.1.1.1 example.com` | answer via local resolver after DNAT |
| Unauthorized exit user | Public IP | select exit node + `curl` | denied by Grants |

Run WAN scans only against addresses you own or are authorized to test.

## Packet capture

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
- DNAT directs classic DNS to the router;
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

## Firewall counters

Capture counters before and after each test:

```sh
iptables -nvL EDGE_TS_INPUT --line-numbers
iptables -nvL EDGE_TS_FORWARD --line-numbers
iptables -t nat -nvL EDGE_TS_PREROUTING --line-numbers
```

If test evidence is published, sanitize counters and captures first. Never commit public IPs, auth material, or sensitive internal hostnames.

## Performance baseline

Measure at idle and under three flows: direct WAN, Tailscale subnet routing, and exit-node routing.

```sh
top -b -n 1
free
ping -c 30 TARGET
iperf3 -c TARGET -t 30 -P 1
iperf3 -c TARGET -t 30 -P 4
```

Record median/p95 latency, loss, one/four-stream throughput, CPU, RAM, temperature, firmware, Tailscale version, and test direction. Consumer router CPU is expected to be the exit-node bottleneck; measure rather than estimate.
