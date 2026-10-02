# Issue #137 — Personal Cloud browser-access validation

Date: 2026-09-30

## Scope

This evidence captures the validated network/access baseline for browser-based
Personal Cloud access. It is intentionally sanitized and does not publish
Tailscale node addresses, authentication hashes, passwords, private keys or CA
private material.

Issue #137 remains open only for the planned trusted-device DELETE policy,
final post-change regression/reboot acceptance and source-control of the exact
project-owned Dufs patch/build recipe. Safe rename, storage usage, explicit
negative-boundary checks, Android/Poco acceptance and no-WAN validation are
complete.

## Service boundary

Observed reference state:

```text
name:       cloud.home.arpa
LAN alias:  192.168.50.254/24 on br0:routercloud
transport:  HTTPS/TCP 443
serve root: /tmp/mnt/ROUTER_DATA/RouterCloud
service:    project-patched Dufs 0.46.0
rename:     independently enabled, same-directory only
delete:     globally disabled
symlinks:   disabled
```

The listener was bound to the dedicated RouterCloud alias rather than the
router-management address or a wildcard listener.

## Functional checks

Authenticated browser/API checks passed for:

```text
browse directory:             PASS
create directory:             PASS
upload:                       PASS
download:                     PASS
safe same-directory rename:   PASS
destination overwrite denied: PASS
cross-directory move denied:  PASS
delete denied globally:       PASS
storage usage display:        PASS
Polish UI / cache refresh:     PASS
```

The deployed project patch separates safe rename from upstream Dufs 0.46.0's
delete coupling. The production build keeps global destructive delete disabled.

## Reboot / mount-order recovery

A real reboot exposed a storage-order race. Entware became ready before the
`ROUTER_DATA` filesystem. The service correctly deferred, and the later data
volume post-mount event retried startup:

```text
routercloud: deferred: RouterCloud storage not ready; post-mount will retry
custom_script: post-mount (.../ROUTER_DATA)
routercloud-ip: RouterCloud address already present
routercloud: started
routercloud-post-mount: RouterCloud startup completed after mount event
```

Post-recovery checks reported both init components alive and the HTTPS listener
present on `192.168.50.254:443`.

An obsolete executable backup of the old `S67` script was found in
`/opt/etc/init.d`. It was moved to a non-executable backup directory so
`rc.unslung` no longer treats it as a second service.

## Tailscale firewall validation

Before the dedicated rule existed, remote HTTPS attempts reached the router on
`tailscale0` and were logged by the project fail-closed policy:

```text
IN=tailscale0 DST=192.168.50.254 PROTO=TCP DPT=443 ASUS-EDGE-DROP
```

The final policy uses a dedicated RouterCloud allowlist instead of reusing or
broadening router-management HTTPS.

After a full reboot, the persistent chain contained the source-scoped rule:

```text
ACCEPT tcp <authorized-fedora-ts-ip> -> 192.168.50.254 tcp dpt:443 ctstate NEW
LOG
DROP
```

A real remote test was then run with the Fedora workstation disconnected from
the home WLAN and attached to a mobile hotspot.

Observed client routing:

```text
192.168.50.254 dev tailscale0 table 52 src <fedora-ts-ip>
```

Observed HTTPS result:

```text
{"status":"OK"}
HTTP=200 IP=192.168.50.254
```

The RouterCloud firewall rule counter increased from zero to one packet for the
new connection. Router SSH remained outside this RouterCloud exception.

The Tailscale peer path used DERP during this test; direct peer-to-peer transport
was not required for functional acceptance.

## Split DNS

The remote client could initially reach RouterCloud only with an explicit
address override. DNS transport itself was healthy:

```text
router Tailscale DNS -> public name: NOERROR
cloud.home.arpa: NXDOMAIN
```

The local RouterCloud record was then added to firmware dnsmasq:

```text
host-record=cloud.home.arpa,192.168.50.254
```

