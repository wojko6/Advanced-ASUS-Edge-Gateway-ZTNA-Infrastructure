# RouterCloud Metro — File View UX v1.0: design and rollout plan

Date: 2026-10-12  
Tracking: [issue #225](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/225)  
Stable baseline: merged Home AJAX [PR #224](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/224) (squash commit `0021ba3c0a193d74ce3baaa4db3897dfb2eec4c3`)  
Development: `feat/routercloud-file-view-ux-v1`

## Intent

Improve **single-file** View and Edit presentation with the existing rectangular Metro tile identity.
Keep the folder/index dashboard, storage metrics, favorites, search, Home AJAX,
login/session, file permissions and backend unchanged.

## Baseline source audit

- Metro currently uses `index.html` plus `index.css` and `index.js`; View and Edit routes
  share `.editor-page` and execute `setupEditorPage()`.
- `index.html` places `.dashboard-storage` and `.dashboard-aside` in the
  common `.head` container. The storage label is visible even if
  `.storage-info` has no data; the Recent side panel can be empty.
- Actions on View/Edit: Home, download, and — only for authorized editable
  text — Save and Discard. Their behavior must not change.
- The project's Dufs `EditData` returned for file routes contains
  `href`, `kind`, `uri_prefix`, `editable`, capability flags,
  `auth`, `user`, but **no file `size` or `mtime`**. Do not fabricate
  those values or assume listing metadata is available in the file route.
  Display filename, extension/type (derived), file location (derived
  from URL) and View/Edit state first. Add size/mtime only if genuinely
  available via an authorized, separately tested frontend-only request.
- Existing inline PDF iframe and editable TXT path must be preserved.
  Supported image preview (e.g. `.ico`, PNG, JPEG, WebP) is a separate
  gated enhancement with a graceful non-image fallback.

## Proposed incremental implementation

### Stage A — isolated View/Edit layout

1. Add a View/Edit-only mode marker after DOM ready; never modify directory mode.
2. Hide the empty storage section for file routes, suppress irrelevant search,
   and compact **only file-mode** action tiles while retaining 44 px touch
   targets, visible focus ring, keyboard access and sharp edges.
3. Replace the side panel's empty Recent presentation with an accessible
   `Informacje o pliku` section using textContent, never untrusted HTML.
4. Verify TXT read-only/editable behavior, PDF iframe rendering, binary fallback;
   make no changes to file save/discard handlers or permission checks.

### Stage B — image preview

1. Permit a small explicit extension allowlist (ICO, PNG, JPG/JPEG, GIF,
   WEBP, SVG only after security review); use a safe `img` URL and error
   fallback. Do not add cross-origin conversion, uploaded preview files or
   externally fetched scripts.
2. Keep PDF iframe and text editor paths unchanged; test direct authenticated
   file access, missing file, unsupported format and no capability escalation.
3. Consider `Content-Type` and `Content-Disposition` as part of the
   acceptance; URL extension alone is not proof that bytes form an image.

### Stage C — regression and handoff

- Generate deterministic View/Edit fixtures for Fedora localhost; do not
  rely on the index-only `build-preview.sh` to represent a file view.
- Run JS syntax, static checks, test fixtures, visual desktop/mobile checks,
  browser Home AJAX regression and GitHub Actions `Validation suite`.
- Preserve production baseline: `index.js` SHA256
  `90171cdb676cb39de41a8e74384ac509294c617ae31a0b06735f5f7f527bcb0c`,
  assets revision `a6b8ba062e194c1e`. Keep rollout, cache-busting revision and
  rollback separate from the design phase.
- **NO ASUS modifications, no service restart, no merge** during local UX
  development; obtain approval for any new production deployment.

## Acceptance / out-of-scope

**Accept:** file page header uses space purposefully, file details derive only
from trusted delivered data, empty storage and Recent clutter disappear,
mobile layout is usable, all existing permissions and file operations retain
their behavior.

**Out of scope:** main dashboard visual redesign, API additions, metadata
invention, changing authentication/edit policies, router changes, new storage
services or a Dufs ARMv7 rebuild.

## Stage A v2 — editor-adjacent file information

User reviewed localhost TXT file-view screenshot and identified a large
vertical dead zone between compact action tiles and the text editor.
Root cause: the file details side-panel and action tiles occupied the same
CSS grid row in `.head`; the taller aside dictated the row's height, pushing
the whole `.main` editor below the aside even though tiles were short.

Revision, **isolated branch only**:

- `setupRouterCloudFileViewUx()` moves the existing `.dashboard-aside`
  DOM node **only for Edit/View routes** into `.editor-page`, after
  populating file information; Index DOM/layout remains untouched.
- The single-file `.head` now has breadcrumb and action rows only;
  `margin-bottom: 14px` eliminates the visual dead zone.
- `.editor-page` is a two-column grid: left preview/editor, right
  `Informacje o pliku`; alignment, dimensions and 16px gutter
  mirror the existing Metro column ratio.
- Responsive rule <=820px stacks content first, metadata second.
- `iframe` PDF, `.editor` textarea and `.not-editable` fallback all
  occupy the same left `preview` grid area. Existing edit permissions
  and save/discard callbacks stay unchanged.
- Added `tests/test-routercloud-file-view-layout.cjs` as a
  source-level regression for route scope, node relocation, layout
  and lack of invented size/mtime.

**Local Fedora verification** from the UX branch:

```sh
cd ~/Projekty/routercloud-home-ajax-test
git pull --ff-only
node --check router/routercloud/webui/metro/index.js
node tests/test-routercloud-file-view-layout.cjs
bash router/routercloud/webui/metro/build-preview.sh
# If the existing localhost fixture at port 8767 is still running,
# it serves the rewritten preview files automatically.
curl -fsS -o /dev/null -w 'FILE_VIEW_HTTP=%{http_code}\n' \\
  'http://127.0.0.1:8767/demo.txt?view'
```

Manual browser acceptance required: TXT at 127.0.0.1:8767/demo.txt?view
has its editor directly under actions; PDF and unsupported ICO layouts
do not leave a header gap; information panel aligns beside preview on
desktop and below on mobile. No production writes/restarts.

## Desktop visual review — details card height

The user supplied a Fedora localhost screenshot of
`http://127.0.0.1:8767/demo.txt?view` after the no-gap v2 layout.
**Visual result:** text editor starts immediately under compact
four-tile actions; desktop file info panel aligns beside the editor.
The previous blank vertical track between actions and textarea has
been eliminated.

Follow-up issue: the existing global `.dashboard-aside` styling
specified `align-self: stretch`, making the file info card as tall
as the editor. File-mode scoped override
`body.routercloud-file-view .editor-page > .dashboard-aside`
now sets `align-self: start` to keep the card's content height.
Added a static regression assertion to
`tests/test-routercloud-file-view-layout.cjs`.

**Next:** run the updated static test, rebuild the isolated Metro
preview on Fedora, refresh the localhost fixture, and visually confirm
the compact details card. PDF and ICO rendering still require
dedicated acceptance; production ASUS is untouched.

## Stage B — native image preview prototype

TXT layout after the metadata-height change: user supplied screenshot
showing compact four action tiles, editor immediately below and metadata
card ending at its own content height (no vertical stretching).
Accepted as the stable File View layout for image previews.

Implemented on draft PR #226 (not on ASUS):

- Native `<img>` preview in `View` routes for ICO, PNG, JPEG, WebP, GIF
  and BMP. The decoder gets the same-origin direct file URL; no
  third-party conversion or object URL and no extra API permissions.
- Supported format extensions are explicitly allowlisted. SVG stays
  in its pre-existing sandboxed iframe path pending separate security
  review. PDF/video/audio retain their existing iframe handling.
- An `error` event removes the failed image and displays a localized
  non-empty fallback (`Nie udało się wyświetlić obrazu. Możesz pobrać plik.`).
- Visuals use a bounded contain-sized image within Metro dark/bordered
  viewport next to the compact file detail card; index dashboard unaffected.
- Loopback fixture at port 8767 now provides a real 24x24 PNG, original
  ICO favicon, corrupt PNG failure example, TXT and PDF placeholder.
- Dedicated Node test simulates the image DOM and error callback without
  network or browser. GitHub Actions `Validation suite` includes JS
  syntax, prior Home AJAX, file layout and native image regressions.

Post-pull Fedora commands:

```sh
cd ~/Projekty/routercloud-home-ajax-test
git pull --ff-only
node --check router/routercloud/webui/metro/index.js
node --check tests/routercloud-file-view-preview.cjs
node tests/test-routercloud-home-ajax.cjs
node tests/test-routercloud-file-view-layout.cjs
node tests/test-routercloud-file-image-preview.cjs
bash router/routercloud/webui/metro/build-preview.sh
# Restart existing localhost port 8767 fixture to load the new PNG routes.
node tests/routercloud-file-view-preview.cjs
```

Manual browser checks: open localhost `favicon.ico?view`,
`pixel.png?view`, `broken.png?view`, `demo.txt?view`,
`report.pdf?view`. Confirm decoding and fallback; browser HTML preview
success is not a production media acceptance. Do not attempt TXT
save within GET-only localhost fixture; its save route is simulated.

**Pending:** CI result, user screenshots/acceptance, responsive widths,
real backend Content-Type/Content-Disposition audit prior to deploy.
No ASUS changes, cache revisions or service restart in this phase.
