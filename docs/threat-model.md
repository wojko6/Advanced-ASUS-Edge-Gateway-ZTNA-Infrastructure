# Threat model

## Scope

The scope includes the ASUS gateway, JFFS/Entware configuration, Tailscale subnet/exit routing, router management plane, recursive DNS, LAN destinations, and forwarded logs. Physical compromise and upstream ISP compromise are documented but not fully mitigated by this project.

## Assets and trust boundaries

| Asset | Security objective |
|---|---|
| Router management plane | Authorized administrators only; no WAN exposure |
| LAN services | Only documented identity/device/service paths |
| Tailscale node state | Confidentiality and integrity |
| DNS resolver/cache | Validated answers, limited clients, resistant to rebinding |
| Firewall policy | Versioned, idempotent, reviewable, recoverable |
| Logs/backups | Integrity, restricted access, useful retention |

## Threats and controls

| ID | Threat | Likelihood | Impact | Primary controls | Residual risk |
|---|---|---:|---:|---|---|
| T1 | Internet attacker reaches management UI | Low | High | No project WAN rule; Merlin WAN management disabled | Firmware/service vulnerability |
| T2 | Compromised tailnet device scans LAN | Medium | High | Grants + destination/port allowlist + default drop | Allowed service may be exploited |
| T3 | Compromised Tailscale admin account | Medium | High | IdP MFA, group review, device-IP firewall layer | Attacker controlling an allowed admin device |
| T4 | DNS bypass with encrypted resolver | High | Medium | Endpoint policy; documented limitation | QUIC/HTTPS tunneling |
| T5 | Malicious LAN device attacks router | Medium | High | Merlin LAN policy, management authentication | Flat-LAN lateral movement |
| T6 | Boot race leaves services unavailable | Medium | Medium | Mount readiness timeout, lock, health check | USB/Entware failure |
| T7 | Upgrade breaks remote access | Medium | High | No boot upgrades, explicit maintenance, backups | Entware rollback availability |
| T8 | Logs are lost or modified | Medium | Medium | Local archive, TLS forwarding, collector retention | Router compromise before forwarding |
| T9 | Backup exposes credentials | Medium | High | State excluded, mode 0600, off-device encryption guidance | Other copied configs may contain secrets |
| T10 | IPv6 bypasses IPv4 rules | Medium | High | IPv6 forwarding out of scope/disabled until tested | Platform-specific IPv6 behavior |

## Abuse cases to test

- A normal tailnet user attempts router SSH and HTTPS.
- An approved user attempts SMB on an unlisted LAN host.
- A compromised endpoint sends DNS directly to `1.1.1.1:53`.
- A client uses DoH/DoT and bypasses classic DNS interception.
- A remote client uses the exit node without membership in `group:exit-users`.
- The firewall hook runs repeatedly and duplicate jumps do not appear.
- `/opt` mounts after the startup timeout and services remain unavailable but fail visibly.

Review this model after every new exposed service, firmware upgrade, LAN addressing change, or identity-policy change.
