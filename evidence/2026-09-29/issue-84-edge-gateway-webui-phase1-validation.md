# Issue #84 — Edge Gateway WebUI Phase 1 validation

**Status:** PASS  
**Date:** 2026-09-29  
**Evidence class:** Live functional validation / sanitized  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton

## Purpose

Validate the first project-native ASUS Edge Gateway WebUI implementation as a
read-only operational surface without changing the existing DNS, Tailscale or
firewall architecture.

The implementation uses the Merlin Addons API pattern only as a mounting
mechanism. The upstream Unbound-Merlin-UI project remains a reference, not a
runtime dependency.

## Phase 1 scope

The deployed page exposes read-only status for:

- router model and firmware;
- IPv6 firmware service state;
- WAN WebUI state;
- LAN management access restriction state;
- dnsmasq process state;
- Unbound process state;
- firmware DNSSEC flag, explicitly not treated as proof of the project Unbound
  DNSSEC state;
- tailscaled process state;
- WebUI operating mode.

The page contains no Apply action, configuration write path or service restart
control.

## Manual mount validation

The project helper successfully mounted the page through the Merlin Addons API:

```text
Mounted Edge Gateway as user1.asp
URL: /user1.asp
```

Runtime inspection confirmed:

```text
page=user1.asp
{url: "user1.asp", tabName: "Edge Gateway"},
tmpfs on /www/require/modules/menuTree.js type tmpfs (rw,relatime)
```

The page rendered inside the native ASUSWRT interface with the normal left-side
menu and showed the expected selected service/security state.

## Rollback validation

The helper was exercised through a full manual rollback and remount cycle:

```text
=== UNMOUNT ===
Unmounted Edge Gateway

=== AFTER UNMOUNT ===
page=untracked

=== REMOUNT ===
Mounted Edge Gateway as user1.asp
URL: /user1.asp

=== FINAL STATUS ===
page=user1.asp
{url: "user1.asp", tabName: "Edge Gateway"},
tmpfs on /www/require/modules/menuTree.js type tmpfs (rw,relatime)
```

This confirms that the runtime page and menu integration can be removed and
recreated without a router reboot.

## Persistent installation

The project installer was updated to deploy:

- `/jffs/addons/asus-edge/bin/webui-mount`;
- `/jffs/addons/asus-edge/webui/EdgeGateway.asp`.

The installer snapshots the WebUI directory for rollback. The managed
`services-start` path mounts the WebUI as an optional operation and does not
treat a WebUI mount failure as a required network-service failure.

The uninstall path invokes the WebUI unmount helper before restoring managed
hooks.

A controlled installer run completed successfully and created a new rollback
snapshot before live changes.

## Controlled reboot validation

After a controlled router reboot, normal Internet connectivity returned and the
WebUI reappeared without a manual mount command.

Post-reboot runtime state:

```text
=== WEBUI STATUS ===
page=user1.asp
{url: "user1.asp", tabName: "Edge Gateway"},
tmpfs on /www/require/modules/menuTree.js type tmpfs (rw,relatime)
```

The router log independently recorded automatic startup integration:

```text
asus-edge: Edge Gateway WebUI mounted
```

The project health check was then run after the reboot and completed with:

```text
Summary: 0 failure(s), 0 warning(s)
```

The validated health set included the project firewall chains and ordering,
Tailscale connectivity and intentional netfilter ownership, exit-node forwarding
prerequisites, DNS interception policy, Unbound runtime/control reachability,
Unbound DNSSEC validation on the configured loopback port, and syslog-ng.

## Result

**PASS.**

Phase 1 is live-validated for:

- native ASUSWRT rendering;
- read-only status presentation;
- manual mount;
- manual unmount/rollback;
- remount;
- installer deployment;
- startup persistence through `services-start`;
- automatic recovery after a controlled reboot;
- non-regression of the existing project health check.

## Claim boundary

This evidence validates the Phase 1 read-only WebUI only.

It does not validate configuration write actions, Apply/Restart workflows,
generated Unbound configuration, cache/statistics controls, firewall editing or
other future management functions proposed in issue #84.

The firmware DNSSEC flag displayed by the page is not treated as the project's
end-to-end DNSSEC result. The authoritative project validation remains the
direct Unbound DNSSEC health check.

Deployment-specific authentication material, Tailscale identity information,
public addressing and other private infrastructure data are intentionally
omitted.
