# Issue #235 — bounded production read-only privileges and Fedora-only rootless labs (2026-10-21)

> **Classification:** sanitized, operator-reported evidence; **Issue #235 OPEN / `DEPLOYMENT_GATE=HOLD`**. Separate from the approved Tailscale router update and Fedora monitoring changes on the same calendar day. No live DUFS, JFFS, mount-mode, router file or service modification is attributed to this security review.

## Evidence provenance and chronology

- Browser regressions V2.30M/N/N1/O/P/P1, source inventories V2.30Q, router metadata R/R1/R2, design S and kernel/rootless integrations T/U/V were run by the operator in their stated limited scopes. Their printed `PASS`, `HOLD` and `SKIP` statuses are not replaced with inferred success.
- Authorized ASUS read-only metadata collection V2.30R2: `2026-10-21T18:36:51Z`. First V2.30R/R1 runs were partial because the original firmware metadata provider could not be used; R2 used fixed firmware BusyBox `ls`.
- Source snapshot used for the Fedora DUFS 0.46.0 research: 59 files, manifest SHA-256 `8a3f64720476039ab78841dda49e88af9edac949658eded746e7c129e4ca9319`. This is a pinned **source snapshot input**, not a reproducible-build or production binary provenance claim.

## Approved read-only ASUS filesystem and process checkpoint — V2.30R2

| Observation | Operator-reported result | Limits |
| --- | --- | --- |
| Process identity | One heuristic `comm` + executable-basename RouterCloud process match | Neither executable hash nor supervisor child lineage verified |
| Runtime credentials | Real/effective/filesystem UID=0, GID=0; `CapEff=0000003fffffffff` | Process capability bitmask as observed; not a claim of an exploited vulnerability |
| SSD volumes | Both ext4, RW, both mount roots root-owned `0777` | Mount root != necessarily renameable active mountpoint |
| Entware subtree | Root-owned `0755`, `/opt` symlink points to expected tree | Symlink metadata `lrwxrwxrwx` is not a normal symlink permission gate |
| Active-asset historical path | Root-owned directory `0755`; four UI files root-owned `0644` | The historical pinned path was **not validated against the current YAML `assets:` mapping** |
| Backup path | Parent `0777`; private child `0700`; staged candidate `0600` | Private contents protected by DAC, but parent name-replacement risk needs independent review |
| Startup metadata | RouterCloud init executable root-owned `0755`; YAML root-owned `0600`; JFFS scripts root-owned `0755` | No YAML contents or credentials read |
| FD scan | 147 processes, 879 FDs, zero open writable FDs under historical asset path; no truncation | Point-in-time absence is **not** proof no transient or future writer can access the path |
| Audit coverage | 24/24 expected metadata slots available | Not a complete ACL, namespace, publisher-authority or service-identity attestation |

The historical `0777` mount-root observation was already tracked under [14 October Entware evidence](../2026-10-14/entware-feed-and-ssd-permissions.md) and [Draft PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245), whose candidate is **not installed**. No `chmod`, `chown`, mount, restart, secrets inspection or active publication was performed as part of V2.30R–R2.

## Firefox/HTTP E2E — Fedora only

| Version | Bounded observation |
| --- | --- |
| V2.30M | 15/15 self-tests, 10/10 real Firefox E2E; untrusted HTML/SVG script execution denied, cross-origin read denied |
| V2.30N | Hold before auth tests due to wrong versioned asset URL |
| V2.30N1 | 22/22 self-tests, 19/19 Firefox E2E; explicit request-header Basic Auth and operator/viewer access-control checks |
| V2.30O | 21/21 self-tests, 19/19 Firefox E2E; cross-origin authorized `PUT` was preflight-rejected and synthetic target unchanged; `no-cors POST` opaque response did not establish that no request was sent |
| V2.30P/P1 | 22/22 and 26/26 self-tests respectively, but **`SKIP_NO_VERIFIED_AMBIENT_BASIC_AUTH`** (exit code 2) in live Firefox; cached Basic credential/CSRF acceptance remains **unproven** |

These tests were performed against fresh local disposable backend builds, with synthetic Basic credentials and loopback HTTP. Browser OS-level network isolation and production cookie/session behavior were **not** established.

## Publisher, sealed configuration and ancestor boundary — Fedora only

- **V2.30Q:** 12/12 static inventory self-tests, 16/16 source indicators, listing known staging/activation/rollback entrypoints; neither signed publisher authority nor all possible writers were proven.
- **V2.30S:** 30/30 self-tests of an offline DAC model based on saved V2.30R2 output, not a new router audit.
- **V2.30T:** 17/17 model self-tests; kernel user-namespace three-role fixture Publisher 8/8, Untrusted 8/8, HTTP 16/16 and integration 7/7. Sealed `memfd` handed off configuration bytes without granting path read to the HTTP role.
- **V2.30U:** 23/23 self-tests, 11/11 HTTP-child checks, 10/10 live checks of a **real** snapshot-built DUFS 0.46.0 on Fedora. The process ran as nonroot with zero capabilities; `--config /proc/self/fd/N` parsed the sealed YAML; it served separate synthetic data/UI assets while failing to write into the protected UI tree.
- **V2.30V:** 25/25 self-tests; 12/12 HTTP-kernel and 10/10 supervisor checks. A synthetic **non-mountpoint** `0777` parent allowed an unprivileged rename/path-spoofing result; `0755` and `1777` denied it. An already-open FD continued to reference the original inode. This does **not** establish that a live ASUS mountpoint can be renamed or that the full publication race is covered.
- **V2.30W:** script prepared/distributed for a real-DUFS ancestor-path test, but **not run** by the operator at the end of 21 October; **zero V2.30W execution claims**.

## Open gates and safe handoff

1. Independently bind the actual RouterCloud `assets:` mapping and process executable identity, preserving secrets and read-only scope.
2. Establish an authorized Publisher whose control over ancestry, signatures, staged objects and rollback cannot be bypassed by an untrusted writer. A root-owned `0644` file alone is insufficient proof of safe path ancestry.
3. Validate an ARMv7-compatible least-privilege service startup and config handoff; Fedora user namespaces do not certify actual ASUS/Entware, Linux 4.1.52 or startup ordering.
4. Address mount-root `0777` only after separately approved safety gates; leave [Draft PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) separate.
5. Test real session/CSRF and the still-open `V2.30W=NOT_RUN` case if/when the operator resumes.

**Final state:** `ISSUE_235=OPEN`; `PUBLISHER_AUTHORITY=NOT_PROVEN`; `ASUS_NONROOT_DUFS=NOT_TESTED`; `V2.30W=NOT_RUN`; `DEPLOYMENT_GATE=HOLD`. This file is evidence/documentation only, not deployment authorization.
