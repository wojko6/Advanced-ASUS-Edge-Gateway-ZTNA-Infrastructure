# Pi-hole API Phase 0 read-only preflight — 2026-09-28

## Scope

This evidence records the sanitized Phase 0 validation for issue #108. It
covers the supported Pi-hole v6 API path only. It does not publish household
domains, client addresses, hostnames, credentials, session identifiers or the
live query database.

## Deployed Pi-hole build

The reference router reported:

```text
Core:    v6.4.3
Web:     v6.6
FTL:     v6.7.1
Entware: 2026.09.20-1
```

The live query database is configured at:

```text
/opt/etc/pihole/pihole-FTL.db
```

FTL uses WAL mode, a 60-second database interval and 31-day long-term
retention in the validated configuration.

## API and authentication boundary

The FTL DNS and web/API listeners are bound to the dedicated Pi-hole LAN alias;
the exact private address is intentionally omitted here.

The operator enabled Asuswrt-Merlin SSH port forwarding and validated a Fedora
loopback tunnel:

```text
127.0.0.1:18080 -> SSH -> router -> <PIHOLE_LAN_IP>:8080
```

The Pi-hole administrator password was configured so unauthenticated query
history returned HTTP 401. A separate Pi-hole application password then
authenticated successfully through `POST /api/auth`.

The application-password session was validated with:

```text
AUTH_HTTP=200
SESSION_VALID=True
SESSION_VALIDITY=1800
QUERIES_HTTP=200
LOGOUT_HTTP=204
```

The live configuration also reported:

```text
webserver.api.app_sudo = false
```

The collector therefore does not need the normal administrator password and
the application-password session is not granted configuration-changing sudo
rights.

## Query schema

A one-row authenticated query confirmed the following top-level query fields:

```text
id
time
type
status
dnssec
domain
upstream
reply
client
list_id
ede
cname
```

Nested objects were observed as:

```text
client -> ip,name
reply  -> time,type
ede    -> code,text
```

The API response also contained:

```text
cursor
recordsTotal
recordsFiltered
earliest_timestamp
earliest_timestamp_disk
```

No real field values were published.

## Cursor semantics and RAM/disk boundary

The tested API sorts the default query view newest-first. A controlled two-row
test showed:

```text
ID_ORDER_DESC=True
TIME_ORDER_DESC=True
CURSOR_EQ_FIRST_ID=True
```

A later RAM-versus-disk test exposed an important edge case:

```text
MEM_CURSOR_EQ_FIRST=True
DISK_CURSOR_EQ_FIRST=False
MEM_DISK_CURSOR_EQUAL=True
MEM_FIRST_GT_DISK_FIRST=True
FIRST_ID_GAP=13
```

At that instant the in-memory query set contained 9,727 records and the
on-disk set contained 9,714. The 13-record difference was consistent with
fresh queries waiting for the periodic database flush.

This means a collector must **not** use the response-level global cursor as the
first frozen cursor for `disk=true`. The safe snapshot boundary is the first
query ID actually returned by that source. The Fedora collector therefore
freezes each source on its own first returned ID and deduplicates the RAM/disk
union by query ID before persistence.

## Bounded read-cost measurement

A controlled extraction of 100 records from each source produced:

```text
RAM:
  query count:       100
  payload:           30,673 bytes
  API took:          ~3.71 ms
  client wall time:  ~15.59 ms

disk=true:
  query count:       100
  payload:           30,510 bytes
  API took:          ~3.68 ms
  client wall time:  ~15.21 ms
```

Router process/resource snapshot:

```text
Before:
  FTL VmSize:        33,044 kB
  FTL VmRSS:         16,428 kB
  FTL VmSwap:        0 kB
  MemAvailable:      123,140 kB
  SwapFree:          2,621,112 kB
  load average:      0.92 0.77 0.72
  FTL CPU ticks:     5,217

After:
  FTL VmSize:        32,376 kB
  FTL VmRSS:         16,356 kB
  FTL VmSwap:        0 kB
  MemAvailable:      122,948 kB
  SwapFree:          2,621,112 kB
  load average:      0.92 0.77 0.72
  FTL CPU ticks:     5,219
```

For this bounded sample, no material CPU, RAM or swap pressure was observed.
The claim is limited to the tested 100-row extraction and does not substitute
for later long-running collector/storage observation.

## Phase 0 result

**PASS.**

The deployed Pi-hole build provides a supported authenticated read-only API
with the required DNS metadata, a workable source-local snapshot cursor, and
low measured cost for the bounded sample. Phase 1 may proceed on Fedora without
opening or copying the live SQLite database and without enabling broad dnsmasq
query logging.

The security caveat introduced by this design is explicit: Asuswrt-Merlin SSH
port forwarding must remain limited to authenticated SSH access, while the
collector binds its forwarded endpoint only to Fedora loopback.
