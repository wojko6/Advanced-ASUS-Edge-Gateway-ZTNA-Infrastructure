# GeForce NOW Ethernet vs Wi-Fi 6 Stability – Case Study

## Summary

This case study compares a wired Gigabit Ethernet path with a Wi-Fi 6
(802.11ax, 5 GHz) path from the same Fedora workstation through the same
ASUS TUF-AX5400 gateway to a GeForce NOW session served from
`Poland (NP-WAW-01)`.

The purpose was not to compare headline throughput. The test focused on
latency stability, jitter, packet loss, application-visible loss, and the
effect of rare delay spikes on a latency-sensitive cloud-gaming workload.

The observed result was nuanced:

- both transports completed the tested GeForce NOW runs with zero
  application-reported packet loss and zero frame loss at the captured
  overlay snapshots;
- Wi-Fi 6 added only a small amount of average latency;
- Wi-Fi 6 showed substantially larger short-lived latency excursions than
  the wired baseline;
- no ICMP packet loss was observed during the approximately ten-minute
  long Wi-Fi sampling window;
- the wired path was more deterministic in the short controlled baseline,
  while the tested Wi-Fi path remained usable for the application.

The test does not claim that Wi-Fi packet loss can never occur. Earlier
user-observed loss motivated the investigation, but it was not reproduced
during the documented run.

## Environment

- Gateway: ASUS TUF-AX5400, project reference deployment
- Client: Fedora Linux workstation
- Cloud service: GeForce NOW
- GeForce NOW server shown by the client: `Poland (NP-WAW-01)`
- Stream resolution: 2560 × 1440
- Stream codec: H.265, 10-bit, YUV 4:2:0
- Wired path: 1000 Mb/s, full duplex
- Wireless path: 5 GHz, 5500 MHz, 80 MHz, HE/802.11ax, 2 spatial streams
- Wi-Fi signal during the documented run: approximately -60 to -61 dBm
- Observed Wi-Fi PHY rates after the run: 576.4 Mb/s RX and 720.6 Mb/s TX

The SSID, BSSID, private client addresses, Tailscale node addresses and
other deployment-specific identifiers are intentionally omitted.

## Pre-test control of variables

Before the transport comparison, route inspection showed that the
workstation was using a Tailscale exit node for general Internet traffic.

That would have introduced an additional routing/tunnel variable, so the
exit-node selection was disabled on the client and the route was
rechecked. The subsequent Internet route used the normal LAN gateway.

The Ethernet interface was then validated with `ethtool`:

```text
Speed: 1000Mb/s
Duplex: Full
Auto-negotiation: on
Link detected: yes
```

An earlier spot check had reported 100 Mb/s. Because the full pre-test
validation showed 1000 Mb/s before the measurement run, the 100 Mb/s
reading is retained only as a pre-test anomaly and is not treated as the
measured Ethernet state.

## Method

### Short baseline

For each transport, 200 ICMP echo requests were sent at 100 ms intervals
to:

1. the LAN gateway; and
2. a stable public Internet target.

Interface counters were checked around the baseline.

### GeForce NOW application run

The wired run included a packet capture on the client interface and a
GeForce NOW statistics overlay snapshot.

The Wi-Fi run used:

- `iw` link/station telemetry;
- continuous 100 ms ICMP sampling to the LAN gateway;
- continuous 100 ms ICMP sampling to the public Internet target;
- a GeForce NOW statistics overlay snapshot; and
- a client-side packet capture.

The Wi-Fi capture was later recovered and remained readable through
3,675,119 complete packets. The file was truncated in the middle of the
next packet when the client `/tmp` tmpfs reached capacity, so it is used
for bounded flow-, volume-, and timing-level observations only. It is not
treated as a cleanly completed full-session capture or as an independent
source of GeForce NOW application packet-loss counts.

## Short baseline results

