# RouterCloud Home AJAX — production preflight (2026-10-12)

**Tracking:** draft PR #224. **Status:** automated tests and isolated browser acceptance PASS (operator reports); production compatibility PENDING. Nothing has been deployed.

## Critical production-only drift

On 2026-10-11 the storage-tile hotfix was applied directly to the active external RouterCloud `index.js`, without synchronizing its source to repository `main`. Both `main` and PR #224 still show "dostępne z", whereas live production should show "wolne", "łącznie" and "niedostępne". A direct copy of PR #224's current `index.js` would risk rolling this fix back.

**Gate:** before promotion reconcile *all* live-only differences, not merely the known three labels, and rerun tests on that reconciled artifact.

## Correct deployment scope

The current design loads external frontend assets from an `assets:` path in `/opt/etc/dufs-personal-cloud.yaml`. A dated 2026-10-11 record identifies `/opt/etc/init.d/S67routercloud` as the init script and `/opt/share/routercloud-password-recovery-20261003-163712` as the then-current directory. Reverify both before use.

The desired code change is **frontend-only** (`index.js`). It should not require rebuilding the Dufs ARMv7 executable or changing router auth, DNS, firewall, DHCP, Tailscale, or user-data storage. The active asset revision may be cached for a long period; inspect runtime/versioning behavior before claiming a no-restart deployment.

## Read-only production audit

Execute on an existing authorized **ASUS SSH shell**, not on Fedora. This prints no YAML contents, account credentials, cookies, IPs or tokens. It does not write, restart or deploy anything.

```sh
echo '=== ROUTERCLOUD HOME AJAX / READ-ONLY ==='
CONF=/opt/etc/dufs-personal-cloud.yaml
INIT=/opt/etc/init.d/S67routercloud

if [ -r "$CONF" ]; then
    echo 'ROUTERCLOUD_CONFIG=READABLE'
else
    echo 'ROUTERCLOUD_CONFIG=UNREADABLE'
fi

if [ -f "$INIT" ]; then
    echo 'ROUTERCLOUD_INIT=FOUND'
else
    echo 'ROUTERCLOUD_INIT=NOT_FOUND'
fi

ASSETS_DIR=''
if [ -r "$CONF" ]; then
    ASSETS_DIR="$(awk '
      /^[[:space:]]*assets:[[:space:]]*/ {
        sub(/^[[:space:]]*assets:[[:space:]]*/, "")
        gsub(/"/, "")
        sub(/[[:space:]]*$/, "")
        print
        exit
      }' "$CONF")"
fi
case "$ASSETS_DIR" in
    /*) echo 'ROUTERCLOUD_ASSETS_PATH=ABSOLUTE' ;;
    *) echo 'ROUTERCLOUD_ASSETS_PATH=UNRESOLVED'; ASSETS_DIR='' ;;
esac

if [ -n "$ASSETS_DIR" ] && [ -r "$ASSETS_DIR/index.js" ]; then
    JS="$ASSETS_DIR/index.js"
    echo 'ROUTERCLOUD_ACTIVE_INDEX=READABLE'
    printf 'ROUTERCLOUD_ACTIVE_INDEX_BYTES='
    wc -c < "$JS" | tr -d ' '
    printf 'ROUTERCLOUD_ACTIVE_INDEX_SHA256='
    sha256sum "$JS" | awk '{print $1}'
    for needle in wolne łącznie niedostępne ROUTERCLOUD_HOME_AJAX_V1; do
        if grep -Fq "$needle" "$JS"; then
            printf 'FEATURE_%s=PRESENT\n' "$needle"
        else
            printf 'FEATURE_%s=ABSENT\n' "$needle"
        fi
    done
else
    echo 'ROUTERCLOUD_ACTIVE_INDEX=UNREADABLE'
fi

echo 'ROUTERCLOUD_PRODUCTION_MODIFIED=NO'
echo '=== CHECK COMPLETE ==='
```

## Go/no-go requirements

