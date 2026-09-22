# LAN classic-DNS enforcement prototype validation — 2026-09-22

**Status:** PASS  
**Evidence class:** Router live + LAN client / temporary controlled policy  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin  
**Client:** Fedora workstation on the reference LAN

## Purpose

Validate whether classic DNS from a LAN client can be transparently forced through the router resolver when the client explicitly targets an external DNS server.

## Route precondition

An initial attempt was not a LAN test because Fedora policy routing sent `8.8.8.8` through the Tailscale exit node.

Exit-node use was disabled for the test. The client route was then verified as the normal LAN path:

```text
8.8.8.8 via 192.168.50.1 dev <LAN-Wi-Fi-interface> src <LAN-client-address>
```

Deployment-specific client details are omitted from the public artifact.

## Temporary policy

A non-persistent `EDGE_LAN_DNS_TEST` chain was attached to `br0`.

The chain:

1. returned UDP/53 already addressed to the router DNS endpoint;
2. returned TCP/53 already addressed to the router DNS endpoint;
3. redirected other UDP/53 traffic to local port 53;
4. redirected other TCP/53 traffic to local port 53.

No JFFS hook or persistent configuration was changed for this prototype.

## Observation

After controlled external-DNS queries explicitly addressed to `8.8.8.8`, the temporary chain counters showed:

```text
external UDP/53 REDIRECT: 1 packet
external TCP/53 REDIRECT: 1 packet
```

Router-addressed UDP/53 traffic continued to increment the explicit router-return rule.

This demonstrates that, on the tested IPv4 LAN path, classic TCP/UDP port-53 traffic addressed to an external resolver can be redirected to the ASUS local resolver.

## Cleanup

The temporary parent jump was deleted, the test chain was flushed and deleted, and absence of the chain was verified.

## Claim boundary

This validates only the classic IPv4 DNS interception mechanism on the tested LAN path. It does not demonstrate interception of DoH, DoT, DoQ, VPN-carried DNS, application-specific encrypted resolver transports, or IPv6 DNS.

The production repository implementation was subsequently deployed and live-validated as a separate controlled change. See `lan-dns-enforcement-production-validation.md`. The prototype artifact remains bounded to the temporary-chain test described above.
