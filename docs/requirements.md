# Requirements and acceptance map

**Status:** CURRENT — reference deployment and planned validation

**Reviewed:** 2026-09-25

This map links the existing architecture and test procedures to the reference ASUS TUF-AX5400. The status applies only to the stated test date and path. It does not turn a roadmap proposal, a mock test, or an operator-reported observation into independently captured live evidence. For the latest deployment summary see [project status](../PROJECT-STATUS.md); for detailed test methods see [testing](testing.md).

## Roles and use cases

| Role | Intended use | Boundary |
| --- | --- | --- |
| Authorized admin device | Open the router HTTPS panel through Tailscale | Tailscale authorization, exact router firewall source rule and router login |
| Ordinary tailnet device | Use only approved destinations or exit-node access if entitled | No router management; grants and project firewall remain separate checks |
| LAN client | Resolve classic DNS through the router | Router dnsmasq and Unbound; direct DoT control applies to the documented IPv4 `br0` path |
| Router operator | Back up, verify, deploy, check health and recover configuration | Local/LAN access and private recovery copies remain necessary |

## Functional acceptance

| ID | Requirement and observable pass condition | Method / current evidence | Current limit |
| --- | --- | --- | --- |
| F-01 | Only configured admin Tailscale IPv4 sources can reach router HTTPS; from an authorized client the panel loads with its DNS-name certificate verified. | Exact input/DNAT rules plus authorized and unauthorized client probes per [security matrix](testing.md#router-and-remote-client-security-matrix). Fedora verified TLS and Android operator-reported login after the 2026-09-23 reboot are in the [worklog](worklog/2026-09-23.md); the separate unauthorized-client denial is captured in the [sanitized live evidence](../evidence/2026-09-23/unauthorized-tailnet-management-denial.md). | **Validated for the tested 2026-09-23 reference deployment:** the unauthorized client reached the router as a Tailscale peer but could not establish TCP/8443; five scoped NEW TCP/8443 packets were correlated with the temporary counter-only rule and then the production deny tail. Revalidate after admin-source, Tailscale-policy, firewall, or firmware changes. The phone-browser certificate verdict remains client-specific and was not recorded. |
| F-02 | Classic IPv4 UDP/TCP 53 entering on the specified LAN/Tailscale interfaces follows the router DNS path; DNSSEC validation works at Unbound. | Correlate client query, managed NAT counter/packet, dnsmasq, Unbound and WAN. [2026-09-22 LAN](../evidence/2026-09-22/lan-dns-enforcement-production-validation.md) and [tailnet](../evidence/2026-09-22/audit-03-dns-datapath-validation.md) tests support their tested paths; the [2026-09-25 checkpoint](../evidence/2026-09-25/router-live-checkpoint.md) reconfirmed current-firmware LAN UDP/TCP redirect deltas, Tailscale UDP/53 interception and resolver health. | The 2026-09-25 Tailscale check did not repeat the full packet-by-packet dnsmasq/Unbound correlation, so the deeper AUDIT-03 path proof remains tied to 2026-09-22. DoH/DoQ and other encrypted paths are outside this requirement. |
| F-03 | An entitled Tailscale client can use exit-node IPv4 routing only through the selected WAN path, with platform NAT and return handling present. | [2026-09-22 fixed-flow correlation](../evidence/2026-09-22/audit-02-exit-node-nat-validation.md) established the ownership model; the [2026-09-23 post-firmware revalidation](../evidence/2026-09-23/audit-02-post-firmware-exit-node-revalidation.md) repeated the controlled before/after-NAT packet correlation on GNUton `3004.388.11_1-gnuton1_tuf`. | **Validated for the tested current-firmware IPv4 path:** five fixed-ID ICMP requests/replies correlated on `tailscale0` and `ppp0`, with 5/5 client replies and clean final health. This does not prove every protocol/client; a separate second post-reboot Android public-IP comparison remains unrecorded. Revalidate after material firmware/firewall/routing changes. |
| F-04 | On a clean startup the required SSD mounts, swap and project services are available; WPS remains off and unnecessary USB-service listeners are closed. | [2026-09-23 reboot checkpoint](worklog/2026-09-23.md#same-day-router-reboot-and-persistence-check), project health and USB audit; the [2026-09-25 read-only checkpoint](../evidence/2026-09-25/router-live-checkpoint.md) reconfirmed mounts, swap, services and a clean health result later in normal operation. | The 2026-09-25 checkpoint was not documented as a controlled cold-start test. Multiple explicit cold-start cycles remain outstanding. |
| F-05 | A project backup passes its sidecar hash and internal manifest checks; restore dry-run accepts it; a controlled failure during restore attempts rollback. | [Backup/restore procedure](operations.md#backup), [restore behavior](operations.md#restore) and repository recovery tests. Private copied archives and dry-runs passed on 2026-09-23. | The project archive excludes Tailscale state and is not a firmware image; an end-to-end clean-router recovery drill is not recorded. |

## Nonfunctional acceptance and risks

| ID | Goal / decision criterion | Current state |
| --- | --- | --- |
| N-01 | Treat credentials, node state and raw router evidence as private; only publish minimized, reviewed extracts. | [Publication checklist](evidence-collection.md#publication-checklist) applies; the 2026-09-23 raw backup/evidence copies remain private. |
| N-02 | Keep recovery copies in a separate failure domain, encrypted and integrity checked; define retention, backup monitoring, then measure recovery time/data loss in a drill. | Manual private, verified off-router copies exist; automation, monitoring and measured RTO/RPO are [planned](roadmap.md). No target RTO/RPO is claimed. |
| N-03 | Accept Diversion Large only after five normal-use sessions across multiple days, three clean startups and the remaining [roadmap criteria](roadmap.md#diversion-large-normal-use-acceptance-criteria). | In observation; a successful 2026-09-23 reboot alone does not complete acceptance. |
| N-04 | Measure latency, loss, throughput and CPU/RAM before setting performance targets for this platform. | [Performance method](testing.md#performance-baseline) exists and the [GeForce NOW Ethernet/Wi-Fi case study](geforce-now-ethernet-vs-wifi6-case-study.md) provides bounded real-time workload measurements. A later 2026-09-25 wired normal-use observation remained stable for approximately one hour, but no universal throughput, latency or availability objective has been accepted for the platform. |

Future RouterCloud, Pi-hole, alerts and mobile telemetry are proposals in the [roadmap](roadmap.md); they require separate requirements, failure cases and acceptance evidence before being described as deployed capabilities.
