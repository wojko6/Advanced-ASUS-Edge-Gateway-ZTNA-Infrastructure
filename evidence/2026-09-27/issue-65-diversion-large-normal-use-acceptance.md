# Issue #65 — Diversion Large normal-use acceptance

Date: 2026-09-27  
Reference router: ASUS TUF-AX5400  
Reference firmware: GNUton / Asuswrt-Merlin `3004.388.11_1-gnuton1_tuf`  
Filtering state: Diversion `Large + snbAdSupport=no`

## Purpose

Decide whether the current Diversion Large filtering state can be promoted from evaluation to an accepted baseline after multi-day normal use, clean reboot validation, DNS-path checks, list refresh, resource observation and rollback review.

This document contains only sanitized operational evidence. Public IP addresses, Tailscale addresses, node names and account identifiers are intentionally omitted.

## Acceptance summary

| Criterion | Evidence | Result |
|---|---|---|
| At least five representative normal-use sessions across multiple days | Six representative sessions recorded across 2026-09-22, 2026-09-23 and 2026-09-25 | PASS |
| At least three clean router startup/power-on cycles | Issue #66 recorded 3/3 clean cycles on the current reference startup configuration | PASS |
| No unresolved critical false positives | No critical required-site, application or local-service breakage remained unresolved during the observation window | PASS |
| No health-check failures attributable to filtering | Repeated project healthchecks remained at 0 failures / 0 warnings | PASS |
| Representative LAN classic-DNS check | Fedora direct-UDP/53 attempt to an external resolver was intercepted by the LAN DNS enforcement path and resolved successfully | PASS |
| Representative Android-over-Tailscale classic-DNS check | Android/Tailscale direct-UDP/53 attempt remained functional and traversed the Tailscale DNS interception path | PASS |
| One normal Diversion list refresh/update | Supported Diversion blocklist update completed successfully and dnsmasq reloaded cleanly | PASS |
| RAM/swap behavior | Available measurements show no sustained abnormal growth versus the pre-change snapshot | PASS |
| Rollback remains documented and practical | Previous Standard / OISD Small profile retained as the documented fallback | PASS |

## Multi-day normal-use observations

Representative post-activation sessions included:

1. **2026-09-22 — Windows client:** normal media/game-service activity through the home router, including YouTube/Game Pass related DNS activity.
2. **2026-09-22 — Fedora client:** normal network, repository and website access through the router.
3. **2026-09-22 — Android/Poco:** browsing through Tailscale + ASUS exit node, including ordinary website access; blocking remained active without reported site breakage.
4. **2026-09-23 — Fedora:** post-reboot LAN/Tailscale management session; router management remained available.
5. **2026-09-23 — Android:** router-management access through Tailscale on both mobile data and Wi-Fi remained functional.
6. **2026-09-25 — Fedora + Edge:** Xbox Cloud test session without a Diversion-attributed application failure.

Visible ads that were not blocked are treated as an effectiveness limitation / missed blocking, not as a false positive. A separate Android DNS handoff incident from the custom Tailscale Lab work is excluded because that experiment did not use the ASUS exit-node/Diversion path.

## Diversion blocklist refresh

The supported entry point was used:

```sh
/opt/bin/diversion sh-bl-update
```

Observed completion state:

- command return code: `0`;
- no update process remained;
- no Diversion lock remained;
- `DIVERSION_STATUS=enabled`;
- `adblocking=on`;
- `blUpdateErr` empty;
- `bfUpdateLastRun` updated to `Sep 27 13:24:33`;
- syslog recorded an updated **Large** blocking list from one valid source;
- resulting blocked-domain count: **243633**;
- dnsmasq restarted to apply settings;
- `dnsmasq --test`: syntax check OK;
- post-refresh project healthcheck: `0 failure(s), 0 warning(s)`, `RC=0`.

## LAN classic-DNS validation

A Fedora LAN client issued:

```text
dig @1.1.1.1 example.com A
```

The query completed with `status: NOERROR`.

The UDP REDIRECT rule in `EDGE_LAN_DNS_PREROUTING` changed from:

```text
0 packets / 0 bytes
```

to:

```text
1 packet / 80 bytes
```

while the TCP REDIRECT counter remained unchanged.

This confirms that the representative direct classic-DNS attempt on UDP/53 remained functional and was intercepted by the project LAN DNS enforcement path after the Diversion Large refresh.

## Android-over-Tailscale classic-DNS validation

Test conditions:

- Android on LTE/5G;
- Wi-Fi disabled;
- official Tailscale client connected;
- ASUS selected as exit node;
- Termux issued `dig @1.1.1.1 example.com A`.

The query completed successfully with `status: NOERROR` and returned A records.

During the test window, the UDP/53 REDIRECT counter in `EDGE_TS_PREROUTING` increased from **803** to **815** packets, while TCP/53 remained at **55**.

The +12 delta is not treated as one-query/one-packet correlation because Android/Tailscale can generate background DNS traffic. The exact router-side datapath correlation is documented separately. For this acceptance item, the observation confirms that classic DNS from the Android/Tailscale path remained functional after the Diversion refresh and continued through the project interception path.

## Resource review

Available measurements:

| Observation | MemAvailable | Swap used |
|---|---:|---:|
| Pre-Large snapshot, 2026-09-22 | ~105 MiB | ~51 MiB |
| Pre-refresh, 2026-09-27 | ~120 MiB | ~1.1 MiB |
| Post-refresh, 2026-09-27 | ~121 MiB | ~1.6 MiB |

The collected measurements do not show sustained abnormal RAM/swap growth attributable to the Large profile.

## Reboot and health evidence

Issue #66 separately recorded **3/3 clean startup cycles** on the corrected reference startup configuration. Those cycles verified persistent storage, swap, Tailscale, DNS services, firewall persistence, syslog-ng and project health state.

During the current #65 refresh and functional checks, the project healthcheck also remained clean:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

## Rollback

The previous filtering policy was **Standard / OISD Small**.

If the Large profile later causes unacceptable breakage, rollback remains to restore the previous policy and re-run the same DNS/service/health validation gates before accepting the reverted state.

## Acceptance

All acceptance criteria defined in issue #65 are supported by the collected evidence.

Result: **PASS — Diversion Large is accepted as the current filtering baseline.**

This acceptance does not imply perfect blocking coverage. Missed advertisements or future site-specific compatibility issues should be handled as effectiveness/tuning findings unless they constitute an actual false positive or required-service regression.
