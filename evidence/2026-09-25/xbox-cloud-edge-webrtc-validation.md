# Xbox Cloud Gaming Edge/WebRTC validation — 2026-09-25

## Scope

Sanitized client-side evidence from one Xbox Cloud Gaming session in Microsoft
Edge on Fedora Linux.

The source evidence consisted of an `edge://gpu` export and a
`edge://webrtc-internals` dump. The raw WebRTC dump is not published because
it contains session URLs, ICE candidate addresses/ports, certificate
fingerprints, track/SSRC identifiers and other per-session metadata.

This public artifact contains derived values only.

## Client environment

```text
Browser:          Microsoft Edge 154.0.4258.37
Operating system: Fedora Linux, kernel 7.2.7-200.fc44.x86_64
Desktop/session:  GNOME / Wayland
GPU:              NVIDIA GeForce RTX 3060 Laptop GPU
GPU driver:       NVIDIA 615.71.09
```

Generic Edge graphics capability:

```text
Compositing:   Hardware accelerated
Rasterization: Hardware accelerated
Video Decode: Hardware accelerated
Video Encode: Software only
WebGL:         Hardware accelerated
WebGPU:        Hardware accelerated
```

## Retained WebRTC statistics window

```text
Start:    2026-09-25T10:49:23.919Z
End:      2026-09-25T11:06:03.587Z
Duration: 999.668 s
Samples:  1000
```

The counters were already non-zero at the first retained sample. This is a
statistics window, not proof that the full xCloud session began at the stated
start time.

## Video codec and format

```text
kind:            video
codec:           H.264
MIME type:       video/H264
payload type:    116
clock rate:      90000
profile-level-id: 4d001f
frame width:     1920
frame height:    1080
```

Frame-rate samples:

```text
58-62 FPS: 935 / 1000 samples
60 FPS:    807 / 1000 samples
59 FPS:    105 / 1000 samples
30 FPS:     54 / 1000 samples
```

The final series includes a sustained approximately 30 FPS interval. No cause
is assigned from this evidence alone.

## Receiver loss/recovery metrics

Every retained video sample reported:

```text
packetsLost = 0
framesDropped = 0
freezeCount = 0
totalFreezesDuration = 0
nackCount = 0
pliCount = 0
firCount = 0
```

`retransmittedPacketsReceived` was already 427 at the first retained sample
and remained 427 at the final sample. No increase in that counter was observed
during the retained statistics window.

## Receive volume

Video counters:

```text
bytesReceived first: 249,887,152
bytesReceived last:  2,218,009,780
observed increase:   1,968,122,628 bytes

packetsReceived first: 229,248
packetsReceived last:  2,031,599
observed increase:     1,802,351 packets

framesReceived first: 7,781
framesReceived last:  65,934
observed increase:     58,153 frames
```

The browser-derived video bitrate series:

```text
median: approximately 16.61 Mb/s
p95:    approximately 18.39 Mb/s
maximum: approximately 21.12 Mb/s
```

These are observed stream values, not published Xbox bandwidth requirements.

## RTP jitter

Inbound-video jitter across the retained series:

```text
minimum: 0 ms
median:  2 ms
p95:     2 ms
maximum: 8 ms
```

## ICE transport

The selected candidate pair remained nominated and in `succeeded` state.

Sanitized selected-pair properties:

```text
local candidate type:  prflx
remote candidate type: host
protocol:              UDP
relay candidate used:  no
```

Selected-pair WebRTC `currentRoundTripTime`:

```text
minimum: 30 ms
median:  31 ms
p95:     32 ms
maximum: 34 ms
```

This metric is ICE/WebRTC candidate-pair RTT. It is not a controller-to-photon
measurement and is not presented as total gaming latency.

## Audio and data channels

Inbound audio used Opus.

Observed WebRTC data-channel labels:

```text
unreliableinput
reliableinput
input
chat
control
message
qos
```

The `unreliableinput` channel was unordered with `maxRetransmits=0`.
The remaining listed application channels were created ordered.

## Decoder observation

Generic browser capability:

```text
edge://gpu:
Video Decode: Hardware accelerated
```

Per-stream WebRTC report:

```text
decoderImplementation: FFmpeg
powerEfficientDecoder: false
```

Verdict: hardware video-decode capability existed in the browser environment,
but a power-efficient hardware-decoder path was not demonstrated for this
specific xCloud stream. This evidence does not prove CPU-only decoding.

## Verdict

**Observed:**

- one xCloud WebRTC PeerConnection with inbound H.264 video and Opus audio;
- 1920 x 1080 video throughout the retained statistics;
- 935/1000 frame-rate samples between 58 and 62 FPS;
- zero WebRTC video packet loss across all retained samples;
- zero dropped video frames and zero freezes across all retained samples;
- zero NACK/PLI/FIR feedback counts across all retained samples;
- inbound-video jitter median 2 ms and maximum 8 ms;
- nominated/succeeded UDP ICE candidate pair without a selected relay
  candidate;
- selected-pair RTT between 30 and 34 ms;
- generic Edge hardware-video-decode capability;
- per-stream `FFmpeg` decoder report with
  `powerEfficientDecoder=false`.

**Not observed during the retained window:**

- receiver-reported video packet loss;
- frame drops;
- video freezes;
- an increase in the pre-existing retransmitted-packet counter;
- selection of an ICE relay candidate.

**Not tested / not proven:**

- Ethernet-versus-Wi-Fi behaviour for xCloud;
- packet-capture-level transport analysis;
- controller-to-photon latency;
- server-side processing latency;
- cause of the final approximately 30 FPS interval;
- CPU-only decoding;
- equivalence of this one session to other xCloud regions, games, browsers or
  client systems.
