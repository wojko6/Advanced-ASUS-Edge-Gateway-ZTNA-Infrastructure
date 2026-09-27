# Issue #66 — clean startup and persistence evidence

Date: 2026-09-27  
Reference router: ASUS TUF-AX5400  
Reference firmware: GNUton / Asuswrt-Merlin `3004.388.11_1-gnuton1_tuf`

## Purpose

This evidence closes the acceptance target for issue #66 by recording three clean startup cycles on the same reference firmware/configuration after a startup-order correction.

No raw Tailscale addresses, node names, or other private management identifiers are included here.

## Problem observed before the final acceptance set

During an earlier reboot attempt, dnsmasq logged:

```text
cannot fork into background: Cannot allocate memory
```

The router later recovered automatically, but that reboot was intentionally not counted as a clean acceptance cycle.

Live inspection then showed an unfavorable startup order:

1. `/jffs/scripts/post-mount` sourced AMTM's `mount-entware.mod`.
2. `mount-entware.mod` synchronously started Entware through `rc.unslung` and requested `restart_dnsmasq`.
3. Entware startup included `S01syslog-ng`, `S06tailscaled`, `S61unbound`, and `S90taildns`.
4. `S61unbound` also performs a dnsmasq restart through its post-command.
5. The original AMTM-added `swapon` line in `post-mount` was reached only after the synchronous Entware startup returned.

This ordering did not by itself prove that lack of swap was the sole cause of the transient dnsmasq ENOMEM condition, but it exposed a concrete boot-order weakness that aligned with the failure window.

## Remediation applied

A minimal change was made to the live `/jffs/scripts/post-mount`:

- activate the mounted volume's `myswap.swp` before sourcing `mount-entware.mod`;
- verify the swap appears in `/proc/swaps`;
- log a sanitized `pre-Entware swap active` marker;
- preserve the original AMTM-generated lines and behavior.

The pre-change script was backed up on persistent ROUTER_DATA storage before modification. The installed script passed `sh -n` validation.

Because this was a persistent startup configuration change, the acceptance counter was reset and all three final cycles below were collected on the new reference configuration.

## Clean startup cycle results

| Cycle | Post-boot observation | Pre-Entware swap | dnsmasq ENOMEM | Storage / swap | Core services | Firewall persistence | Healthcheck | Error scans | Result |
|---|---|---|---|---|---|---|---|---|---|
| 1/3 | ~11 min uptime | confirmed before Entware startup | none | ENTWARE + ROUTER_DATA rw; both swap files active | tailscaled, Unbound, dnsmasq, syslog-ng running | managed parent jumps exactly once | 0 failures / 0 warnings, RC=0 | no matching OOM / filesystem-I/O / read-only / panic indicators | PASS |
| 2/3 | ~11 min uptime | confirmed before Entware startup | none | ENTWARE + ROUTER_DATA rw; both swap files active | tailscaled, Unbound, dnsmasq, syslog-ng running | managed parent jumps exactly once; stale temporary guards 0/0 | 0 failures / 0 warnings, RC=0 | current-boot and kernel scans clean for targeted indicators | PASS |
| 3/3 | ~10 min uptime | confirmed before Entware startup | none | ENTWARE + ROUTER_DATA rw; both swap files active | tailscaled, Unbound, dnsmasq, syslog-ng running | managed parent jumps exactly once; stale temporary guards 0/0 | 0 failures / 0 warnings, RC=0 | current-boot and kernel scans clean for targeted indicators | PASS |

## Cycle 3 detail

The final cycle showed the corrected order explicitly:

```text
pre-Entware swap active: /tmp/mnt/ENTWARE/myswap.swp
Entware: Starting Entware and Diversion services ...
...
tailscaled started and stabilized on attempt 1
tailscaled restarted after WAN DNS update
services startup completed
```

The WAN-DNS-driven Tailscale restart is expected project behavior: the WAN event handler deliberately restarts the Entware Tailscale service after the local DNS path becomes ready and then waits for Tailscale readiness. It required no manual repair.

Final state included:

- both persistent filesystems mounted read/write;
- both configured swap files active;
- Unbound 1.26.1 running and listening on loopback port 53535 over TCP and UDP;
- Tailscale connected and `tailscale0` present;
- dnsmasq and syslog-ng healthy;
- project firewall chains and parent jumps present exactly once;
- no stale temporary Tailscale guards;
- project healthcheck: `0 failure(s), 0 warning(s)`, `RC=0`;
- no matching targeted OOM, filesystem-I/O, read-only-filesystem, segfault, or kernel-panic indicators.

## Acceptance

Issue #66 acceptance criterion:

> Record at least three clean startup/power-on cycles total under the current reference firmware/configuration, with sanitized evidence and no hidden repair steps between boot and validation.

Result: **PASS — 3/3 clean startup cycles on the new reference configuration.**

No hidden repair step was performed between reboot and validation in the three accepted cycles.

## Follow-up

This evidence validates the current reference startup/persistence behavior. It does not replace longer-duration normal-use acceptance tracked separately, nor does it prove that the pre-fix dnsmasq ENOMEM condition could never have another contributing factor. The startup-order weakness itself is corrected and the failure did not recur in the three-cycle acceptance set.
