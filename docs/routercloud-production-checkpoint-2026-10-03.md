# RouterCloud production checkpoint — 2026-10-03

## Status

RouterCloud is the current browser-facing Personal Cloud service on the reference
ASUS TUF-AX5400 deployment. It remains restricted to the existing LAN/Tailscale
trust boundary and serves only the dedicated RouterCloud data root.

This document supersedes the
[2026-10-02 Metro checkpoint](routercloud-metro-production-checkpoint-2026-10-02.md)
for the current user-facing state. The 2026-10-02 document remains useful as the
historical acceptance record for the first Metro/WebDAV browser phase.

Issues #136, #137 and #138 are complete:

- #136 — automated one-way Fedora -> RouterCloud synchronization;
- #137 — browser-based LAN/Tailscale file access;
- #138 — independent versioned encrypted backup/restore history.

## Current user-facing scope

The current RouterCloud UI includes:

- dedicated RouterCloud login/session authentication;
- login with either the canonical username or the configured email alias;
- Polish Metro-style interface and RouterCloud branding;
- browser favicon and branded login page;
- file/folder browsing;
- file/folder upload;
- browser drag-and-drop upload;
- create-folder and create-file actions;
- per-row download;
- checkbox selection plus selected server-side ZIP download;
- safe same-directory rename;
- RouterCloud-specific delete while generic Dufs delete remains disabled;
- bounded text editing;
- WebDAV desktop integration;
- storage-capacity display;
- AJAX sorting without a full page reload;
- live AJAX search with a 250 ms debounce;
- URL query synchronization for live search without navigation;
- recent-files panel;
- persistent favorites;
- context-menu add/remove favorites;
- favorites-panel drag-and-drop implementation;
- context-aware file views that hide dashboard-only shortcuts;
- aligned recent/favorites panel layout in desktop file views;
- password recovery with a production mail/reset flow;
- coarse RouterCloud backup status in the dashboard.

The browser drag-out-to-desktop experiment remains intentionally retired.
WebDAV is the supported two-way desktop transfer path.

## Live search and sorting

The current main file table can be filtered while the user types.

The live-search implementation:

- waits 250 ms after the last input event;
- reuses the existing JSON/AJAX list refresh path;
- does not reload the whole page;
- updates the browser query string with `history.replaceState`;
- restores the full directory listing when the search field is cleared;
- applies the current query immediately on Enter;
- keeps the right-hand `Ostatnie pliki` / `Ulubione` panel independent from
  filtered table results.

AJAX sorting uses the same refresh pipeline, so an active search query is kept
while sort/order changes are applied.

During a filtered result set, context actions from the independent recent-files
snapshot are intentionally not used against the filtered table indices.

## Favorites

Favorites are persistent application metadata exposed through the project-owned
RouterCloud API.

The UI supports:

- switching the right-hand dashboard panel between recent files and favorites;
- adding/removing favorites from the path context menu;
- removing favorites directly from the favorites panel;
- drag-and-drop source handles in the file table;
- a favorites-panel drop target with a clear `Upuść, aby dodać do ulubionych`
  overlay.

The main `Ulubione` tile is only a panel/navigation control. It is not a second
drop target for the same operation.

The production/UI evidence boundary for this feature is documented in
[the 2026-10-03 UI validation artifact](../evidence/2026-10-03/routercloud-ui-production-validation.md).

## File-view context

`Edit` and `View` pages expose only actions relevant to the selected file.

Dashboard navigation shortcuts such as `Ostatnio dodane` and `Ulubione` are
hidden in those file-specific views. The accepted desktop layout therefore keeps
the primary file actions together and avoids a second row of unrelated dashboard
navigation controls.

## Authentication and internal route namespace

RouterCloud uses the reserved application namespace:

```text
/__routercloud/login
/__routercloud/logout
/__routercloud/favorites
/__routercloud/password-reset/request
/__routercloud/password-reset/confirm
```

The leading double underscore is intentional. These are internal
application/control-plane routes, not user files or folders. Keeping them in a
reserved namespace reduces ambiguity with normal paths under the RouterCloud
data root.

Unauthenticated browser navigation uses the dedicated RouterCloud login flow.
Raw unauthenticated access to the protected root retains ordinary authentication
rejection semantics.

The login form accepts either the canonical RouterCloud username or a configured
email alias. The email address is not a second account: it resolves to the same
canonical DUFS user, so password state, permissions, password overrides and
session signing remain attached to that user. The production alias is configured
separately from password-recovery settings even when both values currently refer
to the same mailbox.

Authentication failures use the same generic response for username and email
attempts so the login flow does not expose which identifier exists.

## Password recovery

The production password-recovery flow was deployed and exercised end to end on
2026-10-03.

Security properties include:

- neutral reset-request behavior for syntactically valid addresses;
- reset token delivered in the URL fragment rather than the query string;
- token submitted only in the confirmation POST body;
- bounded reset-token lifetime and request cooldown;
- raw token not persisted as the stored verifier;
- persistent password override stored outside the served data root;
- SMTP credentials kept in a private router-side curl configuration;
- runtime session invalidation after a successful password change.

