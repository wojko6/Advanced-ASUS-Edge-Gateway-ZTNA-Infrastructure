# Start here — a guided tour of ASUS Edge Gateway

**Status:** CURRENT / NAVIGATION ONLY  
**Reviewed:** 2026-10-26 (navigation and HCC status links; no new live router/service validation)  
**Language:** English reader entry point · [Wersja polska](pl/START-HERE.md)

Welcome. You do **not** need to read the entire repository or run any scripts to understand this project. This page is a **reading map**, not an installation manual or permission to deploy changes.

## What is this project?

This is a reproducible, security-focused Home/SMB network lab built around an **ASUS TUF-AX5400** running GNUton Asuswrt-Merlin. It brings together firewall and access policies, Tailscale remote access, Pi-hole and Unbound DNS, RouterCloud, recovery workflows, and monitoring on a separate Fedora host. The goal is to make design decisions and test outcomes reviewable.

**Scope matters:** the reference ASUS is still the production gateway. This is an *enterprise-style lab*, **not** an enterprise high-availability appliance. A proposed future Flint 4/ASUS split or OPNsense replacement is **design/research**, not a completed migration. The authoritative current deployment and restrictions are in [PROJECT-STATUS.md](../PROJECT-STATUS.md).

## First visit: 15–20-minute route

The times below are **reading estimates**, not benchmarks. Skim the linked sections; you are not expected to read whole documents in one sitting.

| Step | Read | What to look for | Approx. |
| --- | --- | --- | --- |
| 1 | [README introduction and portfolio highlights](../README.md#portfolio-highlights) | Purpose, capabilities, and project boundaries | 3 min |
| 2 | [Current ASUS architecture v1.2](architecture/ASUS-Edge-Gateway-Architecture-2026-10-15-v1.2.md) ([17-page PDF](architecture/ASUS-Edge-Gateway-Architecture-2026-10-15-v1.2.pdf)) | The diagram, router vs. Fedora responsibilities, DNS and storage; **skim**, do not read all 17 PDF pages | 5 min |
| 3 | [High-level trust boundaries](architecture/high-level-trust-boundaries.md) | Which identities and networks can reach which services | 4 min |
| 4 | [Project status](../PROJECT-STATUS.md) | First read the opening status, dated live checkpoints, and explicit HOLD/NOT DEPLOYED restrictions | 5 min |
| 5 | [Documentation model](documentation-model.md) | Which sources prevail when a plan, a test and the running system differ | 2 min |

**After these five stops, you can stop.** If you want more detail, pick *one* track below instead of traversing the whole tree.

## Choose one path according to your interest

| You want to understand… | Open next | You can defer… |
| --- | --- | --- |
| Overall project / portfolio | [README highlights](../README.md#portfolio-highlights) → [case-study index](CASE-STUDIES.md) | Individual test transcripts and daily worklogs |
| Network engineering | [Network design index](network-design.md) → [physical topology](architecture/physical-topology.md) → [addressing and trust zones](architecture/addressing-and-zones.md) | Historic diagrams and unpublished future designs |
| Security and Zero Trust | [Security model](security.md) → [threat model](threat-model.md) → [firewall policy](firewall-policy.md) | Low-level proof for each control until you need verification |
| Operations / deployment | [Operations reference](operations.md) → [Polish operator-guide index](pl/README.md) → [deployment guide (PL)](deployment-pl.md) | Installation commands until compatibility, backup, scope and approvals are reviewed |
| Recovery / reliability | [Disaster Recovery reading index](disaster-recovery-index.md) → [router recovery baseline](router-disaster-recovery.md) | Restoring a live device; the blank-router recovery gate is not fully proven |
| Tests and reproducibility | [Testing strategy](testing.md) → [requirements and acceptance map](requirements.md) → [evidence collection](evidence-collection.md) | Raw dated evidence until you are checking a specific claim |
| Project history / next ideas | [Roadmap](roadmap.md) → [worklog timeline](worklog/README.md) | Treating older proposals or laboratory PASS results as current production state |

### Optional Fedora monitoring UI lab

The [Homelab Control Center V0.1–V0.3 lab](../experiments/fedora/homelab-control-center-v0.1/README.md) is **not** the ASUS router WebUI or a permanently running service. The merged V0.3 experiment has two local-source-backed read-only telemetry panels; synthetic service, incident and recovery widgets remain hidden until DEMO opt-in. The [V0.3 HTTPS test record](../experiments/fedora/homelab-control-center-v0.1/V0.3-DNS-GUARD-PREFLIGHT.md) describes what the manual checks prove—and do not prove. Permanent deployment remains HOLD.

## How the repository is organized

- **Root:** [README](../README.md) is the overview; [PROJECT-STATUS](../PROJECT-STATUS.md) holds current accepted scope; [CHANGELOG](../CHANGELOG.md) tracks changes; [CONTRIBUTING](../CONTRIBUTING.md) explains contribution rules.
- **`docs/`:** current architecture, operational guides, topic indexes, case studies, plans, and dated audits. Start from a topic index, not from the folder's alphabetical listing.
- **`docs/architecture/`:** the dated **current ASUS** architecture and historical/future variants. A larger version number on a *future design* does **not** make it the production baseline.
- **`docs/pl/`:** Polish reader entry point and operator documentation. The [language policy](language-policy.md) explains why some technical contracts remain English.
- **`evidence/YYYY-MM-DD/`:** sanitized, date-bounded observations. Evidence for a lab, mock, QEMU or Fedora run does **not** prove a production-ASUS deployment.
- **`docs/worklog/` and `docs/audits/`:** engineering history and review records. Useful for traceability, not a replacement for current instructions.
- **`scripts/`, `router/`, `monitoring/`, and `tests/`:** implementation and checks. Inspect these only after understanding scope and trust boundaries.

## Read status labels before believing a claim

| Label / phrase | Practical meaning |
| --- | --- |
| **CURRENT** | Maintained guidance, within the document's stated review date and scope |
| **HISTORICAL / SUPERSEDED** | A dated record, not instructions to follow as the latest configuration |
| **PLANNED / DRAFT** | A proposal or candidate; it does **not** mean deployed |
| **PASS** | The *specific recorded test* passed; identify its date, environment and acceptance limits |
| **LAB ONLY / Fedora / QEMU** | Isolated research; not equivalent to execution on the ASUS router |
| **NOT DEPLOYED / HOLD / NO-GO** | A change has not been accepted for production; do not infer installation or authorization |

**Checking an important claim:** start with [PROJECT-STATUS](../PROJECT-STATUS.md), follow the relevant **current guide**, and then inspect its linked **dated evidence**. If the guide and evidence appear inconsistent, use the [source-of-truth rules](documentation-model.md) and retain the explicit uncertainty. A GitHub merge or green CI run proves neither production activation nor live-network acceptance.

## What you can safely skip on day one

Skip the full `evidence/` archive, daily `worklog/` entries, historical architecture PDFs, experimental branches, and lengthy commands in deployment/restore runbooks. Return to them only when examining a particular decision or trying to reproduce a clearly approved test.

**No action on the router is required for this tour.** In particular, do not run installers, restore operations, permission fixes, firewall/DNS changes, or experimental SSD/PrivDrop helpers simply because a procedure appears in the repo. Verify current prerequisites, explicit approval and rollback gates first.

---

**Where next?** [Network design](network-design.md) · [Case studies](CASE-STUDIES.md) · [Polish operator documentation](pl/README.md) · [Current status](../PROJECT-STATUS.md) · [Documentation rules](documentation-model.md)
