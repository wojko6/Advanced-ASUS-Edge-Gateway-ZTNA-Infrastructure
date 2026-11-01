# Local AI Agent C.62.1–C.62.9.3 — read-only evidence and incident-correlation checkpoint

**Date:** 2026-10-31 (Europe/Warsaw)  
**Scope:** Fedora laboratory / local, bounded read-only observations; **not** an ASUS production deployment  
**Evidence basis:** operator-provided Fedora terminal output, local script SHA-256-manifest validation and test reports; dated public router security and network-management evidence  
**Review status:** documentation checkpoint only, no software acceptance or deployment approval

> **Authority invariant:** `MODEL_ACTION_AUTHORITY=NONE`, `DEPLOYMENT_GATE=HOLD`. No unattended action, configuration write, privileged executor, host/router restart, firewall relaxation, service rollout or automatic repair is authorized by these results.

## 1. What this checkpoint does and does not represent

The C.62 sequence progressively extended a local AI Agent *observation laboratory* from simulated data-quality outcomes into separately authorized, bounded **current**, **historical** and **cross-source** reads. The operator ran the scripts manually on Fedora. Reported `PASS` means the named test contract completed; it is **not** a statement that the DNS query path was healthy during every sampled interval, that an outage's root cause was cryptographically established, or that a production AI service is deployed.

