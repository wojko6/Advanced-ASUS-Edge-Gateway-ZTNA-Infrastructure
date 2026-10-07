# DNS Guard v3.2 live acceptance

This runbook covers the **remaining live acceptance only** for issue #192 and
PR #193. Source-controlled mock/static coverage and the full Validation suite
must already be green before using it.

DNS Guard v3.1 remains the rollback baseline until all checkpoints below pass.

## Preconditions

- Keep a trusted LAN recovery session open.
- Take a current project backup and keep the rollback path available.
- Confirm the candidate files deployed on the router match PR #193.
- Do not combine this validation with unrelated firewall, Tailscale, Pi-hole or
  Unbound changes.
- Preserve only sanitized evidence.

Record before-state output from:

```sh
/jffs/addons/asus-edge/bin/dns-guard status
/jffs/addons/asus-edge/bin/dns-guard metrics
/jffs/addons/asus-edge/bin/healthcheck.sh
cru l | grep AsusEdgeDNSGuard
cat /tmp/resolv.conf
```

Expected before state: break-glass inactive, exact once-per-minute watchdog
present, resolver state parseable, and the normal steady state using the
configured local Pi-hole resolver.

## A. Bounded fallback -> stable recovery

The purpose of this test is to exercise the v3.2 resolver state machine without
creating a broad network outage.

1. Force only the router system resolver into validated bootstrap mode:

```sh
/jffs/addons/asus-edge/bin/dns-guard fallback
cat /tmp/resolv.conf
/jffs/addons/asus-edge/bin/dns-guard metrics
```

2. Confirm that the resolver contains only validated independent WAN bootstrap
   nameservers, not loopback and not `EDGE_DNS_LOCAL_RESOLVER_IP`.

3. Allow the watchdog or bounded manual `dns-guard auto` checks to evaluate the
   healthy local path. With the default threshold of three, at least the
   recovery-streak progression and final promotion must be observable; do not
   weaken the threshold merely to make the test pass.

4. After promotion, record:

```sh
cat /tmp/resolv.conf
/jffs/addons/asus-edge/bin/dns-guard status
/jffs/addons/asus-edge/bin/dns-guard metrics
/jffs/addons/asus-edge/bin/healthcheck.sh
```

Acceptance:

- fallback succeeds immediately;
- bootstrap resolver set is independent and valid;
- recovery does not flap between local and bootstrap;
- final resolver returns to the configured Pi-hole target;
- recovery streak resets after promotion;
- break-glass remains inactive;
- healthcheck returns success.

If any step fails, stop the test and use the known-good rollback path rather
than continuing into reboot validation.

## B. Monitoring / fail-open warning

After the Fedora-side `dns-guard-metrics` helper and timer are deployed through
the existing monitoring workflow, confirm that VictoriaMetrics receives only
the coarse DNS Guard metrics documented in the repository.

During a bounded bootstrap interval, verify that Grafana sees current bootstrap
mode. The `dns_guard_sustained_failopen` rule must remain non-firing before its
10-minute window, become warning/firing only when bootstrap mode persists with
fresh collection data, and recover after the resolver returns to local mode.

Do not publish DNS query names, client identities or private addresses as alert
evidence.

## C. Full cold reboot

Run this only after sections A and B are accepted.

Before reboot:

```sh
/jffs/addons/asus-edge/bin/healthcheck.sh
sync
reboot
```

After the router is reachable again, allow normal boot recovery to settle and
record:

```sh
uptime
nvram get ntp_ready
pidof unbound
pidof pihole-FTL
pidof tailscaled
cru l | grep AsusEdgeDNSGuard
cat /tmp/resolv.conf
/jffs/addons/asus-edge/bin/dns-guard status
/jffs/addons/asus-edge/bin/dns-guard metrics
/jffs/addons/asus-edge/bin/healthcheck.sh
```

Acceptance:

- router reaches NTP-ready state without the historical DNS bootstrap deadlock;
- Unbound, Pi-hole and Tailscale recover;
- DNS Guard watchdog is present with the exact managed entry;
- final system resolver is the configured local Pi-hole target;
- break-glass is inactive;
- healthcheck passes;
- normal Internet/DNS functionality is restored.

Only after the bounded recovery test, monitoring acceptance and this cold reboot
all pass should issue #192 be closed and PR #193 leave draft status.