The authoritative production evidence is
[RouterCloud password recovery — production validation](../evidence/2026-10-03/routercloud-password-recovery-production-validation.md).

## Data and operation boundary

The RouterCloud service remains rooted at the dedicated RouterCloud SSD data
directory.

The browser does not gain access to router internals such as `/jffs`, `/etc` or
`/www`.

The production design preserves these controls:

- generic `allow-delete: false`;
- RouterCloud-specific delete authorization;
- independent RouterCloud edit authorization;
- same-parent rename without overwrite;
- symlink following disabled;
- bounded text edit size and atomic replacement;
- read-authorized selected ZIP streaming;
- LAN/Tailscale-only reachability;
- no direct WAN service exposure introduced by RouterCloud.

Frontend visibility is not authorization. The backend remains authoritative for
filesystem and application API operations.

## Backup and recovery

RouterCloud has two independent data-protection layers:

1. the live Personal Cloud sync workflow;
2. off-router versioned encrypted restic history.

The versioned backup uses a separate read-only SSH/rsync identity and a Fedora
staging mirror before restic writes to a separate local backup repository.

The staging mirror is not itself treated as the backup.

The documented retention, integrity-check and restore workflow is in
[RouterCloud — versioned encrypted backups](routercloud-versioned-backup.md).

Production frontend/backend changes are also deployed with separate rollback
copies outside the user-visible RouterCloud data root.

## Deployment model

RouterCloud frontend assets are deployed as a versioned external asset set
rather than by modifying the user data directory.

Material UI deployments follow this pattern:

1. update and validate repository source;
2. merge only after CI passes;
3. copy candidate assets to the router staging path;
4. verify feature markers/hashes before replacement;
5. back up the active asset files outside the served data root;
6. replace assets atomically;
7. restart RouterCloud when required so the external asset revision is
   recomputed;
8. perform the authoritative HTTPS/browser validation from Fedora.

The router is not treated as the authoritative client for its own VIP health
check because that path is not reliable in the reference environment.

## Implementation lineage

The final 2026-10-03 browser state was built through small reviewable changes:

- PR #161 — secure password-recovery frontend and production evidence;
- PR #162 — AJAX sorting;
- PR #163 — recent-panel top alignment;
- PR #164 — recent-panel bottom alignment;
- PR #165 — hide dashboard shortcuts on file views;
- PR #166 — move the favorites drag-and-drop target to the favorites panel;
- PR #167 — AJAX live search;
- PR #172 — username-or-email login UI.

The password-recovery backend is maintained in the project Dufs fork and was
merged separately there. The production password-recovery evidence records the
tested binary hash and source revision used for that rollout.

The email-login backend was merged separately in Dufs PR #2. It adds
configuration-only `routercloud-login-user` and `routercloud-login-email`
settings and resolves the configured email alias to the canonical account only
at the RouterCloud browser login endpoint.

## Production validation summary

Observed production acceptance on 2026-10-03 includes:

- password-recovery request/mail/reset/login flow PASS;
- password persistence after RouterCloud service restart PASS;
- current RouterCloud file-view/dashboard layout visually reviewed after
  deployment;
- file-view contextual shortcut cleanup accepted;
- AJAX sorting accepted in the production UI;
- live AJAX search accepted in the production UI;
- normal protected-root authentication behavior retained;
- canonical username login accepted after the email-login deployment;
- configured email alias accepted with the same password and mapped to the same account.

Repository CI also passed for each merged UI change before merge.

The favorites-panel drag-and-drop implementation is present on current `main`,
passed repository CI and was manually verified in the production browser on
2026-10-03. The observed flow successfully allowed a file/folder row to be
dragged onto the right-hand `Ulubione` panel and added to favorites. Revalidate
this gesture after a material browser/UI change.

## Current state

```text
RouterCloud HTTPS                     LIVE
LAN/Tailscale-only boundary           PRESERVED
Dedicated login/session auth          LIVE
Username login                         LIVE / MANUAL PASS
Email alias login                      LIVE / MANUAL PASS
Password recovery                     LIVE / E2E VALIDATED
Metro Polish UI                       LIVE
Upload file/folder                    LIVE
Create file/folder                    LIVE
AJAX sorting                          LIVE
AJAX live search                      LIVE
Recent files                          LIVE
Favorites                             LIVE
Favorites panel DnD                   LIVE / MANUAL PASS
Safe rename                           LIVE
Custom delete                         LIVE
Bounded text editing                  LIVE
Per-row download                      LIVE
Selected server-side ZIP              LIVE
WebDAV desktop workflow               LIVE
Versioned encrypted backup            COMPLETE (#138)
Generic allow-delete                  FALSE
Symlink following                     FALSE
Production rollback                   AVAILABLE
```

## Evidence boundary

This document describes the current source-controlled and deployed RouterCloud
state as of 2026-10-03.

It does not claim high availability, multi-user account recovery, public-WAN
exposure, immutable backups, browser support beyond the tested clients, or
long-term SMTP deliverability.

Features without a dedicated dated live artifact are described as implemented or
deployed rather than being promoted into stronger production-validation claims.
