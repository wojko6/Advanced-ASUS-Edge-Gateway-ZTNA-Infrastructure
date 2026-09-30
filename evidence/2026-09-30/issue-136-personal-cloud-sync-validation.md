# Issue #136 — Personal Cloud sync validation

**Date:** 2026-09-30  
**Scope:** Fedora `~/RouterCloud/` -> ASUS `/tmp/mnt/ROUTER_DATA/RouterCloud/` over SSH/rsync.

This artifact records live observations from the reference Fedora workstation and ASUS router. Private keys, public-key blobs, key fingerprints, raw `sshd_authkeys` values, and unrelated router state are intentionally omitted.

## Runtime baseline

Observed during validation:

- Fedora rsync: 3.5.0, protocol 32;
- router rsync: Entware 3.4.1, protocol 32;
- router SSH server: Dropbear 2025.89 on the configured non-default SSH port;
- destination: ext4 `ROUTER_DATA` filesystem mounted read/write;
- dedicated directory: `/tmp/mnt/ROUTER_DATA/RouterCloud/`.

The final Fedora client uses `rsync -rtv`, not archive mode, so workstation UID/GID ownership is not intentionally preserved on the router.

## Controlled copy and delete-safety

A controlled file was synchronized to the RouterCloud destination and was present on the SSD.

A separate delete-safety file was then:

1. created locally;
2. synchronized successfully;
3. confirmed present on the router;
4. removed locally;
5. followed by another reconciliation run.

Observed result:

```text
INITIAL_COPY_PASS
DELETE_SAFETY_PASS
```

The remote copy survived because v1 does not use `--delete`.

## Authentication-failure and recovery test

The path and timer triggers were stopped for a bounded failure test. A fresh file was created locally and the dedicated RouterCloud private-key file was temporarily moved out of its expected path.

Before final hardening, this test exposed an important client-side flaw: OpenSSH fell back to the workstation's ordinary default Ed25519 administrator key. `IdentitiesOnly=yes` and disabling the SSH agent were not sufficient to prevent that file-based fallback.

The client was corrected to include both:

```text
-F /dev/null
-o IdentityFile=none
```

together with the explicit RouterCloud `-i` identity and agent/password/keyboard-interactive disabling.

After that correction, the same missing-key scenario produced:

```text
LAST_RESULT=failure
LAST_RC=255
FAILURE_TEST_PASS
```

The new candidate file was not created on the router during the failed run.

After restoring the dedicated key, synchronization recovered immediately:

```text
LAST_RESULT=success
LAST_RC=0
RECOVERY_PASS
```

## Router-side least-privilege restriction

A dedicated RouterCloud public key is used on the router.

The final persistent key record has one forced command:

```text
restrict,command="/jffs/addons/asus-edge/bin/personal-cloud-rsync" ...
```

The wrapper at `/jffs/addons/asus-edge/bin/personal-cloud-rsync` accepts only the exact validated rsync server command for the RouterCloud destination and the matching dry-run command. All other commands are denied.

A shell attempt through the dedicated key produced:

```text
Personal Cloud: command denied
CLOUD_FINAL_SHELL_RC=126
```

Ordinary administrator SSH remained functional.

### Negative configuration finding retained

Entware `rrsync` was installed and tested during hardening. It was not retained in the final authorization path.

A persistence test revealed that combining the pre-existing project wrapper forced command with a second `rrsync` `command=` option created a regenerated key record containing two forced commands. Dropbear then rejected the key with public-key authentication failure.

The persistent record was corrected to the single project wrapper command above. After SSH-service regeneration:

```text
ADMIN_FINAL_PASS
WRAPPER_REGENERATED_PASS
SECOND_COMMAND_REMOVED_PASS
CLOUD_FINAL_SHELL_RC=126
LAST_RESULT=success
LAST_RC=0
WRAPPER_AFTER_RESTART_SYNC_PASS
```

This failed intermediate state is retained here because it explains the final one-command design.

## Full router reboot persistence

The router was rebooted after the final persistent key correction.

The readiness loop verified that Entware rsync, the project wrapper, and the RouterCloud destination had returned. Observed results:

```text
ROUTER_PERSONAL_CLOUD_READY
BOOT_READY_PASS
ADMIN_AFTER_REBOOT_PASS
WRAPPER_AFTER_REBOOT_PASS
SECOND_COMMAND_AFTER_REBOOT_REMOVED_PASS
Personal Cloud: command denied
CLOUD_AFTER_REBOOT_RC=126
LAST_RESULT=success
LAST_RC=0
FULL_REBOOT_SYNC_PASS
```

The final transfer therefore worked after a full router reboot while the dedicated key remained unable to execute an arbitrary shell command.

## systemd automation

The Fedora user units were enabled and active:

- `routercloud-sync.path`;
- `routercloud-sync.timer`;
- `routercloud-sync.service` as a oneshot worker.

The timer provides five-minute reconciliation. The path trigger provides low-latency top-level directory-change notification.

After all SSH and reboot hardening was complete, a new file was created without manually starting the service. The path-trigger acceptance result was:

```text
AUTO_PATH_FINAL_PASS
```

## Acceptance result

For the tested reference deployment:

| Acceptance item | Result |
| --- | --- |
| Controlled create/change copied to SSD | PASS |
| Local deletion does not delete SSD copy in v1 | PASS |
| Missing dedicated identity fails closed | PASS |
| Failed run does not create the pending destination file | PASS |
| Sync resumes after identity restoration | PASS |
| Dedicated key cannot execute arbitrary shell command | PASS |
| Ordinary administrator SSH remains available | PASS |
| Forced-command restriction survives SSH restart | PASS |
| Forced-command restriction survives router reboot | PASS |
| Sync works after full router reboot | PASS |
| Final `systemd.path` automatic trigger | PASS |
| Five-minute reconciliation timer | PASS |

## Boundaries

This evidence does not claim bidirectional synchronization, versioned backup history, browser-based file management, WAN file-service exposure, or universal recursive event detection from `systemd.path`. The timer remains the reconciliation fallback for nested changes. Tailscale transport is compatible with the architecture but was not separately exercised in this acceptance sequence.

Browser access is tracked separately by issue #137. Versioned snapshot/restore history is tracked separately by issue #138.
