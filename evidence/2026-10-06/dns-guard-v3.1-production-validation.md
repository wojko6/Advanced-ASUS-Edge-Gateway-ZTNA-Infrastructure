# DNS Guard v3.1 production validation — 2026-10-06

## Scope

Sanitized evidence for the DNS bootstrap/fail-open remediation on the reference
ASUS TUF-AX5400.

This artifact records only the observations needed to support the public case
study. Deployment-specific public WAN addressing, credentials, and unrelated
household traffic are omitted.

## Pre-remediation finding

The router's Unbound startup path waits for firmware NTP readiness before
starting. The local Pi-hole uses Unbound on loopback port 53535 as its upstream.

A persistent router-system-resolver change to Pi-hole worked after the stack was
already healthy, but a subsequent cold boot produced working IP connectivity
with failed DNS resolution. Restoring independent WAN DNS recovered bootstrap.

## DNS Guard readiness

Before policy activation:

```text
BREAKGLASS=INACTIVE
NTP=PASS
UNBOUND=PASS
PIHOLE_LISTENER=PASS
PIHOLE_QUERY=PASS

CURRENT RESOLVER:
<wan-bootstrap-dns-1>
<wan-bootstrap-dns-2>

DECISION=LOCAL_DNS_READY
```

## Controlled promotion

Observed runtime transition:

```text
PROMOTE=PASS
AUTO=LOCAL_DNS

CURRENT RESOLVER:
nameserver 192.168.50.253

PRODUCTION_DNS=PASS
```

A second run returned the idempotent state:

```text
PROMOTE=ALREADY_LOCAL
AUTO=LOCAL_DNS
```

## Fail-open

With a test-only unreachable Pi-hole address:

```text
FALLBACK=PASS
AUTO=BOOTSTRAP_UNHEALTHY
AUTO_RC=0
FAIL_OPEN_POLICY=PASS
```

The real production resolver was not modified by that isolated test.

## Sticky break-glass

With the persistent break-glass flag present:

```text
BREAKGLASS=ACTIVE
PROMOTE=BLOCKED_BREAKGLASS
PROMOTE_RC=1
FALLBACK=PASS
```

After the test flag was removed, normal local-DNS eligibility returned.

## Watchdog

The production cron entry was present:

```text
* * * * * /jffs/addons/asus-edge/bin/dns-guard auto >/dev/null 2>&1 #AsusEdgeDNSGuard#
```

A real watchdog transition test observed:

```text
WATCHDOG_FALLBACK=PASS
WATCHDOG_RECOVERY=PASS
```

The final resolver returned to:

```text
nameserver 192.168.50.253
```

## Cold boot

After a full reboot, at approximately two minutes uptime:

```text
ntp_ready=1
UNBOUND=RUNNING
PIHOLE=RUNNING
TAILSCALE=RUNNING
BREAKGLASS=INACTIVE
NTP=PASS
UNBOUND=PASS
PIHOLE_LISTENER=PASS
PIHOLE_QUERY=PASS
DECISION=LOCAL_DNS_READY
```

The watchdog entry survived through managed startup recreation and the final
system resolver was Pi-hole.

A normal public lookup through the system resolver succeeded.

## Android Tailscale exit-node DNS

Android LTE routing showed the public test address using the Tailscale TUN
interface. A fresh unique hostname resolved to `1.1.1.1` and the ICMP probe
succeeded through the exit node.

A router capture on `any` showed the unique DNS exchange on loopback:

```text
lo  192.168.50.1 -> 192.168.50.253:53
    A? exitdns-final-<timestamp>.1-1-1-1.sslip.io

lo  192.168.50.253:53 -> 192.168.50.1
    A 1.1.1.1
```

This confirms that the router-side exit-node DNS path reached the local Pi-hole
alias after the cold boot. The capture intentionally omits unrelated traffic.

## Claim boundary

This evidence supports:

- independent DNS bootstrap;
- conditional promotion to Pi-hole;
- fail-open fallback;
- sticky break-glass;
- watchdog fallback/recovery;
- post-reboot persistence;
- the tested Android LTE Tailscale exit-node DNS path to Pi-hole.

It does not support a claim that encrypted DNS from arbitrary applications is
intercepted or that the same startup behavior applies to every router model.
