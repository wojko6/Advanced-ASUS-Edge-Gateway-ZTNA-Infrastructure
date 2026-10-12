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
