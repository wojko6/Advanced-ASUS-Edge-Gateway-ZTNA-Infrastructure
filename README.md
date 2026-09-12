# Advanced ASUS Edge Gateway & Zero-Trust Lab

[![Validation suite](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/actions/workflows/shellcheck.yml/badge.svg)](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/actions/workflows/shellcheck.yml)

A reproducible Home/SMB security-edge lab for the ASUS TUF-AX5400. It combines Asuswrt-Merlin, Entware, Tailscale, Unbound, syslog-ng, and a least-privilege firewall policy.

This is an **enterprise-style lab**, not an enterprise-grade appliance. It has no high availability, redundant WAN, native VLAN microsegmentation, or vendor support.

## Portfolio highlights

- Built a consumer-router security edge with Tailscale identity, project-owned default-deny firewall chains, and explicit router/LAN allowlists.
- Integrated dnsmasq with local Unbound on loopback:53535 and validated DNSSEC with the AD flag after controlled reboots.
- Added install, backup, restore, uninstall, health-check, evidence-collection, WAN-event recovery, and rollback workflows.
- Migrated the persistent Entware environment from USB flash storage to SSD, restored swap-backed service startup, and directly validated SSD mounts, swap activation, Tailscale, Unbound, and resolver configuration after the controlled reboot.
- Captured sanitized live evidence instead of presenting expected behavior as observed results.

## Architecture

![Current ASUS Edge Gateway architecture](docs/images/Architecture.png)

Remote access is enforced at two layers:

1. Tailscale Grants authorize identities and groups.
2. Managed iptables chains restrict router services, LAN destinations, ports, and optional exit-node forwarding.

See [architecture](docs/architecture.md), [firewall policy](docs/firewall-policy.md), and [security limitations](docs/security.md) for the detailed design.

## Key controls

- Default-deny `INPUT` and `FORWARD` policy for traffic arriving on `tailscale0`.
- Idempotent project-owned chains with duplicate jump removal.
- Device allowlist for router management and host/port allowlists for LAN access.
- Fail-closed IPv6 guards until an equivalent granular IPv6 policy is implemented.
- Classic DNS interception on TCP/UDP 53 through dnsmasq and Unbound.
- Bounded `/opt` readiness check and startup lock; no package upgrades during boot.
- Backup, dry-run restore, health checks, mock firewall tests, live tests, and CI.
- Sanitized evidence collection with explicit separation of automated and live results.
- Optional mutually authenticated TLS log forwarding with syslog-ng and reliable disk buffering.
- Automated collector retention that compresses completed logs after 24 hours and expires them after 30 days.

## Repository layout

```text
config/             Example runtime configuration and Tailscale policy
router/scripts/     Asuswrt-Merlin firewall-start and services-start hooks
scripts/            Install, update, health-check, backup, restore, uninstall
tests/              Static, mock-firewall, and live-client tests
docs/               Architecture, security, operations, testing, and roadmap
evidence/           Live-validation procedure and report template
```

## Requirements

- ASUS router supported by Asuswrt-Merlin; reference device: TUF-AX5400.
- JFFS custom scripts enabled.
- Entware mounted at `/opt`.
- Tailscale and Unbound installed; syslog-ng is optional.
- A SHA-256 utility for verified backups; install Entware package `coreutils-sha256sum` when the firmware does not provide one.
- A current router/JFFS backup and local recovery access for first deployment.

Entware package names can differ by target. Confirm them before installation:

```sh
opkg update
opkg list | grep -E '^(tailscale|unbound|syslog-ng|coreutils-sha256sum) '
```

Never commit auth keys, node state, private keys, collector credentials, router exports, or real private infrastructure data.

## Quick start

