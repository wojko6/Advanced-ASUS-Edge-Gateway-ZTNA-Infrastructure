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
