# Android global DNS filtering through Pi-hole and Tailscale

Tracking issue: #152.

## Goal

Provide DNS-level ad/tracker filtering for selected Android clients while
Tailscale remains the only Android VPN/tunnel service.

The design must preserve:

- Tailscale connectivity and routing;
- internal DNS such as `home.arpa`;
- RouterCloud access;
- ASUS management access;
- the existing dnsmasq -> Unbound fallback for other Tailscale clients.

No Android root access or second local-VPN ad blocker is required.

## Resolver design

The default Tailscale classic-DNS path remains:

    ordinary Tailscale client
            |
            v
        tailscale0
            |
            v
    EDGE_TS_PREROUTING
            |
            v
       REDIRECT :53
            |
            v
    firmware dnsmasq
            |
            v
         Unbound

Selected clients can instead use the optional source-scoped Pi-hole path:

    authorized Android Tailscale client
            |
            v
        tailscale0
            |
            v
    EDGE_TS_PREROUTING
            |
            | source match
            v
    DNAT -> dedicated Pi-hole DNS alias :53
            |
            v
       Pi-hole FTL
            |
            v
         Unbound

The source-scoped DNAT rules are installed before the generic Tailscale DNS
REDIRECT rules. Non-matching Tailscale clients therefore retain the historical
dnsmasq path.

## Configuration

The feature is opt-in.

    EDGE_TS_PIHOLE_SOURCES=""
    EDGE_TS_PIHOLE_DNS_IP=""

`EDGE_TS_PIHOLE_SOURCES` accepts space-separated Tailscale IPv4 addresses or
CIDRs.

`EDGE_TS_PIHOLE_DNS_IP` must be a local IPv4 address hosting the dedicated
Pi-hole DNS listener.

Both settings must be configured together. An incomplete or malformed pair is
rejected before firewall mutation.

Example values in public documentation must use documentation/test addresses.
Real deployment-specific Tailscale and LAN addresses remain private.

## Health checks

When the feature is enabled, the health check verifies:

- the configured Pi-hole destination is a local IPv4 address;
- TCP and UDP port 53 listeners exist on that destination;
- every configured source has both UDP and TCP DNAT rules;
- each source-scoped DNAT appears before the generic DNS REDIRECT fallback.

## Security boundaries

This feature controls classic IPv4 DNS over TCP/UDP port 53 entering through
the managed Tailscale interface.

It does not claim interception or blocking of:

- DoH over HTTPS;
- DoT;
- DoQ / QUIC;
- application-specific encrypted DNS;
- unrelated VPN-carried DNS;
- unvalidated IPv6 resolver paths.

DNS filtering also cannot remove advertising that shares the same hostname or
CDN as required application content.

## Validation procedure

A deployment is not considered complete merely because repository tests pass.

For each selected Android client validate:

1. home Wi-Fi DNS reaches Pi-hole;
2. cellular data with Tailscale active reaches Pi-hole;
3. Pi-hole records the original Tailscale client address rather than only the
   router address;
4. a synthetic permitted query is recorded as forwarded;
5. a known blocked test domain is recorded as blocked by Pi-hole;
6. internal `home.arpa` names continue to resolve;
7. Tailscale remains connected;
8. RouterCloud remains functional;
9. ASUS management access remains functional;
10. representative banking/payment and Android connectivity behavior shows no
    regression.

Exit-node use is a separate routing choice. Pi-hole filtering must work without
requiring the Android client to select the ASUS as an exit node.

## Rollback

Remove the client from `EDGE_TS_PIHOLE_SOURCES` and reapply the managed
firewall policy.

The client then returns to the existing generic Tailscale classic-DNS path:

    tailscale0
      -> EDGE_TS_PREROUTING
      -> REDIRECT :53
      -> dnsmasq
      -> Unbound

No Android-side VPN replacement or DNS reconfiguration is required for this
rollback.