1. The active asset path and JS hash must be observed, not inferred from dated docs.
2. The production-only storage fix must be preserved. Investigate unexpected markers.
3. Reconcile against the **actual active JS**, review the diff and rerun syntax, Node regression, static and subfolder browser tests.
4. Build a rollback copy outside the served RouterCloud data root, record before/after hashes, and define the trigger and method for reverting.
5. Check long-lived browser caching and whether a service restart is needed to recalculate the asset revision.
6. Validate the staged HTTPS UI from Fedora using normal TLS verification and login; never print sensitive session state.
7. No merge, activation, router file replacement or service restart without explicit approval.

## Verified / pending

- Fedora `node --check`, focused Home AJAX Node tests, static preview build: **PASS** (user output).
- Favorites -> Home restores Recent: **PASS** (user confirmation).
- Isolated subfolder -> Home -> Back: **PASS** (user confirmation).
- Router baseline hash/path: **PENDING**.
- Production-only drift reconciliation: **PENDING**.
- Rollback, asset cache/revision, live validation: **PENDING**.
- Production activation: **NOT DONE**.

## Read-only audit observed on ASUS (operator output)

On 2026-10-12 the operator reported:

- `ACTIVE_INDEX=READABLE`
- `ACTIVE_INDEX_BYTES=87783`
- `ACTIVE_INDEX_SHA256=d5052ea33917bad9314a49792bc555dd2e7ce2a3f2532aaff3b83c23e4c593b4`
- `FEATURE_wolne=PRESENT`
- `FEATURE_łącznie=PRESENT`
- `FEATURE_niedostępne=PRESENT`
- `FEATURE_ROUTERCLOUD_HOME_AJAX_V1=ABSENT`
- `PRODUCTION_MODIFIED=NO`

This proves the **presence of markers**, not complete parity with tracked
source. No claim is made about unknown changes without a full read-only diff.

## Fedora reconciliation gate (never edits the ASUS)

The scripts are part of draft PR #224 and run **on Fedora**:

```sh
cd ~/Projekty/routercloud-home-ajax-test
git pull --ff-only

# Supply the same router SSH target you normally use (SSH port defaults to 1122).
bash scripts/routercloud-home-fetch-live.sh admin1@ROUTER_HOST

python3 tests/test-routercloud-home-reconcile.py

python3 scripts/routercloud-home-reconcile.py \
  "$HOME/Archiwa/RouterCloud-Home-AJAX-20261012/production-index.js" \
  --out "$HOME/Archiwa/RouterCloud-Home-AJAX-20261012/index.candidate.js"
```

The fetch script parses the current YAML `assets:` path **on the router** but
streams bytes to Fedora over SSH (no remote writes). The local copy must match
the exact audited SHA-256 above; otherwise fail closed and re-audit.

The reconciliation script uses the pinned feature-branch base commit
`d68efba6c4e995408b63160893bed63a097e322c`. It permits only production
differences inside `setupStorageInfo()`, checks all three known storage labels,
and requires that the feature branch has not independently altered that function.
It does not overwrite tracked source, the exported live copy, or any existing
candidate. If it reports `REJECTED`, inspect the drift; **do not force a deploy**.

After `ROUTERCLOUD_RECONCILE=PASS`:

```sh
CANDIDATE="$HOME/Archiwa/RouterCloud-Home-AJAX-20261012/index.candidate.js"

node --check "$CANDIDATE"
ROUTERCLOUD_INDEX_JS="$CANDIDATE" node tests/test-routercloud-home-ajax.cjs
ROUTERCLOUD_PREVIEW_INDEX_JS="$CANDIDATE" \
  bash router/routercloud/webui/metro/build-preview.sh
```

Only after that: browse the local Metro preview; verify the storage tile still
reads `wolne`, `łącznie` and `niedostępne`, and repeat the Home behavior.
The actual backend/auth/cache and rollback acceptance remain separate gates.

Never paste the complete live JavaScript into a chat or commit it to GitHub
without inspecting its contents. The staged candidate under `~/Archiwa`
is **not** the deployed artifact.

