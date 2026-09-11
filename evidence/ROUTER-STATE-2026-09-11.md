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

## Services

The post-reboot validation confirmed:

- `tailscaled` running successfully.
- Tailscale status command successful; the router was online and offering exit-node capability.
- `unbound` running successfully.
- `syslog-ng` restored as part of the validated reboot state documented elsewhere in the repository.

## DNS path

The deployed DNS chain remained:

`client -> dnsmasq -> Unbound @ 127.0.0.1:53535 -> recursive DNS`

The public validation snapshot confirmed:

- `dnsmasq` configured with `no-resolv`.
- `dnsmasq` forwarding to `127.0.0.1#53535`.
- Direct Unbound query for `example.com` returned `NOERROR`.
- The response included the DNSSEC `AD` flag.

## Validation result

The sanitized 2026-09-11 evidence records a PASS for the SSD migration and controlled reboot validation:

- both SSD partitions auto-mounted,
- swap activated automatically,
- Tailscale recovered successfully after the earlier no-swap OOM condition was eliminated,
- Unbound started successfully,
- direct recursive DNS resolution succeeded with DNSSEC validation,
- dnsmasq continued forwarding to the local Unbound resolver.

See: [`2026-09-11/entware-ssd-migration-validation.txt`](2026-09-11/entware-ssd-migration-validation.txt).

## Stability claim boundary

This snapshot proves the validated state at the time of the controlled reboot test. It does **not** by itself prove long-term stability.

A 14-day unchanged-state observation period began on 2026-09-11. Long-term stability should only be claimed after that observation is completed and documented with final uptime, memory/swap, service, resolver, firewall, health-check, and error-log evidence.
