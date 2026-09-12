# Zen endpoint filtering validation — 2026-09-12

## Scope

This artifact records a Windows endpoint validation of Zen as an optional defense-in-depth content-filtering layer. The router remained unchanged during the active 14-day stability observation window.

The purpose was to check practical browser compatibility, DNS-path preservation, HTTPS interception behaviour, ad/content-filtering observations, false positives, approximate endpoint resource cost, and selected runtime-log behaviour without changing router DNS, firewall, Unbound, Tailscale, or other router services.

## Test environment

- Endpoint: Windows workstation.
- Browsers used during validation: Google Chrome and Brave.
- Zen: v0.25.1 in the captured application log.
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

### YouTube — A/B INCONCLUSIVE; FILTER ACTIVITY CONFIRMED

With Zen enabled, tested YouTube videos started without an observed advertisement. A control run with Zen disabled also failed to receive an advertisement.

Because the control session did not produce an ad, this test cannot establish a causal Zen ON/OFF blocking result. The observation therefore remains inconclusive as a user-visible A/B test.

The captured Zen runtime log adds separate technical evidence that the filter engine was actively processing YouTube responses. It recorded removal of ad-related properties including `adSlots`, `playerAds`, and, in later attempts, `adPlacements`. This confirms filter activity against YouTube advertising structures, but it does not substitute for a control session in which an advertisement is actually served with Zen disabled.

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

### Runtime log behaviour — cache/update/proxy observations

The captured Zen application log records initialization as version `v0.25.1`, followed by `checking for updates`, local proxy startup, a whitelist server, and a PAC server. Subsequent proxy starts repeatedly loaded configured subscriptions `from cache`, including EasyList/EasyPrivacy, AdGuard filters, malware/phishing lists, the Polish regional list, and Zen's own lists.

This confirms an update check occurred and confirms filter-cache reuse. It does **not** by itself identify the exact update endpoint, prove that every cache refresh avoids network access, or prove that Zen never performs other outbound activity.

An earlier controlled idle observation did not show unexpected external TCP activity attributable to Zen after other applications using the proxy were closed. That remains a bounded observation from the tested window rather than proof of permanent absence of telemetry.

### Runtime log privacy — PARTIAL REDACTION

The log frequently replaces destinations with `[REDACTED]`, including many TLS-handshake and filtering messages. Redaction is not comprehensive: some DNS/error/debug paths expose destination hostnames, and YouTube processing errors can include full watch URLs.

Conclusion: raw Zen application logs are treated as sensitive evidence and must **not** be committed to the public repository without sanitization. Portfolio evidence should use a sanitized summary or deliberately redacted excerpt only.

### Runtime transport errors — compatibility signal, not compromise evidence

The log contains repeated TLS `EOF`, connection-cancelled/reset, DNS-resolution, and HTTP/2 transport messages during normal browsing. These entries are not by themselves evidence of compromise. One certificate-verification failure caused a destination to be added to Zen's ignored-host handling during the test.

This is operationally relevant because HTTPS interception can encounter applications or destinations whose certificate/trust behaviour is incompatible with interception. Sensitive or certificate-pinned applications remain a residual compatibility area for later normal-use observation.

## Upstream security architecture review

The following points come from the upstream `irbis-sh/zen-desktop` repository and are recorded separately from the workstation observations above. They describe the upstream design and stated controls; this project did not independently audit every implementation detail.

### Local CA trust model

Upstream documentation states that Zen generates its root CA key pair locally on the endpoint, does not send the private key to a remote server, and stores the private key with minimal filesystem permissions (`0600`). The maintainers also state that stronger private-key protection using operating-system facilities is still being explored.

This is consistent with the locally observed `Zen Personal CA` interception model. Because the CA can authorize locally generated HTTPS leaf certificates, compromise of its private key or of the filtering process would be security-significant.

### Sensitive-hostname proxy exclusions

Zen uses a PAC-based system proxy and maintains hostname exclusions for traffic that should not be proxied/MITM. The upstream common exclusion list contains categories such as authentication gateways, government/e-government services, password managers, banks and financial institutions, payment processors, messaging services, and digital-infrastructure providers.

Examples present in the reviewed upstream list include `accounts.google.com`, `bitwarden.com`, `1password.com`, `paypal.com`, `stripe.com`, `revolut.com`, `signal.org`, `whatsapp.com`, `github.com`, and selected OpenAI/ChatGPT service domains.

