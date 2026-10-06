# Case Study: Android DNS Enforcement and Remote Management over Tailscale

## Executive summary

This case study documents the diagnosis and remediation of a multi-layer networking
problem involving Android, Tailscale, Pi-hole, ASUSWRT-Merlin, iptables NAT,
router-local services, and remote administration.

The goal was to provide DNS-level ad and tracker filtering to an Android device
outside the home network without consuming a second Android VPN slot.

The final design preserves:

- Tailscale as the only Android VPN,
- Pi-hole filtering over LTE/5G,
- internal `home.arpa` resolution,
- RouterCloud access,
- source-scoped ASUS administration,
- cellular Internet access without requiring an exit node,
- automated health checks and regression tests.

No Android root access was required.

---

## 1. Initial requirement

> Deployment-specific hostnames and addresses are sanitized. `service.home.arpa`
> is used as a documentation placeholder for the validated internal service name.


The Android client already received Pi-hole filtering while connected to the home
Wi-Fi.

The remote requirement was:

- LTE/5G remains the Internet uplink,
- Tailscale provides the private path to the home network,
- selected DNS traffic is routed through Pi-hole,
- internal DNS names continue to work,
- RouterCloud remains reachable,
- router administration remains restricted to authorized Tailscale clients,
- no additional Android VPN application is introduced.

Target flow:

~~~text
Android / LTE
     |
     v
Tailscale
     |
     v
ASUS Edge Gateway
     |
     +---- DNS ----> Pi-hole ----> Unbound / local DNS
     |
     +---- RouterCloud
     |
     +---- ASUS WebUI
~~~

---

## 2. Relevant architecture

The environment used:

- ASUSWRT-Merlin based edge gateway,
- Tailscale,
- project-managed iptables chains,
- Pi-hole on a router-local IPv4 alias,
- Unbound as validating upstream resolver,
- RouterCloud on a separate router-local IPv4 alias,
- Fedora as the administration and observability workstation,
- Android as the remote client.

The firewall is managed through dedicated chains including:

~~~text
EDGE_TS_INPUT
EDGE_TS_FORWARD
EDGE_TS_PREROUTING
~~~

Tailscale ingress terminates in an explicit deny policy unless traffic matches an
authorized rule.

---

## 3. Source-scoped Pi-hole DNS enforcement

A source-scoped policy was introduced for selected Tailscale clients.

Conceptually:

~~~text
authorized Android client
          |
          | UDP/TCP 53
          v
EDGE_TS_PREROUTING
          |
          | DNAT
          v
Pi-hole DNS endpoint
~~~

The generic Tailscale DNS redirect remained as a fallback for other clients.

This allowed the project to introduce Pi-hole filtering incrementally instead of
changing DNS ownership for the entire tailnet.

---

## 4. Initial validation

Testing was performed with:

- Wi-Fi disabled,
- LTE/5G enabled,
- Tailscale enabled,
- Android Private DNS disabled,
- exit node disabled unless explicitly tested.

A unique DNS marker was generated and queried from Android.

Pi-hole analytics confirmed that the query arrived with the Android client's
Tailscale source identity.

A known advertising domain was also queried and Pi-hole reported it as blocked by
Gravity.

This proved that the remote DNS path could work without routing all Internet traffic
through the Tailscale exit node.

---

## 5. RouterCloud failure

After enabling the DNS policy, the internal RouterCloud hostname resolved correctly,
but the service itself was not reachable remotely.

The Android routing table already contained the expected subnet route.

The key discovery was that the RouterCloud address was not a forwarded LAN host.
It was a router-local IPv4 alias.

Therefore the packet path was:

~~~text
Android
  |
Tailscale
  |
router-local address
  |
INPUT
~~~

and not:

~~~text
Android
  |
Tailscale
  |
FORWARD
  |
LAN host
~~~

The firewall had no matching INPUT rule for RouterCloud.

### Fix

A new optional RouterCloud policy was introduced.

Access is allowed only from configured administrative Tailscale sources and only to
the exact RouterCloud IPv4 address and HTTPS port.

The rule does not grant broad access to the router.

---

## 6. Stale administrative device identity

During the same investigation, the administrative source list still contained an
old Tailscale address for the Android device.

The current device therefore no longer had the same administrative permissions as
the Fedora workstation.

The stale address was removed and the current Android Tailscale address was added.

This restored the intended model:

~~~text
Fedora  = administrative device
Android = administrative device
other tailnet clients = denied by default
~~~

