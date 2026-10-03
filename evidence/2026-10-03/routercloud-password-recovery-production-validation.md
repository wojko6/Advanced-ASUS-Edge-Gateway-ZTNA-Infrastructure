# RouterCloud password recovery — production validation (2026-10-03)

## Scope

This artifact records the controlled production rollout and end-to-end validation of the RouterCloud password-recovery flow on the reference ASUS Edge Gateway deployment.

No passwords, reset tokens, SMTP application passwords, cookies, or real recovery-address values are included.

## Repository revisions

Frontend / infrastructure branch:

- branch: `feat/routercloud-password-recovery`
- validated frontend commit: `0e0486f4cbc4ae22303a3d84c816560928b2e120`
- commit subject: `feat(routercloud): add secure password reset UI`

Backend candidate:

- feature branch: `feat/routercloud-password-recovery`
- candidate SHA-256: `ab6343c1743f99788ddac7e80e3de65aa3d58643ea8b640376e282b394e28d26`
- backend source revision used for the final build: `addd6eaa2efb0efaa137cd79ee9c84087338b919`

The pre-deployment production binary SHA-256 was:

`e846edc7daa5cf2f2f037d087c8c1f7fd7507287cc4dde7fa10ac8f2760ef186`

## Recovery design

The deployed flow keeps the reset token out of the HTTP query string.

The mail link uses:

`https://cloud.home.arpa/__routercloud/login#reset_token=<token>`

The browser reads the token from the URL fragment, removes the fragment from the address bar with `history.replaceState`, and submits the token only in the password-reset confirmation POST body.

The recovery request endpoint intentionally returns a neutral response so the UI does not disclose whether the supplied address maps to the configured account.

The production recovery configuration maps the RouterCloud account to one configured recovery address and references the SMTP curl configuration by path. Credential material itself is not stored in the repository.

## Deployment safety

Before the production switch:

- the active RouterCloud binary, YAML configuration, init script and frontend assets were captured in a rollback snapshot;
- the rollback directory was verified before any active replacement;
- the new ARMv7 binary candidate was verified by SHA-256;
- the seven Metro frontend assets were uploaded to a fresh versioned staging directory and verified against local hashes;
- password-recovery UI markers were verified in the staged login assets;
- the active production binary and active asset directory were rechecked immediately before cutover;
- the production HTTPS endpoint returned the expected unauthenticated health response before cutover.

The final deployment used a same-session staging-and-switch procedure. This avoided the earlier shell-stdin issue where nested SSH commands could consume the remaining local heredoc.

The production service was stopped only after staging verification completed. The new binary and YAML configuration were then atomically moved into place, the service was started, and the listener, active binary hash, active configuration and frontend markers were revalidated.

Rollback remained available from the pre-password-recovery production snapshot throughout the cutover.

## Production acceptance

Observed production checks completed successfully:

- production HTTPS listener returned after the service restart;
- active production binary matched SHA-256 `ab6343c1743f99788ddac7e80e3de65aa3d58643ea8b640376e282b394e28d26`;
- the active YAML contained the four password-recovery configuration keys;
- the production login page returned HTTP 200;
- the deployed login HTML contained the recovery/reset UI markers;
- the deployed login JavaScript contained the fragment and hash-change reset markers;
- a neutral reset request using a non-configured syntactically valid address returned HTTP 204;
- the health-check request did not trigger a real recovery mail;
- the normal unauthenticated RouterCloud root continued to return the expected authentication response.

## Real end-to-end recovery test

A real production password reset was then performed through the user-facing flow.

Observed sequence:

1. The production "forgot password" form accepted the configured recovery address.
2. The reset message was delivered through the configured Gmail SMTP path.
3. The received link targeted the production `cloud.home.arpa` endpoint and did not contain the isolated smoke-test port.
4. The browser opened the new-password form from the URL fragment.
5. A new password was accepted by the production confirmation endpoint.
6. The UI reported that the password had been changed.
7. Login with the new password succeeded.
8. The RouterCloud service was restarted.
9. Login with the new password succeeded again after the restart.

The final post-restart login is the live persistence check: the new credential remained effective across a fresh service process rather than existing only in in-memory state.

## Security properties validated or preserved

The rollout preserved these project boundaries:

- reset links keep the token in the URL fragment rather than the query string;
- raw reset tokens are not intentionally written to repository files or production configuration;
- the recovery UI does not distinguish whether an arbitrary submitted address belongs to the account;
- password policy remains bounded to 12–128 characters;
- SMTP credentials remain in the private router-side curl configuration and are not published;
- the RouterCloud service remains on the existing LAN/Tailscale-only trust boundary;
- generic Dufs delete policy remains independent of the recovery feature;
- a rollback snapshot from immediately before the password-recovery deployment remains available.

## Result

```text
PASSWORD_RECOVERY_PRODUCTION_E2E=PASS
PASSWORD_RESET_MAIL_DELIVERY=PASS
PASSWORD_RESET_FRAGMENT_FLOW=PASS
PASSWORD_CHANGE=PASS
POST_RESET_LOGIN=PASS
SERVICE_RESTART=PASS
POST_RESTART_LOGIN=PASS
ROLLBACK_SNAPSHOT=AVAILABLE
```

## Evidence boundary

This artifact records the controlled 2026-10-03 deployment and the observed production recovery flow. It does not claim long-term SMTP deliverability, high availability, multi-user account recovery, or protection against compromise of the configured mailbox.

The exact recovery address, reset tokens, passwords, application password, cookies and private authentication material are intentionally omitted.
