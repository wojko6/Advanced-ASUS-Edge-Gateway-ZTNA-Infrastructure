# Security design

## Defense in depth

| Control | Protects against | Does not replace |
|---|---|---|
| Tailscale identity + MFA | Stolen network location and unsolicited Internet access | Endpoint security and router authentication |
| Tailscale Grants | Excessive identity access | Local firewall validation |
| Device-IP allowlist | Accidental broad tailnet management access | Identity lifecycle management |
| Default-deny managed chains | Lateral movement through the subnet router | LAN segmentation/VLANs |
| Unbound hardening + DNSSEC | Some spoofing, cache poisoning, rebinding patterns | DoH/DoT controls and endpoint policy |
| TLS syslog forwarding | Passive log interception and basic transport tampering | SIEM correlation and immutable storage |
| Backup hashes | Accidental/corrupt restore material | Encrypted/off-device backup protection |

## Secrets

Never commit:

- Tailscale auth keys or `/opt/var/lib/tailscale/tailscaled.state`;
- router exports, password hashes, SSH private keys, TLS private keys;
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

Classic DNS redirection is a visibility/control measure, not a comprehensive DNS security boundary. Browsers and applications can use DoH (TCP 443), DoT (TCP 853), DoQ (UDP 853), VPN tunnels, or hard-coded proxies. Manage these at the endpoint or a gateway capable of application-aware filtering.

## Logging caveats

The syslog-ng example includes remote TLS forwarding with required peer
verification. Configure the trusted CA, certificates, private keys and collector
hostname before enabling it. Plain UDP syslog is not recommended for security
evidence. A collector is not a SIEM until rules, indexing, alerting, retention,
access control, and incident workflows are deployed.

## Platform limitations

Consumer router firmware and Entware are useful for a lab but do not provide high availability, measured failover, secure boot attestation, enterprise support, or strong workload isolation. The roadmap moves routing and enforcement to OPNsense/x86 and keeps the ASUS device as an access point or secondary lab node.
