<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<!-- ASUS-EDGE-WEBUI: project-native read-only status page -->
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
    .edge-note {
      margin:10px 0 15px 5px;
      padding:10px;
      border:1px solid #596b75;
      background:#2f3b43;
      color:#d8e2e8;
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

    function edgeWanWebuiState(value) {
      if (String(value) === "0")
        return '<span class="edge-ok">Disabled</span>';
      if (String(value) === "1")
        return '<span class="edge-bad">Enabled</span>';
      return '<span class="edge-muted">Unknown</span>';
    }

    function SetCurrentPage() {
      if (document.form) {
        if (document.form.next_page)
          document.form.next_page.value = window.location.pathname.substring(1);
        if (document.form.current_page)
          document.form.current_page.value = window.location.pathname.substring(1);
      }
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
    }

    function initial() {
      /*
       * Render project status before invoking the ASUS menu helper.  This keeps
       * the status page useful even if a firmware-specific menu helper fails.
       */
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

  <!--
    ASUSWRT's show_menu() helper expects the standard named form scaffold.
    This Phase 1 form has no submit controls or apply action and remains
    read-only.
  -->
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
                Project-native status page for the Advanced ASUS Edge Gateway deployment.
              </div>

              <div class="edge-note">
                Phase 1 is read-only. This page does not apply configuration, restart
                services, change DNS, modify firewall rules, or write custom settings.
              </div>

              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead>
                  <tr><td colspan="2">Overview</td></tr>
                </thead>
                <tr>
                  <th>Model</th>
                  <td><% nvram_get("productid"); %></td>
                </tr>
                <tr>
                  <th>Firmware</th>
                  <td>
                    <% nvram_get("firmver"); %>.<% nvram_get("buildno"); %>_<% nvram_get("extendno"); %>
                  </td>
                </tr>
                <tr>
                  <th>IPv6 service</th>
                  <td><% nvram_get("ipv6_service"); %></td>
                </tr>
                <tr>
                  <th>WAN WebUI</th>
                  <td><span id="edge_wan_webui">Unknown</span></td>
                </tr>
                <tr>
                  <th>LAN access restriction</th>
                  <td><span id="edge_access_restriction">Unknown</span></td>
                </tr>
              </table>

              <div>&nbsp;</div>

              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead>
                  <tr><td colspan="2">DNS</td></tr>
                </thead>
                <tr>
                  <th>dnsmasq</th>
                  <td><span id="edge_dnsmasq">Unknown</span></td>
                </tr>
                <tr>
                  <th>Unbound</th>
                  <td><span id="edge_unbound">Unknown</span></td>
                </tr>
                <tr>
                  <th>DNSSEC firmware flag</th>
                  <td><% nvram_get("dnssec_enable"); %></td>
                </tr>
              </table>

              <div>&nbsp;</div>

              <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                     bordercolor="#6b8fa3" class="FormTable">
                <thead>
                  <tr><td colspan="2">Health</td></tr>
                </thead>
                <tr>
                  <th>Tailscale daemon</th>
                  <td><span id="edge_tailscale">Unknown</span></td>
                </tr>
                <tr>
                  <th>WebUI mode</th>
                  <td><span class="edge-ok">Read-only</span></td>
                </tr>
              </table>

              <div class="edge-note">
                Scope boundary: this page reports selected firmware and process state only.
                It does not replace the project health check and does not claim end-to-end
                DNS, Tailscale, firewall, or Internet health.
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
