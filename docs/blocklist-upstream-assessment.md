# Third-party blocklist upstream assessment

## Purpose

This document records the offline review of `hululu1068/AdGuard-Rule` as a possible source of candidate DNS/filtering rules. It is **not** an approval to subscribe the router directly to that aggregate.

The assessment is deliberately performed without changing the router during the 2026-09-11 through 2026-09-25 unchanged-state stability window.

## Executive decision

Do **not** deploy `rule/all.txt`, `rule/adgh.txt`, or `rule/mylist.txt` wholesale.

The project is useful as a discovery source, but its active configuration combines many heterogeneous upstreams aimed at different products, regions, and filtering layers. Its generated outputs are large (`all.txt` is roughly 13.5 MB and `adgh.txt` roughly 7.4 MB in the reviewed tree), and its own documentation expects manual allowlisting when false positives occur.

For this project the safer model is:

1. identify useful upstream sources;
2. prefer authoritative/original upstreams over a third-party aggregate;
3. remove sources that duplicate existing controls or target unrelated regions/products;
4. extract a small project-owned candidate set;
5. test candidates after the stability gate with rollback and false-positive observation.

## Source classification

### Strong candidates for further offline review

These sources have a plausible security/privacy role independent of the aggregate and are worth comparing against the project's existing controls:

- **OISD Basic** — broad curated domain blocking; useful as a comparison/baseline, but overlap must be measured before adoption.
- **AdGuard DNS filter** — DNS-oriented upstream from AdGuard; potentially relevant, but likely to overlap substantially with existing filtering.
- **AdGuard CNAME disguised trackers** — relevant to tracker coverage, subject to compatibility with the project's actual DNS/filtering mechanism.
- **WindowsSpyBlocker** — potentially useful for Windows telemetry/privacy analysis, preferably as an endpoint-specific candidate rather than a universal router policy.
- **Scam Blocklist / uBlock Badware risks** — security-oriented candidates that can be assessed separately from advertising rules.
- **AdAway hosts** — mature hosts-style input, but expected to have substantial overlap with other general ad lists.

None of these are approved for router deployment merely by appearing in this section.

### Mostly redundant or layer-mismatched candidates

The aggregate includes browser/client-oriented lists such as AdGuard Base, anti-adblock filters, uBlock privacy/quick-fix/unbreak/resource-abuse rules, video-specific filters, and cosmetic/modifier rules. These can be valuable inside a capable browser or HTTPS-filtering client, but many semantics do not map cleanly to a DNS-only/router blocking layer.

Zen already supplies endpoint/browser-context filtering in the current Windows assessment. Duplicating client-level cosmetic and response-modification logic at the router would add complexity without equivalent capability.

### Region/product-specific sources not suitable as default project policy

A significant part of the active aggregate is focused on Chinese advertising ecosystems, Chinese mobile applications, regional video services, Android-specific advertising, or individual services such as Zhihu. These sources may contain useful individual domains, but they should not become default policy for this Polish Home/SMB lab without observed traffic that justifies them.

Examples in the reviewed active configuration include AdditionalFiltersCN, ADgk, Chinese video/ad rule sets, HalfLife-derived combinations, Blackmatrix7 advertising rules, Zhihu-specific rules, Android-focused AWAvenue rules, and YouTube-specific community lists.

## `mylist.txt` assessment

The aggregate's local `mylist.txt` is not a pure denylist. It contains many manual exception rules (`@@`) created for the maintainer's own environment, including exceptions for analytics/advertising or telemetry-related domains.

Examples include allow rules for Google Analytics, Google Ad Services, DoubleClick, Google Tag Manager, Microsoft activity/telemetry-related destinations, and numerous China-specific services. Importing these exceptions would silently weaken policy for reasons that are unrelated to this project's requirements.

Therefore `mylist.txt` must **not** be imported as policy.

It does contain individual Xiaomi-related deny candidates, including:

```text
||exp.sug.browser.miui.com^$important
||sentry.d.xiaomi.net^$important
```

These are retained only as **candidates for evidence-driven comparison**. They are not approved for blocking until they are correlated with traffic from the project's Xiaomi endpoint assessment and checked for functional impact.

## Candidate policy for this project

A candidate domain/rule should be promoted only when at least one of the following is true:

- it appears in observed endpoint/router traffic and has a defensible advertising, tracking, telemetry, scam, malware, or abuse role;
- it comes from a high-quality security-oriented upstream and provides measurable coverage not already supplied by existing policy;
- it addresses a documented project requirement with an understood rollback path.

A candidate should be rejected or deferred when:

- it is purely cosmetic/client-side syntax that the router cannot meaningfully enforce;
- it is a broad exception copied from another maintainer's environment;
- it targets a region/service absent from the project without observed evidence;
- it duplicates existing protection without a measurable benefit;
- its functional purpose is ambiguous or blocking it risks authentication, updates, payments, push notifications, or other required functionality.

## Deployment rule

No third-party mega-list will be subscribed directly as the project's security policy. After the stability window, any selected additions should be introduced incrementally, with a known baseline, a small change set, explicit rollback, DNS/functionality validation, and sanitized evidence.

This keeps the repository's policy auditable and project-owned instead of outsourcing trust to a rapidly changing aggregate.