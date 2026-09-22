# 2026-09-22 Diversion ad-blocking validation

## Scope

Controlled post-stability comparison of Diversion filtering policy on the reference ASUS router. The Android client used LTE/5G, Tailscale, and the ASUS exit node. Public evidence omits deployment-specific client addresses and session identifiers.

The test changed only Diversion filtering policy. Firewall, Tailscale exit-node configuration, WAN handling and Unbound listener design were not changed.

## Variant A — Standard + SNBForums support enabled

Initial state:

```text
Diversion 6.1.1
profile: Standard
snbAdSupport=yes
```

Representative result:

```text
BLOCKED  googleads.g.doubleclick.net
ALLOWED  pagead2.googlesyndication.com
ALLOWED  www.googleadservices.com
ALLOWED  adservice.google.com
ALLOWED  app-measurement.com
ALLOWED  www.google-analytics.com
ALLOWED  www.googletagmanager.com
```

Local Diversion logic showed that SNBForums support adds a hard-coded allowlist entry for `pagead2.googlesyndication.com`, while the active blocking list contained `local=/googlesyndication.com/`. The exact allowlist therefore overrode the broader parent-domain block for that host.

## Variant B — Standard + SNBForums support disabled

Diversion's own menu was used to set:

```text
snbAdSupport=no
```

The `pagead2.googlesyndication.com` allowlist exception disappeared and the same sample changed to:

```text
BLOCKED  googleads.g.doubleclick.net
BLOCKED  pagead2.googlesyndication.com
ALLOWED  www.googleadservices.com
ALLOWED  adservice.google.com
ALLOWED  app-measurement.com
ALLOWED  www.google-analytics.com
ALLOWED  www.googletagmanager.com
```

The relevant blocking matches were confirmed as the parent `googlesyndication.com` rule and a direct `clarium.global.ssl.fastly.net` rule.

The classic Android exit-node DNS path was re-checked after the change. A controlled UDP/53 query incremented the `EDGE_TS_PREROUTING` UDP redirect counter by exactly one, and a repeated unique query was visible between dnsmasq and Unbound on loopback port 53535. Result: **PASS / LIVE RE-CHECKED** for the already validated classic-DNS path.

## Variant C — Large + SNBForums support disabled

Diversion was changed to the `Large` profile while retaining `snbAdSupport=no`.

The Diversion status screen reported approximately 246k blocked domains. The original seven-domain sample remained identical to Variant B: two blocked and five allowed.

Real-world validation on `dobreprogramy.pl` and `ithardware.pl` still showed visible advertising.

Packet captures from the Android exit-node client showed many advertising/RTB-related TLS hostnames. Controlled DNS tests from the same client returned `NXDOMAIN` for representative hosts including:

```text
pagead2.googlesyndication.com
securepubads.g.doubleclick.net
googleads4.g.doubleclick.net
tpc.googlesyndication.com
adx.g.doubleclick.net
ep1.adtrafficquality.google
s0.2mdn.net
sync.srv.stackadapt.com
onetag-sys.com
serv-eu-1.onetag-sys.com
pixel.rubiconproject.com
ssp.goadservices.com
ssp.wp.pl
rek.www.wp.pl
dot.wp.pl
```

Required first-party/content hosts such as `www.dobreprogramy.pl` and the broad WP content CDN host `v.wpimg.pl` remained resolvable.

## Focused denylist check

As a reversible test, `sdk-videoplayer.optad360.info` was added to the Diversion denylist. Direct DNS then returned `NXDOMAIN`, but visible advertising still remained. That single endpoint was therefore not sufficient to suppress the observed advertising flow.

## Conclusion

- `snbAdSupport=yes` measurably weakened blocking for at least one tested Google advertising host.
- `snbAdSupport=no` improved DNS-layer coverage without breaking the tested classic-DNS exit-node path.
- The `Large` profile materially broadened the DNS policy.
- Even with `Large + snbAdSupport=no`, multiple advertising/RTB domains returning `NXDOMAIN`, and one focused denylist entry, visible advertising remained on the tested sites.
- DNS-domain filtering must therefore not be presented as complete browser-content or in-app advertising removal.
- Broad shared/first-party CDN hosts should not be blocked merely to hide ads because doing so can break legitimate page content.

## Current test state

At the end of the session:

```text
Diversion: enabled
profile: Large
snbAdSupport=no
focused denylist:
  sdk-videoplayer.optad360.info
```

This is a post-observation maintenance state and is not part of the earlier unchanged-state stability claim.

No firewall, Tailscale, WAN or Unbound architecture change was made during this filtering experiment.

## Follow-up

Before accepting `Large` as the long-term policy, observe normal daily use for false positives and resource impact. Browser/content-filter tooling remains the appropriate layer for visual-ad-removal claims. A future Pi-hole migration may improve observability, per-client policy and management, but it should not be represented as a mechanism that inherently removes every same-origin or shared-CDN advertisement.
