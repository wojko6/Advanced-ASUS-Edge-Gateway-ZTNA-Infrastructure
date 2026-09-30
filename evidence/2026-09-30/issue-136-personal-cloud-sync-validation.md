# Issue #136 — Personal Cloud sync validation

Date: 2026-09-30

Scope: Fedora `~/RouterCloud` to the dedicated router SSD directory `/tmp/mnt/ROUTER_DATA/RouterCloud/` over SSH/rsync.

## Runtime baseline

- Fedora rsync: 3.5.0, protocol 32.
- Router rsync: Entware 3.4.1, protocol 32.
- Router SSH server: Dropbear 2025.89 on port 1122.
- Destination filesystem: ext4 on `/dev/sda2`, mounted read/write at `/tmp/mnt/ROUTER_DATA`.
- Dedicated destination directory created with mode 0700.
- Existing project healthcheck before and after the work: 0 failures, 0 warnings.

## Data-path validation

A controlled test file was copied from Fedora to the router. SHA-256 matched on both endpoints:

```text
bcaba5ff93e102b8919eab862f51304499d99bcd1100e3dfb47ee5894a07eee7
```

A local-removal test then moved the source file outside the sync tree and ran rsync without `--delete`. The remote copy survived and retained the same hash. The local test file was restored afterwards.

The initial archive-mode trial preserved Fedora UID/GID 1000:1000 on the destination. The final client therefore uses `rsync -rtv`, after which destination ownership remained `admin1:root`.

## Restricted SSH identity

A dedicated Ed25519 identity was created for RouterCloud automation. The private key is not stored in this repository.

The router key entry uses a forced command and Dropbear's `restrict` option:

```text
restrict,command="/jffs/addons/asus-edge/bin/personal-cloud-rsync" ...
```

The restricted wrapper accepts only the validated rsync server command for the dedicated destination. Validation results:

- dedicated-key `rsync -rtv`: PASS;
- arbitrary `id` command: denied;
- previous archive-mode `rsync -av`: denied;
- dedicated-key persistence after router reboot: PASS;
- normal administrator SSH after key addition: PASS.

After reboot the active authorized-key count and NVRAM key count were both three, with exactly one RouterCloud entry.

## Automatic synchronization

A user `systemd` oneshot service was validated successfully.

The five-minute reconciliation timer ran without manual intervention. A new file was transferred on the scheduled run and matched locally/remotely:

```text
9639a853f43ac45d94c80cd0afc4e1af4c149b5a1c96d8cfd0f576e58f0b03ec
```

The `systemd.path` trigger was then enabled. A newly created top-level file appeared on the router after approximately two seconds and matched locally/remotely:

```text
b6c168f207d332f77322f25857f1ea3c22e4b31fb37f34e9d1e20220c4a89dc4
```

The path unit remained active and the timer remained active.

## Failure and recovery

Transport failure was simulated by temporarily directing the client to an unused SSH port while the path and timer triggers were stopped.

Observed failure state:

```text
ActiveState=failed
Result=exit-code
ExecMainStatus=255
LAST_RESULT=failure
LAST_RC=255
```

The pre-existing remote test file retained the same SHA-256 before and after the failed attempt, so destination integrity was preserved.

The original client configuration was restored and the service was started again. Recovery result:

```text
Result=success
ExecMainStatus=0
LAST_RESULT=success
LAST_RC=0
PATH=active
TIMER=active
```

This satisfies the issue acceptance criteria for controlled copy/update, no automatic deletion in v1, non-corrupting transport failure, and clean recovery.
