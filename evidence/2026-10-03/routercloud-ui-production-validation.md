# RouterCloud UI — production validation notes (2026-10-03)

## Scope

This artifact records the bounded production/UI observations made while the
2026-10-03 RouterCloud frontend refinements were deployed.

It complements, rather than replaces, the separate
[password-recovery production validation](routercloud-password-recovery-production-validation.md).

No passwords, cookies, reset tokens, SMTP credentials, private file contents or
private infrastructure identifiers are included.

## Source-control sequence

The following frontend/infrastructure changes were merged to `main` after the
repository validation workflow completed successfully:

- PR #162 — AJAX sort;
- PR #163 — align the recent-files panel at the top in desktop file views;
- PR #164 — align the panel bottom edge;
- PR #165 — hide dashboard-only shortcuts in `Edit` / `View`;
- PR #166 — use the right-hand favorites panel as the drag-and-drop target;
- PR #167 — AJAX live search.

The changes were intentionally separated into small pull requests so layout,
navigation and AJAX behavior could be reviewed and rolled back independently.

## Deployment method

Frontend changes were staged outside the active asset names, checked for
expected source markers, backed up, moved into the configured external
RouterCloud asset directory and followed by a RouterCloud service restart where
needed.

The authoritative visual/application check was performed from the Fedora client
through `https://cloud.home.arpa/`.

The reference deployment uses external versioned assets, so restarting the
service after material asset replacement ensures the served asset revision is
recomputed.

## Observed results

### AJAX sorting

The production table sorting change was deployed and accepted in the browser
without requiring a full-page reload.

Result:

```text
ROUTERCLOUD_AJAX_SORT=PASS
```

### Recent/favorites panel layout

The production file view was visually checked after the desktop alignment
change.

The right-hand RouterCloud panel starts at the same top row as the action tiles.
The subsequent bottom-edge adjustment removed the fixed minimum-height behavior
for the hidden-search desktop layout so the panel follows the grid height.

Result:

```text
ROUTERCLOUD_RECENT_PANEL_ALIGNMENT=PASS
```

The validation is a browser visual acceptance, not a pixel-perfect automated
screenshot assertion.

### Context-aware file views

After deployment, `Edit` / `View` no longer show the dashboard-only
`Ostatnio dodane` and `Ulubione` shortcut tiles.

The file-specific actions remain visible.

Result:

```text
ROUTERCLOUD_FILE_VIEW_CONTEXT=PASS
```

### AJAX live search

The live-search change was deployed to the production RouterCloud assets and
accepted in the browser.

Observed user-visible behavior:

- results change while typing;
- the page does not perform a full navigation/reload;
- clearing the search restores the unfiltered listing;
- the right-hand panel remains independent from the filtered table.

Result:

```text
ROUTERCLOUD_LIVE_SEARCH=PASS
```

## Favorites panel drag-and-drop

PR #166 changes the drag-and-drop target from the green `Ulubione` shortcut tile
to the right-hand panel that actually displays favorites.

The source change and repository CI are complete. The feature was also manually
verified in the production browser on 2026-10-03.

Observed behavior:

- a file/folder row could be dragged from the main table;
- the right-hand `Ulubione` panel accepted the drop;
- the item was added to favorites;
- the green `Ulubione` shortcut tile remained only a navigation/panel switch
  rather than a duplicate drop target.

Result:

```text
FAVORITES_PANEL_DND=PASS
```

This is a manual browser acceptance for the tested production UI. Revalidate
after a material browser, drag-and-drop or favorites implementation change.

## Authentication regression boundary

The UI deployments did not intentionally change the dedicated authentication
contract.

The protected RouterCloud root continued to use the expected unauthenticated
authentication response, while the separate password-recovery artifact records
the real login/reset/restart sequence.

## Result summary

```text
ROUTERCLOUD_AJAX_SORT=PASS
ROUTERCLOUD_RECENT_PANEL_ALIGNMENT=PASS
ROUTERCLOUD_FILE_VIEW_CONTEXT=PASS
ROUTERCLOUD_LIVE_SEARCH=PASS
FAVORITES_PANEL_DND=PASS
PASSWORD_RECOVERY_E2E=SEE_SEPARATE_EVIDENCE
```

## Evidence boundary

This is a bounded UI/deployment record. It does not establish long-term browser
compatibility, performance under very large directory listings, concurrent
multi-user behavior, or WAN exposure.

Repository CI and manual browser acceptance are separate evidence layers and are
not treated as substitutes for one another.
