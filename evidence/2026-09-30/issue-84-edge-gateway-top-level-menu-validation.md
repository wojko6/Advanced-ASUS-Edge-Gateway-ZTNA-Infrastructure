# Issue #84 — Edge Gateway top-level menu validation

**Status:** PASS  
**Date:** 2026-09-30  
**Evidence class:** Live functional validation / sanitized  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton

## Purpose

Validate promotion of the project-native Edge Gateway page from an
Administration sub-tab to a standalone left-side item under Advanced Settings,
without changing the page's read-only operational scope.

Target order:

```text
Firewall
Edge Gateway
Administration
System Log
Network Tools
```

The implementation reuses the stock but otherwise unused `menu_Dashboard`
CSS icon class and does not add another firmware CSS patch.

## Initial live test and rollback

The first staged implementation failed during live mount because GNU awk treats
`index` as a built-in function name and rejected it as a `-v` variable.

Observed failure:

```text
awk: fatal: cannot use gawk builtin `index' as variable name
ERROR: Administration menu anchor not found exactly once
PR145_MOUNT=FAIL — rolling back
```

The rollback path completed successfully and restored the previously validated
Administration-tab layout:

```text
Polish WebUI overlay active
Mounted Edge Gateway as user1.asp
URL: /user1.asp
ROLLBACK_ATTEMPTED
```

The implementation was corrected to use `menu_index`, and a static regression
guard was added so the incompatible variable name cannot return unnoticed.

## Second live mount

The corrected staged helper passed shell syntax validation and mounted
successfully without a router reboot:

```text
PR145_MOUNT=PASS
```

Active menu inspection showed:

```text
index: "menu_Firewall"
/* ASUS-EDGE-MENU-BEGIN */
menuName: "Edge Gateway",
index: "menu_Dashboard",
{url: "user1.asp", tabName: "Edge Gateway"},
/* ASUS-EDGE-MENU-END */
index: "menu_Setting",
```

Validation counters were:

```text
EDGE_INDEX_COUNT=1
EDGE_MENU_NAME_COUNT=1
```

The two textual appearances of `Edge Gateway` inside the block are intentional:
one is the menu name and one is the page tab name. There is exactly one
standalone menu object.

## Visual validation

A hard browser refresh showed Edge Gateway as a distinct left-side Advanced
Settings menu item between Firewall and Administration.

Selecting the item opened the existing project-native Edge Gateway dashboard
normally, with the read-only Phase 3 operational sections still rendering.

## Persistent installation

The corrected, live-tested helper was copied to:

```text
/jffs/addons/asus-edge/bin/webui-mount
```

A rollback copy of the prior helper was preserved under the project backup
directory before replacement.

File comparison reported:

```text
PERSISTENT_SCRIPT=PASS
```

A full project health check immediately after the persistent replacement
completed with:

```text
Summary: 0 failure(s), 0 warning(s)
```

## Controlled reboot validation

After a controlled router reboot, Edge Gateway returned automatically as
`user1.asp`.

Post-reboot menu state:

```text
index: "menu_Firewall"
/* ASUS-EDGE-MENU-BEGIN */
menuName: "Edge Gateway",
index: "menu_Dashboard",
{url: "user1.asp", tabName: "Edge Gateway"},
/* ASUS-EDGE-MENU-END */
index: "menu_Setting",
```

Post-reboot counters:

```text
EDGE_INDEX_COUNT=1
EDGE_MENU_NAME_COUNT=1
```

The Polish WebUI overlay remained active and reported the expected validated
hashes for all eight managed firmware resources. The active menu tree remained:

```text
menuTree=polish
```

The scheduled Edge Gateway status refresh also returned automatically:

```text
* * * * * /jffs/addons/asus-edge/bin/webui-status >/dev/null 2>&1 #AsusEdgeWebUIStatus#
```

The final post-reboot project health check completed with:

```text
Summary: 0 failure(s), 0 warning(s)
```

The accepted health set included firewall serialization and managed-chain
integrity, Tailscale connectivity and netfilter ownership, exit-node
prerequisites, LAN classic-DNS and DoT enforcement, IPv6 fail-closed guards,
printer exposure controls, Unbound runtime/control reachability, direct Unbound
DNSSEC validation and syslog-ng runtime state.

## Result

**PASS.**

The Edge Gateway WebUI is live-validated as a standalone Advanced Settings
left-menu item with:

- clean migration from the prior Administration-tab placement;
- one project-owned menu object;
- stock `menu_Dashboard` icon reuse;
- successful rollback from a real mount-time compatibility failure;
- live remount without reboot;
- visual confirmation;
- persistent installation;
- automatic post-reboot restoration;
- preserved Polish WebUI overlay;
- preserved scheduled status refresh;
- final project health check at 0 failures / 0 warnings.

## Claim boundary

This evidence validates menu integration and persistence only.

It does not add or validate new configuration write actions, service restart
controls, Personal Cloud, backup management, Grafana/Pi-hole portal links or
other future management features proposed in issues #84 and #141.
