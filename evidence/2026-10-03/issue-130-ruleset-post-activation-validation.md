# Issue #130 — GitHub main protection post-activation validation (2026-10-03)

## Ruleset readback

GitHub API readback after activation reported:

- ruleset: `Protect main`;
- enforcement: `active`;
- bypass actors: none;
- current user bypass: never;
- deletion protection: enabled;
- non-fast-forward / force-push protection: enabled;
- pull request required;
- required approving reviews: 0;
- required status check: `Validation suite`;
- strict/up-to-date status-check policy: enabled.

The final acceptance still requires a normal PR after activation and a bounded
direct-push rejection test against `main`.

## Status

```text
RULESET_READBACK=PASS
NORMAL_PR_AFTER_RULESET=PENDING
DIRECT_MAIN_PUSH_REJECTED=PENDING
```
