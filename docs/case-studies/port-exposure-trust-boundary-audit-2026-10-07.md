# Case study: port-exposure and trust-boundary audit of an ASUS edge gateway

**Audit date:** 2026-10-07  
**Platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton  
**Scope:** router LAN exposure, Tailscale policy, Fedora observability host, public IPv4 WAN, native WAN IPv6  
**Outcome:** PASS with documented review findings and one bounded assurance gap

## Executive summary

This case study documents a port-exposure audit of the reference ASUS edge-gateway
lab. The objective was not to infer security from configuration files alone, but to
compare four evidence layers:

1. local listeners;
2. firewall and NAT policy;
3. reachability from independent LAN and Tailscale peers;
4. reachability from a genuinely external mobile-Internet path.

The audit found that the main trust boundaries behaved as designed:

- the router's Tailscale management path distinguished an authorized peer from a
  non-authorized peer;
- Fedora syslog ingestion on TCP/6514 accepted the router peer while rejecting a
  different tailnet peer;
- Fedora monitoring services remained unavailable from the ordinary LAN, while
  the intentionally LAN-visible desktop-integration service remained reachable;
- the tested public-IPv4 TCP surface was filtered from an LTE/5G hotspot path;
- native WAN IPv6 was disabled and had no routable WAN address or default route;
- current UPnP/virtual-server runtime state contained no active mapping.

The audit also produced several review findings rather than pretending that
"nothing was open":

- FTP/21 was reachable on the trusted LAN and had a weak operational security
  posture for a service whose requirement had not been established;
- firmware services on TCP/7788 and TCP/18017 plus UDP/18018 were LAN-visible and
  require necessity review;
- mDNS/5353 was visible on a router service alias;
- UPnP was configured as enabled even though no active runtime mapping was found;
- external WAN UDP was not conclusively probed, so the report does not claim full
  Internet-side UDP closure.

A particularly important result was methodological: the first supposed WAN test
was invalidated because Windows resolved the router hostname to an internal LAN
address and selected a Tailscale subnet route. The result was discarded, external
DNS-over-HTTPS resolution was used to obtain the public target, route selection was
verified through the phone hotspot, and only then was the final WAN test accepted.

## Why this audit mattered

A local socket in LISTEN state does not prove that a service is reachable from
another trust zone.

Likewise:

- a firewall rule does not prove that the expected packet path actually reaches it;
- a successful connection does not prove that it used the intended interface;
- an `open|filtered` UDP result does not prove that a service is open;
- a hostname can resolve differently depending on local DNS policy;
- a VPN/subnet-router client can silently change the route used by a test.

The audit therefore used **path validation plus reachability validation** rather
than treating a single scanner result as authoritative.

## Reference environment

The tested deployment included:

- ASUS TUF-AX5400 running Asuswrt-Merlin/GNUton;
- Tailscale with project-owned firewall policy;
- Pi-hole/FTL on a dedicated router-local LAN alias;
- Unbound on loopback;
- RouterCloud/Dufs on a separate router-local HTTPS alias;
- Dropbear SSH for trusted administration;
- syslog-ng forwarding to a Fedora workstation;
- Fedora-hosted Grafana, Loki, VictoriaMetrics, Alloy, Blackbox Exporter and
  related observability services.

Deployment-specific public addresses, DDNS names, tailnet addresses, device
identifiers, MAC addresses, credentials and exact administrative source
allowlists are intentionally omitted.

## Audit model

The tested trust paths were:

~~~text
trusted LAN peer
    |
    +--> router primary/service aliases
    |
    +--> Fedora LAN address

authorized Tailscale peer
    |
    +--> router Tailscale address
    |
    +--> controlled management entry point

non-authorized Tailscale peer
    |
    +--> router Tailscale address
    |
    +--> Fedora Tailscale address

external LTE/5G peer
    |
    +--> public IPv4 WAN address
~~~

The important distinction is that the audit did not assume these paths were
equivalent.

