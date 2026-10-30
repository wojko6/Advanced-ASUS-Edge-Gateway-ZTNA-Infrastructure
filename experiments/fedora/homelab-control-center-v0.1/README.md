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


## V0.13–V0.14 correlation work (operator evidence, 2026-10-29)

The manual offline V0.13.2a lab correlated 21 historical seven-series DNS Guard telemetry gaps against bounded Fedora suspend/resume, interboot journal records, and systemd user-unit collector exits. The operator reported **31/31 synthetic self-tests PASS** and **PASS_CORRELATION_ONLY** on the local seven-day input. Five gaps were strongly suspend-correlated, eight interboot-correlated, three partially host-correlated, one mixed host/collector, four collector-exit-255 observed, and zero entirely unmatched by selected evidence. Correlation is **not** proof of DNS outage, precise power state, SSH root cause, or full journal completeness.

The V0.14 **source-only Draft PR** adds an offline sanitizer and static local-only correlation view. Fedora operator tests recognized **55 collector exit-255 messages and 38 SSH timeout messages** in the bounded Oct 28 journal input; these 93 classified messages are **not 93 independent incidents**. The installed Alloy accepted a composed **temporary** fragment with `ALLOY_VALIDATE=PASS`. The fragment is intentionally **not applied** to the running config.

Separate accepted isolated labs: **V0.14.1** one synthetic Alloy → loopback fake Loki push PASS; **V0.14.2** disposable ACL read-only `alloy` / deny `nobody` PASS; **V0.14.3** read-only `var_lib_t` policy discovery with SELinux Enforcing (broad allow rules; not proof of filesystem isolation); **V0.14.4b** transient systemd process with UID/GID 954, exact `unconfined_service_t` and temporary `var_lib_t` synthetic file: read PASS, write DENIED, `nobody` DENIED, cleanup PASS; 16/16 self and 16/16 unit tests. Historical V0.14.4/V0.14.4a **HOLD** was a full-context string mismatch caused by one trailing NUL from `/proc/self/attr/current`; the narrow V0.14.4b fix retains strict context matching.

**V0.14.5A–B now has isolated test source in Draft #338 (2026-10-30):** corrected private atomic immutable-segment publication and an offline snapshot/ACK replay model, **59/59 focused tests PASS**, full HCC **263/263 Python + 55/55 JavaScript PASS** in the Work Linux container. These results are not Fedora/SELinux/Alloy acceptance. Trusted journal identity, durable checkpoint, safe deletion/retention, SELinux/ACL persistence and real synthetic Alloy full-chain testing remain unimplemented/unaccepted. See [V0.14.5 contract, reproducible tests and limitations](V0.14.5-OFFLINE-SEGMENT-REPLAY-LAB.md). No production journal stream, `/var/lib/hcc-dns-guard` spool, deployed Loki ingestion, service timer, autostart, Grafana alert changes, HCC endpoint, router access or remote exposure has been approved. Running Alloy had supplementary `adm` and `systemd-journal` groups: empty systemd `SupplementaryGroups=` did **not** mean those groups were absent.

**Later acceptance and C continuation (2026-10-30):** the Fedora operator reported
**59/59 A–B tests OK** in 0.088 s, both lab PASS markers and cleanup; three B
receive attempts for two segments are the expected lost-checkpoint replay.
[V0.14.5C](V0.14.5C-DISPOSABLE-CHECKPOINT-LAB.md) now adds actual checkpoint
files in disposable directories, exact ACK before storage, atomic replacement,
restart and abrupt child-exit tests. Current Work results: **28/28 C**, **87/87
A–C**, **291/291 HCC Python**, **55/55 JavaScript** PASS. The operator later
also reported **C 28/28 OK in 0.171 s**, its disposable lab PASS, prefix 1 after
reopen / final 2 and cleanup. A–B and C were accepted in **separate Fedora
runs**. C remains uninstalled and is not proof of power-loss durability,
authenticated event identity, exactly-once delivery or real Alloy compatibility.

See [V0.13–V0.14 evidence and deployment boundaries](V0.13-TO-V0.14-CORRELATION-LAB.md) and the un-applied [Alloy fragment](monitoring/v014-dns-guard-sanitized.alloy.fragment).

