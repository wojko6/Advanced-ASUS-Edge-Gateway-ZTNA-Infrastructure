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

## Post-merge runtime acceptance

After PR #31 was merged, the updated `main` was staged on the reference router without reapplying firewall policy. The local workstation first fast-forwarded to the merged commit and reran the full static suite successfully.

Sanitized acceptance results:

```text
source commit: 4b9c196266921c67ca1d8a701831176bcc4f0442
static test suite: PASS
staged installer: PASS
installed check-usb-exposure.sh: PASS
USB exposure check: 0 failures, 0 warnings, exit 0
core project healthcheck: 0 failures, 0 warnings, exit 0
post-reboot acceptance: PASS
dms_enable=0
minidlna: stopped
smbd: stopped
nmbd: stopped
TCP/UDP 139, 445, 1900, 8200: no listeners
```

This closes the installer-integration acceptance item: the merged `main` successfully installed the dedicated USB exposure check into the project runtime path, and the hardened state persisted after reboot while the existing Tailscale, firewall, Unbound/DNSSEC, swap, and syslog-ng health invariants remained successful.

## Status

**CLOSED — remediation persisted across reboot, the merged regression control was deployed successfully, and post-reboot runtime acceptance passed.**

## Publication notes

This record intentionally omits real LAN addresses, router/USB serial numbers, client inventory, authentication material, and unsanitized NVRAM output.
