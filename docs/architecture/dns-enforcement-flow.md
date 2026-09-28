# DNS Enforcement Flow

## Purpose

This is the canonical DNS-policy diagram for the current reference deployment.
It separates the **Pi-hole-filtered main-LAN DHCP path** from the existing
project classic-DNS interception paths that still terminate at firmware
dnsmasq. It also keeps the direct LAN DoT control and out-of-scope encrypted-DNS
transports explicit.

```mermaid
flowchart TD
    subgraph DHCP["VALIDATED — main-LAN DHCP path"]
        L["DHCP-managed LAN client<br/>TCP/UDP 53"] --> PIP["Pi-hole dedicated LAN alias :53"]
        PIP --> PH["Pi-hole FTL / Gravity"]
        PH --> U["Unbound<br/>127.0.0.1:53535<br/>TCP + UDP"]
    end

    subgraph LAN["VALIDATED — LAN classic-DNS interception on br0"]
        E["LAN client selects another<br/>TCP/UDP 53 destination"] --> LP["nat PREROUTING<br/>-i br0"]
        LP --> LC["EDGE_LAN_DNS_PREROUTING"]
        LC -->|"destination = Pi-hole alias"| PB["RETURN<br/>intentional Pi-hole path"]
        PB --> PIP
        LC -->|"destination = router LAN IP :53"| LR["RETURN<br/>normal local path"]
        LC -->|"other destination TCP/UDP 53"| LX["REDIRECT to local :53"]
        LR --> D["firmware dnsmasq :53"]
        LX --> D
        D -->|"no-resolv<br/>server=127.0.0.1#53535"| U
    end

    subgraph TS["VALIDATED HISTORICAL PATH — Tailscale classic DNS"]
        T["Tailscale client<br/>TCP/UDP 53"] --> TP["nat PREROUTING<br/>-i tailscale0"]
        TP --> TC["EDGE_TS_PREROUTING"]
        TC -->|"TCP/UDP 53"| TX["REDIRECT to local :53"]
        TX --> TI["EDGE_TS_INPUT<br/>accept classic DNS from tailnet CIDR"]
        TI --> D
    end

    U --> R["Recursive / authoritative DNS path"]

    subgraph DOT["BLOCKED — direct IPv4 LAN DoT"]
        DL["LAN client on br0<br/>TCP 853"] --> DF["filter FORWARD<br/>-i br0"]
        DF --> DC["EDGE_LAN_DOT_FORWARD"]
        DC --> DR["REJECT<br/>tcp-reset"]
    end

    subgraph OUT["PENDING / OUT OF CURRENT ENFORCEMENT CLAIM"]
        H["DoH / HTTPS 443"]
        Q["DoQ / QUIC"]
        V["VPN-carried DNS"]
        A["Application-specific encrypted DNS"]
        I6["IPv6 resolver paths"]
    end
```

## Validated scope and limitations

- **Main-LAN DHCP DNS:** the 2026-09-28 cutover advertises only the dedicated
  Pi-hole listener to the tested main-LAN DHCP client. Pi-hole forwards allowed
  external queries to Unbound on `127.0.0.1:53535`.
- **Local naming:** Pi-hole DHCP remains disabled. Conditional reverse DNS uses
  firmware dnsmasq as the local naming source; a post-reboot active lease
  returned the same local hostname through both resolvers.
- **LAN/br0 classic DNS enforcement:** when `EDGE_ENFORCE_LAN_DNS=1`, traffic
  intentionally addressed to the configured Pi-hole alias is allowed to reach
  Pi-hole. Other external TCP/UDP 53 destinations are redirected to the router
  local port 53 and therefore terminate at firmware dnsmasq before Unbound.
- **Tailscale/tailscale0 classic DNS:** the previously validated
  `EDGE_TS_PREROUTING` redirect still terminates at firmware dnsmasq. The
  Pi-hole migration does **not** silently promote this historical path into a
  Pi-hole-filtered claim.