**V0.14.5D synthetic record identity (Work only):** a separate
[memory-only source-envelope model](V0.14.5D-SYNTHETIC-EVENT-IDENTITY-LAB.md)
retains integer microseconds and opaque keyed IDs, recognizes exact replay,
preserves distinct same-time/kind records and refuses changed payload under
the same ID without partially updating its bounded ledger. **31/31 D tests**,
at the D checkpoint **118/118 A–D**, **323/323 HCC Python**, **55/55 JavaScript** PASS in Work.
The key is a public fixture, input unit/cursor is merely declared synthetic
metadata, and the ledger is volatile. This is not authenticated journal input,
collector-run/incident identity or exactly-once delivery. The new schema is
**incompatible with A–C**, with a regression requiring rejection. No actual
spool/Alloy integration or D Fedora operator test has occurred.

**V0.14.5E disposable atomic handoff (Work only):** the
[new private snapshot store](V0.14.5E-ATOMIC-HANDOFF-LAB.md) puts record ID and
complete canonical payload in the same publication. Losing a receipt does not
make committed payload unavailable on reopen/replay. E uses D normalization
without precommitting its volatile ledger; no separate seen-ID file exists.
**34/34 E tests**, at the E checkpoint **152/152 A–E**, **357/357 HCC Python**, **55/55
JavaScript** PASS. This is a retained snapshot, not a receiver ACK or an
append-only Alloy stream. No deletion, scheduler, source authentication,
production store, A–C migration, power-loss guarantee or E Fedora result.

**V0.14.5F synthetic delivery ACK state (Work only):** the
[separate disposable ACK model](V0.14.5F-SYNTHETIC-DELIVERY-ACK-LAB.md) attempts
one retained E record at a time through a volatile in-process fake receiver.
The private ACK file advances after an exact scope/ID/payload-hash match;
reopen resumes by ID without skipping newly appended lower IDs. Receive before
ACK storage can repeat an attempt. E source payloads are never deleted.
**37/37 F tests**, at the F checkpoint **189/189 A–F**, **394/394 HCC Python**, **55/55
JavaScript** PASS. Four child-exit phases do not prove physical power-loss or
remote-receiver durability. This fixture is not Loki's ACK protocol or an
installed transport/scheduler. No F Fedora result, real source, GC or service change.

**V0.14.5G disposable file receiver (Work only):** the
[file-backed synthetic receiver](V0.14.5G-DISPOSABLE-FILE-RECEIVER-LAB.md) retains
full E-format payload before returning F's fixture ACK. Reopen/lost ACK retries
find the same retained ID without rewriting its snapshot. Cross-check all
three stores even after apparent completion; all source/receiver data remain.
**36/36 G tests**, at the G checkpoint **225/225 A–G**, **430/430 HCC Python**, **55/55
JavaScript** PASS, including six actual child-exit phases. Losing both receiver
and ACK state permits replay/rebuild; no independent rollback anchor exists.
No actual Loki/transport, external exactly-once effects, physical power-loss
durability, G Fedora acceptance, GC, production store or service change.

**V0.14.5H offline Loki JSON request encoding (Work only):** the
[memory-only formatter](V0.14.5H-OFFLINE-LOKI-REQUEST-LAB.md) validates an entire
E snapshot before producing one bounded JSON request body, up to 16 records /
64 KiB. Exact microseconds become integer-nanosecond strings; full event lines
retain IDs/scope with two fixed stream labels. Request order is time then ID,
without changing F/G dispatch order or state. **26/26 H tests**, at the H checkpoint
**251/251 A–H**, **456/456 HCC Python**, **55/55 JavaScript** PASS.
No HTTP, actual Loki acceptance, response/ACK interpretation, files, progress
change, batching/selection, H Fedora result or service action. G's state-loss
limitations and all production gates remain open.

**V0.14.5I offline batch planning (Work only):** the
[memory-only planner](V0.14.5I-OFFLINE-BATCH-PLAN-LAB.md) splits all pending
records from a validated E snapshot into H requests, using declared F fixture
ACKs by ID/hash. Global time/ID order, up to 64 requests / 1 MiB total body
bytes; full 1,024-record input tested. Exact-input checksums and complete
recomputation reject drift before a future caller reuses a plan. **30/30 I
tests**, at the I checkpoint **281/281 A–I**, **486/486 HCC Python**, **55/55 JavaScript**
PASS. No HTTP, real receipt/authentication, live file locking, checkpoint
advance or I Fedora acceptance. Fresh bytes must be supplied; old bytes or
consistent forged source/ACKs cannot establish actual receipt or rollback safety.