> **Reference-router stability gate:** the commands in this section describe a normal deployment or planned maintenance workflow. They are **not** instructions to re-run installation, firewall apply, resolver restart, package discovery/update, or an intentional reboot on the currently observed reference router during the unchanged-state window ending **2026-09-25**. During that gate, keep router-side checks read-only unless recovery from an active fault or security incident requires intervention. See [Current stability gate](#current-stability-gate) and [Operations and recovery](docs/operations.md).

Prepare and validate the configuration on a Linux workstation working copy
with Python 3 available for the regression tests (not required on the router):

```sh
cp config/edge.conf.example config/edge.conf
vi config/edge.conf
chmod +x scripts/*.sh router/scripts/* tests/*.sh tests/mocks/*
sh tests/test-static.sh
```

Copy the repository to the router. Keep a LAN session open, then stage the integration without applying the firewall:

```sh
./scripts/install.sh
```

Authenticate the installed Tailscale instance once, using the socket configured in `config/edge.conf`:

```sh
tailscale --socket=/var/run/tailscale/tailscaled.sock up \
  --netfilter-mode=off \
  --accept-dns=false \
  --advertise-routes=192.168.50.0/24 \
  --advertise-exit-node
```

If exit-node mode is disabled in `config/edge.conf`, omit `--advertise-exit-node`. Approve only the required route or exit node in the Tailscale admin console and adapt `config/tailscale/policy.example.hujson` before publishing it.

ASUS Edge intentionally runs Tailscale with `netfilter-mode=off`. The project-owned
`EDGE_TS_*` chains enforce the router firewall policy instead of Tailscale-managed
`ts-input`, `ts-forward`, and `ts-postrouting` chains. Do not change this mode
without redesigning and revalidating the firewall policy.

Apply and validate from the LAN during a planned deployment or maintenance window:

```sh
./scripts/install.sh --apply
/jffs/addons/asus-edge/bin/healthcheck.sh
```

The installer backs up existing Merlin hooks but does not execute unreviewed legacy hooks by default. Set `EDGE_RUN_LEGACY_HOOKS="1"` only after confirming that the preserved scripts do not broaden access, upgrade packages during boot, or duplicate service startup. The installer does not install packages or update Tailscale.

## DNS integration

dnsmasq continues to own port 53 for LAN and `tailscale0`. Unbound listens on `127.0.0.1:53535`, and dnsmasq forwards queries to it. When Tailscale DNS interception is enabled, the active dnsmasq configuration must include `interface=tailscale0`.

For a standard Entware deployment:

```sh
cp config/unbound.conf.example /opt/etc/unbound/unbound.conf
unbound-checkconf /opt/etc/unbound/unbound.conf
```

For amtm Unbound Manager, do not overwrite its generated runtime file. Validate the manager-owned configuration instead. The restart command below is a maintenance action and should not be run on the reference router during the active unchanged-state observation:

```sh
grep -E '^(port: 53535|interface: 127\.0\.0\.1@53535)' /opt/var/lib/unbound/unbound.conf
unbound-checkconf /opt/var/lib/unbound/unbound.conf
/opt/etc/init.d/S61unbound restart
```

Merge `config/dnsmasq.conf.add.example` with any existing `/jffs/configs/dnsmasq.conf.add`; do not overwrite private DDNS or local records. Review `/jffs/scripts/dnsmasq.postconf` for NextDNS or other hooks that may take precedence. Do not run a second resolver on `192.168.50.1:53` while dnsmasq owns that socket.

## Centralized logging

The optional logging design tails the firmware-owned `/tmp/syslog.log`, forwards it through Tailscale using mutually authenticated TLS, and can buffer messages on disk during collector outages. The checked-in examples require trusted peer certificates. Live mTLS delivery, buffer recovery, and post-reboot collector delivery should be described as observed only when the corresponding dated evidence exists; the presence of the example configuration alone is not operational proof.

See [centralized logging with mTLS](docs/centralized-logging.md) for the trust model, safe rollout order, negative certificate test, buffer recovery test, reboot validation, and evidence boundaries.

## Live validation status

The reference environment has multiple dated evidence sets. The **2026-09-11 SSD-migration/reboot artifact** directly validates the storage and core-service subset listed below; other firewall, printer, logging, health-check, and remote-client observations belong to their own dated evidence and must not be inferred from that single artifact.

Directly supported by `evidence/2026-09-11/entware-ssd-migration-validation.txt`:

- both SSD partitions mounted automatically after the controlled reboot;
- active 512 MiB and 2 GiB swap files;
- `tailscaled` running, with the Tailscale status command successful and the router offering exit-node capability;
- `unbound` running;
- direct Unbound resolution on `127.0.0.1:53535` returning `NOERROR` with the DNSSEC `AD` flag;
- dnsmasq configured with `no-resolv` and `server=127.0.0.1#53535`.

The artifact does **not** by itself prove syslog-ng recovery, end-to-end mTLS delivery, firewall/printer results, every exit-node traffic path, or long-term stability. See the sanitized [validated router-state snapshot](evidence/ROUTER-STATE-2026-09-11.md) for the exact claim boundary.

Other dated repository evidence documents additional validation performed in the reference environment, including remote-client DNS behavior and earlier router/firewall checks. Keep those observations attached to their original dates and artifacts rather than folding them into the 2026-09-11 SSD evidence.

Remote-client testing over LTE/5G previously confirmed the functional DNS path:

`Android remote client -> Tailscale tunnel -> router dnsmasq/Diversion -> Unbound on loopback:53535 -> recursive DNS`

That validation confirmed Internet connectivity with Tailscale DNS enabled, DNS traffic through the tunnel, normal resolution of allowed domains, Diversion blocking of a test advertising/tracking domain, DNSSEC validation, and equivalent home-Wi-Fi behavior.

See the [2026-09-08 live validation report](evidence/2026-09-08/live-validation.md), the [SSD migration procedure](docs/ENTWARE-SSD-MIGRATION.md), and the sanitized [2026-09-11 reboot validation evidence](evidence/2026-09-11/entware-ssd-migration-validation.txt).

## Current stability gate

The reference router is in a 14-day unchanged-state observation window from **2026-09-11 through 2026-09-25**. During this gate, router configuration changes and intentional reboots are avoided unless recovery is required. Repository/documentation work and endpoint-only experiments may continue without changing the router.

The planned [endpoint filtering validation](docs/endpoint-filtering-validation.md) evaluates Zen on Windows/Chrome and, optionally, AdGuard for Windows while preserving the existing router DNS architecture. Results will only be promoted to evidence after real tests are completed.

## Validation and recovery

The commands below are operational examples. During the active stability gate, use only the read-only checks that are necessary for observation; defer install/uninstall/restore/firewall-apply actions and deliberate live-client policy tests to a maintenance window unless recovery is required.

Read-only router inspection during the gate can include:

```sh
/jffs/addons/asus-edge/bin/healthcheck.sh
iptables -nvL EDGE_TS_INPUT
iptables -nvL EDGE_TS_FORWARD
iptables -t nat -nvL EDGE_TS_PREROUTING
```

The repository regression suite remains safe to run on a workstation working copy:

```sh
sh tests/test-static.sh
```

The live-client script actively probes management and LAN policy from an authorized remote client. Run it after the stability gate or during a planned validation/maintenance window, not merely as a routine unchanged-state observation:

```sh
sh tests/test-live-client.sh 192.168.50.1 192.168.50.20
```

The second address is an optional LAN host on which SMB should be denied. See [testing](docs/testing.md) for the full security matrix and packet-capture procedure.

Collecting a new evidence snapshot executes the project's collector and should be treated as an explicit validation action. During the unchanged-state gate, prefer existing logs and read-only inspection unless a dated snapshot is intentionally part of the observation plan:

```sh
/jffs/addons/asus-edge/bin/collect-evidence.sh
```

The collector excludes identity/configuration data and redacts firewall addresses, but its output still requires manual review before publication. This repository does not present expected behavior as observed live results. See [evidence collection](docs/evidence-collection.md) and the [validation evidence directory](evidence/README.md).

Backup and rollback commands for planned maintenance or recovery:

```sh
./scripts/backup.sh /opt/backups/asus-edge
./scripts/restore.sh /opt/backups/asus-edge/BACKUP.tar.gz --dry-run
./scripts/uninstall.sh
```

Tailscale updates are a separate planned-maintenance action:

```sh
./scripts/update-tailscale.sh
```

## Documentation

- [Polski przewodnik wdrożenia](docs/deployment-pl.md)
- [Architecture](docs/architecture.md)
- [Firewall policy](docs/firewall-policy.md)
- [Security model and limitations](docs/security.md)
- [Threat model](docs/threat-model.md)
- [Testing strategy](docs/testing.md)
- [Evidence collection](docs/evidence-collection.md)
- [Endpoint filtering validation](docs/endpoint-filtering-validation.md)
- [Validated router-state snapshot](evidence/ROUTER-STATE-2026-09-11.md)
- [Centralized logging with mTLS](docs/centralized-logging.md)
- [Entware SSD migration](docs/ENTWARE-SSD-MIGRATION.md)
- [Printer hardening](docs/PRINTER-HARDENING.md)
- [uiDivStats high-load case study](docs/uidivstats-high-load-case-study.md)
- [Printer setup from LAN](docs/printer-setup-lan-pl.md)
- [Printer setup through Tailscale](docs/printer-setup-tailscale-pl.md)
- [Operations and recovery](docs/operations.md)
- [Roadmap](docs/roadmap.md)

## Validation evidence

Sanitized evidence is stored under `evidence/YYYY-MM-DD/`. Each artifact should state what was actually observed and omit credentials, node state, real private addresses, or unrelated user data. Automated CI/mock output and live-router evidence are separate evidence classes; one must not be presented as proof of the other.

Automated shell, configuration, mock-firewall, recovery, and evidence-redaction tests run in GitHub Actions. Live network claims require separate dated evidence.

## Design principles

1. **Least privilege**: identities are filtered by Tailscale policy, then device IPs and destination ports are filtered again on the router.
2. **Fail closed**: invalid policy input aborts deployment; IPv6 is blocked until equivalent granular policy exists.
3. **Reproducible**: configuration templates, tests, rollback paths, and evidence procedures live with the code.
4. **Observable**: logs, counters, health checks, and sanitized evidence make policy behavior inspectable.
5. **Recoverable**: backups, dry-run restore, installer rollback, and LAN recovery procedures are documented and tested.
6. **Honest scope**: expected, automated, and live-validated behavior are kept separate, and platform limitations are explicit.

## License

See [LICENSE](LICENSE).
