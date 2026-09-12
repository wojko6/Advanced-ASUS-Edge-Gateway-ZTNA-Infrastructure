# Evidence bundle — 2026-09-05

Generated: 20260905T102207Z

This directory contains the sanitized post-deployment/post-reboot snapshot plus a separate infrastructure-storage exposure remediation record. Claims should remain attached to the artifact that actually records the observation.

## Included evidence

- `environment.md` — sanitized platform, uptime, memory, and installed service-version snapshot.
- `healthcheck.md` — summarized project health-check result: 34 OK, 0 WARN, 0 FAIL, exit status 0.
- `dns-validation.md` — direct Unbound validation on loopback:53535 with `NOERROR` and DNSSEC `AD` flag.
- `firewall-counters.md` — sanitized managed-chain counters and policy shape at collection time.
- `live-validation.md` — post-deployment/post-reboot validation covering core service presence, project health check, Tailscale netfilter ownership, managed firewall chains, Tailscale control-plane health, and DNSSEC.
- `usb-infrastructure-exposure.md` — finding, remediation, reboot persistence, and post-merge runtime acceptance for the unintended DLNA/SMB exposure of infrastructure storage.
- `SHA256SUMS` — integrity hashes for the published bundle files present when the snapshot was generated.

## Claim boundaries

The post-reboot report records the checks actually observed on 2026-09-05. It explicitly does not represent the broader remote-client, WAN, identity-policy, or exit-node matrix as completed. Those behaviors require their own dated validation.

`environment.md` records installed versions and point-in-time platform state. Version presence alone is not end-to-end service evidence. For example, the listed syslog-ng version does not prove mTLS collector delivery or reliable-buffer recovery; `live-validation.md` supports only the narrower observation that the service was running after that reboot.

Firewall counters are point-in-time evidence of chain state and traffic already seen. A zero counter does not mean a rule is broken, and a non-zero counter does not by itself prove every intended authorization or negative-policy case.

The infrastructure-storage record is historical evidence from the pre-SSD storage state. Its references to the infrastructure USB device describe the environment tested on 2026-09-05 and should not be rewritten as if the later SSD migration had already occurred.

## Publication review

- Review every file manually before publishing.
- Do not add packet captures, public IP addresses, credentials, hostnames, email addresses, Tailscale node state, cookies, session tokens, or private key material.
- Preserve the original observation date and configuration revision when interpreting historical evidence.
- Keep post-reboot service-presence claims separate from end-to-end application or collector behavior.
- Do not infer remote-client, WAN, identity-policy, or exit-node behavior from this local snapshot unless a separate artifact explicitly records it.
