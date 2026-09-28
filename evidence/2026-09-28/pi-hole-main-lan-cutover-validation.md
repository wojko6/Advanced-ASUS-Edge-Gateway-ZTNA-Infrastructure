# Pi-hole main-LAN cutover and final reboot validation — 2026-09-28

## Scope

This sanitized artifact records the final main-LAN DHCP cutover from Diversion
to Pi-hole on the reference ASUS TUF-AX5400 and the recovery work required to
make the accepted startup path persistent.

It intentionally omits private client addresses, MAC addresses, hostnames,
Tailscale addresses/identities, WAN identifiers and raw household DNS history.

## Final active DNS/filtering components

```text
DHCP-managed main-LAN client
        |
        v
Pi-hole FTL — dedicated LAN alias :53
        |
        v
Unbound — loopback :53535
        |
        v
Internet

firmware dnsmasq
        |
        +-- DHCP
        +-- local/reverse names
        +-- existing classic-DNS interception endpoint
        |
        v
Unbound — loopback :53535
```

Pi-hole DHCP is disabled.

## Full-LAN DHCP result

The generated ASUS DHCP configuration originally appended the router itself as
an additional DNS server. A managed `dnsmasq.postconf` override was added so
main-LAN DHCP option 6 contains only the Pi-hole listener.

A real DHCP renewal on the controlled Fedora client confirmed:

- one DNS server learned from DHCP;
- that server was the dedicated Pi-hole listener;
- normal DNS resolution succeeded;
- a known blocklisted test returned Pi-hole's null-block response.

Other router networks were not changed by this cutover.

## Reverse DNS

Pi-hole conditional reverse DNS was configured for the private LAN reverse zone
with firmware dnsmasq as the local naming source.

After the final reboot, a device with an active DHCP lease returned the same
sanitized local hostname through:

- firmware dnsmasq directly;
- Pi-hole through conditional reverse DNS.

A separate address with no active lease returned `NXDOMAIN` from both paths
and was correctly treated as absence of current DHCP naming data.

## Removed components

The following active or stale components were removed after Pi-hole had passed
the staged and main-LAN checks:

- uiDivStats background jobs/processes and addon files;
- Diversion files, cron entries and dnsmasq/service hooks;
- ASUS DNS Privacy / Stubby;
- inactive historical NextDNS process/listener hook logic.

The final reboot confirmed that none returned.

## Resolver checks after cutover

Observed after the final reboot:

- ordinary A resolution through Pi-hole: successful;
- known blocklisted test through Pi-hole: null-block response;
- DNSSEC negative test through Pi-hole -> Unbound: `SERVFAIL`;
- Unbound listener: present on loopback:53535 TCP and UDP;
- Pi-hole listener: present on the dedicated LAN alias TCP/UDP 53;
- Pi-hole web listener: present on the dedicated LAN alias high port;
- firmware dnsmasq: still configured with `no-resolv` and the local Unbound
  upstream.

## Persistence failure discovered during cleanup

An intermediate reboot exposed a startup fault unrelated to Pi-hole filtering:

- both configured swap files were present on the SSD;
- `/proc/swaps` was empty;
- the active `post-mount` hook only checked swap state and did not execute
  `swapon`;
- Tailscale did not become ready;
- invoking the Tailscale client hit a Go runtime out-of-memory heap allocation
  failure.

Both existing swap files activated successfully when `swapon` was executed
manually. Tailscale then started normally.

## Persistent swap fix

The reference `post-mount` hook was corrected to activate a
`myswap.swp` file for each mounted data volume before the AMTM
`mount-entware.mod` startup path.

The next clean reboot observed:

| Check | Result |
| --- | --- |
| small Entware-volume swap | active |
| large data-volume swap | active |
| total swap capacity | about 2.5 GiB |
| Entware mount | active |
| tailscaled | running automatically |
| Tailscale interface | present |
| Pi-hole alias | present |
| Pi-hole FTL | running automatically |
| Unbound | running |
| Pi-hole FTL swap | 0 kB |
| Unbound swap | 0 kB |
| tailscaled swap | 0 kB |

Representative final resource snapshot:

- memory available: about 128 MiB;
- Pi-hole FTL RSS: about 10 MiB;
- Unbound RSS: about 17 MiB;
- tailscaled RSS: about 37 MiB;
- swap free: approximately the full configured 2.5 GiB at the checkpoint.

## Blocking-list parity result

After refreshing both stacks from the same OISD Big version:

| Item | Count |
| --- | ---: |
| normalized OISD source domains | 244,128 |
| Pi-hole Gravity domains | 244,128 |
| Diversion active domains | 244,126 |
| common domains | 244,126 |
| only Pi-hole | 2 |
| only Diversion | 0 |

The two Pi-hole-only entries were explained by Diversion's built-in essential
allowlist for their parent domains. Raw OISD ABP and dnsmasq2 variants normalized
to the same 244,128-domain set during the controlled source comparison.

## Query-history observation

Pi-hole FTL exposed persistent SQLite query data by client, domain, status,
upstream and reply time.

A bounded normal-use window on one controlled client recorded 217 queries.
This artifact deliberately does not publish the household domain list.

Status distribution in that window:

| Status class | Queries | Share |
| --- | ---: | ---: |
| forwarded | 154 | 70.97% |
| stale cache | 35 | 16.13% |
| cache | 18 | 8.29% |
| Gravity blocked | 6 | 2.76% |
| already forwarded | 4 | 1.84% |

Local/cache/block handling averaged 0.201 ms. Forwarded queries averaged
65.693 ms in that window.

These values are a bounded observation, not a general DNS-performance target.

## Rate-limit observation

Synthetic query-load testing reached Pi-hole FTL's configured per-client
1000-query/60-second limit. FTL logged the affected test client, returned
rate-limited responses during the interval and automatically ended the
limitation afterward.

The default limit was retained for normal operation.

## Service-removal validation

Final state after reboot:

```text
Stubby / DNS Privacy: absent / disabled
NextDNS:              no process, listener or hook
Diversion:            no active directory, binary, cron or hook
uiDivStats:           no active script, cron or background process
```

Private rollback/evidence copies were retained outside the public repository.

## Claim boundary

This validation supports the **main-LAN DHCP Pi-hole cutover** and final
reference-router startup path.

It does not prove that the existing project classic-DNS interception path for
arbitrary external resolver destinations is filtered by Pi-hole. That path
still terminates at firmware dnsmasq before Unbound. The existing Tailscale
classic-DNS redirect likewise requires separate revalidation if it is to be
moved behind Pi-hole filtering.

Encrypted DNS transports remain outside this artifact.
