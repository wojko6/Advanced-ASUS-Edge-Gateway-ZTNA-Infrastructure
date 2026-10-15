# RouterCloud #151 — legacy browser-access PR reconciliation

**Audit date:** 2026-10-15  
**Scope:** GitHub [Draft PR #151](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/151), branch `feat/issue-137-routercloud-browser-access`, versus source-controlled `main` as inspected on 2026-10-15.  
**Decision:** **do not merge the old PR**; preserve dated evidence and snapshot, then close #151 as **superseded** after clean archival PR passes CI. Do **not** re-enable or install old startup scripts/configuration. The review is **GitHub source inspection only**, not a fresh physical ASUS boot/restore test.

## 1. Version and issue context

- PR #151: **43 branch commits**, **21 changed files**, diverged from `main` and **225 commits behind** at the comparison checkpoint. GitHub reported `mergeable_state=dirty` (conflicting). Its previous historical CI `success` is not CI acceptance against current `main`.
- [Issue #137](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/137), browser-based LAN/Tailscale service: **CLOSED 2026-10-01** following operator-reported separate live/reboot and safe-rename acceptance. The old PR text that said `#137 remains open` is a **dated 2026-09-30 statement**, not the current issue status.
- [2026-10-03 production RouterCloud checkpoint](../routercloud-production-checkpoint-2026-10-03.md) documents **later** application-specific login, password recovery, Favorites and separate controlled delete/edit authorization; it also says **generic Dufs deletion remained disabled**. Do not conflate the 2026-09-30 generic DELETE denial with today's entire application feature set.
- [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) is **OPEN/HOLD** for SSD/JFFS privilege, nonroot PrivDrop and active-user-file HTTP origin isolation. The earlier `#137` file-service boundary and negative tests **do not** close these later findings.

## 2. File-by-file disposition

The original 21-file change set is divided by current purpose rather than copied indiscriminately.

| Original PR #151 path | Finding against current main | Decision |
| --- | --- | --- |
| `PROJECT-STATUS.md` | Main has substantially more recent #235, DNS, monitoring and architecture state | **DO NOT REPLAY** |
| `config/dnsmasq.conf.add.example` | Historical addition `host-record=cloud.home.arpa,192.168.50.254` absent from *this* main example | Record as **source/live split-DNS parity question**; do not insert unreviewed host-record into managed example |
| `config/dufs-personal-cloud.yaml.example` | Not in main; historical Dufs v0.46.0 example (global delete off, independent allow-move) | Keep only in original PR history; **NOT SAFE to install as current complete template** |
| `config/edge.conf.example` | Active main has different and later configuration controls | **DO NOT REPLAY** obsolete names/defaults |
| `docs/architecture/tailscale-management-exit-node-flow.md` | Main has newer architecture and separate security evidence | **DO NOT REPLAY** |
| `docs/firewall-policy.md` | Current state differs in RouterCloud allowlist and service policy | Audit contrast in section 3, no firewall mutation |
| `docs/personal-cloud-browser-access.md` | Unique detailed historical design but old `#137` and feature statuses | **ARCHIVED** under [2026-09-30 history](../history/routercloud-browser-access-2026-09-30.md), with prominent dated note |
| `docs/roadmap.md` and `docs/testing.md` | Current main supersedes September status and procedures | **DO NOT REPLAY** |
| `docs/worklog/2026-09-30.md` | Main already contains a 2026-09-30 worklog on other accepted work | Preserve unique #137 proof as **separate dated evidence**, not overwrite worklog |
| `evidence/2026-09-30/issue-137-routercloud-browser-access-validation.md` | Unique operator-reported source, absent from main | **PRESERVED** at [its original evidence path](../../evidence/2026-09-30/issue-137-routercloud-browser-access-validation.md), with Oct 15 chronology note |
| `router/init.d/S66routercloud-ip` | Not tracked in current main at same path | Historic alias bootstrap script. **Do not activate**, compare with actual installed Entware script in a separately approved read-only check |
| `router/init.d/S67routercloud` | Not tracked in current main at same path | Historic **root-launched daemonize/PID/kill** contract; may conflict with #235 PrivDrop, current config and state. **Do not activate** |
| `router/scripts/routercloud-post-mount` | Not tracked in current main | Historic wait/retry entry; potential conflict with trusted JFFS post-mount / swap-before-AMTM #235. **Do not activate** |
| `router/scripts/firewall-start` | Main is significantly newer and uses renamed RouterCloud controls | **DO NOT REPLAY** |
| `scripts/healthcheck.sh` | Current main significantly extended; old policy checks are not a complete gate | **DO NOT REPLAY** |
| `tests/test-config-validation.sh` | Historical variable-name assertions are outdated | **DO NOT REPLAY** |
| `tests/test-firewall-mock.sh` | Current main test suite has evolved | **DO NOT REPLAY** |
| `tests/test-healthcheck-config-validation.sh` | Current main differs in accepted fields and policy | **DO NOT REPLAY** |
| `tests/test-routercloud-browser-static.sh` | Missing in main, but checks **old** variable names and file locations | Retain in original PR as evidence, **do not activate** as a new CI gate |
| `tests/test-static.sh` | Current main has many additional current-state checks | **DO NOT REPLAY** |

**No 2026-09-30 configuration, firewall or router init script is copied into a live installable path by this reconciliation.** Archival documents do not count as boot-component implementation or tested rollback.

## 3. Security-relevant differences requiring deliberate future review

### Remote source authorization

- Historical PR #151 used **`EDGE_ROUTERCLOUD_TS_SOURCES`**, a RouterCloud-specific allowlist, and `EDGE_ROUTERCLOUD_PORT`.
- Current `main` uses `EDGE_ALLOW_ROUTERCLOUD`, `EDGE_ROUTERCLOUD_HTTPS_PORT`, and checks/adds RouterCloud INPUT rules for **`EDGE_ADMIN_TS_SOURCES`** in `router/scripts/firewall-start` and `scripts/healthcheck.sh`.
- **Design consequence:** the separately configurable RouterCloud source list from the old candidate is not present in current main. Whether this grants unintended access depends on actual private runtime lists, Tailscale Grants and app authentication; **no unintended exposure or exploit is established** by comparing these scripts. Record as an independent **least-privilege / identity-policy review question under #235** rather than restore old firewall code from a conflicting branch.

### Boot and service ownership

- The historical `S66routercloud-ip` uses `ip addr` to establish the service alias, and `S67routercloud` launches `/opt/bin/dufs-personal-cloud` through `daemonize` with PID/lock files. It includes stop-time process killing, and no audited `setuid`/capability drop. Neither script is a verified replacement for today's installed router services.
- The historic `routercloud-post-mount` invokes both scripts after a data-directory check. **Main contains no tracked counterpart at the same path**; live startup files under `/opt/etc/init.d` and `/jffs/scripts/post-mount` cannot be inferred solely from Git absence.
- For #235, preserve trusted JFFS ownership/mode checks, **swap-before-AMTM** dependency order and the separately observed **UID 1000-owned `services-start`** discrepancy. Never run the generic installer or overwrite private startup hooks while resolving this historical PR.
- A future **read-only** actual script/hash/config provenance comparison is appropriate; that work does not authorize startup changes, reboots, new service UIDs or permissions updates.

### DNS and application boundary

- Historical `cloud.home.arpa` split DNS and `192.168.50.254` alias were operator-reported in the dated acceptance. The tracked `main` `config/dnsmasq.conf.add.example` intentionally shows a **generic resolver fragment**, not the old host-record. Do not equate missing example text with a missing production DNS record.
- Old Dufs YAML `allow-delete: false` described generic Dufs v0.46.0. Later app-specific delete capabilities do not prove generic deletion should be enabled. Historical binary hashes may differ from October production; do not transplant old file assumptions.
- Both #151 and #137 predate the current active-file **same-origin/404** investigations. Their rooted serve directory/no-WAN checks and source allowlists are **not** a substitute for HTTP header, browser origin, auth/cookie and nonroot execution negative tests under #235.

## 4. Preserved source evidence and current authority

**Preserved here:**

1. [September 30 #137 operator-reported browser-access evidence](../../evidence/2026-09-30/issue-137-routercloud-browser-access-validation.md), date-scoped and explicitly marked as historical.
2. [September 30 browser-access design narrative](../history/routercloud-browser-access-2026-09-30.md), historical and not installable.
3. The original code/config files remain reviewable through [PR #151](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/151) and its historical commits. They have **not** been imported as current runbooks.

**Current source of truth:** [PROJECT-STATUS.md](../../PROJECT-STATUS.md), [Oct 3 RouterCloud production checkpoint](../routercloud-production-checkpoint-2026-10-03.md), [2026-10-15 #235 worklog](../worklog/2026-10-15.md), [secure browser-service case study](../case-studies/routercloud-secure-browser-file-service.md). These dated documents may themselves require newer runtime verification; this archive does not elevate their scope.

**Remaining test gates:** recorded source/live allowlist distinction, exact installed launcher supervision/identity and hash parity, split DNS ownership, and active-file origin/PrivDrop acceptance. No router access, process restart, chmod, config activation, Git config patch, or production rollout was conducted for this GitHub-only audit.

## 5. PR closeout gate

Once the **new documentation-only clean PR** containing this audit and both preserved historical reports passes complete current-main CI and merges, close **Draft #151 as superseded (NOT merged)**, with a link to the new PR. Historical changes not carried forward are **intentionally omitted**, not described as validated or auto-implemented. Do not use PR closure to assert #235 closure.
