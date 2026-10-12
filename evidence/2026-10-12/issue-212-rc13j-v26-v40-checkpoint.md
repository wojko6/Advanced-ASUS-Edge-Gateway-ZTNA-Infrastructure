# Issue #212 — RC13J client DNS continuity checkpoint (2026-10-12)

**Status: OFF-ROUTER LABORATORY / NOT DEPLOYED / ISSUE OPEN.**
This is a sanitized, operator-reported checkpoint. It does not represent a firmware-validated production pilot, and no experimental standby listener, client-failover DNAT, firewall patch, DNS service, or DHCP change was installed on the ASUS.

## Existing production topology — already documented

Do **not** rediscover or redesign this established baseline without a new reason:

- Main-LAN DHCP advertises only Pi-hole FTL at the router's dedicated `192.168.50.253:53` alias; Pi-hole is the filtering endpoint.
- Firmware dnsmasq owns `192.168.50.1:53`, loopback port 53, and router Tailscale port 53 for existing DHCP/local-name and DNS interception paths.
- **Both Pi-hole and firmware dnsmasq forward ordinary external queries to the same Unbound at `127.0.0.1:53535`.** An existing dnsmasq bypass can serve as continuity when Pi-hole alone fails **while Unbound is healthy**, but is **not independent failover when Unbound fails**.
- DNS Guard v3.2 is an independently accepted **router-system-resolver** bootstrap/steady-state mechanism, **not** the unfinished LAN/Tailscale client failover of issue #212.

See `docs/architecture/dns-enforcement-flow.md`, `docs/architecture.md`, `config/dnsmasq.conf.add.example`, and issue #212. This dependency was documented before 2026-10-12; v0.37–v0.40 were read-only confirmations, not new architecture discoveries.

## Operator-reported off-router laboratory results

| Checkpoint | Scope and evidence | Outcome |
| --- | --- | --- |
| RC13C / RC13J v0.26 | Synthetic signed DNSSEC good/forged behavior on original ARMv7 dnsmasq under QEMU, combined with Fedora private kernel NAT/INPUT/filter reload, witness revocation and re-attestation | **PASS** within synthetic/private lab; no public DNSSEC root-to-leaf, no actual ASUS kernel |
| v0.27–v0.28 | Read-only ASUS: Linux 4.1.52, iptables/ip6tables 1.4.15, loaded conntrack/DNAT/REDIRECT, source-managed LAN/Tailscale NAT order; INPUT has 17 rules, Tailscale at #1, LAN NEW accept at #9, loopback NEW accept at #10. IPv6 service/stack disabled at observation | **AUDIT PASS**; no router packet test |
| v0.29 | Four private Fedora hook-order permutations with real UDP/TCP packet ACL, NAT parent ordering, intentional unguarded exposure and restored filter priority | **FINAL PASS** (corrected textual marker `UNGARDED`) |
| v0.30 | Full observed INPUT match predicates and Tailscale chain pattern modeled; synthetic selected/unselected UDP/TCP DNAT emergency and rollback | **FINAL PASS**; ancillary ASUS jump-chain bodies and native firmware runtime not validated |
| v0.31 | Guard-only, disabled-only `firewall-start` candidate built from pinned original; mock idempotence, stale emergency ignored, no standby DNAT, source and patch remain review-only | **MOCK PASS**; candidate not installed and not production-eligible |
| v0.32 | Same candidate adapted *temporarily* to Fedora isolated netfilter; actual UDP/TCP client checks, direct `:55353` deny, idempotence, no emergency DNAT | **PRIVATE KERNEL PASS** |
| v0.33 | Coordinated listener gate: listener starts only after guard verification, is quiesced before planned INPUT reset, refuses startup after guard drift/install failure and requires fresh verification | **PRIVATE KERNEL PASS**; independent firmware INPUT reset still unsafe |
| v0.34 | Adversarial uncoordinated INPUT reset with `0.0.0.0:55353` wildcard listener: LAN reaches exposed listener on both UDP/TCP before watchdog stop | **EXPOSURE REPRODUCED; SAFETY GATE FAIL BY DESIGN**. Correct adversarial test result, unresolved blocker for wildcard model |
| v0.35 | First loopback-only trial timed out due to guard blocking even `lo` probes | **FAILED TEST**; not a passing isolation claim |
| v0.35b | Corrected loopback-only test separates blocked local guard probe from post-reset available local resolver; external LAN/Tailscale/WAN direct access remains blocked across private tested resets | **PRIVATE KERNEL PASS**; original guard still blocks local loopback DNS |
| v0.36 | Scoped INPUT allow exceptions for `lo` destination `127.0.0.1:55353`, UDP/TCP, before port drop; repeated installs, missing exception repair, fully emptied INPUT policy ACCEPT and 17-rule rebuild | **FINAL PASS**. Loopback local access and external direct denial in tested private netfilter; **functional client DNS failover NOT IMPLEMENTED** |
| v0.37–v0.40 | Read-only ASUS verification: separate pihole-FTL `192.168.50.253:53`, dnsmasq `:53`, Unbound on loopback TCP/UDP port `53535`; `route_localnet=0` on examined interfaces, IPv6 disabled, no `:55353` listener; no TPROXY loaded in examined table | **READ-ONLY AUDIT PASS**; confirms prior documented architecture |

