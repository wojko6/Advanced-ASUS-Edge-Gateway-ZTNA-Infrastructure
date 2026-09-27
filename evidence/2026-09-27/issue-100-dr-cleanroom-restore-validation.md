# Issue #100 — Clean-room restore validation

Date: 2026-09-27

## Purpose

Validate the project-native router backup with the production `scripts/restore.sh` implementation without writing to the live ASUS reference router.

The restore used the #100 alternate-root validation path on the Fedora workstation so the same archive validation, manifest verification and copy logic could run against a disposable directory.

## Source artifact

Private off-router project backup:

- archive: `asus-edge-20260927-151247.tar.gz`;
- stored on the Fedora workstation outside the public repository;
- sidecar SHA-256 verification completed successfully before restore;
- internal `SHA256SUMS` manifest verification completed successfully.

The archive contents and configuration values remain private. This evidence records only the validation result.

## Procedure

A disposable target was created on Fedora:

```text
/tmp/asus-edge-dr-cleanroom
```

The restore was executed with:

```sh
EDGE_RESTORE_ROOT=/tmp/asus-edge-dr-cleanroom \
  sh ~/restore-issue100-cleanroom.sh \
  ~/Router-DR-private/project-backups/asus-edge-20260927-151247.tar.gz \
  --apply
```

Because `EDGE_RESTORE_ROOT` was set, the restore target was the disposable Fedora directory rather than the router's live `/jffs` and `/opt` trees.

## Observed result

- every payload entry passed the internal SHA-256 verification;
- the archive passed the exact manifest-coverage check;
- the validated `/jffs/scripts/post-mount` integration hook was present in the backup;
- the restore reported the expected clean-room target;
- the restore completed successfully;
- no live router path was modified by this test.

Observed terminal result:

```text
Clean-room restore target: /tmp/asus-edge-dr-cleanroom
Restore completed. Reboot or restart services after reviewing files.
```

## Claim boundary

This validates the archive structure, content integrity and actual restore/copy path into a disposable filesystem target.

It does **not** by itself prove:

- correct runtime UID/GID reconstruction for addon-managed directories such as `/opt/var/lib/unbound`;
- service startup on Asuswrt-Merlin after a destructive rebuild;
- NVRAM restoration behavior;
- storage/swap reconstruction;
- Tailscale re-enrollment;
- full post-restore router health.

Those remain separate #100 acceptance gates.

## Security / privacy

No raw router configuration contents, credentials, Tailscale node identifiers, private addresses, NVRAM export data or authentication material are included in this evidence.
