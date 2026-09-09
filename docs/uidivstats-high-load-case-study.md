# uiDivStats High Load Incident – Troubleshooting Case Study

## Summary

During routine monitoring of an ASUS TUF-AX5400 running Asuswrt-Merlin,
the router exhibited unusually high load averages despite significant CPU
idle time.

The investigation identified a large accumulation of orphaned uiDivStats
background processes, primarily:

- `uiDivStats flushtodb`
- `uiDivStats querylog`

The installed uiDivStats version was an outdated v3.0.2 release from the
archived `jackyaz/uiDivStats` repository.

The issue was remediated by migrating uiDivStats to v4.0.16 from the
AMTM-OSR-maintained repository, migrating the SQLite statistics database,
and terminating the stale orphaned processes.

## Environment

- Router: ASUS TUF-AX5400
- Firmware: Asuswrt-Merlin / Gnuton
- uiDivStats before remediation: v3.0.2
- uiDivStats after remediation: v4.0.16
- Diversion: enabled
- Entware: enabled
- SQLite-backed uiDivStats statistics
- Tailscale, Unbound and syslog-ng also active

## Initial Symptoms

The router showed elevated system load:

```text
load average: 8.77, 5.43, 4.63
```

Additional samples remained elevated, with the one-minute load staying
above 7 for several measurements.

At the same time, CPU idle time frequently remained between approximately
50% and 80%, suggesting that the load was not caused by sustained CPU
saturation alone.

Approximately 100 uiDivStats-related processes were present.

## Investigation

Process-state inspection showed no significant `D`-state population,
reducing the likelihood of a persistent storage I/O stall.

Inspection of uiDivStats processes revealed many instances such as:

```text
/bin/sh /jffs/scripts/uiDivStats flushtodb
/bin/sh /jffs/scripts/uiDivStats querylog
```

Many of these processes had:

```text
PPID=1
STATE=S
```

A wait-channel inspection showed:

```text
91 do_wait
```

This indicated that 91 orphaned uiDivStats shell processes were sleeping
in the kernel wait path.

The installed uiDivStats release was:

```text
v3.0.2
https://github.com/jackyaz/uiDivStats
```

The script's internal update repository still pointed to the archived
Jackyaz repository.

## Remediation

Before making changes, backups were created for:

- the uiDivStats script,
- uiDivStats configuration,
- the SQLite statistics database.

The current uiDivStats v4.0.16 script from the AMTM-OSR-maintained
repository was then installed.

The new version detected the legacy database schema and prepared the old
database for migration.

Before migration:

```text
new database records: 0
old database records: 40553
```

The built-in maintenance command was executed:

```sh
uiDivStats trimdb
```

The migration completed successfully:

```text
Data migration complete
Database analysis and optimization completed.
Stats updated successfully
```

After migration, the new database contained:

```text
40682 records
```

The legacy `.old` migration database was removed automatically.

## Orphan Process Cleanup

The remaining orphaned `flushtodb` and `querylog` processes with `PPID=1`
were terminated using `SIGTERM`.

The uiDivStats process count dropped from approximately:

```text
94
```

to:

```text
4
```

A later validation showed:

```text
orphan flushtodb/querylog: 0
```

The remaining processes were normal uiDivStats/taildns helper processes.

## Validation

Before remediation:

```text
load average: 8.77, 5.43, 4.63
```

After migration and stale-process cleanup:

```text
load average: 0.97, 1.19, 3.11
```

The higher 15-minute value was expected because the load average still
included measurements from the pre-remediation period.

Additional validation confirmed:

```text
orphan flushtodb/querylog: 0
sqlite3 active processes: 0
```

No recurrence of the orphan-process accumulation was observed during the
initial post-remediation monitoring period.

## Root Cause Assessment

The available evidence strongly indicates that the outdated uiDivStats
v3.0.2 installation was associated with accumulation of orphaned
`flushtodb` and `querylog` processes.

Migrating to uiDivStats v4.0.16 and cleaning the stale processes restored
normal router load.

Because the troubleshooting was performed on a live router rather than
through controlled reproduction of the old software defect, this should
be treated as a strongly supported operational root-cause assessment,
not as proof of a specific upstream software bug.

## Lessons Learned

- High load average does not necessarily mean CPU saturation.
- Process state, PPID and wait-channel inspection can be more informative
  than CPU percentage alone.
- Router add-ons should be included in lifecycle and version monitoring.
- Configuration and application databases should be backed up before
  in-place migrations.
- Post-change validation should measure both functional correctness and
  resource behavior.
- Root-cause claims should distinguish observed evidence from assumptions.

## Result

The router returned to normal operating load, uiDivStats statistics were
preserved through migration, and no orphaned `flushtodb/querylog`
processes were detected after remediation.
