# ASUS Edge Gateway — documentation consistency review

**Review date:** 2026-10-12  
**Type:** repository/tree + search inventory, detailed review of the **current/canonical** architecture, status, operational and requirements documents, cross-check against issue/PR state and user's current platform decision.  
**Evidence boundary:** **documentation review, not an independent live ASUS or Windows test**. This is not a claim that every historical Markdown/PDF/evidence binary was individually read or that 481 source files were re-tested.

## Source inventory and method

- GitHub `main` recursive tree inspected: **481 tracked entries** at the inspection checkpoint, before the documentation branch changes. Documentation candidates in the tree included **214** relevant text/metadata files when including dated `evidence/` and root/docs records. These counts are a scope inventory, **not 214 file-by-file verifications**.
- GitHub source searches identified **13** indexed files with `RT-BE88U`, **8** with `OPNsense`, and other migration references. Dated worklogs, case studies, benchmark plans and PDF snapshots were classified as historical; current canonical files were read with surrounding context and reconciled.
- Read/compared canonical entry points: `README.md`, `PROJECT-STATUS.md`, `docs/roadmap.md`, `docs/architecture.md`, `docs/network-design.md`, `docs/security.md`, `docs/compatibility.md`, `docs/hardware-inventory.md`, `docs/requirements.md`, `docs/architecture/{physical-topology,addressing-and-zones,availability-and-redundancy,high-level-trust-boundaries,dns-enforcement-flow,boot-service-dependency-flow,tailscale-management-exit-node-flow}.md`, dated architectural snapshot, current worklog, changelog, RouterCloud checkpoint, and repository issues #82, #129, #142, #143, #176, #178, #194, #196, #200, #212, #213, #214, #215, #216, #217. Verified active draft PRs #202, #226 and #227 in the read scope.
- Historical evidence **was not edited to simulate the current date**. Old model-specific plans and dated report PDF remain preserved. Newer strategic decision supersedes them.

## Findings and correction ledger

| # | Finding | Correction / authority | Current status |
| --- | --- | --- | --- |
| D-01 | README/PROJECT-STATUS/roadmap/architecture/compatibility/security/hardware all stated ASUS **RT-BE88U** was the target and OPNsense was only fallback | Updated canonical documents and [dated platform decision](../architecture/platform-direction-2026-10-12.md) | **DOC UPDATED**; RT-BE88U migration cancelled |
| D-02 | RT-BE88U "Phase 2" in roadmap and future TUF retirement were written as committed work | Replaced with ASUS CORE v1.0 and **optional unscheduled OPNsense VM research**, no purchase/deployment | **DOC UPDATED** |
| D-03 | Platform-sensitive Trusted/IoT/Guest #143 and TUF benchmark #194 tied to RT-BE88U | Repositioned as platform-neutral design and TUF-only performance baseline; issue headings receive dated supersession | **DOC/ISSUE UPDATED**; no VLANs currently deployed |
| D-04 | #178 repeatedly described as open after the 2026-10-12 synthetic Gmail+Telegram `Firing/Resolved` acceptance | Matched GitHub issue **CLOSED**; kept explicit pending grouping/anti-flap, Email-only YAML vs live Email+Telegram drift, reload persistence and individual five DNS Guard rule tests | **DOC UPDATED**; limited acceptance preserved |
| D-05 | Risk of misreading DNS Guard v3.2 as LAN-client DNS failover | Explicitly separates **router-system** recovery from off-router **#212**; Pi-hole + dnsmasq share Unbound | **DOC UPDATED**; #212 remains OPEN |
| D-06 | RC13J v0.41 synthetic netns sidecar and v0.42 kernel audit could be misinterpreted as ASUS-safe client failover | Linked open **draft PR #227**: v0.41 authorized direct sidecar gateway bypass; v0.42 no proof of `NET_NS`/`VETH`/TPROXY; no actual DNS wire/DNSSEC/firmware pilot | **GATED**; no production authorization |
| D-07 | Pi-hole-aware DR could be overstated from 65-IPK offline reinstall, optional BusyBox boot persistence and earlier recovery | Reiterated **#129 OPEN**; full blank-device Pi-hole-aware recovery, capabilities, aliases, filters, local naming and RTO/RPO not accepted | **GATED** |
| D-08 | Dated 2026-10-08 architecture snapshot/PDF contains future RT-BE88U and #200 OPEN, which would mislead undated readers | Added explicit **2026-10-12 supersession note** to the Markdown snapshot; left dated PDF and historical rows unchanged | **DOC UPDATED** without rewriting history |
| D-09 | Separate Windows 11 VivoBook has only one external physical Ethernet and no virtualization installed | Clarified VM has independent virtual NAT WAN + internal/host-only LAN; no second physical NIC needed for lab; no lab bridged into production and NAT egress is not full isolation | **RESEARCH PLAN ONLY** |
| D-10 | Contradiction between closed alerting issue and future remaining polish | The closed status refers to the bounded validated acceptance. Provisioning drift, missing reload tests and per-rule checks are retained as gaps, not passed | **FOLLOW-UP OPEN, NOT RETESTED** |
| D-11 | Other issue tracker descriptions still include old migration plan | Canonical issue #82, segmentation #143 and performance #194 carry 2026-10-12 supersession notices, retaining historical text for traceability | **ISSUE UPDATED** |

