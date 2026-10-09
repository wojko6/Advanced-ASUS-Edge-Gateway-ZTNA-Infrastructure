# Documentation language and translation policy

**Status:** CURRENT (policy proposal in issue #206; effective once merged)  
**Reviewed:** 2026-10-09  
**Scope:** public documentation, operator guides, evidence, code comments and UI localization.

## Language ownership

This repository is primarily **English-language technical documentation** for a reproducible Home/SMB security-edge lab. **Polish is supported for hands-on operator instructions and user-facing localization**, not as an undocumented second source of truth.

| Material | Default language | Notes |
|---|---|---|
| Root `README.md`, `PROJECT-STATUS.md`, `CHANGELOG.md`, `CONTRIBUTING.md` | English | Project status and portfolio-facing entry points |
| `docs/architecture/`, network/security design, requirements, operations and canonical recovery contracts | English | Historical Polish dated snapshots are retained, not silently rewritten |
| `docs/case-studies/`, `evidence/`, `docs/worklog/` | English | Preserve original historical evidence, quotes, log output and dated claims |
| `docs/pl/` catalog and **operator-focused Polish guides** | Polish | Existing `*-pl.md` and `deployment-pl.md` paths remain valid |
| Code, test assertions, CLI output, config keys and code comments | English / exact technical identifiers | **Do not translate** execution contracts or machine-readable output |
| Polish ASUS WebUI overlay and RouterCloud UI strings | Polish where intended | Product UI localization is independent of documentation-language policy |

Do not treat an English word in Polish operational prose as an automatic error: product names, established network terms, literal status labels and exact commands may legitimately remain English.

## One authoritative operational contract, localized guidance

1. The **source-of-truth precedence** in [documentation-model.md](documentation-model.md) always applies. Language never upgrades a draft, old screenshot or translation into a newer production acceptance result.
2. An English canonical design/recovery document defines the **technical scope, prerequisites, safety gates and claim boundaries**. A Polish companion may be an **operator adaptation**, not a word-for-word translation. Label it as such and link the current English source.
3. A Polish guide must preserve all safety-critical conditions: target model/firmware, read-only vs mutating actions, backup integrity, stop/rollback conditions, startup/DNS order and the distinction between *tested* and *not tested*.
4. If procedures disagree, **stop and reconcile both documents against current status and dated evidence** before execution. Do not silently assume the English or Polish text is current based solely on its language.
5. Any PR changing a recovery/installation safety contract must review the linked Polish guide and record **updated / still compatible / follow-up required** with a reason. Conversely, changes to the Polish guide must check canonical assumptions. Review by a human is required: CI cannot reliably validate semantic translation or operational safety.
6. Reference both documents by link rather than duplicating large identical command blocks when a single version can serve both readers. Preserve explicit locally necessary explanations for Polish operators.

### Current recovery example: issue #129

- Existing English baseline: [router-disaster-recovery.md](router-disaster-recovery.md).
- A new, more detailed English ordered runbook and a **Polish bare-router/empty-SSD operator procedure** are under review in [PR #205](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/205), not yet authoritative on `main`.
- These are **related procedures with different levels of detail**, not a certified line-by-line translation. The new Polish procedure is explicitly **not an executed bare-metal restore**.
- **Merge order:** keep links to PR #205 until its documents are merged; then update [Polish index](pl/README.md) with stable relative links and review the EN/PL acceptance gates together. Do not publish a broken local link to a document not on `main`.

## Language-neutral elements

Never translate or automatically rewrite:
- shell commands, CLI arguments, executable names and file paths;
- environment/configuration keys (`EDGE_*`), JSON/YAML keys, API fields, metric names, test assertions and expected output such as `READY=PASS`;
- package identifiers, firewall chain names, checksum manifests, cryptographic signatures and literal protocol/port identifiers;
- quotations from upstream software, command output, journal entries and historical evidence;
- existing links, anchors and dated worklog entries solely to achieve linguistic uniformity.

Prefer an **explanation alongside** a technical term (for example “tryb awaryjny DNS (break-glass)”), not a replacement of its machine-readable spelling.

## Safe file organization

- [Polish documentation index](pl/README.md) is the **entry point**, not a duplicated source tree.
- Do **not** rename existing Polish guides in a broad migration: `docs/deployment-pl.md`, `docs/printer-setup-lan-pl.md`, `docs/printer-setup-tailscale-pl.md` have existing inbound Markdown links and may be referenced outside this repository.
- For new **standalone** Polish operator guides, prefer `docs/pl/` **after** the PR #205 compatibility discussion. If the guide must retain an established path, index it from `docs/pl/README.md` instead.
- If a future move is justified, retain a stub at the old path pointing to the new one; update internal links and validate them in CI. Do not delete dated historical evidence or old snapshots.

## Review and verification

- `python3 tests/test-doc-links.py` checks the existence of repository-local Markdown link destinations.
- `python3 tests/test-doc-language-policy.py` checks the Polish guide index/required references, file existence and declared documentation policy integration.
- GitHub Actions runs both checks. They **do not** measure translation quality, English/Polish semantic equivalence, firmware state or a successful recovery.
- PR reviewers manually check translated/adapted **technical facts**, cross-language safety gates, terminology and evidence boundaries.

**Change control:** issue [#206](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/206). No router configuration or service changes are authorized by a documentation-only PR.
