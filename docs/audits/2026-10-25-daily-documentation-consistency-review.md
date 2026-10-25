# October 25 engineering documentation — scoped consistency audit

> **Audit date:** 2026-10-25. **Evidence:** public GitHub merged PRs/source documents and *operator-reported* Fedora/ASUS results reflected in the dated logs. **Scope:** October 25 worklog and navigation, current-state declarations and dated HCC project texts; cross-check with the independent private Polish journal (no private details reproduced). **Mode:** documentation-only review; no live SSH/router/Fedora access, system changes or new test acceptance.
>
> **Publication status:** this audit and its corrections are proposed on a **Draft documentation PR**. They are not yet an accepted/merged public chronology until reviewed.

## 1. Documents and evidence reviewed

- [Public engineering worklog](../worklog/2026-10-25.md) and [timeline index](../worklog/README.md); corresponding private Polish October 25 worklog and its README, index and daily guide (checked in the connected private repository, **not mirrored**).
- [Project status](../../PROJECT-STATUS.md), [changelog](../../CHANGELOG.md), [V0.1 HCC initial architecture](../design/homelab-control-center-v0.1-architecture-2026-10-25.md), [V0.2 Fedora-local reader contract](../../experiments/fedora/homelab-control-center-v0.1/V0.2-LOCAL-LIVE-LAB.md) and [local Caddy/HTTPS activation record](../design/homelab-control-center-local-https-alias-2026-10-25.md).
- Merged HCC PRs [#305](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/305), [#306](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/306), [#307](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/307), [#308](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/308); client contract [#309](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/309); WebUI [#310](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/310). [Issue #303](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/303) remains open; [#304 Black Box](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/304) is a separate research gate.
- CI sources: [#309 validation](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/actions/runs/40226271420) and [#310 validation](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/actions/runs/40227125947) succeeded on their tested commits. CI cannot verify subsequent operator-controlled local activation.

## 2. Findings and disposition

| Priority | Finding | Resolution in this documentation review |
| --- | --- | --- |
| High | The first October 25 public worklog amendment included Fedora Recovery, #289, #283 and ASUS WebUI, but **omitted merged HCC PRs #305–#308** and separately authorized Fedora-local HTTPS activation. | Added separate worklog sections for HCC architecture, V0.1/V0.2, local 7/7 VictoriaMetrics observation, Caddy/hosts change and operator's browser report, with explicit test limits. |
| High | The top of `PROJECT-STATUS.md` was **dated October 24** and called Unbound the latest ASUS production change; the later **WebUI-only** publish was not represented. | Advanced the dated status to October 25 while retaining October 24 Unbound as the **latest DNS-specific** production change. All unrelated router security gates remain HOLD. |
| Medium | The initial HCC design document still displayed **PLANNED / no implementation** and the V0.2 runbook broadly disallowed Caddy publishing. These were accurate **historical pre-activation gates** but misleading as unqualified *current* statements. | Added dated supersession notes for merged V0.1/V0.2 and the narrow **loopback-only existing-Caddy** exception. This does **not** approve LAN/Tailscale/WAN exposure or HCC service autostart. |
| Medium | `CHANGELOG.md` had no October 25 entries despite merged PRs and real bounded local/ASUS activations. | Added event- and surface-specific release-history entries: Fedora maintenance/Recovery, HCC #303, client #289, WebUI #283. |
| Medium | The private Polish October 25 journal had a subsequently appended **local AI agent V0.17.3 laboratory** section, while its earlier introduction and summary still described a two-stage day. The HCC stream was absent from the day-level summary. | Reconciled the private journal as *thematic workstreams*, added a separate HCC/HTTPS section, a final accepted/HOLD summary, and refreshed three Polish navigation entries. AI laboratory details remain private, separated from actual production changes. |
| Medium | The initial #283 issue closure explicitly recorded **source fix only / no ASUS deployment**. Later operator evidence established a *separately approved* on-router WebUI-only deployment. | Both phases are preserved rather than silently rewriting history. The worklog/status clarify later approval, V1 preflight HOLD, firmware `/www/user` link, verified backup, V2 publish and read-only live postflight. |
| Low | Numerous independent “PASS” claims risk conflating CI, synthetic fixtures, Fedora-local tests, source build, proxy reachability and live router service health. | Wording distinguishes all those evidence types, and records missing end-to-end browser/API, reboot durability, long soak and complete disaster-recovery gates explicitly. |

## 3. Evidence boundaries not to erase

- **ASUS WebUI #283:** published only the JFFS status script, JFFS source ASP and active ASP page. Operator-reported `ISSUE283_DEPLOYMENT=PASS`, byte-parity PASS, and `SNAPSHOT_AGE_SECONDS=19` with freshness/admin count/active ASP checks PASS. The snapshot age is a **point measurement**. No claim of a browser screenshot, full rendering, cold reboot, security pen test or long-duration service availability.
- **Writable temporary ancestor:** `/www/user` points to firmware `/tmp/var/wwwext`; bounded V2 trusted-path gate accepted that known structure while still reporting writable `/tmp` as an **unresolved threat-model caveat**. Avoid treating this as general permission to follow untrusted symlinks or deploy SSD/JFFS security helpers.
- **HCC Fedora-local alias:** `control.home.arpa` activation affected **only workstation** hosts/Caddy and reloaded Caddy. The operator reported HTTP SNI success and working local browser address. That is distinct from a persistent HCC installation, endpoint authentication, independent certificate UI verification, live `/api/summary` browser fetch acceptance and LAN/Tailscale access. HCC #303 and Black Box #304 remain open/HOLD.
- **Fedora Recovery:** actual isolated Btrfs `root` receive and encrypted Restic content check succeeded; no booted-OS restore, full `/home` recovery or accepted SELinux metadata restoration. Fedora Tailscale's post-package-migration reboot persistence remains untested.
- **Client/health fixtures #289:** 17 offline checks and source warning semantics do not verify real network access, DNS Guard failover or complete alert delivery.
- **Private/public boundary:** synthetic OpenCode/Ollama/rootless Podman agent tests V0.17.3 were documented privately with V0.18 HOLD. They are **not** ASUS production implementation or new public product functionality; no private operational output was copied into the public report.

## 4. Change and review checklist

- [x] Reconcile dated/merged HCC vs. WebUI chronological scope in the public worklog.
- [x] Correct current-state date and distinctions: router WebUI vs. DNS services vs. Fedora HTTPS.
- [x] Remove misleading *current* implications from historically accurate HCC design/runner gates.
- [x] Extend public changelog and worklog navigation.
- [x] Keep private Polish journal and its indexes consistent without publishing raw private records.
- [x] Preserve known HOLD gates and observed failures; do not promote synthetic tests into production evidence.
- [ ] Public review and final PR CI after **this** doc amendment; do not auto-merge.
- [ ] Independent browser/API/certificate, long-soak and post-reboot acceptance where appropriate (not executed by this audit).

**Outcome:** the identified date-specific contradictions were corrected **in documentation only**. This is a scoped consistency audit, not a complete code/security review, a full Markdown repository link crawler or new authorization for production operations.