- **Resolver chain:** both Pi-hole and firmware dnsmasq use Unbound on
  `127.0.0.1:53535` for ordinary external resolution.
- **Direct LAN DoT:** when `EDGE_BLOCK_LAN_DOT=1`,
  `EDGE_LAN_DOT_FORWARD` rejects direct IPv4 TCP/853 traffic arriving on
  `br0` with tcp-reset.
- The DoT rule is **not** a universal DoT control. It does not claim equivalent
  enforcement for Tailscale, other ingress interfaces, tunnels or IPv6.
- DoH/HTTPS 443, DoQ/QUIC, VPN-carried DNS, application-specific encrypted
  resolvers and IPv6 resolver paths remain separate assessment items.

## DNS analytics visibility boundary

Issue #108 builds analytics from the query history already recorded by Pi-hole
FTL for the validated DHCP-managed main-LAN path. That is an observability
overlay, not a change to the resolver datapath shown above.

The live Grafana dashboard therefore describes its dataset as
**Pi-hole-visible DNS activity**. Queries redirected to firmware dnsmasq and
encrypted-DNS traffic that bypasses the local resolver are not automatically
present in that dataset.

The Tailscale boundary is now directly demonstrated: a controlled classic-DNS
query with Tailscale active was captured on `tailscale0` but absent from
Pi-hole RAM/disk history and the Fedora collector. With Tailscale disabled, the
same controlled client was visible through the ordinary main-LAN Pi-hole path.
The hard-coded external LAN interception path remains to be correlated
separately.

Broad dnsmasq query logging is not enabled merely to duplicate Pi-hole history.

See [Network DNS Visibility / Client Activity Analytics](../network-dns-visibility-client-activity-analytics.md).

## 2026-09-28 Pi-hole cutover validation

The reference main LAN completed a staged Pi-hole migration:

- dedicated Pi-hole listener and FTL persistence passed;
- OISD source/Gravity parity was measured;
- main-LAN DHCP was changed to advertise only Pi-hole;
- reverse DNS was validated through firmware dnsmasq for an active lease;
- Diversion, uiDivStats, Stubby and an inactive NextDNS hook were removed;
- an intermediate reboot exposed missing swap activation and a Tailscale
  Go-runtime OOM;
- pre-Entware swap activation was restored;
- the final reboot returned swap, Tailscale, Pi-hole, Unbound and DHCP DNS
  automatically.

See the [final case study](../pi-hole-on-router-case-study.md) and
[sanitized cutover evidence](../../evidence/2026-09-28/pi-hole-main-lan-cutover-validation.md).

## Historical current-firmware interception evidence

The classic-DNS interception datapath itself was revalidated on 2026-09-27.
The controlled Fedora test established the tested historical path:

Fedora → Tailscale exit-node path → tailscale0 → EDGE_TS_PREROUTING →
REDIRECT :53 → firmware dnsmasq :53 → Unbound 127.0.0.1:53535.

Both UDP/53 and TCP/53 showed exact +1 managed REDIRECT counter deltas and
matching dnsmasq-to-Unbound loopback traffic in the controlled window.

That evidence remains valid for the tested interception mechanism, but it is not
evidence that the path now traverses Pi-hole.

## Traceability

- [router/scripts/firewall-start](../../router/scripts/firewall-start)
- [config/dnsmasq.conf.add.example](../../config/dnsmasq.conf.add.example)
- [config/unbound.conf.example](../../config/unbound.conf.example)
- [AUDIT-03 current-firmware DNS datapath revalidation — 2026-09-27](../../evidence/2026-09-27/audit-03-current-firmware-dns-datapath-revalidation.md)
- [Pi-hole single-client pilot — 2026-09-28](../../evidence/2026-09-28/pi-hole-single-client-pilot-validation.md)
- [Pi-hole main-LAN cutover — 2026-09-28](../../evidence/2026-09-28/pi-hole-main-lan-cutover-validation.md)
