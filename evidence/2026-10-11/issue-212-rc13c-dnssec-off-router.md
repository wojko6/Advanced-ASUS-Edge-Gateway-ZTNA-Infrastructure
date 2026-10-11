# Issue #212 — off-router DNSSEC and ASUS ARMv7 parser evidence (2026-10-11)

**Evidence class:** operator-reported Fedora isolation and original firmware-binary parser observations. Public, sanitized summary only. No private lab packet captures, production logs, credentials, authenticated sessions, or raw router configuration are included.

## Preconditions and boundaries

- Reference router: ASUS TUF-AX5400 / GNUton Asuswrt-Merlin 388.11 / ARMv7. Production DNS Guard v3.2 is already separate and accepted for **router-system DNS**; this issue concerns *future* LAN/Tailnet-client continuity.
- The Fedora experiment used disposable private network/process conditions, synthetic signed DNSSEC zone and upstream, and no external default route.
- Signed RRset validity and tampered signed RRset rejection were checked with cryptographic fixtures before attributing resolver results.
- No live ASUS dnsmasq restart, firewall flush, NAT/DHCP edit or automatic client DNS failover occurred.

## Observed Fedora RC13c resolver gate

| Control | Verdict | Evidence boundary |
| --- | --- | --- |
| Signed Ed25519 synthetic fixture | PASS | Local cryptographic fixture |
| Altered RRset / unchanged signature | REJECTED — PASS | Does not alone test a resolver |
| Private isolated DNS upstream | PASS | No Internet DNS/default route required |
| Fedora dnsmasq UDP valid signed A | NOERROR, AD=TRUE — PASS | Fedora dnsmasq binary only |
| Fedora dnsmasq TCP valid signed A | NOERROR, AD=TRUE — PASS | Fedora dnsmasq binary only |
| Fedora dnsmasq UDP tampered signed A | SERVFAIL, no bogus A — PASS | Fedora dnsmasq binary only |
| Fedora dnsmasq TCP tampered signed A | SERVFAIL, no bogus A — PASS | Fedora dnsmasq binary only |
| SmartDNS **RC13c** DNSSEC runtime | NOT TESTED (binary unavailable in this run) | Earlier RC13b non-DNSSEC parity PASS is a different test |
| Native ASUS ARMv7 DNSSEC runtime | NOT TESTED | Parser result below does not imply it |
| Asuswrt-Merlin production | UNTOUCHED | No deployed client failover |

RC13c full **isolated Fedora dnsmasq** resolver gate: **PASS**. This explicitly supersedes the **PENDING** status of the previous day's prepared-but-not-yet-run experiment without changing the earlier entry's historical correctness.

## ASUS ARMv7 original-binary parser checkpoint: RC13X.24f

Operator reported: original archived DNS binary and lab test script integrity check PASS, synthetic crypto fixture PASS, tampered RRset rejected by fixture validation, locally generated anchor PASS, router-account config PASS.

Exact parser observation:

```text
dnsmasq: syntax check OK
```

Exit status: `0`; `RC13X.24f` parser acceptance: **PASS**; **`DNS_SERVER_STARTED=NO`**. This establishes accepted test-config syntax for that archived original binary in the stated off-router execution path. It is **not** a native runtime DNSSEC cryptographic acceptance test.

Other reported incremental ARMv7/QEMU gates (RC13G/H/I/J, RC13X.22b/.23) have separately scoped operator logs; do not replace or aggregate those logs into a claim of full DNSSEC runtime or deployability.

## Required next evidence

1. Original ASUS ARMv7 resolver **runtime** under isolated QEMU (`RC13X.24g`): validate authentic and forged synthetic DNSSEC over UDP/TCP with explicit process/no-bogus-answer evidence.
2. Verify service supervision and firmware name-based `dnsmasq` shutdown semantics, privilege model, no-DHCP and port ownership, JFFS2/recovery durability and rollback.
3. Source-scoped LAN/Tailnet INPUT/FORWARD/NAT reapply and rollback; account for conntrack-pinned existing sessions; prohibit unauthorized clients and private-name DNS leaks.
4. Obtain explicit authorization before any bounded live single-client pilot; preserve current Pi-hole/Unbound filtering and router-system DNS Guard v3.2.

**Conclusion:** OFF-ROUTER TESTS ONLY. `#212` remains **OPEN**; **no automatic client DNS failover deployed**.

Related: [#212](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212), [previous day's lab record](../2026-10-10/issue-212-client-dns-failover-lab.md), [2026-10-11 worklog](../../docs/worklog/2026-10-11.md).
