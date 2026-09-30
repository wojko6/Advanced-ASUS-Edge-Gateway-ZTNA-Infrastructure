# Issue #137 — Personal Cloud browser-access validation

Date: 2026-09-30

## Scope

This evidence captures the validated network/access baseline for browser-based
Personal Cloud access. It is intentionally sanitized and does not publish
Tailscale node addresses, authentication hashes, passwords, private keys or CA
private material.

Issue #137 remains open because rename, storage usage and explicit
negative-boundary acceptance are not yet complete. Android/Poco remote-client
acceptance is complete.

## Service boundary

Observed reference state:

```text
name:       cloud.home.arpa
LAN alias:  192.168.50.254/24 on br0:routercloud
transport:  HTTPS/TCP 443
serve root: /tmp/mnt/ROUTER_DATA/RouterCloud
service:    Dufs 0.46.0
delete:     disabled
symlinks:   disabled
```

The listener was bound to the dedicated RouterCloud alias rather than the
router-management address or a wildcard listener.

## Functional checks

Authenticated browser/API checks passed for:

```text
browse directory: PASS
create directory: PASS
upload:           PASS
download:         PASS
delete denied:    PASS
```

Rename remains pending because Dufs 0.46.0 couples `MOVE` authorization to the
delete permission. The safe baseline kept delete disabled.

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

## Security claim boundary

This evidence supports the following claims only:

- RouterCloud HTTPS works on the LAN and through an authorized Tailscale source;
- the Tailscale allow is destination/port/source scoped and does not broaden
  router-management SSH/HTTPS;
- Dufs is rooted at the dedicated Personal Cloud directory and delete/symlink
  features are disabled in the current profile;
- service startup survives the observed Entware/data-volume mount ordering;
- split DNS allows the same private hostname to work remotely;
- authorized Android/Poco access over LTE/5G is live-validated;
- the Android browser trusts the RouterCloud TLS chain after installation of
  the public CA certificate and dedicated login succeeds.

Not yet claimed:

- completed rename support;
- completed storage-usage UI;
- explicit negative traversal tests against every router-internal path;
- explicit external-WAN negative scan;
- direct Tailscale peer-to-peer transport.
