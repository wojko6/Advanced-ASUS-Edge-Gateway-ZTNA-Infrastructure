# RouterCloud secure browser file service — case study

## Scope

This case study summarizes the production-validated RouterCloud deployment on
the reference ASUS edge gateway. The detailed operational source of truth
remains the dated [2026-10-03 production checkpoint](../routercloud-production-checkpoint-2026-10-03.md).

RouterCloud is a browser-facing Personal Cloud service constrained to the
existing LAN/Tailscale trust boundary and to a dedicated data root rather than
the router filesystem.

## Security and architecture decisions

The validated design includes:

- HTTPS-only browser access inside the existing trusted network boundary;
- custom login/session authentication;
- production-tested password recovery;
- backend-authorized rename, delete, edit and archive operations;
- generic Dufs delete kept disabled;
- WebDAV desktop integration;
- AJAX sorting and live search without full-page reloads;
- persistent favorites and recent-files UI;
- independent versioned encrypted backups through a read-only Fedora pull path;
- versioned frontend assets and rollback copies;
- explicit separation between CI, browser acceptance and production evidence.

The design intentionally avoids turning RouterCloud into a general-purpose
router-filesystem browser. File operations are limited to the dedicated
RouterCloud content root and must pass the application authorization layer.

## Validation

The production checkpoint records the live service state after the 2026-10-03
deployment. Separate evidence covers the UI and password-recovery paths:

- [UI production validation](../../evidence/2026-10-03/routercloud-ui-production-validation.md)
- [password-recovery production validation](../../evidence/2026-10-03/routercloud-password-recovery-production-validation.md)

## Portfolio value

This case is useful because it demonstrates how a lightweight upstream file
server can be extended without silently broadening its filesystem, network or
authorization boundary. The important engineering work is the trust-boundary
design, controlled mutation API, deployment/rollback discipline and independent
backup path rather than the visual frontend alone.

## Claim boundary

The case supports the tested RouterCloud deployment and its documented
LAN/Tailscale-only access model. It does not claim Internet exposure, general
router-filesystem access, or that repository CI alone proves browser/runtime
behavior.

For implementation and current-state details, use the
[production checkpoint](../routercloud-production-checkpoint-2026-10-03.md) as
the authoritative dated record.
