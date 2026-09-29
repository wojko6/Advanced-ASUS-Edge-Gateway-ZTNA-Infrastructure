# Issue #127 — LAN management and WAN exposure hardening validation

**Status:** PASS  
**Date:** 2026-09-29  
**Evidence class:** Router live / controlled maintenance / sanitized  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton

## Purpose

Validate and reduce the remaining router-management and automatic-WAN-exposure
surface without changing multiple unrelated trust boundaries at once.

This evidence corresponds to issue #127.

## Pre-change read-only assessment

The router was inspected before any modification.

Observed management state:

- WAN WebUI access was disabled;
- Telnet was disabled;
- SSH was enabled for LAN administration on the configured non-default port
  1122;
- HTTPS WebUI was available on LAN port 8443;
- the platform LAN access-restriction feature was not yet enabled.

Observed automatic/static exposure state:

- main-WAN UPnP was disabled;
- `miniupnpd` was not running;
- no UDP 1900 or 5351 listener was present;
- runtime UPnP NAT/filter chains contained no dynamic mapping rules;
- Port Trigger was disabled and had no configured rules;
- the DMZ-host field was empty;
- WAN ping was disabled;
- one stale static forward remained: WAN TCP 20 and 21 were forwarded to
  SSH/22 on an inactive LAN host.

The stale forward target did not resolve as a live neighbor and had no current
DHCP lease, static DHCP record or custom-client record. A small packet counter
on WAN TCP/21 was observed but was not treated as evidence that the service was
legitimately in use.

The router's own FTP service remained enabled for local use with WAN FTP access
disabled.

## Change 1 — remove stale static WAN forwarding

Before changing state, the existing port-forward enable flag and complete rule
value were written to a root-readable rollback artifact on JFFS.

The stale static forwarding rule was then removed, static port forwarding was
disabled, NVRAM was committed and the firewall was rebuilt.

Post-change validation confirmed:

- the static forwarding rule list was empty;
- the platform VSERVER chain no longer contained the TCP 20/21 DNAT entries;
- the remaining VSERVER path contained only the empty runtime UPnP chain;
- project-owned Tailscale management/DNS rules remained present after the
  firewall rebuild;
- the deployed project health check completed successfully.

Health-check result:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

## Change 2 — restrict normal-LAN router administration

The Fedora administration workstation was identified from the active SSH
session. Fedora NetworkManager configuration was checked and confirmed to use a
stable per-SSID Wi-Fi MAC policy. A dedicated DHCP reservation was therefore
installed for the administration workstation before enforcing the allowlist.

A separate rollback script was prepared on JFFS before enabling the access
restriction.

The platform access-restriction feature was then enabled for one authorized
normal-LAN administration host with access type `3`:

- WebUI (`1`);
- SSH (`2`);
- combined WebUI + SSH (`3`).

The resulting IPv4 firewall policy:

- permits router HTTPS/8443 from the authorized Fedora workstation;
- permits router SSH/1122 from the authorized Fedora workstation;
- ends the `ACCESS_RESTRICTION` chain with an unconditional DROP;
- evaluates that chain before the platform's general new-connection ACCEPT for
  the normal LAN.

The existing project-owned `EDGE_TS_INPUT` path remains evaluated separately
for Tailscale traffic, preserving the previously validated remote-management
boundary.

## Positive validation

From the authorized Fedora administration workstation:

```text
SSH_ACCESS_OK
HTTP_CODE=200
```

After the negative test and cleanup, a second positive check also succeeded:

```text
ADMIN_SSH_OK
WEBUI_HTTP=200
```

## Negative validation

A temporary unused normal-LAN IPv4 address outside the active DHCP allocation
was added to the Fedora Wi-Fi interface solely for the controlled negative
test. The original authorized address and existing SSH session were left
unchanged.

Using the temporary non-admin source:

- HTTPS/8443 timed out;
- SSH/1122 timed out.

The temporary address was removed immediately after the test and the authorized
administration address remained present.

The platform chain counters then showed traffic reaching the terminal deny:

```text
ACCESS_RESTRICTION
authorized HTTPS rule: ACCEPT
authorized SSH rule:   RETURN
default rule:          DROP
observed default DROP: 10 packets / 600 bytes
```

This provides firewall-level evidence that the controlled non-admin attempts
were denied by the intended restriction policy.

## Normal-use regression check

A GeForce NOW session was started after the exposure-reduction changes and
operated normally. This is a bounded normal-use regression check rather than a
throughput or latency benchmark.

## Result

**PASS.**

Issue #127 acceptance criteria are satisfied for the adopted changes:

- rollback paths were prepared before modification;
- positive administration tests passed from the authorized host;
- controlled negative WebUI and SSH tests were denied;
- service/listener, NVRAM and firewall state were reviewed;
- the project health check remained clean;
- normal cloud-gaming use remained functional after hardening;
- sanitized evidence was retained.

## Claim boundary

This artifact records the reference-router state and controlled tests observed
on 2026-09-29.

It does not claim that all future client-address changes are automatically
safe, that every possible WAN exposure mechanism is absent indefinitely, or
that IPv6/Wi-Fi parity work is complete. IPv6 and Wi-Fi security evidence
remain separate follow-up scope under issue #128.

Deployment-specific public IP addresses, Tailscale node addresses, client MAC
addresses and unrelated raw logs are intentionally omitted.


## Subsequent same-day status

Issue #128 was completed later on 2026-09-29. The statement above that
IPv6/Wi-Fi parity remained follow-up scope reflects the state at the end of the
#127 validation itself; the later result is recorded separately in
[issue-128-ipv6-wifi-security-parity.md](issue-128-ipv6-wifi-security-parity.md).