A direct Tailscale DNS query subsequently returned:

```text
cloud.home.arpa. A 192.168.50.254
```

The initial remote Fedora acceptance used a restricted/split nameserver for
`home.arpa` pointing to the router Tailscale DNS listener. With Tailscale DNS
and subnet routes enabled on that Fedora client, normal system resolution and
browser access to:

```text
https://cloud.home.arpa/
```

worked over the mobile hotspot without `--resolve`.

During the later Android troubleshooting, the restricted `home.arpa`
nameserver was changed to the router LAN DNS address reachable through the
advertised subnet route. That final form was then validated from the Android
client over LTE/5G.

Deployment-specific Tailscale addresses are intentionally omitted.

## Android/Poco remote-client acceptance

A second authorized remote-client test was completed from the Android phone over
LTE/5G using the project development Tailscale client.

Troubleshooting showed that the development client and the previously installed
official Android client were separate tailnet nodes. The active development
client also required both Tailscale DNS and subnet routes to be enabled. Once
the active node identity was placed in the dedicated RouterCloud allowlist, the
phone resolved and opened:

```text
https://cloud.home.arpa/
```

over the mobile network.

After policy reload, the dedicated RouterCloud rule started at zero and then
recorded two new TCP connection packets from the authorized mobile node. The
stale allowlist entry for the removed official Android client was deleted.

The public RouterCloud CA certificate was installed in the Android trust store.
The browser then accepted the private TLS chain without a certificate warning,
and dedicated RouterCloud login succeeded.


## Boundary and no-WAN validation

Explicit negative tests were completed against the production-safe build.
Attempts involving the service root, parent traversal, encoded traversal and a
symlink destination outside the RouterCloud root were rejected, and outside
sentinel data remained unchanged. Root rename was also rejected.

The RouterCloud listener remained bound to the dedicated LAN alias on TCP/443;
no wildcard RouterCloud listener and no WAN DNAT/port-forward to that alias were
present. With Wi-Fi and Tailscale disabled, a real cellular client could not
reach the RouterCloud service. These checks support the bounded claim that the
validated configuration does not directly expose RouterCloud on the public WAN.

## Dual-client management-policy reconciliation

The authorized Android/Poco device was aligned with the Fedora administration
workstation for both normal-LAN and Tailscale management access. The live audit
found and removed a stale Android tailnet identity from the management policy.

The audit also found a management NAT inconsistency: the Tailnet-facing
management ingress port was being reused as the local ASUS WebUI target even
though the active `httpds` listener had moved to TCP/443. The corrected design
keeps the distinct Tailnet ingress port but DNATs to the actual
`192.168.50.1:443` listener. RouterCloud remains separately addressed on its
own alias TCP/443, so the two HTTPS services do not collide.

The live private configuration contained repeated consecutive entries from
earlier maintenance. It was backed up and deduplicated; deployment-specific
source addresses remain intentionally omitted here.

## Security claim boundary

This evidence supports the following claims only:

- RouterCloud HTTPS works on the LAN and through an authorized Tailscale source;
- the Tailscale allow is destination/port/source scoped and does not broaden
  router-management SSH/HTTPS;
- Dufs is rooted at the dedicated Personal Cloud directory, symlinks and
  global destructive delete are disabled, and safe rename is independently
  gated by the project patch;
- service startup survives the observed Entware/data-volume mount ordering;
- split DNS allows the same private hostname to work remotely;
- authorized Android/Poco access over LAN and LTE/5G is live-validated;
- the Android browser trusts the RouterCloud TLS chain after installation of
  the public CA certificate and dedicated login succeeds;
- safe rename, storage reporting, root/traversal/symlink negative checks and the
  tested no-WAN boundary are live-validated.

Not yet claimed:

- trusted-device destructive DELETE;
- reproducible rebuild from a repository-owned Dufs patch set/build recipe;
- direct Tailscale peer-to-peer transport.
