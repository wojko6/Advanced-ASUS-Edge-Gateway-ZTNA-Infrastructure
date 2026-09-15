# Stability Gate checkpoint — 2026-09-15

## Scope

Read-only checkpoint collected during the 14-day unchanged-state observation period that began on 2026-09-11. No router configuration change was made as part of this checkpoint.

This artifact is intentionally sanitized. Tailscale addresses, LAN addresses, account identifiers, and other machine-specific identifiers from the raw command output are not published.

## Observation

Router-local time at collection: 2026-09-15 20:15 CEST.

Observed uptime:

```text
4 days, 4 hours, 26 minutes
load average: 0.76, 0.99, 0.91
```

## Health check

The deployed health check completed successfully:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

The check reported OK for the following relevant controls and dependencies:

- configuration readability;
- Entware `/opt` availability;
- required swap;
- `tailscaled` process and Tailscale connectivity;
- `tailscale0` presence;
- disabled Tailscale netfilter management and absence of competing Tailscale netfilter chains;
- dnsmasq inclusion of the Tailscale interface;
- IPv4 input, forwarding, and NAT policy chains;
- chain ordering and terminal DROP policy;
- source-scoped printer policy;
- disabled ASUS USB print-server state and closed router TCP/515;
- IPv6 input/forward guards and chain ordering;
- absence of legacy broad Tailscale ACCEPT/NAT rules;
- Unbound process/control interface;
- DNSSEC validation on the local Unbound listener;
- syslog-ng process.

## Memory and swap

Observed memory state:

```text
RAM total:               ~500 MiB
RAM available after cache/buffers: ~165 MiB
Swap total:              ~2.5 GiB
Swap used:               ~45 MiB
```

Both expected swap files were active. The larger data-volume swap carried the observed usage; the Entware-volume swap was available and unused at collection time.

No out-of-memory event was observed in the targeted recent-error check.

## Storage

The Entware filesystem was mounted and available through `/opt`.

Observed filesystem utilization:

```text
Entware volume: ~62.7 GiB total
Used:           ~723 MiB
Utilization:    1%
```

## Required services

The following required processes were observed running:

```text
tailscaled   RUNNING
unbound      RUNNING
syslog-ng    RUNNING
dnsmasq      RUNNING
```

Tailscale status showed the router connected to the tailnet and the expected peers present. Raw node addresses and account identifiers are intentionally omitted.

## DNS path

Observed listeners were consistent with the deployed DNS architecture:

- dnsmasq listening on router-local DNS endpoints;
- Unbound listening locally on port `53535` over TCP and UDP;
- the health check independently confirmed DNSSEC validation through Unbound using the AD flag.

A local Stubby listener was also observed. No configuration change was made because the deployed health check passed the intended Unbound/DNSSEC path and this checkpoint is part of an unchanged-state stability observation.

## Targeted recent-error check

A read-only search of the available router syslog for the following high-signal terms returned no matches during this checkpoint:

```text
oom
out of memory
segfault
panic
I/O error
read-only
filesystem error
```

Result language is intentionally limited to **not observed in the inspected log at collection time**; it is not a claim that such an event can never occur.

## Verdict

**PASS — Stability Gate checkpoint**

Evidence supporting the verdict:

```text
Health check:          0 FAIL / 0 WARN
Entware SSD:           OK
Required swap:         OK
Tailscale:             OK
Firewall/ZTNA policy:  OK
Unbound/DNSSEC:        OK
syslog-ng:             OK
Critical log matches:  none observed
Configuration changes: none
```

This checkpoint demonstrates a healthy observed state approximately four days into the current router uptime and during the ongoing unchanged-state observation period. It does **not** by itself establish long-term stability. The 14-day Stability Gate remains in progress and should only be closed after the full observation period is completed without a disqualifying router-side configuration change or unresolved stability failure.
