# Unauthorized tailnet management denial — 2026-09-23

## Scope

This artifact records a controlled negative management-access test against the reference ASUS edge gateway after the 2026-09-23 firmware and admin-source policy changes.

The test question was narrow:

> Can a distinct tailnet device that is **not** present in `EDGE_ADMIN_TS_SOURCES` establish a new TCP connection to the router management service on TCP/8443?

Real Tailscale IPv4 addresses, private hostnames, account identifiers, and underlying peer endpoint details are intentionally omitted.

## Roles

| Role | Authorization state | Purpose |
| --- | --- | --- |
| Fedora workstation | configured admin source | existing authorized comparison role |
| Android phone | configured admin source | existing authorized comparison role |
| Windows client | not configured as an admin source | negative-test source |
| ASUS edge gateway | target | router management endpoint on TCP/8443 |

The Windows client was a valid member of the same tailnet. This test therefore distinguishes tailnet membership from router-management authorization.

## Client observations

From the unauthorized Windows client:

1. A Tailscale peer ping to the router succeeded.
2. A TCP/8443 probe used the Tailscale interface and the client's tailnet source address.
3. The TCP connection did not establish: `TcpTestSucceeded=False`.

This rules out the simple explanation that the denial occurred because the client was not connected to Tailscale or could not reach the router as a peer.

## Router packet observation

A read-only packet capture was run on the router's `tailscale0` interface with a directional filter scoped to:

- the unauthorized tailnet source;
- the router tailnet destination;
- TCP destination port 8443.

The capture recorded:

- **5 packets captured**;
- **5 packets received by the filter**;
- **0 packets dropped by the kernel**.

All five captured packets were TCP SYN packets from the unauthorized client to TCP/8443. Each captured IP packet was 52 bytes.

The capture filter was intentionally directional. It proves that the five client-to-router SYN packets reached `tailscale0`; it does **not** independently prove the presence or absence of reverse-direction packets.

## Firewall correlation

The production `EDGE_TS_INPUT` policy already contained two source-specific TCP/8443 ACCEPT rules for the configured admin devices, followed by the production logging and terminal DROP path.

For the controlled measurement, a temporary source-specific rule was inserted **after** the production admin ACCEPT rules and **before** the existing LOG/DROP tail. It matched only:

- the unauthorized source;
- TCP destination port 8443;
- `ctstate NEW`.

The rule jumped to a temporary `EDGE_NEGTEST` chain containing only `RETURN`. It did not ACCEPT, REJECT, DNAT, or otherwise broaden access. Returning from the temporary chain resumed evaluation at the unchanged production LOG/DROP tail.

After the temporary test-chain counter was zeroed, one controlled client probe produced:

- **5 matched packets**;
- **260 matched bytes**.

This exactly matches the five 52-byte SYN packets recorded by `tcpdump`.

During the same controlled probe, the two production admin TCP/8443 ACCEPT counters did not increase. Therefore the unauthorized packets did not match either configured admin-source ACCEPT rule.

The aggregate production LOG/DROP counters also increased during the wider observation window, but other denied traffic was present. The complete aggregate delta is therefore not attributed solely to this test. The source-specific temporary counter is the attribution mechanism used for this evidence.

## Cleanup and post-test health

Immediately after the measurement:

1. the temporary jump from `EDGE_TS_INPUT` was deleted;
2. the temporary `EDGE_NEGTEST` chain was flushed and deleted;
3. explicit checks confirmed that neither the jump nor the chain remained;
4. the normal project health check was run.

Final production health result:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

No permanent firewall-policy change was made by this validation.

## Verdict

**PASS — negative management-access path live validated for the tested reference deployment on 2026-09-23.**

The distinct unauthorized tailnet client:

- remained a functioning Tailscale peer;
- delivered NEW TCP/8443 SYN packets to the router's `tailscale0` interface;
- did not match either configured admin TCP/8443 ACCEPT rule;
- could not establish the TCP/8443 management connection.

Together with the separately documented authorized Fedora HTTPS/TLS validation, this closes the previously outstanding role-specific negative probe for requirement F-01 in the tested environment.

## Claim boundary

This result validates the router-side management source policy for the tested tailnet client, router state, and date. It does not establish:

- universal behaviour for every tailnet identity or device;
- remote NAT traversal, DERP, or every possible underlying Tailscale transport path;
- phone-browser certificate validation;
- behaviour after future changes to admin sources, Grants, firewall rules, Tailscale, or firmware.

Re-run the authorized/unauthorized role matrix after material policy or platform changes.