---

## 7. DNS behaviour with exit node enabled

An additional failure appeared while the Tailscale exit node was enabled.

`service.home.arpa` stopped resolving on Android.

Packet capture showed DNS queries leaving the router through the WAN interface to an
external resolver, which returned `SERVFAIL` for the private `home.arpa` name.

At the same time, the source-scoped Android-to-Pi-hole DNAT counter did not increase.

After disabling the exit node:

- the Android-specific Pi-hole DNAT counter increased,
- the generic DNS redirect counter did not increase for the test query,
- `service.home.arpa` resolved correctly again.

### Design conclusion

An exit node is not required for this use case.

The intended mobile configuration is:

~~~text
LTE/5G Internet
+
Tailscale private routing
+
Pi-hole DNS over Tailscale
+
exit node OFF
~~~

This keeps the cellular path for ordinary Internet traffic while using Tailscale only
for private services and DNS enforcement.

---

## 8. ASUS WebUI failure

RouterCloud started working, but ASUS WebUI access still failed.

The firewall contained an administrative rule for TCP/8443 and packet counters
increased when Android attempted to connect.

This proved that traffic was reaching the managed firewall policy.

The next diagnostic step was to inspect the real service listeners.

The router showed:

~~~text
ASUS httpds:
router LAN address :443

RouterCloud:
separate router-local address :443
~~~

However, the firewall was configured as:

~~~text
Tailscale :8443
     |
     v
DNAT
     |
     v
router LAN address :8443
~~~

Nothing was listening on the destination port.

This was the root cause of `ERR_CONNECTION_REFUSED`.

---

## 9. Port model correction

The design incorrectly used one variable for both:

- the externally exposed Tailscale administration port,
- the real internal ASUS WebUI listener port.

The policy was split into two explicit settings:

~~~text
EDGE_ROUTER_HTTPS_PORT=8443
EDGE_ROUTER_HTTPS_TARGET_PORT=443
~~~

The corrected path is:

~~~text
authorized admin
      |
      | TCP/8443
      v
Tailscale router address
      |
      | DNAT
      v
router LAN address:443
      |
      v
ASUS httpds
~~~

RouterCloud remains independent:

~~~text
RouterCloud alias:443
~~~

This avoids a port conflict while preserving the established remote administration
interface.

---

## 10. Healthcheck improvement

The previous healthcheck could report a completely healthy firewall even while the
ASUS WebUI DNAT pointed to a port with no listener.

New health checks were added for:

- external router HTTPS port validity,
- internal router HTTPS target port validity,
- real TCP listener on the configured target endpoint,
- source-scoped DNAT rule,
- post-DNAT INPUT rule,
- every configured administrative Tailscale source.

The healthcheck can now detect a mismatch between firewall configuration and the
actual application listener.

---

## 11. Regression tests

A dedicated contract test was added for router HTTPS management.

The test verifies the valid path:

~~~text
8443 -> router LAN address:443
~~~

and rejects:

- wrong administrative source,
- wrong incoming port,
- wrong DNAT target port,
- wrong INPUT destination,
- wrong INPUT port,
- listener on the old port,
- listener on the wrong address,
- missing listener.

Existing Pi-hole and RouterCloud contract tests continued to pass.

The complete regression suite remained green after the change.

---

## 12. Final validation

The final mobile validation was performed with:

~~~text
Wi-Fi:      OFF
LTE/5G:     ON
Tailscale:  ON
Exit node:  OFF
~~~

The following behaviours were confirmed:

### Internal DNS

`service.home.arpa` resolved to the expected internal RouterCloud address.

Pi-hole analytics showed:

~~~text
type=A
status=CACHE
reply_type=IP
~~~

### Advertising-domain blocking

A known advertising domain was returned as a blocked Pi-hole result.

Pi-hole analytics showed:

~~~text
status=GRAVITY
reply_type=IP
~~~

The Android client received the configured blocking response.

### Unique DNS marker

A fresh test hostname appeared in Pi-hole analytics under the Android Tailscale
client identity.

This proved that the remote query actually traversed the intended Pi-hole path.

### RouterCloud

RouterCloud was reachable through its internal hostname over LTE/5G and Tailscale.

### ASUS administration

The source-scoped administrative NAT and INPUT counters increased for the Android
client.

The validated management path was:

~~~text
Tailscale TCP/8443
        |
        v
DNAT
        |
        v
