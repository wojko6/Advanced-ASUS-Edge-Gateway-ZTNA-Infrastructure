# Unbound 1.26.2 ARMv7 — release-readiness checkpoint (2026-10-23)

> **Scope:** evidence-backed, operator-reported Fedora 44 / rootless Podman / QEMU tests and bounded **read-only** ASUS checks. **Not a deployment or go-live approval.** Production continues on Unbound **1.26.1-1** (five Entware packages); target is **1.26.2-1**. `DEPLOYMENT_GATE=HOLD`.
>
> This documentation is a new workstream separate from [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235), installer Issue #278 and Draft [PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245). No ASUS package installation, service restart, configuration change, or router staging occurred as part of the 1.26.2 work on this date.

## Source and package provenance

- Existing [Draft PR #202](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/202) supplies the **1.26.1** Entware ARMv7 recoverable build recipe; it remains a draft. The 1.26.2 candidate was built separately on Fedora from a locally modified, pinned copy. **It has not been merged or deployed.**
- Target Entware `armv7-3.2`, ARM EABI5 **soft-float**, glibc 2.27, Entware `/opt` layout. The source archive was hash-checked prior to the local build.
- Seven `1.26.2-1` packages built and metadata/hash-checked. Exactly **five** match the already-installed production package set: `libunbound`, `unbound-daemon`, `unbound-anchor`, `unbound-checkconf`, `unbound-control`. `unbound-host` and `unbound-control-setup` are **not** part of the intended upgrade.
- Five original `1.26.1-1` rollback IPKs were recovered and checked against their historical checksum manifest. A final Fedora-only release staging check verified the **5+5** intended IPKs and the protected Manager start script: `RELEASE_STAGING=PASS_FEDORA_ONLY`. Router staging was **not performed**.

## Runtime and protocol validation (Fedora laboratory)

| Gate | Observed result | What it does **not** establish |
| --- | --- | --- |
| IPK hashes, package metadata, ABI | PASS | Router-runtime acceptance |
| QEMU ARMv7 `unbound -V` | `Version 1.26.2` / PASS | Running resolver functionality |
| QEMU `unbound-checkconf` | Valid configuration accepted, deliberately invalid option rejected / 2 of 2 PASS | Compatibility with the complete live Manager configuration |
| QEMU local authoritative test zone | UDP/TCP `NOERROR` and `NXDOMAIN` / 4 of 4 PASS | Internet recursion or DNSSEC |
| QEMU direct iterative recursion | **NOT PROVEN**: positive name returned `SERVFAIL`; root-server probes received `REFUSED` with `ra` rather than expected authoritative responses; Unbound logged `THROWAWAY` and root priming failure | No evidence this is an Unbound 1.26.2 defect; network interception is a plausible cause |
| IANA laboratory root trust anchor | Signed root-anchor update verified; KSK `38696` present | Independent DNSSEC acceptance |
| QEMU forwarded DNSSEC via existing ASUS Unbound 1.26.1 over TCP SSH forwarding | Positive `NOERROR + AD` over UDP/TCP at the QEMU listener; negative `SERVFAIL` over UDP/TCP / 4 of 4 PASS | Independent cryptographic validation by 1.26.2: upstream 1.26.1 was also validating |

**Trust-anchor caveat:** the legacy `/opt/etc/unbound/root.key` packaged by Entware is old and not registered as an `opkg` conffile. The currently active `/opt/var/lib/unbound/root.key` was observed separately with KSK `38696`. Never replace the active key with the legacy packaged file as part of maintenance.

## Real package-manager transaction tests — isolated, not on the router

The exact production `opkg` ARM EABI5 soft-float **statically linked** binary was read-only copied to Fedora and compared byte-for-byte using SHA-256. A local permissions issue (`0600` rather than executable `0700`) was fixed on the **Fedora copy only** before successful QEMU execution.

- Rootless Podman, QEMU and an isolated container with **no network, no host bind mounts and no router access** exercised synthetic upgrade/downgrade `opkg` transactions.
- The subsequent **real-IPK** laboratory test installed all five `1.26.1-1` IPKs, upgraded all five to `1.26.2-1`, then downgraded all five to `1.26.1-1` (`opkg` return code 0 at each transaction; package statuses confirmed).
- This lab supplied **nine synthetic dependency entries** in the package database, with empty `.list` files; **actual dependency libraries were not installed**, and no Unbound daemon was executed inside that `opkg` transaction container. This proves package file/db behavior only, not runtime interoperability.
- Both upgrade and downgrade **overwrite** `/opt/etc/init.d/S61unbound` because it is package-owned and **not** registered as a conffile. The laboratory restore marker was successfully restored **after both operations**.
- Locally modified `/opt/etc/unbound/unbound.conf` **was preserved**; the new package payload was put in `unbound.conf-opkg`. The `resolve_conffiles` notice occurred in `Collected errors` while the specific expected transaction returned code 0; this notice alone is not a fatal install failure.
- The separate package-owned legacy `/opt/etc/unbound/root.key` is **not** a conffile and may be overwritten. Runtime Manager files in `/opt/var/lib/unbound/` were absent from the new IPK payload and preserved in the isolated file transaction test.
- An additional snapshot-based restoration rehearsal reproduced start-script replacement and restored **7 of 7 protected files** to byte-identical contents. It did **not** operate the live router or validate a live failure rollback.

## ASUS read-only production checks (2026-10-23)

- Five installed IPKs remain `1.26.1-1`; the active resolver process uses `/opt/var/lib/unbound/unbound.conf` and listens on loopback TCP/UDP port `53535`.
- The protected `S61unbound` SHA-256 matches the local off-router snapshot, as do the selected configuration/key baselines. Active configuration `unbound-checkconf` PASS; active root key contains KSK `38696`.
- **Restoration metadata gate:** the Fedora-only release staging intentionally holds files at mode `0600` and its directory at `0700`; this staging copy is **not** directly deployable as an init script. The actual ASUS Manager `S61unbound` baseline was executable (`0755`, observed owner `admin1`, group `root`). A separately approved router restore must re-establish and check the correct **file bytes, executable mode, owner/group and path** before invoking any start action. Do not infer mode preservation from a standalone checksum or blindly copy a `0600` staged script onto the live init path.
- Off-router archived configuration: **five required plus two optional files**, archive hash and five required per-file hashes PASS. The original rollback packages remain intact. No extra router backup is needed on the basis of this checkpoint.
- `S61unbound` sources `/opt/etc/init.d/rc.func`. Its `ARGS` point to the active Manager config, `POSTCMD="service restart_dnsmasq"` executes on the start path, and the `stop` action uses `killall unbound` with a wait. An explicit `kill` action uses `killall -9`; a normal restart does **not** automatically escalate to SIGKILL. The `restart` dispatch does not provide transactional stop/start semantics.
- Observed client-facing DNS listeners: dnsmasq and Pi-hole on port 53; Unbound on `127.0.0.1:53535`. Read-only positive DNS checks returned `NOERROR` for the Unbound TCP tunnel, dnsmasq and Pi-hole; only the Unbound tunnel demonstrated `AD`.
- DNS Guard: `crond` running; **one matching scheduled entry**; services and listener present. No corresponding entries were found in the checked syslog. **Last watchdog execution is unverified, failover was not exercised, and DNS continuity while Unbound is stopped is not proven.**
- Existing active Manager configuration and active trust-anchor files were observed with permissive mode `0666`. This warrants **separate** lifecycle/permissions review; do not alter ownership/modes as part of this version upgrade without its own tests.

## Deferred maintenance sequence and abort boundaries

**Not an executable runbook; no approval to apply it.** A separate maintenance-window authorization is required, acknowledging possible client DNS interruption.

1. Re-check router/package state, off-router verified rollback material, DNS health, available storage and SSH access. Keep the watchdog and affected services under observation without changing DNS Guard controls as an undocumented workaround.
2. Transfer only the separately hash-verified install/rollback set to a private router staging location **after separate authorization**. The current staging exists **only on Fedora**.
3. Establish an operator-controlled pause/stop of Unbound, verify that the old process is fully gone **before** manipulating the installed packages, and preserve an independently reachable administration path. Do **not** use a blind `S61unbound restart`.
4. Install only the five intended `1.26.2-1` IPKs as one reviewed maintenance operation; check exit codes and installed status. Restore and verify the original Manager `S61unbound` **before** starting the service; re-check active config/trust anchor. Expect a dnsmasq restart via `POSTCMD` when the start action actually runs.
5. Validate new Unbound process/version, active configuration, TCP/UDP DNS and signed-good/bogus DNSSEC, client paths through dnsmasq/Pi-hole, DNS Guard state and service logs.
6. If any acceptance check fails, halt rather than repeatedly restarting DNS. Use the separately verified five `1.26.1-1` IPKs, restore the Manager script and protected configuration, revalidate the live resolver and client DNS, and record the incident. A lab rollback is **not** a guarantee of router recovery.

### State at the close of 2026-10-23

```text
UNBOUND_PRODUCTION=1.26.1-1
UNBOUND_TARGET=1.26.2-1
FEDORA_STAGING=PASS
IPK_OPKG_LAB=PASS_FILE_TRANSACTIONS_ONLY
QEMU_LOCAL_DNS=PASS
QEMU_FORWARDED_DNSSEC=PASS_VIA_1261_UPSTREAM
DIRECT_ITERATIVE_RECURSION=NOT_PROVEN
DNS_GUARD_MAINTENANCE_CONTINUITY=NOT_PROVEN
ROUTER_STAGING=NOT_PERFORMED
PRODUCTION_INSTALLATION=NOT_PERFORMED
DEPLOYMENT_GATE=HOLD
```

**Next checkpoint:** 2026-10-24, **not** a scheduled automatic action. Perform a brief fresh read-only health check, explicitly approve (or reject) router staging, approve a maintenance window with potential DNS interruption, and only then consider controlled upgrade/rollback execution. Preserve Draft PR #202 as a separate build-reproducibility workstream; do not merge this document into code or unrelated security work.
