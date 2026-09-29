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
        ? '<span class="edge-ok">Działa</span>'
        : '<span class="edge-bad">Zatrzymany</span>';
    }

    function edgeBooleanState(value, enabledText, disabledText) {
      if (String(value) === "1")
        return '<span class="edge-ok">' + enabledText + '</span>';
      if (String(value) === "0")
        return '<span class="edge-muted">' + disabledText + '</span>';
      return '<span class="edge-muted">Nieznany</span>';
    }

    function edgeSnapshotBoolean(value, yesText, noText) {
      return Number(value) === 1
        ? '<span class="edge-ok">' + yesText + '</span>'
        : '<span class="edge-muted">' + noText + '</span>';
    }

    function edgeRequiredState(value) {
      return Number(value) === 1
        ? '<span class="edge-ok">Obecny</span>'
        : '<span class="edge-bad">Brak</span>';
    }

    function edgeRunningState(value) {
      return Number(value) === 1
        ? '<span class="edge-ok">Działa</span>'
        : '<span class="edge-bad">Zatrzymany</span>';
    }

    function edgeSchedulerState(value) {
      return Number(value) === 1
        ? '<span class="edge-ok">Zaplanowane</span>'
        : '<span class="edge-bad">Brak</span>';
    }

    function edgeWanWebuiState(value) {
      if (String(value) === "0")
        return '<span class="edge-ok">Wyłączone</span>';
      if (String(value) === "1")
        return '<span class="edge-bad">Włączone</span>';
      return '<span class="edge-muted">Nieznany</span>';
    }

    function edgeUnboundRuntimeState(value) {
      return String(value) === "running"
        ? '<span class="edge-ok">Działa</span>'
        : '<span class="edge-bad">Zatrzymany / niedostępny</span>';
    }

    function edgeNumber(value) {
      var number = Number(value);
      if (!isFinite(number))
        return "Brak danych";
      return String(Math.round(number));
    }

    function edgePercent(hits, misses) {
      var hitCount = Number(hits);
      var missCount = Number(misses);
      var total = hitCount + missCount;
      if (!isFinite(total) || total <= 0)
        return "Brak danych";
      return ((hitCount / total) * 100).toFixed(1) + "%";
    }

    function edgeMilliseconds(seconds) {
      var value = Number(seconds);
      if (!isFinite(value))
        return "Brak danych";
      return (value * 1000).toFixed(1) + " ms";
    }

    function edgeDuration(seconds) {
      var remaining = Math.floor(Number(seconds));
      if (!isFinite(remaining) || remaining < 0)
        return "Brak danych";

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
        return "Brak danych";
      return (value / 1024).toFixed(1) + " MiB";
    }

    function edgeGiB(kib) {
      var value = Number(kib);
      if (!isFinite(value))
        return "Brak danych";
      return (value / 1048576).toFixed(1) + " GiB";
    }

    function edgeStorage(used, total, percent) {
      var totalKiB = Number(total);
      if (!isFinite(totalKiB))
        return "Brak danych";

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
        setText("edge_snapshot", '<span class="edge-bad">Migawka niedostępna</span>');
        return;
      }

      var system = data.system || {};
      var services = data.services || {};
      var tailscale = data.tailscale || {};
      var policy = data.policy || {};
      var firewall = data.firewall || {};
      var unbound = data.unbound || {};

      setText("edge_snapshot", '<span class="edge-ok">Załadowano</span>');
      setText("edge_generated", data.generated || "Brak danych");

      setText("edge_system_uptime", edgeDuration(system.uptime));
      setText("edge_system_load", edgeNumber(system.load1 * 100) / 100 + " / " +
        edgeNumber(system.load5 * 100) / 100 + " / " + edgeNumber(system.load15 * 100) / 100);
      setText("edge_system_memory", edgeMiB(system.memUsedKiB) + " / " + edgeMiB(system.memTotalKiB));
      setText("edge_system_swap", edgeMiB(system.swapUsedKiB) + " / " + edgeMiB(system.swapTotalKiB) +
        " (" + edgeNumber(system.swapDevices) + " urządzeń)");
      setText("edge_system_opt", edgeStorage(system.optUsedKiB, system.optTotalKiB, system.optUsedPct));
      setText("edge_system_jffs", edgeStorage(system.jffsUsedKiB, system.jffsTotalKiB, system.jffsUsedPct));

      setText("edge_svc_tailscale", edgeRunningState(services.tailscaled));
      setText("edge_svc_unbound", edgeRunningState(services.unbound));
      setText("edge_svc_dnsmasq", edgeRunningState(services.dnsmasq));
      setText("edge_svc_pihole", edgeRunningState(services.piholeFtl));
      setText("edge_svc_syslog", edgeRunningState(services.syslogNg));
      setText("edge_svc_scheduler", edgeSchedulerState(services.scheduler));
      setText("edge_dns_pihole", edgeRunningState(services.piholeFtl));

      setText("edge_ts_version", tailscale.version || "Brak danych");
      setText("edge_ts_connected", edgeSnapshotBoolean(tailscale.connected, "Połączono", "Rozłączono"));
      setText("edge_ts_peers", edgeNumber(tailscale.peers));
      setText("edge_ts_active", edgeNumber(tailscale.activePeers));
      setText("edge_ts_direct", edgeNumber(tailscale.directPeers));
      setText("edge_ts_offline", edgeNumber(tailscale.offlinePeers));
      setText("edge_ts_exit_offered", edgeSnapshotBoolean(tailscale.exitNodeOffered, "Ogłaszany", "Nieogłaszany"));
      setText("edge_ts_netfilter", edgeSnapshotBoolean(policy.projectOwnsNetfilter, "Zarządzany przez projekt", "Zarządzany przez Tailscale"));

      setText("edge_policy_intercept_dns", edgeSnapshotBoolean(policy.interceptDns, "Włączone", "Wyłączone"));
      setText("edge_policy_lan_dns", edgeSnapshotBoolean(policy.enforceLanDns, "Włączone", "Wyłączone"));
      setText("edge_policy_dot", edgeSnapshotBoolean(policy.blockLanDot, "Zablokowane", "Dozwolone"));
      setText("edge_policy_exit", edgeSnapshotBoolean(policy.exitNodeEnabled, "Włączone", "Wyłączone"));
      setText("edge_policy_https", edgeSnapshotBoolean(policy.routerHttps, "Dozwolone", "Niedozwolone"));
      setText("edge_policy_ssh", edgeSnapshotBoolean(policy.routerSsh, "Dozwolone", "Niedozwolone"));
      setText("edge_policy_admins", edgeNumber(policy.adminSourceCount));
      setText("edge_policy_printer", edgeSnapshotBoolean(policy.printerPolicy, "Skonfigurowane", "Nieskonfigurowane"));

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
      setText("edge_unbound_version", unbound.version || "Brak danych");
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
      setText("edge_unbound_generated", data.generated || "Brak danych");
    }

    function loadGatewaySnapshot() {
      $.ajax({
        url: "/ext/asus-edge/status.js?_=" + new Date().getTime(),
        dataType: "script",
        cache: false,
        timeout: 3000,
        success: renderGatewaySnapshot,
        error: function() {
          setText("edge_snapshot", '<span class="edge-bad">Migawka niedostępna</span>');
          setText("edge_unbound_snapshot", '<span class="edge-muted">Migawka niedostępna</span>');
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

      var ipv6Service = "<% nvram_get("ipv6_service"); %>";
      document.getElementById("edge_ipv6_service").innerHTML =
        (ipv6Service === "disabled") ? "Wyłączona" : ipv6Service;

      document.getElementById("edge_wan_webui").innerHTML =
        edgeWanWebuiState("<% nvram_get("misc_http_x"); %>");
      document.getElementById("edge_access_restriction").innerHTML =
        edgeBooleanState("<% nvram_get("enable_acc_restriction"); %>", "Włączone", "Wyłączone");

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
                Natywny dla projektu panel operacyjny wdrożenia Advanced ASUS Edge Gateway.
              </div>

              <div class="edge-note">
                Faza 3 pozostaje tylko do odczytu. Panel udostępnia wyłącznie oczyszczony lokalny stan
                operacyjny: na stronie nie są publikowane tożsamości tailnetu, dane uwierzytelniające ani prywatne
                adresy polityk.
              </div>

              <div class="edge-nav">
                <a href="#overview">Przegląd</a>
                <a href="#services">Usługi</a>
                <a href="#tailscale">Tailscale</a>
                <a href="#firewall">Zapora</a>
                <a href="#dns">DNS / Unbound</a>
                <a href="#health">Stan</a>
              </div>

              <a class="edge-section-anchor" id="overview"></a>
              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Przegląd / System</td></tr></thead>
                <tr><th>Migawka</th><td><span id="edge_snapshot">Ładowanie...</span></td></tr>
                <tr><th>Wygenerowano migawkę</th><td><span id="edge_generated">Ładowanie...</span></td></tr>
                <tr><th>Model</th><td><% nvram_get("productid"); %></td></tr>
                <tr><th>Oprogramowanie</th><td><% nvram_get("firmver"); %>.<% nvram_get("buildno"); %>_<% nvram_get("extendno"); %></td></tr>
                <tr><th>Czas pracy systemu</th><td><span id="edge_system_uptime">Ładowanie...</span></td></tr>
                <tr><th>Średnie obciążenie 1 / 5 / 15</th><td><span id="edge_system_load">Ładowanie...</span></td></tr>
                <tr><th>RAM używana / łącznie</th><td><span id="edge_system_memory">Ładowanie...</span></td></tr>
                <tr><th>Pamięć wymiany użyta / łącznie</th><td><span id="edge_system_swap">Ładowanie...</span></td></tr>
                <tr><th>Pamięć /opt</th><td><span id="edge_system_opt">Ładowanie...</span></td></tr>
                <tr><th>Pamięć /jffs</th><td><span id="edge_system_jffs">Ładowanie...</span></td></tr>
                <tr><th>Usługa IPv6</th><td><span id="edge_ipv6_service"></span></td></tr>
                <tr><th>WebUI od strony WAN</th><td><span id="edge_wan_webui">Nieznany</span></td></tr>
                <tr><th>Ograniczenie dostępu z LAN</th><td><span id="edge_access_restriction">Nieznany</span></td></tr>
              </table>

              <div>&nbsp;</div>

              <a class="edge-section-anchor" id="services"></a>
              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Usługi podstawowe</td></tr></thead>
                <tr><th>Tailscale</th><td><span id="edge_svc_tailscale">Ładowanie...</span></td></tr>
                <tr><th>dnsmasq</th><td><span id="edge_svc_dnsmasq">Ładowanie...</span></td></tr>
                <tr><th>Unbound</th><td><span id="edge_svc_unbound">Ładowanie...</span></td></tr>
                <tr><th>Pi-hole FTL</th><td><span id="edge_svc_pihole">Ładowanie...</span></td></tr>
                <tr><th>syslog-ng</th><td><span id="edge_svc_syslog">Ładowanie...</span></td></tr>
                <tr><th>Harmonogram statusu WebUI</th><td><span id="edge_svc_scheduler">Ładowanie...</span></td></tr>
              </table>

              <div>&nbsp;</div>

              <a class="edge-section-anchor" id="tailscale"></a>
              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Tailscale / ZTNA</td></tr></thead>
                <tr><th>Wersja</th><td><span id="edge_ts_version">Ładowanie...</span></td></tr>
                <tr><th>Stan połączenia</th><td><span id="edge_ts_connected">Ładowanie...</span></td></tr>
                <tr><th>Znane węzły</th><td><span id="edge_ts_peers">Ładowanie...</span></td></tr>
                <tr><th>Aktywne węzły</th><td><span id="edge_ts_active">Ładowanie...</span></td></tr>
                <tr><th>Węzły połączone bezpośrednio</th><td><span id="edge_ts_direct">Ładowanie...</span></td></tr>
                <tr><th>Węzły offline</th><td><span id="edge_ts_offline">Ładowanie...</span></td></tr>
                <tr><th>Ogłaszanie węzła wyjściowego (exit node)</th><td><span id="edge_ts_exit_offered">Ładowanie...</span></td></tr>
                <tr><th>Zarządzanie Netfilterem</th><td><span id="edge_ts_netfilter">Ładowanie...</span></td></tr>
              </table>

              <div>&nbsp;</div>

              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Polityka projektu</td></tr></thead>
                <tr><th>Przechwytywanie klasycznego DNS przez Tailscale</th><td><span id="edge_policy_intercept_dns">Ładowanie...</span></td></tr>
                <tr><th>Wymuszanie klasycznego DNS w LAN</th><td><span id="edge_policy_lan_dns">Ładowanie...</span></td></tr>
                <tr><th>LAN DoT / TCP 853</th><td><span id="edge_policy_dot">Ładowanie...</span></td></tr>
                <tr><th>Przekazywanie ruchu przez exit node</th><td><span id="edge_policy_exit">Ładowanie...</span></td></tr>
                <tr><th>HTTPS routera ze źródeł administracyjnych tailnetu</th><td><span id="edge_policy_https">Ładowanie...</span></td></tr>
                <tr><th>SSH routera ze źródeł administracyjnych tailnetu</th><td><span id="edge_policy_ssh">Ładowanie...</span></td></tr>
                <tr><th>Skonfigurowane źródła administracyjne tailnetu</th><td><span id="edge_policy_admins">Ładowanie...</span></td></tr>
                <tr><th>Polityka drukarki ograniczona do źródeł</th><td><span id="edge_policy_printer">Ładowanie...</span></td></tr>
              </table>

              <div>&nbsp;</div>

              <a class="edge-section-anchor" id="firewall"></a>
              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Integralność zapory / łańcuchy</td></tr></thead>
                <tr><th>EDGE_TS_INPUT</th><td><span id="edge_fw_input_chain">Ładowanie...</span></td></tr>
                <tr><th>EDGE_TS_FORWARD</th><td><span id="edge_fw_forward_chain">Ładowanie...</span></td></tr>
                <tr><th>EDGE_TS_PREROUTING</th><td><span id="edge_fw_nat_chain">Ładowanie...</span></td></tr>
                <tr><th>EDGE_LAN_DNS_PREROUTING</th><td><span id="edge_fw_lan_dns_chain">Ładowanie...</span></td></tr>
                <tr><th>EDGE_LAN_DOT_FORWARD</th><td><span id="edge_fw_lan_dot_chain">Ładowanie...</span></td></tr>
                <tr><th>EDGE_TS6_INPUT</th><td><span id="edge_fw_ipv6_input_chain">Ładowanie...</span></td></tr>
                <tr><th>EDGE_TS6_FORWARD</th><td><span id="edge_fw_ipv6_forward_chain">Ładowanie...</span></td></tr>
              </table>

              <div>&nbsp;</div>

              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Liczniki zapory — narastająco</td></tr></thead>
                <tr><th>Zaakceptowane pakiety Tailscale INPUT</th><td><span id="edge_fw_input_accept">Ładowanie...</span></td></tr>
                <tr><th>Zarejestrowane odrzucenia Tailscale INPUT</th><td><span id="edge_fw_input_log">Ładowanie...</span></td></tr>
                <tr><th>Odrzucone pakiety Tailscale INPUT</th><td><span id="edge_fw_input_drop">Ładowanie...</span></td></tr>
                <tr><th>Zaakceptowane pakiety Tailscale FORWARD</th><td><span id="edge_fw_forward_accept">Ładowanie...</span></td></tr>
                <tr><th>Zarejestrowane odrzucenia Tailscale FORWARD</th><td><span id="edge_fw_forward_log">Ładowanie...</span></td></tr>
                <tr><th>Odrzucone pakiety Tailscale FORWARD</th><td><span id="edge_fw_forward_drop">Ładowanie...</span></td></tr>
                <tr><th>Pakiety LAN DNS z pominięciem przekierowania</th><td><span id="edge_fw_dns_bypass">Ładowanie...</span></td></tr>
                <tr><th>Przekierowane pakiety LAN DNS</th><td><span id="edge_fw_dns_redirect">Ładowanie...</span></td></tr>
                <tr><th>Odrzucone pakiety LAN DoT</th><td><span id="edge_fw_dot_reject">Ładowanie...</span></td></tr>
                <tr><th>Odrzucone pakiety IPv6 INPUT</th><td><span id="edge_fw_ipv6_input_drop">Ładowanie...</span></td></tr>
                <tr><th>Odrzucone pakiety IPv6 FORWARD</th><td><span id="edge_fw_ipv6_forward_drop">Ładowanie...</span></td></tr>
              </table>

              <div>&nbsp;</div>

              <a class="edge-section-anchor" id="dns"></a>
              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Usługi DNS</td></tr></thead>
                <tr><th>dnsmasq</th><td><span id="edge_dnsmasq">Nieznany</span></td></tr>
                <tr><th>Proces Unbound</th><td><span id="edge_unbound">Nieznany</span></td></tr>
                <tr><th>Proces Pi-hole FTL</th><td><span id="edge_dns_pihole">Ładowanie...</span></td></tr>
                <tr><th>Flaga DNSSEC oprogramowania</th><td><% nvram_get("dnssec_enable"); %></td></tr>
              </table>

              <div>&nbsp;</div>

              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Stan Unbound — odświeżany co minutę</td></tr></thead>
                <tr><th>Stan działania Unbound</th><td><span id="edge_unbound_snapshot">Ładowanie...</span></td></tr>
                <tr><th>Wersja</th><td><span id="edge_unbound_version">Ładowanie...</span></td></tr>
                <tr><th>Nasłuchiwanie</th><td><span id="edge_unbound_listener">Ładowanie...</span></td></tr>
                <tr><th>Czas pracy</th><td><span id="edge_unbound_uptime">Ładowanie...</span></td></tr>
                <tr><th>Zapytania</th><td><span id="edge_unbound_queries">Ładowanie...</span></td></tr>
                <tr><th>Trafienia pamięci podręcznej</th><td><span id="edge_unbound_cachehits">Ładowanie...</span></td></tr>
                <tr><th>Chybienia pamięci podręcznej</th><td><span id="edge_unbound_cachemiss">Ładowanie...</span></td></tr>
                <tr><th>Współczynnik trafień pamięci podręcznej</th><td><span id="edge_unbound_hitratio">Ładowanie...</span></td></tr>
                <tr><th>Odpowiedzi SERVFAIL</th><td><span id="edge_unbound_servfail">Ładowanie...</span></td></tr>
                <tr><th>Poprawnie zabezpieczone odpowiedzi DNSSEC</th><td><span id="edge_unbound_secure">Ładowanie...</span></td></tr>
                <tr><th>Błędne odpowiedzi DNSSEC</th><td><span id="edge_unbound_bogus">Ładowanie...</span></td></tr>
                <tr><th>Wstępne pobieranie (prefetch)</th><td><span id="edge_unbound_prefetch">Ładowanie...</span></td></tr>
                <tr><th>Obsługa wygasłych wpisów (serve-expired)</th><td><span id="edge_unbound_expired">Ładowanie...</span></td></tr>
                <tr><th>Średni czas rekursji</th><td><span id="edge_unbound_recavg">Ładowanie...</span></td></tr>
                <tr><th>Mediana czasu rekursji</th><td><span id="edge_unbound_recmedian">Ładowanie...</span></td></tr>
                <tr><th>Wygenerowano migawkę</th><td><span id="edge_unbound_generated">Ładowanie...</span></td></tr>
              </table>

              <div class="edge-note">
                Liczniki Unbound są narastające dla bieżącego procesu resolvera. Liczniki SERVFAIL
                oraz DNSSEC-bogus mają charakter diagnostyczny i mogą się pokrywać;
                nie są tutaj traktowane jako niezależne liczniki awarii. Pełna walidacja DNSSEC
                pozostaje zadaniem kontroli stanu projektu.
              </div>

              <a class="edge-section-anchor" id="health"></a>
              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead><tr><td colspan="2">Stan / granice bezpieczeństwa</td></tr></thead>
                <tr><th>Demon Tailscale</th><td><span id="edge_tailscale">Nieznany</span></td></tr>
                <tr><th>Tryb WebUI</th><td><span class="edge-ok">Tylko do odczytu</span></td></tr>
                <tr><th>Odświeżanie migawki</th><td>Co 1 minutę przez Merlin cru</td></tr>
                <tr><th>Pełny stan projektu</th><td><span class="edge-muted">Użyj healthcheck.sh — ten panel nie wyznacza pełnego stanu projektu</span></td></tr>
              </table>

              <div class="edge-note">
                Zakres: panel prezentuje wybrane informacje o oprogramowaniu, procesach,
                polityce projektu, zagregowanym stanie Tailscale, pamięci i licznikach zapory. Nigdy nie
                wyświetla nazw węzłów, tożsamości tailnetu, danych uwierzytelniających ani prywatnych
                adresów źródeł administracyjnych ani adresów drukarki. Kontrola stanu projektu pozostaje
                źródłem nadrzędnym dla pełnej walidacji zapory, DNSSEC, routingu i odtwarzania.
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
