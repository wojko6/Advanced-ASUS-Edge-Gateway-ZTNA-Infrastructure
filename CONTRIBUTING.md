# Contributing

Contributions should preserve the project's security boundaries, reproducibility, and evidence quality. A change that makes the lab look more capable on paper but is not supported by code or observed evidence is not an improvement.

## Code and router-policy changes

Keep deployed scripts compatible with BusyBox `sh` unless a script explicitly declares another shell.

New router rules or services must be:

- least-privilege and fail-closed where practical;
- idempotent;
- scoped to project-owned chains/hooks instead of silently taking ownership of unrelated firmware state;
- covered by an appropriate mock/static/recovery test;
- documented in the firewall policy, security design, and threat model when they alter a trust boundary;
- paired with rollback/recovery guidance when failure could affect management access, DNS, routing, or startup.

Do not introduce boot-time package upgrades or other uncontrolled external changes into the validated startup path.

## Documentation changes

Documentation must distinguish between:

- implemented behaviour;
- behaviour validated in CI/mock tests;
- behaviour observed on the reference router or a defined client;
- planned work;
- known limitations.

Avoid words such as `production-grade`, `enterprise-grade`, `fully secure`, `guaranteed`, or `blocks all` unless the repository contains evidence that genuinely supports the exact claim. The ASUS deployment is an enterprise-style Home/SMB lab, not a high-availability enterprise appliance.

When a document introduces a new validation layer, keep its results separate from other layers. For example, endpoint HTTPS/content filtering must not be described as router-side filtering capability.

## Before a pull request

Run the repository test suite on a Linux workstation or CI runner:

```sh
sh tests/test-static.sh
```

When a change affects one of the independently checked deployment paths, also run the relevant focused test:

```sh
sh tests/test-wan-event-handler.sh
sh tests/test-install-rollback.sh
```

Do not run repository tests on the production/reference router unless a procedure explicitly requires router-local validation.

## Evidence contributions

Never include secrets, real credentials, private packet captures, Tailscale node state, router configuration exports, browser profiles, cookies, session tokens, exported trust stores, certificate private keys, or unreviewed raw logs.

Evidence must:

1. identify the date and relevant software/configuration versions;
2. identify the source role or device and the defined test scenario;
3. distinguish expected from observed behaviour;
4. use `Observed`, `Not observed`, `Not tested`, or `Inconclusive` where those terms fit;
5. preserve failed or negative results when they explain a later fix;
6. state important limitations and confounding variables;
7. pass the manual publication review in `docs/evidence-collection.md`;
8. include a regenerated SHA-256 manifest when the dated evidence set uses one.

Prefer minimized, sanitized text evidence over screenshots, full packet captures, or complete logs. Only create a dated evidence directory after a real test has been performed and reviewed; empty templates are not validation evidence.

## Stability observation gate

The reference router is in an unchanged-state stability observation from 2026-09-11 through 2026-09-25. During that period, documentation, repository work, CI/mock testing, and workstation-local endpoint experiments are acceptable. Do not use a contribution as a reason to change router firewall, DNS, Unbound, Tailscale, startup hooks, filtering lists, services, or to intentionally reboot the router before the observation completes.

Read-only router observations are acceptable when needed to corroborate a test without changing the validated state.
