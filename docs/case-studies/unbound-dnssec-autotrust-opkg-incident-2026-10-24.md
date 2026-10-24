# DRAFT — Unbound DNSSEC Trust-Anchor Permission Outage During a Package Upgrade

> **Status:** DRAFT / INCOMPLETE — prepared on 2026-10-24. **Not a completed 1.26.2 deployment case study.**
> **Environment:** ASUS TUF-AX5400, GNUton Asuswrt-Merlin, Entware ARMv7, Unbound + dnsmasq + Pi-hole.
> **Evidence:** operator-reported production terminal outputs; independently executed rootless Fedora/ARMv7 package laboratory reported by the operator; verified backup/package metadata. No production execution is implied by publication.
> **Current production:** Unbound **1.26.1-1**, five related Entware packages; local DNS and bounded DNSSEC checks PASS; **1.26.2 production upgrade HOLD**.

## Executive summary

A planned 1.26.1-to-1.26.2 Unbound package upgrade passed substantial pre-deployment checks but disrupted the validating resolver path. The installer and subsequent rollback were able to report transient start success even though the Unbound process exited shortly afterward. Restoring the five 1.26.1 packages was **insufficient** to restore the daemon.

A foreground run exposed the immediate fatal error:

~~~text
fatal error: could not open autotrust file for writing, /root.key.<temporary-suffix>: Permission denied
~~~

The service ran as an unprivileged user inside a chroot. The existing DNSSEC trust-anchor file was writable, but the *directory containing it* was owned by root and not writable by the service account. RFC 5011 automatic trust-anchor maintenance needs to create a temporary file alongside the anchor; configuration syntax validation does not check that runtime filesystem operation.

A bounded production repair moved the writable trust anchor into a dedicated, unprivileged-owned subdirectory under the chroot, without making the chroot root broadly writable or disabling DNSSEC. The original 1.26.1 package set then passed DNS and DNSSEC acceptance tests.

A subsequent isolated experiment using the **actual ASUS ARMv7 `opkg` executable** and all ten real 1.26.1/1.26.2 IPKs reproduced package-driven normalization of a pre-existing Unbound chroot directory from service-owned `0700` to root-owned `0755` on both upgrade and downgrade. The dedicated anchor subdirectory and its contents remained unchanged in that experiment.

**Evidence boundary:** the laboratory establishes that this particular `opkg`/IPK combination *can* reset the directory metadata. The October 23 production backup did not include the chroot directory entry, so its owner/mode immediately before the production upgrade are unknown. The laboratory does **not** prove that a production metadata transition took place on October 24.

## System context and deployment boundary

- Production Unbound uses an unprivileged runtime account (`nobody`, UID/GID 65534) and a chroot; the validating resolver listens on a loopback TCP/UDP port used by the router's DNS front ends.
- Firmware dnsmasq and Pi-hole expose distinct client-facing DNS paths. DNS Guard is a separate router-resolver recovery layer; its presence does not prove uninterrupted client DNS during this maintenance.
- The intended update comprised five coherent packages: `libunbound`, `unbound-daemon`, `unbound-anchor`, `unbound-checkconf`, `unbound-control`.
- The update was manually authorized within a maintenance window; this document does not authorize another deployment or claim unattended upgrade support.
- Separate RouterCloud, SSD security, JFFS, installer, disaster-recovery and Fedora workflows are **out of scope**.

## Observed incident timeline — 2026-10-24

