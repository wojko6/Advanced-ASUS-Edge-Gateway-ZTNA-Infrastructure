# WebRTC Exit Node Leak Validation

## Purpose

Validate that browser WebRTC traffic does not expose the mobile carrier public IP address while an Android device is connected through the ASUS TUF-AX5400 Tailscale exit node.

## Test environment

- Client: Android phone
- Access network: mobile data (Wi-Fi disabled)
- VPN overlay: Tailscale
- Exit node: ASUS TUF-AX5400
- Test method: compare the normal public IP address with the public IP address reported by a WebRTC leak test

Public IP addresses recorded during the test are intentionally redacted in this repository documentation.

## Baseline — Tailscale disabled

With Wi-Fi disabled and the phone using only the mobile network:

- Normal public IP: **MOBILE_PUBLIC_IP**
- WebRTC public IP: **MOBILE_PUBLIC_IP**

The WebRTC result matched the active mobile connection, as expected when no VPN or exit node was in use.

## Tailscale exit-node test

Tailscale was enabled and the ASUS router was selected as the exit node while the phone remained connected through mobile data:

- Normal public IP: **HOME_EXIT_NODE_PUBLIC_IP**
- WebRTC public IP: **HOME_EXIT_NODE_PUBLIC_IP**

The WebRTC result matched the ASUS exit node's public egress address. The mobile carrier public IP observed in the baseline test was not exposed by WebRTC while the exit node was active.

## Result

**PASS — no WebRTC bypass of the tested Tailscale exit-node path was observed.**

For this test scenario, both ordinary browser traffic and the WebRTC test presented the same public IP address associated with the ASUS exit-node path. The mobile-network public IP from the baseline test did not appear in the WebRTC result after enabling Tailscale and selecting the ASUS exit node.

## Scope and limitations

This result documents one controlled validation performed on the tested Android/browser/network configuration. It should not be interpreted as proof that every browser, WebRTC implementation, network transition, or future software version can never leak addressing information.

The test should be repeated after material changes to the browser, Android networking configuration, Tailscale configuration, or exit-node policy.
