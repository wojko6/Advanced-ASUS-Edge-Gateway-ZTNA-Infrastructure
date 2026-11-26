# Tailscale 1.104.2 ARMv7 — controlled router deployment

Date: 2026-10-21

## Scope and provenance

Operator-provided terminal output from the reference ASUS TUF-AX5400 running GNUton, following an explicitly authorized Tailscale-only deployment initiated from Fedora over independent LAN SSH. This is a **bounded live acceptance**, not a full router reboot or externally witnessed exit-node throughput test.

The new `tailscale` and `tailscaled` binaries were locally built for Linux ARMv7 from pinned upstream Tailscale tag `v1.104.2` (commit `e26db7a5797683ec99ad1516c40b628c7f2dfd71`) with Go 1.27.3 and `CGO_ENABLED=0`. The Fedora/QEMU laboratory preceded the live deployment; passing emulator tests do not by themselves prove firmware compatibility.

## Laboratory evidence reported before deployment

- ARMv7 static ELF and executable-version checks: PASS.
- Isolated daemon start and local IPC: PASS.
- DNS resolver and forwarder tests: 14/14 PASS.
- WireGuard engine logic/network reconfiguration tests: 7/7 PASS.
- Two synthetic peers, including bidirectional packets and configuration/metric checks: five subtests PASS.
- Simulated direct, firewall, and two-NAT discovery scenarios: 3/3 PASS; three successive test-count runs yielded 9/9 scenario passes.
- Scoped memory test with 512 MiB cgroup limit: 9/9 simulated NAT scenarios PASS; zero OOM kills.
- Scoped real ARMv7 `tailscaled` under QEMU with 128 MiB cgroup limit: 10/10 IPC requests PASS; peak `memory.peak` 63,537,152 bytes (~60.6 MiB); zero OOM kills. These are host emulator/cgroup readings, **not** native router daemon RSS or long-term stability guarantees.

## Live deployment (operator-reported)

| Check | Observed |
| --- | --- |
| Deployment | `DEPLOYMENT=PASS` |
| Previous live version | `1.103.375` (unstable/dev) |
| Installed live version | `1.104.2` |
| Staging verification | `STAGED_BINARIES=PASS` |
| Binary replacement | `BINARIES_REPLACED=YES` |
| Tailscale running and connected | PASS |
| `tailscale0` | Present |
| Automatic Tailscale update application | Disabled |
| Native Tailscale netfilter management | Disabled; no competing `ts-*` chains |
| Exit-node prerequisites | IPv4 forwarding, platform WAN NAT, project forwarding and return path PASS; observed WAN interface `ppp0` |
| DNS and policy integration | DNS Guard local resolver/break-glass inactive, Pi-hole source-scoped DNS, Unbound DNSSEC, managed firewall and RouterCloud access policy PASS |
| Other runtime dependencies | Required swap and syslog-ng PASS |
| Project healthcheck | **0 failures, 0 warnings** |
| Entware package metadata | `OPKG_METADATA_CHANGED=NO` |
| Identity/state file replacement | `IDENTITY_STATE_REPLACED=NO` |
| Installation gate | `DEPLOYMENT_GATE=LIVE_VALIDATED` |

Running daemon SHA-256 reported post-deployment:

```text
5ab9a22ccf8422fe92e9994427023a02420e2508c4b575eab91efb96ae811ecb
```

A dated rollback snapshot was retained in router-private storage. Its exact deployment-local path is intentionally omitted from this public report; the original operational recovery record remains outside the repository.

A project-owned controlled service restart and post-deployment healthcheck succeeded. The update did **not** run `opkg upgrade` and did not intentionally replace the existing Tailscale identity/state file. Do not infer that the prior version's package metadata tracks the live custom binaries.

## Boundaries and follow-up

- **Not performed:** full ASUS reboot with Tailscale 1.104.2, external/mobile client exit-node dataplane test, extended native-device soak test, production rollback rehearsal or blank-device recovery.
- The healthcheck confirms configured forwarding/NAT and service availability; it is not packet-level confirmation of every client route or application.
- This deployment is separate from Issue #235/PR #245 PrivDrop/SSD/Dufs work. `DEPLOYMENT_GATE=HOLD` remains unchanged **for those independent projects**; `LIVE_VALIDATED` applies only to this Tailscale update.
- Recheck Tailscale startup and the project healthcheck at the next planned router reboot; no extra reboot is claimed here.
