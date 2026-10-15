# Issue #235 — off-router HTTP origin / trusted assets hardening (2026-10-13)

> **Historical scope note (added 2026-10-15):** This document preserves the test state and unpublished-worktree status **as of October 13**. Subsequent trusted-asset descriptor and ARMv7/PrivDrop investigations are separately recorded in [October 14](../../docs/worklog/2026-10-14.md) and [October 15](../../docs/worklog/2026-10-15.md) worklogs. The later draft code and isolated PASS results do not establish a production HTTP-origin fix. Do not replace the dated limitations below with unverified later claims.

**Status:** LOCAL SECURITY CANDIDATE, TESTED IN FEDORA LAB — **NOT COMMITTED/PUSHED/MERGED OR DEPLOYED AS BACKEND**.  
**Scope:** [#235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) — Dufs 0.46.0 RouterCloud file response headers and trusted UI asset boundaries.  
**Evidence source:** operator command output and local Rust tests. No production browser exploit or least-privilege runtime acceptance. Synthetic localhost/off-router fixtures only.

## Source and production boundary

- Isolated worktree: `~/Projekty/routercloud-security-235/dufs`; branch `security/issue235-file-origin-guard`, observed local base `c3accce`; modified `src/server.rs`, new untracked `tests/routercloud_security_origin.rs`. All changes remained local at end of session.
- Untrusted active HTML/SVG/XML/MHTML-like user files receive `Content-Disposition: attachment`, `Content-Security-Policy: sandbox`, `X-Content-Type-Options: nosniff`; dedicated tests also cover auth, GET/HEAD, Range/multipart, and benign image/PDF handling.
- Sanitized earlier read-only ASUS inspection: assets and data-root paths do not nest; assets root was root-owned, mode 0755; inspected UI files were root-owned, mode 0644; no symlinks seen and optional `404.html` was absent. Those metadata checks do not prove runtime immutability.
- No service restarts, permission changes, DNS/firewall/Tailscale changes, or binary deployment to production ASUS during this local test sequence.

## RED → GREEN findings

| Case | Reproduced RED | Local change / observed GREEN |
| --- | --- | --- |
| Arbitrary YAML `error-page` referencing user HTML | HTTP 404 `inline; filename="user404.html"`, no CSP | Restrict trusted 404 treatment to expected `assets/404.html` outside data root; explicit negative, positive, overlapping-root tests; security suite **9/9 PASS** at checkpoint |
| Versioned asset file symlink outside assets | HTTP 200 `inline`, CSP absent | `resolve_trusted_asset` checks path components/symlinks and canonical containment; persistent regression turns GREEN |
| `/__routercloud/login` asset symlink outside assets | HTTP 200 `inline`, CSP absent | Same guard; two persistent symlink tests passed; dedicated security suite **11/11 PASS** |
| Startup `assets/index.html` symlink to user HTML | Main UI response HTTP 200 with synthetic marker and CSP absent | Linux startup index opened with directory descriptor plus `openat(O_NOFOLLOW)` for final entry; targeted script ended GREEN; **8/8** existing `tests/assets.rs` PASS |
| Separate file/metadata/MIME pathname opens | Code review found distinct opens including multipart MIME sniff | V2 handler now uses single `fs::File::open` for response body plus `file.metadata()` and `get_content_type_from_open_file(&mut file, path)`; multipart duplicate MIME open removed. **`ISSUE235_SINGLE_FD_V2=PASS`**, including full `cargo test --locked -q` |

The intermediate full Rust suite before startup/single-FD changes was **217/217 PASS**. Final V2 script reported PASS for formatting/diff checks and the complete locked test suite, but its abbreviated final log did not state a new numeric total. Do not claim every race eliminated or browsers proven safe just because a subset of tests is green.

## Residual risks and compatibility

1. **TOCTOU REMAINS OPEN:** `resolve_trusted_asset` still checks pathname then `handle_send_file` opens it by pathname. A concurrent filesystem replacement could break the checked-object/served-object identity. Implement a directory-FD-relative walk (e.g. component-by-component `openat` with `O_NOFOLLOW`), retain the same opened descriptor for metadata/MIME/body, and protect trusted root/base integrity. A mere pre-open `canonicalize` is insufficient.
2. The Linux startup-index fix checks the final symlink only; it does not establish protection against every parent directory rename/replacement, mount alias or writable trusted UI file. The non-Linux fallback is not an equivalent hardened implementation.
3. Trusted asset route, login assets, custom 404 and initial `index.html` must share an explicit fail-closed policy; test nested legitimate assets, partial content, cache validators, HEAD, and authenticated/guest cases after changing open semantics.
4. **Render compatibility is deliberately degraded:** test calls to `--render-index` and `--render-spa` returned `200` with `attachment; filename="index.html"`, CSP `sandbox` and `nosniff`. Existing render tests passed but do not validate inline browser hosting. Current production configuration audit found all three opt-in `--render-*` modes unset, so this break is unlikely to affect the current RouterCloud deployment; it matters for a generic Dufs host. Do not relax same-origin document headers globally.
5. Issue #235 also tracks **separate P1 process privileges** (root/capabilities, writable path review, least privilege) and real-browser origin/session testing. Source tests are not production acceptance.

## Next-session acceptance gate

- Open trusted UI assets by descriptor relative to a validated trusted directory, without reopening by path; reconcile custom 404/startup and MIME with the same-FD response implementation.
- Add RED/GREEN tests for symlink traversal at each component, root containment, directory replacement/race where feasible, legitimate asset operation, and optional render-mode contract.
- Run full `cargo fmt --all -- --check`, `git diff --check`, `cargo test --locked`, targeted security and assets/render tests, and review the entire diff including new untracked tests.
- Keep production ASUS untouched, and **do not commit/push/merge/deploy the local backend security patch** until the operator explicitly approves the scoped code review and later rollout. Separate privilege hardening into its own gate.

See [2026-10-13 public worklog](../../docs/worklog/2026-10-13.md) and [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235).