Acceptance excerpts provided by operator: `RC13J_V26_EXTERNAL_ACCEPTANCE=PASS`, `RC13J_V29_CORRECTED_ACCEPTANCE=PASS`, `RC13J_V30_EXTERNAL_ACCEPTANCE=PASS`, `RC13J_V31_EXTERNAL_ACCEPTANCE=PASS`, `RC13J_V32_EXTERNAL_ACCEPTANCE=PASS`, `RC13J_V33_EXTERNAL_ACCEPTANCE=PASS`, `RC13J_V34_EXTERNAL_ACCEPTANCE=PASS`, `RC13J_V35B_EXTERNAL_ACCEPTANCE=PASS`, `RC13J_V36_EXTERNAL_ACCEPTANCE=PASS`. These attest to the defined laboratory test scenarios; `RC13J_V34_EXPOSURE_SAFETY_GATE=FAIL_BY_DESIGN` must **not** be relabeled as a safety PASS.

## Engineering decision and mandatory gates

1. **Reject wildcard standby `0.0.0.0:55353` for production**, because independent INPUT reset caused immediate UDP/TCP LAN exposure. A periodic watcher does not provide zero-exposure guarantees.
2. **Retain loopback-only, scoped-access model as an off-router isolation proof**, not a fully working client-failover design. The original DNAT-to-`:55353` approach cannot simply forward LAN/Tailscale clients to `127.0.0.1:55353` with the currently disabled `route_localnet`. Do **not** enable route_localnet or modify firmware dnsmasq to make a test green.
3. **Independent external DNS resolution is essential for the Unbound-failure case.** Reusing the existing firmware dnsmasq with its current Unbound upstream cannot meet it. Pi-hole Gravity filtering will be bypassed in a deliberately approved emergency policy; warn and audit which clients are allowed.
4. Next off-router design gate: compare **concrete transport candidates** from selected LAN/Tailscale `/32` DNS queries to an independent isolated resolver without a publicly reachable standby socket or global DNS policy change; prove actual UDP **and** TCP response routing, original-destination/source ACL, local-name and private PTR nonleak, DNSSEC validation, failure/rollback, forged/unauthorized access and *uncoordinated* filter reset.
5. Follow with firmware-matched ARMv7/kernel 4.1.52 behavior, startup/service restart and process supervision, stale conntrack handling, bounded memory tests, failure injection and an explicit **separately authorized single-client pilot**. IPv6 currently disabled; re-enabling it requires a new separate gate.
6. Keep a single managed `firewall-start` and existing `flock` semantics. Preserve existing Pi-hole, DNS Guard v3.2, Unbound, Tailscale, NAT and DHCP, with **no router changes** and **no general/global conntrack flush** in current work.

### Documentation/implementation boundary

The v0.26–v0.36 laboratory scripts, candidate patches and operator logs reside in off-router evidence/archive paths; they are **not deployed production source** and this checkpoint does not upload them. A passing Fedora namespace test is not proof of safety on Merlin Linux 4.1.52. Issue #212 remains OPEN.

## RC13J v0.41 follow-up — private DNS sidecar transport (2026-10-12)

Operator-supplied Fedora rootless network-namespace lab log:

