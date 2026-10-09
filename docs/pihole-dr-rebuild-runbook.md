# Pi-hole-aware router reconstruction runbook — issue #129

**State: documented recovery order; complete blank-device execution NOT TESTED.**  
**Applies to:** reviewed ASUS TUF-AX5400 / GNUton-Asuswrt-Merlin reference baseline.  
**Safety:** not an unattended production restore script. Do not run these steps against the healthy reference router simply to exercise a backup.

This runbook extends the [router DR baseline](router-disaster-recovery.md). It records critical order and acceptance criteria, not a claim that restoring three archives automatically rebuilds the machine.

## Phase 0 — recovery authorization and prerequisites

1. Diagnose the actual failure. Prefer read-only inspection and service-specific recovery over restoring a working device.
2. Obtain physical LAN access and an agreed maintenance window. Do not rely exclusively on the affected router's DNS, WAN or Tailscale.
3. Confirm a **compatible model and firmware baseline** before considering native ASUS CFG import. A CFG file is not portable proof of cross-model or cross-firmware compatibility.
4. Confirm private, off-router artifacts and checksum sidecars for (a) ASUS Edge CORE, (b) Pi-hole DR, and (c) native CFG. Record source provenance and package versions. Neither sidecar nor encrypted archive belongs in the public repo.
5. Validate GPG decryption, external SHA-256 integrity and the archive's internal file manifest on a **private ephemeral tmpfs workspace** with sufficient free space; keep decrypted files away from normal disk, Git and shell history. Stop on any mismatch or unknown archive member.
6. Distinguish backup currency from service health at capture time. The Pi-hole generator performs pre/post SHA checks but not an atomic cross-file transaction; never capture Gravity while it is being modified.

**Gate 0:** required private artifacts decrypt, their manifests match, target compatibility is reviewed and a non-router fallback management path exists. Otherwise **STOP**.

## Phase 1 — firmware, volumes and baseline platform

1. Install/recover the reviewed firmware on the compatible router. Review and, only if necessary and compatible, restore its native CFG via the supported ASUS mechanism; do not indiscriminately import it onto a healthy router.
2. Recreate intended `ENTWARE` and `ROUTER_DATA` filesystems and mount roles, JFFS script support, and relevant USB/storage identifiers as operator-reviewed configuration. Do not assume USB `/dev/sdX` naming stability.
3. Recreate intended swap files. The reference requires **swap activation before AMTM-managed Entware service startup**. The archived `post-mount` is at `recovery-reference/` for comparison only. Do **not** overwrite the AMTM-owned live hook with it. Reconcile the current manager hook manually and run `sh -n`.
4. Install/verify Entware and the necessary package inventory from the reviewed manifest. Check actual runtime binary versions as well as package metadata (they may differ).
5. Ensure independent firmware/WAN DNS is functional for initial NTP bootstrap before making the router depend on Pi-hole. DNS Guard watchdog scheduling must precede waiting for `/opt`.

**Gate 1:** correct mounts and writable filesystems, expected swap topology and ordering, functioning firmware management/LAN access, Entware package manager and independent DNS/NTP bootstrap. If missing, **STOP** before starting the full stack.

## Phase 2 — restore ASUS Edge CORE and manager-owned integrations

1. Examine the encrypted CORE archive off-router and execute `scripts/restore.sh BACKUP.tar.gz --dry-run` only against the reviewed decrypted archive. The script requires the archive, not the encrypted `.gpg` file.
2. Rehearse a restore using the **disposable** `EDGE_RESTORE_ROOT` target. The alternate root must pre-exist, be an absolute nonsymlink non-`/` directory, and be isolated from live firmware paths.
3. Review the manifest/allowlist and compare project-owned JFFS/opt state to the target. Only after formal recovery authorization consider production `--apply`; the default target without `EDGE_RESTORE_ROOT` is **live router paths**.
4. Reinstall/verify AMTM and Unbound Manager ownership. Project archives do not authorize blind overwrite of manager-managed startup hooks. The restore implementation excludes archived live `post-mount` even for old backup layouts.
5. Recreate the Unbound runtime directory ownership contract (reference `/opt/var/lib/unbound`: uid 65534, gid 0, mode 0755) on the **rebuild target**; validate the actual generated configuration with `unbound-checkconf`. Do not preserve world-writable historical modes as a security requirement.

**Gate 2:** core file-manifest integrity, project-owned scripts present, no unintended AMTM hook replacement, Unbound manager/runtime ownership and config validated. If inconsistent, roll back the candidate restore and review.

## Phase 3 — reinstall Pi-hole package and reconstruct state

