# Pi-hole DR backup generator — issue #129

**State (2026-10-09):** Generator merged in [PR #204](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/204); six offline regressions, operator-run read-only production capture, encrypted/private round-trip and independent file/manifest checks **PASS**. FTL capabilities reapplied successfully on a disposable Fedora tmpfs restored copy. A controlled reboot of the **already provisioned** router also passed; this does **not** validate a complete router or Entware rebuild. See the [reboot acceptance](../evidence/2026-10-09/issue-129-pihole-dr-reboot-persistence.md) and [rebuild runbook](pihole-dr-rebuild-runbook.md).

The Fedora-side `scripts/backup-pihole-dr.py` reads allowlisted Pi-hole artifacts from the TUF-AX5400 through SSH. It does **not** write to the router. Only private Fedora tmpfs holds the unencrypted transfer and recovery archive; only the AES256 GPG encrypted `.tar.gz.gpg` and checksum sidecar are persisted off-router. Do not publish backups, logs containing private data, or NVRAM exports.

## Source and policy

- Source: specifically enumerated Pi-hole configuration, Gravity SQLite DB, static FTL binary, `nonroot`, Entware helpers, router DNS integration snippets and the post-mount reference hook.
- Intentionally excluded: Pi-hole FTL query-history DB, Tailscale authentication state, credentials outside the allowlist, attached user data, and NVRAM (separate native encrypted CFG).
- Pi-hole account: `uid=999`, `gid=999`, failure on unexpected values.
- Pi-hole directory: `999:999 / 0755`; TOML and Gravity: `999:999 / 0640`.
- FTL binary and known init helpers: `0:0 / 0755`.
- FTL capabilities: capture the exact `getcap` output in `manifest/ftl-capabilities.txt`, fail if it differs from the reviewed 7-capability baseline. **The tar archive does not preserve the binary capability xattr**; apply and verify capabilities on the recovery target after installing the reviewed FTL binary.
- `post-mount` is stored **only** under `recovery-reference/jffs/scripts/post-mount`; never auto-restore this addon-managed hook. Review and reconcile swap-before-Entware ordering manually.
- Existing `0666` modes for the two DNS integration configs may be preserved as observed but are not approved hardened permissions; review writers under separate security scope before changing them.
- The source file SHA256 set is read both before and after SSH TAR capture; each file's snapshot hash must match the router. This detects ordinary concurrent changes, but is not an atomic cross-file snapshot.
- Gravity is examined by SQLite `PRAGMA integrity_check` and requires `journal_mode=delete`. **Do not run if Pi-hole Gravity maintenance/updates are actively modifying the database**. For future high-concurrency or WAL deployments, replace raw file capture with a reviewed SQLite online-backup mechanism.
- The output includes a complete file SHA-256 manifest and is checked before GPG encryption, then verified after decryption.

## Installation and offline regression

Work on a dedicated branch. Place this package's `scripts/`, `tests/` and `docs/` files under your existing Git repository. Do not commit private backups.

```sh
python3 tests/test_pihole_dr_backup.py
python3 -m py_compile scripts/backup-pihole-dr.py
```

All six tests use synthetic content and never contact the ASUS router.

## Run (after local review)

On Fedora, with the normal, private `XDG_RUNTIME_DIR` mounted as tmpfs, enough available space, functional SSH key access and pinentry/GPG configuration:

```sh
python3 scripts/backup-pihole-dr.py \
  --router admin1@192.168.50.1 \
  --port 1122 \
  --dest "$HOME/Archiwa/ASUS-Edge-Issue-129"
```

The command reads router files without changing them. It fails closed on SSH nonzero status, changing sources, unexpected files, unexpected UID/GID/mode or capabilities, or invalid Gravity SQLite. It prompts for a GPG passphrase and writes a new uniquely timestamped private encrypted archive. Any failed transfer or processing discards the plaintext tmpfs workspace. The destination directory must be owned by the invoking user with no group/other permissions.

A successful generator is **not** proof of a complete recovery. The verified private archive and isolated Pi-hole/FTL tests establish recovery components only; a **new blank-device/Entware** rebuild and post-restore validation are still required. NVRAM must be restored separately using a compatible router/firmware; Unbound/Core archives, Entware installation, storage/swap, startup ordering, Pi-hole `setcap`, DHCP, firewall and Tailscale re-enrollment require the documented rebuild procedure.

## Production permission reapplication — recovery target only

After verifying the package provenance and rebuilding the expected 999:999 service account, restore the Pi-hole `opt/etc/pihole` directory and Gravity ownership/mode from the archive as verified. For the reviewed FTL binary, apply the capability string from the private `manifest/ftl-capabilities.txt` via a controlled `setcap` command, then verify `getcap` on the target. Do not apply changes directly on the healthy reference router just to test a backup.
