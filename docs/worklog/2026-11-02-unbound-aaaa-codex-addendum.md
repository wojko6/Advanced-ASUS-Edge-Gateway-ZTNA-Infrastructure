# 2026-11-02 — Unbound AAAA/DNSSEC repair and Codex C64 review (supplement)

> **Scope:** Sanitized, operator-reported end-of-day supplement to [the November 2 worklog](2026-11-02.md). This is not a general production audit. It does not replace the independent DNS Guard Issue #287 laboratory record in [Draft PR #361](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/361). No secrets, local workstation user data, private screenshots or raw router logs are reproduced here.

## 1. Fedora Codex OAuth failure isolated to DNS AAAA handling

The operator installed the ChatGPT Linux RPM (reported version `chatgpt-26.1027.51404-1.x86_64`) and initially received `token_exchange_failed` while signing in to Codex. On Fedora, IPv4 HTTPS to `https://auth.openai.com/oauth/token` succeeded with expected method-not-allowed `HTTP 405` and successful certificate validation; time sync was good. DNS queries for public `AAAA` records failed with `SERVFAIL`, first for the OpenAI authentication name and then for `cloudflare.com`. IPv4 `A` records continued working. The same `SERVFAIL` occurred when querying the LAN Pi-hole directly, via both UDP and TCP. A checking-disabled (`CD`) query yielded `NOERROR` without usable `AAAA` records, which was diagnostic but not by itself proof of a particular validation defect.

Pi-hole v6 configuration was inspected read-only: it forwarded to a local resolver at `127.0.0.1#53535`, Pi-hole's own `dns.dnssec` was disabled, and its visible `misc.dnsmasq_lines` contained no `filter-AAAA` directive. On the ASUS router, `netstat` identified the listening process as **Unbound 1.26.2**, using the manager-generated runtime file `/opt/var/lib/unbound/unbound.conf`. The separate example at `/opt/etc/unbound/unbound.conf` was **not the live configuration** and led to an earlier misleading check.

The active manager configuration explicitly contained `do-ip6: no` **and** `private-address: ::/0`, with a header comment explaining that the latter deliberately drops all IPv6 answer addresses. Unlike `do-ip6: no`, which controls DNS transport, `private-address: ::/0` also covers public IPv6 results. With Unbound's strict `respip validator iterator` chain and DNSSEC hardening, that overbroad response policy explained the observed `AAAA` behavior. The causal chain was supported by successful recovery after removing only this directive; no independent packet-level root-cause reconstruction was performed.

## 2. Separately operator-authorized narrow Unbound production change

An initial shell attempt ran on Fedora rather than ASUS, failed to find the router paths and **did not modify the router**. The operator repeated the commands in the router shell:

1. Prepared a temporary copy of the **actual** runtime config and deleted exactly one active `private-address: ::/0` line. `unbound-checkconf` passed; `diff` showed a one-line content change.
2. Stored and verified a pre-change backup under the persistent Unbound Manager JFFS directory. File copy/integrity checks reported `BACKUP=PASS` and `BACKUP_INTEGRITY=PASS`.
3. Confirmed authenticated local `unbound-control status`, version 1.26.2, three modules (`respip validator iterator`), no service error.
4. Used a guarded copy/replace and `unbound-control reload` of the active configuration; reported `CONFIG_APPLIED=PASS` with the original Unbound PID still alive. The active file permissions changed from world-writable `0666` to `0644`; the backup was set to `0600`.
5. Verified against Unbound: `cloudflare.com AAAA` returned two public addresses with `AD=1` and an `RRSIG`; `auth.openai.com AAAA` returned two public IPv6 addresses; `cloudflare.com A` kept `AD=1`; intentionally invalid `dnssec-failed.org A` continued to return `SERVFAIL`.
6. From Fedora, flushed only the local DNS cache and confirmed OpenAI `AAAA` answers through both Pi-hole and `systemd-resolved`, `cloudflare.com AAAA` through Pi-hole, and HTTPS `405` / TLS verified to the OAuth token URL.

