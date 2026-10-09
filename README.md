# Advanced ASUS Edge Gateway & Zero-Trust Lab

[![Validation suite](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/actions/workflows/shellcheck.yml/badge.svg?branch=main)](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/actions/workflows/shellcheck.yml)

A reproducible Home/SMB security-edge lab for the ASUS TUF-AX5400. The current reference deployment combines Asuswrt-Merlin, Entware, Tailscale, Pi-hole, Unbound, syslog-ng, off-router observability, and a least-privilege firewall policy.

This is an **enterprise-style lab**, not an enterprise-grade appliance. It has no high availability, redundant WAN, native VLAN microsegmentation, or vendor support.

**Current reference Tailscale runtime:** `1.103.375` on the unstable/dev track. Earlier dated evidence that records `1.102.3` is a historical pre-upgrade checkpoint, not the current live router state.

**Planned router migration target:** ASUS RT-BE88U on a compatible Asuswrt-Merlin 3006.x branch. OPNsense/x86 is not the current target architecture; it is retained only as a future contingency if requirements eventually exceed the ASUS platform.

**Current maintenance boundaries (reviewed 2026-10-09):** DNS Guard v3.2 was production-validated within the separate [2026-10-08 break-glass/power-cycle gate](docs/dns-guard-v3.2-recovery-audit-live-validation.md); the existing reference router then passed a [controlled 2026-10-09 Pi-hole-aware reboot](evidence/2026-10-09/issue-129-pihole-dr-reboot-persistence.md), **not** a clean-device restoration. Deployed self-built Unbound `1.26.1-1` is current; [PR #202](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/202) is an **open draft, workstation-only reproducibility/recovery candidate**, not an upgrade. [Issue #200](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/200) is **closed** after an operator-provided 698-entry permission audit, retained Pi-hole owner exception, zero group/world-writable entries, and merged [isolated regression PR #209](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/209) (8/8 CI). No live emergency rollback is claimed. The Pi-hole-aware **full Disaster Recovery [#129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129) remains OPEN**. See [current status](PROJECT-STATUS.md), [9 October worklog](docs/worklog/2026-10-09.md) and [#200 final evidence](evidence/2026-10-09/issue-200-final-permissions-acceptance.md).

## Recovery documentation

Start with the [Disaster Recovery navigation index](docs/disaster-recovery-index.md) for the **current** backup coverage, canonical English/Polish runbooks, dated test evidence and unresolved acceptance gates. On 2026-10-09 the project verified **65 exact-version Pi-hole/Entware IPKs** and performed a genuine **offline `opkg` installation in a disposable ARMv7 container** ([sanitized evidence](evidence/2026-10-09/issue-129-offline-pihole-opkg-cleanroom.md)). That result is **not** a blank-router restore or a production deployment; #129 remains open.

## Portfolio highlights

- Built a consumer-router security edge with Tailscale identity, project-owned default-deny firewall chains, and explicit router/LAN allowlists.
- Integrated dnsmasq with local Unbound on loopback:53535 and validated DNSSEC with the AD flag after controlled reboots.
- Migrated main-LAN DNS filtering from Diversion to an on-router Pi-hole/FTL listener while preserving Unbound, firmware DHCP/local naming, rollback evidence and reboot recovery.
- Built a privacy-bounded Pi-hole DNS analytics pipeline on Fedora using a crash-safe collector, Alloy, Loki and Grafana; live tests covered reboot recovery, two-client attribution and an evidence-backed Tailscale visibility gap.
- Added a project-native read-only Edge Gateway WebUI and an eight-resource, version-pinned Polish ASUS/GNUton localization overlay with exact-hash validation and reboot persistence.
- Added install, backup, restore, uninstall, health-check, evidence-collection, WAN-event recovery, and rollback workflows.
- Migrated the persistent Entware environment from USB flash storage to SSD, restored swap-backed service startup, and directly validated SSD mounts, swap activation, Tailscale, Unbound, and resolver configuration after the controlled reboot.
- Extended validation into latency-sensitive cloud workloads: compared GeForce NOW over Gigabit Ethernet and Wi-Fi 6, and analyzed an Xbox Cloud Gaming session with browser-native WebRTC RTP, jitter, ICE RTT, frame-delivery, bitrate, and decoder telemetry.
- Isolated a Wi-Fi 6 HE160 interoperability problem by comparing HE80/HE160 on a MediaTek MT7922, repeating the matrix across two Windows drivers, and using an independent Android 2x2 HE160 client to separate AP-wide capability from client/pair-specific behavior.
- Shipped RouterCloud on the dedicated LAN/Tailscale-only HTTPS service with custom login/session auth, production-tested password recovery, branded Polish Metro UI, AJAX sorting and live search, recent files and persistent favorites, safe rename/delete/edit workflows, WebDAV desktop integration, server-side ZIP downloads for checkbox-selected files/folders, and independent versioned encrypted backups while keeping generic `allow-delete: false`.
- Expanded the off-router Grafana catalog to **15 source-controlled rules** (five infrastructure; one sustained DNS Guard fail-open; five new PR #197 recovery checks; four RouterCloud). All configure the existing e-mail receiver. The five new DNS Guard UIDs were verified loaded, not individually firing/e-mail-tested.
- Performed a multi-vantage port-exposure audit across LAN, Tailscale, Fedora and a verified LTE/5G WAN path, including positive/negative identity tests and explicit invalidation of misleading results when routing did not match the intended trust boundary.
- Captured sanitized live evidence instead of presenting expected behavior as observed results.

## Architecture

The current reference architecture is documented as a source-controlled network-design set instead of one canonical raster image. Start with the [Network Design Documentation Index](docs/network-design.md).

Core architecture documents now include:

- [Architecture PDF — 2026-10-08](docs/architecture/ASUS-Edge-Gateway-Architecture-2026-10-08.pdf) — dated, print-friendly portfolio snapshot; detailed Markdown files remain authoritative.

- [Dated technical architecture overview — 2026-10-08](docs/architecture/ASUS-Edge-Gateway-Architecture-2026-10-08.md) — current snapshot; detailed architecture documents remain canonical.
- [Physical Topology](docs/architecture/physical-topology.md)
- [High-Level Architecture / Trust Boundaries](docs/architecture/high-level-trust-boundaries.md)
- [Addressing and Trust-Zone Plan](docs/architecture/addressing-and-zones.md)
- [DNS Enforcement Flow](docs/architecture/dns-enforcement-flow.md)
- [Tailscale Management + Exit-Node Flow](docs/architecture/tailscale-management-exit-node-flow.md)
- [Boot & Service Dependency Flow](docs/architecture/boot-service-dependency-flow.md)
- [Availability / Redundancy / SPOF](docs/architecture/availability-and-redundancy.md)
- [L2 and Network-Access Security Applicability](docs/architecture/l2-security-applicability.md)

The previous `docs/images/Architecture.png` is retained only as a historical/illustrative artifact and is no longer the source of truth.

Remote access is enforced through Tailscale policy plus project-owned local firewall controls:

1. Tailscale Grants authorize identities and groups.
2. Managed iptables chains restrict router services and selected LAN destinations/ports.
3. Exit-node forwarding is currently constrained by the managed Tailscale ingress chain and detected WAN egress, but the router-local exit-node rule is not yet source-scoped; issue #176 tracks the additional local source allowlist.

Current-firmware validation is tied to dated evidence rather than inferred from the diagrams. AUDIT-02 exit-node forwarding/NAT ownership was revalidated on GNUton 388.11 on 2026-09-23, and AUDIT-03 classic IPv4 UDP/TCP port-53 packet correlation was revalidated on the same reference firmware on 2026-09-27. DoH/HTTPS 443, DoQ/QUIC, VPN-carried DNS, application-specific encrypted DNS and IPv6 resolver paths remain outside any universal DNS-enforcement claim.

See the [network design index](docs/network-design.md), [architecture](docs/architecture.md), [swap and memory reliability](docs/swap-and-memory-reliability.md), [firewall policy](docs/firewall-policy.md), [security limitations](docs/security.md), and the [requirements and acceptance map](docs/requirements.md) for the detailed design, test methods and current validation limits.

The current RouterCloud browser/service state is recorded in the [2026-10-03 production checkpoint](docs/routercloud-production-checkpoint-2026-10-03.md), with bounded UI observations in the [same-day production validation](evidence/2026-10-03/routercloud-ui-production-validation.md) and the separate [password-recovery E2E validation](evidence/2026-10-03/routercloud-password-recovery-production-validation.md). The [2026-10-02 Metro checkpoint](docs/routercloud-metro-production-checkpoint-2026-10-02.md) remains as the historical baseline for the first Metro/WebDAV phase.

The 2026-10-07 RouterCloud increment introduced four Grafana rules for backup failure/staleness and maintenance failure/staleness. The live `routercloud_backup_bad` path was fault-tested through `Firing` and recovery while the real backup state was restored afterward. See [monitoring](monitoring/README.md), [RouterCloud versioned backup](docs/routercloud-versioned-backup.md), and the [sanitized alerting validation](evidence/2026-10-07/grafana-routercloud-alerting-live-validation.md).

**DNS Guard v3.2:** [PR #197](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/197) merged on 2026-10-08 after fresh CI 4/4 PASS. Bounded manual break-glass ON/OFF and a real power-cycle with Entware available passed; the watchdog was scheduled before Entware mounted and the router automatically returned from bootstrap WAN DNS to Pi-hole. Final healthcheck: 0 failures / 0 warnings. Cold boot **without** mountable Entware and deliberate simultaneous local/bootstrap DNS faults were not tested. See [v3.2 production validation](docs/dns-guard-v3.2-recovery-audit-live-validation.md).

## Key controls

- Project-owned Tailscale ingress chains are evaluated before competing parent rules and terminate in unconditional `DROP` for traffic arriving on `tailscale0` unless an explicit allow rule matches.
- Idempotent project-owned chains with duplicate jump removal.
- Device allowlist for router management and host/port allowlists for LAN access.
- Fail-closed IPv6 guards until an equivalent granular IPv6 policy is implemented.
- Classic DNS interception on TCP/UDP 53 through dnsmasq and Unbound.
- Pre-Entware swap activation in the validated live reference boot path, plus bounded `/opt` readiness and startup locking; no package upgrades during boot.
- Backup, dry-run restore, health checks, mock firewall tests, live tests, and CI.
- Sanitized evidence collection with explicit separation of automated and live results.
- Optional mutually authenticated TLS log forwarding with syslog-ng and reliable disk buffering.
- Automated collector retention that compresses completed logs after 24 hours and expires them after 30 days.
- Pi-hole DNS activity analytics Phase 0-3 are live-validated: bounded Fedora collection, local Alloy/Loki ingestion, Grafana dashboarding, controlled reboot persistence and two-client main-LAN distinguishability all passed within the documented Pi-hole-visible scope.
- Availability and classic enterprise L2/AAA controls are documented explicitly as implemented, planned, not applicable or not yet validated; recoverability is not presented as high availability.

## Repository layout

```text
config/             Example runtime configuration and Tailscale policy
router/scripts/     Asuswrt-Merlin firewall-start and services-start hooks
scripts/            Install, update, health-check, backup, restore, uninstall
monitoring/         Fedora observability and Pi-hole DNS analytics reference stack
tests/              Static, mock-firewall, and live-client tests
docs/               Architecture, security, operations, testing, and roadmap
evidence/           Sanitized dated validation artifacts, evidence policy and templates
```

## Requirements

- ASUS router supported by Asuswrt-Merlin; reference device: TUF-AX5400.
- JFFS custom scripts enabled.
- Entware mounted at `/opt`.
- Tailscale and Unbound installed; syslog-ng is optional unless remote logging is enabled.
- The current reference main-LAN design also uses Pi-hole/FTL through Entware on a dedicated LAN alias. Pi-hole is not installed by the repository's generic `install.sh`; use the validated migration/case-study procedure and treat its package/listener/startup state as a separate deployment dependency.
- A SHA-256 utility for verified backups; install Entware package `coreutils-sha256sum` when the firmware does not provide one.
- A working `flock` utility on the router PATH; `firewall-start` requires it to serialize concurrent policy rebuilds and fails closed if it is unavailable.
- A current router/JFFS backup and local recovery access for first deployment.
- Optional but recommended for modern workstation file transfers: Entware `openssh-sftp-server`. The reference GNUton/Dropbear build delegates the `sftp` subsystem to `/opt/libexec/sftp-server`; installing this package lets current OpenSSH `scp` clients use their default SFTP transport without forcing legacy SCP with `scp -O`.

Entware package names can differ by target. Confirm them before installation:

```sh
opkg update
opkg list | grep -E '^(tailscale|unbound|syslog-ng|coreutils-sha256sum|openssh-sftp-server) '
```

Never commit auth keys, node state, private keys, collector credentials, router exports, or real private infrastructure data.

### Reference compatibility

The original 2026-09-11 SSD/reboot baseline used an ASUS TUF-AX5400 running ASUSWRT-Merlin 3004.388.9_2-gnuton1. The reference router was upgraded on 2026-09-23 to GNUton 3004.388.11_1-gnuton1_tuf; the current reference Tailscale runtime was later upgraded on 2026-10-06 from 1.102.3 to the checksum-verified official ARM unstable build 1.103.375, with daemon restart and later cold-boot return validated; the [same-day worklog](docs/worklog/2026-09-23.md) records a subsequent reboot, clean project health and USB exposure audits, persisted admin firewall rules, Fedora DNS/verified HTTPS smoke tests, a role-specific negative management test from a distinct unauthorized tailnet client, and a post-firmware fixed-flow Exit Node packet correlation. The [management evidence](evidence/2026-09-23/unauthorized-tailnet-management-denial.md) confirms that tailnet membership alone did not grant TCP/8443 router-management access, while the [Exit Node revalidation](evidence/2026-09-23/audit-02-post-firmware-exit-node-revalidation.md) reconfirmed project-owned forwarding plus platform-owned WAN NAT on the current firmware. These results do not establish universal firmware compatibility or long-term stability. Component compatibility is defined by tested behaviour: Tailscale must preserve the configured socket/routing and intentional `netfilter-mode=off` ownership model; Unbound must validate the deployed configuration and expose the configured loopback listener; syslog-ng remains optional unless remote logging is configured. Record actual material package versions in dated evidence after upgrades. See [compatibility and revalidation](docs/compatibility.md). See also the [Tailscale 1.103.375 router runtime upgrade](evidence/2026-10-06/tailscale-1.103.375-router-upgrade-validation.md) for the current live-version checkpoint.


## Quick start

> **Reference-router stability observation:** the planned unchanged-state window was closed on **2026-09-22** after continuous 24/7 powered operation from **2026-09-11 through 2026-09-22**. This was not the originally planned full 14-day window through 2026-09-25, so the repository does not claim a completed 14-day endurance test. Subsequent router changes should still be performed as deliberate maintenance with backup, rollback and post-change validation. See [Stability observation](#stability-observation) and [Operations and recovery](docs/operations.md).

Prepare and validate the configuration on a Linux workstation working copy
with Python 3 available for the regression tests (not required on the router):

```sh
cp config/edge.conf.example config/edge.conf
vi config/edge.conf
chmod +x scripts/*.sh router/scripts/* tests/*.sh tests/mocks/*
sh tests/test-static.sh
```

Copy the repository to the router. Keep a LAN session open, then stage the integration without applying the firewall:

```sh
./scripts/install.sh
```

Authenticate the installed Tailscale instance once, using the socket configured in `config/edge.conf`:

```sh
tailscale --socket=/var/run/tailscale/tailscaled.sock up \
  --netfilter-mode=off \
  --accept-dns=false \
  --advertise-routes=192.168.50.0/24 \
  --advertise-exit-node
```

If exit-node mode is disabled in `config/edge.conf`, omit `--advertise-exit-node`. Approve only the required route or exit node in the Tailscale admin console and adapt `config/tailscale/policy.example.hujson` before publishing it.

ASUS Edge intentionally runs Tailscale with `netfilter-mode=off`. The project-owned
`EDGE_TS_*` chains enforce the router firewall policy instead of Tailscale-managed
`ts-input`, `ts-forward`, and `ts-postrouting` chains. Do not change this mode
without redesigning and revalidating the firewall policy.

Apply and validate from the LAN during a planned deployment or maintenance window:

```sh
./scripts/install.sh --apply
/jffs/addons/asus-edge/bin/healthcheck.sh
```

The installer backs up existing Merlin hooks but does not execute unreviewed legacy hooks by default. Set `EDGE_RUN_LEGACY_HOOKS="1"` only after confirming that the preserved scripts do not broaden access, upgrade packages during boot, or duplicate service startup. The installer does not install packages or update Tailscale.

## DNS integration

The current reference deployment uses split local DNS ownership. Pi-hole FTL owns TCP/UDP 53 on a dedicated LAN alias advertised to main-LAN DHCP clients. Firmware dnsmasq continues to own the router LAN/Tailscale port-53 sockets for DHCP/local-name duties and the generic project classic-DNS interception fallback. Both Pi-hole and dnsmasq forward ordinary external resolution to Unbound on `127.0.0.1:53535`. When Tailscale DNS interception is enabled, the active dnsmasq configuration must still include `interface=tailscale0`.

Issue #152 adds an opt-in exception for selected Tailscale IPv4 sources: their TCP/UDP 53 traffic can be DNATed to the dedicated Pi-hole listener before the generic Tailscale REDIRECT. The 2026-10-06 reference-client validation confirmed that selected path over LTE/5G with Tailscale enabled and the exit node disabled. Non-matching Tailscale clients continue through `dnsmasq -> Unbound`. The 2026-09-28 main-LAN DHCP Pi-hole result remains valid, while arbitrary hard-coded external classic-DNS on LAN still follows its separately documented interception path.

For a standard Entware deployment:

```sh
cp config/unbound.conf.example /opt/etc/unbound/unbound.conf
unbound-checkconf /opt/etc/unbound/unbound.conf
```

For amtm Unbound Manager, do not overwrite its generated runtime file. Validate the manager-owned configuration instead. The restart command below is a maintenance action and should be used only during a planned maintenance window:

```sh
grep -E '^(port: 53535|interface: 127\.0\.0\.1@53535)' /opt/var/lib/unbound/unbound.conf
unbound-checkconf /opt/var/lib/unbound/unbound.conf
/opt/etc/init.d/S61unbound restart
```

Merge `config/dnsmasq.conf.add.example` with any existing `/jffs/configs/dnsmasq.conf.add`; do not overwrite private DDNS or local records. Review `/jffs/scripts/dnsmasq.postconf` for NextDNS or other hooks that may take precedence. Do not run a second resolver on `192.168.50.1:53` while dnsmasq owns that socket.

## DNS filtering validation

A controlled 2026-09-22 Diversion comparison tested `Standard + snbAdSupport=yes`, `Standard + snbAdSupport=no`, and `Large + snbAdSupport=no`. Disabling the SNBForums support exception measurably improved blocking, and the Large profile broadened DNS coverage, but representative sites still rendered advertising even while many observed ad-tech hostnames returned `NXDOMAIN` from the Android Tailscale exit-node client.

Diversion `Large + snbAdSupport=no` was the accepted historical filtering baseline after issue #65 closed on 2026-09-27. On 2026-09-28 the reference main LAN was then migrated to Pi-hole running directly on the router through Entware. The staged pilot, OISD parity comparison, main-LAN DHCP cutover, reverse-DNS check, duplicate-service cleanup and final reboot validation all completed on the same controlled maintenance day.

Pi-hole now provides the reference main-LAN DNS-filtering path while Unbound remains the validating upstream and firmware dnsmasq remains responsible for DHCP/local naming plus the existing classic-DNS interception endpoint. The final case study explicitly records a swap-startup regression discovered during cleanup: Tailscale failed with a Go-runtime OOM until pre-Entware swap activation was restored and revalidated by another clean reboot.

DNS filtering remains useful but is not equivalent to request-level/browser content blocking, and neither stack is claimed to block all visual or in-application advertising.

See:
- [the sanitized Diversion validation](evidence/2026-09-22/diversion-ad-blocking-validation.md);
- [the Pi-hole case-study plan](docs/pi-hole-on-router-case-study-plan.md);
- [the final Pi-hole migration case study](docs/case-studies/pi-hole-on-router-case-study.md);
- [the 2026-09-28 sanitized Pi-hole pilot evidence](evidence/2026-09-28/pi-hole-single-client-pilot-validation.md);
- [the 2026-09-28 sanitized main-LAN cutover evidence](evidence/2026-09-28/pi-hole-main-lan-cutover-validation.md).

## Centralized logging

The optional logging design tails the firmware-owned `/tmp/syslog.log`, forwards it through Tailscale using mutually authenticated TLS, and can buffer messages on disk during collector outages. The checked-in examples require trusted peer certificates. Live mTLS delivery, buffer recovery, and post-reboot collector delivery should be described as observed only when the corresponding dated evidence exists; the presence of the example configuration alone is not operational proof.

See [centralized logging with mTLS](docs/centralized-logging.md) for the trust model, safe rollout order, negative certificate test, buffer recovery test, reboot validation, and evidence boundaries.

## DNS activity analytics

Issue #108 follows the adopted Pi-hole architecture rather than using broad
dnsmasq query logging as the primary source. The 2026-09-28 implementation is
live-validated through the Pi-hole-visible main-LAN path:

- authenticated Pi-hole v6 API access over a Fedora loopback SSH forward;
- bounded disk/memory collection with source-local cursors, deduplication and a
  crash-safe Fedora checkpoint/journal;
- local Alloy -> Loki ingestion with loopback-only listeners and no
  high-cardinality domain/client labels;
- the provisioned `Pi-hole — Aktywność DNS v2` Grafana dashboard;
- automatic recovery after a controlled Fedora reboot;
- two controlled main-LAN clients distinguished in the collected dataset.

A controlled Windows test confirmed the generic Tailscale fallback boundary:
classic DNS carried over Tailscale was visible on `tailscale0` but absent from
Pi-hole history when it followed `Tailscale -> dnsmasq -> Unbound`. Issue #152
now adds a separately validated selected-client path: source-scoped Tailscale
DNS DNAT reaches Pi-hole and preserves the client source identity for analytics.
Coverage therefore depends on the active policy path; the generic fallback is
not automatically Pi-hole-visible. The remaining #108 work is bounded
retention/storage observation, rollback/uninstall validation and correlation of
the hard-coded external classic-DNS LAN interception path. Encrypted-DNS
coverage remains a separate measurement track under issue #68. Raw household
query history remains private.

See [Network DNS Visibility / Client Activity Analytics](docs/network-dns-visibility-client-activity-analytics.md),
the [sanitized collector validation](evidence/2026-09-28/pi-hole-dns-collector-live-validation.md)
and the [Phase 2/3 + reboot/client validation](evidence/2026-09-28/pi-hole-dns-analytics-phase2-3-validation.md).

## Live validation status

The reference environment has multiple dated evidence sets. The **2026-09-11 SSD-migration/reboot artifact** directly validates the storage and core-service subset listed below; other firewall, printer, logging, health-check, and remote-client observations belong to their own dated evidence and must not be inferred from that single artifact.

Directly supported by `evidence/2026-09-11/entware-ssd-migration-validation.txt`:

- both SSD partitions mounted automatically after the controlled reboot;
- active 512 MiB and 2 GiB swap files;
- `tailscaled` running, with the Tailscale status command successful and the router offering exit-node capability;
- `unbound` running;
- direct Unbound resolution on `127.0.0.1:53535` returning `NOERROR` with the DNSSEC `AD` flag;
- dnsmasq configured with `no-resolv` and `server=127.0.0.1#53535`.

The artifact does **not** by itself prove syslog-ng recovery, end-to-end mTLS delivery, firewall/printer results, every exit-node traffic path, or long-term stability. See the sanitized [validated router-state snapshot](evidence/ROUTER-STATE-2026-09-11.md) for the exact claim boundary.

Other dated repository evidence documents additional validation performed in the reference environment, including remote-client DNS behavior and earlier router/firewall checks. Keep those observations attached to their original dates and artifacts rather than folding them into the 2026-09-11 SSD evidence.


On **2026-10-06**, issue #152's selected Android classic-DNS path was
live-validated with Wi-Fi disabled, LTE/5G active, Tailscale active and the ASUS
exit node disabled. A fresh query appeared in Pi-hole under the selected client
identity, internal RouterCloud naming resolved, a known advertising domain was
blocked by Pi-hole Gravity, RouterCloud remained reachable, and authorized ASUS
management reached the actual TCP/443 httpds listener through external
TCP/8443. The production healthcheck completed with zero failures and warnings.

The stricter Pi-hole filter was subsequently promoted from a temporary
Android-only group to the global `Default` policy alongside OISD Big and
AdGuard DNS Filter. The temporary strict group and explicit Android Pi-hole
client entries were removed. A global smoke test confirmed normal public DNS,
internal `home.arpa`, Gravity blocking and normal HTTPS connectivity.

Follow-up Fedora testing also found that Tailscale's `~.` DNS route caused
ordinary public DNS to follow `tailscale0` and miss Pi-hole analytics through
the generic fallback. Adding the administration workstation to the selected
source-scoped Pi-hole transport restored Pi-hole visibility while preserving
Tailscale DNS/MagicDNS; a fresh marker appeared under the workstation's
Tailscale identity and the healthcheck remained clean.

A representative Android compatibility check subsequently passed without
observed regression across banking/payment use, Google Play, routine
applications, notifications and internal-service access. A later 2026-10-06
cold-boot resilience test added DNS Guard v3.1 and live-validated Android LTE
with the ASUS selected as a Tailscale exit node: the router-side DNS query was
captured on loopback from the ASUS system resolver to the local Pi-hole alias,
and the answer returned successfully through the tested exit-node path.
Encrypted-DNS interception and long-term endurance remain outside this claim.
See the
[issue #152 policy](docs/android-pihole-tailscale-policy.md),
[sanitized issue #152 validation](evidence/2026-10-06/issue-152-android-pihole-tailscale-validation.md),
[DNS Guard validation](evidence/2026-10-06/dns-guard-v3.1-production-validation.md),
and the
[DNS bootstrap deadlock incident case study](docs/case-studies/dns-bootstrap-deadlock-dns-guard-v3.1.md).

On **2026-09-25**, a fresh read-only router checkpoint reconfirmed the reference deployment on GNUton `3004.388.11_1-gnuton1_tuf`: both SSD filesystems and swap were active, core services were running, direct Unbound resolution returned the DNSSEC `AD` flag, and the project health check completed with `0 failure(s), 0 warning(s)` and `HEALTHCHECK_RC=0`. Controlled Fedora tests also produced exact production counter deltas for LAN UDP/TCP 53 interception, direct TCP/853 rejection and Tailscale UDP/53 interception. A same-day Exit Node retest was deliberately not promoted into new datapath evidence because the first flow ran without an exit node selected and a later router capture attempt did not start; the 2026-09-23 fixed-flow capture remains authoritative for the current-firmware Exit Node claim. See the [sanitized checkpoint](evidence/2026-09-25/router-live-checkpoint.md) and [dated worklog](docs/worklog/2026-09-25.md).

On **2026-09-23**, after the firmware and admin-source changes, a distinct Windows tailnet client outside `EDGE_ADMIN_TS_SOURCES` retained Tailscale peer reachability but could not establish TCP/8443 to router management. A directional `tailscale0` capture and a temporary source-specific counter-only firewall rule correlated exactly five NEW TCP/8443 SYN packets / 260 bytes before the unchanged production deny tail. The temporary instrumentation was removed and the final production health check returned zero failures and warnings. See the [sanitized unauthorized-management validation](evidence/2026-09-23/unauthorized-tailnet-management-denial.md).

On 2026-09-22, a live exit-node validation established the reference deployment's NAT ownership model as **project-owned filtering + platform-owned WAN NAT**. On **2026-09-23**, after the upgrade to GNUton `3004.388.11_1-gnuton1_tuf`, the same boundary was revalidated with a controlled five-packet ICMP flow: fixed identifier `4244`, sequence numbers `1..5`, matching requests/replies on `tailscale0` before NAT and `ppp0` after source translation, 5/5 client replies, and zero kernel capture drops. The preflight and final health checks confirmed `ip_forward=1`, the project WAN-forward rule, platform `ppp0` `MASQUERADE`, and the established/related return path; the final health check reported zero failures and warnings. See the [2026-09-22 validation](evidence/2026-09-22/audit-02-exit-node-nat-validation.md) and [2026-09-23 post-firmware revalidation](evidence/2026-09-23/audit-02-post-firmware-exit-node-revalidation.md).

The 2026-09-08 LTE/5G validation observed behavior consistent with the intended remote DNS path:

`Android remote client -> Tailscale tunnel -> router dnsmasq -> Unbound on loopback:53535 -> recursive DNS` **(historical/current Tailscale interception path; Diversion was removed from the active stack on 2026-09-28)**

That historical result remains bounded to what was measured on that date. On **2026-09-22**, the previously unresolved Fedora/Android exit-node DNS datapath was re-tested with unique classic-DNS queries sent intentionally to an external resolver address. Read-only packet captures and `EDGE_TS_PREROUTING` counters validated UDP/53 and TCP/53 interception from Fedora, forwarding from dnsmasq to Unbound on `127.0.0.1:53535`, and equivalent controlled classic-DNS behavior from an Android client on LTE/5G with the ASUS selected as exit node.

The validated claim is intentionally limited to **classic DNS over UDP/TCP port 53**. It does not claim interception of DoH, DoT, QUIC-based encrypted DNS, or every application-specific resolver path.

See the [2026-09-22 AUDIT-03 DNS datapath validation](evidence/2026-09-22/audit-03-dns-datapath-validation.md), the [2026-09-08 live validation report](evidence/2026-09-08/live-validation.md), the [SSD migration procedure](docs/ENTWARE-SSD-MIGRATION.md), and the sanitized [2026-09-11 reboot validation evidence](evidence/2026-09-11/entware-ssd-migration-validation.txt).

## Stability observation

The unchanged-state observation was closed on **2026-09-22**. The reference router remained powered and in normal 24/7 operation from **2026-09-11 through 2026-09-22** without an intentional configuration-change cycle during that observation period. The originally planned end date was 2026-09-25, so this result must be described as the completed 2026-09-11 → 2026-09-22 continuous observation, **not** as a completed 14-day endurance test.

At the closing read-only check, the project health check reported `0 failure(s), 0 warning(s)` with `HEALTHCHECK_RC=0`; Entware/SSD storage, required swap, Tailscale, project firewall chains, Unbound/DNSSEC and syslog-ng were healthy, and the inspected syslog contained no matching OOM, crash, filesystem-I/O or read-only-filesystem errors.

Endpoint-filtering validation includes dated Zen evidence on Windows and a Fedora/GNOME proxy-integration case study. AdGuard for Windows remains an optional future comparison. These endpoint results remain separate from router-side capability claims.

## Validation and recovery

The commands below are operational examples. The unchanged-state observation is complete; install/uninstall/restore/firewall-apply actions and deliberate live-client policy tests should still be treated as planned maintenance with a current backup and rollback path.

Read-only router inspection during planned validation can include:

```sh
/jffs/addons/asus-edge/bin/healthcheck.sh
iptables -nvL EDGE_TS_INPUT
iptables -nvL EDGE_TS_FORWARD
iptables -t nat -nvL EDGE_TS_PREROUTING
```

The repository regression suite remains safe to run on a workstation working copy:

```sh
sh tests/test-static.sh
```

The live-client script actively probes management and LAN policy from an authorized remote client. Run it during a planned validation/maintenance window:

```sh
sh tests/test-live-client.sh 192.168.50.1 192.168.50.20
```

The second address is an optional LAN host on which SMB should be denied. See [testing](docs/testing.md) for the full security matrix and packet-capture procedure.

Collecting a new evidence snapshot executes the project's collector and should be treated as an explicit validation action:

```sh
/jffs/addons/asus-edge/bin/collect-evidence.sh
```

The collector excludes identity/configuration data and redacts firewall addresses, but its output still requires manual review before publication. This repository does not present expected behavior as observed live results. See [evidence collection](docs/evidence-collection.md) and the [validation evidence directory](evidence/README.md).

Backup and rollback commands for planned maintenance or recovery:

```sh
./scripts/backup.sh /opt/backups/asus-edge
./scripts/restore.sh /opt/backups/asus-edge/BACKUP.tar.gz --dry-run
./scripts/uninstall.sh
```

Tailscale updates are a separate planned-maintenance action. The updater
compares Entware package metadata with the actual live CLI/daemon version,
refuses implicit downgrades, preserves verified rollback binaries before a
package mutation, and runs managed service recovery plus the project health
check afterward. Tailscale automatic update application is deliberately
disabled so package changes cannot bypass this path:

```sh
./scripts/update-tailscale.sh
```

See [Tailscale maintenance and rollback](docs/tailscale-maintenance.md).

## Case studies

- [Case study index](docs/CASE-STUDIES.md) — curated portfolio index with explicit evidence, remediation, validation, and limitations.
- [Canonical case-study directory](docs/case-studies/) — all public case-study documents in one location.
- [Port exposure and trust-boundary audit](docs/case-studies/port-exposure-trust-boundary-audit-2026-10-07.md) — sanitized multi-vantage LAN/Tailscale/WAN exposure validation with explicit route verification and claim boundaries.

## Documentation

**Documentation languages:** canonical architecture, security, testing and evidence documentation is maintained in English. Polish-language operator guides are available through the [Polski indeks dokumentacji](docs/pl/README.md); see the [documentation language policy](docs/language-policy.md).

- [Polski przewodnik wdrożenia](docs/deployment-pl.md)
- [Architecture](docs/architecture.md)
- [Requirements and acceptance](docs/requirements.md)
- [Firewall policy](docs/firewall-policy.md)
- [Security model and limitations](docs/security.md)
- [Threat model](docs/threat-model.md)
- [Testing strategy](docs/testing.md)
- [Evidence collection](docs/evidence-collection.md)
- [Endpoint filtering validation](docs/endpoint-filtering-validation.md)
- [Validated router-state snapshot](evidence/ROUTER-STATE-2026-09-11.md)
- [Centralized logging with mTLS](docs/centralized-logging.md)
- [Entware SSD migration](docs/ENTWARE-SSD-MIGRATION.md)
- [Printer hardening](docs/PRINTER-HARDENING.md)
- [uiDivStats high-load case study](docs/case-studies/uidivstats-high-load-case-study.md)
- [Wi-Fi 6 HE160 interoperability case study](docs/case-studies/wifi6-he160-mt7922-interoperability-case-study.md)
- [Printer setup from LAN](docs/printer-setup-lan-pl.md)
- [Printer setup through Tailscale](docs/printer-setup-tailscale-pl.md)
- [Operations and recovery](docs/operations.md)
- [Optional ARMv7 BusyBox 1.36.1 — isolated deployment, rollback and recovery](docs/custom-busybox-armv7.md)
- [DNS bootstrap resilience](docs/case-studies/dns-bootstrap-deadlock-dns-guard-v3.1.md)
- [Roadmap](docs/roadmap.md)
- [Engineering worklog](docs/worklog/README.md)
- [Documentation model and source-of-truth rules](docs/documentation-model.md)
- [Compatibility and revalidation](docs/compatibility.md)

## Validation evidence

Sanitized evidence is stored under `evidence/YYYY-MM-DD/`. Each artifact should state what was actually observed and omit credentials, node state, real private addresses, or unrelated user data. Automated CI/mock output and live-router evidence are separate evidence classes; one must not be presented as proof of the other.

Automated shell, configuration, mock-firewall, recovery, and evidence-redaction tests run in GitHub Actions. Live network claims require separate dated evidence.

## Design principles

1. **Least privilege**: identities are filtered by Tailscale policy, then device IPs and destination ports are filtered again on the router.
2. **Fail closed**: invalid policy input aborts deployment; IPv6 is blocked until equivalent granular policy exists.
3. **Reproducible**: configuration templates, tests, rollback paths, and evidence procedures live with the code.
4. **Observable**: logs, counters, health checks, and sanitized evidence make policy behavior inspectable.
5. **Recoverable**: backups, dry-run restore, installer rollback, and LAN recovery procedures are documented and tested.
6. **Honest scope**: expected, automated, and live-validated behavior are kept separate, and platform limitations are explicit.

## License

See [LICENSE](LICENSE).