The C.62-series Python sources and their local ZIP/manifests **are not represented as published by this repository checkpoint**. Earlier dependencies remain review-separated in stacked **Draft PRs [#343](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/343), [#344](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/344) and [#345](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/345)**. This documentation is based on operator-supplied results, not on a new GitHub source-code or CI verification of C.62 scripts.

## 2. Acceptance matrix — exactly scoped

| Stage | Operator-reported offline tests | Additional operator-reported run | Result / claim boundary |
| --- | ---: | --- | --- |
| C.62.1 | 52/52 PASS | Four fixed loopback VM instant GETs | `PASS_CURRENT_VM_SAMPLED_ONLY`; sample freshness per raw timestamp not yet proven |
| C.62.2 | 56/56 PASS | Eight fixed loopback VM instant GETs with `timestamp(metric)` | `PASS_CURRENT_VM_SAMPLE_TIMESTAMPS_ONLY`; eight queries not atomic |
| C.62.3 | 59/59 PASS | Synthetic gap/recovery matrix | Offline-only; distinct raw sample times required, no host-state inference |
| C.62.4 | 45/45 PASS | Twelve recent VM frames, 12 fresh and zero gaps | `PASS_RECENT_VM_RANGE_SAMPLED_ONLY`; no real gap recovery observed in selected window |
| C.62.5 | 56/56 PASS | Warsaw calendar day 2026-10-30, 288 five-minute slots | 139 fresh, 149 gaps in three spans; `PASS_CALENDAR_VM_OBSERVATION_ONLY` |
| C.62.6 | 60/60 PASS | Cross-midnight VM window (2026-10-30/31) | 120-slot gap, 21 following-day fresh slots, two distinct recovery confirmations; `PASS_CROSS_DAY_VM_OBSERVATION_ONLY` |
| C.62.7 | 68/68 PASS | 15 synthetic restart/collector-gap scenarios | `PASS_SYNTHETIC_RESTART_EVIDENCE_MATRIX_ONLY`; no real reboot attestation |
| C.62.8 | 50/50 PASS | Two bounded Fedora procfs observations of current boot data | `PASS_CURRENT_FEDORA_BOOT_SAMPLED_ONLY`; no historical reboot proved by this step alone |
| C.62.9 | 64/64 PASS | 16 curated/synthetic Wi-Fi and SSH correlation scenarios; manual redacted incident fixture | `PASS_CURATED_INCIDENT_EVIDENCE_ONLY`; report of prior 2.4 GHz use was operator-supplied |
| C.62.9.1 | 40/40 PASS | Live local journald preflight **HOLD** | `TOO_MANY_CLASSIFIED_EVENTS`; explicitly **not** a successful live read |
| C.62.9.2 | 48/48 PASS | Two bounded local journald reads (user/system) | 500 total journal rows, successfully classified and correlated; `PASS_JOURNAL_EVIDENCE_BOUNDED_ONLY` |
| C.62.9.3 | 62/62 PASS | Eight fixed VM loopback queries + two bounded local journal reads + *dated* router ACL evidence | `PASS_BOUNDED_CROSS_SOURCE_OBSERVATION_ONLY`; direct router ACL state at incident **not** checked |

The entry for C.62.9.1 is deliberately retained as a **failed live gate**; increasing the event volume bound with explicit accounting was implemented as a separate C.62.9.2 laboratory iteration, without rewriting C.62.9.1 history.

## 3. Measured Oct 30/31 observation gaps, not inferred outages

**C.62.5, 2026-10-30 (Warsaw calendar day):** 288 slots at five-minute cadence, 139 fresh and 149 not qualified as fresh. The three gap spans contained 135, 5 and 9 slots. The late-evening span remained unresolved at the day's end. Five-minute sampling does not observe all shorter interruptions.

**C.62.6 cross-midnight:** 156 inspected slots (not a complete following day), with one 120-slot gap spanning the day boundary. On Oct 31 the first fresh sample was at **09:15 CET** and two distinct consecutive confirmations were available by **09:20 CET**. `CROSS_DAY_SAMPLING_RESUMED_NOT_HEALTH_PROOF` means resumed sampled collection, not verified DNS availability or host uptime.

**C.62.8 current Fedora boot:** the operator reported stable `boot_id` within the local double read and `/proc` boot epoch equivalent to **2026-10-31 09:09:33 CET**; `uptime` advanced. A separate operator `journalctl --list-boots` showed the previous boot's last journal entry on **2026-10-30 23:18:10 CET** and the current boot starting **2026-10-31 09:09:35 CET**. Different boot identities support a new Fedora boot, but not the reason, exact power-off time, router state, or uninterrupted DNS access during the intervening gap. The first post-gap fresh VM sample occurred about 5.5 minutes after the new boot.

## 4. Oct 30, 18:10–18:45 CET — Wi-Fi administration-path incident

C.62.9.3's **real** joint check on operator Fedora returned:

```text
PARENT_SOURCE_SHA256_PINS=PASS
VM_OBSERVATION_SLOTS=8
VM_FRESH_SLOTS=3
VM_GAP_SLOTS=5
VM_GAPS_OVERLAP_SSH_WIFI_WINDOW=YES
VM_FRESH_SLOTS_AFTER_WIFI=2
JOURNAL_CLASSIFIED_SSH_TIMEOUTS=23
JOURNAL_COLLECTOR_FAILURES=42
JOURNAL_WIFI_RECONNECT_EVENTS=1
JOURNAL_COLLECTOR_SUCCESS_EVENTS=7
FIRST_SSH_TIMEOUT_LOCAL=2026-10-30T18:15:11+0100
WIFI_RECONNECT_LOCAL=2026-10-30T18:35:42+0100
FIRST_SUCCESS_AFTER_WIFI_LOCAL=2026-10-30T18:36:22+0100
HISTORICAL_ACCESS_RESTRICTION_SNAPSHOT_DATE=2026-09-30
HISTORICAL_AUTHORIZED_DHCP_LEASE_MATCH=OBSERVED_MATCH_TO_DATED_SNAPSHOT
LIVE_ROUTER_ACL_AT_INCIDENT=NOT_VERIFIED
ROOT_CAUSE=UNDETERMINED
STATUS=VM_GAP_AND_JOURNAL_RECOVERY_CORRELATED_HISTORICAL_ACL_LEASE_MATCH
V021C6293_RESULT=PASS_BOUNDED_CROSS_SOURCE_OBSERVATION_ONLY
```

At the five-minute grid level, **18:10 / 18:40 / 18:45** were sampled `FRESH/LOCAL`, whereas **18:15, 18:20, 18:25, 18:30 and 18:35** were gaps. These grid labels **do not measure the exact network interruption length**. The journald correlation showed 23 SSH timeouts and 42 collector failures in the bounded window, then a Wi-Fi profile reconnection at 18:35:42 and the first collector success **after that reconnection** at 18:36:22. Seven total collector successes include earlier successes (first at 18:10:31); do not confuse the earliest overall success with post-reconnect recovery.

The same incident had ten Pi-hole tunnel exit events and two Tailscale link/rebind events in the separate C.62.9.2 report. These are evidence of local service/path behavior; successful collection does **not** prove Pi-hole, Unbound, DNS Guard's client query path or the router's full health.

**Historical security policy, not newly measured October runtime configuration:**
- [Issue #127 access restriction evidence (2026-09-29)](../../evidence/2026-09-29/issue-127-lan-management-wan-exposure-hardening.md) records `ACCESS_RESTRICTION` source-address allowlisting for router WebUI/SSH and a terminal default DROP, after setting a Fedora DHCP reservation.
- [WebUI security drift evidence (2026-09-30)](../../evidence/2026-09-30/webui-security-policy-drift-validation.md) records the enabled policy and an allowlist including Fedora's historically reserved management lease (exact private IPs deliberately omitted here).
- [Fedora/ASUS management-path case study (2026-10-21)](../case-studies/fedora-asus-lan-management-dhcp-allowlist-2026-10-21.md) describes an already-resolved, highly similar symptom: the 2.4 GHz client profile had a different MAC/IP and could not open management SSH/HTTPS, while reconnecting to the intended 5 GHz profile restored the approved lease, HTTPS HTTP 200 and SSH.
- [Issue #128 Wi-Fi baseline (2026-09-29)](../../evidence/2026-09-29/issue-128-ipv6-wifi-security-parity.md) describes both main WLANs as trusted and AP isolation disabled; do not automatically call the 2.4 GHz radio a guest/IoT segment.

**Interpretation:** intentional management source-address restriction is a **strong, historically supported explanation** for the observed SSH timeouts from the wrong profile. The October 30 VM/journal timing and historical lease match reinforce that hypothesis. They **do not** prove the live October 30 firewall rules, SSID-specific enforcement, the exact rejected packet path, that RF band itself enforces policy, or the original reason Fedora selected the other Wi-Fi profile. `ROOT_CAUSE=UNDETERMINED` remains correct; do **not** label the observed SSH denial an ASUS or DNS service outage or request firewall relaxation.

## 5. Source, security and reasoning boundaries

- Classify **MISSING_SERIES / STALE_COLLECTION / OBSERVATION_GAP** separately from **DNS query-path outage**.
- Treat only two **distinct** fresh post-gap raw timestamps as an observation-recovery confirmation; one sample or duplicate timestamp is insufficient.
- Treat `journalctl --list-boots` and procfs `boot_id`/uptime as **host-boot signals**, not cryptographically attested or complete power history. Source identity and clock alignment can be incomplete.
- Treat individual VM GETs as **non-atomic**; report SHA-256 protects deterministic report identity, not source authentication.
- Keep **operator statements** (prior 2.4 GHz use) distinct from machine log classifications (Wi-Fi profile named 5GHz) and actual RF measurement (`RF_FREQUENCY_MEASURED=NO`).
- A historical ACL snapshot must **never** be silently elevated to a verified live-rule state.
- All read permissions remain bounded and manual. The C.62.9.3 run contacted only local VM loopback and local journald as claimed, not the router, Ollama, Loki, HCC, executor or Podman; it made no file writes.

## 6. Follow-up and publication boundary

1. Preserve this evidence checkpoint as **documentation only** and review it separately from the stacked earlier C.57–C.61 code PRs.
2. Consider a later versioned, read-only source-review PR for C.62 laboratory scripts **only after** exact-file SHA, import and CI provenance are checked; do not imply they are present on main.
3. If exact Oct 30 ACL enforcement is ever necessary, seek separately approved bounded router-side evidence. No such access is required merely to document or close this observational lab checkpoint.
4. For future agent output, prefer `MANAGEMENT_ACCESS_POLICY_MATCH_PLAUSIBLE_NOT_PROVEN` with `ROOT_CAUSE=UNDETERMINED`, not `DNS_OUTAGE_PROVEN` or an automatic fix.

**Deployment state: `DEPLOYMENT_GATE=HOLD`; `MODEL_ACTION_AUTHORITY=NONE`.**
