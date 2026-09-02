# Operations and recovery

## Change workflow

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

Move backups off the USB storage attached to the router. The script excludes Tailscale state but other configs can still contain internal data; encrypt at rest outside this repository.

## Restore

Restore is dry-run by default:

```sh
./scripts/restore.sh BACKUP.tar.gz --dry-run
./scripts/restore.sh BACKUP.tar.gz --apply
```

The restore verifies the internal manifest before writing. Review paths and maintain physical access.

## Emergency rollback

From a LAN/serial recovery session:

```sh
./scripts/uninstall.sh
service restart_firewall
```

If hooks cannot run, rename the managed hook files under `/jffs/scripts/`, restore the corresponding installer backup, and restart the router. The installer prints its timestamped backup path.

## Updates

Never place `opkg update` or package upgrades in a boot hook. Use a maintenance window:

```sh
./scripts/backup.sh /opt/backups/asus-edge
./scripts/update-tailscale.sh
```

Entware may not retain a previous package version. Download/retain the known-good package before an upgrade if a package-level rollback is required.

## Resolver ownership

Use exactly one active upstream path behind dnsmasq. A supported deployment is `dnsmasq → Unbound:53535`. If NextDNS manages `dnsmasq.postconf`, verify whether it exits after configuring `127.0.0.1:5342`; in that state Unbound may be valid but unused.

For amtm Unbound Manager, treat `/opt/var/lib/unbound/unbound.conf` as the generated runtime configuration. Do not replace it with the standard Entware example. Back up and review both the manager hook and runtime configuration before changes.

## Log rotation

Use unique `cru` identifiers for every job:

```sh
cru a ASUS_Edge_LogRotate_1200 "0 12 * * * /opt/sbin/logrotate /opt/etc/logrotate.conf"
cru a ASUS_Edge_LogRotate_1800 "0 18 * * * /opt/sbin/logrotate /opt/etc/logrotate.conf"
cru l | grep ASUS_Edge
```

Do not reuse one identifier for multiple schedules because the later entry can replace the earlier task.
