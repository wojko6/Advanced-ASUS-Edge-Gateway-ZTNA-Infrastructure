# Pi-hole DNS collector live validation — 2026-09-28

## Scope

This evidence records the first live Fedora deployment and recovery validation
of the issue #108 Pi-hole DNS activity collector.

The evidence is intentionally sanitized. It does not publish household domains,
client addresses, hostnames, credentials, Pi-hole session IDs or raw NDJSON
records.

## Deployment boundary

The validated path is:

```text
Pi-hole FTL authenticated API on ASUS
        |
        | SSH local forward
        v
127.0.0.1:18080 on Fedora
        |
        v
pihole-dns-collector.py
        |
        +--> local SQLite state/checkpoint
        |
        +--> private queries.ndjson
```

The collector remains Fedora-side. No Loki/Alloy deployment is claimed by this
evidence.

## Initial deployment defect and recovery

The first live collector run exposed a first-run file-creation defect. With an
empty state directory, the collector prepared a batch but attempted to reopen
the not-yet-created NDJSON file using a recovery path that required the file to
already exist.

The failure was:

```text
collector_error: unexpected FileNotFoundError
```

PR #120 fixed the first-append branch and added a regression test.

After installing the fixed collector, the previously prepared batch was
recovered automatically:

```text
recovered prepared batch; checkpoint=10081
collector_ok last_id=10096 disk_head=10085 mem_head=10096
disk_pending=4 union_pending=15
```

This is direct live evidence that the prepared-batch journal survived a failed
run and allowed the collector to resume without discarding the staged batch.

## First integrity check

After recovery and a second manual run:

```text
EVENT_LINES=10096
UNIQUE_IDS=10096
DUPLICATE_IDS=0
STRICTLY_ASCENDING=True
FILE_MAX_ID=10096
CHECKPOINT=10096
CHECKPOINT_MATCH=True
```

A later manual run added only newly observed rows:

```text
LINES_BEFORE=10096
LINES_AFTER=10114
LINES_ADDED=18
collector_ok last_id=10114 disk_head=10096 mem_head=10114
disk_pending=0 union_pending=18
```

The disk head remaining at the previous checkpoint while the memory head
advanced further is consistent with the Phase 0 finding that recent FTL queries
can exist in memory before the periodic long-term database flush.

## Recurring timer validation

The systemd user timer was enabled successfully and repeatedly invoked the
one-shot collector.

Observed successful runs included:

```text
last_id=10127 disk_head=10121 mem_head=10127 disk_pending=7  union_pending=13
last_id=10141 disk_head=10127 mem_head=10141 disk_pending=0  union_pending=14
last_id=10218 disk_head=10143 mem_head=10218 disk_pending=2  union_pending=77
last_id=10253 disk_head=10248 mem_head=10253 disk_pending=30 union_pending=35
```

Each sample completed in roughly 1.3-1.4 seconds.

At that checkpoint the private local event file contained:

```text
10253 events
approximately 3.4 MiB
```

The file-size observation is a point-in-time sample only and is not yet a
retention/storage-growth model.

## Tunnel ownership correction

During the outage test, stopping the systemd-managed tunnel did not initially
remove access to the Pi-hole API. Investigation showed that a manual Phase 0 SSH
tunnel was still listening on the same local port.

The stale manual tunnel was identified by process inspection and stopped. After
that cleanup, no process remained listening on the collector's local API port.

This was a test-environment overlap, not a collector data-integrity failure.

## Controlled transport outage

With the recurring timer stopped for the experiment and no SSH tunnel listening,
the collector was run directly.

Before the outage run:

```text
event lines: 10358
checkpoint:  10358
```

The expected transport failure occurred:

```text
collector_error: Pi-hole API connection failed for /api/auth:
<urlopen error [Errno 111] Connection refused>
RC=1
```

After the failed collection attempt:

```text
event lines: 10358
```

The failed transport therefore did not append partial data or advance the
accepted dataset.

## Recovery after transport restoration

The systemd-managed SSH tunnel was restored and the collector was started again.

The first recovery run reported:

```text
collector_ok last_id=10403 disk_head=10395 mem_head=10403
disk_pending=37 union_pending=45
```

The collector therefore caught up across the outage using both long-term
on-disk history and newer in-memory FTL rows.

A later scheduled run advanced the dataset again without integrity loss.

## Final live integrity checkpoint

With both the systemd tunnel and collector timer active, the final integrity
check reported:

```text
SERVICES:
active
active

EVENT_LINES=10414
UNIQUE_IDS=10414
DUPLICATE_IDS=0
STRICTLY_ASCENDING=True
FILE_MAX_ID=10414
CHECKPOINT=10414
CHECKPOINT_MATCH=True
```

## Result

**PASS — Phase 1 collector deployment and short-outage recovery are
live-validated for the tested environment.**

The validated claims are intentionally bounded:

- authenticated Pi-hole API access through a Fedora loopback SSH tunnel works;
- the one-shot collector and recurring systemd timer work;
- checkpoint state remains consistent with the local NDJSON event stream;
- no duplicate query IDs were present in the validated dataset;
- event IDs remained strictly ascending;
- a transport failure returned non-zero without advancing the dataset;
- collection resumed after transport restoration and caught up with missed
  Pi-hole-visible events;
- the previously implemented prepared-batch journal recovered from a real
  failed first run.

Still outstanding before issue #108 can be considered complete:

- controlled two-client end-to-end distinction in the collector/Loki view;
- Loki and Grafana Alloy deployment;
- bounded DNS-specific retention and measured longer-term storage growth;
- Grafana DNS activity dashboard;
- explicit non-Pi-hole-path coverage evidence;
- final rollback/uninstall validation for the analytics backend.