| Metric | Ethernet | Wi-Fi 6 / 5 GHz |
|---|---:|---:|
| LAN RTT minimum | 0.368 ms | 0.972 ms |
| LAN RTT average | 0.578 ms | 2.973 ms |
| LAN RTT maximum | 3.293 ms | 67.379 ms |
| LAN RTT mdev | 0.244 ms | 6.416 ms |
| LAN packet loss | 0% | 0% |
| Internet RTT minimum | 9.484 ms | 9.999 ms |
| Internet RTT average | 10.056 ms | 12.507 ms |
| Internet RTT maximum | 10.668 ms | 55.908 ms |
| Internet RTT mdev | 0.176 ms | 4.666 ms |
| Internet packet loss | 0% | 0% |

The short, method-matched baseline therefore showed only a small average
latency penalty for Wi-Fi, but materially larger jitter and tail latency.

No new Ethernet interface error/drop counters were recorded during the
wired baseline.

## Long Wi-Fi latency sample

During the longer Wi-Fi run, the client collected thousands of replies.

### LAN gateway

```text
Replies:       6176
Expected:      6176
Lost:          0
Loss:          0.0000 %
RTT min:       0.690 ms
RTT avg:       2.184 ms
RTT max:       247.000 ms
RTT stddev:    3.998 ms
RTT >= 20 ms:  6
RTT >= 50 ms:  3
RTT >=100 ms:  2
```

### Public Internet target

```text
Replies:       6000
Expected:      6000
Lost:          0
Loss:          0.0000 %
RTT min:       8.940 ms
RTT avg:       11.543 ms
RTT max:       311.000 ms
RTT stddev:    5.182 ms
RTT >= 20 ms:  20
RTT >= 50 ms:  10
RTT >=100 ms:  3
```

Because large excursions were visible to the LAN gateway itself, at least
part of the observed tail latency occurred on or before the local wireless
hop rather than exclusively on the ISP or GeForce NOW path.

The events were rare: the run still completed with zero ICMP loss.

## Wi-Fi link telemetry

After the long session, `iw` reported:

```text
frequency:        5500 MHz
channel width:    80 MHz
mode:             HE / 802.11ax
signal:           -61 dBm
signal average:   -61 dBm
RX PHY rate:      576.4 Mb/s
TX PHY rate:      720.6 Mb/s
TX retries:       0
TX failed:        0
beacon loss:      0
rx drop misc:     743
```

The `rx drop misc` value is a driver/kernel interface statistic and is
not equivalent to 743 lost GeForce NOW packets. It is therefore recorded
as an observation only.

The GeForce NOW overlay labeled the transport as `WiFi 5.0`, while
Linux `iw` directly reported HE/802.11ax parameters. For this case study,
`iw` is used as the link-layer source of truth.

## Wired GeForce NOW packet capture

The Ethernet capture contained:

```text
Capture duration: 493.155 s
Packets:          approximately 2.706 million
Captured data:    approximately 3.718 GB
```

The dominant UDP traffic was associated with one GeForce NOW service
endpoint on UDP/5004. The two principal conversations to that endpoint
accounted for approximately 3.7 GB of traffic.

A 10-second filtered I/O view of the streaming endpoint showed continuous
non-zero traffic throughout the active stream interval. Across the
approximately 450-second active interval:

- filtered stream data: approximately 3.716 GB;
- average filtered throughput: approximately 66.1 Mb/s;
- highest observed 10-second average: approximately 101.6 Mb/s.

These values describe this specific game scene and encoder behaviour.
They are not a minimum bandwidth requirement for GeForce NOW.

The service endpoint did not answer ICMP echo requests. A route probe
reached the destination network edge at approximately 11–12 ms before
later hops stopped responding. The lack of ICMP replies from the streaming
host is not evidence of stream packet loss.

## Wi-Fi GeForce NOW packet capture

The recovered Wi-Fi capture remained readable for:

```text
Capture duration: 678.772 s
Complete packets: 3,675,119
Captured data:    approximately 4.308 GB
File size:        approximately 4.432 GB
```

Traffic filtered to UDP/5004 contained:

```text
Frames:           3,649,546
Bytes:            4,304,608,129
Share of packets: approximately 99.3% of readable capture packets
Average rate:     approximately 50.7 Mb/s across the capture window
```

