# Xbox Cloud Gaming in Microsoft Edge — WebRTC Case Study

## Summary

This case study examines one Xbox Cloud Gaming browser session on a Fedora
workstation using Microsoft Edge. The purpose was to understand the
client-visible real-time transport and decoding path rather than to benchmark
the Xbox service or the WAN connection.

The session was inspected with Chromium/Edge WebRTC Internals and
`edge://gpu`. The retained WebRTC statistics provide approximately 1000
one-second samples spanning 999.668 seconds.

The main observations were:

- Xbox Cloud Gaming used a WebRTC PeerConnection with inbound H.264 video and
  Opus audio;
- the video stream remained at 1920 x 1080 throughout the retained statistics;
- 935 of 1000 reported video-rate samples were between 58 and 62 FPS;
- WebRTC reported zero video `packetsLost`, zero `framesDropped`, zero
  freezes, and zero NACK/PLI/FIR requests throughout the retained sample;
- the selected ICE candidate pair used UDP and did not use a relay candidate;
- selected-pair WebRTC RTT stayed between approximately 30 and 34 ms;
- `edge://gpu` reported generic hardware video-decode capability, while the
  active WebRTC stream reported `decoderImplementation=FFmpeg` and
  `powerEfficientDecoder=false`.

The final decoder observation is intentionally bounded: the evidence does not
prove CPU-only decoding, but it also does not demonstrate a power-efficient
hardware-decoder path for this specific xCloud stream.

## Environment

Client-side environment recorded for the test:

```text
Browser:          Microsoft Edge 154.0.4258.37
Operating system: Fedora Linux, kernel 7.2.7-200.fc44.x86_64
Session:          GNOME / Wayland
GPU:              NVIDIA GeForce RTX 3060 Laptop GPU
GPU driver:       NVIDIA 615.71.09
Browser source:   Flatpak
```

The generic Edge GPU capability page reported:

```text
Compositing:   Hardware accelerated
Rasterization: Hardware accelerated
Video Decode: Hardware accelerated
Video Encode: Software only
WebGL:         Hardware accelerated
WebGPU:        Hardware accelerated
```

Those capability flags describe the browser/GPU environment. They are not
treated as proof that the active xCloud video stream used a hardware decoder.

## Method

A single Xbox Cloud Gaming session was started in Microsoft Edge.

Before/during the session:

1. `edge://gpu` was exported to record the browser, OS, graphics backend and
   generic acceleration capabilities.
2. `edge://webrtc-internals` was opened before the xCloud session.
3. The session was allowed to run normally.
4. The inbound RTP video statistics were inspected while the session was
   active.
5. A WebRTC Internals dump was exported before the browser state was discarded.

The raw WebRTC dump is not committed to the public repository. It contains
session-specific URL data, ICE candidate addresses/ports, certificate
fingerprints, track/SSRC identifiers and other metadata that are unnecessary
for the public technical claims.

The published evidence therefore contains only derived, sanitized values.

## WebRTC session structure

The browser created one PeerConnection for the observed xCloud session.

The WebRTC event log showed:

- an inbound video transceiver;
- an inbound audio transceiver;
- multiple application data channels.

Observed data-channel labels included:

```text
unreliableinput
reliableinput
input
chat
control
message
qos
```

The `unreliableinput` channel was created unordered with
`maxRetransmits=0`; the other listed input/control/message channels were
created ordered.

This supports the client-side observation that the browser session uses
WebRTC not only for audio/video delivery but also for interactive application
data. The dump alone does not establish the server-side implementation beyond
the exposed WebRTC behaviour.

## Video format and frame delivery

The inbound video codec was:

```text
MIME type:      video/H264
Payload type:   116
Clock rate:     90000
SDP parameters: level-asymmetry-allowed=1;
                packetization-mode=1;
                profile-level-id=4d001f
```

The reported video dimensions remained:

```text
frameWidth:  1920
frameHeight: 1080
```

Across the 1000 retained samples:

```text
58-62 FPS samples: 935 / 1000
60 FPS samples:    807 / 1000
59 FPS samples:    105 / 1000
30 FPS samples:     54 / 1000
```

The final block of the series settled at approximately 30 FPS. The WebRTC
dump does not establish whether that change was caused by game/application
state, encoder behaviour, scene complexity or another factor. It is therefore
not classified as a network fault.

## Loss, recovery and freezes

For the entire retained video-statistics series:

```text
packetsLost:          0
framesDropped:        0
freezeCount:          0
totalFreezesDuration: 0
nackCount:            0
pliCount:             0
firCount:             0
```

