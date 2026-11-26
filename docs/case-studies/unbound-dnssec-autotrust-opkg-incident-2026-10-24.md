# Unbound DNSSEC Trust-Anchor Permission Outage and Controlled Recovery

> **Status:** incident + subsequent successful Unbound 1.26.2 R2 production redeployment documented on 2026-10-24; the publication [PR #297](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/297) **was merged on 2026-10-24**. Historical incident details below are preserved as observed.
> **Environment:** ASUS TUF-AX5400, GNUton Asuswrt-Merlin, Entware ARMv7, Unbound + dnsmasq + Pi-hole.
> **Evidence:** operator-reported production terminal outputs; independently executed rootless Fedora/ARMv7 package laboratory reported by the operator; verified backup/package metadata. No production execution is implied by publication.
> **Final operator-reported production state (later October 24):** five packages **1.26.2-1**, D1/D2 PASS and direct UDP/TCP positive/bogus DNSSEC PASS; **controlled** DNS Guard fault injection, cold power-loss reboot and long soak **not tested**; an **actual post-R2 reboot later passed bounded runtime/DNSSEC/client checks**, with an unresolved `0666` RFC 5011 anchor-file mode; later read-only incident forensics confirmed real spontaneous DNS Guard WAN fail-open at 10:25:02 and local promotion at 11:08:01 (router-system resolver only). Earlier 1.26.1 recovery/HOLD below is a **historical interim checkpoint**.

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

## Historical open items at the interim incident checkpoint

> **Historical checklist only, not the current open-work register:** this captures questions remaining at the *first* failed attempt. The later V6–V9 tests, R2 production upgrade and one actual ASUS functional reboot occurred afterwards. Full bare-metal recovery, controlled failover, pre-incident metadata uncertainty, RFC 5011 hardening #298 and manager/PID compatibility #299 remain separate. Later documentation reconciled the public example and DR guide; this does not imply any new configuration was deployed.

- [ ] Execute full ARMv7 Unbound 1.26.2 runtime test with real dependencies in isolation, covering DNS TCP/UDP, positive/negative DNSSEC and permission-failure injection.
- [ ] Review/update the actual controlled D1/D2 maintenance and rollback gates to require stable post-start identity and DNSSEC queries; test before deployment.
- [ ] Obtain separate operator authorization and successfully update the **production** router to 1.26.2; record package state, active config, DNSSEC and client DNS validation.
- [ ] Separately evaluate reboot persistence and longer soak on the repaired configuration, with an agreed recovery path.
- [ ] Resolve/document the remaining pre-upgrade production directory-metadata uncertainty. Do not turn a plausible causal explanation into an observed fact.
- [ ] Reconcile the public example configuration and operational runbook with the new anchor-directory requirements (separate reviewed change; **not** silently included in this draft).
- [ ] Review public sanitization, citations, timeline accuracy and CI; merge only after operator review and accepted final deployment evidence.

## Later same-day resolution — R2 production 1.26.2 deployment

The early HOLD shown throughout the incident investigation was correct **at the time**, but became outdated after new Fedora full-dependency validation and a separate authorized, controlled R2 maintenance window later on 2026-10-24. Preserve the evidence sequence rather than rewriting the initial failure as a success.

1. **Complete ARMv7 lab:** V6 ran actual Unbound 1.26.2 and the exact IPK libunbound with real staged dependencies under QEMU/rootless Podman; V7.1 validated valid `AD=1` versus bad RRSIG `SERVFAIL` over UDP/TCP; V8.1 iterated over local synthetic ROOT → TLD → CHILD and validated DS/DNSKEY; V9 kept the old RFC 5011 KSK `VALID` and a new KSK `ADDPEND` through a daemon restart in the same disposable container. Each lab reported PASS; none tested the real RFC 5011 30-day promotion, ASUS cold reboot or public DNSSEC end to end.
2. **Active-anchor correction preserved:** active production `auto-trust-anchor-file` was confirmed in the protected, service-owned `dnssec-auto` directory, not the legacy root-of-chroot key. The prior failed maintenance history and backup stayed intact. The revised R2 scripts use a separate private staging directory and guard the active anchor.
3. **Baseline and R2 staging:** current 1.26.1 direct TCP DNSSEC good/bogus and router/Pi-hole client baseline PASS. New 11/11 source/stage checks, original five-package version/Manager/socket preflight, active restricted anchor and disk margin PASS.
4. **Attended successful D1:** `OPKG_UPGRADE_RC=0`, exactly five packages `1.26.2-1`, custom `S61unbound` restored/verified, Unbound started and passed basic service checks. `D1_RESULT=PASS_1262_RUNNING_AWAIT_D2_DNSSEC`.
5. **Independent production D2:** real-router direct Unbound TCP valid DNSSEC `AD=1` and bogus `SERVFAIL` PASS, dnsmasq and Pi-hole clients PASS. Subsequent **direct UDP** `dig` on the ASUS itself gave `UNBOUND_1262_DIRECT_UDP_AD1=PASS` and `UNBOUND_1262_DIRECT_UDP_SERVFAIL=PASS`; no further production changes/restarts in the UDP check.

| Final gate | Status |
| --- | --- |
| Five production Unbound 1.26.2-1 packages | **PASS** |
| D1 controlled install, custom Manager and daemon start | **PASS** |
| D2 direct TCP DNSSEC + router and Pi-hole DNS | **PASS** |
| Additional direct UDP DNSSEC positive AD / negative SERVFAIL | **PASS** |
| Real DNS Guard failover during deliberate outage | **NOT TESTED** — no intentional fault injection |
| Real DNS Guard fail-open and local return in earlier unplanned production incident | **OBSERVED AFTER THE FACT** in router syslog and time-series; client continuity not proven |
| ASUS reboot after R2 / functional persistence | **PASS after one observed actual reboot**, direct DNSSEC UDP/TCP and dnsmasq/Pi-hole client DNS |
| RFC 5011 anchor-file DAC after reboot | **CHECK:** owner/parent directory correct, file mode `0666` versus intended `0600` |
| Cold power-loss reboot / extended soak | **NOT TESTED** |
| Historical pre-incident chroot directory owner/mode | **UNKNOWN** |
| RFC 5011 real 30-day KSK acceptance | **NOT TESTED** |

**Conclusion:** close the authorized Unbound **package-update and bounded DNSSEC/client-path acceptance** task as a successful production R2 deployment. The earlier incident, recovery and initial rollback remain historically true; preserving them matters. PR #297 was subsequently reviewed and merged; publication state is separate from the operational evidence. Do not turn the remaining independent DNS Guard/reboot items into retroactive production validation.

For the complete sanitized production timeline and raw pass markers, see [the October 24 R2 deployment acceptance](../operations/unbound-1.26.2-production-deployment-2026-10-24.md).

## Monitoring and alert-delivery aftermath — later October 24 forensic addendum

A separate read-only review of the production ASUS syslog archive, Fedora VictoriaMetrics/Blackbox series, Grafana journal, SQLite rule configuration and received alert e-mails established that DNS Guard **did** select independent WAN/bootstrap DNS at **10:25:02** and later promoted back to local Pi-hole at **11:08:01** during the **unplanned** initial Unbound outage. These observations were discovered **after** the original D1/D2 deployment acceptance. The earlier phrase `DNS Guard live failover not tested` referred specifically to the absence of a **controlled fault-injection acceptance test**; it should not erase the newly established historical transitions.

A source-controlled router-DNS Blackbox probe returned **83 failures / 121 samples** in the 10:20–11:20 interval, while separate HTTPS and ICMP probes reported **121/121 PASS** each. The monitoring host experienced **14** Grafana notifier errors classified with DNS lookup/timeout/retry signals; the DNS Guard FIRING e-mail was received only at **11:07:03** and RESOLVED at **11:12:02**. The precise historical Fedora DNS upstream, transport-specific channel attribution and history of the separate router-DNS-probe alert remain **unproven**. No Fedora DNS or alert configuration was changed.

See the distinct [DNS Guard and delayed Grafana alert delivery case study](dns-guard-grafana-alert-delivery-dns-failure-2026-10-24.md) for the full chronology, sanitized evidence and proposed independent monitoring DNS follow-up. That analysis does **not** change the R2 Unbound 1.26.2-1 PASS verdict or claim client-DNS continuity.

## Afterward: successful reboot and real ARMv7 file-mode reproducer

After the successful R2 upgrade, the operator completed **one actual router reboot**, followed by read-only verification: installed Unbound 1.26.2 packages **5/5 PASS**, Unbound/Pi-hole processes and sockets PASS, direct DNSSEC valid AD and invalid SERVFAIL over **UDP and TCP PASS**, router dnsmasq and Pi-hole DNS PASS, and DNS Guard back on its local DNS path with watchdog registered. This establishes bounded **functional restart persistence**, not an uninterrupted start, full power-loss cold boot or long soak.

The only reported file-mode exception was the active RFC 5011 auto-trust-anchor file: owner `65534:65534` and private parent directory `0700` remained correct, but `root.key` itself was **0666**, not the previously provisioned `0600`; its `mtime` and `ctime` changed around 52 seconds after router start. The protected directory limits ordinary users' access to that file. The actual production daemon's effective `umask` at the write event was **not measured**.

Source inspection of Unbound release-1.26.2 identified `autr_write_file()` as using `fopen(tempf, "w")` and atomic `rename()`, without preserving the original file mode. On Fedora, a synthetic V1 writer reproduced replacement modes `umask 000 → 0666`, `022 → 0644`, `077 → 0600` (**3/3 PASS**). V2 went beyond the model: **real Unbound 1.26.2 ARMv7** with verified IPK libunbound and real staged dependencies executed RFC 5011 writes in rootless QEMU/Podman. Both `000` and `077` variants passed inode replacement, KSK `VALID/ADDPEND` and daemon-process restart retention; their actual post-write and post-restart modes were **0666** and **0600**, respectively. Newly created launcher log-file modes changed with the mask too. Therefore `umask 077` is an **isolated-lab candidate**, not an authorized production patch. The existing ASUS service-manager launch chain, other file permissions and full compatibility remain to be reviewed. No router chmod, edit or restart was performed in the hardening investigation.

The [R2 operations report](../operations/unbound-1.26.2-production-deployment-2026-10-24.md) contains the exact post-reboot and V1/V2 observations with explicit PASS/HOLD boundaries.

### Scoped V3 Fedora-only follow-up (no production change)

An additional operator-run V3 test scoped `umask 077` to the **actual Unbound 1.26.2 ARMv7 child process** while retaining parent launcher `umask 022` in two starts of the hash-pinned V9 Podman/QEMU fixture. V9 self-tests **26/26 PASS**; the real daemon retained RFC 5011 `ADDPEND` across process restart, and its rewritten anchor was **0600** before/after the restart. The parent-created laboratory logs and PID file were **0644**, independently readable by UID 65534, with no observed parent-mask leakage: `V3_RESULT=PASS_SCOPED_CHILD_077_PARENT_022_ACTUAL_ARMV7`.

This confirms scoped masking in the **isolated laboratory**, not the real Entware process manager: the V3 PID file was shell-created. Source-controlled `router/scripts/services-start` also offers a direct recovery launch outside `S61unbound`. Therefore `PRODUCTION_MANAGER_VERIFIED=NO` and `DEPLOYMENT_GATE=HOLD` remain. The complete bounded evidence appears in [R2 operations report section 7](../operations/unbound-1.26.2-production-deployment-2026-10-24.md#7-scoped-umask-real-armv7-v3-launcher-and-permission-regression).

## References

- [October 23 Unbound 1.26.2 release-readiness checkpoint](../operations/unbound-1.26.2-armv7-release-readiness-2026-10-23.md) — historical pre-upgrade state, not the current runtime claim.
- [Existing Unbound 1.26.1 security-remediation case study](unbound-cve-2026-81642-remediation-case-study.md) — separate completed security update; not retroactively changed by this incident.
- [NLnet Labs Unbound configuration reference](https://unbound.docs.nlnetlabs.nl/en/latest/manpages/unbound.conf.html) — automatic trust-anchor file behavior.
- [OpenWrt packages issue #3624](https://github.com/openwrt/packages/issues/3624) — historical analogous package-driven directory ownership change; **not** proof of the 2026 production timeline.

> **Publication update:** [PR #297](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/297) **was merged on 2026-10-24**; this editorial status change is not a new production acceptance. The initial incident, 1.26.1 recovery, isolated laboratory, and later successful R2 production 1.26.2 deployment are **different dated claims**. **Controlled** DNS Guard fault injection, cold power-loss reboot and long-soak tests remain untested; one actual post-R2 reboot passed functional DNSSEC/client checks, but RFC 5011 file-mode hardening remains open. Real unplanned DNS Guard fail-open/failback was separately observed.
