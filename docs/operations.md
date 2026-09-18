# Operations and recovery

## Current reference-state gate

The reference deployment completed its SSD migration and controlled reboot validation on 2026-09-11. A 14-day unchanged-state stability observation runs through 2026-09-25.

Until that observation completes, the normal change workflow below is **not** an instruction to deploy routine changes to the reference router. Repository/documentation work, CI/mock testing, workstation-local endpoint tests, and read-only router observations may continue. Defer routine firewall, DNS, Unbound, Tailscale, startup-hook, filtering-list, service, package, and reboot changes until the gate ends.

An active compromise or materially unsafe exposure takes priority. If an emergency router change is required, document the interruption and start a new unchanged-state observation after returning to a known-good state.

## Change workflow

Use this workflow for a planned maintenance window outside an active unchanged-state observation:

1. Back up JFFS and relevant Entware configuration.
2. Edit the repository copy, not the live file first.
3. Run static/mock tests.
4. Keep a LAN recovery session open.
5. Install without `--apply`, inspect deployed files, and review the quarantined legacy hooks.
6. Keep `EDGE_RUN_LEGACY_HOOKS="0"` unless each previous hook is proven compatible.
7. Apply the firewall and run health checks.
8. Run the remote security matrix and inspect counters/logs.
9. Commit sanitized evidence and the configuration change.

## Backup

```sh
./scripts/backup.sh /opt/backups/asus-edge
sha256sum -c /opt/backups/asus-edge/BACKUP.tar.gz.sha256
```

The backup is created with a restrictive umask and the resulting archive plus sidecar checksum are set to mode `0600`. The archive contains an internal `SHA256SUMS` manifest covering every backed-up payload file. This provides corruption/integrity checking for the backup contents, but neither the internal manifest nor the sidecar checksum authenticates a backup obtained from an untrusted source. The script intentionally excludes Tailscale state and authentication material.

Move backups off the router-attached SSD and keep an independent copy on another trusted system. Other included configs can still contain internal data; encrypt backups at rest outside this repository.

Do not treat the router-attached SSD as the only backup merely because it is now the persistent Entware/data device. A failure, filesystem corruption, operator error, or compromise affecting the router can affect locally attached storage at the same time.

## Restore

Restore is dry-run by default:

```sh
./scripts/restore.sh BACKUP.tar.gz --dry-run
./scripts/restore.sh BACKUP.tar.gz --apply
```

The restore rejects links, special files, unsafe paths, duplicate archive
entries and multiple top-level roots. It requires every payload file to appear
exactly once in the internal SHA-256 manifest before copying anything to the
router. Hashes detect corruption; they do not authenticate an untrusted backup.
Only regular files and directories with simple path names (letters, digits,
underscore, dot, dollar sign, hyphen and slash) are accepted. A copy failure
returns non-zero and reports a potentially partial restore. Review paths and
maintain physical access; restore is not an atomic filesystem transaction.

`--dry-run` validates the archive structure, accepted entry types, manifest coverage and file hashes without copying payload files into `/jffs` or `/opt`. Use it before every planned restore. `--apply` then copies only the `jffs` and `opt` trees present in the verified archive. It does not delete unrelated files that are absent from the backup, does not restore Tailscale state, and does not automatically restart services or reboot the router. Review the restored files before choosing the required recovery action.

The installer snapshots the configuration, both hooks, managed binaries and
preserved legacy hooks before changing live files. A failed copy or failed
`--apply` restores that entire set, including removing files that did not exist
before a first install. After a failed firewall apply it restarts the firmware
firewall only if file rollback succeeds. Recovery errors retain the snapshot
and require local intervention. The snapshot directory must be new; if two
installs begin within the same second, a name collision aborts before live
files are changed. Do not run concurrent installations.

## Fedora clean-room Disaster Recovery

The repository also contains the host-side Fedora restore finalization helper used during clean-room recovery validation:

```sh
sudo sh ./scripts/fedora-dr-restore.sh /mnt/sysroot --dry-run
sudo sh ./scripts/fedora-dr-restore.sh /mnt/sysroot --apply
```

Run it from Fedora Live/rescue after the restored Fedora root, `/boot`, and `/boot/efi` filesystems are mounted below the target root. The helper refuses `/`, refuses a target backed by the same filesystem source as the running root, and requires the target root, `/boot`, and `/boot/efi` to be exact mountpoints rather than ordinary directories. **Do not point it at the running host.**

The helper is dry-run by default. Before changing anything it:

