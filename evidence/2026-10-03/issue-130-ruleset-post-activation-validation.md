# Issue #130 — GitHub main protection post-activation validation (2026-10-03)

## Ruleset readback

GitHub API readback after activation reported:

- ruleset: `Protect main`;
- enforcement: `active`;
- target: `~DEFAULT_BRANCH` (`main`);
- bypass actors: none;
- current user bypass: never;
- deletion protection: enabled;
- non-fast-forward / force-push protection: enabled;
- pull request required;
- required approving reviews: 0;
- required status check: `Validation suite`;
- strict/up-to-date status-check policy: enabled.

Deletion and force-push protection are accepted from the active ruleset readback.
No destructive delete or force-push test was performed against production
`main`.

## Normal PR after activation

PR #170 was created after the ruleset became active.

Observed behavior:

- the PR targeted `main`;
- the aggregate `Validation suite` ran;
- workflow run #1424 completed successfully;
- the PR became mergeable after the required check passed;
- PR #170 merged successfully through the normal protected-branch path.

Result:

```text
NORMAL_PR_AFTER_RULESET=PASS
```

## Direct main update rejection

A temporary branch was created from current `main` and given one harmless test
commit containing only an issue #130 marker file.

A direct non-force update of the `main` ref to that commit was then attempted
through the GitHub API.

GitHub rejected the update with HTTP 422 and the repository-rule message:

```text
Changes must be made through a pull request.
```

The test commit did not become part of `main`.

Result:

```text
DIRECT_MAIN_PUSH_REJECTED=PASS
```

## Final status

```text
RULESET_ACTIVE=PASS
MAIN_TARGET=PASS
MAIN_DELETE_BLOCKED=PASS (ruleset readback)
MAIN_FORCE_PUSH_BLOCKED=PASS (ruleset readback)
PULL_REQUEST_REQUIRED=PASS
VALIDATION_SUITE_REQUIRED=PASS
STRICT_UP_TO_DATE=PASS
NORMAL_PR_AFTER_RULESET=PASS
DIRECT_MAIN_PUSH_REJECTED=PASS
DOCUMENTATION=PASS
ISSUE_130_ACCEPTANCE=PASS
```

## Evidence boundary

The behavioral test proves that a direct fast-forward-style update to protected
`main` is rejected by the active pull-request rule.

The branch-deletion and non-fast-forward/force-push controls are documented from
the active ruleset configuration readback rather than by performing destructive
operations against production `main`.

Signed tags/releases, artifact signing and stronger multi-maintainer review
requirements remain later extensions.
