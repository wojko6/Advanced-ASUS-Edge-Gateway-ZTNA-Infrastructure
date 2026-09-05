# USB infrastructure hardening

## Scope

The reference deployment keeps Entware under `/opt` on router-attached USB storage. That storage is infrastructure, not a general-purpose LAN file share or media library.

If Asuswrt USB sharing services are enabled, a LAN client can receive visibility into the mounted filesystem even when the Tailscale policy and project-owned `EDGE_TS_*` chains are working correctly. This is a separate LAN trust boundary and must be controlled independently.

## Observed finding

A LAN client was able to enumerate the Entware directory tree through the router's UPnP/DLNA media server. The generated MiniDLNA configuration used:

```text
media_dir=/mnt
```

which caused the media server to browse the router's mounted USB hierarchy, including the infrastructure volume.

SMB was also enabled on the router, but the Entware share required an authenticated router account and guest SMB access was disabled. The remediation nevertheless removed both unnecessary exposure paths because the infrastructure USB device is not intended to be user-accessible.

## Remediation

For deployments where the USB device exists only to host Entware and project services:

1. Disable the Asuswrt UPnP/DLNA media server in the web UI.
2. Disable Asuswrt Samba/SMB USB sharing if it is not explicitly required.
3. Do not edit generated `/etc/minidlna.conf` or `/etc/smb.conf` as the primary fix; persist the intended state through firmware settings.
4. Keep `/opt` mounted and validate Tailscale, Unbound, syslog-ng, firewall chains, and DNSSEC after the change.
5. Reboot and repeat the validation to prove persistence.

Do not publish router serial numbers, USB serial numbers, real host inventories, private LAN addresses, authentication material, or unsanitized NVRAM output as evidence.

## Policy controls

The example configuration provides two deployment controls:

```sh
EDGE_REQUIRE_DLNA_DISABLED="1"
EDGE_REQUIRE_SMB_DISABLED="1"
```

The secure defaults are appropriate when the attached USB device is infrastructure-only. A deployment that intentionally provides media or file sharing may set the relevant control to `0`, but that exception should be documented and tested separately.

Run the dedicated check on the router:

```sh
/jffs/addons/asus-edge/bin/check-usb-exposure.sh
```

Expected output for an infrastructure-only USB deployment includes:

```text
[OK]   MiniDLNA disabled in NVRAM
[OK]   minidlna process stopped
[OK]   DLNA/SSDP ports closed
[OK]   smbd process stopped
[OK]   nmbd process stopped
[OK]   SMB ports closed
```

## Reboot validation

After a router reboot, validate all of the following:

```sh
echo "dms_enable=$(nvram get dms_enable)"
pidof minidlna || echo "MINIDLNA_STOPPED"
pidof smbd || echo "SMBD_STOPPED"
pidof nmbd || echo "NMBD_STOPPED"
netstat -lnptu 2>/dev/null | grep -E ':(139|445|1900|8200)[[:space:]]' \
  || echo "USB_SHARING_PORTS_CLOSED"
/jffs/addons/asus-edge/bin/healthcheck.sh
/jffs/addons/asus-edge/bin/check-usb-exposure.sh
```

For the hardened reference state, `dms_enable` must be `0`, the three service processes must be absent, the four sharing/discovery ports must be closed, and both health checks must exit successfully.

## Reference runtime acceptance

The merged implementation was subsequently staged from `main` on the reference router without reapplying the firewall policy. The workstation was first updated to commit `4b9c196266921c67ca1d8a701831176bcc4f0442` and the static test suite passed. The staged installer then deployed the dedicated check into `/jffs/addons/asus-edge/bin/`.

After installation and after a full reboot, the reference deployment produced the following sanitized acceptance state:

```text
staged installer: PASS
check-usb-exposure.sh: 0 failures, 0 warnings, exit 0
healthcheck.sh: 0 failures, 0 warnings, exit 0
dms_enable=0
minidlna: stopped
smbd: stopped
nmbd: stopped
TCP/UDP 139, 445, 1900, 8200: no listeners
post-reboot acceptance: PASS
```

The installer-integration acceptance item is therefore complete for the reference deployment.

## Security rationale

Tailscale identity enforcement protects paths entering through the tailnet. It does not automatically remove services exposed directly to the local LAN. Infrastructure storage therefore requires its own least-privilege policy: no unnecessary discovery, media indexing, or file-sharing service should expose the Entware filesystem.
