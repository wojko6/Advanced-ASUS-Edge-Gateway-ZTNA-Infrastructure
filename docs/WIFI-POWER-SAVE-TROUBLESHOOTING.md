# Wi-Fi Power-Save Troubleshooting Case Study

## Incident summary

A Fedora workstation experienced intermittent network instability during latency-sensitive online gaming. Baseline connectivity looked healthy, but short latency spikes were noticeable in Counter-Strike 2 (CS2). The objective was to isolate whether the problem originated in the ISP/WAN path, the router, Ethernet/LAN, the Wi-Fi link, or the Linux wireless power-management configuration.

The investigation identified a strong relationship between Wi-Fi power saving and the observed instability. Disabling wireless power saving produced a clear subjective improvement and materially reduced high-percentile LAN latency and worst-case spikes. The setting was then made persistent with NetworkManager and verified after a system reboot.

This case study documents the troubleshooting process rather than claiming a hardware defect in the wireless adapter.

## Environment

- OS: Fedora Linux
- Laptop: Lenovo Legion 5 15ACH6H
- WLAN interface: `wlp4s0`
- WLAN adapter: Realtek RTL8852AE 802.11ax PCIe
- PCI ID: `10ec:8852`
- Lenovo subsystem: `17aa:4852`
- Kernel driver: `rtw89_8852ae`
- Ethernet interface: `eno1`
- Router/LAN gateway used for testing: `192.168.50.1`
- External test endpoint: Cloudflare `1.1.1.1`
- Workload: Counter-Strike 2

Adapter/driver identification:

```bash
lspci -nnk | grep -A4 -Ei 'network|wireless'
```

Observed relevant output:

```text
04:00.0 Network controller [0280]: Realtek Semiconductor Co., Ltd. RTL8852AE 802.11ax PCIe Wireless Network Adapter [10ec:8852]
    Subsystem: Lenovo Device [17aa:4852]
    Kernel driver in use: rtw89_8852ae
    Kernel modules: rtw89_8852ae
```

## Symptoms and initial clue

The primary symptom was intermittent network instability perceived during CS2 gameplay rather than consistently high latency or sustained packet loss.

An important observation was that keeping a continuous ping running appeared to make the connection more stable. That suggested that continuous traffic might be preventing the wireless interface from entering or transitioning through a low-power state.

The wireless power-save state was therefore checked:

```bash
iw dev wlp4s0 get power_save
```

Initial state:

```text
Power save: on
```

## Diagnostic methodology

The investigation used controlled A/B comparisons rather than immediately replacing hardware.

Two destinations were monitored simultaneously:

```bash
ping -D -i 0.2 192.168.50.1 | tee ~/ping-router-cs2.log
ping -D -i 0.2 1.1.1.1 | tee ~/ping-internet-cs2.log
```

The local gateway measurement was used to observe the laptop-to-router path. The external endpoint measurement was used to observe the end-to-end path beyond the router.

Three relevant configurations were compared:

1. Wi-Fi with power saving enabled.
2. Ethernet as a control path.
3. Wi-Fi with power saving disabled.

The comparison focused on packet loss, median latency, P95/P99 latency and maximum observed latency rather than relying only on averages.

## Results

### Wi-Fi — Power Save ON

Local gateway (`192.168.50.1`):

- replies: 5,364
- inferred packet loss: 0%
- average: ~1.32 ms
- median: ~1.12 ms
- P95: ~1.76 ms
- P99: ~5.62 ms
- maximum: 41.9 ms

External endpoint (`1.1.1.1`):

- replies: 5,333
- inferred packet loss: 0%
- average: ~11.40 ms
- median: ~11.3 ms
- P95: ~12.0 ms
- P99: ~15.0 ms
- maximum: 61.6 ms

The baseline was good, but the local wireless path contained occasional high-latency outliers.

### Ethernet control

Fedora selected Ethernet because it had the lower route metric:

```text
default via 192.168.50.1 dev eno1 ... metric 100
default via 192.168.50.1 dev wlp4s0 ... metric 600
```

For a clean control test, Wi-Fi was disabled and the same measurements were repeated over `eno1`.

Local gateway:

- replies: 3,218
- inferred packet loss: 0%
- average: ~0.47 ms
- median: ~0.45 ms
- P95: ~0.58 ms
- P99: ~0.78 ms
- maximum: 15.3 ms

External endpoint:

- replies: 3,288
- inferred packet loss: 0%
- average: ~10.28 ms
- median: ~10.4 ms
- P95: ~10.7 ms
- P99: ~11.4 ms
- maximum: 17.2 ms

The Ethernet control was highly stable. This reduced the likelihood that the router, ISP connection, or the laptop's general networking stack was the primary source of the observed gameplay issue.

### Wi-Fi — Power Save OFF

Power saving was temporarily disabled:

```bash
sudo iw dev wlp4s0 set power_save off
iw dev wlp4s0 get power_save
```

Expected/observed state:

```text
Power save: off
```

The user also reported a clear subjective improvement in CS2 with power saving disabled.

The measurement was then repeated.

Local gateway:

