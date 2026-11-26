# Homelab Control Center V0.1–V0.3 — Fedora-only experiments

**State (2026-10-26):** ISOLATED, MANUAL-ONLY FEDORA LAB / `DEPLOYMENT_GATE=HOLD`. V0.1–V0.3 source has merged, **not** been installed as a persistent application. Related: [#303](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/303) (Control Center), [#304](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/304) (Black Box), and merged design [PR #305](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/305).

The **default V0.1** is a static Polish-language dashboard with four views and six fictional scenarios; **nothing in V0.1 is a live measurement**. Separate, manually launched **V0.2/V0.3** variants use a bounded, read-only Fedora-local VictoriaMetrics adapter. V0.3 has **two real telemetry panels** (scrape-target counts and the DNS Guard exporter-reported mode), while fictional service/incident/recovery data stay hidden until explicit DEMO opt-in. The project does **not** install a permanent background process, contact ASUS directly from HCC, execute router commands, allow arbitrary metrics queries or authorize remote exposure.

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

## Optional Fedora V0.2 source preflight (not a live dashboard)

The separate `tools/fedora-v02-readonly-preflight.py` script is available for **manual, review-first** source inventory. It does not connect the demo to real monitoring and does not create any service.

```bash
python3 -B tools/fedora-v02-readonly-preflight.py --self-test
python3 -B tools/fedora-v02-readonly-preflight.py --inspect
# Optional explicitly requested read-only loopback probes:
python3 -B tools/fedora-v02-readonly-preflight.py --run
```

Only use `--run` after reviewing its source. That mode performs three GET requests **solely to 127.0.0.1**, with short timeouts and fixed paths: VictoriaMetrics health and aggregated `count(up)`, plus Loki readiness. No raw labels/logs are printed. A successful preflight is **not** a live V0.2 adapter acceptance. See [V0.2 preflight boundaries](V0.2-PREFLIGHT.md).
## V0.3 manually started, read-only lab (2026-10-26)

Merged [PR #312](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/312) introduced the second fixed-query, live-labelled DNS Guard telemetry panel and a separate non-root V0.3 server. Merged [PR #313](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/313) hides all fictional DEMO content until explicit opt-in and visually neutralizes its statuses. **Source merge is not runtime installation.** The existing workstation-only `https://control.home.arpa/` alias can forward to V0.3 only when the operator has manually started its foreground server. V0.2 and V0.3 both bind port **8788** and cannot run simultaneously.

After reviewing the exact source, confirming no other process owns the test port, and explicitly stopping a foreground V0.2 lab (if running), a non-root Fedora operator can test V0.3:

```bash
node --test tests/*.mjs
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_*.py' -v
python3 -B tools/v03_local_server.py --serve-readonly-v03
# Stop with Ctrl+C. Do not enable systemd/autostart or expose outside loopback.
```

In the recorded October 26 manual browser and HTTPS tests, VictoriaMetrics showed **7/7 scrape targets UP**, and DNS Guard telemetry reported **LOCAL**, watchdog enabled, break-glass inactive; one cross-site API request returned **HTTP 403**. These are point-in-time observations, **not** independent DNS lookup validation, service-wide uptime proof, complete web security testing or authorization to install a production application. See [V0.3 HTTPS/source limits](V0.3-DNS-GUARD-PREFLIGHT.md) and [synthetic DEMO isolation](V0.3-DEMO-OPT-IN-PREFLIGHT.md). Black Box [#304](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/304) remains separate and unimplemented. **Persistent HCC deployment, autostart, authentication hardening and remote access are HOLD.**

## Acceptance boundaries

- The demonstration clock is fixed to `2026-10-25T14:00:00Z`. Age values are relative to that **fixture**, not current time.
- `OFFLINE` requires an explicit fictional planned-outage annotation. Missing source is `UNKNOWN` and old metric is `STALE`.
- Recovery deliberately separates backup, Restic integrity, isolated Btrfs restore and bootable OS verification; no restore is executed.
- The Incidents view uses **fictional events**, not the actual October 24 router incident. Evidence-based historical replay belongs to #304.
- Default **V0.1** remains fixture-only, but **V0.2/V0.3** have strictly allowlisted, loopback-only, non-root *manual* live-read adapters. Complete live service-health acceptance, permanent deployment, authentication hardening and remote access are **not implemented/approved**.
- ASUS production, DNS Guard, Unbound, Pi-hole, RouterCloud/DUFS, Grafana alert rules, Fedora Recovery and Tailscale configurations are untouched.

**DEPLOYMENT_GATE=HOLD.**
