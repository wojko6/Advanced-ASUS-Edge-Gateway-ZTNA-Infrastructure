# Threat model

## Scope

The scope includes the ASUS gateway, JFFS/Entware configuration, Tailscale subnet/exit routing, router management plane, recursive DNS, LAN destinations, forwarded logs, and optional endpoint-filtering validation. Physical compromise and upstream ISP compromise are documented but not fully mitigated by this project.

Endpoint content filtering is a separate optional trust boundary. It is evaluated as defense in depth and must not be confused with router-side DNS enforcement.

## Assets and trust boundaries

| Asset | Security objective |
|---|---|
| Router management plane | Authorized administrators only; no WAN exposure |
| LAN services | Only documented identity/device/service paths |
| Tailscale node state | Confidentiality and integrity |
| DNS resolver/cache | Validated answers, limited clients, resistant to rebinding |
| Firewall policy | Versioned, idempotent, reviewable, recoverable |
| Logs/backups | Integrity, restricted access, useful retention |
| Endpoint HTTPS trust store | No unauthorized CA persistence; controlled installation/removal |
| Endpoint browsing/session data | Not exposed through evidence collection or public repository content |

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
| T11 | Endpoint filter silently changes DNS path | Medium | Medium | DNS-path validation; endpoint DNS protection disabled for architecture-preservation tests | Application-level DoH or VPN bypass |
| T12 | HTTPS interception CA is abused or left behind | Low | High | Source/version verification, trust-store inspection, uninstall/cleanup validation | Endpoint compromise can undermine local trust store |
| T13 | Endpoint evidence leaks private browsing/session data | Medium | High | Sanitized text-first evidence, manual review, no cookies/tokens/profiles/private keys | Human redaction error |
| T14 | Endpoint-filter result is overstated as router capability | Medium | Medium | Separate test methodology and precise result language | Portfolio reader may still conflate layers |

## Abuse cases to test

- A normal tailnet user attempts router SSH and HTTPS.
- An approved user attempts SMB on an unlisted LAN host.
- A compromised endpoint sends DNS directly to `1.1.1.1:53`.
- A client uses DoH/DoT and bypasses classic DNS interception.
- A remote client uses the exit node without membership in `group:exit-users`.
- The firewall hook runs repeatedly and duplicate jumps do not appear.
- `/opt` mounts after the startup timeout and services remain unavailable but fail visibly.
- A Windows endpoint filter is enabled and the workstation DNS resolver is checked for unexpected replacement.
- Endpoint HTTPS filtering is disabled/uninstalled and the local trust-store/certificate state is checked for expected cleanup.
- Endpoint-filter evidence is reviewed for hostnames, account identifiers, cookies, tokens, private IPs, unrelated browsing history, and certificate private material before publication.

## Evidence and claim boundary

Endpoint-filtering results are date-, version-, browser-, and workload-specific. A successful YouTube or browser test demonstrates only what was observed during the defined test window. It does not establish permanent blocking effectiveness and does not prove equivalent router-side capability.

During the completed 2026-09-11 through 2026-09-22 stability observation, endpoint tests were kept workstation-local and router-side checks were read-only. Future observation windows must declare equivalent restrictions explicitly in `PROJECT-STATUS.md` rather than relying on this historical sentence.

Review this model after every new exposed service, firmware upgrade, LAN addressing change, identity-policy change, or newly trusted endpoint interception component.
