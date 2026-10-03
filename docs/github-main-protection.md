# GitHub main-branch protection and required validation

Issue: #130

## Goal

Protect the repository's `main` branch against accidental direct changes and
history rewriting while keeping the normal contribution path simple:

```text
feature/docs branch
      |
      v
pull request
      |
      v
Validation suite
      |
      v
merge to main
```

This repository contains firewall, DNS, recovery and deployment configuration,
so source-control protection is part of the project supply-chain boundary.

## Required check design

The GitHub Actions workflow is named `Validation suite` and contains two
substantive validation jobs:

- `Static, recovery and evidence checks`;
- `WAN handler and install rollback checks`.

Issue #130 requires a single stable required check for branch protection. The
workflow therefore exposes an aggregate job also named `Validation suite`.

The aggregate job:

- always runs after both substantive jobs finish;
- prints both dependency results;
- succeeds only when both dependencies report `success`;
- fails when either dependency fails, is cancelled, or does not complete
  successfully.

This avoids protecting `main` with only one half of the validation workflow and
gives the ruleset one stable status-check context.

## Target repository ruleset

Create one active branch ruleset targeting only the default branch:

```text
Ruleset name: Protect main
Enforcement:  Active
Target:       default branch / main
Bypass:       none
```

Enable these rules:

- restrict deletions;
- block force pushes;
- require a pull request before merging;
- require status checks to pass;
- require the `Validation suite` status check;
- require the branch to be up to date before merging.

Do **not** enable a blanket `Restrict updates` rule. Normal merges from approved
pull requests must remain possible.

## Pull-request review decision

A mandatory human approval is not enabled in the initial #130 baseline.

Reason: the repository currently uses a single-maintainer workflow, so requiring
another approving reviewer would either deadlock normal maintenance or create a
meaningless self-approval exception.

Sensitive changes still remain subject to:

- branch-based development;
- pull-request diff review;
- required repository validation;
- deployment-time backup/rollback and live validation where applicable.

If an independent maintainer/reviewer is added later, firewall, installer,
recovery, authentication and deployment-sensitive paths are good candidates for
CODEOWNERS plus a required approving review.

## Secret and privacy boundary

Branch protection does not change the existing publication rules.

Never commit:

- credentials, passwords, reset tokens or session cookies;
- SSH/TLS private keys;
- Tailscale node/auth state;
- real recovery addresses or SMTP application passwords;
- private router exports;
- unsanitized DNS history, packet captures or household browsing data;
- other deployment-specific secrets already excluded by repository policy.

The ruleset reduces accidental source-control changes. It is not a secret
scanner, artifact-signing system or deployment authorization system.

## Activation order

1. Merge the aggregate `Validation suite` check to `main` through a normal PR.
2. Confirm the aggregate check has completed successfully at least once.
3. In repository settings, create the `Protect main` ruleset with the controls
   above.
4. Read back the effective rules applying to `main`.
5. Create a small follow-up PR after protection is active and confirm it can
   merge only after `Validation suite` passes.
6. Perform a bounded direct-push rejection test from a temporary local commit.
7. Record sanitized evidence and close #130 only after both the normal-PR and
   direct-push paths are validated.

## Direct-push rejection test

Do this only after the effective rules have been read back and confirmed.

Create a temporary local branch from current `origin/main`, make an empty test
commit, and attempt to push that commit directly to `main`.

Expected result:

```text
DIRECT_MAIN_PUSH=REJECTED
```

The test commit must never become part of `main`. If GitHub unexpectedly accepts
it, stop and repair the branch history through a normal reviewed recovery path
before claiming #130 complete.

Do not use force-push as a test against production `main`.

## Acceptance

Issue #130 is complete only when all of the following are true:

```text
RULESET_ACTIVE=PASS
MAIN_DELETE_BLOCKED=PASS
MAIN_FORCE_PUSH_BLOCKED=PASS
PULL_REQUEST_REQUIRED=PASS
VALIDATION_SUITE_REQUIRED=PASS
NORMAL_PR_AFTER_RULESET=PASS
DIRECT_MAIN_PUSH_REJECTED=PASS
DOCUMENTATION=PASS
```

Signed tags/releases and deployment artifact signing remain later extensions.