**V0.14.5J owned loopback HTTP exchange (Work only):** the
[new isolated exchange](V0.14.5J-OWNED-LOOPBACK-EXCHANGE-LAB.md) starts its own
ephemeral IPv4 peer and one bounded Python client. The peer validates capability
and exact selected H bytes; strict report/peer checks recognize only the chosen
empty-204 fixture result. Timeout/interrupt paths kill/reap the client, then
close the listener/thread. **30/30 J tests**, at the J checkpoint **311/311 A–J**, **516/516
HCC Python**, **55/55 JavaScript** PASS. Self-test is memory-only; lab/network
tests use owned loopback sockets and children. No real Loki, durable receipt,
progress change or J Fedora result. Pending count remains 33 after the lab.

**V0.14.5K bounded prefix exchange (Work only):** the
[sequential prefix runner](V0.14.5K-BOUNDED-PREFIX-EXCHANGE-LAB.md) selects at most
four I requests (default three), checks supplied source/ACK bytes before each
and stops at the first state/exchange/cleanup error. Each J peer closes before
the next callback; all selected scripts validate before any network. **25/25 K
tests**, at the K checkpoint **336/336 A–K**, **541/541 HCC Python**, **55/55 JavaScript** PASS.
Self-test stays memory-only; lab exchanges three requests with separate owned
loopback fixtures. All 33 records remain pending / two declared ACKs unchanged.
No retry, receipt/progress persistence, resume cursor, run-wide deadline, live
locks, actual Loki or K Fedora acceptance. A–J Python modules are unchanged.
HCC CI also checks matching pushes to the exact Draft branch, alongside
PR/manual triggers. Results are matched to head SHA/event in Draft #338;
the original K head's missing HCC run remains recorded in the worklog.

**PR #338 functional scope is frozen at A–K:** the
[closing review](V0.14.5-A-K-FREEZE-REVIEW.md) records model boundaries, a fixed
non-finite-number bug in the imported V0.14 view and corrected B3B2E test
ordering. Closing Work regression: **542/542 Python**, including **336 A–K**,
and **55/55 JavaScript PASS**. A–K modules and runtime HTTP/source guards are
unchanged. Follow-up input/storage, transport/receipt and Fedora runtime work
belongs in separate PRs. #338 remains open/Draft/unmerged; source scope freeze
does not grant deployment or Fedora/actual Loki acceptance.

**Separate V0.14.6A stacked Draft follow-up:** the
[supplied journal-envelope adapter](V0.14.6A-SUPPLIED-JOURNAL-ENVELOPE-LAB.md)
checks declared metadata and maps three text hints to D identity / E snapshot
bytes in memory, preserving microseconds and distinct cursors. **29/29 new
cases / 571/571 full Python / 55/55 JavaScript PASS** in Work. Supplied JSON
can be forged and is not trusted provenance. No reader, actual journal,
file/key input, persistence, ACK, transport or V0.14.6A Fedora acceptance.
The new Draft targets frozen #338's branch; its A–K source remains unchanged.
[PL adaptation](../../../docs/pl/hcc-v0146a-journal-envelope-lab.md).

**DEPLOYMENT_GATE=HOLD.**

## Acceptance boundaries

- The demonstration clock is fixed to `2026-10-25T14:00:00Z`. Age values are relative to that **fixture**, not current time.
- `OFFLINE` requires an explicit fictional planned-outage annotation. Missing source is `UNKNOWN` and old metric is `STALE`.
- Recovery deliberately separates backup, Restic integrity, isolated Btrfs restore and bootable OS verification; no restore is executed.
- The Incidents view uses **fictional events**, not the actual October 24 router incident. Evidence-based historical replay belongs to #304.
- Default **V0.1** remains fixture-only, but **V0.2/V0.3** have strictly allowlisted, loopback-only, non-root *manual* live-read adapters. Complete live service-health acceptance, permanent deployment, authentication hardening and remote access are **not implemented/approved**.
- ASUS production, DNS Guard, Unbound, Pi-hole, RouterCloud/DUFS, Grafana alert rules, Fedora Recovery and Tailscale configurations are untouched.

**DEPLOYMENT_GATE=HOLD.**
