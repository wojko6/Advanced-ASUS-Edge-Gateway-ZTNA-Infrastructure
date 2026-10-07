# Tailscale Android DNS Failure – Routing and Private DNS Troubleshooting Case Study

## Summary

On 2026-09-24, an Android/HyperOS client connected to Tailscale showed an intermittent but severe failure mode:

- IPv4 connectivity remained available;
- direct IP tests such as `ping 1.1.1.1` succeeded;
- hostname resolution failed with `unknown host` / `Could not resolve host`;
- Android reported that the active network had no working Private DNS.

The initial symptom resembled an upstream Tailscale Android netstack defect related to TUN replacement during Wi-Fi/cellular handoff.

A controlled investigation did **not** reproduce that upstream defect after the local environment was cleaned up.

Instead, two independent configuration problems were identified:

1. an overlapping Tailscale subnet route for the same `192.168.50.0/24` network to which the phone was physically connected over Wi-Fi;
2. a DNS Toggle Wi-Fi profile that forced Android Private DNS to a NextDNS DoT hostname on a network where direct DoT was intentionally blocked by the router security policy.

After correcting both conditions, both the official Tailscale 1.102.3 client and a custom post-fix laboratory build completed repeated Wi-Fi/cellular handoff tests without DNS failure.

The case is useful because the original symptom looked like a single VPN/DNS software bug, while the evidence showed multiple interacting configuration layers.

## Environment

Relevant components:

- Android / HyperOS mobile client;
- official Tailscale Android 1.102.3;
- custom Tailscale Android laboratory build;
- ASUS edge router using the project firewall/DNS policy;
- LAN subnet: `192.168.50.0/24`;
- router / LAN DNS endpoint: `192.168.50.1`;
- DNS Toggle application using Android `WRITE_SECURE_SETTINGS`;
- NextDNS configured as an Android Private DNS provider;
- Termux, ADB and `scrcpy` used for controlled testing and evidence collection.

The custom APK was installed side-by-side with the official client by using a separate application ID.

## Initial Symptom

While Tailscale was active, the phone could retain normal IP connectivity while DNS resolution failed.

Representative result:

```text
ping 1.1.1.1
3 packets transmitted, 3 received, 0% packet loss

ping one.one.one.one
ping: unknown host one.one.one.one
```

A similar lookup through curl failed:

```text
curl: (6) Could not resolve host: example.com
```

This separated basic IPv4 reachability from name resolution.

## Initial Upstream Hypothesis

