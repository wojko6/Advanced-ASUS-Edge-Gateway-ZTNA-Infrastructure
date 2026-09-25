# GeForce NOW Ethernet vs Wi-Fi 6 validation — 2026-09-25

## Scope

Sanitized client-side validation comparing Ethernet and Wi-Fi 6/5 GHz for
a latency-sensitive GeForce NOW session through the ASUS Edge reference
gateway.

This artifact records observed values only. It omits SSID/BSSID, private
client addresses, Tailscale node addresses and unrelated packet-capture
content.

## Pre-test route control

General Internet traffic was initially routed through a Tailscale exit
node. Exit-node selection was disabled before the comparison and the
client route was rechecked to use the normal LAN gateway.

Ethernet link validation before the measured run:

```text
Speed: 1000Mb/s
Duplex: Full
Auto-negotiation: on
Link detected: yes
```

## Ethernet baseline

```text
LAN:
200 transmitted, 200 received, 0% packet loss
rtt min/avg/max/mdev = 0.368/0.578/3.293/0.244 ms

Internet:
200 transmitted, 200 received, 0% packet loss
rtt min/avg/max/mdev = 9.484/10.056/10.668/0.176 ms

Interface counter deltas:
rx_errors  +0
rx_dropped +0
tx_errors  +0
tx_dropped +0
```

## Ethernet GeForce NOW capture

```text
Number of packets: approximately 2.706 million
File size:         approximately 3.810 GB
Data size:         approximately 3.718 GB
Capture duration:  493.155 s
Data byte rate:    approximately 7.539 MB/s
```

Dominant streaming endpoint observed in the capture:

```text
UDP/5004
principal conversation: approximately 3.646 GB
secondary conversation: approximately 69 MB
```

The public service IP is omitted from this evidence summary because the
GeForce NOW overlay independently identifies the selected service
location and the endpoint may change between sessions.

Filtered 10-second I/O statistics for the streaming endpoint:

```text
active interval:               approximately 450 s
filtered data:                 approximately 3.716 GB
average filtered throughput:   approximately 66.1 Mb/s
highest 10-second average:     approximately 101.6 Mb/s
zero-traffic gaps in active interval: none observed
```

Direct ICMP echo to the streaming host received no replies. A route probe
reached the destination network edge at approximately 11–12 ms before
later hops stopped responding. This is recorded as ICMP filtering/non-
response, not stream packet loss.

## Ethernet application snapshot

GeForce NOW overlay:

```text
server:              Poland (NP-WAW-01)
ping:                9 ms
packet loss:         0
frame loss:          0
resolution:          2560 x 1440
codec:               H.265, 10-bit, YUV 4:2:0
game frame rate:     103 FPS
stream frame rate:   108 FPS
```

## Wi-Fi link

Linux `iw` identified the wireless link as:

```text
band:                5 GHz
frequency:           5500 MHz
channel width:       80 MHz
mode:                HE / 802.11ax
spatial streams:     2
signal before:       approximately -60 dBm
signal after:        -61 dBm
signal average:      -61 dBm
RX PHY rate after:   576.4 Mb/s
TX PHY rate after:   720.6 Mb/s
TX retries:          0
TX failed:           0
beacon loss:         0
rx drop misc:        743
```

The `rx drop misc` counter is not interpreted as GeForce NOW packet
loss.

## Wi-Fi GeForce NOW capture

The Wi-Fi capture was recovered after the initial documentation pass.
`capinfos` and `tshark` could read 3,675,119 complete packets before
reporting that the file had been cut short in the middle of the next
packet.

```text
Number of complete packets: 3,675,119
File size:                  approximately 4.432 GB
Data size:                  approximately 4.308 GB
Capture duration:           678.771553 s
Average packet size:        1172.23 bytes
Average packet rate:        approximately 5,414 packets/s
```

UDP/5004 traffic in the readable capture prefix:

```text
Frames:                     3,649,546
Bytes:                      4,304,608,129
Share of readable packets:  approximately 99.3%
Average filtered rate:      approximately 50.7 Mb/s
```

Two UDP/5004 conversations dominated the stream traffic. Public service
and private client addresses are omitted from this sanitized record.

