# Wi-Fi 6 HE160 Interoperability – MediaTek MT7922 vs ASUS/Broadcom Case Study

## Summary

On 2026-09-26, a Windows laptop equipped with a MediaTek Wi-Fi 6E MT7922
adapter showed severe and asymmetric TCP throughput degradation when the ASUS
TUF-AX5400 5 GHz radio operated at HE160.

The same client performed normally at HE80.

The investigation used:

- controlled HE80/HE160 A/B testing;
- both TCP traffic directions;
- two MT7922 driver revisions;
- router-side `wl sta_info` telemetry;
- runtime chanspec and DFS verification;
- and an independent Android HE160 reference client.

The key observation was that the MT7922 client achieved approximately
850–880 Mb/s at HE80 but only approximately 75 Mb/s in the most affected HE160
direction with the current driver.

An independent Android client connected to the same ASUS 5 GHz radio at
160 MHz / 2 spatial streams achieved approximately 670–706 Mb/s in the same
general test environment.

The evidence therefore does not support a simple conclusion that the ASUS
access point is generally incapable of useful HE160 operation. The fault domain
was narrowed to HE160 behaviour involving the tested MT7922 client and the
ASUS/Broadcom platform, without assigning sole root cause to either side.

## Environment

### Access point

- Router: ASUS TUF-AX5400
- Firmware family: Asuswrt-Merlin / GNUton
- 5 GHz runtime interface: `eth6`
- Channel: 100
- Security: WPA3-Personal
- Test widths: 80 MHz and 160 MHz
- HE160 runtime chanspec during the final reference tests: `100/160`
- DFS state during the final HE160 test state: In-Service Monitoring, channel cleared

### Wired endpoint

A Linux workstation connected to the LAN acted as the fixed iperf3 endpoint.

The wireless-client tests reached well above 800 Mb/s at HE80, so the valid
measurement runs were not limited by a 100 Mb/s wired link.

### Windows client

- Wi-Fi adapter: MediaTek Wi-Fi 6E MT7922
- Spatial streams: 2x2
- Old driver: `3.3.0.918`
- Current driver: `26.40.2.587`
- Current-driver date: 2026-05-18
- NDIS: 6.70

The old driver package was exported before the update so that rollback remained
available.

### Android reference client

A modern Wi-Fi 6 Android smartphone was used as an independent HE160 reference
client.

During the controlled comparison it associated at:

```text
channel width: 160 MHz
rx spatial streams: 2
tx spatial streams: 2
RSSI during active tests: approximately -45 to -42 dBm
```

Private IP addresses, MAC addresses, BSSIDs, SSIDs and hostnames are
intentionally omitted from the public case study.

## Initial Symptom

The Windows client could establish a valid 2x2 HE160 association with a high
reported PHY rate, but application throughput was unexpectedly poor.

With the current MT7922 driver, the HE160 association reached:

```text
Receive rate:  2402 Mb/s
Transmit rate: 2402 Mb/s
802.11 mode:   802.11ax
channel:       100
```

This demonstrated that the symptom was not simply a low negotiated PHY rate.

The discrepancy between link rate and TCP throughput became the central
troubleshooting question.

## Test Method

TCP throughput was measured with iperf3 using four parallel streams for
120 seconds.

Client to LAN:

```sh
iperf3 -c <server> -t 120 -P 4
```

LAN to client:

```sh
iperf3 -c <server> -t 120 -P 4 -R
```

During the tests, the ASUS access point was sampled every three seconds with
`wl sta_info`.

The monitored fields included:

- runtime `chanspec`;
- OMI channel width;
- RX/TX spatial-stream count;
- rate of the last TX packet;
- rate of the last RX packet;
- RSSI;
- `tx pkts retries`;
- `rx total pkts retried`.

This allowed application-layer throughput to be compared with wireless
link-layer telemetry.

## Finding 1 – Configured HE160 Did Not Initially Guarantee Runtime HE160

An early configuration state could report a configured chanspec of `100/160`
while the radio runtime remained at `100/80`.

A controlled temporary experiment changed the following variables together:

```sh
nvram set wl_bw_switch_160=0
nvram set wl0_bw_switch_160=0
nvram set wl1_bw_switch_160=0
```

No `nvram commit` was performed.

After restarting the wireless subsystem, the 5 GHz runtime changed from
`100/80` to:

```text
100/160
```

The test therefore demonstrated that the `bw_switch_160` mechanism family
affected runtime 160 MHz operation in this environment.

Because all three values were changed together, the evidence does **not**
identify which individual variable is responsible.

