# Homelab Control Center — operator-local HTTPS alias

> Date: 2026-10-25
> **Follow-up (2026-10-26):** the existing **Fedora-local-only** Caddy alias was also used with a **manually started V0.3** backend on `127.0.0.1:8788`. Both fixed HTTPS APIs returned bounded live telemetry; one crafted cross-site request returned HTTP 403. V0.3 source [#312](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/312) and [#313](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/313) is **merged**, but this does not add HCC autostart, modify Caddy, create router/Pi-hole DNS records, or authorize remote access. The V0.2 explanation below is the historical October 25 activation scope; see [V0.3 details](../../experiments/fedora/homelab-control-center-v0.1/V0.3-DNS-GUARD-PREFLIGHT.md).
>
> **Status (operator report, 2026-10-25): FEDORA-LOCAL HTTPS ALIAS ACTIVATED / BROWSER ACCESS REPORTED WORKING / BACKEND AUTOSTART=NO / APP DEPLOYMENT_GATE=HOLD.**
> Earlier work was documentation/staging only. The operator has since explicitly run a guarded local activation, changing **Fedora** `/etc/hosts` and `/etc/caddy/Caddyfile` and reloading **Caddy only**. No ASUS, Pi-hole DNS, Unbound, Tailscale or HCC service-autostart configuration change is reported.
> Tracks [#303 Homelab Control Center](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/303); existing operator-local Grafana and Pi-hole precedents are [monitoring/caddy/README.md](../../monitoring/caddy/README.md) and [monitoring/caddy/Caddyfile](../../monitoring/caddy/Caddyfile).

## User-facing goal

Use **`https://control.home.arpa/`** on the **Fedora operator workstation only**, similarly to the *existing* local-only URLs `https://grafana.home.arpa/` and `https://pihole.home.arpa/`. Do not introduce a DNS entry in the ASUS/Pi-hole/Unbound production chain merely for this operator-local alias.

The panel remains an opt-in, foreground V0.2 **read-only lab** and still requires an operator-started `127.0.0.1:8788` backend. A friendly HTTPS name **does not** imply a resident service, automatic start, remote availability or production security acceptance.

## Operator-local request path

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

## Caddy site block — operator-reported as activated

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

## Operator-confirmed browser access — 2026-10-25

After successful guarded Caddy reload and the SNI/HTTP smoke tests, the operator opened the new Control Center address and reported **“Działa” (works)** in the browser. This completes the agreed **operator-local friendly-URL smoke checkpoint** at the level actually reported: the HTTPS hostname can be used to access the application on the Fedora workstation.

**Evidence limits:** the brief confirmation does **not** separately record a screenshot, browser TLS security UI, an explicit fresh `/api/summary` response through Caddy, the refreshed scrape-target count, repeat browser checks for Grafana and Pi-hole, or long-running uptime. Therefore these individual properties should **not** be marked as independently verified by the reply alone. The earlier bounded activation helper did report SNI routes `control:200`, `grafana:302`, `pihole:302`. No HTTPS alias failures have been reported.

**Scope:** local-only Caddy HTTPS and `/etc/hosts` activation is complete; neither backend autostart nor permanent application deployment is enabled. No router/DNS changes, Tailscale exposure, LAN/WAN listener or HCC service installation is implied. `DEPLOYMENT_GATE=HOLD` for broader deployment. The documentation PR can be reviewed/merged separately; merging a document **must not** alter live configuration.

## Operator-confirmed Fedora-local activation checkpoint — 2026-10-25

**Source:** the operator's captured terminal output of `hcc-control-home-arpa-activate-v1.py` on the Fedora workstation. This is **operator-reported runtime evidence**, not a claim of access to the private host by the GitHub reviewer.

| Check | Evidence |
| --- | --- |
| Guarded helper self-tests | `SELFTEST_RESULT=14/14` |
| Caddy candidate scope | `CANDIDATE_DELTA=EXACT_9_LINE_APPEND` |
| Pre-apply config parity | `SOURCE_RUNTIME_PARITY=MATCH` |
| Candidate validation | `CANDIDATE_VALIDATE=PASS` |
| Privileged activation | `--apply --confirm-local-caddy-reload` explicitly run by operator |
| Private rollback backup | `BACKUP_DIRECTORY` printed and retained **on Fedora**; private absolute path intentionally excluded from public repository |
| Control Center SNI HTTPS route | `control.home.arpa:200` |
| Existing Grafana SNI route | `grafana.home.arpa:302` |
| Existing Pi-hole SNI route | `pihole.home.arpa:302` |
| Local-only activation verdict | `ACTIVATION=PASS_FEDORA_LOCAL_ONLY` |
| Brave certificate trust | `BROWSER_TLS_TRUST=REQUIRES_MANUAL_BRAVE_CHECK` |
| Permanent backend startup | `BACKEND_AUTOSTART=NO` |
| ASUS configuration changes | `NO_ASUS_CONFIG_CHANGES=YES` |

**Scope of acceptance:** This verifies the helper's bounded local activation and route-level responses; a 200 or 302 alone does **not** prove valid Firefox/Brave user trust, full application rendering, successful browser `GET /api/summary`, new TLS certificate-chain validation, end-to-end source freshness or long-duration health. On failure of later checks, use the protected operator-local rollback directory and the previously staged `--rollback` procedure; never post the path or copy private data to the public repo.

**Next manual browser check (no more system writes):** With the non-root HCC `127.0.0.1:8788` backend running, open `https://control.home.arpa/` in Brave. Confirm no certificate interstitial, the app renders, `GET /api/summary` is accepted same-origin through Caddy and the visible real VM tile matches the API response (currently healthy scrape targets might differ from earlier 7/7). Grafana and Pi-hole should still be manually visited to verify user-facing behavior. Do not weaken TLS verification or rewrite `Origin` / `Sec-Fetch-Site` to make a failed browser check pass.

**Security/deployment boundary:** Fedora's HTTPS alias is now operational at the checked route level. It remains **local**, **unauthenticated**, and **manually served**. No DNS entries on the ASUS, Pi-hole/Unbound service changes, Caddy LAN/Tailscale exposure, auto-start or permanent HCC daemon were approved. `DEPLOYMENT_GATE=HOLD` for app deployment and remote access.

## Operator-verified active Caddy configuration parity — 2026-10-25

The operator ran a **read-only** Caddy source/runtime preflight on Fedora and provided this bounded output:

```text
CADDY_SOURCE_ADAPT=PASS
CADDY_ACTIVE_CONFIG=READABLE
SOURCE_RUNTIME_PARITY=MATCH
NO_CONFIG_WRITES=YES NO_RELOAD=YES ASUS_CONTACTED=NO
DEPLOYMENT_GATE=HOLD
```

This supplements the earlier preflight (15/15 synthetic tests; Caddy `ACTIVE`; port 443 and HCC backend 8788 `LOOPBACK_ONLY`; local `control.home.arpa` alias and Caddy control site absent; existing Grafana/Pi-hole site blocks present). It establishes that the **adapted on-disk Caddyfile matched the actively reported configuration at the moment of measurement**. It does not establish browser certificate trust or reverse-proxy Host/Origin compatibility.

### Candidate-only staging gate (before any activation)

A locally generated Fedora-only stage helper is available for operator review in the current working conversation. It has `--self-test`, `--inspect` and `--stage` modes; its local tests returned **12/12 PASS**. The helper does not run `sudo`, write under `/etc`, reload Caddy, access ASUS or make external network requests. `--stage` repeats active parity and loopback checks, generates a private candidate Caddyfile by **appending** the reviewed control site to the *actual* current Fedora Caddyfile, records a `127.0.0.1 control.home.arpa` hosts-entry hint, and runs `caddy adapt` against that candidate only.

**Not an activation instruction:** the locally generated helper is not bundled or pinned in this document. Inspect the actual source supplied to the operator before invoking it; do not assume that any file named similarly is a trusted deployment artifact. Never copy the candidate into `/etc/caddy/Caddyfile` or edit `/etc/hosts` just because staging reports success. The next separate approval requires a least-change backup/validate/reload/rollback plan protecting the existing Grafana and Pi-hole sites.

**Historical staging status:** source/runtime parity `MATCH`; `control.home.arpa` was **not active yet** at this checkpoint. See the dated operator activation checkpoint below.

## Operator-verified staged candidate — 2026-10-25

The operator ran the separate, **staging-only** Python helper. Output establishes:

| Gate | Operator-reported evidence |
| --- | --- |
| Synthetic helper tests | `SELFTEST_RESULT=12/12` |
| Caddy source/runtime parity | `SOURCE_RUNTIME_PARITY=MATCH` |
| Existing local sites | Existing Caddy source confirmed, alias absent |
| Caddy HTTPS and HCC backend listeners | Both `LOOPBACK_ONLY` (443 and 8788) |
| Candidate syntax/adaptation | `CANDIDATE_ADAPT=PASS` |
| Private staged files | Fresh operator-owned directory `0700`, candidate and hosts hint each `0600` |
| Changes to operating system | `NO_ETC_CHANGES=YES`, `NO_RELOAD=YES`, `NO_DNS_CHANGES=YES` |

The staging directory path is deliberately excluded from public documentation. The **on-disk candidate's full contents have not been independently inspected via this repository**; on-host review of the diff, running Caddy, and the alias entry remains a separate activation gate.

### Pre-activation checklist — historically used as the gate

The following safety checklist was defined **before** the operator exercised the explicit Fedora-local activation on 2026-10-25; retain it for audits, future reapplication and rollback:

1. **No root to inspect.** Compare the staged `Caddyfile.candidate` against **the current** `/etc/caddy/Caddyfile`; require **only one additive site block** for `control.home.arpa`, containing `bind 127.0.0.1`, `tls internal` and `reverse_proxy 127.0.0.1:8788` with upstream Host explicitly set to `127.0.0.1:8788`. Abort if the live file changed since staging or unexpected site/config edits appear.
2. **Reconfirm parity:** `caddy adapt --config /etc/caddy/Caddyfile --adapter caddyfile` must correspond to the active local admin `GET 127.0.0.1:2019/config/` before changing any file; also verify no existing hosts alias, non-loopback Caddy listener, site conflict or unexpected imports.
3. **Validate candidate independently:** `caddy validate --config <staged-candidate> --adapter caddyfile` should succeed without modifying the live service. Refuse validation errors and unexpected changes. The previously passing `caddy adapt` is **not** an activation validation.
4. **Review full rollback first:** preserve a root-controlled, non-world-readable **restorable backup of both** the existing `/etc/caddy/Caddyfile` and `/etc/hosts`, including permissions/ownership; record their hashes; confirm a testable procedure to restore these exact files and reload **only Caddy** on failure. Do not replace the entire live Caddyfile with a stale repository template.
5. **Explicit operator opt-in:** only at this step apply the validated additive Caddyfile and the **Fedora-only** `127.0.0.1 control.home.arpa` hosts alias. Do not modify ASUS/Pi-hole DNS, Unbound, public firewall or Tailscale.
6. **Controlled reload and read-only checks:** validate the installed Caddy source before an explicit `systemctl reload caddy`. Confirm the new SNI site is still bound only on loopback; test HTTPS certificate trust in Brave and `GET /` plus `GET /api/summary` with browser requests using unmodified `Origin`/`Sec-Fetch-Site` headers. Backend will respond only while the operator manually runs `127.0.0.1:8788`.
7. **No regression:** verify `https://grafana.home.arpa/` and `https://pihole.home.arpa/` still work, and no LAN/Tailscale/WAN access is newly available. On any failed gate, stop; restore the original Caddyfile and hosts from protected backups, validate, and reload Caddy. If even rollback reload fails, report the incident and do not claim recovery without verifying the running configuration.

**Historical stop condition:** staging alone did not authorize activation. On 2026-10-25 the operator separately ran the guarded `--apply --confirm-local-caddy-reload` action. **Deployment of the HCC application as a permanent service remains HOLD.**

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
**Current status:** Fedora-local HTTPS alias applied; operator reports the new browser address works; prior SNI route smoke reports `control.home.arpa:200`, `grafana.home.arpa:302`, `pihole.home.arpa:302`  
**Gate:** Operator-local HTTPS alias and browser-access smoke are **accepted**, while **separate certificate UI verification, explicit `/api/summary` freshness and full Grafana/Pi-hole browser regressions are not individually documented**. The HCC backend stays manual/foreground; `DEPLOYMENT_GATE=HOLD` for permanent application installation or broader network access.

A future implementation PR may add Caddy configuration material after the operator confirms the current live Caddy state. Merely merging this design document **must not** trigger Caddy reload, automatic deployment or DNS mutation.