The capture file was not cleanly finalized because the client `/tmp`
tmpfs reached capacity. The readable prefix is used only for bounded
flow-, volume-, and timing-level observations. It is not used to derive
GeForce NOW packet-loss counts or to claim complete capture coverage of
the session.

## Wi-Fi short baseline

```text
LAN:
200 transmitted, 200 received, 0% packet loss
rtt min/avg/max/mdev = 0.972/2.973/67.379/6.416 ms

Internet:
200 transmitted, 200 received, 0% packet loss
rtt min/avg/max/mdev = 9.999/12.507/55.908/4.666 ms
```

Interface deltas during this short baseline:

```text
rx_errors  +0
rx_dropped +4
tx_errors  +0
tx_dropped +0
```

The four `rx_dropped` increments are interface/kernel counters and are
not treated as four lost application packets.

## Wi-Fi long latency sample

LAN gateway:

```text
Replies:       6176
Expected:      6176
Lost:          0
Loss:          0.0000 %
RTT min:       0.690 ms
RTT avg:       2.184 ms
RTT max:       247.000 ms
RTT stddev:    3.998 ms
RTT >= 10 ms:  10
RTT >= 20 ms:  6
RTT >= 30 ms:  5
RTT >= 50 ms:  3
RTT >=100 ms:  2
```

Public Internet target:

```text
Replies:       6000
Expected:      6000
Lost:          0
Loss:          0.0000 %
RTT min:       8.940 ms
RTT avg:       11.543 ms
RTT max:       311.000 ms
RTT stddev:    5.182 ms
RTT >= 10 ms:  5865
RTT >= 20 ms:  20
RTT >= 30 ms:  13
RTT >= 50 ms:  10
RTT >=100 ms:  3
```

## Wi-Fi application snapshot

GeForce NOW overlay:

```text
server:              Poland (NP-WAW-01)
ping:                10 ms
packet loss:         0
frame loss:          0
resolution:          2560 x 1440
codec:               H.265, 10-bit, YUV 4:2:0
game frame rate:     99 FPS
stream frame rate:   97 FPS
```

The GeForce NOW overlay displayed `WiFi 5.0` as its transport label, but
the operating system directly reported HE/802.11ax. The link-layer
classification in this evidence therefore follows `iw`.

## Later same-day observational follow-up

After the controlled comparison, the wired path was used for approximately
one hour of normal GeForce NOW play.

Operator-observed state during that period:

```text
transport:              Ethernet
application packet loss: 0
ping:                   stable
```

The endpoint Zen filter was toggled on/off without an observed change in
GeForce NOW loss or latency behaviour.

This is retained as a bounded normal-use observation rather than a
controlled filter benchmark.

A same-day Exit Node overlay comparison is not used as acceptance evidence.
Route verification after the screenshots showed that the nominal final
return-to-baseline segment still had the ASUS exit node selected, so the
intended A/B/A sequence was confounded. The client was subsequently
returned to the normal Ethernet/LAN route and that route state was
explicitly verified.

## Verdict

**Observed:**

- zero ICMP packet loss in both short baselines;
- zero ICMP loss across the long Wi-Fi sample;
- zero packet loss and zero frame loss in both captured GeForce NOW
  overlay snapshots;
- Wi-Fi average latency remained close to Ethernet;
- Wi-Fi produced materially higher short-baseline jitter and rare long-run
  latency spikes, including spikes visible to the LAN gateway;
- the recovered Wi-Fi capture contained 3,675,119 readable packets across
  678.772 s, with UDP/5004 accounting for approximately 99.3% of them.

**Not observed during this run:**

- reproducible Wi-Fi packet loss;
- GeForce NOW packet/frame loss at the captured application snapshots.

**Not tested / unavailable:**

- symmetric long-duration Ethernet ping sampling;
- packet-level derivation of GeForce NOW application loss from UDP/5004;
- a cleanly finalized full-session Wi-Fi capture, because the recovered
  file was truncated when the capture tmpfs reached capacity.

The evidence supports a bounded conclusion that Wi-Fi 6 was functional and
loss-free in the documented window but less deterministic in latency than
the wired reference path.
