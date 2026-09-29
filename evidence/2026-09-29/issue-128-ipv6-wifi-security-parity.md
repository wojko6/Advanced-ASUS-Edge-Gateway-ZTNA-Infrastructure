# Issue #128 — IPv6 and Wi-Fi security parity evidence

**Status:** PASS  
**Date:** 2026-09-29  
**Evidence class:** Read-only live validation / sanitized  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton

## Purpose

Establish the current IPv6 and Wi-Fi security baseline before adding further
enforcement.

No persistent configuration change was required by this validation.

## IPv6 baseline

Router-side inspection showed:

- IPv6 service configured as disabled;
- kernel IPv6 disabled globally and by default;
- no IPv6 addresses present on router interfaces;
- no IPv6 routes or IPv6 default route;
- no active router-advertisement configuration observed in the generated
  dnsmasq configuration.

The Fedora client independently showed:

- only link-local IPv6 on the normal LAN interfaces;
- no native global IPv6 address on Wi-Fi or Ethernet;
- no native IPv6 default route;
- a separate Tailscale IPv6 address on the Tailscale interface only.

This establishes that native WAN/LAN IPv6 is currently disabled rather than
merely failing at one client.

The project-owned fail-closed IPv6 Tailscale guards remain installed:

- `EDGE_TS6_INPUT` is the first IPv6 INPUT rule for `tailscale0`;
- `EDGE_TS6_FORWARD` is the first IPv6 FORWARD rule for `tailscale0`;
- both chains allow only RELATED/ESTABLISHED traffic before logging and
  unconditionally dropping remaining traffic.

Because native IPv6 is disabled, no broader IPv6 management/DNS parity claim is
made. The accepted posture is documented disablement until explicit IPv6 parity
is designed and live-tested.

## Trusted Wi-Fi baseline

Both active main WLANs were inspected from NVRAM and mapped to their runtime
radio interfaces.

### 2.4 GHz trusted WLAN

- enabled;
- WPA2/WPA3-Personal transition mode;
- AES encryption;
- WEP disabled;
- PMF enabled in transition/optional mode;
- AP isolation disabled, consistent with a trusted LAN.

### 5 GHz trusted WLAN

- enabled;
- WPA3-Personal;
- AES encryption;
- WEP disabled;
- PMF required;
- AP isolation disabled, consistent with a trusted LAN.

A Fedora client connected to the active 5 GHz WLAN independently reported
`WPA3` security at 5 GHz, providing client-side confirmation of the runtime
authentication mode.

No TKIP or WEP configuration was observed on either active trusted WLAN.

## Guest WLAN baseline

All configured guest BSS slots on both radios were disabled at the time of
validation.

Their stored configuration included intranet access disabled, but because the
guest BSSs were not active, this evidence does not claim live-tested guest
client isolation.

If a guest/IoT WLAN is enabled in the future, its isolation and intranet policy
must be validated with an active client rather than inferred from stored NVRAM
alone.

## WPS

Both observed WPS enable flags were disabled.

## Result

**PASS.**

Issue #128 acceptance is satisfied without a persistent configuration change:

- IPv6 state was measured from both router and client perspectives;
- project IPv6 guard ordering and terminal deny behavior were inspected;
- trusted WLAN authentication, cipher and PMF state were recorded;
- WEP/TKIP absence was established for active trusted WLANs;
- guest WLAN state and the limit of non-active isolation evidence were
  documented;
- the active 5 GHz WLAN received client-side WPA3 confirmation;
- no GUI-only assumption was used as the basis for a persistent change.

## Claim boundary

This artifact records the observed reference state on 2026-09-29.

It does not claim live guest/IoT isolation because all guest BSSs were disabled.
It also does not claim IPv6 policy parity with IPv4; native IPv6 is intentionally
disabled and the Tailscale IPv6 path remains fail-closed until equivalent
granular policy is implemented and tested.

SSID names, MAC addresses, public addresses and other deployment-specific
identifiers are intentionally omitted.
