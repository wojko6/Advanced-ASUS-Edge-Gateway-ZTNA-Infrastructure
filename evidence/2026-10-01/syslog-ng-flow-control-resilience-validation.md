# syslog-ng local archive resilience validation — 2026-10-01

## Scope

This sanitized record documents a live failure investigation and controlled
fault-injection test for the router-to-Fedora centralized logging path.

Deployment-specific Tailscale addresses are intentionally omitted. No private
keys, certificates, raw packet captures, or unrelated router logs are included.

## Initial symptom

The router's firmware logger continued writing to `/tmp/syslog.log`, but new
test messages stopped appearing in the router's local syslog-ng archive and no
new application payload was observed toward the collector.

The router syslog-ng process itself remained running.

## Source-file diagnosis

The active source path and the file descriptor held by syslog-ng referenced the
same inode, ruling out the suspected stale-handle-after-rotation explanation.

Observed before remediation:

```text
source inode:       same for path and open FD
syslog-ng position: 65536
source size:        239215 bytes, then 239279 bytes, later >243 KiB
```

A unique source probe was written successfully by Asuswrt, the source file grew,
but the syslog-ng file-descriptor position remained fixed at 65,536 bytes and
the marker did not reach the local archive.

## Transport findings

Independent checks established that:

- the Fedora syslog-ng listener was bound only to the collector's Tailscale
  address on TCP/6514;
- the router and collector had previously established the TLS/TCP session;
- mTLS end-to-end delivery had already been validated;
- the stalled condition was therefore upstream of normal message transmission:
  syslog-ng was no longer consuming the source file.

Historical router logs showed an extended interval of collector connection
failures before reconnection. The original router configuration placed both the
local archive and remote TLS destination on one log path with
`flags(flow-control)`.

## Remediation

The live router configuration was backed up. Hard flow-control was removed from
the shared fan-out path while the remote TLS destination retained its reliable
disk buffer.

Configuration syntax validation returned success before restart.

After restarting syslog-ng, the new source file descriptor immediately caught
up to the current source-file size. A normal-path marker then appeared in:

1. `/tmp/syslog.log`;
2. the router local archive;
3. the Fedora collector archive.

## Controlled collector-outage test

A temporary firewall rule made only the router-to-collector TCP/6514 path
unavailable. The sender was restarted to ensure the old established session was
not reused.

During the outage:

```text
collector TCP session: absent
test marker:            written to /tmp/syslog.log
local archive:          marker present
source FD position:     251702
source file size:       251702
```

This directly demonstrated that collector unavailability no longer stopped
local source consumption or local archival.

After removing the temporary firewall rule:

- the TCP/6514 session returned to `ESTABLISHED`;
- the same outage marker appeared in the Fedora collector archive.

This validates store-and-forward recovery for the tested outage while
preserving local log availability.

## Root-cause assessment

The observed failure is consistent with hard syslog-ng flow-control coupling
the local archive's availability to backpressure from the remote collector.
Removing hard flow-control from the shared local+remote path eliminated that
coupling in the controlled fault test.

The exact internal reliable-queue occupancy at the original stall was not
measured. This record therefore does not claim that a specific queue-full
threshold was directly observed.

## Regression requirement

The public router example must retain both local and remote destinations but
must not contain hard `flags(flow-control)` on that fan-out path. Repository
static tests enforce this invariant.

## Result

**PASS** — normal delivery, local archival during collector outage, and delayed
remote delivery after recovery were all observed on 2026-10-01.
