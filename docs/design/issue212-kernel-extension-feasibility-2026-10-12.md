# Issue #212 — ASUS kernel-extension feasibility review (2026-10-12)

**Decision: RESEARCH/OFF-ROUTER CONFIGURATION GATE ONLY; production kernel replacement NOT APPROVED.**
This note records public source inspection plus operator-provided read-only ASUS data. No build or module load, no firmware image generated, and no hardware tested.

> **Supersession note (2026-10-13):** The RT-BE88U is no longer a planned purchase/migration target under the [2026-10-12 platform decision](../architecture/platform-direction-2026-10-12.md). RT-BE88U kernel-profile observations below are **historical source-feasibility evidence**, not a proposed production kernel update or new router plan. All #212 client-DNS experiments remain off-router.

## Goal and risk boundary

Assess whether enabling `CONFIG_NET_NS`, `CONFIG_VETH`, `CONFIG_NETFILTER_XT_TARGET_TPROXY` and `CONFIG_NETFILTER_XT_MATCH_SOCKET` could support the optional private DNS sidecar experiments of [Issue #212](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212).

The **v0.41 selected-client direct sidecar-gateway bypass remains a blocker even if all kernel features are added**. A kernel-feature experiment is not equivalent to a secure client-DNS failover.

## Public upstream source findings (inspectable paths)

### TUF-AX5400 / current production

- Read-only operator check: `uname -r=4.1.52`, `armv7l`, `iptables 1.4.15`, `/proc/self/ns/net` absent, no visible `veth`/`xt_TPROXY`/`xt_socket`, `/proc/config.gz` unavailable; `nf_conntrack` present, DNAT/MARK/REDIRECT targets registered.
- GNUton's Broadcom 963178 target profile selects `LINUX_4_1_0=y`: [target profile](https://github.com/gnuton/asuswrt-merlin.ng/blob/master/release/src-rt-5.02axhnd.675x/targets/963178GW/963178GW).
- Negative `/proc`/`sys/module` inventory is a strong deployment warning, **not** an independently verified final `.config` or a safe authorization to load modules.
- Practical benefit of custom kernel work on this **current production gateway** is low relative to bricking, closed-driver/ABI, stability and maintenance costs. **NO-GO for live experiments**.

### RT-BE88U / historical candidate (migration cancelled)

- Official RMerl model target profile: Broadcom `BRCM_CHIP=6813`, `PROFILE_KARCH=aarch64`, `PROFILE_ARCH=armsfp`, `LINUX_4_19_0=y`: [RT-BE88U 96813GW profile](https://github.com/RMerl/asuswrt-merlin.ng/blob/main/release/src-rt-5.04behnd.4916/targets/96813GW/96813GW.RT-BE88U). **Kernel and userspace architecture can differ**; do not assume 64-bit userspace from aarch64 kernel target.
- The repository's generic `arch/arm64/configs/defconfig` declares `CONFIG_VETH=m` and `CONFIG_USER_NS=y`: [generic ARM64 defconfig](https://github.com/RMerl/asuswrt-merlin.ng/blob/main/release/src-rt-5.04behnd.4916/kernel/linux-4.19/arch/arm64/configs/defconfig). **Generic ≠ RT-BE88U shipped .config**; neither `CONFIG_NET_NS` nor production VETH presence has been established by this observation.
- Broadcom's [OpenSync generator](https://github.com/RMerl/asuswrt-merlin.ng/blob/main/release/src-rt-5.04behnd.4916/hostTools/scripts/gendefconfig.d/50opensync.conf) explicitly sets `CONFIG_VETH=y` and `CONFIG_NETFILTER_XT_TARGET_TPROXY=m` for `BUILD_OPENSYNC_GW`; alternate OpenSync mode enables TPROXY built-in. The RT-BE88U model profile says **`# BUILD_OPENSYNC is not set`**. Thus these lines prove *source-level configuration support under an optional feature*, **not** inclusion in the RT-BE88U firmware.
- [Merlin build Makefile](https://github.com/RMerl/asuswrt-merlin.ng/blob/main/release/src-rt/Makefile) handles `EXTRA_KERNEL_CONFIGS` (y/n/m flags and `extraKernelConfig`); it suggests offline kernel-config experimentation is possible. Whether all required objects can link with the precise RT-BE88U SDK and prebuilt Broadcom modules is **UNTESTED**.
- The Asuswrt-Merlin author describes Wi-Fi 7 platform kernels as 4.19 family and points out the SDK/patch dependence: [SNBForums primary-developer discussion](https://www.snbforums.com/threads/about-the-linux-kernel-version-of-the-firmware-of-asus-wifi-7-router.88502/).
- Proprietary Wi-Fi components depend on Broadcom SDK and may not support kernel version changes: [RMerlin response on wireless driver/SDK compatibility](https://www.snbforums.com/threads/can-we-load-different-versions-of-wireless-drivers-on-boot.83436/).

## Feature acceptance matrix

| Requirement | TUF-AX5400 observed | RT-BE88U public sources | Decision |
|---|---|---|---|
| `CONFIG_NET_NS=y` | netns handle absent, final config unknown | feature part of kernel source; final RT-BE88U config **unknown** | Must establish config before any build |
| `CONFIG_VETH=y/m` | module not visible | generic defconfig `m`; OpenSync conditional `y`, default RT-BE88U profile OpenSync disabled | Source-capable, deployed unknown |
| `CONFIG_NETFILTER_XT_TARGET_TPROXY=y/m` | not visible | Kconfig and conditional OpenSync support; final config unknown | Source-capable, deployed unknown |
| `CONFIG_NETFILTER_XT_MATCH_SOCKET=y/m` | not visible | Kconfig source option exists; final config unknown | Source-capable, deployed unknown |
| Broadcom proprietary Wi-Fi, packet acceleration and WAN | production baseline works | proprietary/sdk dependencies | Must protect in every experiment |
| Stable source-scoped client DNS failover | **NOT DEPLOYED** | no independent resolver/wire-level failover proved | Explicitly separate from kernel research |

## Staged decision (no production changes)

**Gate A — offline read-only source baseline (now):**
1. Pin exact Merlin source commit and exact RT-BE88U release/SDK target, not generic `main` alone.
2. Reproduce *final generated kernel `.config` for that model* and Kconfig dependency resolution, with unchanged baseline. Verify `CONFIG_NAMESPACES`, `CONFIG_NET_NS`, `CONFIG_VETH`, `CONFIG_NETFILTER_XT_TARGET_TPROXY`, `CONFIG_NETFILTER_XT_MATCH_SOCKET`, routing/mangle/NAT and necessary loading tools.
3. Inventory modules, signing/vermagic, SDK-only objects/closed drivers and image/partition sizes. Preserve explicit original rollback artifact.

**Gate B — optional off-router build research (not yet done):**
4. Try *same kernel version and SDK* source-only config diff and compile as a separate disposable variant; confirm critical vendor modules, Wi-Fi/WAN kernel interfaces and ABI remain viable. Do not equate a successful `make` with a deployable or safe firmware.
5. Do not try on production router; only consider a **separately authorized spare-device** experiment with physical recovery mechanism and independent Internet fallback, if benefits justify it.

**Gate C — client DNS design (independent of kernel):**
6. First eliminate v0.41 direct-gateway bypass with exact packet-origin restrictions or a transport that has no exposed gateway. Prove LAN/Tailnet selected/unselected UDP/TCP, no private-name/PTR leakage, DNSSEC, Pi-hole and Unbound outage separately, conntrack failback and uncoordinated INPUT reset; still OFF-ROUTER.
7. Prefer a truly independent DNS resolver/host design using verified router DNAT/REDIRECT if the custom-kernel cost exceeds benefit. This will not survive the physical ASUS outage if clients depend on its routing.

## Cost/benefit recommendation

- **TUF-AX5400 kernel change:** **NO-GO** on the production device. High risk; only marginal Issue #212 value.
- **RT-BE88U offline config/build research:** **CONDITIONAL GO**; source-level knobs exist, hardware capacity is better, final feature inclusion/ABI remains unproven.
- **RT-BE88U production custom kernel:** **NO-GO until separate approval after Gate A+B and a spare-device validation**. All usual firmware updates could require rebuilding and retesting the kernel and vendor modules.
- **Linux 6.x rebase:** **NO-GO**: Broadcom SDK/Wi-Fi/SoC coupling makes an entire kernel family jump a platform-porting project rather than simply turning on netns.

**No changes made to `main`, running ASUS services, firmware, routes, DNS, sysctls, Tailscale or iptables.** This is a documentation-only feasibility note on draft PR #227. Issue #212 remains **OPEN**.