The symptoms were compared with Tailscale issue
[tailscale/tailscale#21155](https://github.com/tailscale/tailscale/issues/21155):

> Android: netstack stops transmitting after tun swap on network change; DNS forwarder and PeerAPI go dead while WireGuard stays up.

Tailscale merged
[tailscale/tailscale#21332](https://github.com/tailscale/tailscale/pull/21332)
on 2026-09-21 to avoid terminating netstack sender goroutines after a TUN write error.

Because the local phone was running official Tailscale 1.102.3, a post-fix Android build was prepared for A/B testing rather than assuming that the upstream issue was the root cause.

## Reproducible Post-Fix Laboratory Build

The Android source was pinned to:

```text
tailscale-android:
41edc608a2673c3035f997c15cb4cdbe123262cb
```

That revision pinned the Tailscale core to:

```text
tailscale.com v1.103.0-pre.0.20260921205240-523b626a8e8f
```

The resulting application reported:

```text
1.103.309-t523b626a8-g41edc608a
```

For side-by-side installation, the debug build was changed to:

```text
applicationIdSuffix = ".lab"
```

giving:

```text
com.tailscale.ipn.lab
```

The APK was verified with Android build tools and had SHA-256:

```text
9271b1ae9428a88b04609e04921373969477c64f7c14b5c65d07bf8060dfffed
```

The custom build was used only as a diagnostic comparison client. It was not treated as production software.

## Finding 1 – Overlapping Subnet Route

Android `dumpsys connectivity` showed that the phone was physically attached to the home Wi-Fi network:

```text
wlan0
192.168.50.100/24
DNS: 192.168.50.1
route: 192.168.50.0/24 -> wlan0
```

At the same time, the Tailscale VPN also installed:

```text
192.168.50.0/24 -> tun
```

The same prefix therefore existed both as the directly connected Wi-Fi LAN and as an accepted Tailscale subnet route.

During the failure state:

```text
ping 192.168.50.1
3 packets transmitted, 0 received, 100% packet loss
```

while:

```text
ping 1.1.1.1
```

continued to work.

### Controlled Change

`Use Tailscale subnets` was disabled on the Android client.

After the change:

- the `192.168.50.0/24 -> tun` route disappeared from the VPN;
- direct access to `192.168.50.1` immediately returned.

Representative validation:

```text
ping 192.168.50.1
3 packets transmitted, 3 received, 0% packet loss
```

### Assessment

This is direct evidence of a real overlapping-route condition.

The accepted Tailscale subnet route conflicted with the network to which the phone was already locally attached.

This issue affected reachability to the local router/DNS endpoint, but fixing it did **not** by itself restore Android system DNS. A second problem remained.

## Finding 2 – System Resolver Failure with Working DNS Transport

After correcting the subnet-route overlap, the system resolver could still fail even though raw DNS traffic worked.

Direct DNS queries were tested from Termux.

Router DNS:

```text
dig @192.168.50.1 example.com A +time=3 +tries=1

status: NOERROR
SERVER: 192.168.50.1#53
```

Public DNS:

```text
dig @1.1.1.1 example.com A +time=3 +tries=1

status: NOERROR
SERVER: 1.1.1.1#53
```

At the same time, normal system resolution could still return:

```text
ping: unknown host www.kernel.org
curl: (6) Could not resolve host: www.kernel.org
```

### Assessment

This isolated the remaining failure to the Android system resolver / Private DNS path rather than:

- IPv4 connectivity;
- UDP/53 transport;
- the router's DNS service;
- public recursive DNS reachability.

## Finding 3 – DNS Toggle Re-Enabling Strict Private DNS

Android settings repeatedly showed:

```text
private_dns_mode=hostname
private_dns_specifier=<profile>.dns.nextdns.io
```

Android network state also reported:

```text
UsePrivateDns: true
PrivateDnsBroken
```

An ADB inspection of DNS Toggle showed that it:

- was actively running;
- had `android.permission.WRITE_SECURE_SETTINGS` granted;
- used Shizuku integration;
- had a configured Wi-Fi profile for the home network.

The DNS Toggle UI showed that the home Wi-Fi profile had:

```text
Enable Private DNS = ON
```

and the configured NextDNS server was reported by the application as:

```text
DNS server unreachable on port 853 (DoT)
```

This is consistent with the project router's policy of blocking direct LAN DNS-over-TLS on TCP/853.

### Controlled Change

DNS Toggle was force-stopped and Android Private DNS was set to off for the diagnostic test.

The setting remained off instead of reverting to `hostname`.

System DNS immediately recovered:

```text
ping www.kernel.org
-> resolved and replied

curl -4 -I --max-time 15 https://www.kernel.org
-> HTTP/2 200
```

The DNS Toggle Wi-Fi profile was then edited so that it no longer forced Private DNS on the home network.

The resulting Android mode was:

```text
private_dns_mode=opportunistic
```

and hostname resolution remained functional.

### Assessment

The evidence strongly supports a configuration interaction:

```text
DNS Toggle Wi-Fi profile
        |
        v
strict Android Private DNS
        |
        v
NextDNS over DoT / TCP 853
        |
        v
router policy rejects direct DoT
        |
        v
PrivateDnsBroken
        |
        v
system resolver failure
```

The test does not establish a defect in DNS Toggle itself.

The application was applying the Wi-Fi policy that had been configured. The problem was that this policy conflicted with the router's DNS enforcement model.

## Clean A/B Validation

After both local configuration issues were removed, the clients were tested under the same baseline:

- Exit Node: None;
- Tailscale subnet routes: disabled;
- no strict Android Private DNS on the home Wi-Fi profile;
- normal Wi-Fi and cellular connectivity;
- repeated Wi-Fi to LTE/cellular transitions.

The post-fix laboratory client completed five Wi-Fi/cellular cycles without losing IP or DNS connectivity.

The official Tailscale 1.102.3 client was then tested with the same clean configuration.

It also completed five cycles without DNS failure.

Representative checks after handoff included:

```sh
ping -c 2 1.1.1.1
ping -c 2 www.kernel.org
curl -4 -I --max-time 10 https://www.kernel.org
```

All tests passed in the clean configuration.

## Upstream Bug Assessment

The original symptom superficially resembled Tailscale issue #21155.

However, the local evidence does **not** establish that #21155 was reproduced.

Important differences:

- the observed local failure also occurred while remaining on Wi-Fi;
- an overlapping subnet route was present locally;
- strict Private DNS was repeatedly re-enabled by a local automation profile;
- direct DNS to both the LAN resolver and `1.1.1.1` remained functional during part of the failure;
- after removing the local conflicts, both official 1.102.3 and the post-fix build passed the same repeated network-handoff test.

Therefore the custom post-fix build was valuable as a control, but the investigation does not support the claim that PR #21332 fixed the local incident.

## Root Cause Assessment

Two independent local configuration conditions were demonstrated.

### Root cause A – route overlap

The phone accepted a Tailscale subnet route for `192.168.50.0/24` while being physically connected to that same subnet over Wi-Fi.

Evidence:

- route present on the VPN;
- local router unreachable;
- route removed after disabling Tailscale subnet acceptance;
- router reachability immediately restored.

### Root cause B – incompatible Private DNS automation

DNS Toggle forced a strict NextDNS Private DNS profile on the home Wi-Fi network while the router security policy intentionally prevented direct client DoT on TCP/853.

Evidence:

- Android repeatedly returned to `private_dns_mode=hostname`;
- DNS Toggle had the required secure-settings permission;
- the home Wi-Fi profile explicitly enabled Private DNS;
- DNS Toggle reported the provider unreachable on DoT/853;
- Android reported `PrivateDnsBroken`;
- after stopping the automation and disabling strict Private DNS, normal system resolution recovered.

The two conditions overlapped and made the incident initially resemble a Tailscale Android DNS defect.

## Remediation

The operational remediation was:

1. disable Tailscale subnet-route acceptance on the phone when it is connected directly to the same `192.168.50.0/24` network;
2. change the DNS Toggle home Wi-Fi profile so that it does not force strict Private DNS;
3. retain the router's intentional DNS/DoT enforcement policy;
4. use the official Tailscale client for normal operation;
5. retain the side-by-side laboratory APK only as a diagnostic A/B tool.

## Lessons Learned

- A working ping to a public IP does not prove DNS health.
- A DNS-looking failure can originate in routing, resolver policy, VPN integration, or encrypted-DNS enforcement.
- Overlapping local and VPN subnet routes should be checked early with the actual OS route state.
- Direct `dig @resolver` tests are useful for separating DNS transport from the system resolver.
- Android `dumpsys connectivity` can expose route ownership, VPN DNS state and `PrivateDnsBroken` conditions.
- Automation tools with `WRITE_SECURE_SETTINGS` can silently change the effective DNS state and should be included in the troubleshooting scope.
- Security controls must be evaluated together: a deliberate DoT block and a client-side rule that forces DoT are individually valid choices but operationally incompatible.
- Suspected upstream bugs should be tested only after local configuration variables are controlled.
- A custom patched build is useful as an experimental control even when the suspected upstream defect is ultimately not reproduced.
- A disciplined case study should record negative findings as carefully as confirmed root causes.

## Result

After removing the overlapping subnet route and correcting the DNS Toggle Wi-Fi policy:

- the local router/DNS endpoint remained reachable;
- system hostname resolution worked;
- HTTP requests resolved and completed normally;
- direct DNS queries remained functional;
- repeated Wi-Fi/cellular handoffs completed successfully;
- both official Tailscale 1.102.3 and the custom post-fix build passed five controlled handoff cycles.

The final evidence supports two interacting local configuration problems and does not support attributing the incident to Tailscale issue #21155.