**Accepted scope:** the previously reproducible `AAAA SERVFAIL` condition cleared across Unbound → Pi-hole → Fedora, while positive and negative DNSSEC tests remained as expected. The operator's later GUI screenshot showed that the ChatGPT desktop app reached its authenticated onboarding and Codex interface; no proof of unrelated IPv6 routing, overnight DNS stability, or application backend correctness is implied.

**Outstanding production follow-up, not yet executed:** Unbound Manager has default `KEEPACTIVECONFIG="N"` and may restore its template during some upgrade flows. The operator should explicitly preserve the locally modified active config on a future upgrade, or design and test a manager-supported persistent override; do not claim update-persistence verified. Separately audit the reported `0777` `unbound.postconf` permissions, but do not combine permission and DNS policy changes in one unreviewed action. Backup and rollback are available; a restart/reboot persistence test was **not** performed.

## 3. Local AI Agent C64 review: source frozen; Codex found test and validation gaps

An assistant self-review was documented as **non-independent** PR comments for [#354](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/354), [#355](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/355), [#358](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/358) and [#359](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/359). All are **OPEN DRAFT / FROZEN FOR REVIEW**, no source-branch update or merge. The stacked relationship is #354 → #355 → #358 → #359, separate from Draft #353. No independent human security sign-off.

The operator then ran an additional review through the Codex desktop environment, using a local C64.1 checkout and GitHub source for later stages. Codex reported a clean local working tree, local C64.1 HEAD behind the expected PR SHA by two documentation-only commits while relevant code blobs matched, and **192 C64 tests plus 49 C63.8.1 parser tests passing in its sandboxed review environment**. These results were **reported by Codex**, not independently replayed on the router or by this documentation update. Codex did not report a proven P0/P1 issue, production request, model invocation, or privilege escalation; it did identify five concrete findings:

| Severity | Stage | Finding and required regression |
| --- | --- | --- |
| P2 | #355 / C64.1 | Network-denying mocks surround only selected tests; the older C63.8.1 `HTTPConnection` default is bound at function definition time. Run whole-suite network denial and assert injection before original fetch can execute. No real GET was observed. |
| P2 | #358 / C64.2 | Loopback ownership matching combines inodes across `127.0.0.1`, `127.0.0.2` and `::1`; a different loopback endpoint may be accepted as manual-review evidence. Match exact IPv4 endpoint/family/inode, fail closed for ambiguity. |
| P2 | #359 / C64.3 | Untrusted `preflight_result` such as a list can raise `TypeError` rather than the contractual bounded `Hold`. Add exact type checks and negative JSON-shape tests. |
| P3 | #359 / C64.3 | General `evaluate_inputs()` labels caller-provided dictionaries `SYNTHETIC_ONLY`; distinguish unverified caller input from a fixture-producing wrapper. |
| P3 | #359 / C64.3 | Contradictory listener metadata, e.g. zero listeners with a positive inode match, passes producer-consumer plausibility checks while decision remains HOLD. Add cross-field consistency tests. |

Codex also flagged **unconfirmed** risks for C64.2 process/PID races, executable resolution through inherited `PATH`, and future real HTTP total deadline/response-header policies. These were not reproduced as production exploits.

**Tomorrow — plan, not execution:** prepare narrowly scoped **new correction branches** and tests for #355, #358 and #359; compare fixes against the frozen commits and re-review in Codex before separate merge consideration. Do not silently edit frozen branches or couple #353. No production read from VictoriaMetrics, no model requests, no authorized remediation. Invariants remain `DEPLOYMENT_GATE=HOLD`, `MODEL_ACTION_AUTHORITY=NONE`, `REMEDIATION_AUTHORIZED=false`, `root_cause=UNDETERMINED`, `DNS_HEALTH=NOT_ESTABLISHED` **for the C64 lab outputs**; these labels do not describe the separately repaired production DNS incident.

## Day close

The live Unbound DNS-policy repair is **distinct** from DNS Guard's earlier Cron/Entware `dig` patch and from Issue #287 research. Codex audit findings were documented, but no C64 implementation change or merger was performed. This supplement is **documentation-only**, pending review and normal CI; it does not itself certify production readiness.
