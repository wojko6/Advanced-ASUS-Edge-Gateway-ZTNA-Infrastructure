# Security policy

This repository documents a Home/SMB security lab and reference deployment. It is not a managed security product and does not provide a guaranteed security-response SLA.

## Reporting a security issue

Do not open a public issue containing sensitive evidence or details that would make an unpatched deployment easier to compromise.

Keep the following out of public issues, pull requests, discussions, and evidence commits:

- router configuration exports or backups;
- credentials, password hashes, API/auth tokens, SSH private keys, TLS private keys, or Tailscale auth/state material;
- real private-network inventories when they identify the deployment;
- public WAN addresses, DDNS credentials, router serial numbers, or device MAC addresses;
- unreviewed packet captures, DNS logs, syslog archives, or screenshots containing sensitive traffic;
- browser profiles, cookies, session identifiers, exported trust stores, or endpoint-filter CA private material;
- exploit details for a vulnerability that remains exposed on the reference deployment.

When reporting a problem publicly, provide the smallest sanitized reproduction that still demonstrates the issue: affected component, repository version/commit, firmware or OS version, expected behaviour, observed behaviour, and redacted logs when necessary.

## Credential or identity compromise

For a suspected credential or Tailscale identity compromise:

1. revoke the affected Tailscale device/key or identity session;
2. remove the affected identity/device from applicable Grants/groups and `EDGE_ADMIN_TS_SOURCES`;
3. rotate affected router and service credentials;
4. inspect available configuration and authentication logs from a trusted system;
5. review whether backup/evidence artifacts may also contain exposed material;
6. restore/reapply the known-good firewall and management policy from a trusted LAN recovery path when required;
7. validate management, DNS, routing, and Tailscale behaviour before restoring normal remote administration.

Do not rely on remote access as the only recovery path for a management-plane incident.

## Endpoint HTTPS-filtering incidents

Endpoint HTTPS/content filters introduce a separate local trust boundary when they install a root CA or intercept TLS. If an endpoint-filter certificate/private key, installer source, or local proxy is suspected to be compromised:

1. disable the endpoint filter;
2. disconnect the affected endpoint from sensitive sessions when appropriate;
3. remove the filter's trusted root certificate according to the product's documented removal procedure;
4. verify that the unexpected CA is no longer trusted by Windows and relevant browsers/applications;
5. rotate credentials or sessions that may have traversed the compromised endpoint when exposure is plausible;
6. preserve only sanitized incident evidence.

An endpoint-filter incident does not automatically imply compromise of the router DNS resolver, Tailscale state, or firewall. Investigate each trust boundary separately.

## Evidence disclosure

Treat raw packet captures and full logs as private by default. Prefer minimized text extracts that have been manually reviewed. Follow `docs/evidence-collection.md` before publishing evidence.

Evidence should describe what was observed, when, and under which version/configuration. Absence of an event in a limited test window is not proof that it can never occur.

## Deployment safety

Apply changes only to devices you control or are authorized to administer. Preserve a physical/trusted-LAN recovery path and validate changes against the actual Asuswrt-Merlin/Entware target before relying on them remotely.

The reference router is under an unchanged-state stability observation from 2026-09-11 through 2026-09-25. During that gate, do not modify router firewall, DNS, Unbound, Tailscale, startup hooks, filtering lists, services, or intentionally reboot the device merely to test a repository change. Documentation, CI/mock tests, workstation-local endpoint tests, and read-only router observations can continue without invalidating the intended unchanged-state observation.

Security fixes that are necessary to address an active compromise or materially unsafe exposure take priority over the observation gate. If an emergency change is required, document that the stability observation was interrupted and start a new observation period after the deployment returns to a known-good state.
