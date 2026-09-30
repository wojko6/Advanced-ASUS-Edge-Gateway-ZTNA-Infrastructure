# Personal Cloud browser access

Issue: #137

## Status

The browser-access baseline and the current RouterCloud v1 feature set are
live-validated for the reference ASUS/Fedora/Android deployment. Network
access, TLS, authentication, reboot persistence, source-scoped Tailscale
firewalling, split DNS, safe rename, Polish UI, storage-usage presentation and
the explicit no-WAN/root-containment negative checks are working.

Issue #137 remains open because destructive delete is still intentionally
disabled globally. The next change is a separate trusted-device delete policy,
followed by final regression/reboot validation and source-control of the exact
project-owned Dufs patch set/build recipe.

## Architecture

```text
LAN client
   |
   +---- HTTPS cloud.home.arpa ----+
                                   |
remote Tailscale client            |
   |                               |
   +-- split DNS home.arpa         |
   |      -> router LAN DNS         |
   |         via subnet route       |
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

The reference deployment started from Dufs 0.46.0 and now runs a small
project-owned patch set on top of that version. The current ARMv7 static-musl
production binary has SHA-256:

```text
5da9f0960aaf92d243da1dffbca5b42bfce1c86150b643507db8df5fa496be03
```

The patch set adds independently gated safe rename, Polish UI text, asset
cache-busting and lightweight storage-capacity reporting while retaining the
upstream 0.46.0 root/symlink containment baseline. The exact patched source and
reproducible ARM build recipe are not yet committed to this repository; that is
an explicit remaining reproducibility item before #137 closes.

The hardened configuration template is
[`config/dufs-personal-cloud.yaml.example`](../config/dufs-personal-cloud.yaml.example).

Important baseline settings:

- dedicated listener on the RouterCloud LAN alias rather than `0.0.0.0`;
- dedicated application authentication;
- TLS enabled;
- project-patched independent `allow-move: true`;
- global `allow-delete: false`;
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

Router-management HTTPS uses a separate Tailnet-facing ingress port and DNATs
to the actual local ASUS `httpds` listener on TCP/443. Keeping that ingress
port distinct from RouterCloud TCP/443 prevents the management DNAT from
intercepting RouterCloud traffic.

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
`home.arpa`, pointing at the router LAN DNS address reachable through the
advertised subnet route. This avoids sending unrelated DNS traffic through the
router while keeping the private RouterCloud name resolvable for authorized
remote clients.

The public repository does not record deployment-specific Tailscale addresses.

## TLS

The reference deployment uses a small private CA and a server certificate whose
SAN contains `cloud.home.arpa` and the dedicated RouterCloud LAN address.

Only the CA certificate is distributed to trusted clients. The CA private key
remains off-router and must not be copied into the repository. The Android
reference client was validated after importing only the public CA certificate:
the browser accepted `https://cloud.home.arpa/` without a certificate warning
and dedicated RouterCloud authentication succeeded.

## Validated behavior

The current reference validation has demonstrated:

- authenticated browser access over the home LAN from the Fedora workstation
  and the authorized Android/Poco client;
- upload, directory creation and download;
- safe same-directory rename without enabling global delete;
- overwrite refusal and cross-directory move refusal;
- Polish UI plus native filesystem-capacity reporting;
- browser asset cache-busting after the custom UI rebuild;
- delete denied while global `allow-delete: false`;
- explicit root/traversal/symlink-escape negative tests;
- remote HTTPS over a real mobile connection through Tailscale from both
  authorized device classes;
- source-scoped RouterCloud firewall rules for the authorized remote clients;
- normal `cloud.home.arpa` resolution remotely after split-DNS configuration;
- trusted Android TLS access after installing only the public RouterCloud CA
  certificate;
- automatic recovery after a real reboot and delayed `ROUTER_DATA` mount;
- explicit no-WAN validation: no wildcard RouterCloud listener, no WAN DNAT to
  the RouterCloud alias and a cellular test with Tailscale disabled could not
  reach the service.

Sanitized evidence is in
[`evidence/2026-09-30/issue-137-routercloud-browser-access-validation.md`](../evidence/2026-09-30/issue-137-routercloud-browser-access-validation.md).

## Remaining acceptance work

Do not close #137 yet.

Remaining items are:

1. implement trusted-device DELETE so the authenticated read/write user may
   delete only when the actual socket peer address belongs to the authorized
   Fedora or Android device set; keep global `allow-delete: false`;
2. keep root deletion forbidden and repeat unauthenticated, untrusted-source,
   traversal and symlink-escape negative tests for the new DELETE path;
3. commit the exact Dufs patch set/source delta and reproducible ARMv7 build
   recipe so the production binary can be independently rebuilt from the repo;
4. repeat the complete production/reboot acceptance after the delete-policy
   change, then reconcile the issue/PR and close #137.

The current safe-move patch deliberately separates rename from Dufs 0.46.0's
upstream delete coupling. It allows only the reviewed rename behavior and does
not make destructive DELETE generally available.


## Post-#137 RouterCloud evolution

The browser-access baseline is intended to remain maintainable after #137 rather
than becoming a frozen one-off Dufs binary. The preferred maintenance model is a
version-pinned upstream Dufs release plus a small project-owned patch set, with
rebase/update to newer upstream releases only after source review, automated
regression tests and ARMv7 live validation.

Planned candidates include:

- complete Polish UI and RouterCloud-specific branding;
- storage-capacity/free-space presentation;
- independently gated safe file operations;
- lightweight audit/event logging and integration with the existing external
  monitoring stack;
- more granular user/path authorization where it remains simple to audit;
- optional recycle-bin/recovery behavior coordinated with #138 versioned
  snapshots;
- additional lightweight file previews;
- optional entry point from the Edge Gateway portal (#84).

The router remains the limiting execution environment. Heavy indexing, OCR,
media transcoding, large databases or similar workloads should stay off-router.
Any future feature must preserve the dedicated RouterCloud root, symlink/root
containment protections, dedicated authentication, LAN/Tailscale-only exposure,
source-scoped firewall policy and the existing no-WAN boundary.
