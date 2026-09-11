# Validation evidence

Automated shell, configuration, mock-firewall, recovery, and evidence-redaction tests run in [GitHub Actions](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/actions).

Live results are environment-specific and are not fabricated in this repository. Use [the collection procedure](../docs/evidence-collection.md) on the deployed router, review and sanitize the output, complete the relevant client-side checks, and then add a dated evidence directory.

The [live-validation template](live-validation-template.md) distinguishes expected behavior from observed behavior. A row is evidence only after its date, source role, command, observation, and verdict have been completed.

## Published validation timeline

- **2026-09-11 — current router baseline:** sanitized SSD/Entware migration and controlled reboot validation. The published evidence records automatic mounting of both SSD partitions, active swap, restored Tailscale/Unbound/syslog-ng service state, dnsmasq forwarding to local Unbound, DNSSEC AD validation, and the post-reboot health-check result. Start with the recruiter-facing [validated router-state snapshot](ROUTER-STATE-2026-09-11.md), then review the underlying [2026-09-11 evidence](2026-09-11/entware-ssd-migration-validation.txt).
- **2026-09-08 — remote-client validation:** Android over LTE/5G with Tailscale DNS enabled. It validates the remote DNS path through Tailscale, dnsmasq/Diversion, and recursive Unbound, including normal resolution, DNSSEC validation, and NXDOMAIN blocking of a test advertising/tracking domain. See the [live validation report](2026-09-08/live-validation.md).
- Earlier dated directories preserve narrower validation snapshots and regression evidence from the deployment process.

The 2026-09-08 Android remote-client test used a Tailscale beta client. The report does not claim that the previously observed stable-client DNS issue has been fixed in a stable Android release.

## Evidence policy

Published evidence must not contain authentication material, private keys, Tailscale identity details, public WAN addresses, device MAC addresses, router serial numbers, DDNS credentials, or raw authorization headers. Raw router logs require manual sanitization before publication.

A successful controlled reboot and health check demonstrate reboot stability and functional recovery at that point in time. They do **not** by themselves prove long-term stability. The reference deployment entered a 14-day unchanged-state observation period on 2026-09-11; long-term stability should only be claimed after that observation is completed and documented.
