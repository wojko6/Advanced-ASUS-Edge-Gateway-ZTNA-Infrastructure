# Evidence collection

This project separates automated checks from live deployment evidence. Static analysis and mock tests run in GitHub Actions. Router, WAN, Tailscale identity, and performance results must come from the target environment.

## Router snapshot

Run the collector on the router after installation and health validation:

```sh
/jffs/addons/asus-edge/bin/collect-evidence.sh
```

The default destination is a timestamped directory under `/tmp`. You can provide another new directory as the first argument:

```sh
/jffs/addons/asus-edge/bin/collect-evidence.sh /tmp/asus-edge-evidence-review
```

The collector records:

- router model, firmware, kernel, memory, uptime, and service versions;
- counts of healthcheck OK/WARN/FAIL statuses and its exit status;
- managed IPv4 and IPv6 firewall counters;
- a direct Unbound DNSSEC result;
- SHA-256 hashes for the generated Markdown files.

It does not collect Tailscale status, user identities, device names, configuration contents, routing tables, full DNS responses, or packet captures. Firewall source and destination addresses, including translated NAT targets, are replaced before the report is written.

Detailed healthcheck diagnostics are deliberately omitted because failure
messages can contain private device addresses or paths. Run `healthcheck.sh`
locally to investigate failures, and manually sanitize any diagnostic excerpt
you choose to publish. Existing historical snapshots are not rewritten.

## Remote validation

The router snapshot cannot prove client identity policy or WAN filtering. Run the matrix in [testing.md](testing.md) from the required locations:

- an authorized Tailscale admin device;
- a non-admin Tailscale device;
- an approved service user;
- an unauthorized exit-node user;
- an external host you control for WAN testing.

Record actual results in [the live-validation template](../evidence/live-validation-template.md). Replace every placeholder or remove the row; never present an expected result as an observed result.

## Publication checklist

Before committing evidence:

1. Review every generated file manually.
2. Remove public IP addresses, real internal addresses, email addresses, hostnames, usernames, serial numbers, tokens, keys, and collector destinations.
3. Do not publish raw router exports or Tailscale state.
4. Treat packet captures as private by default. Publish only purpose-built, minimized, manually inspected extracts.
5. State the test date, firmware, direction, source role, expected result, observed result, and verdict.
6. Keep failed results when they explain a later fix; link the correcting commit or issue.

## Suggested evidence layout

```text
evidence/
├── README.md
├── live-validation-template.md
└── YYYY-MM-DD/
    ├── environment.md
    ├── healthcheck.md
    ├── firewall-counters.md
    ├── dns-validation.md
    ├── live-validation.md
    └── SHA256SUMS
```

Only create a dated directory after completing and reviewing a real validation run.