The values remained temporary during the investigation.

## Finding 2 – MT7922 Was Healthy at HE80

The Windows client produced near-Gigabit TCP throughput at HE80.

Representative results with the current driver were:

| Direction | Sender | Receiver | TCP retransmissions |
|---|---:|---:|---:|
| Windows client -> LAN | ~885 Mb/s | ~880 Mb/s | not used as the primary comparison |
| LAN -> Windows client | ~857 Mb/s | ~856 Mb/s | 0 |

The router simultaneously reported:

```text
chanspec:       100/80
OMI:            80 MHz, 2ss RX / 2ss TX
link bandwidth: 80 MHz
```

This strongly reduced the likelihood of a generic LAN bottleneck, a generally
malfunctioning Wi-Fi adapter, or a client incapable of high TCP throughput.

## Finding 3 – HE160 Produced Severe, Direction-Dependent Degradation

With the current MT7922 driver and the same general path, HE160 performance was
substantially worse:

| Direction | Sender | Receiver | TCP retransmissions |
|---|---:|---:|---:|
| Windows client -> LAN | ~76.0 Mb/s | ~74.7 Mb/s | not used as the primary comparison |
| LAN -> Windows client | ~401 Mb/s | ~401 Mb/s | 3,872 |

The forward direction was the most affected.

The comparison between approximately 880 Mb/s receiver throughput at HE80 and
approximately 74.7 Mb/s at HE160 is the strongest controlled A/B result in the
investigation.

During problematic HE160 operation, the association remained at 160 MHz and
2 spatial streams and the reported PHY rate remained high. Strong RSSI was also
observed during the controlled runs.

The symptom therefore cannot be explained only by weak signal or low negotiated
link rate.

## Driver A/B Test

The original MT7922 driver was:

```text
3.3.0.918
```

A newer compatible driver was installed:

```text
26.40.2.587
```

The HE160 results changed as follows:

| Direction | Driver 3.3.0.918 | Driver 26.40.2.587 |
|---|---:|---:|
| Windows client -> LAN | ~53.2 Mb/s receiver | ~74.7 Mb/s receiver |
| LAN -> Windows client | ~339 Mb/s receiver, 5,410 Retr | ~401 Mb/s receiver, 3,872 Retr |

The newer driver therefore improved the HE160 symptom but did not eliminate the
large HE80/HE160 disparity.

This is evidence that the driver revision affects the behaviour, but it does
not prove that the Windows driver is the sole root cause.

## Finding 4 – Independent HE160 Client Performed Normally

To test whether HE160 on the ASUS radio was globally unusable, an independent
Android client was connected to the same 5 GHz radio.

Before the workload, the router confirmed:

```text
chanspec:       100/160
OMI:            160 MHz, 2ss RX / 2ss TX
link bandwidth: 160 MHz
```

With strong RSSI during the active tests, the Android client produced:

| Direction | Sender | Receiver | TCP retransmissions |
|---|---:|---:|---:|
| Android client -> LAN | 707 Mb/s | 706 Mb/s | 20 |
| LAN -> Android client | 673 Mb/s | 671 Mb/s | 404 |

This is substantially higher than the MT7922 HE160 result in both directions.

The Android result therefore strongly weakens the hypothesis that the ASUS
access point is simply incapable of sustaining useful HE160 throughput.

It instead narrows the problem toward behaviour specific to the tested MT7922
client, its software/firmware stack, or interoperability between MT7922 and the
ASUS/Broadcom HE160 implementation.

## Router-Side Retry Telemetry

The router's Broadcom `wl sta_info` counters were useful for correlation, but
they could not be treated as application-loss counters.

During the Android HE160 client-to-LAN run, the approximate active-test
counter changes were:

```text
tx pkts retries:        +3,031
rx total pkts retried: +87,415
```

The same iperf3 run still completed at approximately:

```text
707 Mb/s sender
706 Mb/s receiver
20 TCP retransmissions
```

During the Android reverse run, the approximate active-test changes were:

```text
tx pkts retries:        +5,464
rx total pkts retried: +83,494
```

while iperf3 completed at approximately:

```text
673 Mb/s sender
671 Mb/s receiver
404 TCP retransmissions
```

The Broadcom station counter therefore does not map one-to-one to iperf3 TCP
`Retr`, and it must not be described as an exact count of lost TCP packets.

It is retained as station-associated wireless telemetry only.

This also explains why high values in `rx total pkts retried` cannot, by
themselves, establish poor application performance.

## Consolidated Results

### Windows MT7922

