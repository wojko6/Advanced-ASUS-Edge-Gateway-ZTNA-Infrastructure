# Post-Stability Gate Validation Plan

## Scope

This procedure is prepared for the first planned validation window after the reference router's unchanged-state observation completes on **2026-09-25**.

It is intentionally documentation-only until the stability gate is closed. Do not execute the live-router commands in this document during the active unchanged-state window unless recovery or a security incident requires intervention.

## Phase 0 — close the observation window

Record:

- final router uptime;
- RAM available and swap usage;
- SSD/Entware mounts and utilization;
- Tailscale process/control-plane state;
- Unbound process and DNSSEC validation;
- dnsmasq state and intended upstream;
- syslog-ng state;
- project health-check result;
- recent log review for OOM, crashes, unexpected restarts, WAN/DNS recovery failures, storage/mount errors;
- any router-side intervention during the window.

Acceptance rule: the stability gate is closed only if the observation period is complete and every intervention or exception is explicitly recorded. A healthy point-in-time check does not retroactively prove an uninterrupted unchanged-state period.

## Phase 1 — AUDIT-02: exit-node IPv4 NAT

### Goal

Identify the effective WAN NAT rule/chain that translates authorized Tailscale exit-node client traffic.

### Read-only inspection

Run from an authorized LAN/recovery session:

```sh
iptables -t nat -S POSTROUTING
iptables -t nat -nvL POSTROUTING --line-numbers
iptables-save -t nat
```

Record the relevant WAN interface:

```sh
nvram get wan0_gw_ifname
```

Do not add a MASQUERADE or SNAT rule simply because the project-owned filter chain does not contain one.

### Controlled correlation

From an authorized exit-node client, generate a small, identifiable flow to an external test endpoint.

Correlate:

1. packet enters `tailscale0`;
2. project-owned `EDGE_TS_FORWARD` permits the flow;
3. packet leaves the selected WAN interface;
4. an existing platform NAT rule/chain accounts for source translation;
5. return traffic is permitted by established/related state.

Use counters before and after the test:

```sh
iptables -nvL EDGE_TS_FORWARD --line-numbers
iptables -t nat -nvL POSTROUTING --line-numbers
```

If packet capture is required, keep the capture short and sanitize it before publication.

### Closure

AUDIT-02 closes only when sanitized evidence identifies the effective NAT owner/path and demonstrates the authorized exit-node flow using it.

If the platform already supplies the required NAT, no project-owned NAT rule should be added merely for documentation symmetry.

## Phase 2 — AUDIT-03: Fedora/Android DNS datapath

### Goal

Determine the actual resolver path used by Fedora and Android when both use the same exit node and unchanged router configuration.

### Record client variables

For each client record:

- OS and version;
- Tailscale version;
- network transport;
- Tailscale DNS setting;
- Android Private DNS state where applicable;
- any explicit encrypted DNS, VPN, proxy, or browser DoH/DoQ setting.

Change only one client-side variable between controlled cases.

### Three probes per client

1. Normal OS resolver lookup.
2. Explicit classic DNS query to a known external resolver on port 53.
3. Router-resolver query where the client exposes that path.

For classic DNS, correlate with:

```sh
iptables -t nat -nvL EDGE_TS_PREROUTING --line-numbers
```

and existing dnsmasq/Unbound observations.

Where a packet capture is necessary:

```sh
tcpdump -ni tailscale0 -w /tmp/ts-dns.pcap 'port 53'
tcpdump -ni br0 -w /tmp/lan-dns.pcap 'port 53'
```

Use offline analysis and delete/sanitize raw captures after evidence extraction.

### Interpretation

Distinguish explicitly between:

- classic port-53 traffic redirected to router dnsmasq and Unbound;
- a resolver supplied through Tailscale or the client OS;
- Android Private DNS / DoT;
- application/browser DoH or DoQ;
- another VPN/proxy path.

A successful DNS lookup alone is insufficient evidence of the router resolver path.

### Closure

AUDIT-03 closes only when the observed client resolver paths are correlated with router-side evidence and the final evidence clearly separates classic DNS from encrypted/client-specific DNS.

## Phase 3 — remediation only if evidence requires it

If AUDIT-02 or AUDIT-03 identifies an actual defect:

1. document the observed failure;
2. design the smallest remediation;
3. test it away from the reference deployment where practical;
4. define rollback before deployment;
5. apply during a planned maintenance window;
6. repeat affected validation;
7. restart the stability baseline if the reference router state changes materially.

Do not introduce a configuration change merely to make an audit item appear closed.

## Phase 4 — publication

Publish only sanitized evidence:

- no credentials or tokens;
- no private Tailscale addresses or node IDs;
- no MAC addresses;
- no real WAN identifiers;
- no exact filesystem UUID/PARTUUID values;
- no private hostnames or resolver account identifiers;
- no raw packet captures.

The final audit report should distinguish:

- CI/static evidence;
- router live evidence;
- remote-client evidence;
- endpoint/mobile evidence.

## Current repository state

As of 2026-09-18:

- GitHub Actions run **#465**: SUCCESS;
- Fedora clean-room DR validation: PASS;
- AUDIT-01: CLOSED;
- AUDIT-04: CLOSED;
- AUDIT-05: CLOSED;
- AUDIT-02: OPEN / GATED;
- AUDIT-03: OPEN / GATED;
- reference router remains under the unchanged-state observation window through 2026-09-25.
