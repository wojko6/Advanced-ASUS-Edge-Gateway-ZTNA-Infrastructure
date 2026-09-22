# Entware migration from USB flash drive to SSD

Date: 2026-09-11

## Goal

Migrate the router's active Entware installation from a USB flash drive to a SATA SSD while preserving services, configuration, permissions and boot-time behavior.

This document records a completed migration of the reference Home/SMB lab deployment. It is a historical procedure and validation record. The subsequent unchanged-state observation was deliberately closed on 2026-09-22 after continuous operation from 2026-09-11 through 2026-09-22; it did not run through the originally planned 2026-09-25 end date.

## Target storage layout

The SSD was prepared with GPT and two ext4 partitions:

- `ENTWARE` — 64 GiB-class partition for Entware and early-boot swap
- `ROUTER_DATA` — remaining space for router data and additional swap

After a clean reboot the router mounted them as:

```text
/dev/sda1 on /tmp/mnt/ENTWARE type ext4
/dev/sda2 on /tmp/mnt/ROUTER_DATA type ext4
```

## Migration method

The old Entware tree was copied from the original ext4 USB flash drive to the SSD over SSH using `tar`, preserving file ownership, permissions and symlinks. A transient Unix-domain socket used by Tailscale was intentionally not copied; it is recreated automatically by the service.

Example migration pattern:

```sh
sudo tar -C '/path/to/old/entware' -cpf - . | \
ssh -p <ssh-port> <router-admin>@<router-lan-ip> \
"tar -C '/tmp/mnt/ENTWARE/entware' -xpf -"
```

The migrated tree size was approximately 274 MiB and both `/opt/bin/opkg` and `/opt/etc/init.d/rc.unslung` were present after the copy.

## Diversion / dnsmasq logging restoration

A temporary troubleshooting change had disabled Diversion's `log-facility=/opt/var/log/dnsmasq.log` injection. Before migration the original line was restored so the migrated installation retained the intended dnsmasq logging path.

## Swap handling

The router has limited physical memory, and Tailscale failed to start when no swap was active, producing a Go runtime out-of-memory error. To avoid this during normal operation and boot:

- a 512 MiB swap file was placed on `ENTWARE` so swap becomes available early,
- a 2 GiB swap file was kept on `ROUTER_DATA` as additional capacity,
- `/jffs/scripts/post-mount` was changed to enable `${1}/myswap.swp` dynamically instead of using the old flash-drive mount path.

The resulting post-mount logic is:

```sh
#!/bin/sh
. /jffs/addons/amtm/mount-entware.mod # Added by amtm

[ -f "${1}/myswap.swp" ] && swapon "${1}/myswap.swp" 2>/dev/null # Added by amtm

[ -x "${1}/entware/bin/opkg" ] && [ -x /jffs/scripts/uiDivStats ] && /jffs/scripts/uiDivStats startup "$@" & # uiDivStats
```

This avoids hard-coding a USB label or mount path and works with the mount point passed by ASUSWRT-Merlin.

## Validation after controlled reboot

The migration was validated after a full router reboot.

### Storage

```text
/dev/sda1 on /tmp/mnt/ENTWARE type ext4
/dev/sda2 on /tmp/mnt/ROUTER_DATA type ext4
```

### Swap

```text
/tmp/mnt/ENTWARE/myswap.swp     524284 KiB
/tmp/mnt/ROUTER_DATA/myswap.swp 2097148 KiB
```

Both swap files were enabled automatically after boot.

### Services

`tailscaled` and `unbound` both returned live process IDs after reboot.

Tailscale status confirmed the router was online and still advertising exit-node capability. Exact tailnet addresses and account identifiers are intentionally omitted from repository evidence.

### DNS / Unbound

A direct DNS test against Unbound succeeded:

```sh
/opt/bin/dig @127.0.0.1 -p 53535 example.com
```

Observed result:

```text
status: NOERROR
flags: qr rd ra ad
SERVER: 127.0.0.1#53535
```

The dnsmasq forwarding path also remained correct:

```text
no-resolv
server=127.0.0.1#53535
```

## Evidence boundary

The dated artifact `evidence/2026-09-11/entware-ssd-migration-validation.txt` directly supports the SSD mounts, active swap files, running Tailscale/Unbound processes, Tailscale control-plane status, the direct Unbound DNSSEC response, and the recorded dnsmasq upstream configuration at that validation point.

It does **not** by itself prove syslog-ng recovery, end-to-end mTLS collector delivery, every firewall or printer path, every exit-node traffic path, or long-term stability. Those claims require their own dated evidence. Process presence after the controlled reboot is also narrower than continuous service availability.

## Result

For the checks recorded in the 2026-09-11 validation artifact, the SSD-backed Entware environment mounted correctly after the controlled reboot, both swap files were active, Tailscale and Unbound were running, and the tested resolver configuration remained intact.

The old flash drive is no longer required for the active Entware runtime. A separate unchanged-state observation later completed the bounded 2026-09-11 through 2026-09-22 interval; this migration document does not by itself prove indefinite long-term stability.
