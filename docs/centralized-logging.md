# Centralized logging with mutual TLS

This design forwards the Asuswrt local log to a Linux collector over Tailscale and mutually authenticated TLS (mTLS). The router authenticates the collector certificate, the collector authenticates the router certificate, and a reliable disk buffer preserves messages while the collector is unavailable.

> **Reference-router status:** the unchanged-state observation was closed on **2026-09-22**. The rollout, restart, outage and reboot procedures below are maintenance/validation procedures and should be executed only with backup, rollback and post-change verification. A repository configuration example or CI result is not evidence of live end-to-end logging on the reference router.

## Data path

```text
Asuswrt syslogd -> /tmp/syslog.log -> router syslog-ng
    -> Tailscale -> TLS 6514 -> collector syslog-ng
    -> /var/log/asus-edge/<router>/<date>.log
```

The router configuration deliberately tails `/tmp/syslog.log`. Do not enable the syslog-ng `system()` source on Asuswrt: the firmware already owns `/dev/log` and `/proc/kmsg`.

## Trust model

| Control | Router | Collector |
| --- | --- | --- |
| Network isolation | Sends through Tailscale | Listens only on its Tailscale address |
| Peer authentication | Validates the collector certificate | Validates the router client certificate |
| TLS policy | `peer-verify(required-trusted)` | `peer-verify(required-trusted)` |
| Private key | Client key, mode `0600` | Collector key, mode `0600` |
| Message durability | Reliable disk buffer | Date-partitioned files, mode `0640` |

Use a dedicated internal CA. Keep its private key off the router and never commit any key, issued certificate, CSR, Tailscale address, or production configuration to this repository.

## Example files

- Router: `config/syslog-ng.conf.example`
- Linux collector drop-in: `config/syslog-ng-collector.conf.example`

The examples use `example.invalid` and RFC 5737 documentation addresses. Replace them locally. Ensure the collector certificate SAN matches the collector Tailscale DNS name or IP, and issue the router certificate with `extendedKeyUsage=clientAuth`.

Recommended permissions:

```sh
chmod 700 /opt/etc/syslog-ng/tls
chmod 600 /opt/etc/syslog-ng/tls/router-client.key
chmod 644 /opt/etc/syslog-ng/tls/router-client.crt

chmod 700 /etc/syslog-ng/tls
chmod 600 /etc/syslog-ng/tls/collector.key
chmod 644 /etc/syslog-ng/tls/collector.crt
```

## Safe rollout order

Use this sequence in a planned maintenance window, not during an active unchanged-state observation:

1. Back up both syslog-ng configurations.
2. Install the dedicated CA certificate plus the collector certificate/key and router client certificate/key before enabling the TLS listener or sender.
3. Configure the collector with `key-file()`, `cert-file()`, `ca-file()`, and `peer-verify(required-trusted)` from the first network-facing test.
4. Validate the collector configuration and confirm that its certificate SAN matches the Tailscale DNS name or IP used by the router.
5. Configure the router destination with `key-file()`, `cert-file()`, `ca-file()`, and `peer-verify(required-trusted)`.
6. Validate and restart the collector, then validate and restart the router sender.
7. Test both negative and positive mTLS cases: an unauthenticated client must fail, while the issued router client certificate must succeed.
8. Remove temporary private-key copies.

Do not weaken peer verification as a normal rollout step. If certificate troubleshooting requires isolating a trust-chain problem, do it offline or in a disposable/non-reference environment rather than exposing the production collector with `optional-untrusted`. The checked-in examples intentionally use `required-trusted` on both peers.

## Validation

Configuration syntax checks are read-only, but a router-side restart is a maintenance action. On the current post-observation reference state, validate syntax first and perform sender restarts or trust-policy changes only in a planned maintenance window with rollback.

Validate configuration before every planned restart:

```sh
# Router
LD_LIBRARY_PATH=/opt/lib:/opt/usr/lib \
  /opt/sbin/syslog-ng -s -f /opt/etc/syslog-ng.conf

# Collector
sudo syslog-ng -s
```

A TLS client without a certificate must fail when validating the deployed mTLS policy:

