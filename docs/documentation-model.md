# Documentation model and source of truth

**Status:** CURRENT

**Last reviewed:** 2026-10-24 (current navigation and status reconciliation; documentation-only, not a router acceptance run). See [October 24 closeout](audits/2026-10-24-current-navigation-closeout.md) and the [earlier source-of-truth audit](audits/2026-10-16-repository-documentation-review.md).

**Applies to:** `main`

This project deliberately separates current state, implementation, live evidence, plans and historical engineering records. When documents disagree, use the precedence below instead of merging claims from different evidence classes.

## Source-of-truth precedence

1. **`PROJECT-STATUS.md`** — current project phase, accepted baseline, open/closed findings and explicit deployment boundaries.
2. **Dated `evidence/` artifacts** — proof for specific observed claims under the documented date, device, method and limitations. Evidence proves only the claim it records; it does not automatically mean the same code/configuration is still deployed.
3. **Current operational/network-design documentation** — `docs/network-design.md`, `docs/hardware-inventory.md`, `docs/operations.md`, `docs/deployment-pl.md`, `docs/requirements.md`, security/firewall/testing documentation and current architecture documentation. The network-design index organizes the current L1-L7 documentation; the requirements map records test ownership and limits. Both must follow current status and dated observations when deployment state changes.
4. **`README.md`** — public summary derived from the current status and supporting evidence.
5. **`docs/roadmap.md`** — planned or candidate work; a roadmap item is not implemented or validated unless another current source says so.
6. **`docs/worklog/`** — dated public engineering chronology. A worklog explains what happened; it is not a substitute for evidence.
7. **Dated audit/remediation/planning documents** — historical decision records. Completed or superseded documents must say so explicitly at the top.
8. **`CHANGELOG.md`** — release/unreleased change history; it must be synchronized with the current status before a release is cut.

## Document lifecycle labels

Use one of these labels for documents whose lifecycle could be ambiguous:

- **CURRENT** — active instructions or status.
- **PLANNED / DRAFT** — proposed work that is not yet an accepted implementation.
- **COMPLETED / HISTORICAL** — retained for traceability after the described work has finished.
- **SUPERSEDED** — replaced by another named document or design.

A historical document may intentionally contain old dates or open findings when it is clearly marked as historical. Do not rewrite historical records merely to make them look current.

**Operational safety rule:** an old acceptance runbook with commands that could change DNS, WAN, firewall or reboot state must carry a conspicuous `COMPLETED / HISTORICAL` notice and link to the current accepted evidence. Merely leaving it in the docs tree must not imply that its instructions are pending or safe to re-run.

**Version vocabulary:** `ASUS CORE v1.0` names an *engineering stability/recovery milestone* for the current TUF-AX5400 architecture. The independent repository software `VERSION` file (at this review `2.1.4-dev`) is a packaging/release identifier, **not** proof that CORE v1.0 has been accepted or released. Do not infer deployed versions from either label alone.

## Documentation language ownership

The [documentation language policy](language-policy.md) defines repository English/Polish roles without changing the source-of-truth hierarchy above:

- **EN canonical technical documents** retain the project-level design, evidence and recovery contracts.
- **PL operator guides** are linked from the [Polish documentation index](pl/README.md), whether stored under `docs/pl/` or at compatible historical paths.
- A localized guide may be an operator adaptation, not a literal translation. The current English contract and dated live evidence govern technical claims; safety-critical divergence requires review and reconciliation before following either guide.
- Preserve literal commands/metrics, historical logs, stable links and dated evidence; do not auto-translate source code or rewrite history.

For issue #129, the [Disaster Recovery navigation index](disaster-recovery-index.md) maps the current documents and validation gates without introducing a competing source of truth. The [English DR baseline](router-disaster-recovery.md) and [staged reconstruction runbook](pihole-dr-rebuild-runbook.md), merged in PR #205, define the technical recovery contract. The [Polish bare-router operator guide](router-bare-metal-recovery-pl.md) is a step-gated adaptation, not a completed end-to-end recovery test. Review safety gates across languages before changing either document.

## Repository vs live-deployment boundary

Always distinguish:

- code/configuration present in the Git repository;
- behavior validated by CI/static/mock tests;
- behavior deployed on the reference router;
- behavior observed live on the router or a defined client.

A merged PR or green CI run does **not** prove that the same revision is installed on the reference ASUS. Promotion into the live validated baseline requires dated live evidence when the claim depends on deployment state.

## Architecture asset rule

The canonical current network design is indexed by `docs/network-design.md` and
uses focused, source-controlled documents under `docs/architecture/`:

- `ASUS-Edge-Gateway-Architecture-2026-10-08.md` — historical high-level snapshot, not continuously refreshed; the later [v1.2 dated architecture](architecture/ASUS-Edge-Gateway-Architecture-2026-10-15-v1.2.md) and current project status take precedence.
- `physical-topology.md` — physical roles and attachment/failure boundaries;
- `high-level-trust-boundaries.md` — logical trust boundaries;
- `addressing-and-zones.md` — public IPAM and current/planned zone ownership;
- `dns-enforcement-flow.md` — DNS datapaths and enforcement scope;
- `tailscale-management-exit-node-flow.md` — remote management/forwarding flow;
- `boot-service-dependency-flow.md` — boot/runtime dependencies;
- `availability-and-redundancy.md` — HA applicability and SPOF model;
- `l2-security-applicability.md` — L2/AAA applicability matrix.

Not every architecture document is a Mermaid flow diagram. Applicability and
inventory documents are canonical when their purpose is tabular rather than
flow-oriented.

A dated exported PDF is a publication artifact, not an automatically
updating source of truth. Publish only after a privacy review; record
reference date and keep current Markdown status, diagrams, and evidence
authoritative.

The latest published **reference production** technical-architecture PDF is
[`ASUS-Edge-Gateway-Architecture-2026-10-15-v1.2.pdf`](architecture/ASUS-Edge-Gateway-Architecture-2026-10-15-v1.2.pdf),
with the [dated v1.2 Markdown source](architecture/ASUS-Edge-Gateway-Architecture-2026-10-15-v1.2.md).
The previous [2026-10-13 v1.1 PDF](architecture/ASUS-Edge-Gateway-Architecture-2026-10-13-v1.1.pdf),
2026-10-08 PDF and its Markdown overview are **historical records**.
Publishing v1.2 is a documentation change only: it does not establish a new
router-wide acceptance, hardware purchase, DNS/firewall change, approved
Issue #235 SSD remediation, or OPNsense/Flint migration.

**Version namespace caveat (2026-10-16 audit):** version numbers are **publication-specific**, not a single monotonically increasing repository release sequence. The historical **2026-10-08** architecture PDF uses “wersja 2.0” on its cover; the **2026-10-15 production** architecture publication is **v1.2**, while the **2026-10-15 conditional Flint 4 future-design** PDF is separately **v2.0**. Always identify an architecture by **date + current-production versus hypothetical-future scope + exact filename**, never by “v2.0” alone. Do not rewrite historical PDF cover pages to fake a unified version history.

`docs/images/Architecture.png` is retained only as a historical/illustrative
artifact and is not a source of truth for the current deployment.

Planned future-state diagrams must be clearly labelled as planned and must not
silently replace the validated current-deployment diagrams. Retired diagrams
should remain only when their historical/provenance value is explicit. This
avoids presenting competing diagrams as equally current.
