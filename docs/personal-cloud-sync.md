# Personal Cloud one-way sync

This component implements issue #136: an auditable, one-way file sync from a Fedora workstation to the SSD attached to the ASUS router.

## Design

```text
Fedora ~/RouterCloud
        |
        | rsync -rtv over SSH
        v
ASUS /tmp/mnt/ROUTER_DATA/RouterCloud/
```

Version 1 deliberately does **not** use `--delete`. Removing a local file therefore does not remove the copy already stored on the router SSD.

The Fedora side uses:

- `scripts/routercloud-sync.sh`;
- a dedicated Ed25519 identity at `~/.ssh/id_ed25519_routercloud` by default;
- a `systemd.path` unit for low-latency top-level change triggers;
- a five-minute `systemd.timer` as the full-tree reconciliation mechanism;
- `flock` to prevent overlapping sync runs;
- a local state file at `~/.local/state/routercloud-sync/status.env`.

The router side uses `router/scripts/personal-cloud-rsync` as a forced-command wrapper. The dedicated public key must be installed with an `authorized_keys` restriction equivalent to:

```text
restrict,command="/jffs/addons/asus-edge/bin/personal-cloud-rsync" ssh-ed25519 <PUBLIC_KEY> personal-cloud-rsync
```

Do not publish the private key or the router's complete `sshd_authkeys` value.

## Router preparation

Install Entware rsync and create the destination:

```sh
/opt/bin/opkg install rsync
mkdir -p /tmp/mnt/ROUTER_DATA/RouterCloud
chmod 0700 /tmp/mnt/ROUTER_DATA/RouterCloud
```

Copy `router/scripts/personal-cloud-rsync` to:

```text
/jffs/addons/asus-edge/bin/personal-cloud-rsync
```

with mode `0755`.

Persist the restricted public key using the firmware's SSH authorized-key mechanism while preserving all existing keys. Asuswrt-Merlin materializes those entries into `/root/.ssh/authorized_keys` at runtime. Verify the restricted key after a reboot before relying on automation.

The wrapper is fail-closed: it accepts only the exact rsync server commands used by the tested `-rtv` live and dry-run modes for the dedicated RouterCloud path. Shell commands, SCP, a different rsync flag set, and a different destination are denied. A future rsync client upgrade may change the generated server command; in that case synchronization should fail closed until the wrapper is revalidated.

## Fedora installation

Install the client:

```sh
mkdir -p ~/.local/bin ~/.config/systemd/user
install -m 0700 scripts/routercloud-sync.sh ~/.local/bin/routercloud-sync
install -m 0644 config/systemd/routercloud-sync.service ~/.config/systemd/user/
install -m 0644 config/systemd/routercloud-sync.timer ~/.config/systemd/user/
install -m 0644 config/systemd/routercloud-sync.path ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now routercloud-sync.timer routercloud-sync.path
```

The defaults match the validated deployment:

```text
source:  ~/RouterCloud/
host:    192.168.50.1
user:    admin1
port:    1122
key:     ~/.ssh/id_ed25519_routercloud
target:  /tmp/mnt/ROUTER_DATA/RouterCloud/
```

The source, host, user, port and key can be overridden with `ROUTERCLOUD_SOURCE`, `ROUTERCLOUD_HOST`, `ROUTERCLOUD_USER`, `ROUTERCLOUD_SSH_PORT` and `ROUTERCLOUD_KEY`. The server-side destination remains intentionally fixed by the forced-command wrapper.

## Operations

Inspect the latest result:

```sh
cat ~/.local/state/routercloud-sync/status.env
journalctl --user -u routercloud-sync.service --no-pager
systemctl --user list-timers routercloud-sync.timer --all
systemctl --user status routercloud-sync.path
```

A successful status file contains `LAST_RESULT=success` and `LAST_RC=0`. A transport failure records `LAST_RESULT=failure` with the rsync/SSH return code.

`systemd.path` is an acceleration path, not the sole correctness mechanism. Directory watches do not guarantee recursive detection of every deep-file modification. The periodic timer therefore remains enabled to reconcile the complete tree.

## Security properties

- no WAN-facing service is added;
- the automation key is restricted to the forced rsync command;
- no automatic deletion occurs in v1;
- destination ownership is controlled by the router rather than copied from Fedora because the client uses `-rtv`, not archive mode;
- SSH uses `BatchMode=yes`, `IdentitiesOnly=yes`, strict host-key checking and a connection timeout;
- failed transport leaves existing destination files unchanged under the tested failure case;
- the local lock prevents concurrent rsync instances.

See `evidence/2026-09-30/issue-136-personal-cloud-sync-validation.md` for the validation record.
