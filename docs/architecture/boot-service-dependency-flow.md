# Boot and Service Dependency Flow

## Purpose

This diagram distinguishes the **current reference router's validated live boot ordering** from the repository-managed services-start recovery logic. That distinction matters because the pre-Entware swap ordering correction recorded by #66 currently lives in the reference router's /jffs/scripts/post-mount rather than in a repository-managed post-mount hook.

```mermaid
flowchart TD
    B["Filesystem / Entware volume mounted"] --> PM["Reference /jffs/scripts/post-mount<br/>LIVE REFERENCE CONFIG"]
    PM --> PS["Activate mounted myswap.swp<br/>before AMTM Entware startup<br/>VALIDATED #66"]
    PS --> AM["AMTM mount-entware.mod"]
    AM --> RC["rc.unslung start"]
    RC --> S1["S01 syslog-ng"]
    S1 --> S6["S06 tailscaled"]
    S6 --> S61["S61 Unbound"]
    S61 --> DM["dnsmasq restart / resolver integration"]
    DM --> S90["Later Entware startup work<br/>including S90taildns where installed"]

    MS["Merlin services-start"] --> LK["Acquire services-start lock"]
    LK --> OP["Wait for /opt readiness<br/>bounded timeout"]
    OP --> AS["If AMTM ownership detected:<br/>wait for Entware startup to settle"]
    AS --> TS["Preserve stable tailscaled<br/>or recover with bounded retries"]
    TS --> SW["Before project Tailscale recovery:<br/>require active swap when policy/platform requires it"]
    SW --> UP["tailscale up<br/>netfilter-mode=off<br/>apply advertised routes / exit-node policy"]
    UP --> UB["Preserve stable Unbound<br/>or validate config and recover directly"]
    UB -->|"only after direct Unbound recovery"| RD["restart dnsmasq"]
    UB --> SL["Preserve/start optional syslog-ng"]
    RD --> SL
    SL --> FW["Run /jffs/scripts/firewall-start"]
    FW --> OK["services startup completed"]
    OK --> HC["healthcheck.sh available<br/>manual / validation step<br/>not auto-run by services-start"]

    WE["WAN connected event"] --> WH["wan-event-handler"]
    WH --> WD["Wait for dnsmasq + Unbound<br/>127.0.0.1:53535"]
    WD --> SR["Enforce /tmp/resolv.conf<br/>nameserver 127.0.0.1"]
    SR --> RT["Restart S06tailscaled"]
    RT --> TR["Wait for Tailscale status ready"]
```

## Validated scope and limitations

- The 2026-09-27 #66 evidence found that the original reference post-mount order could start Entware services before its AMTM-added swapon line was reached.
- The reference router was corrected so the mounted volume's swap is activated **before** sourcing AMTM mount-entware.mod. Three fresh clean cycles then passed with no recurring dnsmasq ENOMEM event.
- This pre-Entware post-mount correction is **validated live reference configuration**, but it is not presently installed or owned by the repository's services-start script. If AMTM rewrites post-mount, this ownership boundary must be rechecked.
- services-start waits for /opt, detects AMTM ownership, lets the external Entware startup settle, and preserves already-stable services where possible.
- The repository's own swap guard is specifically before Tailscale recovery on platforms/policies that require swap; it does not replace the live reference pre-Entware post-mount ordering correction.
- Unbound is preserved if stable. Direct recovery validates the configuration and restarts dnsmasq only after a successful recovery.
- syslog-ng is optional in services-start.
- firewall-start is required. Required service/firewall failures cause services-start to exit non-zero.
- healthcheck.sh is an explicit validation tool; services-start does not automatically invoke it.
- wan-event-handler is a separate WAN-connected recovery path. It waits for the local DNS path, points the system resolver at 127.0.0.1, restarts the Entware Tailscale service and waits for the local Tailscale API to become ready.

## Traceability

- [router/scripts/services-start](../../router/scripts/services-start)
- [router/scripts/wan-event-handler](../../router/scripts/wan-event-handler)
- [router/scripts/firewall-start](../../router/scripts/firewall-start)
- [config/edge.conf.example](../../config/edge.conf.example)
- [Clean startup and persistence evidence — 2026-09-27](../../evidence/2026-09-27/issue-66-clean-startup-persistence-evidence.md)
