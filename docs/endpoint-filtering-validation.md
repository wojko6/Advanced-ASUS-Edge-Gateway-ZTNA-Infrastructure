# Endpoint Filtering Validation

## Purpose

This test track evaluates endpoint-side content filtering as an optional defense-in-depth layer alongside the existing ASUS Edge Gateway DNS controls. It does **not** replace dnsmasq, Unbound, DNSSEC, or router firewall policy.

The initial candidate is Zen on Windows with Chrome. AdGuard for Windows may be evaluated later with the same methodology if a controlled comparison is useful.

## Stability-gate constraint

During the 2026-09-11 through 2026-09-25 unchanged-state router observation window:

- do not modify router DNS, firewall, Tailscale, Unbound, dnsmasq, startup hooks, filtering lists, or service configuration for these tests;
- router-side verification is read-only;
- do not intentionally reboot the router for endpoint-filter testing;
- endpoint software changes remain confined to the selected workstation.

## Test objectives

1. Determine whether endpoint filtering removes content that DNS-level filtering cannot reliably remove, including YouTube advertising.
2. Confirm that the workstation continues to use the existing router DNS path.
3. Identify HTTPS/certificate compatibility problems and false positives.
4. Measure basic endpoint overhead and operational impact.
5. Produce sanitized, reproducible evidence suitable for the public repository.

## Baseline

Before enabling the endpoint filter, record:

- Windows version and patch level;
- Chrome version;
- active DNS server reported by Windows;
- a normal DNS lookup result;
- representative browsing behaviour;
- YouTube advertising behaviour during a defined test session;
- baseline browser/system CPU and memory observations.

Do not publish usernames, hostnames, public IP addresses, Tailscale addresses, browsing history, account identifiers, or unrelated DNS queries.

## Zen validation

Validate Zen in this order:

1. Verify the installer/source and record the tested version.
2. Install Zen only on the selected Windows workstation.
3. Record any local CA/certificate changes required for HTTPS filtering.
4. Confirm ordinary HTTPS websites load without certificate warnings.
5. Test Chrome browsing with Zen enabled.
6. Run a repeatable YouTube test and record whether pre-roll/mid-roll advertising is observed.
7. Check representative sites for false positives or broken page functionality.
8. Observe CPU/RAM impact during idle browsing and video playback.
9. Confirm DNS-path preservation using Windows-side DNS inspection and read-only router log observation where useful.
10. Disable Zen and verify that the endpoint returns to its baseline state.

## Optional AdGuard for Windows comparison

If AdGuard for Windows is evaluated, use the same baseline and test cases.

For architecture-preservation testing:

- keep AdGuard DNS Protection disabled;
- keep the router-provided DNS path authoritative;
- enable only the endpoint/content-filtering features required for the comparison;
- document the exact tested AdGuard version and settings;
- do not infer that successful endpoint filtering proves router-side filtering behaviour.

## DNS-path acceptance criteria

PASS requires all of the following:

- Windows continues to report the expected router DNS resolver;
- normal DNS resolution succeeds;
- endpoint filtering does not intentionally redirect DNS to an external resolver;
- when router logs are inspected, expected workstation DNS activity remains visible through the existing path;
- no router configuration change is required to make the endpoint filter work.

A DNS leak-test website may be used as supplementary evidence, but it must not be the sole proof of the local DNS path.

## HTTPS and safety checks

Because system-level content filters can inspect HTTPS traffic, document:

- whether a local root CA is installed;
- where the product stores its private key, when documented/observable without exposing it;
- certificate warnings or TLS failures;
- incompatibility with security-sensitive applications;
- uninstall/disable behaviour and certificate cleanup.

Never commit certificate private keys, exported trust stores, browser profiles, cookies, authentication tokens, or packet captures containing private session data.

## Evidence format

Create a dated evidence directory only after a real test is performed. Suggested artifacts:

```text
evidence/YYYY-MM-DD/endpoint-filtering/
  README.md
  environment.txt
  dns-path-sanitized.txt
  zen-results.md
  adguard-results.md        # only if actually tested
  checksums.sha256
```

Screenshots are optional. Prefer concise text evidence where it proves the result more clearly and exposes less personal information.

## Result language

Use precise claims:

- **Observed:** directly demonstrated in the recorded test.
- **Not observed:** not seen during the defined test window; this is not proof that it can never occur.
- **Not tested:** no evidence collected.
- **Inconclusive:** evidence was insufficient or confounded.

Do not claim that Zen or AdGuard permanently blocks all YouTube advertising. YouTube delivery changes over time, so results are version- and date-specific.

## Relationship to router filtering

Endpoint filtering and router filtering solve different parts of the problem:

- router DNS filtering provides network-wide domain-level policy and visibility;
- endpoint content/HTTPS filtering can remove page or media elements that cannot be reliably separated at DNS level;
- browser-native controls such as Brave Shields can provide another endpoint-specific layer.

The intended design is defense in depth without silently bypassing the router's validated DNS architecture.
