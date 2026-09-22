# Compatibility and revalidation

**Status:** CURRENT  
**Last reviewed:** 2026-09-22  
**Reference evidence:** 2026-09-11 baseline plus 2026-09-22 exit-node/DNS datapath validation

The project is validated against a specific reference deployment. It does not claim a universal minimum version for every Asuswrt-Merlin or Entware package combination.

| Component | Reference / compatibility contract | Revalidation trigger |
| --- | --- | --- |
| Router | ASUS TUF-AX5400 | hardware/platform change |
| Firmware | ASUSWRT-Merlin 3004.388.9_2-gnuton1 in the published 2026-09-11 baseline | firmware upgrade or firewall architecture change |
| Shell/runtime | BusyBox-compatible POSIX `sh` for deployed scripts | shell/tooling change |
| Entware/storage | persistent `/opt` on the validated SSD-backed layout | storage migration, mount or startup-ownership change |
| Tailscale | configured local socket, required subnet/exit routing and intentional `netfilter-mode=off` ownership model must remain functional | Tailscale update, socket/state-path or netfilter-mode change |
| Unbound | deployed configuration validates and exposes the configured loopback listener; reference path uses `127.0.0.1:53535` | Unbound update, listener or config-manager change |
| dnsmasq | firmware-owned port-53 listener in the current architecture, forwarding to local Unbound | resolver ownership/port change or Pi-hole migration |
| syslog-ng | optional unless remote logging is configured; configured TLS path must validate on both peers | package, TLS or collector change |
| WAN NAT | platform-owned Asuswrt-Merlin `MASQUERADE`/SNAT is a runtime dependency for the validated exit-node architecture | firmware, firewall or WAN-interface policy change |

## Version evidence policy

Record actual Tailscale, Unbound, syslog-ng and other material package versions in dated evidence after upgrades. Do not infer compatibility merely because a package installs or a process starts.

The repository does not publish an evidence-backed universal minimum package-version matrix. Adding one requires controlled compatibility testing across every version range being claimed.

## Mandatory revalidation after material changes

Repeat the affected live checks after:

- Asuswrt-Merlin firmware upgrades;
- Tailscale upgrades that can affect routing, local API/socket behaviour or netfilter integration;
- Unbound/dnsmasq ownership or listener changes;
- firewall or WAN NAT architecture changes;
- migration from Diversion to another DNS filtering layer;
- storage or startup-hook ownership changes.

For exit-node changes, re-check IPv4 forwarding, project forwarding, platform NAT, established/related return handling and packet-level datapath correlation. For DNS changes, re-check classic UDP/TCP 53 from the relevant LAN/Tailscale clients and keep encrypted DNS outside the claim unless it is separately tested.

Repository/CI success remains a separate evidence class: it does not prove that the same revision has been deployed on the reference router.