1. Install the *reviewed* Entware Pi-hole/FTL build matching the private package manifest and verify its provenance/CPU architecture. Build the dedicated service account and group only with reviewed target-safe procedures: reference uid/gid **999:999**.
2. Keep FTL and any conflicting DNS listeners stopped while staging restore on the rebuild target. Inspect private archive member names, uid/gid/mode and internal checksums; do not blindly extract arbitrary paths as root.
3. Restore the reviewed Pi-hole configuration and Gravity DB/policy payload. Reference `/opt/etc/pihole` directory 999:999/0755; `pihole.toml` and `gravity.db` 999:999/0640; FTL binary 0:0/0755. Independently verify Gravity SQLite integrity **before** use and validate filtering after startup.
4. Restore reviewed Pi-hole helper/init integration, including `S64pihole-ip` and `S65pihole-FTL`, without replacing addon-managed `post-mount`. Verify executable permissions and shell syntax.
5. The TAR **does not retain** `security.capability`. Verify the restored FTL binary SHA-256 and apply the **exact seven-capability set from the private `manifest/ftl-capabilities.txt`** on the **rebuild target** with `setcap`; then verify `getcap`. This has been proven only on a disposable Fedora tmpfs copy, not on a fresh Entware rebuild.
6. Confirm that dedicated Pi-hole LAN alias `192.168.50.253` exists before FTL attempts port 53. Unbound must be ready on `127.0.0.1:53535`, with no collision between Pi-hole listener and firmware dnsmasq.
7. Do **not** restore the private query-history database or Tailscale authentication state from the project archive. Re-establish runtime sessions/collector credentials through separate authorized management paths if required.

**Gate 3:** matching package/binary provenance, Pi-hole identity and file modes, FTL capabilities, Gravity integrity, DNS alias/listener ownership, ordered start and no unexpected conflict. If not satisfied, do not make Pi-hole the router's only resolver.

## Phase 4 — DNS, security and service convergence

1. Keep or recover independent WAN bootstrap resolver availability. Validate NTP and Unbound before local DNS Guard promotion.
2. Confirm local Pi-hole forwarding through Unbound on both UDP and TCP, ordinary external lookups, a controlled known-blocked domain, DNSSEC positive and negative cases, main-LAN DHCP DNS policy, conditional reverse-DNS for an active lease, and the firmware dnsmasq interception/local naming path.
3. Inspect `dns-guard ready`, `status`, `metrics`, `/tmp/resolv.conf`, the exact once-per-minute `AsusEdgeDNSGuard` cron entry and the running `crond` process. Confirm break-glass semantics; do not force failover merely to satisfy a test.
4. Reconcile firewall rules and source allowlists; verify no unauthorized management service exposure. Restore Tailscale by **fresh authorized re-enrollment** if node state was intentionally excluded. Validate correct `netfilter-mode=off` and project firewall ownership.
5. Verify syslog-ng and optional Pi-hole read-only API/collector/Grafana telemetry **separately**. Their failure is not automatically evidence that baseline DNS is broken.
6. Run the complete project healthcheck and record exact errors/warnings rather than silently assuming a fixed boot time.

**Gate 4:** DNS functionality including blocking/DNSSEC/reverse-DNS, correct DHCP/router resolver policy, watchdog, security boundaries and project healthcheck all confirmed. No inferred PASS for paths not tested.

## Phase 5 — controlled boot persistence / rollback

The **2026-10-09 production reference router** passed one operator-confirmed reboot with Entware available: new uptime, all required DNS-stack services, exact FTL capabilities, DNS Guard local mode/watchdog and a project healthcheck of **0 failures / 0 warnings**. See [sanitized evidence](../evidence/2026-10-09/issue-129-pihole-dr-reboot-persistence.md).

**That is a persistence test on an already provisioned router, not proof of a replacement-router restore.** Once an isolated rebuild reaches Gate 4, test its own controlled reboot with physical access; record boot logs and confirm pre-Entware swap activation, independent DNS/NTP bootstrap and automatic return to Pi-hole. Early Jan 1 log times may precede NTP clock sync. Never issue automatic repeat restarts on failed health probes.

If a gate fails, **STOP** and preserve current evidence. Recover the independent bootstrap DNS/manual break-glass path **only under a reviewed local recovery plan**; do not assume break-glass repairs a failed WAN. Do not blindly import CFG, overwrite AMTM hooks, turn off filtering/network restrictions or reset the healthy production router. Prefer rollback to the last known-good snapshot or keep the replacement device isolated until corrected.

## Explicit limitations and next exercise

- Full blank-device/blank-Entware reconstruction including package identities, restored-target xattrs and all post-restore DNS/DHCP/API/collector validations: **NOT TESTED**.
- Boot without mountable Entware, concurrent local/bootstrap DNS loss and full-installer deployment: **NOT TESTED**, separately waived in the [DNS Guard v3.2 production review](dns-guard-v3.2-recovery-audit-live-validation.md).
- Native CFG import on a fresh compatible unit: **NOT TESTED**.
- Proposed next safe step: isolate a compatible test target, build from reviewed firmware/Entware manifests and exercise Gates 0–5 there before treating issue #129 as end-to-end complete.
