# Blocklist candidates v1 — offline only

## Status

**OFFLINE REVIEW ONLY — NOT DEPLOYED**

This candidate set was prepared during the router unchanged-state stability window. It does not change the ASUS router, DNS policy, Unbound, firewall, Tailscale, or any running service.

The purpose is to reduce a large third-party aggregate to a small number of testable ideas. Inclusion below means "worth validating", not "approved to block".

## Candidate set

| Candidate | Scope | Current decision | Validation requirement |
| --- | --- | --- | --- |
| OISD Basic | broad ads/tracking/malicious domains | Compare only | Measure overlap with existing policy before considering any adoption. Prefer original upstream, not the aggregate copy. |
| AdGuard DNS filter | DNS-level ads/tracking/security | Compare only | Determine incremental domain coverage and false-positive cost versus current DNS controls. |
| AdGuard CNAME disguised trackers | CNAME-based tracking | Research candidate | Confirm that the project's DNS path can benefit from the source semantics and that it does not duplicate existing resolver/filter behaviour. |
| Scam Blocklist | scam/fraud domains | Security candidate | Check source maintenance/provenance and incremental coverage. Security value must be separable from general advertising rules. |
| uBlock Badware risks | badware/security | Security candidate | Review whether the source can be normalized safely for the intended DNS layer; do not copy browser-only syntax blindly. |
| WindowsSpyBlocker | Windows telemetry/privacy | Endpoint-focused candidate | Compare against actual Windows endpoint traffic before deciding whether any domains belong in network-wide policy. |
| AdAway hosts | general ad/tracker hosts | Low-priority comparison | Expected high overlap; adopt nothing unless measurable unique value remains after deduplication. |

## Xiaomi evidence candidates

The reviewed third-party maintainer list contains two Xiaomi-related deny rules that are relevant enough to retain for later traffic correlation:

```text
||exp.sug.browser.miui.com^$important
||sentry.d.xiaomi.net^$important
```

These are **not deployed** and are not assumed malicious. They are candidate indicators only.

A previously observed Xiaomi endpoint also queried:

```text
api.ad.intl.xiaomi.com
```

That observed destination should be handled separately from imported rules because it comes from project traffic evidence rather than from the third-party candidate list.

Before any Xiaomi rule is promoted, record:

1. which device/OS generated the request;
2. what user action preceded it;
3. frequency and query type;
4. whether the domain has a required functional role;
5. result of a temporary controlled block after the stability gate;
6. rollback result if functionality changes.

## Explicit exclusions from v1

The following are intentionally not candidates for router-wide import:

- the aggregate `all.txt`;
- the aggregate `adgh.txt`;
- the maintainer-specific `mylist.txt`;
- broad `@@` allow/exception rules from another environment;
- cosmetic filtering rules;
- browser response-modification rules;
- anti-adblock UI rules;
- China-specific service lists without matching observed project traffic;
- YouTube community lists as DNS/router policy;
- Android/mobile advertising mega-lists without evidence of incremental value;
- duplicated copies of the same upstream obtained through multiple aggregators/CDNs.

## Promotion criteria

A candidate can move from this document into a post-gate controlled test only when it has:

- an identifiable original upstream and understandable purpose;
- a reason to exist beyond the project's current controls;
- syntax compatible with the target filtering layer;
- a bounded test plan;
- a rollback method;
- a way to detect false positives;
- no requirement to weaken authentication, updates, payments, push notifications, or other required services merely to make the list appear effective.

## Post-gate test order

After the router stability gate completes successfully, candidate testing should proceed from smallest and best-evidenced change to broadest comparison:

1. evidence-backed individual domains observed in project telemetry;
2. narrowly scoped security candidates;
3. CNAME/tracker-specific coverage if technically applicable;
4. broad-list overlap measurement;
5. only then consider whether any broader upstream adds enough unique value to justify its operational cost.

Do not introduce multiple new upstreams simultaneously. Each test should produce a before/after result and be independently reversible.

## Current recommendation

No new router blocklist is required during the stability window. The existing project should continue collecting normal operational evidence. The candidate set above is intentionally small so that later changes remain attributable, auditable, and recruiter-defensible.