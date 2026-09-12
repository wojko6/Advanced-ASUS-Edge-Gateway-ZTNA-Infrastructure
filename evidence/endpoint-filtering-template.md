# Endpoint filtering validation report

> **Template only.** This file is not validation evidence. Replace every placeholder with an observed result, use `NOT TESTED` where appropriate, and remove irrelevant rows before publishing a dated report.

## Test context

| Field | Value |
|---|---|
| Date/time | `<YYYY-MM-DD HH:MM timezone>` |
| Endpoint | `<device role/model>` |
| Operating system | `<edition/version/build>` |
| Browser | `<name/version>` |
| Filter product | `<Zen / AdGuard for Windows / other>` |
| Filter version | `<version>` |
| Filter settings/profile | `<settings relevant to the test>` |
| Router DNS path expected | `<for example: endpoint -> ASUS dnsmasq -> Unbound:53535>` |
| Router configuration revision | `<commit SHA or reference-state identifier>` |
| Stability-gate status | `<active / ended / not applicable>` |

## Safety and trust-boundary checks

| ID | Check | Expected | Observed | Verdict |
|---|---|---|---|---|
| EP-01 | Filter source/version recorded | Reproducible product identity | `<observation>` | `<PASS/FAIL/INCONCLUSIVE/NOT TESTED>` |
| EP-02 | DNS resolver/path with filter disabled | Existing router DNS path retained | `<observation>` | `<...>` |
| EP-03 | DNS resolver/path with filter enabled | Existing router DNS path retained unless DNS replacement is the explicit test | `<observation>` | `<...>` |
| EP-04 | HTTPS trust behavior | No unexplained certificate warning or TLS breakage | `<observation>` | `<...>` |
| EP-05 | Local root CA behavior, if applicable | Installation/trust scope understood and removable | `<observation>` | `<...>` |
| EP-06 | Disable/uninstall cleanup | Filter disabled and test CA removed when applicable | `<observation>` | `<...>` |

## Functional comparison

Run the same defined workload for baseline and filtered states. Do not describe a single successful session as permanent blocking capability.

| ID | Workload | Baseline observation | Filtered observation | Verdict/notes |
|---|---|---|---|---|
| WEB-01 | Representative news/content site | `<observation>` | `<observation>` | `<...>` |
| WEB-02 | Representative site with consent/advertising elements | `<observation>` | `<observation>` | `<...>` |
| WEB-03 | Defined YouTube session | `<observation>` | `<observation>` | `<...>` |
| WEB-04 | Login/account workflow on a TLS-sensitive site | `<observation>` | `<observation>` | `<...>` |
| WEB-05 | Download/update or other TLS-sensitive application | `<observation>` | `<observation>` | `<...>` |

## Compatibility and false positives

| Application/site | Expected behavior | Observed behavior | False positive or breakage? | Notes |
|---|---|---|---|---|
| `<target>` | `<expected>` | `<observed>` | `<yes/no/inconclusive>` | `<notes>` |

## Endpoint resource observations

Resource measurements are endpoint-local and must not be presented as router performance results.

| State | CPU observation | RAM observation | Notes |
|---|---:|---:|---|
| Baseline | `<value/method>` | `<value/method>` | `<notes>` |
| Filter enabled | `<value/method>` | `<value/method>` | `<notes>` |

## Router-side corroboration

During the reference-router unchanged-state observation window, router-side corroboration must remain read-only. Do not change dnsmasq, Unbound, firewall, logging, blocklists, services, packages, or reboot the router merely to complete this report.

| Check | Method | Observed | Verdict |
|---|---|---|---|
| Endpoint still uses expected router DNS authority | `<endpoint resolver check and/or existing read-only router log>` | `<observation>` | `<PASS/FAIL/INCONCLUSIVE/NOT TESTED>` |
| No unexpected resolver replacement detected | `<method>` | `<observation>` | `<...>` |

## Result boundary

Use these terms precisely:

- **Observed** — directly seen during the documented test window.
- **Not observed** — specifically looked for but not seen during that window; not proof it can never occur.
- **Not tested** — no test was performed.
- **Inconclusive** — available observations do not support a reliable conclusion.

Overall result: `<PASS / FAIL / INCONCLUSIVE / NOT TESTED>`

Summary: `<short evidence-based conclusion>`

Limitations/confounders:

- `<browser extensions, cache, account state, region, dynamic ad delivery, product version, workload variability, etc.>`

## Publication review

- [ ] This report contains real observations; no placeholder is presented as evidence.
- [ ] Product, OS, browser, date, settings, and workload are recorded.
- [ ] DNS-path claims are separated from HTTPS/content-filtering claims.
- [ ] Endpoint results are not described as router capabilities.
- [ ] No credentials, cookies, session tokens, browser profiles, private browsing history, or unrelated personal data are included.
- [ ] No endpoint-filtering CA private key, exported private trust material, or authentication database is included.
- [ ] Public/internal addresses and hostnames are minimized or anonymized where appropriate.
- [ ] Negative and inconclusive results are retained rather than rewritten as success.
- [ ] Sanitized supporting artifacts have SHA-256 hashes when they are published with the report.