1. identifies the filesystem currently mounted as the target `/boot`;
2. obtains its current filesystem UUID;
3. checks the target `/etc/fstab` `/boot` entry;
4. checks the Fedora GRUB configuration locations for a stale old `/boot` UUID;
5. reports the SELinux relabel that will be performed.

With `--apply`, it creates an atomically unique private rollback directory under `/var/tmp`, updates the target `/boot` UUID references, and runs the restored system's `restorecon -RF /boot` through `chroot`. If the finalization step fails, it restores the backed-up configuration files. SELinux relabel changes are policy-derived and are not reverse-applied by the rollback path.

This helper is deliberately a **finalization helper**, not the complete restore engine. Partition creation, filesystem creation, Btrfs receive/snapshot work, restoring root/home/boot/EFI payloads, adapting non-`/boot` filesystem identities, regenerating kernel/initramfs/GRUB state where required, and creating/verifying the firmware boot entry remain explicit recovery steps until they receive equivalent automation and regression coverage.

This procedure was validated in the 2026-09-18 clean-room VMware restore. The validation found that the restored target could have a different `/boot` filesystem identity and that the restored `/boot` tree initially carried `unlabeled_t` SELinux labels. The helper turns those observed recovery steps into an explicit, repeatable procedure. The detailed sanitized validation record is [FEDORA-DR-RESTORE-VALIDATION-2026-09-18.md](FEDORA-DR-RESTORE-VALIDATION-2026-09-18.md).

## Emergency rollback

From a LAN/serial recovery session:

```sh
./scripts/uninstall.sh
service restart_firewall
```

`uninstall.sh` removes the project-owned IPv4 and IPv6 runtime chains/jumps and restores a preserved pre-project hook only when the current hook is marked as ASUS Edge managed. It intentionally leaves the project configuration and backups in place for review. It does **not** itself restart the firmware firewall, stop Tailscale/Unbound/syslog-ng, remove packages, erase Tailscale state, or delete unrelated router configuration. Treat `service restart_firewall` as a separate recovery action and verify the resulting state locally.

If hook restoration or managed-hook removal fails, `uninstall.sh` returns non-zero and reports an incomplete uninstall. Do not continue with a remote-only recovery assumption; inspect `/jffs/scripts` through local access before deciding whether to restart the firewall.

If hooks cannot run, rename the managed hook files under `/jffs/scripts/`, restore the corresponding installer backup, and restart the router. The installer prints its timestamped backup path.

An emergency rollback during the active stability observation interrupts that observation. Record why it was necessary and establish a new known-good baseline before restarting the observation period.

## Updates

Never place `opkg update` or package upgrades in a boot hook. Use a planned maintenance window outside the active stability gate:

```sh
./scripts/backup.sh /opt/backups/asus-edge
./scripts/update-tailscale.sh
```

`update-tailscale.sh` is deliberately coupled to the managed recovery path. Before it touches Entware package metadata, it requires both `/jffs/addons/asus-edge/bin/services-start` and `/jffs/addons/asus-edge/bin/healthcheck.sh` to exist and be executable. A failed `opkg update`, failed upgradable-package query, failed Tailscale package upgrade, failed post-update service recovery, or failed final health check returns non-zero. If no Tailscale update is advertised, the script exits without changing the package. Treat any non-zero result after `opkg upgrade tailscale` as a maintenance incident: keep local/LAN recovery access, inspect the managed service logs and health output, and do not assume that the package transaction itself was rolled back.

Entware may not retain a previous package version. Download/retain the known-good package before an upgrade if a package-level rollback is required. The maintenance helper does not implement package rollback; its recovery contract is to restore the managed runtime path where possible and fail visibly when that cannot be verified.

## Resolver ownership

Use exactly one active upstream path behind dnsmasq. The validated reference path is `dnsmasq → Unbound:53535`. If another DNS component manages `dnsmasq.postconf`, verify whether it redirects dnsmasq to a different local listener; in that state Unbound may be healthy but unused by clients.

For amtm Unbound Manager, treat `/opt/var/lib/unbound/unbound.conf` as the generated runtime configuration. Do not replace it with the standard Entware example. Back up and review both the manager hook and runtime configuration before changes.

