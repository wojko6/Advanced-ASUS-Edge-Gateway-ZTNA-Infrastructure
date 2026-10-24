# Compatibility and revalidation

**Status:** CURRENT

**Last reviewed:** 2026-10-24 (Unbound 1.26.2 R2 and one functional ASUS reboot; other components retain date-scoped evidence)

**Reference evidence:** 2026-09-11 storage baseline, 2026-09-22/23 exit-node and DNS datapath validation, 2026-09-27 startup/current-firmware checks, the [2026-09-28 Pi-hole cutover validation](../evidence/2026-09-28/pi-hole-main-lan-cutover-validation.md), the [2026-10-06 Tailscale 1.103.375 runtime validation](../evidence/2026-10-06/tailscale-1.103.375-router-upgrade-validation.md), the [2026-10-21 Tailscale 1.104.2 ARMv7 bounded live deployment](../evidence/2026-10-21/tailscale-1.104.2-armv7-live-validation.md), the [2026-10-24 Unbound R2 record](operations/unbound-1.26.2-production-deployment-2026-10-24.md), the [DNS Guard v3.2 bounded live validation](dns-guard-v3.2-recovery-audit-live-validation.md), the [2026-10-09 Pi-hole-aware production reboot](../evidence/2026-10-09/issue-129-pihole-dr-reboot-persistence.md), and the [optional BusyBox 1.36.1 live validation](../evidence/2026-10-09/custom-busybox-armv7-live-validation.md)

The project is validated against a specific reference deployment. It does not claim a universal minimum version for every Asuswrt-Merlin or Entware package combination.

| Component | Reference / compatibility contract | Revalidation trigger |
| --- | --- | --- |
| Router | ASUS TUF-AX5400 | hardware/platform change |
| Firmware | ASUSWRT-Merlin 3004.388.9_2-gnuton1 in the published 2026-09-11 baseline; GNUton 3004.388.11_1-gnuton1_tuf in the 2026-09-23 reference-router health, reboot, DNS and HTTPS smoke checks | firmware upgrade or firewall architecture change |
| Shell/runtime | Firmware `/bin/busybox` 1.25.1 and firmware `/bin/sh` (BusyBox-compatible POSIX shell) remain authoritative for router startup and deployed scripts | firmware shell/applets, interpreter or startup hook changes |
| Optional operator utilities | Separately installed, pinned, statically linked ARM EABI5 BusyBox 1.36.1 at `/jffs/addons/asus-edge/tools/busybox/1.36.1/busybox`; explicit applet invocation only, **no** global PATH/shell replacement and not present in CORE backup | rebuild, new ABI/hardware/firmware, relocation, adding a script dependency or changing DR coverage |
| Entware/storage | persistent `/opt` on the validated SSD-backed layout | storage migration, mount or startup-ownership change |
| Tailscale | current reference runtime `1.104.2` (operator-compiled stable ARMv7 binaries, 2026-10-21 live service restart/healthcheck PASS 0/0); configured local socket, subnet/exit routing and intentional `netfilter-mode=off` ownership remain required. Earlier `1.103.375` unstable/dev and `1.102.3` checks are historical; full reboot with `1.104.2` is not yet evidenced. | Tailscale update, track/source change, socket/state-path or netfilter-mode change |
| Unbound | **2026-10-24 production:** five ARMv7 IPKs `1.26.2-1`, manager-generated config/custom `S61unbound`, loopback `127.0.0.1:53535`, direct UDP/TCP good AD / bogus SERVFAIL and one real-router reboot functional PASS. Chroot `root:root 0755`; writable `dnssec-auto` `65534:65534 0700`; active `root.key 0666` is **open hardening**, not accepted as desired mode (#298/#299 HOLD). Bare-metal restore untested. [R2 report](operations/unbound-1.26.2-production-deployment-2026-10-24.md) | Package, Manager/PID/`rc.func`, trust-anchor location/ownership/umask, listener, DNSSEC or restore-contract change |
| Pi-hole FTL | current main-LAN DHCP filtering service on a dedicated LAN alias; Pi-hole DHCP disabled; allowed queries use local Unbound upstream | Pi-hole/FTL update, database/schema change used by analytics, listener/alias change, Gravity/policy change or startup-order change |
| dnsmasq | firmware-owned router-LAN/Tailscale port-53 listener retained for DHCP/local naming and existing classic-DNS interception, forwarding ordinary external resolution to local Unbound | firmware update, resolver ownership/port change, DHCP option change or interception-path redesign |
| syslog-ng | optional unless remote logging is configured; configured TLS path must validate on both peers | package, TLS or collector change |
| WAN NAT | platform-owned Asuswrt-Merlin `MASQUERADE`/SNAT is a runtime dependency for the validated exit-node architecture | firmware, firewall or WAN-interface policy change |

## Platform continuity and optional future OPNsense

**2026-10-12 decision:** continue on **ASUS TUF-AX5400**. The previously
planned ASUS RT-BE88U is **not** a migration/purchase target. OPNsense/x86
is possible in an **unscheduled future**; the first research setup is an
isolated Windows 11 virtual laboratory, not a deployed router.

No ABI/feature compatibility is transferable by assumption between ASUS
GNUton Linux 4.1.52/iptables/Entware/JFFS and FreeBSD/PF/OPNsense.
If migration is ever approved, require new interface/WAN/DHCP/IPv4/IPv6,
DNSSEC/Pi-hole/Unbound, firewall/NAT, Tailscale, RouterCloud, mTLS logs,
backup/restore, reboot, trust-zone and physical recovery evidence.
The old RT-BE88U benchmark plan is historical optional comparison work
and must not be used to imply approval.

See [platform decision](architecture/platform-direction-2026-10-12.md).

## Version evidence policy

Record actual Tailscale, Pi-hole/FTL, Unbound, syslog-ng and other material package versions in dated evidence after upgrades. Do not infer compatibility merely because a package installs or a process starts.

The repository does not publish an evidence-backed universal minimum package-version matrix. Adding one requires controlled compatibility testing across every version range being claimed.

## Mandatory revalidation after material changes

Repeat the affected live checks after:

- Asuswrt-Merlin firmware upgrades;
- Tailscale upgrades that can affect routing, local API/socket behaviour or netfilter integration;
- Pi-hole/FTL, Unbound or dnsmasq ownership/listener/upstream changes;
- Pi-hole query-schema changes when issue #108 analytics depends on those fields;
- firewall or WAN NAT architecture changes;
- DNS filtering-layer migration or classic-DNS interception-path redesign;
- storage or startup-hook ownership changes;
- installer/backup/restore changes or edits to protected JFFS tree owner/group/mode policy (the accepted #200 snapshot is scoped to the audited 2026-10-09 state);
- optional BusyBox upgrades or any new runtime dependency on its versioned path (this build is a side-by-side admin tool, not an early-boot requirement).

For exit-node changes, re-check IPv4 forwarding, project forwarding, platform NAT, established/related return handling and packet-level datapath correlation. For DNS changes, re-check classic UDP/TCP 53 from the relevant LAN/Tailscale clients and keep encrypted DNS outside the claim unless it is separately tested.

Repository/CI success remains a separate evidence class: it does not prove that the same revision has been deployed on the reference router.

The 2026-09-23 reboot check covered mounted storage, swap, WPS/USB exposure, project health, exact admin firewall rules, and Fedora DNS/HTTPS smoke tests. It does not replace packet-level exit-node correlation or establish phone-browser certificate status, multiple cold-start reliability, or a universal firmware support range.
