# Runtime-drift health-check hardening live validation — 2026-09-22

**Status:** PASS  
**Evidence class:** Router live / controlled maintenance  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin

## Purpose

Validate deployment of the health-check hardening added after the legacy `nat-start` cleanup. The new revision detects:

- direct exact-interface Tailscale NAT rules in parent `PREROUTING` that bypass the project-owned `EDGE_TS_PREROUTING` chain;
- active JFFS hooks relevant to this deployment that are symlinked or group/world writable.

## Pre-deployment validation

The repository copy had SHA-256:

```text
5d96555bad141c40191855e2f121de0412635cb7e5fe14d41b5ec73842db6233
```

The candidate was transferred to a temporary router path, then:

- the SHA-256 was verified;
- `sh -n` returned success;
- the full test run completed with zero failures and zero warnings;
- both new drift controls reported `[OK]`.

Observed new checks:

```text
[OK]   no direct Tailscale NAT rules outside EDGE_TS_PREROUTING
[OK]   active JFFS hooks are not group/world writable or symlinked
```

## Controlled deployment

The previously deployed health-check revision was verified before replacement and backed up. The hardened candidate was re-verified before installation.

After installation, the live health check completed successfully:

```text
Summary: 0 failure(s), 0 warning(s)
LIVE_HEALTHCHECK_RC=0
```

Final active-file SHA-256:

```text
5d96555bad141c40191855e2f121de0412635cb7e5fe14d41b5ec73842db6233
```

Deployment completion marker:

```text
DEPLOYMENT_OK
```

## Result

**PASS.** The runtime-drift hardening revision is deployed on the reference router and the live health check passes with the expected repository-matching digest.

## Claim boundary

This validates the deployed health-check revision and the router state observed during this run. It does not guarantee that future configuration drift cannot occur, and it does not imply that later repository revisions are automatically deployed.

Deployment-specific addresses, identities, credentials, private backup paths, and unrelated raw router output are intentionally omitted.