| Phase | Operator-reported observation | What it actually proves |
| --- | --- | --- |
| Prior readiness | Fedora/QEMU tests, real IPK install/rollback lab, off-router backup, hash-checked staging and read-only router preflight | Prepared artifacts and bounded compatibility evidence; not post-upgrade router runtime |
| Production upgrade | Five packages showed `1.26.2-1`; Unbound process/listeners disappeared | Package version convergence did not imply service health |
| D1 / D2 | D1 declared the resolver running/awaiting DNSSEC; subsequent D2 DNSSEC check failed | A single immediate process check can miss early fatal exits |
| Production rollback | Five packages restored to `1.26.1-1`; Manager/start script restored and basic start appeared successful | Package restoration did not restore persistent Unbound operation |
| Focused diagnosis | `unbound-checkconf` passed; the foreground resolver exited on trust-anchor temporary-file creation with permission denied | Direct immediate failure mechanism |
| Focused recovery | Dedicated writable anchor directory, isolated anchor copy, one configuration directive changed, pre-change backup preserved | Narrow active production configuration repair, **not** a package upgrade |
| Independent acceptance | Direct resolver TCP DNSSEC: valid answer with AD; deliberately bogus DNSSEC: SERVFAIL; router and Pi-hole client DNS: UDP/TCP 4/4 PASS | Bounded resolver and client-path recovery on 1.26.1 |
| Runtime gate V1 | Stable process identity over 60 seconds, correct anchor metadata, expected package versions and listeners | Much stronger post-start confidence than one-shot start status |

The first attempted read-only acceptance after rollback reported zero Unbound processes and listeners despite `unbound-checkconf` success. A single start check had previously seen the process disappear within seconds. The corrected recovery reported process and socket presence at 3, 8, 18 and 38 seconds, followed by independent read-only testing.

## Direct trigger: RFC 5011 anchor write permissions

The failing configuration placed `auto-trust-anchor-file` directly in the chroot root. Before repair the observed relevant metadata were:

| Object | Owner | Mode |
| --- | --- | --- |
| Chroot directory root | `root:root` | `0755` |
| Existing active trust-anchor file | `nobody:nobody` | `0666` |
| Unbound daemon process | `nobody` | unprivileged |

Within the chroot, creating a temporary sibling of `root.key` requires directory write permission. File-level writability is not enough. The foreground error names a generated temporary file, not merely an unsuccessful overwrite of the existing anchor.

The remedy kept the chroot root `root:root 0755`, introduced a dedicated anchor directory owned by UID/GID 65534 with mode `0700`, copied the current anchor there with mode `0600`, and repointed `auto-trust-anchor-file` to that location. A private rollback backup was retained. No blanket `chmod 777` or DNSSEC disablement was used.

This is a **bounded production remedy**, not proof of permanent cold-boot persistence or proof that future package versions will never change the directory model.

## Root-cause investigation: backups and real IPK metadata

The off-router archive captured on October 23 passed its SHA-256 integrity check and recorded the pre-update active config pointing at `root.key` directly under the chroot, along with the active anchor file at `65534:65534 0666`. **The chroot directory itself was not represented in that archive.**

Inspection of the five original and five new IPKs showed that `unbound-daemon` in *both* versions explicitly ships the chroot directory as `UID=0 GID=0 MODE=0755`. Other inspected members of the five-package set did not declare that directory.

This is not a 1.26.2-only packaging difference. It is a conflict between the package's directory ownership model and the previous configuration's need for a writable *sibling temporary file* at the chroot root.

### Fedora-only `opkg` reproduction

The V2 isolated lab ran the genuine operator-provided ARMv7 `opkg` binary (hash checked) and ten hash-verified, actual IPKs in a rootless Podman container under emulation, without networking, production mounts or router contact.

| Isolated test | Initial synthetic chroot | After real `opkg` transaction | Result |
| --- | --- | --- | --- |
| Upgrade `1.26.1 → 1.26.2` | `65534:65534 0700` | `0:0 0755` | REPRODUCED |
| Downgrade `1.26.2 → 1.26.1` | `65534:65534 0700` (reset intentionally before test) | `0:0 0755` | REPRODUCED |
| Dedicated anchor directory | `65534:65534 0700` | unchanged after each transaction | PASS |
| Dedicated synthetic anchor file | `65534:65534 0600` | metadata and contents unchanged | PASS |

All three `opkg` transactions (initial installation, upgrade, downgrade) completed with RC=0 and the correct package version sets. Locally modified conffiles were preserved and generated package sidecars as expected; the package-managed init script still needed explicit restoration.

