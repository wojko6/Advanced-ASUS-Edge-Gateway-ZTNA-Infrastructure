# RouterCloud Metro Web v2

This directory contains the active RouterCloud Metro Web frontend.

Compatibility baseline:

    ../live-baseline/

Upstream reference:

    ../assets/

Rules:

- do not modify live-baseline;
- preserve Dufs backend/API semantics;
- preserve RouterCloud allow_move behavior;
- preserve safe same-directory rename semantics;
- preserve independent allow_delete gating;
- preserve storage information;
- preserve Polish localization;
- validate functionality before deployment to the router.

## Home navigation (ROUTERCLOUD_HOME_AJAX_V1)

- In a directory index, the Home tile and the root breadcrumb load `/?json`
  and update the directory list without a whole-page reload.
- Re-clicking Home on the unfiltered root restores the Recent panel and
  refreshes its listing via AJAX in production. Static preview does not request
  JSON because it only serves an HTML root snapshot.
- The original link remains the fallback in Edit/View pages, protecting
  the editor's unsaved document state.
- Home waits for active/queued/failed uploads to be resolved, including
  a second check after the JSON response.
- In-flight older directory-list AJAX responses cannot overwrite a
  completed Home transition (route epoch).
- Back/Forward deliberately reloads the destination to restore the correct
  directory snapshot (there is no general SPA router yet).
- Clicking Home restores the Recent panel (but never deletes saved Favorites).
  On cross-directory return Home, search, sort and archive selection are cleared.
- A failed Home fetch leaves the current view and URL unchanged.

Validation on Fedora, before packaging/deploying the ASUS ARMv7 binary:

```sh
node tests/test-routercloud-home-ajax.cjs
bash router/routercloud/webui/metro/build-preview.sh
```

Also manually verify root click (no document reload), subfolder -> Home,
favorites -> Home panel reset, upload-in-progress behavior, network-error
fallback and the browser Back/Forward path. The preview models the
initial root view only; nested-path navigation requires live API or a
mock JSON endpoint.

### Full browser navigation check (isolated subfolder fixture)

The regular Metro preview at port 8765 emulates **only the root directory**.
For a real browser check of the transition from a folder back to root, first
rebuild the static preview, then start the separate localhost-only fixture:

```sh
bash router/routercloud/webui/metro/build-preview.sh
node --check tests/routercloud-home-browser-preview.cjs
node tests/routercloud-home-browser-preview.cjs
```

Open `http://127.0.0.1:8766/Testowy/`. Click **Katalog główny**.
Expected: URL becomes `/`, the table changes from the single synthetic
`plik-testowy-z-podfolderu.txt` to the root preview list **without loading a new
HTML document**. The **Ulubione** panel should switch to **Ostatnio dodane**
when Home is clicked. Browser Back should return to `/Testowy/` (a reload
on Back is intentional). Use Ctrl+C to stop the fixture server.

The fixture only serves synthetic demo data and the static preview assets
on `127.0.0.1:8766`. It never connects to or modifies the ASUS router.
It does not replace final validation against the actual RouterCloud backend.
