# Architecture

![Advanced ASUS Edge Gateway architecture](images/architecture-v2.png)

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
    participant F as iptables DNAT
    participant D as dnsmasq :53
    participant U as Unbound :53535
    participant A as Authoritative DNS
    C->>F: UDP/TCP 53 (any destination)
    F->>D: 192.168.50.1:53
    D->>U: 127.0.0.1:53535
    U->>A: Iterative DNS query
    A-->>U: Signed response
    U-->>D: Validated answer
    D-->>C: DNS response
```

Encrypted DNS does not use this flow and is not intercepted.

The supplied IPv6 chains fail closed for new Tailscale input and forwarded traffic. IPv6 access requires a separate granular policy and live validation before those guards are relaxed.

## Boot sequence

```mermaid
flowchart TD
    B["Merlin services-start"] --> W["Wait for /opt with timeout"]
    W --> E["Start Entware services"]
    E --> S["Wait for required swap"]
    S --> T["Start/retry Tailscale"]
    T --> F["Apply idempotent firewall"]
    F --> H["Health check available"]
```

On low-memory 32-bit systems with strict kernel overcommit, the startup path
waits for active swap before launching the Go-based Tailscale daemon. Failed
daemon starts are retried and propagated as a required-service failure without
preventing the fail-closed firewall from being applied. The startup path uses
the installed package version; updates remain a separate maintenance operation.
