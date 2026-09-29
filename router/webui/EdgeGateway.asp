<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<!-- ASUS-EDGE-WEBUI: project-native read-only operational dashboard -->
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="X-UA-Compatible" content="IE=Edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="-1" />
  <link rel="shortcut icon" href="images/favicon.png" />
  <link rel="icon" href="images/favicon.png" />
  <title>Edge Gateway</title>
  <link rel="stylesheet" type="text/css" href="index_style.css" />
  <link rel="stylesheet" type="text/css" href="form_style.css" />

  <script type="text/javascript" src="/js/jquery.js"></script>
  <script type="text/javascript" src="/state.js"></script>
  <script type="text/javascript" src="/general.js"></script>
  <script type="text/javascript" src="/popup.js"></script>
  <script type="text/javascript" src="/help.js"></script>
  <script type="text/javascript" src="/detect.js"></script>

  <style type="text/css">
    .edge-ok { color:#7fff7f; font-weight:bold; }
    .edge-bad { color:#ff8080; font-weight:bold; }
    .edge-muted { color:#b8c4cc; }
    .edge-warn { color:#ffd27f; font-weight:bold; }
    .edge-note {
      margin:10px 0 15px 5px;
      padding:10px;
      border:1px solid #596b75;
      background:#2f3b43;
      color:#d8e2e8;
    }
    .edge-nav {
      margin:10px 0 15px 5px;
      line-height:28px;
    }
    .edge-nav a {
      display:inline-block;
      margin:0 6px 6px 0;
      padding:3px 9px;
      border:1px solid #596b75;
      background:#25313a;
      color:#d8e2e8;
      text-decoration:none;
    }
    .edge-section-anchor {
      position:relative;
      top:-10px;
    }
  </style>

  <script type="text/javascript">
    function edgeServiceState(pid) {
      return (parseInt(pid, 10) > 0)
        ? '<span class="edge-ok">Running</span>'
        : '<span class="edge-bad">Stopped</span>';
    }

    function edgeBooleanState(value, enabledText, disabledText) {
      if (String(value) === "1")
        return '<span class="edge-ok">' + enabledText + '</span>';
      if (String(value) === "0")
        return '<span class="edge-muted">' + disabledText + '</span>';
      return '<span class="edge-muted">Unknown</span>';
    }

    function edgeSnapshotBoolean(value, yesText, noText) {
      return Number(value) === 1
        ? '<span class="edge-ok">' + yesText + '</span>'
        : '<span class="edge-muted">' + noText + '</span>';
    }

    function edgeRequiredState(value) {
      return Number(value) === 1
        ? '<span class="edge-ok">Present</span>'
        : '<span class="edge-bad">Missing</span>';
    }

    function edgeRunningState(value) {
      return Number(value) === 1
        ? '<span class="edge-ok">Running</span>'
        : '<span class="edge-bad">Stopped</span>';
    }

    function edgeSchedulerState(value) {
      return Number(value) === 1
        ? '<span class="edge-ok">Scheduled</span>'
        : '<span class="edge-bad">Missing</span>';
    }

    function edgeWanWebuiState(value) {
      if (String(value) === "0")
        return '<span class="edge-ok">Disabled</span>';
      if (String(value) === "1")
        return '<span class="edge-bad">Enabled</span>';
      return '<span class="edge-muted">Unknown</span>';
    }

    function edgeUnboundRuntimeState(value) {
      return String(value) === "running"
        ? '<span class="edge-ok">Running</span>'
        : '<span class="edge-bad">Stopped / unavailable</span>';
    }

    function edgeNumber(value) {
      var number = Number(value);
      if (!isFinite(number))
        return "N/A";
      return String(Math.round(number));
    }

    function edgePercent(hits, misses) {
      var hitCount = Number(hits);
      var missCount = Number(misses);
      var total = hitCount + missCount;
      if (!isFinite(total) || total <= 0)
        return "N/A";
      return ((hitCount / total) * 100).toFixed(1) + "%";
    }

    function edgeMilliseconds(seconds) {
      var value = Number(seconds);
      if (!isFinite(value))
        return "N/A";
      return (value * 1000).toFixed(1) + " ms";
    }

    function edgeDuration(seconds) {
      var remaining = Math.floor(Number(seconds));
      if (!isFinite(remaining) || remaining < 0)
        return "N/A";

      var days = Math.floor(remaining / 86400);
      remaining %= 86400;
      var hours = Math.floor(remaining / 3600);
      remaining %= 3600;
      var minutes = Math.floor(remaining / 60);
      var secs = remaining % 60;
      var parts = [];

      if (days) parts.push(days + " d");
      if (hours || days) parts.push(hours + " h");
      if (minutes || hours || days) parts.push(minutes + " min");
      parts.push(secs + " s");
      return parts.join(" ");
    }

    function edgeMiB(kib) {
      var value = Number(kib);
      if (!isFinite(value))
        return "N/A";
      return (value / 1024).toFixed(1) + " MiB";
    }

    function edgeGiB(kib) {
      var value = Number(kib);
      if (!isFinite(value))
        return "N/A";
      return (value / 1048576).toFixed(1) + " GiB";
    }

    function edgeStorage(used, total, percent) {
      var totalKiB = Number(total);
      if (!isFinite(totalKiB))
        return "N/A";

      var formatter = totalKiB < 1048576 ? edgeMiB : edgeGiB;
      return formatter(used) + " / " + formatter(total) + " (" + edgeNumber(percent) + "%)";
    }

    function SetCurrentPage() {
      if (document.form) {
        if (document.form.next_page)
          document.form.next_page.value = window.location.pathname.substring(1);
        if (document.form.current_page)
          document.form.current_page.value = window.location.pathname.substring(1);
      }
    }

    function setText(id, value) {
      var element = document.getElementById(id);
      if (element)
        element.innerHTML = value;
    }

    function renderGatewaySnapshot() {
      var data = window.edgeGatewayStatus;
      if (!data) {
        setText("edge_snapshot", '<span class="edge-bad">Snapshot unavailable</span>');
        return;
      }

      var system = data.system || {};
      var services = data.services || {};
      var tailscale = data.tailscale || {};
      var policy = data.policy || {};
      var firewall = data.firewall || {};
      var unbound = data.unbound || {};

      setText("edge_snapshot", '<span class="edge-ok">Loaded</span>');
      setText("edge_generated", data.generated || "N/A");

      setText("edge_system_uptime", edgeDuration(system.uptime));
      setText("edge_system_load", edgeNumber(system.load1 * 100) / 100 + " / " +
        edgeNumber(system.load5 * 100) / 100 + " / " + edgeNumber(system.load15 * 100) / 100);
      setText("edge_system_memory", edgeMiB(system.memUsedKiB) + " / " + edgeMiB(system.memTotalKiB));
      setText("edge_system_swap", edgeMiB(system.swapUsedKiB) + " / " + edgeMiB(system.swapTotalKiB) +
        " (" + edgeNumber(system.swapDevices) + " device(s))");
      setText("edge_system_opt", edgeStorage(system.optUsedKiB, system.optTotalKiB, system.optUsedPct));
      setText("edge_system_jffs", edgeStorage(system.jffsUsedKiB, system.jffsTotalKiB, system.jffsUsedPct));

      setText("edge_svc_tailscale", edgeRunningState(services.tailscaled));
      setText("edge_svc_unbound", edgeRunningState(services.unbound));
      setText("edge_svc_dnsmasq", edgeRunningState(services.dnsmasq));
      setText("edge_svc_pihole", edgeRunningState(services.piholeFtl));
      setText("edge_svc_syslog", edgeRunningState(services.syslogNg));
      setText("edge_svc_scheduler", edgeSchedulerState(services.scheduler));
      setText("edge_dns_pihole", edgeRunningState(services.piholeFtl));

      setText("edge_ts_version", tailscale.version || "N/A");
      setText("edge_ts_connected", edgeSnapshotBoolean(tailscale.connected, "Connected", "Disconnected"));
      setText("edge_ts_peers", edgeNumber(tailscale.peers));
      setText("edge_ts_active", edgeNumber(tailscale.activePeers));
      setText("edge_ts_direct", edgeNumber(tailscale.directPeers));
      setText("edge_ts_offline", edgeNumber(tailscale.offlinePeers));
      setText("edge_ts_exit_offered", edgeSnapshotBoolean(tailscale.exitNodeOffered, "Advertised", "Not advertised"));
      setText("edge_ts_netfilter", edgeSnapshotBoolean(policy.projectOwnsNetfilter, "Project-owned", "Tailscale-managed"));

      setText("edge_policy_intercept_dns", edgeSnapshotBoolean(policy.interceptDns, "Enabled", "Disabled"));
      setText("edge_policy_lan_dns", edgeSnapshotBoolean(policy.enforceLanDns, "Enabled", "Disabled"));
      setText("edge_policy_dot", edgeSnapshotBoolean(policy.blockLanDot, "Blocked", "Allowed"));
      setText("edge_policy_exit", edgeSnapshotBoolean(policy.exitNodeEnabled, "Enabled", "Disabled"));
      setText("edge_policy_https", edgeSnapshotBoolean(policy.routerHttps, "Allowed", "Denied"));
      setText("edge_policy_ssh", edgeSnapshotBoolean(policy.routerSsh, "Allowed", "Denied"));
      setText("edge_policy_admins", edgeNumber(policy.adminSourceCount));
      setText("edge_policy_printer", edgeSnapshotBoolean(policy.printerPolicy, "Configured", "Not configured"));

      setText("edge_fw_input_chain", edgeRequiredState(firewall.tsInputChain));
      setText("edge_fw_forward_chain", edgeRequiredState(firewall.tsForwardChain));
      setText("edge_fw_nat_chain", edgeRequiredState(firewall.tsPreroutingChain));
      setText("edge_fw_lan_dns_chain", edgeRequiredState(firewall.lanDnsChain));
      setText("edge_fw_lan_dot_chain", edgeRequiredState(firewall.lanDotChain));
      setText("edge_fw_ipv6_input_chain", edgeRequiredState(firewall.ipv6InputChain));
      setText("edge_fw_ipv6_forward_chain", edgeRequiredState(firewall.ipv6ForwardChain));
      setText("edge_fw_input_accept", edgeNumber(firewall.inputAcceptPackets));
      setText("edge_fw_input_log", edgeNumber(firewall.inputLogPackets));
      setText("edge_fw_input_drop", edgeNumber(firewall.inputDropPackets));
      setText("edge_fw_forward_accept", edgeNumber(firewall.forwardAcceptPackets));
      setText("edge_fw_forward_log", edgeNumber(firewall.forwardLogPackets));
      setText("edge_fw_forward_drop", edgeNumber(firewall.forwardDropPackets));
      setText("edge_fw_dns_bypass", edgeNumber(firewall.lanDnsBypassPackets));
      setText("edge_fw_dns_redirect", edgeNumber(firewall.lanDnsRedirectPackets));
      setText("edge_fw_dot_reject", edgeNumber(firewall.lanDotRejectPackets));
      setText("edge_fw_ipv6_input_drop", edgeNumber(firewall.ipv6InputDropPackets));
      setText("edge_fw_ipv6_forward_drop", edgeNumber(firewall.ipv6ForwardDropPackets));

      setText("edge_unbound_snapshot", edgeUnboundRuntimeState(unbound.status));
      setText("edge_unbound_version", unbound.version || "N/A");
      setText("edge_unbound_listener", unbound.interface || ("127.0.0.1@" + unbound.port));
      setText("edge_unbound_uptime", edgeDuration(unbound.uptime));
      setText("edge_unbound_queries", edgeNumber(unbound.queries));
      setText("edge_unbound_cachehits", edgeNumber(unbound.cachehits));
      setText("edge_unbound_cachemiss", edgeNumber(unbound.cachemiss));
      setText("edge_unbound_hitratio", edgePercent(unbound.cachehits, unbound.cachemiss));
      setText("edge_unbound_servfail", edgeNumber(unbound.servfail));
      setText("edge_unbound_secure", edgeNumber(unbound.secure));
      setText("edge_unbound_bogus", edgeNumber(unbound.bogus));
      setText("edge_unbound_prefetch", edgeNumber(unbound.prefetch));
      setText("edge_unbound_expired", edgeNumber(unbound.expired));
      setText("edge_unbound_recavg", edgeMilliseconds(unbound.recursionAvg));
      setText("edge_unbound_recmedian", edgeMilliseconds(unbound.recursionMedian));
      setText("edge_unbound_generated", data.generated || "N/A");
    }

    function loadGatewaySnapshot() {
      $.ajax({
        url: "/ext/asus-edge/status.js?_=" + new Date().getTime(),
        dataType: "script",
        cache: false,
        timeout: 3000,
        success: renderGatewaySnapshot,
        error: function() {
          setText("edge_snapshot", '<span class="edge-bad">Snapshot unavailable</span>');
          setText("edge_unbound_snapshot", '<span class="edge-muted">Snapshot unavailable</span>');
        }
      });
    }

    function refreshEdgeStatus() {
      document.getElementById("edge_unbound").innerHTML =
        edgeServiceState("<% sysinfo("pid.unbound"); %>");
      document.getElementById("edge_dnsmasq").innerHTML =
        edgeServiceState("<% sysinfo("pid.dnsmasq"); %>");
      document.getElementById("edge_tailscale").innerHTML =
        edgeServiceState("<% sysinfo("pid.tailscaled"); %>");

      document.getElementById("edge_wan_webui").innerHTML =
        edgeWanWebuiState("<% nvram_get("misc_http_x"); %>");
      document.getElementById("edge_access_restriction").innerHTML =
        edgeBooleanState("<% nvram_get("enable_acc_restriction"); %>", "Enabled", "Disabled");

      loadGatewaySnapshot();
    }

    function initial() {
      refreshEdgeStatus();

      try {
        show_menu();
      }
      catch (error) {
        if (window.console && console.error)
          console.error("ASUS Edge: show_menu() failed", error);
      }

      SetCurrentPage();
    }
  </script>
</head>

<body onload="initial();" class="bg">
  <div id="TopBanner"></div>
  <div id="Loading" class="popup_bg"></div>

  <form method="post" name="form" action="">
    <input type="hidden" name="current_page" value="" />
    <input type="hidden" name="next_page" value="" />
    <input type="hidden" name="group_id" value="" />
    <input type="hidden" name="modified" value="0" />
    <input type="hidden" name="first_time" value="" />
    <input type="hidden" name="preferred_lang" id="preferred_lang"
           value="<% nvram_get("preferred_lang"); %>" />
    <input type="hidden" name="firmver" value="<% nvram_get("firmver"); %>" />

  <table class="content" align="center" cellpadding="0" cellspacing="0">
    <tr>
      <td width="17">&nbsp;</td>
      <td valign="top" width="202">
        <div id="mainMenu"></div>
        <div id="subMenu"></div>
      </td>
      <td valign="top">
        <div id="tabMenu" class="submenuBlock"></div>

        <table width="98%" border="0" align="left" cellpadding="5" cellspacing="0"
               bordercolor="#6b8fa3" class="FormTitle">
          <tr>
            <td bgcolor="#4D595D" valign="top">
              <div>&nbsp;</div>
              <div class="formfonttitle">Edge Gateway</div>
              <div style="margin:10px 0 10px 5px;" class="splitLine"></div>
              <div class="formfontdesc">
                Project-native operational dashboard for the Advanced ASUS Edge Gateway deployment.
              </div>

              <div class="edge-note">
                Phase 3 remains read-only. The dashboard exposes sanitized local operational
                state only: no tailnet identities, authentication material or private policy
                addresses are published to the page.
              </div>

              <div class="edge-nav">
                <a href="#overview">Overview</a>
                <a href="#services">Services</a>
                <a href="#tailscale">Tailscale</a>
                <a href="#firewall">Firewall</a>
                <a href="#dns">DNS / Unbound</a>
                <a href="#health">Health</a>
              </div>

              <a class="edge-section-anchor" id="overview"></a>
              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Overview / System</td></tr></thead>
                <tr><th>Snapshot</th><td><span id="edge_snapshot">Loading...</span></td></tr>
                <tr><th>Snapshot generated</th><td><span id="edge_generated">Loading...</span></td></tr>
                <tr><th>Model</th><td><% nvram_get("productid"); %></td></tr>
                <tr><th>Firmware</th><td><% nvram_get("firmver"); %>.<% nvram_get("buildno"); %>_<% nvram_get("extendno"); %></td></tr>
                <tr><th>System uptime</th><td><span id="edge_system_uptime">Loading...</span></td></tr>
                <tr><th>Load average 1 / 5 / 15</th><td><span id="edge_system_load">Loading...</span></td></tr>
                <tr><th>RAM used / total</th><td><span id="edge_system_memory">Loading...</span></td></tr>
                <tr><th>Swap used / total</th><td><span id="edge_system_swap">Loading...</span></td></tr>
                <tr><th>/opt storage</th><td><span id="edge_system_opt">Loading...</span></td></tr>
                <tr><th>/jffs storage</th><td><span id="edge_system_jffs">Loading...</span></td></tr>
                <tr><th>IPv6 service</th><td><% nvram_get("ipv6_service"); %></td></tr>
                <tr><th>WAN WebUI</th><td><span id="edge_wan_webui">Unknown</span></td></tr>
                <tr><th>LAN access restriction</th><td><span id="edge_access_restriction">Unknown</span></td></tr>
              </table>

              <div>&nbsp;</div>

              <a class="edge-section-anchor" id="services"></a>
              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Core services</td></tr></thead>
                <tr><th>Tailscale</th><td><span id="edge_svc_tailscale">Loading...</span></td></tr>
                <tr><th>dnsmasq</th><td><span id="edge_svc_dnsmasq">Loading...</span></td></tr>
                <tr><th>Unbound</th><td><span id="edge_svc_unbound">Loading...</span></td></tr>
                <tr><th>Pi-hole FTL</th><td><span id="edge_svc_pihole">Loading...</span></td></tr>
                <tr><th>syslog-ng</th><td><span id="edge_svc_syslog">Loading...</span></td></tr>
                <tr><th>WebUI status scheduler</th><td><span id="edge_svc_scheduler">Loading...</span></td></tr>
              </table>

              <div>&nbsp;</div>

              <a class="edge-section-anchor" id="tailscale"></a>
              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Tailscale / ZTNA</td></tr></thead>
                <tr><th>Version</th><td><span id="edge_ts_version">Loading...</span></td></tr>
                <tr><th>Control status</th><td><span id="edge_ts_connected">Loading...</span></td></tr>
                <tr><th>Known peers</th><td><span id="edge_ts_peers">Loading...</span></td></tr>
                <tr><th>Active peers</th><td><span id="edge_ts_active">Loading...</span></td></tr>
                <tr><th>Direct peers</th><td><span id="edge_ts_direct">Loading...</span></td></tr>
                <tr><th>Offline peers</th><td><span id="edge_ts_offline">Loading...</span></td></tr>
                <tr><th>Exit node advertisement</th><td><span id="edge_ts_exit_offered">Loading...</span></td></tr>
                <tr><th>Netfilter ownership</th><td><span id="edge_ts_netfilter">Loading...</span></td></tr>
              </table>

              <div>&nbsp;</div>

              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Project policy</td></tr></thead>
                <tr><th>Tailscale classic-DNS interception</th><td><span id="edge_policy_intercept_dns">Loading...</span></td></tr>
                <tr><th>LAN classic-DNS enforcement</th><td><span id="edge_policy_lan_dns">Loading...</span></td></tr>
                <tr><th>LAN DoT / TCP 853</th><td><span id="edge_policy_dot">Loading...</span></td></tr>
                <tr><th>Exit-node forwarding</th><td><span id="edge_policy_exit">Loading...</span></td></tr>
                <tr><th>Router HTTPS from admin tailnet sources</th><td><span id="edge_policy_https">Loading...</span></td></tr>
                <tr><th>Router SSH from admin tailnet sources</th><td><span id="edge_policy_ssh">Loading...</span></td></tr>
                <tr><th>Configured admin tailnet sources</th><td><span id="edge_policy_admins">Loading...</span></td></tr>
                <tr><th>Source-scoped printer policy</th><td><span id="edge_policy_printer">Loading...</span></td></tr>
              </table>

              <div>&nbsp;</div>

              <a class="edge-section-anchor" id="firewall"></a>
              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Firewall integrity / chains</td></tr></thead>
                <tr><th>EDGE_TS_INPUT</th><td><span id="edge_fw_input_chain">Loading...</span></td></tr>
                <tr><th>EDGE_TS_FORWARD</th><td><span id="edge_fw_forward_chain">Loading...</span></td></tr>
                <tr><th>EDGE_TS_PREROUTING</th><td><span id="edge_fw_nat_chain">Loading...</span></td></tr>
                <tr><th>EDGE_LAN_DNS_PREROUTING</th><td><span id="edge_fw_lan_dns_chain">Loading...</span></td></tr>
                <tr><th>EDGE_LAN_DOT_FORWARD</th><td><span id="edge_fw_lan_dot_chain">Loading...</span></td></tr>
                <tr><th>EDGE_TS6_INPUT</th><td><span id="edge_fw_ipv6_input_chain">Loading...</span></td></tr>
                <tr><th>EDGE_TS6_FORWARD</th><td><span id="edge_fw_ipv6_forward_chain">Loading...</span></td></tr>
              </table>

              <div>&nbsp;</div>

              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Firewall counters — cumulative</td></tr></thead>
                <tr><th>Tailscale INPUT accepted packets</th><td><span id="edge_fw_input_accept">Loading...</span></td></tr>
                <tr><th>Tailscale INPUT logged drops</th><td><span id="edge_fw_input_log">Loading...</span></td></tr>
                <tr><th>Tailscale INPUT dropped packets</th><td><span id="edge_fw_input_drop">Loading...</span></td></tr>
                <tr><th>Tailscale FORWARD accepted packets</th><td><span id="edge_fw_forward_accept">Loading...</span></td></tr>
                <tr><th>Tailscale FORWARD logged drops</th><td><span id="edge_fw_forward_log">Loading...</span></td></tr>
                <tr><th>Tailscale FORWARD dropped packets</th><td><span id="edge_fw_forward_drop">Loading...</span></td></tr>
                <tr><th>LAN DNS bypass packets</th><td><span id="edge_fw_dns_bypass">Loading...</span></td></tr>
                <tr><th>LAN DNS redirected packets</th><td><span id="edge_fw_dns_redirect">Loading...</span></td></tr>
                <tr><th>LAN DoT rejected packets</th><td><span id="edge_fw_dot_reject">Loading...</span></td></tr>
                <tr><th>IPv6 INPUT dropped packets</th><td><span id="edge_fw_ipv6_input_drop">Loading...</span></td></tr>
                <tr><th>IPv6 FORWARD dropped packets</th><td><span id="edge_fw_ipv6_forward_drop">Loading...</span></td></tr>
              </table>

              <div>&nbsp;</div>

              <a class="edge-section-anchor" id="dns"></a>
              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">DNS services</td></tr></thead>
                <tr><th>dnsmasq</th><td><span id="edge_dnsmasq">Unknown</span></td></tr>
                <tr><th>Unbound process</th><td><span id="edge_unbound">Unknown</span></td></tr>
                <tr><th>Pi-hole FTL process</th><td><span id="edge_dns_pihole">Loading...</span></td></tr>
                <tr><th>DNSSEC firmware flag</th><td><% nvram_get("dnssec_enable"); %></td></tr>
              </table>

              <div>&nbsp;</div>

              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Unbound runtime — refreshed every minute</td></tr></thead>
                <tr><th>Unbound runtime status</th><td><span id="edge_unbound_snapshot">Loading...</span></td></tr>
                <tr><th>Version</th><td><span id="edge_unbound_version">Loading...</span></td></tr>
                <tr><th>Listener</th><td><span id="edge_unbound_listener">Loading...</span></td></tr>
                <tr><th>Uptime</th><td><span id="edge_unbound_uptime">Loading...</span></td></tr>
                <tr><th>Queries</th><td><span id="edge_unbound_queries">Loading...</span></td></tr>
                <tr><th>Cache hits</th><td><span id="edge_unbound_cachehits">Loading...</span></td></tr>
                <tr><th>Cache misses</th><td><span id="edge_unbound_cachemiss">Loading...</span></td></tr>
                <tr><th>Cache hit ratio</th><td><span id="edge_unbound_hitratio">Loading...</span></td></tr>
                <tr><th>SERVFAIL answers</th><td><span id="edge_unbound_servfail">Loading...</span></td></tr>
                <tr><th>DNSSEC secure answers</th><td><span id="edge_unbound_secure">Loading...</span></td></tr>
                <tr><th>DNSSEC bogus answers</th><td><span id="edge_unbound_bogus">Loading...</span></td></tr>
                <tr><th>Prefetch</th><td><span id="edge_unbound_prefetch">Loading...</span></td></tr>
                <tr><th>Serve-expired</th><td><span id="edge_unbound_expired">Loading...</span></td></tr>
                <tr><th>Recursion average</th><td><span id="edge_unbound_recavg">Loading...</span></td></tr>
                <tr><th>Recursion median</th><td><span id="edge_unbound_recmedian">Loading...</span></td></tr>
                <tr><th>Snapshot generated</th><td><span id="edge_unbound_generated">Loading...</span></td></tr>
              </table>

              <div class="edge-note">
                Unbound counters are cumulative for the current resolver process. SERVFAIL
                and DNSSEC-bogus counters are diagnostic counters and may overlap; they are
                not treated here as independent outage counts. End-to-end DNSSEC validation
                remains the responsibility of the project health check.
              </div>

              <a class="edge-section-anchor" id="health"></a>
              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Health / safety boundary</td></tr></thead>
                <tr><th>Tailscale daemon</th><td><span id="edge_tailscale">Unknown</span></td></tr>
                <tr><th>WebUI mode</th><td><span class="edge-ok">Read-only</span></td></tr>
                <tr><th>Snapshot refresh</th><td>1 minute via Merlin cru</td></tr>
                <tr><th>Full project health</th><td><span class="edge-muted">Use healthcheck.sh — not inferred from this dashboard</span></td></tr>
              </table>

              <div class="edge-note">
                Scope boundary: the dashboard reports selected firmware, process, project
                policy, aggregate Tailscale state, storage and firewall counters. It never
                renders peer names, tailnet identities, authentication material, private
                admin-source addresses or printer addresses. The project health check remains
                authoritative for end-to-end firewall, DNSSEC, routing and recovery claims.
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
  </form>
  <div id="footer"></div>
</body>
</html>
