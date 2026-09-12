# Zen endpoint filtering validation — 2026-09-12

## Scope

This artifact records a Windows endpoint validation of Zen as an optional defense-in-depth content-filtering layer. The router remained unchanged during the active 14-day stability observation window.

The purpose was to check practical browser compatibility, DNS-path preservation, HTTPS interception behaviour, ad/content-filtering observations, false positives, and approximate endpoint resource cost without changing router DNS, firewall, Unbound, Tailscale, or other router services.

## Test environment

- Endpoint: Windows workstation.
- Browsers used during validation: Google Chrome and Brave.
- Zen: enabled for the active-filter tests.
- Brave Shields: disabled during the dedicated Zen/Brave load test so browser-native blocking would not be intentionally mixed with the Zen result.
- Router DNS address configured on the Windows Wi-Fi interface: `192.168.50.1`.
- Router identity returned by direct DNS queries: `TUF-AX5400-ABF8`.

## Results

### DNS-path preservation — PASS at the endpoint

`Get-DnsClientServerAddress -AddressFamily IPv4` showed the active Wi-Fi interface using:

```text
Wi-Fi  {192.168.50.1}
```

A first `nslookup example.com` used `192.168.50.1` and ultimately resolved successfully, but included two 2-second timeout messages. The timeout was not reproduced in the follow-up test.

Ten consecutive explicit queries to `192.168.50.1` completed successfully:

```text
nslookup example.com 192.168.50.1
```

All 10/10 responses identified the DNS server as `TUF-AX5400-ABF8` at `192.168.50.1` and returned addresses for `example.com` without a timeout.

Conclusion: Zen did not replace the Windows IPv4 DNS server during this validation, and the endpoint continued to send the tested DNS queries to the router. This endpoint test does not by itself re-prove every downstream dnsmasq/Unbound property.

### General browser compatibility — PASS for tested sites

With Zen enabled, normal use of the following sites was reported as working without an observed rendering/login compatibility problem:

- Facebook
- Google
- Xiaomi

This is a functional spot check, not a claim of universal compatibility.

### WP Poczta — false-positive / anti-adblock compatibility case

WP Poczta was used as a focused compatibility test. Standard Zen filtering blocked multiple advertising/cookie-sync requests during inspection, including requests associated with advertising infrastructure. However, the visible first-party/native banner could still be rendered.

Two custom cosmetic-filter experiments were then performed:

```text
poczta.wp.pl##[class*="NativeFullBannerSlot"]
```

and a narrower image-only variant:

```text
poczta.wp.pl##[class*="NativeFullBannerSlot"] img
```

In both cases the advertisement disappeared, but the login form disappeared as well. Removing the custom rule restored both the advertisement and the login form.

The inspected page DOM also contained ad-detection-related elements. The observations are therefore consistent with an anti-adblock/rendering dependency, but the exact internal WP mechanism was not proven.

Conclusion: do not deploy either custom WP cosmetic rule. The result is retained as a real false-positive/compatibility example rather than hidden by an over-broad exception or an unsupported claim.

### YouTube — INCONCLUSIVE

With Zen enabled, tested YouTube videos started without an observed advertisement. A control run with Zen disabled also failed to receive an advertisement.

Because the control session did not produce an ad, this test cannot establish a causal Zen ON/OFF blocking result. The observation is retained as inconclusive rather than promoted to a PASS claim.

### HTTPS interception — PASS for the tested browser path

With Zen enabled, Brave reported the `example.com` connection as secure and the presented certificate as valid. Certificate inspection showed a locally issued certificate with:

- issuer CN: `Zen Personal CA`
- issuer organization: `Irbis`
- subject organization: `Irbis`
- observed validity: approximately 24 hours for the generated leaf certificate

This confirms that the tested HTTPS path was being locally intercepted/re-signed by Zen and that the browser trusted the installed Zen CA for this connection.

Security implication: Zen's local CA and HTTPS interception capability are high-trust endpoint components. A compromise or unsafe implementation of such a component would have visibility into decrypted traffic it intercepts. This test validates observed operation and browser trust, not the security of Zen's source code or implementation.

### Resource use — acceptable CPU, notable RAM

Observed `Zen.exe` memory states during the session:

- earlier observation: `1,581,620 KB` (about 1.51 GiB)
- later observation after browser/load activity: `790,956 KB` (about 772 MiB)
- after closing the additional Brave tabs and waiting about five minutes: approximately unchanged at the later value

The displayed CPU value was effectively 0% at the captured moments.

Opening roughly 15–20 browser tabs and exercising pages did not cause the later Zen memory figure to grow beyond the observed ~791 MB state. The short test therefore did not demonstrate a monotonic memory leak. It also does not prove long-term memory stability.

Conclusion: CPU impact was low in the captured snapshots, while RAM use was material for an endpoint filtering utility and should remain an operational consideration.

## Overall assessment

| Area | Result | Notes |
| --- | --- | --- |
| Windows DNS server preserved | PASS | Wi-Fi remained configured for `192.168.50.1` |
| Repeated direct DNS queries | PASS | 10/10 to `192.168.50.1`; initial transient timeout was not reproduced |
| Facebook / Google / Xiaomi | PASS | Functional spot checks only |
| WP Poczta | PARTIAL / COMPATIBILITY ISSUE | Standard filtering usable, but tested custom cosmetic ad rules removed the login form too |
| YouTube ad blocking | INCONCLUSIVE | No ad appeared in either Zen ON or Zen OFF control run |
| HTTPS interception | PASS | Browser trusted a leaf certificate issued by `Zen Personal CA` |
| CPU | PASS for captured snapshots | Effectively 0% at capture time |
| RAM | NOTABLE COST | Stabilized near ~791 MB in the short follow-up; earlier ~1.58 GB state observed |
| Router configuration impact | NONE | No router configuration change was made for this validation |

## Decision

Zen remains a viable endpoint-side defense-in-depth candidate based on this short validation, with two important qualifications:

1. custom cosmetic filtering can create site-specific compatibility failures, demonstrated by WP Poczta;
2. memory use is significant enough to monitor if Zen is retained long term.

The YouTube result must remain explicitly inconclusive until a controlled session produces an advertisement with Zen disabled and allows a meaningful ON/OFF comparison.

No result in this artifact changes or shortens the separate router stability gate. Router-side DNS/filtering remains authoritative for the project architecture, and Zen is treated as an optional endpoint layer rather than a replacement for router controls.
