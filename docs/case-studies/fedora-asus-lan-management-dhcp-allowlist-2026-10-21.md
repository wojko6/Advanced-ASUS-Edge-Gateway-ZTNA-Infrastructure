# Case study: Fedora loses LAN administration of ASUS despite working Wi-Fi and Internet

**Incident date:** 2026-10-21  
**Reference environment:** Fedora 44 (KDE/NetworkManager/systemd-resolved), ASUS TUF-AX5400 with GNUton Asuswrt-Merlin, Pi-hole/Unbound, Tailscale and project-managed firewall  
**Case state:** **INVESTIGATION OPEN — probable DHCP reservation / source allowlist mismatch, not yet proven or remediated**  
**Evidence:** operator-provided terminal output and photographs, compared with earlier dated router security evidence. No new privileged live-router shell capture was available during this incident.

## Executive summary

The Fedora administrative workstation retained Internet access and could ping the ASUS gateway but could no longer connect to the router's LAN HTTPS panel or nondefault SSH port. An Android phone on the **same Wi-Fi** could open the router's HTTPS panel. A Fedora packet capture showed TCP SYN attempts and retransmissions without any router SYN-ACK or RST in the captured window.

The most likely explanation is that the Fedora host's **current DHCP-assigned IPv4 address no longer matches the permitted LAN management source address(es)**. On 2026-09-29, the team deliberately created a DHCP reservation for the Fedora workstation and enabled a stock ASUS `ACCESS_RESTRICTION` chain, which limits HTTPS/SSH to authorized LAN sources and ends in DROP. On 2026-09-30, a dated router snapshot listed two allowed LAN-admin addresses. Neither was the current address observed during this incident. However, **neither the live October 21 DHCP reservation/MAC mapping nor the live `ACCESS_RESTRICTION` rules/counters have yet been inspected**. A reservation mismatch is therefore a leading hypothesis, **not a confirmed root cause**.

The incident coincided with a **separate Fedora DNS failure**, which the operator resolved by disabling acceptance of Tailscale-supplied DNS. Restored web browsing did not restore router administration. These are two observed symptoms with different demonstrated fixes/diagnostic boundaries; neither is established as a regression caused by the ASUS Tailscale 1.104.2 rollout.

## 1. Intended security and addressing model

The reference topology places the administrative Fedora laptop and Android phone on the ASUS LAN/Wi-Fi. Fedora ordinarily obtains an address from router DHCP. The router runs a local HTTPS management service and SSH restricted to LAN on a nondefault port.

