# Evidence collection

This project separates automated checks from live deployment evidence. Static analysis and mock tests run in GitHub Actions. Router, WAN, Tailscale identity, endpoint-filtering, mobile-telemetry, and performance results must come from the relevant target environment.

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

## Endpoint-filtering evidence

Endpoint tests are collected on the workstation, not by the router evidence collector. Follow [endpoint-filtering-validation.md](endpoint-filtering-validation.md) and keep the router unchanged during the active stability gate.

For a Zen or AdGuard for Windows test, record only the minimum information needed to reproduce and evaluate the result:

- date and defined test window;
- Windows and browser versions;
- endpoint-filter version and relevant settings;
- baseline versus enabled state;
- Windows-reported DNS resolver/path result;
- HTTPS/certificate behaviour;
- defined browser/YouTube observations;
- false positives or broken functionality;
- CPU/RAM observations when measured;
- final verdict for each test case.

If router dnsmasq logs are used to corroborate DNS-path preservation during the stability window, inspect them read-only and publish only a minimized sanitized extract. Do not enable new logging or change router configuration solely to create endpoint evidence.

## Mobile-telemetry evidence

Mobile telemetry requires a separate test record for each phone. Capture at minimum:

- device model and OS/version;
- relevant hardening/debloat state;
- network path;
- scenario and duration;
- observation method;
- sanitized destinations or aggregate counts relevant to the test question;
- limitations and confounding variables.

A second Xiaomi running a different system version is a separate comparative case study. Do not label it as a controlled before/after debloat test. Historical single DNS queries may be cited as context, but they are not a quantitative baseline.

Prefer aggregate counts and short sanitized extracts over full raw DNS logs or packet captures.

## Publication checklist

Before committing evidence:

1. Review every generated or manually collected file.
2. Remove public IP addresses, real internal addresses, email addresses, hostnames, usernames, serial numbers, MAC addresses, tokens, keys, collector destinations, cookies, browser/session identifiers, and certificate private material.
3. Do not publish raw router exports, Tailscale state, browser profiles, exported trust stores, or authentication databases.
4. Treat packet captures, raw DNS logs, and screenshots as private by default. Publish only purpose-built, minimized, manually inspected extracts.
5. State the test date, environment/version information, source role/device, expected result where applicable, observed result, and verdict.
6. Keep failed results when they explain a later fix; link the correcting commit or issue.
7. Distinguish **Observed**, **Not observed**, **Not tested**, and **Inconclusive**. Do not convert absence during a short test into a permanent claim.
8. After adding or updating a dated evidence set and completing sanitization, regenerate its SHA-256 manifest so it covers the final published artifacts. Do not include the manifest itself in its own checksum list.

## Suggested evidence layout

```text
evidence/
├── README.md
├── live-validation-template.md
└── YYYY-MM-DD/
    ├── router/                  # when router evidence was collected
    │   ├── environment.md
    │   ├── healthcheck.md
    │   ├── firewall-counters.md
    │   └── dns-validation.md
    ├── remote-client/           # when remote-client validation was performed
    │   └── live-validation.md
    ├── endpoint-filtering/      # only after a real endpoint test
    │   ├── README.md
    │   ├── environment.txt
    │   ├── dns-path-sanitized.txt
    │   └── results.md
    ├── mobile-telemetry/        # only after a real phone test
    │   └── DEVICE-CASE-STUDY.md
    └── SHA256SUMS
```

Existing historical evidence directories keep their current layout; do not rewrite them merely to match this suggested structure. Use the structured layout for future multi-source validation sets when it improves clarity.

Only create a dated evidence directory after completing and reviewing a real validation run. Empty placeholders are not evidence.