The V1 laboratory run **failed at synthetic test setup**, before an upgrade was attempted, due to missing rootless-container file-ownership capabilities. V2 added only container-scoped `CHOWN`, `FOWNER` and `DAC_OVERRIDE`. Reporting the V1 failure matters: it was a harness bug, not evidence of a failed `opkg` upgrade.

**Laboratory limitation:** nine dependency records were synthetic database stubs, not real ARMv7 runtime libraries. These trials establish package/file/metadata behavior, **not** runnable Unbound 1.26.2 or independent DNSSEC validation.

## Recovery validation and gate improvement

After the targeted repair, the independent production test reported:

- five packages `1.26.1-1` and active configuration syntax PASS;
- exactly one Unbound process, TCP and UDP loopback sockets present;
- direct Unbound TCP DNS `NOERROR`, positive DNSSEC AD and negative DNSSEC `SERVFAIL`;
- router DNS UDP/TCP and Pi-hole DNS UDP/TCP: **4/4 client paths PASS**;
- stronger read-only gate: directory `0700`/anchor file `0600` owned by the service UID, unchanged process identity over 60 seconds, seven bounded negative predicate self-tests PASS.

Remaining evidence gaps: the direct resolver DNSSEC *UDP query* was not executed in the 60-second runtime-gate run (socket presence only), cold reboot persistence not tested, long-duration soak not measured, and real-runtime 1.26.2 with complete libraries not accepted.

## Lessons and preventive gates

1. Treat `unbound-checkconf` as a syntax/configuration check, **not** a filesystem write-permission or post-start health gate.
2. Validate writable *directory* semantics for automatic DNSSEC anchor state, especially when using a chroot and privilege drop.
3. Account for `opkg` directory metadata normalization during **both upgrades and rollback**. Package restoration alone may not restore service operability.
4. Preserve and verify package-managed init-script customizations, conffile sidecars and actual active configuration separately.
5. Observe unchanged daemon identity and usable DNSSEC responses after the maintenance action; one successful start return is insufficient.
6. Keep package-metadata laboratories distinct from full ARM runtime and client-path acceptance.

## Open items before publication as a completed case study

- [ ] Execute full ARMv7 Unbound 1.26.2 runtime test with real dependencies in isolation, covering DNS TCP/UDP, positive/negative DNSSEC and permission-failure injection.
- [ ] Review/update the actual controlled D1/D2 maintenance and rollback gates to require stable post-start identity and DNSSEC queries; test before deployment.
- [ ] Obtain separate operator authorization and successfully update the **production** router to 1.26.2; record package state, active config, DNSSEC and client DNS validation.
- [ ] Separately evaluate reboot persistence and longer soak on the repaired configuration, with an agreed recovery path.
- [ ] Resolve/document the remaining pre-upgrade production directory-metadata uncertainty. Do not turn a plausible causal explanation into an observed fact.
- [ ] Reconcile the public example configuration and operational runbook with the new anchor-directory requirements (separate reviewed change; **not** silently included in this draft).
- [ ] Review public sanitization, citations, timeline accuracy and CI; merge only after operator review and accepted final deployment evidence.

## References

- [October 23 Unbound 1.26.2 release-readiness checkpoint](../operations/unbound-1.26.2-armv7-release-readiness-2026-10-23.md) — historical pre-upgrade state, not the current runtime claim.
- [Existing Unbound 1.26.1 security-remediation case study](unbound-cve-2026-81642-remediation-case-study.md) — separate completed security update; not retroactively changed by this incident.
- [NLnet Labs Unbound configuration reference](https://unbound.docs.nlnetlabs.nl/en/latest/manpages/unbound.conf.html) — automatic trust-anchor file behavior.
- [OpenWrt packages issue #3624](https://github.com/openwrt/packages/issues/3624) — historical analogous package-driven directory ownership change; **not** proof of the 2026 production timeline.

> **Publication gate:** DRAFT. Laboratory reproduction, production recovery and successful 1.26.2 production upgrade are **three distinct claims**. The latter remains **HOLD**.
