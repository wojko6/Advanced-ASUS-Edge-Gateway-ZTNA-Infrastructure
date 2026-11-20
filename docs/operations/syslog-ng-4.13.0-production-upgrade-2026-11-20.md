# syslog-ng 4.13.0 ARMv7 — production upgrade and rollback record

**Status:** CURRENT dated checkpoint, 2026-11-20. The operator reported an attended syslog-ng **4.12.0-3 → 4.13.0-1** update on the ASUS TUF-AX5400 and one successful post-upgrade log found in Loki/Grafana. This document records performed steps and recovery boundaries; it is **not** an unattended deployment procedure or proof of a rollback drill.

## Observed runtime and compatibility

- Router ARMv7 kernel 4.1.52, Entware glibc 2.27; Fedora 45 built a valid ARMv7 IPK with **35** plugin `.so` files and the expected interpreter.
- Runtime checks: `opkg status syslog-ng` reported **4.13.0-1**; `syslog-ng --version` reported **4.13.0**; supervisor and worker processes were present.
- The custom `/opt/etc/syslog-ng.conf` SHA-256 matched the pre-change value. The installer created `/opt/etc/syslog-ng.conf-opkg` for its packaged default. **Do not activate the default without a separate reviewed change.**
- One uniquely marked router log line was observed downstream in Grafana Explore / Loki. This is a positive ingestion smoke, not evidence for every source, continuous uptime or a repeat full mTLS validation.

## Preserved recovery material (operator-reported)

- Exact older **4.12.0-3** IPK, with packaged binary MD5 matching the prior router executable; new **4.13.0-1** IPK, both verified by SHA-256 after transfer.
- Production program/module/configuration backup on the router and a hash-verified copy on Fedora.
- Separate protected off-router TLS key/certificate/CA archive; no private key material is committed to the repository.
- Stopped-state snapshot of reliable disk queue and configuration from the maintenance run. The snapshot creation reported success; **restore/replay was not exercised**.

## Reliable buffer and recovery constraints

The configured router sender uses `disk-buffer(reliable(yes))` with `.rqf` and `syslog-ng.persist` files. Their allocated sizes do **not** reveal queued-message counts. In the old runtime `syslog-ng-ctl stats` failed because its expected control socket did not exist. The true backlog was not measured.

For future failures, keep an independent management session, preserve all current queue/persist files, and inspect versions, processes, configuration and destination health before doing anything destructive. Avoid `killall -9`, repeated restart loops, or deleting/overwriting queue files. After a deliberate graceful stop, make a separate, consistent copy of the then-current state before a reviewed downgrade. Do **not** blindly restore stale `.rqf` or `.persist` files across different versions: duplicates, lost messages or incompatibility must be assessed. An old IPK and archive are **rollback resources, not an exercised recovery guarantee**.

The observed absence of `/opt/lib/functions.sh` allowed installed package wrapper scripts to exit early, but does not prove an `opkg` transaction is interruption-free. The service script uses shared `rc.func` functions, including a forced-kill branch that must not be selected casually.

## Post-change test (read-only except one synthetic log message)

1. Verify installed and executable versions, both processes and the SHA-256 of the unchanged custom configuration. Run `syslog-ng --syntax-only -f /opt/etc/syslog-ng.conf`.
2. Emit a uniquely tagged router `logger` message if that source is monitored.
3. In Grafana Explore select Loki, filter the router stream and the marker; for example:

   ```logql
   {job="asus-edge", service_name="asus-edge", source="asus-router"} |= "UNIQUE_MARKER"
   ```

4. Verify message content and timestamp, rather than concluding success from a nonempty chart. Do not expose credentials or raw production logs in public evidence.

## Pending separate acceptance

- A supervised downgrade/restore drill with queue replay/loss-duplication analysis.
- Control-socket diagnostics if stats are needed, without changing production solely for instrumentation.
- Post-reboot/power-loss persistence, long soak and repeated independent mTLS negative/positive tests.

The observed production update does **not** lift unrelated DNS Guard, Issue #235, HCC/agent, privilege or router DR HOLD gates.

[Nov 20 worklog](../worklog/2026-11-20.md) · [logging architecture and earlier mTLS tests](../centralized-logging.md).
