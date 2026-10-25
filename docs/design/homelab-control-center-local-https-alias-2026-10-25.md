# Homelab Control Center — proposed operator-local HTTPS name

> Date: 2026-10-25
>
> **Status: DRAFT PROPOSAL ONLY / NOT CONFIGURED / DEPLOYMENT_GATE=HOLD.**
> No live DNS, /etc/hosts, Caddy, systemd, HTTPS trust-store, Tailscale or application configuration has been changed by this document.
> Tracks [#303 Homelab Control Center](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/303); existing operator-local Grafana and Pi-hole precedents are [monitoring/caddy/README.md](../../monitoring/caddy/README.md) and [monitoring/caddy/Caddyfile](../../monitoring/caddy/Caddyfile).

## User-facing goal

Use **`https://control.home.arpa/`** on the **Fedora operator workstation only**, similarly to the *existing* local-only URLs `https://grafana.home.arpa/` and `https://pihole.home.arpa/`. Do not introduce a DNS entry in the ASUS/Pi-hole/Unbound production chain merely for this operator-local alias.

The panel remains an opt-in, foreground V0.2 **read-only lab** and still requires an operator-started `127.0.0.1:8788` backend. A friendly HTTPS name **does not** imply a resident service, automatic start, remote availability or production security acceptance.

## Proposed local request path

```text
Fedora Brave: https://control.home.arpa/
     | /etc/hosts only: control.home.arpa -> 127.0.0.1
     v
Fedora Caddy: 127.0.0.1:443, tls internal
     | HTTPS terminated / re-proxy only on loopback
     | upstream Host rewritten to 127.0.0.1:8788
     v
Control Center V0.2: 127.0.0.1:8788, foreground/non-root
     | strictly fixed PromQL aggregate GETs only
     v
VictoriaMetrics: 127.0.0.1:8428
```

This approach follows the existing Caddy scheme already used for Grafana and Pi-hole. It does **not** grant clients in the LAN, authorized Tailscale peers or WAN access to Control Center. The name `home.arpa` also occurs in router-managed split DNS for other *separate* services, but the proposed Control Center alias is **not** a router-side DNS record: only this Fedora operator workstation's `/etc/hosts` should resolve it to loopback.

## Illustrative Caddy site block — **NOT APPLIED**

```caddyfile
https://control.home.arpa {
    bind 127.0.0.1
    tls internal

    reverse_proxy 127.0.0.1:8788 {
        # V0.2's deliberate Host allowlist accepts the backend identity only.
        header_up Host 127.0.0.1:8788
    }
}
```

**Critical:** keep `Origin` and `Sec-Fetch-Site` headers from the actual browser request. Do not overwrite, suppress or spoof them as `same-origin` in the proxy to bypass the V0.2 backend's cross-site API checks. Neither `0.0.0.0`, `::`, LAN binding nor `tailscale serve` is equivalent to this loopback-only contract.

Caddy has a pre-existing site bound to loopback TCP/443, so adding another SNI hostname is architecturally reasonable. Actual Caddy version, active config and trust must be verified on the operator host before editing its live config. **Do not replace the active /etc/caddy/Caddyfile with the repository template**; the live Grafana/Pi-hole routes and CA may contain post-checkpoint changes. Review a minimal additive edit against the actual file, with a restorable backup and `caddy validate` before any reload.

The local name would be installed *only after a separate explicit operator approval* by adding:

```text
127.0.0.1 control.home.arpa
```

to the Fedora workstation's `/etc/hosts`. No router Pi-hole Local DNS Record, dnsmasq override, Unbound zone or Tailscale MagicDNS setting is necessary or approved.

## Preconditions for any later operator-approved activation

1. Read-only discovery: verify existing Caddy binds **only** `127.0.0.1:443` and still handles `grafana.home.arpa` and `pihole.home.arpa` without changes; check the current `/etc/hosts` to avoid duplicate/mismatched names. Do not expose local interface IPs or production Caddy config in public issues.
2. Validate `control.home.arpa` does not conflict with an existing local or managed name. Its hosts override must map to **loopback**, not a router/host LAN IP.
3. Capture and protect the current Caddy configuration, verify the new site with `caddy validate`, and design an immediate rollback that restores the exact old config without disrupting the other existing sites. **No reload is authorized by this design.**
4. Ensure the existing Caddy internal CA is actually trusted by **Brave** for the new hostname; adding a new local certificate should not require installing a new trusted private key or exporting any Caddy CA material.
5. Foreground-start the Control Center backend as the **normal non-root operator** on `127.0.0.1:8788`; the proxy must return a clear unavailable error if the lab is stopped. No systemd unit, cron timer or auto-start.
6. After explicit approval, test `GET /` and `GET /api/summary` through the **HTTPS name** with genuine browser and existing CA trust; verify safe same-origin fetch and correct status, not a misleading green fallback. Require negative checks for incorrect Host/Origin, non-loopback listener, denied mutation methods and attempted cross-site API fetch. Failure must not expose VM labels or other data.
7. Confirm existing Grafana and Pi-hole frontends remain functional, and **no access** from an unrelated LAN/Tailscale/WAN client to the new alias is introduced. SNI/DNS and loopback-only checks must be independently verified.

## Security limitations

- An operator-local, **unauthenticated** Caddy frontend is only a cosmetic convenience layer over the existing local read-only lab. It **does not authenticate local users**; other local processes or users on the workstation may be able to connect. On a shared host, add an explicitly designed authentication/authorization gate before claiming user isolation.
- The V0.2 backend's strict `Host` check would currently reject `control.home.arpa:8788` directly. The **only** proposed upstream rewrite is `Host: 127.0.0.1:8788`. No backend allowlist broadening, automatic redirects or exposure of raw query endpoints is required.
- The backend's `Origin` condition currently allows no Origin or a direct local HTTP Origin. Standard same-origin browser GET requests generally omit `Origin`; nevertheless, real HTTPS-through-proxy browser behavior **must be tested**, and any rejection should fail closed pending a reviewed fix. Never hide mismatched Origin by rewriting browser security headers.
- The existing Caddy trusted internal CA and port 443 are shared operational dependencies. A careless Caddy reload could affect existing Pi-hole and Grafana frontends, **even with no changes to those backend services**. This is why configuration activation must be independently authorized.
- No claim of readiness for outside-workstation access, source-by-source monitoring health, whole-host isolation, boot-persistent availability, full security review, or Black Box #304.

## Decision and exit gate

**Proposed friendly name:** `https://control.home.arpa/`  
**Scope:** Fedora operator workstation only, HTTPS through pre-existing loopback Caddy  
**Current status:** documentation-only, not yet reachable, no runtime mutation  
**Gate:** HOLD until source/doc review, explicit operator permission for local Caddy/hosts configuration, actual host preflight and verified rollback

A future implementation PR may add Caddy configuration material after the operator confirms the current live Caddy state. Merely merging this design document **must not** trigger Caddy reload, automatic deployment or DNS mutation.
