# Case study: Fedora loses LAN administration of ASUS despite working Wi-Fi and Internet

**Incident date:** 2026-10-21  
**Reference environment:** Fedora 44 (KDE/NetworkManager/systemd-resolved), ASUS TUF-AX5400 with GNUton Asuswrt-Merlin, Pi-hole/Unbound, Tailscale and project-managed firewall  
**Case state:** **OPERATIONALLY RESOLVED — 5 GHz administrative profile restored both HTTPS and SSH; exact enforcing firewall condition not yet isolated**  
**Evidence:** operator-provided terminal output and photographs, compared with earlier dated router security evidence. No new privileged live-router shell capture was available during this incident.

## Executive summary

The Fedora administrative workstation retained Internet access and could ping the ASUS gateway but could no longer connect to the router's LAN HTTPS panel or nondefault SSH port. An Android phone connected to ASUS Wi-Fi could open the router's HTTPS panel; the phone's exact radio/band was not established. A Fedora packet capture showed TCP SYN attempts and retransmissions without any router SYN-ACK or RST in the captured window.

**Operator correction and positive recovery:** router administration was intentionally used over the **5 GHz Wi-Fi profile**, while the Fedora **2.4 GHz profile** could not connect to router HTTPS/SSH. The operator then changed only the Fedora connection to the existing 5 GHz profile, recovered the historically reserved admin lease, and measured **HTTPS HTTP 200** and **SSH_ACCESS_OK**. The reported 2.4 GHz negative and 5 GHz positive demonstrate the **operational access-path distinction**. As the WLAN profile, client MAC and client IP changed together, the evidence **does not isolate** whether an SSID-specific firewall control, source-IP allowlist, or both enforced the denial.

A **separate relevant fact** emerged from the live DHCP WebUI screenshot: the existing `fedora-admin` manual reservation was still present, using a stable locally administered MAC and an address previously granted management rights. Fedora's 2.4 GHz profile used a **different** locally administered MAC and received a **different** IP; upon returning to the 5 GHz profile, Fedora recovered its **reserved admin IP**. No reservation or firewall modification was needed. This strongly supports **per-profile network identity and source address** as relevant, but alone does not prove whether the 2.4 GHz rejection was SSID-specific or simply the consequence of source-IP allowlisting. On 2026-09-29 the team installed the admin DHCP reservation and the ASUS `ACCESS_RESTRICTION` policy; a 2026-09-30 snapshot includes the reserved admin address.

The incident coincided with a **separate Fedora DNS failure**, which the operator resolved by disabling acceptance of Tailscale-supplied DNS. Restored web browsing did not restore router administration. These are two observed symptoms with different demonstrated fixes/diagnostic boundaries; neither is established as a regression caused by the ASUS Tailscale 1.104.2 rollout.

## 1. Intended security and addressing model

The reference topology places the administrative Fedora laptop and Android phone on ASUS Wi-Fi. The operator reports that only the intended 5 GHz administrative WLAN path grants router management; the 2.4 GHz WLAN intentionally does not. Fedora ordinarily obtains an address from router DHCP. The router runs a local HTTPS management service and SSH restricted to LAN on a nondefault port.

