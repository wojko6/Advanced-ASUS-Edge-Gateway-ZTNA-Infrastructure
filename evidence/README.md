# Validation evidence

Automated shell, configuration, mock-firewall, recovery, and evidence-redaction tests run in [GitHub Actions](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/actions).

Live results are environment-specific and are not fabricated in this repository. Use [the collection procedure](../docs/evidence-collection.md) on the deployed router, review and sanitize the output, complete the relevant client-side checks, and then add a dated evidence directory.

Use the template that matches the evidence class:

- The [live-validation template](live-validation-template.md) is for router, firewall, DNS/Tailscale, remote-client, and related live-network validation. A row is evidence only after its date, source role, command or method, observation, and verdict have been completed.
- The [endpoint-filtering template](endpoint-filtering-template.md) is for workstation-local Zen, AdGuard for Windows, or comparable endpoint-filter validation. It records baseline/filtered states, DNS-path preservation, HTTPS/root-CA behaviour, compatibility, resource observations, cleanup, and claim boundaries.

Both files are templates only. A template or unfilled placeholder is never validation evidence.

## Published validation timeline

- **2026-09-11 — current router baseline:** sanitized SSD/Entware migration and controlled reboot validation. The published evidence records automatic mounting of both SSD partitions, active swap, restored Tailscale/Unbound/syslog-ng service state, dnsmasq forwarding to local Unbound, DNSSEC AD validation, and the post-reboot health-check result. Start with the recruiter-facing [validated router-state snapshot](ROUTER-STATE-2026-09-11.md), then review the underlying [2026-09-11 evidence](2026-09-11/entware-ssd-migration-validation.txt).
- **2026-09-08 — remote-client validation:** Android over LTE/5G with Tailscale DNS enabled. It validates the remote DNS path through Tailscale, dnsmasq/Diversion, and recursive Unbound, including normal resolution, DNSSEC validation, and NXDOMAIN blocking of a test advertising/tracking domain. See the [live validation report](2026-09-08/live-validation.md).
- Earlier dated directories preserve narrower validation snapshots and regression evidence from the deployment process.

The 2026-09-08 Android remote-client test used a Tailscale beta client. The report does not claim that the previously observed stable-client DNS issue has been fixed in a stable Android release.

## Evidence classes

Keep evidence separated by what actually produced it:

| Class | Examples | What it can demonstrate |
|---|---|---|
| CI / mock | shell syntax, config validation, mocked firewall behaviour, recovery tests | repository logic and expected policy behaviour in the test harness |
| Router live | health check, mounts, processes, firewall counters, DNSSEC query | observed state of the reference ASUS deployment at a point in time |
| Remote client | LTE/5G Tailscale path, DNS resolution, service reachability | observed end-to-end behaviour from a defined client |
| Endpoint filter | Zen or AdGuard test on Windows/Chrome | endpoint-specific content filtering, DNS-path preservation, compatibility and overhead |
| Mobile telemetry | sanitized DNS/traffic observations from a defined phone/scenario | traffic observed for that device, OS, configuration and test window |

Do not merge these classes into a stronger claim than the underlying evidence supports. In particular, endpoint HTTPS/content filtering does not prove equivalent router-side filtering capability.

## Endpoint-filter evidence

Use the methodology in [endpoint filtering validation](../docs/endpoint-filtering-validation.md) and record the run with the [endpoint-filtering evidence template](endpoint-filtering-template.md). A dated endpoint result should identify at minimum:

- test date;
- Windows and browser versions;
- filter product/version and relevant settings;
- baseline state and filtered state;
- DNS-path result;
- HTTPS/certificate result;
- defined YouTube/browser test observations;
- false positives or broken sites observed;
- basic CPU/RAM observations when measured;
- PASS, FAIL, INCONCLUSIVE, or NOT TESTED verdicts.

Do not publish browser profiles, cookies, session identifiers, certificate private keys, exported trust stores, unrelated browsing history, or raw captures containing private sessions.

## Mobile-telemetry evidence

Mobile telemetry is device- and software-specific. Record the phone model, OS/version, relevant hardening/debloat state, network path, test duration, and scenario. Prefer controlled scenarios such as idle, reboot/startup, selected system-app use, and normal interactive use.

A second Xiaomi device with a different model or OS version is an independent comparative case study, not a controlled before/after debloat baseline. Differences may be caused by hardware, OS version, region, installed applications, configuration, vendor services, or hardening choices. State those limitations next to the results.

Historical individual DNS observations may provide context but must not be converted into an invented quantitative baseline.

## Evidence policy

Published evidence must not contain authentication material, private keys, Tailscale identity details, public WAN addresses, device MAC addresses, router serial numbers, DDNS credentials, raw authorization headers, cookies, browser/session tokens, or certificate private material. Raw router logs and packet captures require manual sanitization before publication.

Prefer the smallest artifact that proves the claim. Sanitized text output is usually preferable to a full packet capture or screenshot because it reduces accidental disclosure and makes the evidence easier to review.

Use precise result language:

- **Observed** — directly demonstrated during the documented test.
- **Not observed** — not seen during the documented test window; not proof that it can never occur.
- **Not tested** — no evidence collected.
- **Inconclusive** — available evidence is insufficient or confounded.

A successful controlled reboot and health check demonstrate reboot stability and functional recovery at that point in time. They do **not** by themselves prove long-term stability. The reference deployment entered a 14-day unchanged-state observation period on 2026-09-11; long-term stability should only be claimed after that observation is completed and documented.

During that observation period, endpoint tests may be performed without router configuration changes. Any router-side corroboration must remain read-only so the unchanged-state stability gate is preserved.