The cumulative `retransmittedPacketsReceived` counter was 427 at the first
retained sample and remained 427 at the final sample. It therefore did not
increase during the retained statistics window and is not interpreted as 427
loss events during this test.

These are WebRTC receiver statistics. They demonstrate what the browser
reported for this session window; they do not prove that packet loss can never
occur on Xbox Cloud Gaming.

## Receive rate and traffic volume

The browser's derived inbound-video bitrate series showed:

```text
median: approximately 16.61 Mb/s
p95:    approximately 18.39 Mb/s
maximum: approximately 21.12 Mb/s
```

The cumulative video `bytesReceived` counter increased from 249,887,152 to
2,218,009,780 bytes across the retained statistics, an increase of
approximately 1.968 GB.

The cumulative video `packetsReceived` counter increased from 229,248 to
2,031,599, an increase of 1,802,351 packets.

Because both counters were already non-zero at the first retained sample, the
final cumulative values are not presented as the total traffic of the complete
Xbox Cloud Gaming session.

## Jitter and selected-pair RTT

Inbound video RTP jitter during the retained series was:

```text
median: 2 ms
p95:    2 ms
minimum: 0 ms
maximum: 8 ms
```

The nominated ICE candidate pair remained in `succeeded` state and used UDP.

Sanitized candidate properties:

```text
local candidate type:  prflx
remote candidate type: host
protocol:              UDP
relay candidate used:  no
```

The selected-pair `currentRoundTripTime` series was:

```text
median: 31 ms
p95:    32 ms
minimum: 30 ms
maximum: 34 ms
```

This value is the WebRTC ICE candidate-pair RTT. It must not be described as
full controller-to-photon latency or total game input latency.

## Decoder-path observation

The generic browser capability report stated:

```text
Video Decode: Hardware accelerated
```

However, the inbound WebRTC video stream consistently reported:

```text
decoderImplementation: FFmpeg
powerEfficientDecoder: false
```

These two observations are not treated as contradictory proof of a defect.
The first is a browser/GPU capability statement; the second is a
stream-specific WebRTC decoder report.

The evidence therefore supports only the following bounded conclusion:
hardware video decoding was available to Edge in the test environment, but a
power-efficient hardware-decoder path was not demonstrated for this specific
xCloud stream.

No claim is made that `FFmpeg` necessarily means CPU-only decoding in every
Chromium/Edge configuration.

## Interpretation

This session demonstrates the value of browser-native WebRTC telemetry for a
real-time cloud workload.

Compared with a packet capture alone, WebRTC Internals exposes application-
meaningful receiver metrics such as:

- RTP packet loss;
- decoded and dropped frames;
- freezes;
- codec and frame dimensions;
- receiver jitter;
- feedback counters;
- ICE candidate-pair state and RTT;
- decoder implementation metadata.

For this documented session, the browser reported a stable 1080p H.264
stream, mostly near 60 FPS, without receiver-reported packet loss, dropped
frames or freezes.

The test also illustrates an evidence-boundary lesson: a generic browser
capability such as "hardware video decode available" must not automatically
be converted into a claim that a particular real-time stream used that path.

## Limitations

- This is one browser session on one client and one point in time.
- No controlled Ethernet-versus-Wi-Fi comparison was performed for xCloud.
- No packet capture was collected for this xCloud run.
- No independent controller-to-photon or input-latency measurement was made.
- The WebRTC statistics begin with non-zero cumulative counters, so they do not
  represent the complete session from its first packet.
- The final reduction to approximately 30 FPS is recorded but its cause is not
  established by the available evidence.
- The selected ICE candidate pair and service topology may change between
  sessions.
- `decoderImplementation=FFmpeg` and
  `powerEfficientDecoder=false` do not by themselves prove CPU-only decode.

## Evidence

A sanitized dated evidence summary is stored in:

- [Xbox Cloud Gaming Edge/WebRTC validation](../evidence/2026-09-25/xbox-cloud-edge-webrtc-validation.md)

The raw WebRTC Internals dump and raw screenshots are intentionally excluded
from the public repository because they contain session-specific and
network-specific identifiers.

## Result

The retained browser telemetry shows a successful Xbox Cloud Gaming WebRTC
session delivering 1920 x 1080 H.264 video, predominantly near 60 FPS, with
zero browser-reported RTP packet loss, dropped frames and freezes during the
recorded statistics window.

The case study is useful primarily as an example of layered client-side
diagnostics and disciplined claim boundaries: browser capability state,
per-stream RTP statistics, ICE transport metrics and decoder metadata are
treated as related but distinct evidence sources.
