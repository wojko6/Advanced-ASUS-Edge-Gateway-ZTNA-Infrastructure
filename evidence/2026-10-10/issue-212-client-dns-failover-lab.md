# Issue #212 — client DNS continuity engineering checkpoint (2026-10-10)

**Evidence class:** sanitized **operator-reported** off-router lab and router **read-only** observations, consolidated from [Issue #212](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212). These are not results independently rerun by GitHub Actions and **not** approval for production deployment.

## Scope and topology

- Deployed reference: ASUS TUF-AX5400, GNUton Merlin 388.11, Linux 4.1.52 ARMv7, iptables 1.4.15 and firmware dnsmasq 2.91.
- The current DHCP-advertised main-LAN DNS endpoint remains Pi-hole at `192.168.50.253`; Unbound remains the validating upstream on router loopback port `53535`. Firmware dnsmasq handles native/local naming and certain redirected classic DNS flows. DNS Guard v3.2 protects the **router system resolver**, not all DHCP/Tailscale clients.
- **No client DNS failover** or second standby resolver has been deployed.

## Bounded results

| Gate | Reported result | Evidence boundary |
|---|---|---|
| RC1–RC12 isolated tests | PASS within recorded tests | Fedora private kernel/netns, source-copy mocks, selected UDP/TCP, INPUT/FORWARD, DNAT and rollback; not ASUS firmware |
| RC11b routed FORWARD | PASS | Real routed UDP/TCP to separate synthetic Pi-hole-like namespace; no production pilot |
| RC12 local INPUT/conntrack | PASS | Direct high-port `55353` DNS access was denied in disposable private namespace while selected DNAT from original port 53 worked |
| RC13 firewall identity | READ-ONLY PASS | 339-byte managed entrypoint and 19,022-byte production target; pinned original target hash matched lab **baseline**, not lab changes |
| RC13 native-lifecycle review | FINDING | Firmware restart stops processes by `dnsmasq` name; observed two processes are a parent/child, not HA |
| RC13 private renamed dnsmasq | PASS | Disposable Fedora PID/NET test survived name-scoped kill and answered UDP/TCP; not proof on ASUS |
| RC13b SmartDNS 48.4 vs dnsmasq | PASS | Portable x86_64 synthetic DNS/PTR/private-name tests; RSS snapshot not ARMv7 estimate |
| RC13c signed DNSSEC fixture | PASS | dnspython/cryptography validated signed Ed25519 record and rejected forged A; **not** resolver validation |
| RC13c full dnsmasq/SmartDNS resolver test | **PENDING** | Test archive prepared and statically checked; operator did not execute end-to-end resolver gate |

## Additional observations and safety

The router `firewall-start` wrapper delegates to a 19,022-byte managed script with SHA-256 `5bca3badd1b083e8e886d0fc3b550a467b6cdd407e4c03b530668041e43c39c8`. The unmodified original matched the pinned source-copy baseline. Existing UDP conntrack flows can stay pinned after selector changes; no global conntrack flush is authorized.

The name-scope risk was identified by reading GNUton's tagged `stop_dnsmasq()` and `killall_tk()` implementation. No live firmware DNS restart was invoked to test it. An accidental x86_64 archive download attempt on the ARMv7 ASUS returned curl(23); a read-only follow-up reported no archive and no SmartDNS process. A portable x86_64 build is **not** a deployable ARMv7 artifact.

Operator milestones: `RC12_LOCAL_INPUT_LAB=PASS`, `RC13_PRIVATE_PROCESS_LIFECYCLE_LAB=PASS`, `RC13B_PRIVATE_DNS_PARITY_GATE=PASS`, `RC13C_CRYPTOGRAPHIC_FIXTURE_GATE=PASS`, `RC13C_FULL_RESOLVER_GATE=PENDING`. The documented experiments left host DNS/netfilter and production ASUS unchanged; no issue #212 implementation was committed.

## Open gates

Actual ASUS kernel original-port conntrack matcher semantics, stable ARMv7 resolver binary and privilege model, DNSSEC self-validation vs pass-through, real Merlin lifecycle and `killall_tk` behavior, private names, source-scoped ACL enforcement, startup/watchdog, reboot persistence, failback, monitoring and independently staged rollback. Only a separate explicitly approved **single-client pilot** may follow isolated/firmware-matched acceptance. Issue #212 remains **OPEN**.

**Sources:** [end-of-day technical checkpoint](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212#issuecomment-6101709148), [chronological worklog](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212#issuecomment-6101712179), [RC13c preparation](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212#issuecomment-6101536301).
