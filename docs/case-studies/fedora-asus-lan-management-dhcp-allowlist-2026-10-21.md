# Case study: Fedora loses LAN administration of ASUS despite working Wi-Fi and Internet

**Incident date:** 2026-10-21  
**Reference environment:** Fedora 44 (KDE/NetworkManager/systemd-resolved), ASUS TUF-AX5400 with GNUton Asuswrt-Merlin, Pi-hole/Unbound, Tailscale and project-managed firewall  
**Case state:** **INVESTIGATION OPEN — operator identifies intentional 5 GHz-only router administration; A/B validation still pending**  
**Evidence:** operator-provided terminal output and photographs, compared with earlier dated router security evidence. No new privileged live-router shell capture was available during this incident.

## Executive summary

The Fedora administrative workstation retained Internet access and could ping the ASUS gateway but could no longer connect to the router's LAN HTTPS panel or nondefault SSH port. An Android phone connected to ASUS Wi-Fi could open the router's HTTPS panel; the phone's exact radio/band was not established. A Fedora packet capture showed TCP SYN attempts and retransmissions without any router SYN-ACK or RST in the captured window.

**Operator correction after the packet-capture review:** router administration was intentionally permitted on the **5 GHz Wi-Fi network** but blocked for clients on the **2.4 GHz network**. Fedora was connected to the 2.4 GHz SSID during the failure. This is now the leading operator-identified explanation, pending a controlled 5 GHz reconnect and positive HTTPS/SSH test. The exact enforcement mechanism (per-SSID isolation/firewall policy versus source-IP allowlisting) remains to be verified.

A **separate relevant fact** emerged from the live DHCP WebUI screenshot: an existing `fedora-admin` manual reservation still maps a previously configured locally administered MAC to a historically approved LAN-admin IP, while Fedora's current 2.4 GHz connection uses a different locally administered MAC and received a different IP. This mismatch is real, but does **not** establish that DHCP drift independently caused the timeout; the access boundary may intentionally be based on the Wi-Fi/SSID path. On 2026-09-29 the team had installed an admin reservation and an ASUS `ACCESS_RESTRICTION` chain; its dated 2026-09-30 allowlist includes the reserved Fedora address. Do not override the active MAC or router reservation to fix a network-segmentation policy.

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

The Fedora NetworkManager active connection was the operator-identified **2.4 GHz SSID** during the timeout. The operator subsequently confirmed the intended policy: administrative access is only permitted from **5 GHz Wi-Fi**. This operator explanation fits the TCP symptom but has not yet been confirmed by a 5 GHz control test.

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

The Fedora active profile was the **2.4 GHz** SSID. After looking at the earlier tests, the operator pointed out that the deployment **deliberately restricts router administration to 5 GHz Wi-Fi**, keeping management unavailable to 2.4 GHz clients. That control, rather than an unexpected failure, may account for the observed no-response SYN pattern. **A switch-to-5 GHz confirmation test has not yet been submitted.**

The phone's DHCP WebUI screenshot showed the original `fedora-admin` manual reservation **still present**, contradicting the earlier suggestion that it was necessarily lost. The reserved MAC differs from both the Fedora's current locally administered Wi-Fi MAC and the factory hardware MAC. Fedora on the 2.4 GHz profile received a different lease. Those are factual observations, but do not prove which condition enforced the rejection. A 5 GHz profile can legitimately use a distinct, stable MAC/lease; source-IP and WLAN policy may coexist.

Do **not** infer that 2.4 GHz is inherently insecure, or that the radio band itself enforces authorization. The implementation could be SSID isolation, a guest-network rule, VLAN/firewall restrictions, or source-IP policy. Determine it from validated settings only if the access result is unexpected.

## 6. Safe validation and recovery — **5 GHz test pending**

No router or Fedora security settings need to change to test the operator-identified policy.

1. On Fedora, connect to the **already configured authorized 5 GHz SSID** (use the appropriate known Wi-Fi profile). Do not force a different MAC, assign a historical IP alias, or edit router DHCP/firewall rules.
2. Check the active SSID/profile, Wi-Fi MAC and IP lease. Confirm the local route to the ASUS router.
3. Test the router's currently configured LAN HTTPS service and the existing nondefault SSH port. A successful authenticated management session on **5 GHz** compared with the recorded 2.4 GHz timeouts would strongly support an intentional WLAN-specific access boundary.
4. If 5 GHz still times out, then inspect the existing `fedora-admin` DHCP reservation and the active `ACCESS_RESTRICTION` source allowlist (through an independently authorized management path). Do not assume the reserved MAC was lost: the operator's screenshot confirms the reservation is present.
5. Once access is restored, verify that 2.4 GHz still cannot administer the router, as an intentional **negative** security check. Do not loosen the policy to fix an access failure caused by selecting the wrong WLAN.

Only append a confirmed remediation and closed status after both positive 5 GHz and negative 2.4 GHz behavior are validated. Distinguish this incident from the separately resolved Tailscale DNS client issue.

## 7. Case outcome and evidence boundaries

**Confirmed:**
- Fedora's public DNS problem resolved after it stopped accepting Tailscale DNS; stable browsing was explicitly reported.
- Fedora reached the router at ICMP/L2 and had correct LAN routing, but captured management TCP attempts had no response.
- Android on ASUS Wi-Fi opened the HTTPS panel; the phone's exact Wi-Fi band was not established.
- Historical project evidence establishes a designed DHCP-reservation-plus-source-allowlist protection model and earlier negative tests exhibiting management timeouts.
- The phone's LAN DHCP settings show the original `fedora-admin` reservation is still present, while the current 2.4 GHz Fedora MAC and lease differ.
- The operator identifies intentional **5 GHz-only administration** as the previously overlooked network access constraint.
- The 2026-10-21 Tailscale installation healthcheck reported an enabled restriction and a populated rule list.

**Still unproven / OPEN:**
- Actual 5 GHz re-association and successful management tests, plus the current router rule that enforces the 2.4 GHz denial.
- Router-side `ACCESS_RESTRICTION` packet counters matching the Fedora failed attempts.
- Whether the relevant rule uses per-SSID policy, guest isolation, VLAN separation, source-IP restrictions, or a combination.
- Successful SSH/HTTPS restoration from Fedora; post-remediation healthcheck and persistence.
- Any causal link between the ASUS Tailscale 1.104.2 upgrade and administrative connectivity.

**Engineering lesson:** A working gateway ping, healthy services and a phone-accessible GUI do **not** prove the intended operator workstation is on an authorized *management network*. Before assuming failed services or lost DHCP reservations, inspect the active SSID/segment and the intentionally designed management boundary. If source-IP permissions are also used, keep the **MAC → DHCP reservation → lease → allowlist** mapping consistent. Do not weaken a functioning network boundary just to make tests pass.

This is an intentionally open incident report. Append a dated **resolution addendum** only after reconnection to authorized 5 GHz Wi-Fi, positive Fedora management tests, and preservation of the intended 2.4 GHz deny policy are demonstrated.