## Phase 1 — listener and firewall inventory

The first phase collected local socket state and firewall policy.

### Router observations

Expected project services included:

- DNS;
- router HTTPS;
- Pi-hole DNS and web UI on a dedicated alias;
- RouterCloud HTTPS on another dedicated alias;
- Dropbear SSH;
- Unbound on loopback;
- Tailscale dynamic listeners.

Additional firmware or optional-service listeners included:

- TCP/21 — vsftpd;
- TCP/5152 — envrams;
- TCP/7788 and UDP/7788 — cfg_server;
- TCP/18017 and UDP/18018 — wanduck;
- UDP/9999 — infosvr;
- UDP/5353 — mDNS/Avahi;
- UDP/59000 — firmware wireless/service process.

A key lesson from this phase was that several processes were bound to wildcard
addresses. Their real exposure therefore had to be measured from another host.

### Fedora observations

The Fedora monitoring stack was mostly loopback-bound.

Relevant network-visible exceptions included:

- syslog-ng on the Fedora Tailscale address, TCP/6514;
- GSConnect/KDE Connect on its desktop-integration port range;
- normal Tailscale transport listeners.

The Tailscale firewalld zone used a deny-oriented policy with a source-specific
allow rule for the router-to-Fedora syslog path.

## Phase 2 — full LAN TCP scan

A full TCP 1-65535 scan was performed from a separate LAN host against:

- the router primary LAN address;
- the Pi-hole service alias;
- the RouterCloud service alias.

The important result was not simply a count of open ports. It showed which
wildcard-bound services were actually reachable on each alias.

Confirmed LAN-reachable TCP services included:

| Port | Service / role | Audit status |
| ---: | --- | --- |
| 21 | vsftpd | REVIEW-HIGH |
| 53 | DNS | EXPECTED |
| 443 | router or RouterCloud HTTPS depending on address | EXPECTED |
| 1122 | Dropbear SSH | EXPECTED / VERIFY |
| 7788 | cfg_server | REVIEW |
| 8080 | Pi-hole web on its service alias | EXPECTED |
| 18017 | wanduck | REVIEW |

TCP/5152 was observed as filtered from the LAN despite the local listener,
corroborating the explicit firewall drop.

The application-specific aliases behaved as intended for their web surfaces:
the Pi-hole web UI and RouterCloud HTTPS endpoint remained associated with their
respective aliases.

## Phase 3 — service attribution and configuration review

Targeted service fingerprinting was correlated with the earlier local process
inventory.

This avoided a common mistake: treating scanner product guesses as authoritative.

Examples:

- Dropbear was confirmed from local process state rather than an Nmap service-name
  guess;
- firmware DNS identity was derived from the real local resolver process;
- TCP/7788 remained weakly fingerprinted remotely, but local evidence mapped it to
  cfg_server;
- TCP/18017 mapped to the ASUS wanduck service.

### FTP finding

FTP/21 became the highest-priority review item.

Observed configuration characteristics included:

- anonymous access disabled;
- local users enabled;
- writes enabled;
- TLS enabled;
- local-user chroot enabled;
- permissive local umask;
- weak/absent transfer and syslog auditing;
- no proven operational need at audit time.

The preferred remediation is not "add more hardening" by default. If the service
is unnecessary, disabling it removes more risk than incrementally hardening an
unused service.

## Phase 4 — targeted UDP validation

UDP was tested conservatively.

The audit explicitly treated:

~~~text
open|filtered
~~~

as **inconclusive**, not as proof of an open service.

Confirmed LAN-visible UDP surfaces included the expected DNS/DHCP paths plus
selected firmware/discovery services. SNMP and IKE/NAT-T test ports were closed
from the tested LAN vantage.

A full UDP 1-65535 scan was started but intentionally aborted after excessive
runtime relative to evidentiary value. Router health was checked afterward and
remained normal.

This decision was documented instead of hiding an incomplete test.

## Phase 5 — authorized Tailscale peer

