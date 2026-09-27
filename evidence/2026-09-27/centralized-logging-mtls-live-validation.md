# Centralized logging mTLS live validation — 2026-09-27

## Scope

Sanitized live validation of centralized logging from the reference
ASUS TUF-AX5400 to the Fedora monitoring host.

Deployment-specific Tailscale addresses, private hostnames, certificate bytes,
private keys and CA secrets are intentionally excluded.

## Components

```text
Router:  syslog-ng 4.10.2
Fedora:  syslog-ng 4.11.0
Transport: Tailscale + mutual TLS on TCP/6514
```

The router tails the Asuswrt-owned `/tmp/syslog.log` rather than attempting to
replace firmware ownership of `/dev/log` or `/proc/kmsg`.

## Router-side hardening

The pre-existing syslog-ng deployment was healthy and syntax-valid, but two
configuration directories had mode `0777`.

They were corrected without restarting syslog-ng:

```text
/opt/etc/syslog-ng       0777 -> 0755
/opt/etc/syslog-ng/ca.d  0777 -> 0755
/opt/etc/syslog-ng/tls   remained 0700
```

Sensitive file modes were already appropriate:

```text
router client private key: 0600
router client certificate: 0644
CA certificate:             0644
syslog-ng.conf:             0600
```

The active router configuration passed a syntax check before any PKI change.

## PKI rotation

The existing router certificate chained to an older internal CA, but the
private key for that CA was not available on the Fedora host or router.

A new dedicated logging CA was therefore generated with an encrypted private
key retained off-router and outside the repository.

Issued leaf certificates were purpose-limited:

```text
collector: Extended Key Usage = TLS Web Server Authentication
router:    Extended Key Usage = TLS Web Client Authentication
```

Both certificates included the corresponding Tailscale IPv4 address in SAN.
OpenSSL purpose and IP-SAN verification passed before deployment.

New router PKI files were first copied to a staging directory and tested
directly from the router against the Fedora collector. The handshake reported:

```text
Verification: OK
TLSv1.3
Verify return code: 0 (ok)
```

The new PKI was then installed side-by-side under new filenames. A candidate
`syslog-ng.conf.next` was generated, uploaded, syntax-checked successfully and
confirmed not to modify the active configuration before cutover.

## Fedora collector isolation

Fedora syslog-ng was configured to listen only on the host's Tailscale IPv4
address on TCP/6514.

Firewall policy was narrowed to:

```text
normal Fedora workstation zone: TCP/6514 closed
tailscale0 zone: target DROP
tailscale0 rich rule: router Tailscale /32 -> TCP/6514 accept
```

No wildcard `0.0.0.0:6514` local listener was present; the socket was bound to
the Tailscale address.

## Mutual-TLS negative and positive tests

Without a client certificate, the TLS handshake reached the collector
certificate successfully but was rejected with:

```text
tlsv13 alert certificate required
negative test return code: non-zero
```

With the issued router client certificate:

```text
Verification: OK
positive test return code: 0
```

This validates required client-certificate authentication for the tested
collector path.

## End-to-end message validation

After the staged router cutover, a unique test message was generated with
`logger`.

The same message was observed first in the router's `/tmp/syslog.log` and then
in the Fedora collector's date-partitioned file under:

```text
/var/log/asus-edge/router/
```

The Fedora collector service was active/enabled and had no matching recent
TLS/certificate/error entries.

**Result: PASS — live router -> Tailscale -> mTLS -> Fedora centralized logging
was observed end to end.**

## Short collector-outage recovery

Fedora syslog-ng was intentionally stopped. Three unique router messages were
then generated while the collector was unavailable.

After 15 seconds, the collector was started again. All three messages appeared
in the Fedora log:

```text
BUFFER_MESSAGES_FOUND=3/3
```

No matching collector errors remained after recovery.

This validates short-outage buffering/retry for the tested running router
process. It does not prove queue persistence through a router reboot or power
loss. The configured reliable disk-buffer directory is preallocated, so its
unchanged filesystem size during the test is not used as evidence of queue
depth.

## Remaining validation boundary

This artifact does not yet claim:

- logging-path persistence after a router reboot;
- persistence of queued messages across router power loss;
- long-duration collector outage capacity;
- centralized search/indexing beyond date-partitioned syslog files;
- alerting on log content.