The security hardening from [Issue #127](../../evidence/2026-09-29/issue-127-lan-management-wan-exposure-hardening.md) intentionally:
- confirmed that Fedora's NetworkManager Wi-Fi MAC policy should remain stable for the configured SSID;
- created a dedicated DHCP reservation for the Fedora administration workstation;
- enabled the platform LAN `ACCESS_RESTRICTION` policy, allowing the selected client WebUI and SSH (access type `3`) and denying other LAN source addresses;
- retained separate source-scoped Tailscale management restrictions.

A later [2026-09-30 configuration snapshot](../../evidence/2026-09-30/webui-security-policy-drift-validation.md) recorded `ACCESS_RESTRICTION=1`, a nonempty rule list, and two explicitly allowed administrative LAN source addresses. Those addresses are intentionally **not recopied** into this public case study. As of 2026-10-21, the actual permitted source set and reserved MAC-to-IP associations are **not yet directly observed**.

This design is safe only while **address reservation, active client MAC identity, current DHCP lease and the firewall's authorized source addresses remain consistent**.

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
| Router HTTPS from Android | Successful on same Wi-Fi when the URL explicitly used `https://` | Router HTTPS service is reachable from at least one other client |
| Fedora TCP/443 + SSH-port | Connection timeout | Likely silent discard or absent reply; exact reason remains open |

The prior phone test that returned `ERR_CONNECTION_REFUSED` was not equivalent to the later explicit **HTTPS** test. The router UI screenshot reported an HTTPS LAN listener on port 443 and SSH enabled for LAN on the configured nondefault port. Historical references to HTTPS port 8443 correspond to **earlier dated** settings; they are not evidence of today's port-443 listener configuration.

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

## 5. Why a DHCP reservation mismatch is the leading hypothesis

This installation already had a **deliberate** policy of mapping one administrative workstation to a predictable address before enabling a source-IP-based administrative allowlist.

The October 21 Fedora interface snapshot showed a **currently leased IP outside the earlier recorded administrative source addresses**. This is consistent with both the HTTPS and SSH timeouts and with the deliberately denied negative tests previously performed for Issue #127. The fact that Android HTTPS still worked makes a system-wide httpd outage less likely.

The discrepancy could be caused by **any** of the following; none is verified:
- a DHCP reservation lost or altered after a settings reset/import or later reconfiguration;
- a client MAC-address change (for example NetworkManager Wi-Fi cloned/stable MAC settings or a different adapter/profile);
- a mismatch between the saved reservation and the actual active Wi-Fi MAC;
- a manual change to the management allowlist not reflected in older public evidence;
- a separate firewall/policy issue that happens to produce the same TCP symptoms.

A normal **router reboot** should not itself erase a persistently saved DHCP reservation; a factory reset or restoration of different NVRAM settings can change it. In the absence of MAC and live DHCP/NVRAM evidence, do not assert which event occurred.

## 6. Safe recovery workflow — **planned, not yet executed**

The next operator action should use the still-working HTTPS management session on the phone (or equivalent independent local management path), **without disabling all security rules**:

1. On Fedora, collect only the active Wi-Fi MAC identity, NetworkManager connection/profile name and current DHCP address using `nmcli`. Do not post a full MAC address to public issue text or evidence.
2. On ASUS, review **LAN → DHCP Server → manually assigned addresses**. Match the real current Fedora Wi-Fi MAC against the reservation. Review the **actual LAN management access restriction rule list** using the authorized router management interface; do not infer it from the remote/WAN controls screenshot.
3. If a mismatch is proven, reconcile the **one** reservation/MAC binding with the intended administrative IP. Verify the target address is free and is not another device's reservation. Preserve existing administrator rules; make the narrowest change possible. Have local recovery access before applying a firewall change.
4. Renew/reconnect only Fedora's affected Wi-Fi connection **after** saving the corrected reservation. Revalidate current address and direct route before retrying SSH.
5. From Fedora, test HTTPS on the *current* configured LAN port, and SSH on the configured nondefault port. Confirm at least one authenticated administrative session and check that an unauthorized client is still denied. Do not call the incident fixed until **both** expected positive management paths return.
6. If the source/IP mapping was already correct, proceed with authorized **read-only** inspection of `iptables -nvL ACCESS_RESTRICTION`, NVRAM access-restriction state and management listeners; do not flush the firewall, change `iptables` from another service or reset router configuration by guesswork.

Temporary aliases or forcibly assigning a historically allowed IPv4 address without first identifying its reserved owner can create an IP conflict and obscure the real failure. Do not use this as a blind workaround.

## 7. Case outcome and evidence boundaries

**Confirmed:**
- Fedora's public DNS problem resolved after it stopped accepting Tailscale DNS; stable browsing was explicitly reported.
- Fedora reached the router at ICMP/L2 and had correct LAN routing, but captured management TCP attempts had no response.
- Android on the same Wi-Fi opened the ASUS HTTPS panel.
- Historical project evidence establishes a designed DHCP-reservation-plus-source-allowlist protection model and earlier negative tests exhibiting management timeouts.
- The 2026-10-21 Tailscale installation healthcheck reported an enabled restriction and a populated rule list.

**Still unproven / OPEN:**
- Live 2026-10-21 DHCP reservation, Wi-Fi MAC mapping, and exact permitted management IPs.
- Router-side `ACCESS_RESTRICTION` packet counters matching the Fedora failed attempts.
- Whether the problem began at a reboot, firmware NVRAM import, client MAC change, or other event.
- Successful SSH/HTTPS restoration from Fedora; post-remediation healthcheck and persistence.
- Any causal link between the ASUS Tailscale 1.104.2 upgrade and administrative connectivity.

**Engineering lesson:** A successful router service healthcheck, functional gateway ping and even a phone-accessible GUI do **not** prove that the intended administrative workstation can still reach the management plane. Source-IP-based security requires a maintained **MAC → DHCP reservation → active lease → management allowlist** invariant; testing this invariant prevents an apparently healthy gateway from becoming unmanageable from its primary workstation.

This is an intentionally open incident report. Append a dated **resolution addendum** only after the actual reservation/allowlist mismatch and restored Fedora access are demonstrated.