## Candidate verification — 2026-10-12

Operator confirmed the reconciled **local Fedora** candidate:

- Candidate SHA-256 checked against `90171cdb676cb39de41a8e74384ac509294c617ae31a0b06735f5f7f527bcb0c`: **PASS**.
- `node --check` on the candidate: **JS_SYNTAX=PASS**.
- `ROUTERCLOUD_INDEX_JS=... node tests/test-routercloud-home-ajax.cjs`: **ROUTERCLOUD_HOME_AJAX_TEST=PASS**.
- Screenshots of the candidate preview show the old storage hotfix intact (`wolne`, `łącznie`, `zajęte`, `niedostępne`), and Favorites -> Home resets to Recent: **VISUAL PASS**.

**This is not evidence of production rollout.** The reconciled candidate is held off-router.
PR source file alone is still not the deployable artifact: it lacks the live-only storage change.

### Next gates

1. From Fedora, check the real RouterCloud asset response `Cache-Control`, `ETag` or other revision metadata, and observe the `index.js?v=...` URL in authenticated browser DevTools. Avoid sharing cookies/session headers.
2. Confirm the current external `assets:` path and that the active file SHA matches the audited value immediately before staging.
3. Prepare a versioned router-side rollback copy outside the served data root; verify its hash, intended cleanup and restoration commands.
4. If a service restart is necessary to update the asset revision, schedule that explicitly and test health before and after.
5. Production deployment/activation still needs specific operator approval. No RouterCloud restart or production modification occurred.


## Production cache evidence and revision model — 2026-10-12

Operator's read-only Fedora HEAD request for the production Dufs index.js returned:

| Response | Value |
| --- | --- |
| HTTP | 200 |
| Cache-Control | `public, max-age=31536000, immutable` |
| Last-Modified | `Sun, 11 Oct 2026 21:04:29 GMT` |
| ETag | `"1791752669527-87783"` |
| Content-Length | 87783 |
| Production modified | NO |

The live index.js is marked immutable for up to a year. Changed ETag/mtime
at the same URL does not force browsers to revalidate during freshness.

