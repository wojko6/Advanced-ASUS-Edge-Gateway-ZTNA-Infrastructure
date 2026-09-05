# USB infrastructure exposure validation — 2026-09-05

## Finding

A LAN client could enumerate the directory structure of the router-attached infrastructure USB device through the UPnP/DLNA media server.

## Root cause

The generated MiniDLNA configuration used the entire mount hierarchy as its media root:

```text
media_dir=/mnt
```

The infrastructure USB device hosted Entware and project services and was not intended to be a LAN media source.

## Impact

A non-tailnet LAN client could browse the Entware directory tree. No claim is made here that SMB write access was available. The issue was information exposure through an unnecessary LAN-side service and a violation of the intended infrastructure-storage trust boundary.

## Remediation

- Disabled the Asuswrt UPnP/DLNA media server through persistent firmware settings.
- Disabled unused Samba/SMB USB sharing.
- Left the USB device mounted for `/opt` and Entware services.

## Validation

After remediation and again after a router reboot:

```text
dms_enable=0
minidlna: stopped
smbd: stopped
nmbd: stopped
TCP/UDP 139, 445, 1900, 8200: no listeners
project healthcheck: 0 failures, 0 warnings
project healthcheck exit status: 0
```

The LAN client no longer discovered or browsed the infrastructure USB tree.

## Status

**CLOSED — remediation persisted across reboot and the core ASUS Edge health check remained successful.**

## Publication notes

This record intentionally omits real LAN addresses, router/USB serial numbers, client inventory, authentication material, and unsanitized NVRAM output.
