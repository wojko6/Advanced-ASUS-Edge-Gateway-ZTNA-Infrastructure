# Homelab Control Center V0.1 — Fedora-only static demo

**State:** ISOLATED PROTOTYPE, not deployed. Related: [#303](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/303) (Control Center), [#304](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/304) (Black Box), and proposed design [PR #305](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/305).

A static, Polish-language status dashboard with 4 navigable views and 6 switchable synthetic scenarios. **Nothing here is a live measurement.** No dependencies, CDN, package installation, privileged commands, systemd services, backend adapter, internet fetch, router connection, state mutation or background operation.

## Run locally on Fedora (explicit opt-in)

Requires Python 3; no `sudo`:

```bash
cd /path/to/homelab-control-center-v0.1
bash run-lab.sh --serve
```

Open `http://127.0.0.1:8787/` in a local browser. The server binds to **127.0.0.1 only** and serves only files in this directory. It is not exposed to the LAN, WAN or Tailscale. Press **Ctrl+C** to stop it. Do not run as root; do not use `--bind 0.0.0.0` or expose via reverse proxy. HTML modules should be served through this local server, not opened directly via `file://`.

Although the browser loads local CSS/JS assets over loopback HTTP, the app makes **no external requests** and its CSP disables the `fetch` family of network connections. No client-side storage is used. For high-trust hosts, keep this as an **isolated user test**, not a hardened production web service; Python's `http.server` is only for local demo use.

## Validate

```bash
node --test tests/*.mjs
bash -n run-lab.sh
```

The Node tests cover fixture consistency, status semantics and static safety checks. Optional browser validation includes desktop and mobile layout, keyboard navigation, the six scenario options and four sections. Node is **only required to run tests**, not to view the demo.

## Acceptance boundaries

- The demonstration clock is fixed to `2026-10-25T14:00:00Z`. Age values are relative to that **fixture**, not current time.
- `OFFLINE` requires an explicit fictional planned-outage annotation. Missing source is `UNKNOWN` and old metric is `STALE`.
- Recovery deliberately separates backup, Restic integrity, isolated Btrfs restore and bootable OS verification; no restore is executed.
- The Incidents view uses **fictional events**, not the actual October 24 router incident. Evidence-based historical replay belongs to #304.
- Real monitoring data and loopback-bound API adapters are **not implemented**. A future approval and separate threat model are needed first.
- ASUS production, DNS Guard, Unbound, Pi-hole, RouterCloud/DUFS, Grafana alert rules, Fedora Recovery and Tailscale configurations are untouched.

**DEPLOYMENT_GATE=HOLD.**
