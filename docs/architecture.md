# Architecture

![Advanced ASUS Edge Gateway architecture](images/Architecture.png)

## Logical components

| Layer | Component | Responsibility |
|---|---|---|
| Identity/policy | Tailscale Grants | User/group/device authorization and exit-node entitlement |
| Overlay | Tailscale | Encrypted connectivity, subnet advertisement, optional exit routing |
| Local enforcement | iptables | Router service, LAN destination, port, and WAN-interface policy |
| DNS | dnsmasq + Unbound | LAN listener, recursive resolution, DNSSEC validation, cache |
| Observability | syslog-ng | Local archive and optional TLS forwarding |
| Operations | Merlin hooks + scripts | Deterministic startup, health checks, backup, restore, update |

## Trust boundaries and flows

```mermaid
flowchart TD
    U["Remote identity + device"] -->|Tailnet policy| TS["Tailscale overlay"]
    TS -->|tailscale0| FW["EDGE_TS_INPUT / FORWARD"]
    FW -->|Admin device IP + port| MGMT["Router management"]
    FW -->|Host + port allowlist| LAN["Selected LAN service"]
    FW -->|Output interface = WAN| NET["Optional exit node"]
    FW -->|Default| DROP["Drop + rate-limited log"]
```

Tailscale is the first authorization boundary. The router firewall is a second, independent boundary. Router login and service authentication remain required after network access is granted.

## DNS flow

```mermaid
sequenceDiagram
    participant C as Remote client
    participant F as iptables REDIRECT
    participant D as dnsmasq :53
    participant U as Unbound :53535
    participant A as Authoritative DNS
    C->>F: UDP/TCP 53 (any destination)
    F->>D: REDIRECT to router-local :53
    D->>U: 127.0.0.1:53535
    U->>A: Iterative DNS query
    A-->>U: Signed response
    U-->>D: Validated answer
    D-->>C: DNS response
```

Classic UDP/TCP port 53 arriving on `tailscale0` is redirected to the router-local DNS listener. The firewall uses the netfilter `REDIRECT` target rather than DNAT to a configured LAN address, so DNS interception remains bound to the receiving router even if its LAN IPv4 address changes. Encrypted DNS does not use this flow and is not intercepted.

The supplied IPv6 chains fail closed for new Tailscale input and forwarded traffic when `ip6tables` is available. If `ip6tables` is unavailable, the current scripts warn and the deployment must independently verify that IPv6 is disabled; the repository does not claim fail-closed IPv6 enforcement in that state. IPv6 access requires a separate granular policy and live validation before those guards are relaxed.

## Boot sequence

```mermaid
flowchart TD
    B["Merlin services-start"] --> W["Wait for /opt with timeout"]
    W --> A["Let amtm/Entware startup settle"]
    A --> S["Require active swap when policy/platform needs it"]
    S --> T["Preserve or start/retry Tailscale"]
    T --> U["Preserve or recover Unbound"]
    U --> L["Preserve or start optional syslog-ng"]
    L --> F["Apply idempotent firewall"]
    F --> H["Health check available"]
```

The project does not blindly restart all Entware services at boot. On the reference deployment, amtm owns the normal Entware startup path; ASUS Edge waits for that startup to settle, preserves services that are already stable, and performs bounded recovery only when required. `EDGE_RUN_RC_UNSLUNG=1` is an explicit alternative for deployments where no external hook owns `rc.unslung`.

On low-memory 32-bit systems with strict kernel overcommit, the startup path waits for active swap before launching the Go-based Tailscale daemon. Failed daemon starts are retried and propagated as a required-service failure without preventing the fail-closed firewall from being applied. Unbound is likewise preserved when stable and recovered directly only when needed; dnsmasq is restarted after successful Unbound recovery so the resolver chain returns to a known state. syslog-ng is optional and its absence does not make required service startup fail.

The startup path uses installed package versions. Package and Tailscale updates remain separate planned-maintenance operations and are not performed automatically during boot.