- `RC13J_V41_ROOTLESS_PRIVATE_ROUTER_NETFILTER=PASS`, `RC13J_V41_NO_EXTERNAL_DEFAULT_ROUTES=PASS`.
- `RC13J_V41_SIDECAR_PRIVATE_INDEPENDENT_INPUT_ACL=PASS` and `RC13J_V41_SCOPED_LAN_TAILNET_DNAT=PASS`.
- `RC13J_V41_BEFORE_UNCOORDINATED_RESET_TCP_UDP=PASS` and `RC13J_V41_AFTER_UNCOORDINATED_RESET_TCP_UDP=PASS`: selected LAN/Tailnet synthetic DNS-like UDP/TCP probes are routed to sidecar while unselected remain on primary within a private model.
- `RC13J_V41_HOST_FILTER_RESET_INNER_ACL_UNCHANGED=PASS`; this checks ONLY the sidecar's separate INPUT ACL survives a flush of the parent/private-router INPUT/FORWARD tables.
- **Blocking counterexample:** `RC13J_V41_SELECTED_DIRECT_SIDECAR_GATE_REACHABLE=YES` and `RC13J_V41_SELECTED_DIRECT_GATE_EXCLUSION_PROVED=NO`. Even a selected client can contact `10.212.41.2:1053` directly and circumvent normal selected-client DNS/53 ingress semantics. The inner ACL accepts source IP but has no strong proof of *how* the packet reached it. Therefore this is a **security design blocker**, not merely a missing rule in production.
- `RC13J_V41_CORE_LOOPBACK_REACHABLE_ONLY_INSIDE_SIDECAR=PASS`. Actual core resolver on 127.0.0.1:55353 remains namespace-private; gateway itself is network-facing on the private routed veth.
- `RC13J_V41_DNS_WIRE_FORMAT=NOT_TESTED_SYNTHETIC_ECHO`, `RC13J_V41_DNSSEC=NOT_TESTED`, `RC13J_V41_ASUS_KERNEL_4_1=NOT_TESTED`, `RC13J_V41_UNCONTROLLED_ROUTER_RESET_SAFETY=LIMITED_INNER_ACL_ONLY`, `RC13J_V41_PRODUCTION_ELIGIBLE=NO`.
- `RC13J_V41_TRANSPORT_EXPERIMENT=PASS_WITH_OPEN_DIRECT_GATE_BLOCKER`, `RC13J_V41_EXTERNAL_ACCEPTANCE=PASS`, `ASUS_PRODUCTION=UNTOUCHED`.

Local operator log reported: `~/Archiwa/ASUS-Edge-Issue-212/rc13j-evidence/dns-sidecar-v41-20261012-185722.log` (not committed; not independently read). The test proves neither deployment feasibility nor spoof-proof / reset-proof origin authentication on Merlin 4.1.52.

**Decision:** do not promote current routed sidecar gateway to production. Next gate is read-only firmware kernel/iptables capability inventory and off-router provenance-stronger routing/proxy architecture exploration, **without changing route_localnet, dnsmasq, DNS Guard or firewall on ASUS**.

## RC13J v0.42 follow-up — ASUS read-only kernel feasibility audit (2026-10-12)

Operator-reported actual ASUS TUF-AX5400 output:

| Feature | Observation | Confidence boundary |
| --- | --- | --- |
| Kernel/toolchain | `4.1.52`, `armv7l`, `iptables v1.4.15` | Confirmed live |
| `/proc/self/ns/net` | `NETNS_HANDLE=NOT_FOUND` | Strong warning: network namespaces **not confirmed**, possible disabled `CONFIG_NET_NS` or platform-specific proc behavior; not a compile-time proof |
| `/sys/module/veth` | `NOT_VISIBLE` | No evidence of veth loaded/built in; visibility alone cannot prove absent support |
| `xt_TPROXY`, `xt_socket`, `nf_tproxy_core` | `NOT_VISIBLE` | TPROXY/socket match not demonstrated; neither module load nor actual support tested |
| `/sys/module/nf_conntrack` | `PRESENT` | Existing conntrack |
| `/proc/net/ip_tables_targets` | `DNAT`, `MARK`, `REDIRECT` reported | Listed loaded/registered targets; MARK alone is **not** TPROXY or provenance authentication |
| `/proc/config.gz` | `KERNEL_CONFIG=UNAVAILABLE` | Kernel build options still unknown |
| Safety markers | Read-only complete; no modules loaded, no iptables/sysctl/service changes | `ASUS_PRODUCTION=UNTOUCHED` |

**Decision:** **NO-GO for deployment planning based on the v0.41 veth/netns sidecar** until firmware-matched ability to instantiate netns/veth has been established by trustworthy non-production evidence. It is inappropriate to assume Fedora netns capabilities carry to Merlin 4.1.52. Even if netns were supported, v0.41's selected-source *direct gateway* bypass remains a separate blocker. TPROXY is similarly **UNPROVEN**, not declared definitively impossible. Do not load modules, change kernel/sysctl, append firewall rules or attempt namespace creation on production to force proof.

**Next design direction:** compare feasible alternatives using already-proven iptables DNAT/REDIRECT/conntrack and a separately isolated resolver **outside the ASUS network namespace / potentially on a separate always-on host**. An alternate resolver must be independent of shared Unbound for an Unbound failure case. Prove source scope, UDP/TCP, direct-host/bypass policy, normal Pi-hole filtering, synthetic faults, failback and risk during independent INPUT reset in Fedora lab; keep extra hardware and production placement as explicit choices, not foregone conclusions. An independent physical host also does *not* eliminate the ASUS single point of failure for routed client traffic.

References for feature semantics: `CONFIG_NET_NS` required for netns (network_namespaces(7)); kernel TPROXY documentation requires its target/socket match and policy routing, plus transparent socket support.