## Current accepted reference — 2026-10-12

- **Router**: ASUS TUF-AX5400 / GNUton `3004.388.11_1-gnuton1_tuf`, Linux 4.1.52, 512 MiB RAM. Last broad live production acceptance 2026-10-09: 0 failures / 0 warnings; no new live runtime audit during this review.
- **DNS**: Pi-hole LAN alias `192.168.50.253`, firmware dnsmasq classic-DNS interception and one shared local Unbound `127.0.0.1:53535`; DNS Guard v3.2 supports router-system DNS fallback only. This remains a single-router/Unbound failure domain.
- **Services/security**: Tailscale (reference operator-verified `1.103.375` unstable/dev), Grants plus managed local firewall, exit-node source scoping #176 pending; RouterCloud on router SSD `192.168.50.254` plus isolated UX draft work; no public WAN app publishing; native LAN/WAN IPv6 not active in reference.
- **Fedora**: Grafana + VictoriaMetrics + Loki/Alloy/syslog-ng, 15 alerts; bounded real synthetic `Firing/Resolved` Gmail and Telegram path accepted on 2026-10-12; one monitoring host, no HA.
- **Reliability**: historical boot/swap restoration, versioned off-router RouterCloud backups and partially verified DR; comprehensive current Pi-hole-aware DR #129 outstanding. #200 permission hardening **CLOSED**. No current VLANs, dual WAN, gateway HA, dedicated OOB or proven UPS.
- **Platform policy**: **No RT-BE88U migration**, TUF remains production; **future OPNsense option with no date**, VM-only investigation using a Windows 11 laptop when separately pursued. This does not reclassify the ASUS source repository as frozen.

## Documentation changed on this branch

New: [platform decision](../architecture/platform-direction-2026-10-12.md), **this audit**.

Updated: root `README.md`, `PROJECT-STATUS.md`, `CHANGELOG.md`; `docs/roadmap.md`, `architecture.md`, `compatibility.md`, `hardware-inventory.md`, `security.md`, `requirements.md`, `network-design.md`, `worklog/2026-10-12.md`; `docs/architecture/addressing-and-zones.md`, `availability-and-redundancy.md`, `physical-topology.md`, `high-level-trust-boundaries.md` and the **dated Markdown** architecture snapshot (with supersession note only).

The separate **draft PR #227** contains the granular RC13J v0.26-v0.42 evidence and kernel-source research; do **not** claim it was merged or is part of the `main` source. The current architecture-documentation PR and PR #227 may overlap on `docs/roadmap.md` and `docs/worklog/2026-10-12.md`; reconcile these paths on review before any merge.

## Outstanding checks and acceptance boundaries

- New documentation branch requires GitHub PR review, source validation and link/CI checks. **This is not a completed/merged CORE v1.0 release.**
- Current router not touched; no live hardware/OPNsense, client DNS failover, new kernel or WAN changes.
- Existing historical plans remain findable. Their RT-BE88U claim is explicitly overridden; no rewrite of old test reports, worklogs or PDF binary.
- No asserted universal performance of a future OPNsense or automatically resilient frontend: actual backend independence, DNSSEC, Pi-hole policy parity, DHCP, source-address visibility, PF routing and independent restore all require future VM tests.

## Validation performed on the GitHub documentation branch

- GitHub compare before the final audit note: `main...docs/2026-10-12-asus-core-opnsense-research-pivot` reported **18 changed files**, all Markdown documentation, zero changes to code/configuration/runtime/scripts.
- Checked **321 local Markdown links** across those 18 changed files against the branch's recursive Git tree. **Zero unresolved file references**; the two initially unmatched raw targets (`docs/case-studies/` and `evidence/`) were links to existing **directories**, not missing files. This does not validate external HTTPS destinations or Markdown fragment/anchor IDs.
- The GitHub `Validation suite` workflow was observed **in progress** on the branch during review. This audit makes **no CI PASS claim**; inspect the final checks before any merge.
- Draft PR [#228](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/228) holds these documentation changes. PR #227 remains a separate draft; reconcile their common roadmap/worklog files when merging. `main` has not been changed by this branch.