This reduces interception exposure for listed sensitive destinations, but it is a maintained allow/exclusion list rather than a universal guarantee that every sensitive hostname is excluded.

### Release provenance controls

Upstream documentation states that GitHub releases and associated tags are immutable and that release artifacts are built through GitHub CI with artifact attestations. The documented verification workflow uses GitHub CLI attestation verification against `irbis-sh/zen-desktop`.

These controls provide a stronger provenance path for release artifacts obtained through the documented GitHub release workflow and allow an operator to verify that an attested artifact was produced by the project's CI from the associated source.

### Update-delivery residual risk

The upstream security architecture explicitly marks update delivery as a work in progress. It states that updates are currently served from a private Cloudflare R2 bucket and acknowledges that this delivery path, without sufficient cryptographic verification, is not by itself an adequate integrity guarantee.

The maintainers list project-owned binary signing, runtime signature verification, and a framework such as TUF as possible future improvements.

For this project, that is a material residual risk because Zen is a high-trust endpoint component capable of HTTPS interception. Release provenance controls are a positive property, but they should not be conflated with a fully hardened automatic-update channel.

### Upstream review conclusion

The reviewed upstream design shows deliberate attention to the risks created by system-wide proxying and local HTTPS interception: local CA generation, sensitive-host exclusions, public source, immutable releases, and artifact attestations are positive controls. The most important documented residual concern is the still-in-progress cryptographic hardening of update delivery. Local CA private-key protection is another area the maintainers themselves identify for improvement.

These upstream claims improve the architectural context for the endpoint test but do not convert this artifact into a source-code security audit or formal supply-chain verification.

## Overall assessment

| Area | Result | Notes |
| --- | --- | --- |
| Windows DNS server preserved | PASS | Wi-Fi remained configured for `192.168.50.1` |
| Repeated direct DNS queries | PASS | 10/10 to `192.168.50.1`; initial transient timeout was not reproduced |
| Facebook / Google / Xiaomi | PASS | Functional spot checks only |
| WP Poczta | PARTIAL / COMPATIBILITY ISSUE | Standard filtering usable, but tested custom cosmetic ad rules removed the login form too |
| YouTube ad blocking | INCONCLUSIVE A/B | No ad appeared in either Zen ON or Zen OFF control run; runtime logs independently confirm ad-object filter activity |
| HTTPS interception | PASS | Browser trusted a leaf certificate issued by `Zen Personal CA` |
| CPU | PASS for captured snapshots | Effectively 0% at capture time |
| RAM | NOTABLE COST | Stabilized near ~791 MB in the short follow-up; earlier ~1.58 GB state observed |
| Filter cache | CONFIRMED | Configured subscriptions were repeatedly loaded from cache on later proxy starts |
| Application update check | CONFIRMED | Runtime log records `checking for updates`; exact update network path was not established by this artifact |
| Idle unexpected outbound TCP | NOT OBSERVED | Bounded controlled observation; not proof of permanent telemetry absence |
| Log privacy | PARTIAL REDACTION | Raw log can expose hostnames/full URLs in some error/debug paths and is not suitable for public commit |
| Upstream CA / proxy design | POSITIVE WITH RESIDUAL RISK | Local CA and sensitive-host exclusions are documented; CA key protection remains high-trust |
| Upstream release provenance | POSITIVE | Immutable releases and GitHub artifact attestations are documented |
| Upstream update delivery | RESIDUAL RISK | Upstream explicitly describes cryptographic update verification as work in progress |
| Router configuration impact | NONE | No router configuration change was made for this validation |

## Decision

Zen remains a viable endpoint-side defense-in-depth candidate based on this short validation, runtime-log evidence, and upstream architecture review, with four important qualifications:

1. custom cosmetic filtering can create site-specific compatibility failures, demonstrated by WP Poczta;
2. memory use is significant enough to monitor if Zen is retained long term;
3. Zen is a high-trust HTTPS-interception component, and upstream update-delivery hardening is not yet described as complete;
4. raw application logs require sanitization because destination redaction is incomplete.

The YouTube user-visible result must remain explicitly inconclusive until a controlled session produces an advertisement with Zen disabled and allows a meaningful ON/OFF comparison. The runtime log nevertheless provides separate evidence that Zen actively removed YouTube ad-related response properties during the tested session.

No result in this artifact changes or shortens the separate router stability gate. Router-side DNS/filtering remains authoritative for the project architecture, and Zen is treated as an optional endpoint layer rather than a replacement for router controls.