- replies: 2,795
- inferred packet loss: 0%
- average: ~1.20 ms
- median: ~1.11 ms
- P95: ~1.70 ms
- P99: ~2.55 ms
- maximum: 8.96 ms

External endpoint:

- replies: 2,750
- inferred packet loss: 0%
- average: ~10.87 ms
- median: ~10.6 ms
- P95: ~11.5 ms
- P99: ~12.6 ms
- maximum: 60.9 ms
- only three samples exceeded 20 ms

## Comparison

| Test | LAN median | LAN P95 | LAN P99 | LAN max | Packet loss |
|---|---:|---:|---:|---:|---:|
| Wi-Fi, Power Save ON | ~1.12 ms | ~1.76 ms | ~5.62 ms | 41.9 ms | 0% |
| Wi-Fi, Power Save OFF | ~1.11 ms | ~1.70 ms | ~2.55 ms | 8.96 ms | 0% |
| Ethernet | ~0.45 ms | ~0.58 ms | ~0.78 ms | 15.3 ms | 0% |

Disabling Wi-Fi power saving did not materially change the already-good median latency. The more important change was in the tail of the latency distribution:

- LAN P99 decreased from ~5.62 ms to ~2.55 ms, approximately a 55% reduction.
- Maximum observed LAN latency decreased from 41.9 ms to 8.96 ms, approximately a 79% reduction.
- No packet loss was observed in either Wi-Fi configuration.

This is consistent with a latency-spike problem rather than a throughput or persistent packet-loss problem.

## Root-cause assessment

The evidence supports a Wi-Fi power-management/driver interaction as the most likely cause of the observed instability in this environment.

The evidence chain was:

1. The normal Wi-Fi baseline was fast but contained occasional local latency spikes.
2. Continuous traffic appeared to improve perceived stability.
3. Wi-Fi power saving was confirmed to be enabled.
4. Disabling power saving produced a clear subjective improvement in CS2.
5. Ethernet provided a stable control path, reducing suspicion of the WAN/router path.
6. Wi-Fi measurements with power saving disabled showed substantially better P99 and worst-case local latency.
7. The remediation remained effective after reconnecting and after rebooting Fedora.

This does **not** establish that the Realtek RTL8852AE hardware is defective. A more precise conclusion is that, on this Fedora system using `rtw89_8852ae`, the enabled WLAN power-saving behavior correlated strongly with latency instability under this latency-sensitive workload.

## Measurement limitation

The ICMP measurement itself is an important confounding factor.

The tests used:

```bash
ping -D -i 0.2 ...
```

This generates traffic every 200 ms. Because the original symptom appeared to improve when continuous ping traffic was present, the measurement traffic may itself have kept the wireless radio active and reduced the effect being investigated.

Therefore, the ping comparison may **understate** the real difference between Power Save ON and OFF during normal gameplay. It should not be treated as laboratory proof of a kernel/driver defect.

The strongest evidence is the combined A/B result: the gameplay behavior changed when power saving was disabled, Ethernet was stable as a control, and the measured Wi-Fi tail latency improved after the configuration change.

## Remediation

The fix was first tested temporarily with `iw`. After successful validation, it was made persistent for the active NetworkManager Wi-Fi profile.

The connection profile was identified with:

```bash
nmcli connection show
```

Power saving was disabled persistently for that profile:

```bash
sudo nmcli connection modify "Orange_światłowód_5GHz" 802-11-wireless.powersave 2
```

The stored value was verified:

```bash
nmcli -f 802-11-wireless.powersave connection show "Orange_światłowód_5GHz"
```

Result:

```text
802-11-wireless.powersave: 2 (disable)
```

The connection was then reactivated:

```bash
sudo nmcli connection down "Orange_światłowód_5GHz"
sudo nmcli connection up "Orange_światłowód_5GHz"
```

Runtime state:

```bash
iw dev wlp4s0 get power_save
```

Result:

```text
Power save: off
```

## Post-reboot validation

The laptop was rebooted to confirm that the fix was persistent rather than only affecting the current session.

After reboot:

```bash
iw dev wlp4s0 get power_save
```

Result:

```text
Power save: off
```

This completed remediation validation.

## Decision on hardware replacement

An Intel AX210 had been considered as a possible replacement adapter. The controlled troubleshooting showed that replacing the WLAN card was not justified at this stage: the existing RTL8852AE became stable for the observed workload after correcting the power-management configuration.

The hardware upgrade was therefore deferred rather than used as the first troubleshooting step.

## Lessons learned

- Separate the local WLAN/LAN path from the WAN path during latency troubleshooting.
- Use Ethernet as a control before blaming the ISP or router.
- Inspect high-percentile and worst-case latency; averages can hide short spikes that affect real-time applications.
- Treat power management as a first-class troubleshooting variable on mobile Linux systems.
- Validate a suspected fix both subjectively under the original workload and quantitatively.
- Verify persistence after reconnect and reboot.
- Document measurement limitations and avoid presenting correlation as stronger proof than the experiment supports.

## Outcome

**Status: resolved.**

Wi-Fi power saving was disabled persistently through NetworkManager. The runtime state remained `Power save: off` after reboot, gameplay behavior improved, and the measured local tail latency was substantially reduced. No WLAN hardware replacement was required.