Two UDP/5004 conversations to the GeForce NOW service dominated the
capture. Their deployment-specific endpoint addresses are intentionally
omitted from the public evidence.

Ten-second UDP/5004 I/O statistics showed non-zero stream traffic from the
start of the active game stream through the final readable interval. The
changing byte rate is consistent with a variable-bitrate real-time stream
and is not, by itself, evidence of network instability.

The file ended mid-packet because the tmpfs used for capture storage
reached capacity. Wireshark/tshark and `capinfos` both reported the
truncation after the 3,675,119 readable packets. Measurements above are
therefore bounded to the readable prefix of the file. The capture is not
used to infer application packet loss; that metric remains sourced from
the GeForce NOW statistics overlay.

## GeForce NOW overlay observations

| Metric | Ethernet snapshot | Wi-Fi snapshot |
|---|---:|---:|
| GeForce NOW ping | 9 ms | 10 ms |
| Packet loss | 0 | 0 |
| Frame loss | 0 | 0 |
| Game frame rate | 103 FPS | 99 FPS |
| Stream frame rate | 108 FPS | 97 FPS |
| Server | Poland (NP-WAW-01) | Poland (NP-WAW-01) |
| Resolution | 2560 × 1440 | 2560 × 1440 |
| Codec | H.265 10-bit | H.265 10-bit |

The frame-rate difference is not treated as a network-performance result.
The snapshots were captured in different game moments and rendering load
can change independently of network transport.

The important application-level observation is that both snapshots showed
zero packet loss and zero frame loss, with only a 1 ms difference in the
displayed GeForce NOW ping.

## Interpretation

The experiment demonstrates why average ping alone is insufficient for
interactive traffic.

In the short matched baseline, Wi-Fi increased average Internet RTT by
only about 2.45 ms, but its maximum and variability increased much more
strongly. The longer Wi-Fi sample then exposed rare excursions to hundreds
of milliseconds while still delivering every ICMP probe.

For this tested location, signal level and workload:

- Wi-Fi 6 provided adequate average latency and application-level
  performance for GeForce NOW;
- the wireless path was less deterministic than Ethernet;
- rare queueing/retry/airtime effects can exist even when average ping,
  throughput and application-visible loss look healthy;
- Ethernet remains the cleaner reference transport for latency-sensitive
  validation because it removes the shared radio medium from the path.

## Limitations

- The long-duration ping sampling was collected for Wi-Fi, not Ethernet,
  so the 247/311 ms Wi-Fi maxima must not be compared as if they came from
  equal-duration Ethernet samples.
- The Wi-Fi capture was truncated when the client tmpfs reached capacity.
  The 3,675,119 complete packets preceding the truncation are usable for
  bounded flow/volume analysis, but the file is not treated as a cleanly
  completed full-session capture.
- GeForce NOW overlay values are snapshots, not a full-session time
  series.
- The tested Wi-Fi result applies to this client position, signal level,
  channel conditions and point in time.
- Zero packet loss in this run means loss was not observed during the
  documented window. It does not prove that packet loss cannot occur on
  the wireless path.
- The observed service endpoint is session-specific and may change.

## Evidence

A sanitized dated evidence summary is stored in:

- [GeForce NOW Ethernet vs Wi-Fi 6 validation](../evidence/2026-09-25/geforce-now-ethernet-vs-wifi6-validation.md)

Raw packet captures are not committed because they are large and may
contain unrelated traffic. The evidence record contains only the minimum
derived measurements required to support the documented claims.

## Result

Both tested paths delivered a successful 1440p GeForce NOW session with
zero packet loss and zero frame loss shown by the application snapshots.

The meaningful difference was not headline bandwidth or average ping. It
was latency consistency: Wi-Fi 6 showed rare but much larger delay spikes,
including on the local path to the gateway, while the short wired baseline
remained tightly bounded.

This makes the test a practical example of using layered evidence — link
telemetry, ICMP sampling, packet capture and application statistics — to
separate average performance from real-time stability.
