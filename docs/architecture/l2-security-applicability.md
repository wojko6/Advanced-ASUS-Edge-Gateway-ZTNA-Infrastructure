# L2 and network-access security applicability

**Status:** CURRENT / DESIGN GUIDANCE  
**Last reviewed:** 2026-10-07

## Purpose

Record classic enterprise Layer-2 and AAA controls explicitly, including the
controls that are not applicable to the present consumer-router topology.

Absence from the implementation must not be mistaken for accidental omission.

## Applicability matrix

| Control | Current status | Rationale / future trigger |
| --- | --- | --- |
| VLAN segmentation | PLANNED | issue #143; target Trusted/IoT/Guest separation |
| DHCP Snooping | N/A CURRENTLY | requires managed switching/VLAN access layer with supported enforcement |
| Dynamic ARP Inspection | N/A CURRENTLY | normally depends on managed switching and trusted DHCP bindings |
| switch Port Security | N/A CURRENTLY | no documented managed access-switch port layer |
| BPDU Guard / Root Guard | N/A CURRENTLY | no documented STP access/distribution topology |
| STP/RSTP | N/A CURRENTLY | no documented redundant L2 topology or switching loop |
| storm control | N/A CURRENTLY | requires managed switch/AP support and measured requirement |
| 802.1X wired/wireless NAC | DEFERRED | not justified for the current single-gateway Home/SMB baseline; reconsider with managed AP/switch layer |
| RADIUS | DEFERRED | useful if centralized WLAN/802.1X/device administration is introduced |
| TACACS+ | DEFERRED | not justified for one consumer gateway; reconsider with multiple managed network devices/admins |
| WPA2/WPA3 AES | IMPLEMENTED / VALIDATED at documented checkpoint | active trusted WLANs documented without WEP/TKIP |
| WPS | DISABLED / VALIDATED | documented current security baseline |
| PMF | OBSERVED / DOCUMENTED | preserve device compatibility and revalidate when WLAN policy changes |
| Tailscale identity + MFA | IMPLEMENTED | remote identity boundary; not a substitute for LAN L2 controls |
| source-restricted router management | IMPLEMENTED | LAN and Tailscale management use explicit source restrictions |

## AAA boundary

The current management model uses:

- router-local authentication;
- SSH key authentication where enabled;
- Tailscale identity/Grants with MFA at the identity provider;
- source-scoped local firewall rules;
- mTLS for centralized syslog transport.

This is not equivalent to centralized network-device AAA through
RADIUS/TACACS+. The latter should be added only when the number/type of managed
network devices makes central AAA operationally useful.

## Future segmentation acceptance

When issue #143 moves from design to implementation, the project should add:

- VLAN ID/subnet table;
- trunk/access-port map;
- per-zone DHCP/DNS behavior;
- default-deny inter-zone ACL matrix;
- explicit mDNS/multicast relay policy;
- management-plane zone;
- negative tests between zones;
- switch/AP-specific protections where the selected hardware supports them.

## Claim boundary

This matrix explains applicability. It does not claim unsupported enterprise
switching controls are present on the current ASUS platform.
