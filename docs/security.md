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

## Source-control supply-chain safety

The repository `main` branch is intended to be protected by the #130 GitHub
ruleset baseline: normal changes go through pull requests, the aggregate
`Validation suite` check must pass, branch deletion and force-push are blocked,
and no ruleset bypass actor is configured.

The activation and validation procedure is documented in
[GitHub main-branch protection and required validation](github-main-protection.md).

This control protects repository history and merge flow. It does not replace
secret exclusion, dependency review, signed releases, deployment hash
verification, or live-router validation.

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

## DNS activity analytics privacy caveats

Pi-hole query history can reveal sensitive browsing and application metadata
even though it does not contain complete HTTPS URLs or page contents.

The deployed issue #108 analytics pipeline therefore treats the live Pi-hole
query database, real client identifiers and household domains as private
operational data. Collection is read-only, indexing/retention stay off-router,
and public evidence uses controlled synthetic domains, aggregates or manually
sanitized extracts.

Full domains and client identifiers are not persistent high-cardinality Loki
labels. The dashboard also exposes resolver-coverage gaps rather than implying
complete visibility. The tested Tailscale classic-DNS path is now directly
confirmed outside Pi-hole history; the hard-coded LAN dnsmasq interception path,
DoH/DoQ, VPN-carried DNS and unvalidated IPv6 paths remain separate
measurements.

The analytics plan does not authorize HTTPS interception.

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

## RouterCloud security boundary

RouterCloud is a separate application surface from the ASUS management WebUI.
It remains LAN/Tailscale-only, is rooted at the dedicated RouterCloud data
directory, and must not be treated as a generic browser for the router
filesystem.

The reserved `/__routercloud/...` namespace is application control-plane space,
not user storage. Current internal routes include login/logout, favorites and
password-reset endpoints. The double underscore is intentional and reduces
ambiguity with normal files and directories.

The current design preserves these controls:

- dedicated RouterCloud login/session authentication;
- backend authorization remains authoritative even when the frontend hides or
  exposes an action;
- generic Dufs `allow-delete` remains disabled in production;
- RouterCloud-specific delete and edit paths are separately gated;
- safe rename remains same-parent/no-overwrite;
- symlink following is disabled;
- bounded text editing and server-side selected ZIP operate inside the dedicated
  data root;
- no RouterCloud change introduces direct WAN exposure.

Password recovery adds a separate sensitive path. Production validation records
the following boundaries:

- reset-request responses do not intentionally disclose whether a submitted
  syntactically valid address belongs to the account;
- reset tokens are delivered in the URL fragment rather than the query string;
- the browser removes the fragment and submits the token only in the reset POST
  body;
- the stored reset verifier is not the raw token;
- reset lifetime and request frequency are bounded;
- password overrides are stored outside the served data root;
- SMTP credentials remain in private router-side configuration and must never be
  committed.

RouterCloud versioned backup uses a separate read-only SSH/rsync identity. That
identity must not gain arbitrary shell access or write/delete capability on the
live RouterCloud tree. The Fedora staging mirror is not itself considered a
backup; restic history is the independent recoverable layer.

See the
[2026-10-03 RouterCloud production checkpoint](routercloud-production-checkpoint-2026-10-03.md),
[password-recovery production validation](../evidence/2026-10-03/routercloud-password-recovery-production-validation.md)
and [versioned backup design](routercloud-versioned-backup.md).

### Open RouterCloud hardening observations

The current RouterCloud deployment remains intentionally LAN/Tailscale-only,
but application exposure on the edge router still deserves separate hardening.

Source review identified two items that must not be hidden by the network
boundary:

- user-controlled files are served from the same application origin as the
  RouterCloud UI/API, and some file types can be rendered inline. Active
  HTML/SVG/XML-style content should therefore be treated as a potential
  same-origin application risk until active content is forced to download or
  moved to a separate origin;
- the production RouterCloud process privilege/UID boundary must be verified
  explicitly. If the service runs as root, an application-level code execution
  defect would have an unacceptably large router-wide blast radius.

These are hardening findings, not a claim that an exploit has been demonstrated.

## Logging caveats

The syslog-ng example includes remote TLS forwarding with required peer
verification. Configure the trusted CA, certificates, private keys and collector
hostname before enabling it. Plain UDP syslog is not recommended for security
evidence. A collector is not a SIEM until rules, indexing, alerting, retention,
access control, and incident workflows are deployed.

## Platform limitations

Consumer router firmware and Entware are useful for a lab but do not provide high availability, measured failover, secure boot attestation, enterprise support, or strong workload isolation. The planned next gateway platform is ASUS RT-BE88U on a compatible Asuswrt-Merlin 3006.x branch, with the current architecture revalidated rather than replaced. OPNsense/x86 is retained only as a future contingency if documented requirements later exceed the ASUS platform.
