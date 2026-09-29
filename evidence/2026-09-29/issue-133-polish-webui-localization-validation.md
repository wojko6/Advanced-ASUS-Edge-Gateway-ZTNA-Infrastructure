# Issue #133 — persistent Polish ASUS WebUI localization validation

**Status:** PASS  
**Date:** 2026-09-29  
**Evidence class:** Router live / controlled reboot / sanitized  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton

## Purpose

Validate that the project-owned Polish ASUS/GNUton WebUI localization overlay
is reproducible, mounted exactly once per managed resource and restored
automatically after a controlled router reboot.

The repository stores reviewed patch deltas and pinned hashes rather than
complete vendor WebUI files.

## Managed resources

The final v9 overlay manages eight resources:

- `/www/PL.dict`;
- `/www/help.js`;
- `/www/Tools_Sysinfo.asp`;
- `/www/Tools_OtherSettings.asp`;
- `/www/Advanced_WAdvanced_Content.asp`;
- `/www/state.js`;
- `/www/device-map/router_status.asp`;
- `/www/device-map/router.asp`.

## Final validated hashes

```text
PL.dict                         1bc59ad0727ee6198dd75a35a15be3313fed67ac816c85bd741463415773e8ac
help.js                         7da975a69b1237499ee238e93ede215c3e235c5b34a5d87ab507d45a4e063778
Tools_Sysinfo.asp               3dbef5d95c02561baf920a6b2014ed34d021eb5ce6723c076ddecf9072d839df
Tools_OtherSettings.asp         6cee7405bcc556ac3af1baee418a2ffa85cad39b37c3f76e340ef2a8297595c6
Advanced_WAdvanced_Content.asp  62b5c08839fb238c17bdace3e968c799233926873c50cb400e6de2d2356e10fc
state.js                        21c1653b9d76c1fe174044467a3ba4648908a4e525df7735fd23d3c737ae2dfb
router_status.asp               1435585d9f1f8a77e1f03d765f7114c9f2a33da26425bc38512922d5e0f56b95
router.asp                      5c809d2105bfdb87f1e6493ddc8cf05f78dbd3f50be402d3846f3b987d3f7cd6
```

The live files matched those expected values after reboot.

## Persistence validation

After a controlled reboot, the localization status helper reported all eight
expected hashes and:

```text
menuTree=polish
```

Runtime mount inspection showed exactly one bind mount for every managed
resource:

```text
/www/PL.dict=1
/www/help.js=1
/www/Tools_Sysinfo.asp=1
/www/Tools_OtherSettings.asp=1
/www/Advanced_WAdvanced_Content.asp=1
/www/state.js=1
/www/device-map/router_status.asp=1
/www/device-map/router.asp=1
```

This confirms that startup persistence restored the overlay without duplicate
mount stacking.

## Visual validation

The final live WebUI was visually checked after deployment. The completed v9
sweep included the system-status and QR-code surfaces in addition to the
previously validated dictionary, help, Tools and advanced-wireless changes.

Examples of final visible corrections include:

- `System Status` -> `Stan systemu`;
- `Internet Traffic` -> `Ruch internetowy`;
- `Core 1/2/3` -> `Rdzeń 1/2/3`;
- `Show QR code` -> `Pokaż kod QR`;
- `Scan to connect` -> `Zeskanuj, aby połączyć`;
- `Close` -> `Zamknij`.

## Project health

The complete project health check was run after reboot and returned:

```text
Summary: 0 failure(s), 0 warning(s)
```

The accepted health set included firewall serialization and chain integrity,
Tailscale connectivity and netfilter ownership, exit-node forwarding
prerequisites, LAN DNS/DoT policy, fail-closed IPv6 guards, printer exposure
controls, Unbound runtime/DNSSEC checks and syslog-ng.

## Repository validation

The implementation was committed as `d23a4d6`
(`feat: complete persistent Polish ASUS WebUI localization`).

Repository static validation and `git diff --check` passed before the commit.
A later CI-only fixture regression caused by the new installation-time GNU
`patch` dependency was corrected separately; it did not change the live
overlay behavior.

## Result

**PASS.**

The final localization overlay is reproducible from pinned firmware resources,
hash-verified, visually validated and persistent through a controlled reboot.

## Claim boundary

This evidence is specific to the pinned
`3004.388.11_1-gnuton1_tuf` WebUI resources. A firmware update that changes
the source hashes intentionally requires a fresh review/rebase before the
overlay can be rebuilt.

The result validates the Polish UI path. It does not claim that hard-coded
Polish strings in patched vendor JavaScript/ASP resources preserve equivalent
presentation when another UI language is selected.