With amtm, `post-mount` sources `mount-entware.mod`, which already runs `rc.unslung`. Keep `EDGE_RUN_RC_UNSLUNG="0"` so the project does not launch a parallel Entware startup. The project waits for NTP readiness and a configurable quiet interval after amtm startup activity and preserves a stable Unbound or syslog-ng process. If amtm does not leave Unbound running, recovery validates the generated configuration and starts `/opt/sbin/unbound` directly. Validation and launch receive a command-scoped `LD_LIBRARY_PATH=/opt/lib:/opt/usr/lib`; this prevents the early-boot loader from pairing Entware's `libunbound` with the older firmware libc, without changing the global environment that `rc.unslung` manages. Recovery intentionally bypasses `S61unbound` because that wrapper restarts dnsmasq after every launch attempt, including a failed one, which can feed the boot-time socket race. Before direct recovery it removes the Unbound PID file only when no Unbound process exists. Required-service failures are returned as a non-zero `services-start` status instead of being masked. Set `EDGE_RUN_RC_UNSLUNG="1"` only on deployments where no external hook owns Entware startup. Inspect `/tmp/asus-edge-entware-start.log`, `/tmp/asus-edge-unbound-start.log`, or `/tmp/asus-edge-syslog-ng-start.log` when startup fails.

## Tailscale OOM during boot

On this low-memory 32-bit router, `tailscaled` has previously failed with `out of memory
allocating heap arena map` even when its resident memory was modest. With strict
kernel overcommit, the daemon's virtual-memory reservation can be rejected if
swap has not yet been activated by `post-mount`.

The current reference deployment uses SSD-backed persistent storage and active swap validated after the 2026-09-11 controlled reboot. The original failure mode remains relevant to startup ordering, but references to USB-flash-backed swap describe the pre-migration state rather than the current storage layout.

Keep `EDGE_REQUIRE_SWAP="auto"` or set it explicitly to `1`. The managed
`services-start` hook waits for active swap, removes an orphaned socket, and
retries the daemon using the general service-attempt settings. It keeps the
previous daemon log as `/opt/var/log/tailscaled.log.previous`.

Verify recovery during a scheduled maintenance/validation window, not by intentionally rebooting the router during the active stability gate:

```sh
cat /proc/swaps
pidof tailscaled
/jffs/addons/asus-edge/bin/healthcheck.sh
```

Review and sanitize daemon logs before sharing or publishing them.

## Android printer troubleshooting over Tailscale

Keep only one Android print service enabled while testing and add the printer by
its LAN address. First verify the printer web interface through the Tailscale
subnet route, then inspect the managed forward-chain counters while submitting
one small job.

A working SNMP exchange proves reachability and printer-status access, not job
submission. If packet capture shows UDP/161 request/response traffic but no TCP
connection to the configured IPP or raw-print port, the job stopped inside the
Android print stack. Opening more firewall ports will not correct that state.

Use a header-only capture when diagnosis is required and live-router capture is appropriate for the current validation phase:

```sh
tcpdump -ni any -nn -s 96 \
  'host PRINTER_LAN_IP and (tcp port 80 or tcp port 631 or tcp port 9100 or udp port 161)'
```

Before retrying, cancel the job, force-stop the Android print spooler and print
plugin, clear the spooler's pending-job data, and restart the phone. Test with a
single small page. Some mobile print services do not submit jobs while cellular
data is the active transport even though Tailscale routing and SNMP work. An
external Wi-Fi connection or hotspot with Tailscale enabled was validated as a
working remote-print path for the tested Samsung plugin.

Unrelated denied traffic must remain denied. For example, a phone attempting to
reach a workstation service such as TCP/1716 is not printer traffic and is not a
reason to expand `EDGE_PRINTER_TCP_PORTS`.

## Collector log retention

The centralized collector has a separate retention helper, `scripts/asus-edge-log-retention.sh`. It is not a router boot hook and does not modify the reference router. Run it on the collector host first in its default dry-run mode and inspect the candidate files before applying retention:

```sh
./scripts/asus-edge-log-retention.sh --dry-run
./scripts/asus-edge-log-retention.sh --apply
```

By default it operates under `/var/log/asus-edge`, compresses eligible older logs after 1440 minutes, deletes eligible compressed logs after 43200 minutes, and excludes the current day's log from those actions. Override its environment settings only on the collector after reviewing the target directory and retention requirements. Keep collector retention evidence separate from router stability evidence.

## Log rotation

Use unique `cru` identifiers for every job:

```sh
cru a ASUS_Edge_LogRotate_1200 "0 12 * * * /opt/sbin/logrotate /opt/etc/logrotate.conf"
cru a ASUS_Edge_LogRotate_1800 "0 18 * * * /opt/sbin/logrotate /opt/etc/logrotate.conf"
cru l | grep ASUS_Edge
```

Do not reuse one identifier for multiple schedules because the later entry can replace the earlier task.