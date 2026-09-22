# Security design

## Defense in depth

| Control | Protects against | Does not replace |
|---|---|---|
| Tailscale identity + MFA | Stolen network location and unsolicited Internet access | Endpoint security and router authentication |
| Tailscale Grants | Excessive identity access | Local firewall validation |
| Device-IP allowlist | Accidental broad tailnet management access | Identity lifecycle management |
| Default-deny managed chains | Lateral movement through the subnet router | LAN segmentation/VLANs |
| Unbound hardening + DNSSEC | Some spoofing, cache poisoning, rebinding patterns | Encrypted-DNS transport controls and endpoint policy |
| Project-owned LAN DNS enforcement | Direct classic-DNS bypass on TCP/UDP 53 and direct IPv4 LAN DoT on TCP 853 | DoH/DoQ, VPN-carried DNS, IPv6 resolver-path controls, endpoint policy |
| Endpoint content filtering (optional) | Browser/app content that DNS filtering cannot reliably separate | Router DNS policy, endpoint patching, browser security |
| TLS syslog forwarding | Passive log interception and basic transport tampering | SIEM correlation and immutable storage |
| Backup hashes | Accidental/corrupt restore material | Encrypted/off-device backup protection |

## Secrets

Never commit:

- Tailscale auth keys or `/opt/var/lib/tailscale/tailscaled.state`;
- router exports, password hashes, SSH private keys, TLS private keys;
- endpoint-filtering CA private keys, exported browser trust stores, cookies, profiles, or authentication tokens;
- real internal hostnames/IPs when the repository must remain public;
- SIEM tokens, collector credentials, or private CA keys.

The provided backup excludes Tailscale state. Store backups off-device and encrypt them using a separate process appropriate to your environment.

## Management safety

- Keep WebUI WAN access disabled.
- Prefer HTTPS-only router management.
- Enable SSH only for explicit admin device IPs and key authentication.
- Require MFA in the identity provider used by Tailscale.
- Remove stale devices and rotate compromised node credentials promptly.
- Test from LAN before relying on remote access.

## DNS caveats

The reference deployment now enforces classic LAN DNS on TCP/UDP 53 and blocks direct IPv4 LAN DoT on TCP 853 with a project-owned `br0` FORWARD policy. Those controls are live validated, but they are not a comprehensive encrypted-DNS security boundary. DoH over HTTPS/443, DoQ/QUIC, VPN-carried DNS, IPv6 resolver paths, application-specific encrypted resolvers, hard-coded proxies, and traffic entering through interfaces outside the documented LAN policy remain separate controls or assessment items. `EDGE_LAN_DOT_FORWARD` must therefore be described as a direct IPv4 LAN DoT control, not as a universal DoT block.

Endpoint-side filtering must not be presented as proof that router DNS filtering can block the same content. Conversely, an endpoint filter that silently replaces the configured DNS resolver can reduce router visibility and invalidate DNS-path assumptions. The endpoint-filtering validation therefore checks that the existing router DNS path remains authoritative.

## Endpoint HTTPS filtering caveats

Optional system-level content filters such as Zen or AdGuard for Windows may inspect HTTPS by installing a local certificate authority and proxying traffic on the endpoint. This creates a separate trust boundary from the ASUS gateway.

Before treating such a tool as part of the validated design:

- verify the software source and tested version;
- document whether a local root CA is installed and how it is removed;
- verify that normal TLS validation and security-sensitive applications continue to work;
- keep DNS protection disabled when the purpose of the test is to preserve the existing router DNS architecture;
- record false positives and certificate failures rather than hiding them;
- never publish generated CA private keys or private browsing/session material.

Endpoint HTTPS interception is optional defense in depth, not a prerequisite for the router security edge. See `docs/endpoint-filtering-validation.md` for the controlled test methodology.

## Logging caveats

The syslog-ng example includes remote TLS forwarding with required peer
verification. Configure the trusted CA, certificates, private keys and collector
hostname before enabling it. Plain UDP syslog is not recommended for security
evidence. A collector is not a SIEM until rules, indexing, alerting, retention,
access control, and incident workflows are deployed.

## Platform limitations

Consumer router firmware and Entware are useful for a lab but do not provide high availability, measured failover, secure boot attestation, enterprise support, or strong workload isolation. The roadmap moves routing and enforcement to OPNsense/x86 and keeps the ASUS device as an access point or secondary lab node.
