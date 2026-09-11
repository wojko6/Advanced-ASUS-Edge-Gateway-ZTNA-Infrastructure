# Entware migration from USB flash drive to SSD

Date: 2026-09-11

## Goal

Migrate the router's production Entware installation from a USB flash drive to a SATA SSD while preserving services, configuration, permissions and boot-time behavior.

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

## Result

The Entware installation, Tailscale, Unbound, dnsmasq integration and swap configuration all survived the controlled reboot and started automatically from the SSD-backed environment.

The old flash drive is no longer required for the active Entware runtime.
