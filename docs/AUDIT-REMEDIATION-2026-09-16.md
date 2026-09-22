# Audit remediation report — 2026-09-16

**Status:** COMPLETED / HISTORICAL  
**Snapshot date:** 2026-09-16  
**Subsequent closure:** AUDIT-02 and AUDIT-03 were later closed with live evidence on 2026-09-22; current status is maintained in `../PROJECT-STATUS.md`.

## Scope

This report records the remediation state of the repository audit performed against the ASUS Edge Gateway / ZTNA project. The review covered implementation, security boundaries, install/rollback behaviour, firewall/DNS/Tailscale design, logging, backup/recovery, CI/tests, documentation, evidence hygiene, and portfolio presentation.

At the time of this report, the reference router was inside the then-planned 2026-09-11 through 2026-09-25 unchanged-state stability gate. The observation was later closed on 2026-09-22. Repository changes described in this historical report did not imply corresponding router configuration changes.

## AUDIT-01 — transactional restore

**Status: CLOSED**

The restore apply path previously validated archive structure and integrity but could leave an earlier destination changed if a later copy failed.

Remediation changed restore apply semantics so that affected live paths are snapshotted into a private pre-restore workspace before mutation. If snapshot creation fails, restore does not begin. If an apply operation fails after mutation starts, rollback removes paths newly created by the failed restore and restores the pre-restore state. Rollback failure is surfaced explicitly as a manual-recovery condition rather than hidden.

Regression coverage includes snapshot failure and a controlled partial-restore failure after earlier data has already changed. The validation suite passed after the remediation.

## AUDIT-02 — exit-node NAT dependency

**Status: OPEN / GATED**

The project deliberately runs Tailscale with `netfilter-mode=off` and owns its Tailscale-facing firewall policy. Exit-node mode permits forwarding from `tailscale0` only to the selected WAN interface, but the project does not create its own `MASQUERADE` or `SNAT` rule.

This does not demonstrate an exit-node failure: successful client Internet access has been observed, and the underlying Asuswrt/Asuswrt-Merlin WAN policy may provide the required source NAT. The audit finding is that the repository had not explicitly identified and validated that dependency.

Documentation now distinguishes project-owned forwarding from platform-owned/effective WAN NAT. Closure requires read-only identification of the effective POSTROUTING/NAT path and a controlled correlation with authorized exit-node traffic. No NAT rule is to be added merely to make the documentation assertion true.

## AUDIT-03 — Android/Fedora DNS datapath

**Status: OPEN / GATED**

The intended classic DNS path is coherent: Tailscale-facing port-53 traffic is redirected to the router-local dnsmasq listener, and dnsmasq is configured to use the local Unbound listener. Earlier Android observations were consistent with this design, but later read-only observations raised a question about whether every tested Android exit-node DNS flow actually traversed that path.

Documentation now treats this as an evidence boundary rather than a confirmed universal behaviour. A post-gate comparison procedure uses the same router state and exit node for Fedora and Android, records client DNS/Tailscale conditions, separates normal resolver behaviour from explicit classic DNS and encrypted DNS, and requires router-side correlation before declaring the path validated.

No router DNS change is justified until that controlled comparison identifies the actual path.

## AUDIT-04 — evidence identifiers

**Status: CLOSED**

A Zen endpoint-validation document contained deployment identifiers that were unnecessary to support the technical conclusion. The identifiers were replaced with neutral placeholders while the test result and engineering value were retained.

The remediation reinforces the repository rule that evidence publication is a minimization exercise: a value should be retained only when it is necessary to reproduce or understand the result.

## AUDIT-05 — Android DNS claim boundary

**Status: CLOSED**

README language previously allowed a bounded Android observation to read as stronger proof of the end-to-end exit-node DNS datapath than the evidence supported.

The wording was changed to preserve the historical observation while explicitly separating it from the unresolved later datapath question. The repository no longer claims that every Android exit-node DNS flow necessarily traverses dnsmasq/Diversion/Unbound.

## Additional repository cleanup

A previously open engineering-worklog pull request for 2026-09-11 was reviewed for relevance and sensitive content, then squash-merged into `main`. The worklog preserves the SSD/Entware migration baseline, controlled reboot validation, QoS cleanup, health-check result, and start of the stability observation.

`docs/firewall-policy.md` now documents the exit-node NAT validation boundary. `docs/testing.md` now contains the controlled Android/Fedora DNS datapath procedure.

## Closure criteria

The audit is not fully closed while AUDIT-02 and AUDIT-03 remain evidence-gated.

AUDIT-02 can close when sanitized evidence identifies the effective exit-node IPv4 NAT path and demonstrates that the expected authorized flow uses it. AUDIT-03 can close when controlled Fedora/Android observations establish the actual resolver paths and clearly separate classic port-53 handling from encrypted or client-specific DNS behaviour.

If either validation reveals a defect, the finding remains open through remediation and regression testing. If the current design is confirmed, closure should record the evidence without introducing unnecessary configuration changes.

## Current assessment

The audit remediation completed so far improves failure recovery, evidence hygiene, claim precision, and test planning without disturbing the reference router during its stability observation. Three findings are closed. Two findings are intentionally left open because their closure depends on real runtime evidence rather than additional static analysis.
