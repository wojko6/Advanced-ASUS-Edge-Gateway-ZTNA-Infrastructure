# Router state — 2026-09-11

This document records the validated public baseline of the reference ASUS TUF-AX5400 deployment after the Entware SSD migration and controlled reboot on 2026-09-11.

It is a sanitized portfolio snapshot, not a complete configuration dump. Tailnet addresses, usernames/account identifiers, LAN peer details, process IDs, public WAN addresses, MAC addresses, router serial numbers, credentials, and raw authorization material are intentionally omitted.

## Platform

- Router: ASUS TUF-AX5400
- Firmware: ASUSWRT-Merlin 3004.388.9_2-gnuton1
- Entware persistent storage: SSD

## Storage and swap

After the controlled reboot:

- `/dev/sda1` mounted automatically on `/tmp/mnt/ENTWARE` as ext4.
- `/dev/sda2` mounted automatically on `/tmp/mnt/ROUTER_DATA` as ext4.
- A 512 MiB swap file on `ENTWARE` was active.
- An additional 2 GiB swap file on `ROUTER_DATA` was active.
- Both swap files reported zero use at the validation point.

These storage and swap observations are directly supported by the sanitized `2026-09-11/entware-ssd-migration-validation.txt` artifact.

## Services

The published 2026-09-11 SSD-migration artifact directly confirms:

- `tailscaled` running successfully;
- Tailscale status command successful, with the router online and offering exit-node capability;
- `unbound` running successfully.

`syslog-ng` is part of the broader reference deployment and is discussed in other repository documentation/evidence, but it is **not directly evidenced by the SSD-migration validation artifact linked below**. Do not use this snapshot alone to claim successful syslog-ng recovery, mTLS delivery, buffering, or post-reboot collector delivery.

## DNS path

The deployed DNS chain remained:

`client -> dnsmasq -> Unbound @ 127.0.0.1:53535 -> recursive DNS`

The public validation snapshot directly confirmed:

- `dnsmasq` configured with `no-resolv`;
- `dnsmasq` forwarding to `127.0.0.1#53535`;
- direct Unbound query for `example.com` returned `NOERROR`;
- the response included the DNSSEC `AD` flag.

The artifact confirms the configured dnsmasq upstream and a successful direct Unbound query at the validation point. It does not, by itself, prove every possible client path, encrypted-DNS behavior, or continuous resolver availability outside that observation.

## Validation result

The sanitized 2026-09-11 evidence records a PASS for the specific SSD migration and controlled reboot checks captured in the artifact:

- both SSD partitions auto-mounted;
- swap activated automatically;
- Tailscale was running successfully after the earlier no-swap OOM condition was addressed;
- Unbound was running successfully;
- direct recursive DNS resolution succeeded with DNSSEC validation;
- dnsmasq remained configured to use the local Unbound resolver.

See: [`2026-09-11/entware-ssd-migration-validation.txt`](2026-09-11/entware-ssd-migration-validation.txt).

## Evidence boundary

Treat this document as an index/interpretation of the linked sanitized artifact, not as additional independent evidence. Claims above are deliberately limited to observations present in that artifact unless another evidence source is explicitly named.

In particular:

- process presence/status at one validation point is not a long-term availability claim;
- an advertised exit-node capability is not, by itself, evidence that every exit-node traffic path was exercised successfully in this artifact;
- a DNSSEC `AD` response for the recorded direct query is evidence for that validation event, not a guarantee for every domain or future query;
- configuration presence is not equivalent to end-to-end traffic validation;
- components not captured in the linked artifact must not be inferred merely because they are part of the intended architecture.

## Stability claim boundary

This snapshot proves the validated state at the time of the controlled reboot test. It does **not** by itself prove long-term stability.

At the time of this 2026-09-11 snapshot, a longer unchanged-state observation was planned through 2026-09-25. That later observation was deliberately closed on 2026-09-22 after continuous operation from 2026-09-11 through 2026-09-22, so it must not be described as a completed 14-day endurance test.

This later outcome does not expand the claims of the 2026-09-11 snapshot itself. The snapshot remains point-in-time evidence for the checks above; the completed observation interval and its closing health/log review are documented separately in current project status and the dated 2026-09-22 worklog/evidence material.
