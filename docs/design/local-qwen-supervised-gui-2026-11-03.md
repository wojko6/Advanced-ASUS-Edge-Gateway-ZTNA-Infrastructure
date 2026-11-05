# Fedora Qwen supervised GUI — operator-reported boundary (2026-11-03)

**Classification:** separate workstation prototype, not production ASUS code. The actual Python desktop UI, its screenshots and reported offline test suite have **not** been published in this repository. This note describes observed behavior, not an independently reviewed implementation.

## Runtime and operations

An existing portable Ollama **0.40.11** on the Fedora KDE host served local **Qwen3.5 4B** through loopback. The operator observed a working browser UI and KDE shortcut, later updated through **v0.10.1**.

| Class | Prototype policy | Boundary |
| --- | --- | --- |
| Fixed DNS, service, log, HTTP metric reads | Automatic for known read IDs | Bounded output, local predetermined sources; no model-defined shell |
| Open selected GUI apps / known folders | Automatic | Explicit allowlist; launching an app is not arbitrary code execution permission |
| Copy small files or rename within workspace | Single-use human approval | Exact source/destination preview, bounded path, no overwrite |
| Close selected app / modify volume | Approval required | Changes session state |
| Arbitrary command, `sudo`, file deletion/edit, free mouse/keyboard injection, router configuration | Not provided | Requires separate design, safety review and operator authorization |

The GUI's limited executor **does** have action authority in the user's session. In contrast, the distinct source-merged **C.63 agent** has `MODEL_ACTION_AUTHORITY=NONE` and its deployment gate remains `HOLD`. Neither should be described as unrestricted or production-approved.

## Evidence and interpretation rules

- Display the raw observed command result separately from the model's narrative. Exit status `0` or workflow `COMPLETE` is not synonymous with a healthy service.
- Report bounded sample sizes, metric semantics and per-service health (`OK`, `WARNING`, `ERROR`, `UNKNOWN`), and distinguish an earlier anomalous Loki 503 from a **later** direct 200.
- Empty Grafana manifest discovery polls (cumulative 304 then 315, 0 manifests, 0 reloads) justify a *component-specific* warning. Ordinary dashboard UI search was operational in one operator check; the special discovery path remains unverified.
- A file read or rename requires concise, grounded confirmation, not a DNSSEC/network health report.
- Treat logs and file contents as **untrusted model input**; do not allow them to issue tool commands.

**Security caveats:** no independent review of browser origin/CSRF, approval-token lifecycle, symlink/race resistance, local file confidentiality, SELinux isolation, prompt-injection defenses or KDE Wayland portal interactions for the actual GUI. A read-only-looking operation can still expose private data. The final creator-reported **134/134 offline tests** are not a security attestation.

## November 5 follow-up — v0.12.29, same privilege boundary

This is a **later operator-reported workstation checkpoint**, not a retroactive revision of the November 3 v0.10.1 observations:

- **KWin/WindowsRunner:** an allowlisted D-Bus `Match` call returned search matches (often two records for one opaque match ID). IDs, counts, and icon hints were **not verified as actual window IDs, application/process identities, all open windows, or the active window**. Later grouped icon/category hints and public `/usr/share/applications` metadata remained heuristic. Diagnostic reports intentionally omitted raw window titles/IDs/icon values; the local user-session process necessarily parsed source data before reducing it. No `Run`, KWin script-loading, window-control or mouse/keyboard injection was authorized.
- **User interface:** bounded single-panel log scrolling, summarized resource/monitoring cards, and quick-task prompt insertion were verified in the operator's GUI. A quick-task choice did not execute an action before **Send**.
- **Natural-language routing:** only fixed accepted question variants and carefully scoped follow-ups could select allowlisted reads. Ambiguous RAM-versus-disk or Grafana warning-versus-manifest queries required clarification; no unrestricted model-generated shell command was introduced.
- **Network and service checks:** fixed local DNS resolution of `example.org`, fixed public Google/Cloudflare HTTPS endpoints, and local systemd/HTTP readiness checks supplied bounded evidence. Two successful HTTPS endpoints establish connectivity to **those endpoints at that time**, not all Internet services; these public probes expose ordinary connection metadata to their operators. Active systemd alone is not ready/healthy; a completed command with no complete health grade is not a failed command.
- **Monitoring uncertainty:** Loki `/ready` intermittently returned HTTP 503 marked `INGESTER_NOT_READY`, while `/services` reported 16 components `Running` and systemd was active; the cause remains unproven. Grafana manifest-watcher warnings and zero loaded manifests are a separate component warning from operator-tested dashboard search.
- **Evidence:** the latest creator-reported suite was **338/338 offline PASS**; simulated HTTP/Chromium tests and screenshots of real Fedora GUI flows have **different evidential weights**. They are **not** independently audited production/security tests. Local Python GUI source, raw logs and private user-session data are not in this public repository.

**Security and deployment remain unchanged:** bounded user-session executor and human approval for allowed changes; no arbitrary `sudo`/shell, filesystem takeover, privileged router action, unrestricted window manipulation, persistent autostart or security sign-off. The separately published C.63/C.64 agent has `MODEL_ACTION_AUTHORITY=NONE`; the two programs are not interchangeable. **`DEPLOYMENT_GATE=HOLD`**.

[November 5 workstation observations](../worklog/2026-11-05.md) · [documentation consistency review](../audits/2026-11-05-documentation-consistency-review.md) (both on Draft PR #369 until merged)

**Next gate:** verify source provenance and actual security controls before broader filesystem or window/input access. Router and agent production deployment remain **HOLD**.

[2026-11-03 dated observations](../worklog/2026-11-03.md)
