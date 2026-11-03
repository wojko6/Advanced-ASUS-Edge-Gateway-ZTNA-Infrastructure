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

**Next gate:** verify source provenance and actual security controls before broader filesystem or window/input access. Router and agent production deployment remain **HOLD**.

[2026-11-03 dated observations](../worklog/2026-11-03.md)