An authorized Fedora peer was tested against the router Tailscale address.

The observed policy matched the design:

- DNS TCP/UDP 53: reachable;
- controlled management entry point TCP/8443: reachable;
- direct TCP/443: filtered;
- FTP/21: filtered;
- SSH/1122: filtered;
- TCP/5152: filtered;
- TCP/7788: filtered;
- Pi-hole web/8080: filtered;
- TCP/18017: filtered.

Functional DNS over both UDP and TCP succeeded, and the authorized management
entry point returned HTTP 200.

This was evidence that membership in the tailnet was not being confused with
unrestricted service access.

## Phase 6 — non-authorized Tailscale peer

A second Windows tailnet peer that was not in the router-management allowlist was
tested against the same router Tailscale address.

Expected result:

~~~text
DNS: allowed
management: denied
sensitive router services: denied
~~~

Observed result matched that policy.

DNS remained available, while the management entry point timed out and the
tested router services were unreachable.

This created an important positive/negative evidence pair:

~~~text
authorized peer     -> management allowed
non-authorized peer -> management denied
~~~

## Phase 7 — Fedora LAN exposure

A Windows LAN host was used to validate Fedora exposure.

The first result appeared to show that KDE Connect was unreachable. That result
was inconsistent with:

- an active local TCP/UDP listener;
- an effective nftables allow rule for the KDE Connect port range;
- successful local connection to the Fedora LAN address.

Routing inspection then revealed the real problem: Windows preferred an
advertised Tailscale subnet route for the LAN prefix.

A temporary host route was added through the Wi-Fi interface for the test and
removed immediately afterward.

With the correct physical-LAN path forced:

- ICMP to Fedora succeeded;
- KDE Connect TCP/1716 was reachable;
- Grafana TCP/3000 remained unreachable.

The corrected conclusion was therefore:

**intentional desktop integration reachable; monitoring stack isolated.**

## Phase 8 — Fedora Tailscale source restriction

The non-authorized Windows tailnet peer was tested against Fedora.

All tested monitoring/desktop ports were unreachable, including TCP/6514.

The positive allow case was then confirmed from the router itself: an established
router-to-Fedora TCP/6514 session was present and syslog-ng was running.

This produced another paired policy proof:

~~~text
router peer          -> Fedora TCP/6514 allowed
other tested peer    -> Fedora TCP/6514 denied
~~~

## Phase 9 — WAN firewall and NAT review

Before sending external probes, the router's own WAN policy was inspected.

Relevant observations included:

- remote web-management flag disabled;
- no explicit WAN HTTPS management port;
- no explicit WAN SSH enable value;
- non-LAN traffic traversing the WAN service chain;
- a final INPUT drop;
- explicit source restrictions on management ports;
- no ordinary WAN DNAT/port-forward rule in the active NAT inventory.

UPnP-related and virtual-server chains existed but contained no active runtime
mapping. No UPnP daemon was observed during the snapshot.

The configuration still reported UPnP enabled, so this remains a hardening review
item even though the active runtime state did not show a mapping.

## Phase 10 — proving that the test target is really public

The router WAN address was classified without recording the value.

The audit confirmed:

- the router WAN IPv4 was public;
- the router WAN IPv4 matched the Internet-visible IPv4;
- DDNS was configured.

This ruled out upstream RFC1918 NAT and CGNAT for the tested IPv4 path.

## Phase 11 — invalid WAN test and why it was rejected

The first supposed external test looked excellent: every tested TCP port timed
out.

It was still **invalid**.

Follow-up route diagnostics showed that:

- the router hostname had resolved to an internal LAN address;
- Windows selected a Tailscale subnet route;
- the selected source address belonged to Tailscale.

Therefore the "WAN" test had actually travelled through the overlay network.

The result was explicitly invalidated in the audit record.

This was one of the most important parts of the exercise because it demonstrates
why a security test must validate its own path.

## Phase 12 — corrected external route validation

