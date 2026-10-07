# DNS bootstrap deadlock and fail-open resolver recovery

This document has moved to the canonical incident case study:

[Case study: DNS bootstrap deadlock on Asuswrt-Merlin and recovery with DNS Guard v3.1](case-studies/dns-bootstrap-deadlock-dns-guard-v3.1.md)

The old path is intentionally retained as a compatibility pointer so existing
repository links and external references do not break.

The canonical case study documents the 2026-10-06 incident in full:

- normal websites stopped opening after the router resolver was made dependent
  on Pi-hole across cold boot;
- IP connectivity remained available while DNS resolution failed;
- the root cause was a circular router DNS -> Pi-hole -> Unbound -> NTP -> DNS
  bootstrap dependency;
- DNS Guard v3.1 introduced independent WAN bootstrap DNS, health-gated
  promotion to Pi-hole, fail-open recovery, sticky break-glass and a watchdog;
- the remediation passed controlled failure tests, a complete cold reboot and
  Android LTE + ASUS Tailscale Exit Node DNS validation.
