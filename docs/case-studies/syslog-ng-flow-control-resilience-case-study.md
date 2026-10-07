# syslog-ng local archive resilience under collector outage

## Executive summary

A live centralized-logging incident on the ASUS TUF-AX5400 showed that a
security/reliability feature can create an undesirable failure dependency when
applied at the wrong scope.

The router used syslog-ng to tail Asuswrt's `/tmp/syslog.log`, write a local
archive, and forward the same messages over Tailscale + mTLS to a Fedora
collector. The original shared log path used hard `flags(flow-control)`.

After an extended collector-unavailability period, Asuswrt continued writing
new log entries but syslog-ng stopped advancing its source-file read position.
Because the local archive and remote TLS destination shared the same
flow-controlled path, local archival stopped as well.

The remediation removed hard flow-control from the fan-out path while retaining
the reliable disk buffer on the remote destination. Controlled fault injection
then proved that the local archive remained available while the collector was
unreachable and that the outage marker was delivered remotely after recovery.

## Architecture before remediation

```text
/tmp/syslog.log
      |
      v
  router syslog-ng
      |
      +--> local archive
      |
      +--> reliable disk buffer --> mTLS --> Fedora
      |
      +--> hard flow-control on shared path
```

This looked attractive because hard flow-control protects against dropping
messages when a destination cannot keep up. The operational problem was scope:
the local archive inherited the remote collector's backpressure.

## Investigation

### 1. Separate network state from source-consumption state

The Fedora listener was active on TCP/6514 and the router had demonstrated a
valid established mTLS session. Packet captures during the stalled period showed
connection maintenance but no new application payload after test markers were
generated.

That shifted the investigation away from firewall/Tailscale/certificate setup
and toward the router-side syslog-ng pipeline.

### 2. Prove that Asuswrt still writes the source

Unique `logger` markers appeared in `/tmp/syslog.log`, proving that the
firmware logging path remained alive.

The same markers did not appear in the router's syslog-ng local archive.

### 3. Rule out log rotation

The current `/tmp/syslog.log` path and the file descriptor held by syslog-ng
referenced the same inode. The stale-rotated-file hypothesis was therefore
rejected.

### 4. Inspect the reader position

The decisive observation was the file-descriptor position:

```text
syslog-ng source position: 65536 bytes
source file size:          >239 KiB and still growing
```

The position did not advance after another source marker was written. The
process was alive and holding the correct file, but source consumption was
stalled.

## Remediation

The live configuration was backed up and validated before activation. The
change was deliberately narrow:

- keep the local file destination;
- keep the mTLS remote destination;
- keep the reliable disk buffer for store-and-forward behavior;
- remove hard `flags(flow-control)` from the shared local+remote log path.

A restart released the existing stalled state. The new syslog-ng process
immediately caught up to the current end of `/tmp/syslog.log`.

## Validation

### Normal path

A unique post-change marker was observed in the source file, router local
archive, and Fedora collector. The TCP/6514 session remained established.

### Collector outage

A temporary collector-side firewall rule rejected only the router's TCP/6514
path. The router sender was restarted so the test did not rely on a previously
established connection.

With the collector unavailable:

- there was no established remote TCP session;
- the new marker appeared in `/tmp/syslog.log`;
- the marker appeared in the local archive;
- the syslog-ng source position caught up exactly to source-file size.

This is the behavior the original configuration failed to preserve.

### Recovery

After removing the temporary firewall rule, the remote TLS session
re-established and the marker generated during the outage appeared in the
Fedora collector archive.

That demonstrated both failure-domain isolation for the local archive and
store-and-forward recovery for the tested outage.

## Regression control

The repository static test now fails if the router syslog-ng example contains
hard `flags(flow-control)`. It also confirms that both the local and remote
destinations remain present.

This converts an operational incident into an explicit configuration invariant.

## Evidence boundaries

The investigation directly proves:

- source-file growth while the syslog-ng read position was stalled;
- matching active inode between the source path and open file descriptor;
- restored source consumption after restart;
- local archival while the collector was intentionally unavailable;
- remote delivery of the outage marker after recovery.

It does not directly prove the exact reliable-queue occupancy or a specific
queue-full threshold at the moment the original stall began. The root-cause
statement is therefore bounded to the demonstrated hard-flow-control coupling
and its observed remediation.

See [sanitized validation evidence](../../evidence/2026-10-01/syslog-ng-flow-control-resilience-validation.md).
