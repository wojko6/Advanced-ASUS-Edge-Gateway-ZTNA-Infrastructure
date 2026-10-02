# RouterCloud Metro production checkpoint — 2026-10-02

## Status

RouterCloud Metro Web is live on the reference ASUS TUF-AX5400 deployment at the production HTTPS endpoint. This checkpoint records the browser/frontend and project-patched Dufs behavior that was live-validated before closing the current UI implementation phase.

The production deployment remains rooted at the dedicated RouterCloud storage directory on the SSD and preserves the existing LAN/Tailscale-only trust boundary. No WAN exposure is introduced by this UI work.

## Final user-facing scope

The deployed Metro interface includes:

- dark Metro-style RouterCloud branding;
- dedicated RouterCloud cloud/home/Wi-Fi product icon;
- the same brand icon in the main header, login screen and browser favicon;
- Polish login and file-management UI;
- storage-capacity summary;
- search;
- upload of files and folders;
- create-folder and create-file actions;
- file viewing and bounded text editing;
- safe same-directory rename;
- dedicated custom delete path while generic Dufs delete remains disabled;
- per-row download;
- checkbox selection for files and folders;
- select-all / clear-all from the table header;
- server-side ZIP download containing only the selected items;
- preserved directory hierarchy, including selected empty directories;
- browser-to-RouterCloud drag-and-drop upload;
- live file-list refresh after successful upload;
- WebDAV as the supported desktop integration path for two-way file/folder transfer.

Browser drag-out to the desktop is intentionally not part of the final design. GNOME treated the browser remote URL as an HTML/web resource rather than as the intended file transfer, so WebDAV remains the supported desktop workflow.

## Selected archive behavior

The selected archive action is implemented as a RouterCloud-specific read action carried by POST.

Key properties:

- the request accepts a bounded form body containing the selected relative paths;
- the action requires archive capability;
- each selected path is validated as a normal relative path;
- absolute paths, empty paths, dot components, parent traversal and NUL input are rejected;
- the top-level selection is deduplicated;
- access is checked with read semantics for every selected path;
- root containment is enforced when symlinks are disabled;
- selected top-level hidden entries are denied;
- selected objects must resolve to regular files or directories;
- output is streamed server-side rather than buffered in browser JavaScript;
- directory structure is preserved;
- selected empty directories are represented in the ZIP;
- unrelated, unselected files are not included.

The archive name follows the RouterCloud convention:

`<current-directory>-zaznaczone.zip`

## Authentication and authorization

RouterCloud keeps the dedicated session-auth path introduced by the project-patched Dufs build.

Browser behavior:

- unauthenticated browser HTML navigation is redirected to the RouterCloud login page;
- non-browser/raw unauthenticated requests continue to receive ordinary authentication rejection semantics;
- successful login creates the secure RouterCloud session cookie;
- the cookie remains scoped by host/path rules and is not tied to a TCP port.

The selected archive endpoint authenticates the real HTTP request method while authorizing the filesystem operation with GET/read semantics. This avoids weakening normal POST/write authorization and preserves Digest correctness.

## File operation boundary

The production configuration intentionally keeps generic destructive Dufs semantics disabled:

`allow-delete: false`

RouterCloud-specific operations are separately gated:

- custom delete: enabled only through the RouterCloud path;
- text edit/save: independently gated;
- safe rename: same-parent only and no overwrite;
- symlink following: disabled;
- archive: enabled.

The frontend does not grant capabilities by itself. Backend authorization remains authoritative.

## Text editing

RouterCloud text editing is bounded and isolated from generic overwrite behavior.

Validated properties include:

- existing regular-file requirement;
- symlink refusal;
- text-content check;
- 4 MiB maximum;
- temporary file followed by atomic replacement;
- existing permissions retained;
- generic PUT overwrite remains governed by the normal Dufs delete/overwrite policy.

New unsaved text drafts are removed when discarded. Once saved, the draft marker is cleared so later discard does not delete the persisted file.

## Branding checkpoint

The accepted production branding uses the cloud/home/Wi-Fi RouterCloud icon in three places:

1. main RouterCloud header;
2. RouterCloud login screen;
3. browser favicon.

The final desktop sizing accepted during visual review is:

- main header icon: 96 px;
- login icon: 118 px.

Responsive mobile rules keep a smaller proportional mark.

## Live acceptance completed

The final implementation was exercised on the ARMv7 router build before and after production deployment.

Validated behavior included:

- ARMv7 static candidate build;
- full Rust test suite PASS;
- `cargo check` PASS;
- source worktrees clean after commits;
- isolated candidate listener on TCP/8444;
- production listener on dedicated RouterCloud TCP/443 remained healthy during smoke work;
- mixed file + folder selected ZIP;
- Unicode filename handling;
- folder hierarchy preservation;
- selected empty-folder preservation;
- exclusion of unselected files;
- header select-all / clear-all;
- inactive selected-ZIP tile when nothing is selected;
- active selected-ZIP action when one or more items are selected;
- custom branding on main UI and login screen;
- browser favicon update;
- production backend SHA matched the tested candidate;
- final production asset deployment completed with backup/rollback protection;
- final browser visual acceptance on `https://cloud.home.arpa/`.

## Rollback model

Backend and frontend were deployed as separate material changes.

Before production replacement:

- the live RouterCloud binary was backed up;
- frontend assets were backed up outside the served RouterCloud data root;
- staged file hashes were verified before replacement;
- replacement used same-filesystem temporary files followed by rename;
- the RouterCloud service was restarted and the dedicated listener/process rechecked;
- Fedora performed the authoritative HTTPS health check because the router cannot reliably curl its own RouterCloud alias.

The persistent backup area remains outside the user-visible RouterCloud served directory.

## Desktop integration

WebDAV is the accepted desktop integration mechanism.

Live two-way tests covered:

- RouterCloud/WebDAV -> desktop file transfer;
- RouterCloud/WebDAV -> desktop folder transfer;
- desktop -> RouterCloud/WebDAV file transfer;
- desktop -> RouterCloud/WebDAV folder transfer.

The direct GNOME mount remains:

`davs://cloud.home.arpa/`

## Final implementation state

This checkpoint closes the current RouterCloud Metro browser phase with the following production state:

```text
RouterCloud HTTPS                     LIVE
Dedicated login/session auth          LIVE
Metro dark UI                         LIVE
Polish UI                             LIVE
RouterCloud product branding          LIVE
Main logo 96 px                       LIVE
Login logo 118 px                     LIVE
Custom favicon                        LIVE
Upload file/folder                    LIVE
Create file/folder                    LIVE
Search                                LIVE
Safe rename                           LIVE
Custom delete                         LIVE
Bounded text editing                  LIVE
Per-row download                      LIVE
Selected server-side ZIP              LIVE
Empty-directory ZIP preservation      LIVE
Select-all / clear-all                LIVE
WebDAV two-way desktop workflow       LIVE
Browser drag-out                      INTENTIONALLY RETIRED
Generic allow-delete                  FALSE
Symlink following                     FALSE
LAN/Tailscale trust boundary          PRESERVED
Production backup/rollback            AVAILABLE
```

Future work should treat this state as the RouterCloud Web compatibility baseline rather than restarting from stock Dufs UI assumptions.