| Driver | Width | Client -> LAN | LAN -> Client |
|---|---|---:|---:|
| 3.3.0.918 | HE80 | ~838 Mb/s receiver | ~877 Mb/s receiver, 0 Retr |
| 3.3.0.918 | HE160 | ~53.2 Mb/s receiver | ~339 Mb/s receiver, 5,410 Retr |
| 26.40.2.587 | HE80 | ~880 Mb/s receiver | ~856 Mb/s receiver, 0 Retr |
| 26.40.2.587 | HE160 | ~74.7 Mb/s receiver | ~401 Mb/s receiver, 3,872 Retr |

### Independent Android HE160 reference

| Width | Client -> LAN | LAN -> Client |
|---|---:|---:|
| HE160 | 706 Mb/s receiver, 20 Retr | 671 Mb/s receiver, 404 Retr |

The Android comparison is not intended as a device-performance benchmark.
Its role is diagnostic: it demonstrates that another 2x2 client can sustain
substantially higher throughput on the same HE160 radio.

## Root Cause Assessment

The evidence supports the following bounded assessment:

> The severe throughput degradation is strongly associated with HE160
> operation in the tested MediaTek MT7922 ↔ ASUS/Broadcom combination.

The evidence supports that:

- the MT7922 can deliver high throughput at HE80;
- the problem becomes severe at HE160;
- the symptom is asymmetric by traffic direction;
- a newer MT7922 driver improves HE160 performance but does not resolve it;
- another 2x2 client can deliver approximately 670–706 Mb/s on the same ASUS
  HE160 radio;
- high negotiated PHY rate does not guarantee high TCP throughput;
- Broadcom station retry-related counters are not equivalent to TCP
  retransmission counts.

The evidence does **not** prove that:

- the MT7922 hardware alone is defective;
- the MediaTek Windows driver alone is the root cause;
- the ASUS firmware alone is defective;
- Broadcom HE160 operation is generally broken;
- DFS is the root cause;
- every MT7922/ASUS combination will reproduce the issue.

Remaining candidate classes include:

- MT7922 driver or client firmware behaviour;
- ASUS/Broadcom firmware behaviour;
- vendor-specific 160 MHz interoperability;
- channel-block or DFS/coexistence interactions;
- or a combination of these factors.

## Final Test State

At the end of the measurement phase, the 5 GHz radio reported:

```text
interface:                eth6
configured chanspec:      100/160
runtime chanspec:         100/160
DFS state:                In-Service Monitoring
DFS channel:              cleared
wl_bw_switch_160:         0
wl0_bw_switch_160:        0
wl1_bw_switch_160:        0
```

The `bw_switch_160` values were part of the temporary controlled experiment and
were not committed with `nvram commit`.

## Limitations

This was a controlled troubleshooting exercise on one reference router and a
small number of client devices.

The investigation did not include:

- a second MT7922 device;
- a second Broadcom access point;
- another 160 MHz channel block;
- exhaustive UDP loss/jitter testing;
- RF-spectrum instrumentation;
- controlled reproduction across multiple router firmware releases.

The case therefore narrows the fault domain but does not claim a universal
vendor defect.

## Lessons Learned

- Configured channel width and runtime channel width must be verified
  independently.
- A high PHY rate is not evidence of high application throughput.
- A clean HE80 control test can separate a width-specific wireless problem from
  a generic LAN or endpoint bottleneck.
- Changing one software variable, such as the client driver, is useful even when
  it does not fully resolve the issue because it shows whether the symptom is
  sensitive to that layer.
- A second independent client is a powerful way to distinguish an AP-wide
  problem from client-specific or interoperability behaviour.
- Vendor-specific wireless counters must be interpreted according to their
  semantics and must not be relabeled as TCP loss.
- Root-cause claims should remain narrower than the evidence.

## Result

The investigation converted a vague "Wi-Fi is slow at 160 MHz" symptom into a
reproducible and bounded interoperability case.

The strongest diagnostic sequence was:

```text
poor HE160 throughput on MT7922
-> verify actual HE160 runtime
-> establish healthy HE80 baseline
-> test both traffic directions
-> update MT7922 driver and repeat
-> re-run HE80 with the new driver
-> introduce independent HE160 client
-> compare router telemetry with TCP results
```

The final evidence shows that the ASUS reference router can sustain useful
HE160 throughput with another client, while the tested MT7922 remains
dramatically slower at HE160 than at HE80.

The fault domain is therefore narrowed to the tested MT7922/ASUS-Broadcom HE160
interaction, with sole root cause intentionally left unassigned.