# Centralized logging with mutual TLS

This design forwards the Asuswrt local log to a Linux collector over Tailscale and mutually authenticated TLS (mTLS). The router authenticates the collector certificate, the collector authenticates the router certificate, and a reliable disk buffer preserves messages while the collector is unavailable.

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

1. Back up both syslog-ng configurations.
2. Configure the collector for TLS with `peer-verify(optional-untrusted)` only during initial transport validation.
3. Install the CA certificate plus client certificate and key on the router.
4. Add `key-file()`, `cert-file()`, `ca-file()`, and `peer-verify(required-trusted)` to the router destination.
5. Validate and restart the router sender.
6. Add the CA file and change the collector to `peer-verify(required-trusted)`.
7. Validate and restart the collector.
8. Remove temporary private-key copies.

Do not leave `optional-untrusted` enabled after rollout.

## Validation

Validate configuration before every restart:

```sh
# Router
LD_LIBRARY_PATH=/opt/lib:/opt/usr/lib \
  /opt/sbin/syslog-ng -s -f /opt/etc/syslog-ng.conf

# Collector
sudo syslog-ng -s
```

A TLS client without a certificate must fail:

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

Generate a unique router message and verify it on the collector:

```sh
logger -t asus-edge-test "MTLS_END_TO_END_OK"
grep -R "MTLS_END_TO_END_OK" /var/log/asus-edge
```

## Failure and persistence tests

To validate the disk buffer:

1. Stop syslog-ng on the collector.
2. Generate several unique messages on the router.
3. Wait long enough for the sender to observe the failure.
4. Start the collector.
5. Verify that every buffered message arrives.

Afterward, reboot the router and verify all of the following:

- `syslog-ng` is running;
- the TLS connection to port 6514 is established;
- the project health check returns zero failures and zero warnings;
- a post-reboot test message reaches the collector.

## Operational boundaries

mTLS authenticates the sending router but does not replace Tailscale policy. Restrict port 6514 to the intended router identity in Tailscale Grants or ACLs. Retain the source-address filter as defense in depth.

The reliable buffer protects short outages, not unlimited collector downtime. Monitor storage under `/opt/var/lib/syslog-ng`, define a collector retention policy, and test recovery after configuration or package upgrades.