Code review: [project Dufs server](https://github.com/wojko6/dufs/blob/main/src/server.rs)
shows that compute_assets_revision hashes the external HTML, CSS, JS and
favicon contents and produces a 16-digit hexadecimal revision. Server::new
calculates it ONCE at startup; index HTML substitutes the cached revision
into the script URL parameter ?v=__ASSETS_REV__. Asset requests use
immutable caching. The source explains why a ROUTERCLOUD-ONLY service
restart is expected to be needed after a changed asset is installed;
no router reboot, DNS, Tailscale, or firewall restart is indicated.

### Rollout and rollback gates (design; not executed)

1. Confirm active assets directory, currently loaded version, live SHA and free disk.
2. Create a private dated backup of active JS outside the user data root;
   retain ownership, permissions and original SHA.
3. Stage ONLY the reconciled Fedora candidate with SHA-256
   `90171cdb676cb39de41a8e74384ac509294c617ae31a0b06735f5f7f527bcb0c`.
   Do not deploy the un-reconciled PR index.js (storage patch missing).
4. After explicit approval: validate staged hash, copy via same-filesystem
   temp file and atomic rename, then restart only S67routercloud.
5. From Fedora, confirm HTTPS with TLS verification, login, rendered new
   ?v revision, Home AJAX navigation, storage tile and file operations.
6. If needed, restore the private JS backup atomically, restart RouterCloud
   again to recover the original revision and repeat acceptance checks.

Runtime binary/source parity must still be checked in acceptance.
Changing a file without refreshing the server's revision risks clients
retaining a stale immutable URL. Deployment has NOT been authorized or done.

## Active browser asset revision — 2026-10-12

Fedora Chrome DevTools, on the authenticated production RouterCloud page,
reported:

- `ROUTERCLOUD_ASSETS_REV=503161dd5bee21ac`
- 16 lowercase hexadecimal characters: matches the project's hash revision format.
- Browser read-only inspection; no router file or service changes.

This is the *currently rendered* asset version, not proof that the
version matches every current on-disk asset byte. The previous
2026-10-11 storage hotfix changed external JS in place without a
service restart; the running Dufs instance calculates `assets_revision`
only at startup. Treat this token as the **before** baseline.

After an explicitly approved, UI-only deployment, verify the next
fresh HTML page advertises a DIFFERENT `?v=` token and that browser
fetches the JS from that new URL. A successful rollback should recover
the original JS bytes/hash and, following a RouterCloud-only restart,
the corresponding previous revision if the other hashed assets stay
unchanged. Because of the possible stale starting revision, do not
assume the post-rollback token must equal this observed value unless
startup-content hashes independently confirm it.

### Remaining no-change gate

Before staging: read the YAML `assets:` directory, verify active
`index.js` SHA256 is still
`d5052ea33917bad9314a49792bc555dd2e7ce2a3f2532aaff3b83c23e4c593b4`,
check disk free, current file ownership/mode and the init script path.
Do not print YAML or any credential-bearing files. No service restart
or file replacement until the operator approves a complete rollback plan.

## Final production filesystem preflight — 2026-10-12

Operator's router-side **read-only** checks establish:

- Active frontend folder: `/opt/share/routercloud-password-recovery-20261003-163712`.
- Active `index.js`: 87,783 bytes, root:root, regular file mode `0644`.
- Active SHA-256: `d5052ea33917bad9314a49792bc555dd2e7ce2a3f2532aaff3b83c23e4c593b4` (unchanged from audit).
- Disk-derived Dufs assets revision: `503161dd5bee21ac`.
- Browser-observed current assets revision: `503161dd5bee21ac` — **MATCH**.
- Filesystem: `/dev/sda1`, mounted on `/tmp/mnt/ENTWARE`, 60,955,772 KiB free (`df -k`), 2% used.
- `PRODUCTION_MODIFIED=NO`.

The live asset revision **currently agrees with the disk-derived hash**;
the earlier suspected stale browser revision has been ruled out for
the tested client and file set. This is a clean rollback/version
baseline. No backend executable change is necessary for Home AJAX.

### Next limited action — dedicated backup, no activation

Prepare a dated, private **copy of the active `index.js` outside the
RouterCloud served root** under the Entware SSD, verify its SHA-256
against the exact known-good hash, preserve the original file, and
record the resulting backup directory. Abort if the source hash has
changed, the destination already exists, or disk/permissions are
unexpected. This step writes only a separate rollback copy; it must
not overwrite live frontend files or restart the service.

**Important:** the reconciled candidate remains local on Fedora,
SHA-256 `90171cdb676cb39de41a8e74384ac509294c617ae31a0b06735f5f7f527bcb0c`.
The GitHub feature branch's `index.js` is **not** production-ready by
itself because it lacks the 2026-10-11 storage hotfix.

## Router-side rollback backup — 2026-10-12

Operator's ASUS SSH output after running the backup-only gate:

```text
BACKUP_VERIFICATION=PASS
LIVE_INDEX_UNCHANGED=YES
ROUTERCLOUD_RESTARTED=NO
```

Rollback location: `/opt/var/backups/routercloud-home-ajax-20261012/index.js`.
The original active external asset was not replaced. The backup creation
and hash check succeeded. Before restoration, independently recheck the
backup hash and ownership; backup existence alone does not validate a
future restore or guarantee that a service restart succeeds.

Next: transfer the locally reconciled and SHA-pinned candidate to a
separate private file in that same directory. This staging operation
must never touch the served asset or restart the service.

## Candidate staging — production remains inactive

After `BACKUP_VERIFICATION=PASS`, `LIVE_INDEX_UNCHANGED=YES`,
`ROUTERCLOUD_RESTARTED=NO`, use the separate Fedora staging script:

```sh
cd ~/Projekty/routercloud-home-ajax-test
git pull --ff-only
bash -n scripts/routercloud-home-stage.sh
read -r -p 'ASUS SSH IP/alias: ' ROUTER_HOST
bash scripts/routercloud-home-stage.sh "admin1@$ROUTER_HOST" 1122
```

The script checks the local file
`~/Archiwa/RouterCloud-Home-AJAX-20261012/index.candidate.js`
against the **pinned candidate SHA-256**
`90171cdb676cb39de41a8e74384ac509294c617ae31a0b06735f5f7f527bcb0c`
and 92809 bytes, verifies that both the router's live asset and private
rollback copy still match the **pinned original SHA-256**
`d5052ea33917bad9314a49792bc555dd2e7ce2a3f2532aaff3b83c23e4c593b4`,
streams the candidate via SSH, checks the transfer hash/size, and
promotes it to the **private staging filename only**:

`/opt/var/backups/routercloud-home-ajax-20261012/index.candidate.js`

It refuses to overwrite an existing staged file. It does NOT replace
the served `index.js`, restart RouterCloud, deploy the feature, or
perform a PR merge. Failure should be investigated, not bypassed.
Expected success markers: `LOCAL_CANDIDATE=PASS`,
`LIVE_AND_ROLLBACK_INTEGRITY=PASS`, `STAGING_VERIFICATION=PASS`,
`LIVE_INDEX_UNCHANGED=YES`, `ROUTERCLOUD_RESTARTED=NO`.

After staging, recheck hashes and permission/ownership boundaries;
the eventual activation and rollback are separate operator-approved
steps and require RouterCloud-only restart because of the immutable
asset caching/versioning contract.

## Staging acceptance and final read-only gate — 2026-10-12

Operator Fedora terminal after pulling feature branch:

```text
STAGING_SCRIPT_SYNTAX=PASS
LOCAL_CANDIDATE=PASS
LIVE_AND_ROLLBACK_INTEGRITY=PASS
STAGING_VERIFICATION=PASS
STAGED_BYTES=92809
LIVE_INDEX_UNCHANGED=YES
ROUTERCLOUD_RESTARTED=NO
STAGED_PATH=/opt/var/backups/routercloud-home-ajax-20261012/index.candidate.js
```

This verifies that the reconciled candidate has reached the private
router-side staging directory, while active frontend remains unchanged.
Production activation, restart, and backend E2E acceptance are PENDING.

### Final read-only gate

Run from Fedora after updating the feature branch:

```sh
cd ~/Projekty/routercloud-home-ajax-test
git pull --ff-only
sh -n scripts/routercloud-home-final-check.sh
ssh -T -p 1122 admin1@ROUTER_HOST 'sh -s' < scripts/routercloud-home-final-check.sh
```

This final script checks the exact active YAML assets path, original,
backup, and staged candidate hashes, required UI markers, and computes
the expected next 16-character asset revision by hashing the same
four assets as the project Dufs server with the candidate JS
substituted virtually. It performs no router writes or restarts.
Treat a STOP as a blocking failure; do not deploy around it.

**Important source-control issue still open:** the live-only storage
hotfix resides in the locally reconciled candidate, not yet in the PR
`index.js`. Synchronize the PR source with the audited candidate and
verify its exact SHA-256 before merging; do not deploy PR `index.js` as-is.

## Final activation preflight acceptance — 2026-10-12

The operator reported the following **read-only** verification, run
after staging the exact reconciled candidate on ASUS:

```text
FINAL_CHECK_SYNTAX=PASS
ASSET_SOURCE=PINNED
LIVE_INDEX_INTEGRITY=PASS
ROLLBACK_INTEGRITY=PASS
STAGED_CANDIDATE_INTEGRITY=PASS
STAGED_FEATURE_MARKERS=PASS
LIVE_ASSETS_REV=503161dd5bee21ac
EXPECTED_CANDIDATE_ASSETS_REV=a6b8ba062e194c1e
ROUTERCLOUD_INIT=FOUND
ACTIVE_FILES_MODIFIED=NO
ROUTERCLOUD_RESTARTED=NO
FINAL_PREFLIGHT=PASS
```

This confirms the current live/rollback/staged file hashes and
predicts a different cache-busting revision after a RouterCloud-only
restart. The predicted revision is **not yet observed in production**.

**Remaining source parity requirement:** the currently tracked PR
`router/routercloud/webui/metro/index.js` does not yet include the
production-only storage tile patch. Copy the *local, reconciled*
`index.candidate.js` to that tracked path only after verifying SHA-256
`90171cdb676cb39de41a8e74384ac509294c617ae31a0b06735f5f7f527bcb0c`
and a clean feature branch, then rerun syntax, regression and diff
checks before committing/pushing. The private production dump itself
should not be committed to GitHub; only the reviewed, reconciled,
JavaScript frontend source should be tracked.

**Status:** not merged, no production file replacement, no service
restart. Explicit operator approval remains mandatory for activation.

## Approved controlled activation — 2026-10-12

The operator explicitly approved production activation of the frontend-only
Home AJAX update after all candidate, rollback and revision gates passed.
Project CI for the previous commit 7a87990 was green (Validation suite).

To avoid an unreviewed manual sequence, two **operator-executed** RouterCloud-
only scripts were added and are subject to CI/static validation:

- `scripts/routercloud-home-activate.sh`: on-router pinned source, backup
  and staged-candidate SHA-256 gates; YAML asset path and old version
  checks; atomic same-filesystem `index.js` switch with original
  root:root/0644 file metadata; RouterCloud-only S67routercloud restart;
  post-restart hash/revision check; rollback attempt via `trap` on any
  non-success after file replacement.
- `scripts/routercloud-home-rollback.sh`: manual restore from the
  independently checked rollback copy, same-filesystem atomic replacement
  and RouterCloud-only restart; blocks unknown active versions.

**Operator command after CI passes, from Fedora:**

```sh
cd ~/Projekty/routercloud-home-ajax-test
git pull --ff-only
sh -n scripts/routercloud-home-activate.sh
sh -n scripts/routercloud-home-rollback.sh
ssh -T -p 1122 admin1@192.168.50.1 'sh -s' < scripts/routercloud-home-activate.sh
```

The restart may interrupt RouterCloud briefly. No firmware, router reboot,
Pi-hole, firewall, DNS Guard or Tailscale change is intended. The SSH
transport is for the operator; this GitHub documentation update is not
a remote deployment.

**Expected activation markers:** `RECHECK_LIVE_AND_ROLLBACK=PASS`,
`RECHECK_STAGED_CANDIDATE=PASS`,
`EXPECTED_NEW_ASSETS_REV=a6b8ba062e194c1e`,
`ACTIVE_INDEX_SWITCH=PASS`, `ROUTERCLOUD_RESTART_COMMAND=PASS`,
`LIVE_ASSETS_REV=a6b8ba062e194c1e`, `ACTIVATION=PASS`.
Basic process/HTTP health is still separate from this command. **Final
Fedora/browser acceptance** must check genuine HTTPS certificate
validation, login, `index.js?v=a6b8ba062e194c1e`, Home AJAX
(Favorites -> Home -> Recent and subfolder -> Home -> Back),
storage metrics, upload/download and relevant service logs.

If the activation command returns an error after file replacement,
its exit trap attempts automatic rollback. Read **all markers** before
any additional operation. If production browser acceptance later fails
(despite `ACTIVATION=PASS`), run this operator-only rollback command:

```sh
ssh -T -p 1122 admin1@192.168.50.1 'sh -s' < scripts/routercloud-home-rollback.sh
```

After rollback, expect the original live hash
`d5052ea33917bad9314a49792bc555dd2e7ce2a3f2532aaff3b83c23e4c593b4`
and original asset revision `503161dd5bee21ac`.

**Status at document creation:** scripts prepared, not executed,
production not changed or restarted; PR #224 still Draft and not merged.