The security hardening from [Issue #127](../../evidence/2026-09-29/issue-127-lan-management-wan-exposure-hardening.md) intentionally:
- confirmed that Fedora's NetworkManager Wi-Fi MAC policy should remain stable for the configured SSID;
- created a dedicated DHCP reservation for the Fedora administration workstation;
- enabled the platform LAN `ACCESS_RESTRICTION` policy, allowing the selected client WebUI and SSH (access type `3`) and denying other LAN source addresses;
- retained separate source-scoped Tailscale management restrictions.

A later [2026-09-30 configuration snapshot](../../evidence/2026-09-30/webui-security-policy-drift-validation.md) recorded `ACCESS_RESTRICTION=1`, a nonempty rule list, and two explicitly allowed administrative LAN source addresses. Those addresses are intentionally **not recopied** into this public case study. On 2026-10-21, the phone's DHCP management screenshot **did** show a saved `fedora-admin` reservation to a historically approved administration IP and a locally administered MAC distinct from the current 2.4 GHz MAC. The exact live router-management rule set and how the two WLANs are distinguished have **not** been inspected.

Both controls matter: **administrative-WLAN admission policy** determines which Wi-Fi path may reach the router management plane, while **MAC → DHCP reservation → active lease → any applicable source-IP allowlist** must remain consistent for source-scoped administration. They should not be conflated.

## 2. First symptom: Internet by IP works, DNS fails on Fedora

The operator reported that the Android phone browsed normally on the same Wi-Fi while Fedora could ping a public IPv4 address yet could not resolve public names.

Measured Fedora observations:
- `ping -c 2 -W 2 1.1.1.1`: **2/2 replies**, 0% loss, approximately 10 ms average;
- `getent ahostsv4 example.com`: did not return an address in the bounded attempt;
- `resolvectl query example.com`: hung until interrupted;
- `resolvectl dns`: Wi-Fi DNS was the local Pi-hole listener, while `tailscale0` supplied `100.100.100.100`;
- `resolvectl domain`: `tailscale0` had the catch-all DNS route `~.`.

The operator ran:

```sh
sudo tailscale set --accept-dns=false
```

Websites immediately started loading, and the operator later explicitly confirmed stable Internet. This is **direct evidence for a client-side Tailscale/systemd-resolved DNS routing interaction** in the reported configuration. It does not establish that the upstream Pi-hole, Unbound, router DNS Guard or the router's newly installed Tailscale daemon failed. Disabling receipt of Tailscale DNS can impact MagicDNS resolution on that Fedora client.

## 3. Second symptom: router administration fails over the same working LAN

A read-only attempt to query syslog-ng on the ASUS via Fedora SSH failed with a TCP connection timeout on the known nondefault SSH port. The operator then tested the direct router IPv4 address from Fedora:

| Layer/test | Reported observation | What it establishes |
| --- | --- | --- |
| `ip -4 route get ROUTER_LAN_IP` | Directly through Wi-Fi device `wlp4s0`, current DHCP source address | Not using a Tailscale route to reach the router |
| Gateway IPv4 ICMP | 3/3 replies, average 1.42 ms | Basic bidirectional IP reachability |
| `ip neigh` | Gateway neighbor `REACHABLE` | Working local L2 neighbor discovery; not TCP acceptance |
| TCP/80, /443, /8443, /SSH-port | No successful connection | Does **not** prove every port is filtered: some may not listen |
| Router HTTPS from Android | Successful over ASUS Wi-Fi when the URL explicitly used `https://`; Android radio/band not recorded | Router HTTPS service is reachable from at least one other client |
| Fedora TCP/443 + SSH-port | Connection timeout | Likely silent discard or absent reply; exact reason remains open |

The prior phone test that returned `ERR_CONNECTION_REFUSED` was not equivalent to the later explicit **HTTPS** test. The router UI screenshot reported an HTTPS LAN listener on port 443 and SSH enabled for LAN on the configured nondefault port. Historical references to HTTPS port 8443 correspond to **earlier dated** settings; they are not evidence of today's port-443 listener configuration.

The Fedora NetworkManager active connection was the operator-identified **2.4 GHz SSID** during the timeout. The operator then selected the existing **5 GHz SSID** and reported a successful router HTTPS and SSH test without policy changes. Because source MAC/IP also changed with the profile, those results establish which **existing client profile** works; they do not prove radio-band enforcement independently of source-IP filtering.

The screenshot also showed a setting about allowing particular IP addresses under **remote/WAN administration**, apparently disabled. That must **not** be interpreted as proof that the independently documented platform **LAN `ACCESS_RESTRICTION`** policy is inactive. The successful Tailscale 1.104.2 rollout healthcheck earlier on 2026-10-21 separately reported the router management access restriction enabled and its rule list present, though it did **not** list authorized addresses.

## 4. Packet-level narrowing: SYN retransmissions without responses

On Fedora the operator captured the relevant packets on the Wi-Fi interface:

```sh
sudo tcpdump -ni wlp4s0 \
  'host ROUTER_LAN_IP and tcp and (port 443 or port 1122)'
```

The anonymized pattern was:

```text
FEDORA:ephemeral > ASUS:443   Flags [S]
FEDORA:ephemeral > ASUS:443   Flags [S]  (retry)
FEDORA:ephemeral > ASUS:1122  Flags [S]
FEDORA:ephemeral > ASUS:1122  Flags [S] (retries)
# No SYN-ACK or RST from ASUS to these connection attempts in the captured output
```

This supports the narrower conclusion that **Fedora transmitted the TCP connection requests but saw no answer on the capture interface within the observation window**. It does not locate the packet drop definitively. Plausible domains include ASUS filter rules, per-client restrictions, Wi-Fi/client isolation logic or a less likely return-path problem. A router-side chain counter, if safely readable through an already authorized channel, would be stronger attribution evidence.

The client capture used port-name resolution, rendering port 1122 with a service name; that display label is not protocol proof. Repeating with `tcpdump -nn` would show numeric ports directly.

## 5. Operator-identified WLAN administration boundary, with a separate DHCP discrepancy

The Fedora active profile was the **2.4 GHz** SSID. After looking at the earlier tests, the operator pointed out that the deployment **deliberately uses the 5 GHz Wi-Fi profile for administration**, while the tested 2.4 GHz profile does not have management access. The subsequent switch to 5 GHz **did restore both admin services**, establishing a straightforward operational resolution without changing the router. The captured SYN timeouts reflect the denied/nonresponsive 2.4 GHz client path, not evidence of a service outage.

The phone's DHCP WebUI screenshot showed the original `fedora-admin` manual reservation **still present**, contradicting the earlier suggestion that it was necessarily lost. The reserved MAC differs from both the Fedora's current locally administered Wi-Fi MAC and the factory hardware MAC. Fedora on the 2.4 GHz profile received a different lease. Those are factual observations, but do not prove which condition enforced the rejection. A 5 GHz profile can legitimately use a distinct, stable MAC/lease; source-IP and WLAN policy may coexist.

Do **not** infer that 2.4 GHz is inherently insecure, or that the radio band itself enforces authorization. The implementation could be SSID isolation, a guest-network rule, VLAN/firewall restrictions, or source-IP policy. Determine it from validated settings only if the access result is unexpected.

## 6. Recovery completed — no router settings changed

The operator reconnected Fedora using the **existing 5 GHz administrative Wi-Fi profile** and collected:

```text
ACTIVE_CONNECTION=Orange_[SSID REDACTED]_5GHz
WIFI_MAC=locally administered; matches the active 5 GHz profile
IPv4=historically reserved Fedora admin LAN address
HTTPS_ASUS=HTTP_CODE=200
SSH_ASUS=SSH_ACCESS_OK
```

For comparison, the earlier captured **2.4 GHz** profile had another locally administered MAC and DHCP lease, and its connection attempts to router HTTPS/SSH timed out. The DHCP WebUI screenshot confirmed the historical `fedora-admin` reservation remained present; the recovered 5 GHz IP agrees with that reservation.

**Operator actions:** changed Wi-Fi connection/profile and executed read-only HTTPS/SSH checks. **Not performed:** router reboot, NVRAM edit, DHCP reservation change, firewall flush or allowlist relaxation, manual static IP or MAC override. HTTPS and SSH were operationally recovered.

The 2.4 GHz negative result preceded the successful 5 GHz test, rather than a later controlled repeat. A future router-side read-only review may establish whether the observed denial is the effect of stock ASUS `ACCESS_RESTRICTION`, an explicit Wi-Fi/SSID restriction, or both. Do not claim a clean single-variable 2.4-versus-5 GHz test because NetworkManager used different source MACs and IPs across the profiles.

**Optional nonblocking follow-up:** verify persistent management reachability after a normal reconnect/reboot, and review the corresponding `ACCESS_RESTRICTION` counters or Wi-Fi access configuration if documenting the precise enforcement mechanism is required. The incident itself requires no further production changes.

## 7. Case outcome and evidence boundaries

**Confirmed:**
- Fedora's public DNS problem resolved after it stopped accepting Tailscale DNS; stable browsing was explicitly reported.
- Fedora reached the router at ICMP/L2 and had correct LAN routing, but captured management TCP attempts had no response.
- Android on ASUS Wi-Fi opened the HTTPS panel; the phone's exact Wi-Fi band was not established.
- Historical project evidence establishes a designed DHCP-reservation-plus-source-allowlist protection model and earlier negative tests exhibiting management timeouts.
- The phone's LAN DHCP settings show the original `fedora-admin` reservation is still present, while the current 2.4 GHz Fedora MAC and lease differ.
- The operator identifies the configured **5 GHz administrative Wi-Fi profile** as the intended router-management path.
- Reconnecting Fedora to that profile restored the historical reserved admin IP, router HTTPS **HTTP 200** and SSH **SSH_ACCESS_OK**, without router-side changes.
- The 2026-10-21 Tailscale installation healthcheck reported an enabled restriction and a populated rule list.

**Unverified implementation/persistence details (not blockers to the operational fix):**
- Router-side `ACCESS_RESTRICTION` counters for the Fedora 2.4 GHz source and the exact applied deny/accept mechanism.
- Whether the restriction is based specifically on SSID, on source-IP allowlisting, or both: the two tested profiles used different MACs and IPs.
- Persistence after a later router reboot or fresh DHCP lease; no reboot was needed during recovery.
- Any causal link between the ASUS Tailscale 1.104.2 upgrade and the administrative timeouts: none demonstrated.

**Engineering lesson:** A working gateway ping, healthy services and a phone-accessible GUI do **not** prove the intended operator workstation is on an authorized *management network*. Before assuming failed services or lost DHCP reservations, inspect the active SSID/segment and the intentionally designed management boundary. If source-IP permissions are also used, keep the **MAC → DHCP reservation → lease → allowlist** mapping consistent. Do not weaken a functioning network boundary just to make tests pass.

**Operational resolution recorded 2026-10-21:** the working 5 GHz profile regained both admin access paths, while the previous 2.4 GHz access failure remains preserved as negative evidence. Exact router-side enforcement semantics and reboot persistence are not yet separately established. No security relaxation was applied.
