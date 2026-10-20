# Issue #235 — services-start source and ownership trust (2026-10-20)

> **Status:** OPERATOR-REPORTED, SANITIZED, POINT-IN-TIME READ-ONLY / OFF-ROUTER. **Production remediation NOT PERFORMED.**  
> **Scope:** ASUS Edge `services-start` startup trust chain and its relation to DNS Guard root-Cron. Separate from SSD Draft PR #245, DUFS HTTP-origin hardening and RouterCloud PrivDrop.  
> **Gates:** `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `DEPLOYMENT_GATE=HOLD`. No live script, Cron, DNS service, JFFS, SSD or hook change authorized or reported.

## Provenance and interpretation

The operator executed fixed-path, read-only ASUS audits V1.4–V1.6 and a corrected off-router Python V1.7 classification. Outputs were pasted to the engineering conversation. These are **operator-reported observations**, not CI validation or independent continuous runtime attestation. They were tested against immutable, hash-verified repository source; point-in-time repeated reads do **not** exclude concurrent mutation before or after inspection. No production file contents or identity values are reproduced here.

Earlier [19 October DNS Guard root-Cron trust and rollback evidence](../2026-10-19/issue-235-dns-guard-root-cron-trust-and-rollback.md) established that the separately root-Cron-executed DNS Guard target is nonroot-owned and owner-writable despite matching the approved historical source hash.

## V1.4 — fixed-path DAC snapshot

- Self-test: **6/6 PASS** (expected root/config cases, owner risk, symlink, world-write and ACL negative checks).
- ASUS read-only snapshot: `/jffs/scripts`, `/jffs/configs` and `/jffs/addons/asus-edge/bin` were **root:root, mode 0755, no group/other write**.
- Actual firmware hook `/jffs/scripts/services-start`: **nonroot-owned**, mode **0755**, single hardlink; `TRUST_CHAIN_ITEM_ISSUES=1`. Its nonroot owner may change the bytes subsequently executed at the privileged start boundary, irrespective of current hash.
- Addon `/jffs/addons/asus-edge/bin/services-start`: **root:root, 0755**, single link.
- Config `/jffs/configs/asus-edge.conf`: **root:root, 0600**, single link. A literal `EDGE_DNS_GUARD_WATCHDOG=1` was detected; **not an effective-runtime evaluation**.
- Snapshot does **not** establish ownership trust or quiescence; `TRUST_CHAIN_PREFLIGHT=HOLD`, return code 2.

## V1.5–V1.7 — exact source and drift resolution

- V1.5 self-tests **7/7 PASS**. Both production paths differed from their *initially selected* reference: a short wrapper template for the firmware hook, and immutable repo `router/scripts/services-start` for the addon. This was a **comparison-target issue** for the hook, not evidence of compromise.
- V1.6 self-tests **11/11 PASS**. Two consecutive reads per target matched at the observation points. The hook contained **21,046 bytes / 456 lines**, no generated-wrapper marker or delegation to the addon; addon **20,834 bytes / 453 lines**, with three change regions versus the pinned source.
- Corrected V1.7 comparison: **`HOOK_EQUALS_PINNED_SOURCE=YES`**. The firmware hook exactly matched the immutable reviewed `router/scripts/services-start` source. Hook `!=` live addon. This resolves apparent V1.5 hook drift: the device uses a full script rather than the installer's shorter generated hook template. The observed file contents do **not** prove immutable ownership.
- Addon differs from the source in **three** bounded regions: one replacement around the scheduled Cron command (lexical shell tokens equal), one deletion of the early watchdog call context, one insertion of the call near the tail. The `configure_dns_guard_watchdog` **function body matches** the approved source exactly.
- Corrected V1.7 identified watchdog call sites at **source/hook line 325** and **addon line 443**; `CRON_COMMAND_TOKENS_EQUAL=YES`, `ADDON_WATCHDOG_CALL_MOVED_LATER=YES`. This **does not prove semantic equivalence**: delayed registration could matter if the addon entrypoint is ever executed, especially if a startup dependency stalls. The pinned full hook calls it before waiting for Entware.
- A first auxiliary V1.7 diagnostic hit a Python `bytes`/`str` mismatch; corrected classifier completed with code 0. The earlier empty-call arrays were invalid and **must not** be used as evidence.

## Security significance

1. Two **separate root execution trust boundaries** have now been identified: the firmware `services-start` hook and the root-Cron DNS Guard target. Both were observed **nonroot-owned and owner-writable**. Conversely, the inspected addon script and config passed point-in-time DAC owner/mode checks.
2. The complete firmware hook, not the addon wrapper, matches the approved full `services-start` source. The presence of that file at the expected Merlin hook path plus known source call flow indicates the expected **startup entrypoint**; an actual invocation/process trace was **not** collected.
3. Running the **generic installer** could rewrite the full hook as a generated wrapper. Do **not** use it as an ownership repair; it risks changing startup semantics and cannot be treated as an equivalent byte-preserving update.
4. Identical SHA-256 at audit time does not establish a trusted owner, exclude same-UID writers or make script use race-free. Likewise, a named Cron deletion alone does not drain active DNS Guard runs or prevent new `services-start` event invocations.
5. **Do not overwrite or standardize the live addon** simply to remove the three small differences; its later watchdog call deserves separate release review if the addon is promoted to an entrypoint.

## Remaining maintenance-readiness gates (DESIGN ONLY)

| Gate | Required evidence before approval | Current decision |
| --- | --- | --- |
| Independent inputs and backups | Trusted, immutable or separately protected source bytes and verified, recoverable off-router snapshots **for both live privileged targets**, preserving applicable metadata | DNS Guard copy verified; **hook independent recovery not attested** |
| Dispatcher / runtime quiescence | Suppress named root-Cron re-scheduling **and** Merlin `services-start` re-entry/re-registration; identify in-flight runs and writable FDs; ensure no same-UID writers | **NOT PROVEN** |
| Byte-preserving least-change remediation | Review an isolated two-target trusted-owner publishing plan that preserves the **exact active hook behavior** and vetted DNS Guard bytes, establishes intended `root:root 0755` and rejects partial/mixed state | **NOT PROVEN ON JFFS2** |
| Failure handling | Independent recovery channel and bounded fail-closed rollback before publishing, including uncertain partial commit and JFFS2 interruption limitations | Fedora fixture PASS only; **router not validated** |
| Functional acceptance | Operator-approved targeted test of DNS Guard, Unbound, Pi-hole, Cron re-registration and Merlin startup behavior; separate reboot authorization | **NOT AUTHORIZED** |
| Scope | Keep SSD PR #245, RouterCloud/DUFS and unrelated production services untouched | **ENFORCED / HOLD** |

**Decision:** stop repeating equivalent synthetic diff checks. Next work should address the *actual* readiness gaps: protected hook recovery input, trusted two-target transaction and boot/Cron quiescence protocol. No production apply, Cron deletion, owner/mode mutation, installer execution or reboot follows automatically from these read-only findings. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.