```sh
sudo timeout 5 openssl s_client \
  -tls1_2 \
  -connect COLLECTOR_TAILSCALE_IP:6514 \
  -CAfile /etc/syslog-ng/tls/asus-edge-ca.crt \
  -verify_ip COLLECTOR_TAILSCALE_IP \
  -brief </dev/null
```

The same command with the issued client certificate must succeed:

```sh
sudo timeout 5 openssl s_client \
  -tls1_2 \
  -connect COLLECTOR_TAILSCALE_IP:6514 \
  -CAfile /etc/syslog-ng/tls/asus-edge-ca.crt \
  -verify_ip COLLECTOR_TAILSCALE_IP \
  -cert /path/to/router-client.crt \
  -key /path/to/router-client.key \
  -brief </dev/null
```

Generate a unique router message and verify it on the collector during an appropriate validation window:

```sh
logger -t asus-edge-test "MTLS_END_TO_END_OK"
grep -R "MTLS_END_TO_END_OK" /var/log/asus-edge
```

## Failure and persistence tests

These are controlled fault-injection tests. Run them only in a planned validation window, or on a disposable/non-reference environment.

To validate the disk buffer:

1. Stop syslog-ng on the collector.
2. Generate several unique messages on the router.
3. Wait long enough for the sender to observe the failure.
4. Start the collector.
5. Verify that every buffered message arrives.

A reboot test is also a planned maintenance test. When a reboot is intentionally scheduled, verify all of the following:

- `syslog-ng` is running;
- the TLS connection to port 6514 is established;
- the project health check returns the expected result for the deployed optional-logging policy;
- a post-reboot test message reaches the collector.

The project health check treats syslog-ng as optional unless remote logging is configured; do not describe an absent optional sender as a router-wide health failure.

## Collector retention

The collector example writes one file per router and calendar day. Use the supplied retention script and systemd timer to prevent unbounded storage growth:

- the current day's log is never compressed;
- completed logs older than 24 hours are compressed with gzip;
- compressed logs older than 30 days are removed;
- the script defaults to `--dry-run`;
- the service has a fixed writable path and a read-only system view.

Install and inspect the policy on the Linux collector:

```sh
sudo install -m 0750 scripts/asus-edge-log-retention.sh \
  /usr/local/sbin/asus-edge-log-retention
sudo install -m 0644 config/systemd/asus-edge-log-retention.service \
  config/systemd/asus-edge-log-retention.timer \
  /etc/systemd/system/

sudo systemd-analyze verify \
  /etc/systemd/system/asus-edge-log-retention.service \
  /etc/systemd/system/asus-edge-log-retention.timer
sudo /usr/local/sbin/asus-edge-log-retention --dry-run
```

Review every listed path before enabling deletion. Then enable the daily timer:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now asus-edge-log-retention.timer
systemctl list-timers asus-edge-log-retention.timer
```

The defaults provide at least 30 days of retained logs. Override `ASUS_EDGE_LOG_ROOT`, `ASUS_EDGE_COMPRESS_AFTER_MINUTES`, or `ASUS_EDGE_DELETE_AFTER_MINUTES` only for controlled testing or a deliberately different local policy. The script rejects relative roots and the filesystem root.

Collector-only maintenance does not modify the router, but intentionally stopping the collector can still change the behavior being observed by exercising the router's reliable buffer. During any future declared unchanged-state observation, avoid deliberate collector outages if the goal is to preserve an unchanged end-to-end logging state.

## Operational boundaries

mTLS authenticates the sending router but does not replace Tailscale policy. Restrict port 6514 to the intended router identity in Tailscale Grants or ACLs. Retain the source-address filter as defense in depth.

The reliable buffer protects short outages, not unlimited collector downtime. Monitor storage under `/opt/var/lib/syslog-ng`, define a collector retention policy, and test recovery after configuration or package upgrades during planned maintenance.

The example configuration demonstrates the intended architecture; successful end-to-end mTLS, buffering and post-reboot delivery must be claimed as **observed** only when dated evidence from the deployed environment exists. Configuration presence or CI syntax validation alone is not live operational evidence.