The router hostname was then resolved through independent DNS-over-HTTPS
resolvers rather than the current system resolver.

Both external resolvers returned a public A record.

Windows route selection to that public target was checked before scanning:

- outgoing interface: phone-hotspot Wi-Fi;
- selected source: hotspot/mobile private address;
- next hop: hotspot gateway;
- Tailscale route: not used.

Only after this check was the external probe accepted as a WAN test.

## Phase 13 — final public-IPv4 TCP validation

The final external test ran through the verified LTE/5G hotspot path.

The following TCP ports were tested:

| Port | Purpose |
| ---: | --- |
| 21 | FTP |
| 22 | standard SSH control probe |
| 53 | DNS |
| 80 | HTTP |
| 443 | HTTPS |
| 1122 | router SSH |
| 5152 | firmware listener |
| 7788 | firmware service |
| 8080 | Pi-hole web |
| 8443 | controlled Tailscale management entry point |
| 18017 | firmware WAN-monitor service |

Every tested port returned:

~~~text
FILTERED_TIMEOUT
~~~

No tested TCP port returned OPEN.

The supported claim is therefore:

> The tested public-IPv4 TCP surface was externally filtered from the verified
> mobile-Internet path in the captured configuration snapshot.

It is deliberately **not** generalized to every TCP port or every protocol.

## Phase 14 — native WAN IPv6

The router was also checked for native WAN IPv6.

Observed state:

- IPv6 service disabled;
- IPv6 firewall enabled;
- no WAN IPv6 address;
- no IPv6 default route;
- IPv6 INPUT policy DROP.

Therefore there was no native routable WAN IPv6 target to scan in the current
configuration.

This is separate from Tailscale IPv6, which is handled by the project's own
fail-closed Tailscale IPv6 chain.

## Final assessment

### Overall result

**PASS with review findings.**

The tested security boundaries behaved as intended:

- peer-specific Tailscale management policy worked;
- Fedora syslog access was source-restricted;
- the Fedora monitoring stack was not LAN-exposed;
- the intended LAN desktop-integration service remained reachable;
- the tested public-IPv4 TCP surface was externally filtered;
- no native WAN IPv6 surface existed;
- no active UPnP/virtual-server mapping was observed.

### Review findings

| Priority | Finding | Recommended direction |
| --- | --- | --- |
| HIGH | FTP/21 LAN exposure | Disable if no explicit requirement exists |
| MEDIUM | cfg_server TCP/7788 | Validate firmware dependency and restrict if safe |
| MEDIUM | wanduck TCP/18017 + UDP/18018 | Validate necessity and exposure scope |
| MEDIUM | mDNS/5353 | Keep only where service discovery is required |
| MEDIUM | UPnP configured enabled | Disable if unnecessary; otherwise review secure-mode behavior |
| LOW / assurance gap | external WAN UDP | Do not claim closure without a conclusive external UDP test |

## What this audit demonstrates

The strongest portfolio value of the exercise is not the final word "PASS".

It demonstrates a repeatable security-engineering method:

1. inventory listeners;
2. inspect firewall and NAT ownership;
3. scan from the correct trust zone;
4. correlate scanner output with local process evidence;
5. test positive and negative identities;
6. validate routes before trusting remote results;
7. invalidate misleading evidence instead of rationalizing it;
8. retain explicit claim boundaries and unresolved findings.

## Claim boundary

This case study supports the claim that the **tested TCP surfaces and
identity-specific access paths were correctly restricted in the captured
2026-10-07 configuration snapshot**.

It does **not** claim:

- that every UDP service was externally tested;
- that every possible TCP port was tested from the Internet;
- that future UPnP mappings cannot appear;
- that later firmware changes cannot introduce new listeners;
- that the result applies to other ASUS models or firmware versions without
  revalidation.

Raw deployment-specific evidence remains private. The public version intentionally
preserves the methodology, security findings and validation logic while removing
infrastructure identifiers that would unnecessarily expand the public attack
surface.
