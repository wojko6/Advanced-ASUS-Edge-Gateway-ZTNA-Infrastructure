# Tailscale 1.103.375 router runtime upgrade — validation

Date: 2026-10-06

## Scope

Sanitized validation of the reference ASUS TUF-AX5400 router after replacing
the previously validated live Tailscale 1.102.3 binaries with the official ARM
unstable build 1.103.375.

This artifact documents the later same-day runtime state. Earlier evidence that
records 1.102.3 remains historically correct for the checkpoint at which it was
captured.

## Pre-upgrade state

The live router binaries reported:

```text
1.102.3
tailscale commit 9329c3677031109ff6d0b80abee0cddc8f35ff6f
long 1.102.3-t9329c3677-ga522f65e9
```

Entware package metadata remained substantially older than the live binary:

```text
installed package metadata: 1.96.1-1
feed candidate:             1.96.1-1
```

The repository-side downgrade-prevention work therefore remains relevant even
after the manual runtime upgrade.

## Rollback material

A pre-upgrade rollback snapshot was created before replacing the live binaries.

The snapshot directory name retains an earlier planned target-version label, but
its contents represent the actual pre-upgrade 1.102.3 runtime.

The rollback set included the previous Tailscale binaries, init script, daemon
state and relevant project configuration.

## Upgrade source and integrity

The selected official archive was:

```text
tailscale_1.103.375_arm.tgz
```

Archive SHA-256:

```text
d7f825b307eda0ea2370ad6231c6831bfd8b0ce3432ff29a98b5b955eb54e784
```

The extracted ARM binaries were verified before deployment.

Live binary SHA-256 values after deployment:

```text
tailscale
be10e7ee0f1ec96360e12622c81c57dea09d490aef8b3b902830a55f30cf7e9b

tailscaled
088ede9059ba1f46e42cf502a8850bcb44124a8b341527e9c68c7a8a56f6e45f
```

## Final runtime version

The reference router reported:

```text
1.103.375
track unstable (dev)
tailscale commit f5f326030b8b681079c84799ba5ec097601fcaff
long 1.103.375-tf5f326030-gfa000e593
go1.27.1
```

This is the authoritative current live Tailscale version for the reference
router as of the end of 2026-10-06.

## Runtime validation

The upgrade was followed by a full controlled Tailscale service restart.

Observed after restart:

- the daemon returned successfully;
- the router retained its Tailscale identity;
- subnet-route advertisement remained present;
- exit-node advertisement remained present;
- direct peer connectivity remained functional;
- the project continued to use `netfilter-mode=off`;
- no process swap use was observed for tailscaled at the validation checkpoint;
- tailscaled RSS remained approximately 34 MiB.

A later full router reboot performed during DNS Guard validation also returned
Tailscale automatically, so the 1.103.375 runtime survived the complete
cold-boot path.

## Exit-node and DNS follow-up

The same-day post-upgrade validation subsequently confirmed:

- Android LTE Internet traffic through the ASUS exit node;
- the Android route to public Internet addresses through the Tailscale TUN
  interface;
- successful public traffic through the exit-node dataplane;
- after DNS Guard v3.1 deployment and cold reboot, exit-node DNS reached the
  router system resolver and the local Pi-hole alias before Unbound.

The DNS-specific proof is recorded separately in:

- [DNS Guard v3.1 production validation](dns-guard-v3.1-production-validation.md);
- [DNS bootstrap deadlock and fail-open resolver recovery](../../docs/dns-guard-cold-boot-case-study.md).

## Maintenance boundary

1.103.375 is an **unstable/dev-track** Tailscale build.

It was selected and deployed deliberately after checksum verification and
runtime rollback preparation. It must not be confused with an Entware-managed
package version.

Until the Entware feed catches up or the repository updater gains a separately
validated official-tarball transaction mode:

- do not run an implicit package upgrade that would replace the newer live
  binaries with an older Entware package;
- preserve `AutoUpdate.Apply=false`;
- treat a future runtime change as a planned maintenance action;
- verify source archive integrity and binary provenance;
- retain known-good rollback binaries;
- repeat daemon restart, healthcheck, route advertisement and reboot
  validation after a material change.

## Result

```text
pre-upgrade live:  1.102.3
current live:      1.103.375
track:             unstable (dev)
daemon restart:    PASS
cold-boot return:  PASS
exit-node runtime: PASS
```

The earlier 1.102.3 evidence remains a valid historical checkpoint. It is not
the current live router version after this upgrade.
