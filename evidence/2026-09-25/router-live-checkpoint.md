# Router live checkpoint — 2026-09-25

## Scope

Sanitized live validation of the reference ASUS TUF-AX5400 deployment on
GNUton `3004.388.11_1-gnuton1_tuf`.

The session was intentionally read-only except for client-side Tailscale
exit-node selection during a bounded diagnostic attempt. No router policy,
service, package, or firewall configuration was changed.

Deployment-specific Tailscale addresses, WAN addresses and unrelated
identity data are omitted.

## Router state

Observed runtime state:

```text
firmware:              3004.388.11_1-gnuton1_tuf
Entware filesystem:    mounted rw on SSD
router-data filesystem mounted rw on SSD
JFFS usage:            30%
Entware usage:         2%
router-data usage:     1%
swap 1:                512 MiB active
swap 2:                2 GiB active
```

Core services were running:

```text
tailscaled: RUNNING
unbound:    RUNNING
syslog-ng:  RUNNING
dnsmasq:    RUNNING
```

Tailscale CLI/daemon version reported:

```text
1.102.3
```

The reference router continued to advertise exit-node capability.

## DNS and managed policy state

The active local project configuration reported:

```text
EDGE_INTERCEPT_DNS=1
EDGE_ENFORCE_LAN_DNS=1
EDGE_BLOCK_LAN_DOT=1
EDGE_ENABLE_EXIT_NODE=1
EDGE_ALLOW_ROUTER_HTTPS=1
EDGE_ALLOW_ROUTER_SSH=0
EDGE_REQUIRE_DLNA_DISABLED=1
EDGE_REQUIRE_SMB_DISABLED=1
```

The live firewall contained the expected project-owned parent jumps for:

- `EDGE_TS_INPUT`;
- `EDGE_TS_FORWARD`;
- `EDGE_LAN_DOT_FORWARD`;
- `EDGE_LAN_DNS_PREROUTING`;
- `EDGE_TS_PREROUTING`.

A direct query to Unbound on loopback port 53535 returned `NOERROR` with
the DNSSEC `AD` flag.

## Project health check

The deployed project health check passed every reported check, including:

- SSD/Entware readiness and required swap;
- Tailscale connectivity and `tailscale0`;
- `netfilter-mode=off` and absence of competing Tailscale chains;
- exit-node IPv4 forwarding, project WAN-forward rule, platform WAN NAT and
  established/related return handling;
- dnsmasq interface integration;
- project IPv4 and IPv6 chain ordering and unconditional deny tails;
- printer exposure controls;
- active-hook permission checks;
- LAN classic-DNS and direct-DoT policy checks;
- Unbound process/control/DNSSEC validation;
- syslog-ng availability.

Final result:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

The inspected kernel/system error filter returned no matching OOM, panic,
filesystem-I/O, read-only-filesystem or EXT4 error entries.

## Controlled LAN DNS interception check

The Fedora client was first confirmed to route the external DNS test
destination through the normal LAN gateway.

A controlled UDP/53 query intentionally addressed to an external resolver
succeeded while the managed LAN redirect counter increased by exactly one
packet.

A controlled TCP/53 query to the same external resolver also succeeded
while the managed TCP redirect counter increased by exactly one packet.

Observed production counter deltas:

```text
EDGE_LAN_DNS_PREROUTING UDP redirect: +1 packet
EDGE_LAN_DNS_PREROUTING TCP redirect: +1 packet
```

This reconfirms the deployed classic IPv4 LAN DNS interception mechanism
on the current firmware.

## Controlled direct-DoT check

A direct TLS connection attempt to an external resolver on TCP/853 failed
with `Connection refused`.

At the same time the production DoT rule changed by:

```text
EDGE_LAN_DOT_FORWARD REJECT: +1 packet / +60 bytes
```

This correlates the client failure with the configured project rule.

The claim remains limited to direct IPv4 TCP/853. It does not cover DoH,
DoQ, VPN-carried DNS or application-specific encrypted resolver transports.

## Controlled Tailscale classic-DNS check

A UDP/53 query sent to the router through its Tailscale address succeeded.

The corresponding managed Tailscale DNS redirect counter increased by
exactly one packet:

```text
EDGE_TS_PREROUTING UDP redirect: +1 packet
```

The router health check independently confirmed dnsmasq/Unbound integration
and DNSSEC validation during the same checkpoint.

This is a current-firmware interception/resolver-health reconfirmation. It
is not presented as a replacement for the full packet-by-packet
`tailscale0 -> REDIRECT -> dnsmasq -> Unbound` correlation published on
2026-09-22.

## Exit-node diagnostic boundary

A new same-day exit-node packet-correlation attempt was not accepted as new
datapath evidence.

The initial Fedora test did not have an exit node selected, so the
controlled ICMP flow used the normal LAN route and the project
`EDGE_TS_FORWARD -> WAN` counter did not increase.

A later capture attempt could not start because the router shell did not
provide the expected `timeout` command. Client routing was subsequently
inspected explicitly, revealing when the ASUS exit node was selected and
when it was not.

The previously published 2026-09-23 fixed-flow `tailscale0`/WAN capture
therefore remains the authoritative current-firmware AUDIT-02 datapath
evidence.

## GeForce NOW normal-use follow-up

Later in the same day, approximately one hour of normal GeForce NOW use
over Gigabit Ethernet was operator-observed with stable latency and no
application-reported packet loss.

The endpoint Zen filter was toggled during normal use without an observed
difference in the GeForce NOW loss/latency behaviour.

This is an observational follow-up, not a controlled proof that Zen can
never affect the workload.

An attempted Exit Node A/B/A overlay comparison was not accepted as a
symmetric experiment because route verification later showed that the
nominal final A segment still had the exit node selected. The screenshots
are therefore not used to claim an exit-node latency effect.

After diagnosis, the client exit node was explicitly disabled and the
normal Internet route was re-verified through the wired LAN interface.

## Result

For the 2026-09-25 checkpoint:

```text
router health:                         PASS
LAN classic DNS interception UDP/TCP: PASS
LAN direct DoT/853 block:              PASS
Tailscale classic DNS interception:    PASS
current-firmware resolver health:      PASS
new exit-node packet correlation:      NOT COMPLETED
```

The lack of a new exit-node capture is not treated as a router failure.
The existing 2026-09-23 current-firmware exit-node evidence remains valid
within its documented scope.
