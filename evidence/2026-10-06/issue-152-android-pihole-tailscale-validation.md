# Issue #152 — Android Pi-hole/Tailscale source-scoped validation

**Status:** PARTIAL PASS — transport/DNS/management path validated; stronger
per-device Pi-hole filtering remains open

**Date:** 2026-10-06  
**Evidence class:** Live functional validation / sanitized  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton

## Purpose

Validate the first implementation phase of issue #152: route classic DNS from
one authorized Android Tailscale client through the existing Pi-hole stack
without consuming a second Android VPN slot and without breaking internal DNS,
RouterCloud or ASUS management access.

Deployment-specific client addresses, service URLs and private identifiers are
intentionally omitted.

## Target client conditions

```text
Wi-Fi:      OFF
LTE/5G:     ON
Tailscale:  ON
Exit node:  OFF
```

The exit-node-enabled Android DNS path is not included in this validation claim.

## Source-scoped Pi-hole path

The managed Tailscale NAT chain was extended with source-scoped TCP/UDP 53 DNAT
rules placed before the existing generic DNS REDIRECT fallback.

```text
Android classic DNS
  -> tailscale0
  -> EDGE_TS_PREROUTING
  -> source-scoped DNAT
  -> dedicated Pi-hole listener
  -> Pi-hole FTL / Gravity
  -> Unbound
```

Non-matching Tailscale clients keep the historical generic redirect through
firmware dnsmasq before Unbound. Live firewall counters increased on the
selected-client Pi-hole DNAT rule during the acceptance run.

## Pi-hole visibility

A fresh unique DNS marker generated from the Android client appeared in Pi-hole
analytics under the client's Tailscale source identity.

A known advertising-domain query was recorded by Pi-hole with Gravity blocking
status and the Android client received the configured blocking response.

## Internal DNS and RouterCloud

The internal RouterCloud hostname continued to resolve through the selected
Pi-hole path, and RouterCloud remained reachable over LTE/5G + Tailscale.

Troubleshooting established that the RouterCloud service address is a
router-local alias. The correct local firewall boundary is therefore INPUT, not
FORWARD. The final policy contains an admin-scoped INPUT rule for the service
endpoint.

## ASUS management path

The corrected management path is:

```text
authorized Tailscale source
  -> external TCP/8443
  -> source-scoped DNAT
  -> router LAN TCP/443
  -> ASUS httpds
```

Both NAT and post-DNAT INPUT counters increased during the Android acceptance
run, and administration through the supported hostname succeeded.

Raw Tailscale-IP WebUI access is not treated as the supported management method
and is not claimed by this artifact.

## Health and regression coverage

The post-deployment project healthcheck completed with:

```text
Summary: 0 failure(s), 0 warning(s)
```

Repository coverage includes dedicated contracts for source-scoped Pi-hole DNS
ordering, RouterCloud INPUT policy, ASUS HTTPS external-to-target-port DNAT,
post-DNAT INPUT handling, target-listener presence and invalid configuration.

The first PR #182 CI run exposed a stale Python recovery fixture that did not
model the new TCP/443 listener requirement. The production policy was not
changed for that failure; the fixture was corrected and the subsequent
validation suite passed.

## Private service-portal configuration recovery

Private `EDGE_PORTAL_*` URL keys were found missing from the live local
configuration after normalization. Only those private portal values were
restored from a pre-change backup; the new Pi-hole/Tailscale policy,
RouterCloud rules and management-port correction were not rolled back.
Personal Cloud was then configured as a local portal target.

No deployment-specific service URL or private address is published here.

## Result

The first issue #152 implementation phase is accepted for the tested target
conditions:

- Tailscale remains the only Android VPN/tunnel service;
- selected classic DNS reaches Pi-hole over Tailscale;
- Pi-hole retains the selected client identity;
- internal naming remains functional;
- a known advertising domain is blocked by Gravity;
- RouterCloud remains reachable;
- authorized ASUS WebUI management remains functional;
- the project healthcheck remains clean.

## Remaining scope

Issue #152 is intentionally still open. Remaining work includes the dedicated
Pi-hole client/group assignment for both Android LAN and Tailscale identities,
stronger curated per-device filtering, final allowlist review,
banking/payment and Android-connectivity compatibility checks, and any separate
exit-node/encrypted-DNS work.

See [Android global DNS filtering through Pi-hole and Tailscale](../../docs/android-pihole-tailscale-policy.md)
and the [troubleshooting case study](../../docs/case-studies/android-tailscale-pihole-debugging.md).
