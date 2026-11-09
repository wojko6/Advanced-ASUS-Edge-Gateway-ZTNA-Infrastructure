# Complete Markdown source and external-link audit — 2026-11-09

> **Status:** STATIC_REVIEW_COMPLETE / URL_LIVE_ACCESS_PARTIAL / NOT_A_RUNTIME_SECURITY_AUDIT
>
> **Snapshot:** existing PR #371 branch at `e86d8e9f9efc2499d26ee9f8fcf8fdd1b3bbb2df`. This report is a follow-up to [focused documentation reconciliation](2026-11-09-documentation-reconciliation.md), without a new GitHub issue, production configuration change, router action or automatic PR merge.

## Coverage and methodology

- Inspected **every one of the 323 Markdown files** in the PR branch by fetching source content through the connected GitHub repository. The scan covered **41,277 source lines**; directory scope: **{"other":31,"docs":113,"audit":19,"worklog":53,"evidence":107}**.
- Per file: detected heading structure, external HTTP(S) URL occurrences (including code examples), relative Markdown link destination existence and explicit cross-document fragment targets.
- Across sources: **783 URL occurrences**, **220 unique HTTP(S) strings**. A [complete per-file inventory](2026-11-09-markdown-file-register.md) and [deduplicated external URL ledger](2026-11-09-external-links-register.md) provide traceability.
- All **323** Markdown files had at least one heading. No missing relative file/directory target was detected by the source-pattern checker (**0** findings). The **20 cross-file fragment** destinations were independently matched to heading slugs of the 10 referenced Markdown files (**20/20 matched**). This does not test all possible HTML-generated anchors or external fragment IDs.
- GitHub API verified **130 distinct issue/PR numbers** (representing **135 distinct URLs**) in the project; an additional **35 GitHub resource URLs** were fetched through the GitHub connector, without failures in those provider-supported categories.
- Public website retrieval was tested for all **19** distinct non-GitHub/nonlocal endpoints: **12** served readable content, **4** had matching indexed public resources but direct read timed out, **2** could not be reliably checked, and **1** was an OAuth API endpoint (not a navigable web page). Three GitHub Actions UI URLs were unsupported by direct fetch; the `.github/workflows/shellcheck.yml` file itself exists.
- Another **28 URLs** are local/test/private-address or example references and cannot be externally tested by design.

## Detailed external URL classification

| Result | Unique URLs | Interpretation |
| --- | ---: | --- |
| GitHub issue/PR URL (API verified) | 135 | Target object exists at audit time |
| Other GitHub resource fetched | 35 | Provider returned a matching resource |
| GitHub Actions UI (workflow source exists, page untested) | 2 | Source exists, no claim about badge rendering |
| GitHub Actions landing page (connector unsupported) | 1 | Not checked as web UI |
| Public site directly accessible | 12 | Live/public content retrieved |
| Public site indirectly confirmed via search index | 4 | Direct fetch timed out; not reported broken |
| Public site not verifiable | 2 | Needs separate browser/network inspection |
| OAuth endpoint, not ordinary GET navigation | 1 | A browser redirect/error is not a broken OAuth endpoint |
| Local/example URL | 28 | External checker intentionally inapplicable |

**The two unresolved public links** are `https://bugs.kde.org/show_bug.cgi?id=526934` (access restrictions) and `https://jacklul.github.io/entware-pi-hole/armv7sf-k3.2/` (source address inaccessible to crawler; an archived package-feed path must not be silently replaced with a homepage). Both remain **UNVERIFIED**, not confirmed 404.

Direct requests timed out for a BusyBox `1.36.1` archive, the Grafana file-provisioning page and two systemd manpage URLs. Official/public indexes did show matching resources. Keep their historical URLs pending an authenticated shell/HTTP acceptance test; do not rewrite evidence based on crawler behavior alone.

## Historical-document interpretation

- Historical worklogs, architecture drafts, dated audits, test evidence, recovery experiments and superseded instructions retain **the facts and status labels as of their own dates**, not present-tense production claims.
- The old “Draft #369” wording remains present in the historical **2026-11-05 consistency audit** and **2026-11-03 supervised-GUI design** as a point-in-time note. Current-facing entry points correctly identify #369 as **merged 2026-11-05**; this is not a contradiction to erase from archives.
- Prior Fedora/VictoriaMetrics releases (1.154.1 and 1.155.0) remain valid **historical checkpoints**, while the [Nov 9 accepted report](../../evidence/2026-11-09/fedora-victoriametrics-v1.156.0-live-upgrade.md) records the later 1.156.0 runtime.
- A successful `up=1` scrape does not certify `probe_success`, and a local snapshot does not constitute off-host DR. No historical HOLD was silently upgraded to a current PASS.

## Validation limits / follow-up

This pass **read and mechanically analyzed every Markdown document** and checked all extracted HTTP(S) strings, but it did **not** reproduce every historical experiment, personally validate all technical assertions against devices, run a complete accessibility test of each site at protocol level, or inspect binary media and non-Markdown scripts as historical prose. Some public endpoints are bot-gated, binary downloads, POST-only APIs or intended internal routes. Do not interpret timeout/inaccessibility as definite dead links.

For reproducibility, recheck from a Git clone using an HTTP-aware link checker with explicit allowlists for `.home.arpa`, RFC1918, localhost, example domains, bot-gated sites, external file downloads, and GitHub API-authenticated routes. Preserve dated status and sanitize any output before publishing.

**Conclusion:** **323/323 Markdown sources scanned; 220/220 unique HTTP(S) strings categorized; 130/130 GitHub issue/PR IDs present; no missing relative file destinations; 20/20 cross-file heading anchors matched; 2 public URLs plus GitHub Actions UI remain unverified, not proved broken.** Documentation-only follow-up on existing PR #371.
