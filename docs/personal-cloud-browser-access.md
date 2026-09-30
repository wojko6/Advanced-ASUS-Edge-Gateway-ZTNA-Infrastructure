# Personal Cloud browser access

Issue: #137

## Status

The browser-access baseline is implemented and live-validated for the reference
ASUS/Fedora deployment. The network, TLS, authentication, reboot persistence,
source-scoped Tailscale firewall path and split-DNS path are working.

The issue remains open because rename, storage-usage presentation and the mobile
client acceptance still require separate validation.

## Architecture

```text
LAN client
   |
   +---- HTTPS cloud.home.arpa ----+
                                   |
remote Tailscale client            |
   |                               |
   +-- split DNS home.arpa         |
   |      -> router Tailscale DNS  |
   |                               |
   +-- subnet route 192.168.50/24  |
                                   v
                     192.168.50.254:443
                     Dufs 0.46.0
                            |
                            v
          /tmp/mnt/ROUTER_DATA/RouterCloud
```

The application does not share the router root filesystem. Its Dufs serve root
is the dedicated Personal Cloud directory.

## Selected implementation

The reference deployment uses Dufs 0.46.0. The ARMv7 static-musl binary is not
vendored in this repository. The reviewed release asset used during validation
had SHA-256:

```text
079f0b7ebfb50851a4c9f88c9b12e100322a1137eb57356d1e902f369618c9f6
```

The version was selected after review of the upstream symlink/root containment
fix present in 0.46.0.

The hardened configuration template is
[`config/dufs-personal-cloud.yaml.example`](../config/dufs-personal-cloud.yaml.example).

Important baseline settings:

- dedicated listener on the RouterCloud LAN alias rather than `0.0.0.0`;
- dedicated application authentication;
- TLS enabled;
- `allow-delete: false`;
- `allow-symlink: false`;
- application root fixed to the dedicated RouterCloud directory;
- no WAN listener or WAN forwarding rule is added.

Generate the deployed authentication hash locally and keep it out of Git. The
local CA private key, server private key and deployed authentication material
must never be committed.

## Router-local address and boot persistence

The reference deployment assigns a dedicated secondary IPv4 address to `br0`
through `S66routercloud-ip`. Dufs is managed by `S67routercloud` using
`daemonize`, a PID file and a listener check.

USB mount order is not deterministic. A live reboot exposed a race where Entware
started before the `ROUTER_DATA` filesystem was ready. The final design uses a
short initial wait and an idempotent post-mount retry. Once the data filesystem
appears, the helper starts the alias and Dufs service again.

Canonical source:

- `router/init.d/S66routercloud-ip`
- `router/init.d/S67routercloud`
- `router/scripts/routercloud-post-mount`

Backups of `S*` scripts must not remain executable inside
`/opt/etc/init.d`; `rc.unslung` would treat them as additional startup
scripts.

## Tailscale firewall boundary

RouterCloud access is intentionally separate from router-management HTTPS.

The project firewall accepts RouterCloud HTTPS only when all of the following
match:

- ingress through the existing Tailscale policy path;
- source in `EDGE_ROUTERCLOUD_TS_SOURCES`;
- destination exactly `EDGE_ROUTERCLOUD_IP`;
- TCP destination port `EDGE_ROUTERCLOUD_PORT`.

The rule is inserted before the final logged `DROP` in `EDGE_TS_INPUT`.
This does not enable router SSH or broaden the existing management allowlist.

Example deployment values belong only in the private router configuration:

```sh
EDGE_ROUTERCLOUD_TS_SOURCES="<authorized-tailnet-ip>/32"
EDGE_ROUTERCLOUD_IP="192.168.50.254"
EDGE_ROUTERCLOUD_PORT="443"
```

## DNS

The firmware dnsmasq remains the Tailscale classic-DNS interception target.

The reference local name is:

```text
cloud.home.arpa -> 192.168.50.254
```

The Tailscale control plane uses a restricted/split nameserver for
`home.arpa`, pointing at the router's Tailscale DNS listener. This avoids
sending unrelated DNS traffic through the router.

The public repository does not record deployment-specific Tailscale addresses.

## TLS

The reference deployment uses a small private CA and a server certificate whose
SAN contains `cloud.home.arpa` and the dedicated RouterCloud LAN address.

Only the CA certificate is distributed to trusted clients. The CA private key
remains off-router and must not be copied into the repository.

## Validated behavior

The current reference validation has demonstrated:

- authenticated browser access over the home LAN;
- upload and directory creation;
- download;
- delete denied while `allow-delete: false`;
- remote HTTPS over a real mobile hotspot through Tailscale;
- a source-scoped firewall counter increment on the accepted remote connection;
- normal `cloud.home.arpa` resolution remotely after split-DNS configuration;
- automatic recovery after a real reboot and delayed `ROUTER_DATA` mount.

Sanitized evidence is in
[`evidence/2026-09-30/issue-137-routercloud-browser-access-validation.md`](../evidence/2026-09-30/issue-137-routercloud-browser-access-validation.md).

## Remaining acceptance work

Do not close #137 yet.

Remaining items are:

1. validate a second/mobile authorized Tailscale client;
2. provide rename without casually enabling destructive delete semantics;
3. add a basic storage-usage presentation;
4. perform explicit negative path-containment tests against router-internal paths;
5. perform an explicit no-WAN-exposure validation;
6. finish the custom RouterCloud UI only after the security behavior is frozen.

Dufs 0.46.0 gates `MOVE` behind both upload and delete permission, so the
current safe profile intentionally leaves rename unavailable rather than
enabling delete merely to satisfy the UI.
