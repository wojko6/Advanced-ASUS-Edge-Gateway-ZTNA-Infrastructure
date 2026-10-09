# Issue #129 — Pi-hole-aware DR reboot persistence acceptance

**Date:** 2026-10-09  
**Target:** ASUS TUF-AX5400, GNUton / Asuswrt-Merlin reference deployment  
**Result:** **PASS** for a controlled reboot **with Entware available**. Full bare-metal/blank-storage disaster recovery is **not** claimed.

## Purpose and safety controls

Verify that the current backup/recovery prerequisites and critical DNS stack survive one operator-confirmed reboot, without restoring backup payloads or modifying production configuration.

Before the restart, the operator verified three separately encrypted off-router artifacts (ASUS Edge CORE, Pi-hole DR, native ASUS firmware CFG) and their integrity sidecars. Pi-hole and Unbound, the watchdog, Tailscale, two active swap files and a clean project healthcheck were present. DNS Guard v3.2 readiness, inactive break-glass and two independently responsive WAN bootstrap DNS candidates were confirmed.

The live DNS Guard, active `services-start` hook and native DNS supervisor each matched the `main` source artifact by SHA-256. An initial verifier attempted an unavailable BusyBox `sha256sum` applet; the verification was repeated successfully with Entware `sha256sum`. That diagnostic-script error did not affect the router.

## Controlled restart

The operator had physical router access and typed an explicit `REBOOT` confirmation. The script sent **one** restart command, did not retry it and waited for SSH to reconnect.

| Check | Observed evidence | Verdict |
|---|---|---|
| Pre-reboot recovery copies | All three encrypted files and SHA-256 sidecars verified | PASS |
| DNS Guard source integrity | Guard, active `services-start` and supervisor match `main` | PASS |
| Baseline health | 0 failures / 0 warnings | PASS |
| New system boot | Uptime reduced from 26,763 s to 45 s after SSH reconnect | PASS |
| Entware and swap | Entware present, two swaps active and pre-Entware ordering retained | PASS |
| Services | Unbound, Pi-hole FTL, Tailscale and syslog-ng running | PASS |
| Pi-hole permissions | Exact reviewed seven-capability FTL set present after restart | PASS |
| Local DNS | Dedicated alias and resolver `192.168.50.253` active | PASS |
| DNS Guard | Ready/local/state-valid/watchdog checks PASS; break-glass inactive | PASS |
| Final project health | 0 failures / 0 warnings at 205 s uptime | PASS |

Reported terminal checkpoints:
```text
ISSUE129_ROUTER_REBOOT=PASS
SSH_RECONNECTED=YES
FRESH_BOOT_CONFIRMED=YES
ISSUE129_POSTBOOT_FINAL=PASS
PRODUCTION_CONFIG_UNCHANGED=YES
```

## Boot log sequence

The log timestamps **before NTP synchronisation** appear with a Jan 1 date. Preserve their ordering but do not interpret them as real local 01:00 times.

| Log time | Observation |
|---|---|
| Pre-NTP 01:00:39 | DNS Guard watchdog scheduled |
| Pre-NTP 01:00:43 | DNS Guard policy applied in initial WAN phase |
| Pre-NTP 01:00:44 | Pre-Entware swap already active on data volume |
| 15:36:00 | NTP initial clock set |
| 15:36:03 | ENTWARE mounted; volume swap active before Entware startup |
| 15:36:04–06 | Unbound and Pi-hole FTL started |
| 15:36:17 | DNS Guard policy applied in settled WAN phase |
| 15:38:01 | System resolver automatically promoted to Pi-hole at `192.168.50.253` |

The result demonstrates successful independent boot recovery and autonomous promotion to Pi-hole. **Evidence limit:** the initial WAN-phase policy log does not include the exact resolver contents at that instant. Do not reinterpret it as packet-level proof of which bootstrap DNS server handled each early query.

## What this does not prove

- Restoration of the native CFG into firmware or a full new-device/new-SSD reconstruction;
- fresh Entware and Pi-hole package/service-account installation from zero;
- FTL `security.capability` xattr recovery on a freshly rebuilt **target** filesystem (a disposable Fedora tmpfs round-trip passed separately);
- recovery when Entware is missing, or when both local and WAN bootstrap DNS are unavailable;
- functional restoration of all DHCP, DNSSEC-negative, Gravity, reverse-DNS, Pi-hole API/collector and firewall integration paths **after an actual destructive restore**.

Encrypted archives and detailed operational logs remain private and **are not included in this public evidence**.

## References

- [Issue #129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129)
- [Pi-hole DR generator](../../docs/pihole-dr-generator.md)
- [Router disaster-recovery baseline](../../docs/router-disaster-recovery.md)
- [Rebuild/restore runbook](../../docs/pihole-dr-rebuild-runbook.md)
- [DNS Guard v3.2 bounded production validation](../../docs/dns-guard-v3.2-recovery-audit-live-validation.md)