ASUS httpds TCP/443
~~~

Administration through the supported hostname succeeded.

Raw Tailscale-IP access is not treated as the supported WebUI access method.

### Runtime health

The post-deployment healthcheck completed with:

~~~text
0 failures
0 warnings
~~~

---

## 13. Diagnostic techniques used

The investigation combined several layers of evidence instead of relying on a single
symptom.

Tools and techniques included:

- Android Debug Bridge,
- Android routing inspection,
- Tailscale DNS and routing inspection,
- iptables packet counters,
- NAT rule ordering,
- `tcpdump`,
- `netstat`,
- Pi-hole query analytics,
- unique DNS markers,
- negative tests,
- mock firewall tests,
- configuration validation tests,
- shell syntax validation,
- SHA-256 deployment verification,
- staged deployment before runtime apply.

This allowed each hypothesis to be tested independently.

---

## 14. Key engineering lessons

### Follow the packet across layers

A DNS failure, routing failure, firewall failure, TLS failure, and application
listener failure can look almost identical from a browser.

The investigation therefore followed:

~~~text
client
 -> DNS
 -> route
 -> NAT
 -> firewall
 -> listener
 -> application
~~~

### Packet counters are strong evidence

Increasing NAT and INPUT counters proved that packets reached the expected firewall
rules.

That prevented unnecessary changes to Tailscale routing when the real problem was an
application listener mismatch.

### Router-local aliases behave differently from LAN hosts

Services bound to router-local aliases traverse INPUT, not FORWARD.

This distinction was essential to fixing RouterCloud.

### Exposed and target ports are different concepts

An externally exposed management port does not need to equal the application's local
listener port.

Modelling them separately made the firewall clearer and more resilient.

### Health checks should validate reality

Checking only that a firewall rule exists is insufficient.

A complete health check should also verify that the expected service is actually
listening on the destination endpoint.

### Fixes should produce regression tests

The discovered `8443 -> 8443` failure now has a contract test that explicitly rejects
that configuration.

The debugging session therefore improved both production behaviour and future
reliability.

---

## 15. Global strict policy and Fedora DNS-route finding

The stricter Pi-hole policy was first staged as an Android-only group. After
initial validation, the deployment decision changed: HaGeZi Multi PRO++ Mini was
moved to the global Pi-hole `Default` group alongside the existing OISD Big and
AdGuard DNS Filter sources. The temporary Android-specific group and explicit
Pi-hole client assignments were then removed.

A separate Fedora test revealed another important DNS-routing detail. Even though
the workstation's LAN resolver was Pi-hole, Tailscale had installed `~.` as a
DNS route on `tailscale0`. A normal public lookup therefore followed the
Tailscale DNS path and did not appear in Pi-hole analytics through the generic
fallback.

The fix reused the issue #152 transport design instead of disabling Tailscale
DNS: the Fedora administration workstation was added to the selected
source-scoped Pi-hole set. A fresh unique query was then observed in Pi-hole
under the workstation's Tailscale identity, while the project healthcheck stayed
at zero failures and zero warnings.

This produced two distinct policy layers:

~~~text
Pi-hole content policy:
  global Default -> OISD + AdGuard + HaGeZi PRO++ Mini

Tailscale transport policy:
  selected clients -> source-scoped DNAT -> Pi-hole
  other clients    -> existing generic DNS fallback
~~~

A same-day smoke test confirmed normal public DNS, internal `home.arpa`, a
Gravity-blocked advertising domain and normal HTTPS connectivity. This does not
replace longer application-compatibility observation.

---

## 16. Remaining scope

This case study covers the validated transport, DNS, and remote-management path.

The following work remains separate:

- longer application compatibility testing,
- banking and payment application validation,
- encrypted DNS bypass work such as DoH/DoQ,
- wider DNS analytics and disaster-recovery work.

These items are intentionally not presented as completed.

---

## 17. Result

The final architecture provides Android DNS filtering outside the home network without
requiring a second VPN or forcing all Internet traffic through an exit node.

At the same time, it preserves:

- private DNS,
- RouterCloud,
- restricted router management,
- Pi-hole filtering,
- normal cellular Internet access,
- explicit fail-closed firewall policy.

The most important outcome was not only the operational fix.

The project gained:

- clearer configuration semantics,
- stronger health checks,
- reproducible validation,
- regression coverage for the discovered failure modes,
- documented evidence suitable for future maintenance and technical interviews.
