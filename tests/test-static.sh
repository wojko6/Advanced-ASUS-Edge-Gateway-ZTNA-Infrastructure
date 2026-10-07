#!/bin/sh

set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"

find "$REPO_DIR/router" "$REPO_DIR/scripts" "$REPO_DIR/tests" -type f \( -name '*.sh' -o -path '*/router/scripts/*' \) | while IFS= read -r file; do
    sh -n "$file"
done

[ -x "$REPO_DIR/scripts/fedora-dr-restore.sh" ] || {
    echo "FAIL: Fedora DR finalization helper is not executable" >&2
    exit 1
}

grep -F 'RELEASE_VERSION="$(cat "$REPO_DIR/VERSION")"' "$REPO_DIR/scripts/install.sh" >/dev/null || {
    echo "FAIL: installer does not read the release version from VERSION" >&2
    exit 1
}

for install_snapshot_guard in \
    'BACKUP_PREFIX="$ADDON_DIR/backups/install-$(date +%Y%m%d-%H%M%S)"' \
    'create_install_backup_dir()' \
    'backup_candidate="$BACKUP_PREFIX-$backup_counter"' \
    'EDGE_INSTALL_BACKUP_KEEP'
do
    grep -F "$install_snapshot_guard" "$REPO_DIR/scripts/install.sh" >/dev/null || {
        echo "FAIL: installer snapshot retention/uniqueness guard missing: $install_snapshot_guard" >&2
        exit 1
    }
done

grep -F 'Installed Advanced ASUS Edge Gateway v$RELEASE_VERSION' "$REPO_DIR/scripts/install.sh" >/dev/null || {
    echo "FAIL: installer does not report the release version from VERSION" >&2
    exit 1
}

if command -v shellcheck >/dev/null 2>&1; then
    find "$REPO_DIR/router" "$REPO_DIR/scripts" "$REPO_DIR/tests" -type f \( -name '*.sh' -o -path '*/router/scripts/*' \) -print0 \
        | xargs -0 shellcheck -S warning
else
    echo "WARN: shellcheck not installed"
fi

grep -F 'dig +time=3 +tries=1 +dnssec -p "$EDGE_UNBOUND_PORT" @127.0.0.1' "$REPO_DIR/scripts/healthcheck.sh" >/dev/null || {
    echo "FAIL: healthcheck does not test the configured Unbound port" >&2
    exit 1
}

grep -F '/opt/var/lib/unbound/unbound.conf' "$REPO_DIR/scripts/healthcheck.sh" >/dev/null || {
    echo "FAIL: healthcheck does not detect the amtm Unbound Manager runtime configuration" >&2
    exit 1
}

for backup_path in \
    '/opt/etc/unbound/unbound.conf "$WORK_DIR/opt/etc/unbound/"' \
    '/opt/var/lib/unbound/unbound.conf "$WORK_DIR/opt/var/lib/unbound/"' \
    '/jffs/scripts/dnsmasq.postconf "$WORK_DIR/jffs/scripts/"' \
    '/jffs/scripts/post-mount "$WORK_DIR/recovery-reference/jffs/scripts/"' \
    '/jffs/scripts/wan-event "$WORK_DIR/jffs/scripts/"' \
    '/jffs/scripts/edge-dns-breakglass.sh "$WORK_DIR/jffs/scripts/"' \
    '/jffs/configs/dnsmasq.conf.add "$WORK_DIR/jffs/configs/"'
do
    grep -F "$backup_path" "$REPO_DIR/scripts/backup.sh" >/dev/null || {
        echo "FAIL: backup does not preserve $backup_path" >&2
        exit 1
    }
done

UPDATE_TAILSCALE="$REPO_DIR/scripts/update-tailscale.sh"
for update_guard in \
    'UPGRADABLE="$(opkg list-upgradable)" || {' \
    'ERROR: failed to query upgradable packages' \
    'ERROR: post-update service recovery failed' \
    'ERROR: post-update health check failed'
do
    grep -F "$update_guard" "$UPDATE_TAILSCALE" >/dev/null || {
        echo "FAIL: Tailscale update failure guard missing: $update_guard" >&2
        exit 1
    }
done

if grep -F "opkg list-upgradable | grep '^tailscale '" "$UPDATE_TAILSCALE" >/dev/null; then
    echo "FAIL: Tailscale update query failure can still be masked by a pipeline" >&2
    exit 1
fi

if grep -F 'opkg update && opkg upgrade tailscale' "$REPO_DIR/router/scripts/services-start" >/dev/null; then
    echo "FAIL: package upgrade present in boot path" >&2
    exit 1
fi

for webui_guard in \
    'router/scripts/webui-mount" "$ADDON_DIR/bin/webui-mount" 0755' \
    'router/scripts/webui-pl-build" "$ADDON_DIR/bin/webui-pl-build" 0755' \
    'router/scripts/webui-pl-mount" "$ADDON_DIR/bin/webui-pl-mount" 0755' \
    'router/scripts/webui-status" "$ADDON_DIR/bin/webui-status" 0755' \
    'router/webui/EdgeGateway.asp" "$ADDON_DIR/webui/EdgeGateway.asp" 0644' \
    'snapshot_path "$ADDON_DIR/webui" webui' \
    'restore_path "$ADDON_DIR/webui" webui'
do
    grep -F "$webui_guard" "$REPO_DIR/scripts/install.sh" >/dev/null || {
        echo "FAIL: installer WebUI integration missing: $webui_guard" >&2
        exit 1
    }
done

for webui_pl_build_guard in \
    'WEBUI_PATCH_BIN="${EDGE_PATCH_BIN:-/opt/bin/patch}"' \
    'opkg install patch' \
    'router/webui/patches/$webui_patch' \
    'webui-pl-build" "$ADDON_DIR/bin/webui-pl-build" 0755' \
    'EDGE_ADDON_DIR="$ADDON_DIR"' \
    'WADV_PATCHED_SHA=' \
    'STATE_PATCHED_SHA=' \
    'ROUTER_STATUS_PATCHED_SHA=' \
    'ROUTER_PATCHED_SHA=' \
    'INTERNET_PATCHED_SHA=' \
    'ADV_WAN_PATCHED_SHA=' \
    'ADV_BASICFW_PATCHED_SHA=' \
    'ADV_FIREWALL_PATCHED_SHA=' \
    'ADV_FWUP_PATCHED_SHA=' \
    'ADV_SYSTEM_PATCHED_SHA=' \
    'ADV_BACKUP_PATCHED_SHA=' \
    'ADV_SNMP_PATCHED_SHA=' \
    'MAIN_LOG_PATCHED_SHA=' \
    'MAIN_WSTATUS_PATCHED_SHA=' \
    'MAIN_DHCP_PATCHED_SHA=' \
    'MAIN_IPV6_PATCHED_SHA=' \
    'MAIN_ROUTE_PATCHED_SHA=' \
    'MAIN_IPT_PATCHED_SHA=' \
    'MAIN_CONN_PATCHED_SHA=' \
    'TRAFFIC_RT_PATCHED_SHA=' \
    'TRAFFIC_LAST24_PATCHED_SHA=' \
    'TRAFFIC_DAILY_PATCHED_SHA=' \
    'TRAFFIC_MONTHLY_PATCHED_SHA=' \
    'TRAFFIC_SETTINGS_PATCHED_SHA=' \
    'DNSDIRECTOR_PATCHED_SHA=' \
    'WEBUI_PL_BUILD=PASS'
do
    grep -F "$webui_pl_build_guard" \
        "$REPO_DIR/scripts/install.sh" \
        "$REPO_DIR/router/scripts/webui-pl-build" >/dev/null || {
        echo "FAIL: Polish WebUI build guard missing: $webui_pl_build_guard" >&2
        exit 1
    }
done

for webui_patch in \
    PL.dict.patch \
    help.js.patch \
    Tools_Sysinfo.asp.patch \
    Tools_OtherSettings.asp.patch \
    Advanced_WAdvanced_Content.asp.patch \
    state.js.patch \
    router_status.asp.patch \
    router.asp.patch \
    internet.asp.patch \
    Advanced_WAN_Content.asp.patch \
    Advanced_BasicFirewall_Content.asp.patch \
    Advanced_Firewall_Content.asp.patch \
    Advanced_FirmwareUpgrade_Content.asp.patch \
    Advanced_System_Content.asp.patch \
    Advanced_SettingBackup_Content.asp.patch \
    Advanced_SNMP_Content.asp.patch \
    Main_LogStatus_Content.asp.patch \
    Main_WStatus_Content.asp.patch \
    Main_DHCPStatus_Content.asp.patch \
    Main_IPV6Status_Content.asp.patch \
    Main_RouteStatus_Content.asp.patch \
    Main_IPTStatus_Content.asp.patch \
    Main_ConnStatus_Content.asp.patch \
    Main_TrafficMonitor_realtime.asp.patch \
    Main_TrafficMonitor_last24.asp.patch \
    Main_TrafficMonitor_daily.asp.patch \
    Main_TrafficMonitor_monthly.asp.patch \
    Main_TrafficMonitor_settings.asp.patch \
    DNSDirector.asp.patch
do
    patch_path="$REPO_DIR/router/webui/patches/$webui_patch"
    [ -s "$patch_path" ] || {
        echo "FAIL: Polish WebUI patch missing or empty: $webui_patch" >&2
        exit 1
    }

    patch_target="${webui_patch%.patch}"
    old_header="$(awk 'NR == 1 && $1 == "---" { print $2 }' "$patch_path")"
    new_header="$(awk 'NR == 2 && $1 == "+++" { print $2 }' "$patch_path")"

    case "$old_header" in
        */"$patch_target") ;;
        *)
            echo "FAIL: Polish WebUI patch old path is not -p1 compatible: $webui_patch -> $old_header" >&2
            exit 1
            ;;
    esac

    case "$new_header" in
        */"$patch_target") ;;
        *)
            echo "FAIL: Polish WebUI patch new path is not -p1 compatible: $webui_patch -> $new_header" >&2
            exit 1
            ;;
    esac
done

grep -F 'mount_project_webui' "$REPO_DIR/router/scripts/services-start" >/dev/null || {
    echo "FAIL: services-start does not persist the Edge Gateway WebUI" >&2
    exit 1
}

for webui_pl_guard in \
    'PL_WEBUI_HELPER="/jffs/addons/asus-edge/bin/webui-pl-mount"' \
    'mount_polish_overlay' \
    'unmount_polish_overlay' \
    '/usr/sbin/openssl' \
    'WEBUI_PL_OVERLAY=PASS' \
    'WEBUI_PL_OVERLAY_UNMOUNT=PASS' \
    'menuName: "Informacje o systemie"' \
    'tabName: "Dostrajanie"' \
    'Advanced_WAdvanced_Content.asp' \
    'STATE_TARGET="/www/state.js"' \
    'ROUTER_STATUS_TARGET="/www/device-map/router_status.asp"' \
    'ROUTER_TARGET="/www/device-map/router.asp"' \
    'ADV_WAN_TARGET="/www/Advanced_WAN_Content.asp"' \
    'ADV_BASICFW_TARGET="/www/Advanced_BasicFirewall_Content.asp"' \
    'ADV_FIREWALL_TARGET="/www/Advanced_Firewall_Content.asp"' \
    'ADV_FWUP_TARGET="/www/Advanced_FirmwareUpgrade_Content.asp"' \
    'ADV_SYSTEM_TARGET="/www/Advanced_System_Content.asp"' \
    'ADV_BACKUP_TARGET="/www/Advanced_SettingBackup_Content.asp"' \
    'ADV_SNMP_TARGET="/www/Advanced_SNMP_Content.asp"' \
    'MAIN_LOG_TARGET="/www/Main_LogStatus_Content.asp"' \
    'MAIN_WSTATUS_TARGET="/www/Main_WStatus_Content.asp"' \
    'MAIN_DHCP_TARGET="/www/Main_DHCPStatus_Content.asp"' \
    'MAIN_IPV6_TARGET="/www/Main_IPV6Status_Content.asp"' \
    'MAIN_ROUTE_TARGET="/www/Main_RouteStatus_Content.asp"' \
    'MAIN_IPT_TARGET="/www/Main_IPTStatus_Content.asp"' \
    'MAIN_CONN_TARGET="/www/Main_ConnStatus_Content.asp"' \
    'INTERNET_TARGET="/www/device-map/internet.asp"' \
    'TRAFFIC_RT_TARGET="/www/Main_TrafficMonitor_realtime.asp"' \
    'TRAFFIC_LAST24_TARGET="/www/Main_TrafficMonitor_last24.asp"' \
    'TRAFFIC_DAILY_TARGET="/www/Main_TrafficMonitor_daily.asp"' \
    'TRAFFIC_MONTHLY_TARGET="/www/Main_TrafficMonitor_monthly.asp"' \
    'TRAFFIC_SETTINGS_TARGET="/www/Main_TrafficMonitor_settings.asp"' \
    'DNSDIRECTOR_TARGET="/www/DNSDirector.asp"'
do
    grep -F "$webui_pl_guard" \
        "$REPO_DIR/router/scripts/webui-mount" \
        "$REPO_DIR/router/scripts/webui-pl-mount" >/dev/null || {
        echo "FAIL: Polish WebUI overlay guard missing: $webui_pl_guard" >&2
        exit 1
    }
done

for webui_status_guard in \
    'configure_webui_status' \
    'cru a AsusEdgeWebUIStatus' \
    'unset LD_LIBRARY_PATH' \
    'preserving previous status.js' \
    'stats_noreset' \
    'num.answer.rcode.SERVFAIL' \
    'num.answer.bogus' \
    '/ext/asus-edge/status.js'
do
    grep -F "$webui_status_guard" \
        "$REPO_DIR/router/scripts/services-start" \
        "$REPO_DIR/router/scripts/webui-status" \
        "$REPO_DIR/router/webui/EdgeGateway.asp" >/dev/null || {
        echo "FAIL: Edge Gateway WebUI Phase 2 guard missing: $webui_status_guard" >&2
        exit 1
    }
done

grep -F '/usr/sbin/cru d "$STATUS_CRON_ID"' "$REPO_DIR/router/scripts/webui-mount" >/dev/null || {
    echo "FAIL: WebUI unmount does not remove the Phase 2 refresh schedule" >&2
    exit 1
}

for webui_top_level_menu_guard in \
    'MENU_INDEX="menu_Dashboard"' \
    'ASUS-EDGE-MENU-BEGIN' \
    'menuName: \"" title "\",' \
    'index: \"" menu_index "\",' \
    'reserved menu index already in use' \
    'Edge Gateway menu is not positioned before Administration'
do
    grep -F "$webui_top_level_menu_guard" "$REPO_DIR/router/scripts/webui-mount" >/dev/null || {
        echo "FAIL: Edge Gateway top-level menu guard missing: $webui_top_level_menu_guard" >&2
        exit 1
    }
done

if grep -F 'Tools menu anchor not found' "$REPO_DIR/router/scripts/webui-mount" >/dev/null; then
    echo "FAIL: legacy Administration-tab Edge Gateway mount path remains" >&2
    exit 1
fi

if grep -F -- '-v index="$MENU_INDEX"' "$REPO_DIR/router/scripts/webui-mount" >/dev/null; then
    echo "FAIL: AWK builtin name 'index' is used as a variable in WebUI mount" >&2
    exit 1
fi


for webui_phase4_portal_guard in \
    'safe_http_url()' \
    'EDGE_PORTAL_GRAFANA_URL' \
    'EDGE_PORTAL_NETWORK_DASHBOARD_URL' \
    'EDGE_PORTAL_ENGINEERING_DASHBOARD_URL' \
    'EDGE_PORTAL_DNS_ACTIVITY_URL' \
    'EDGE_PORTAL_PIHOLE_URL' \
    'EDGE_PORTAL_PERSONAL_CLOUD_URL' \
    'portal: {' \
    'edge_portal_grafana_link' \
    'edge_portal_network_link' \
    'edge_portal_engineering_link' \
    'edge_portal_dns_link' \
    'edge_portal_pihole_link' \
    'edge_portal_cloud_link' \
    'rel="noopener noreferrer"'
do
    grep -F "$webui_phase4_portal_guard" \
        "$REPO_DIR/config/edge.conf.example" \
        "$REPO_DIR/router/scripts/webui-status" \
        "$REPO_DIR/router/webui/EdgeGateway.asp" >/dev/null || {
        echo "FAIL: Edge Gateway WebUI Phase 4 portal guard missing: $webui_phase4_portal_guard" >&2
        exit 1
    }
done

for portal_default in \
    EDGE_PORTAL_GRAFANA_URL \
    EDGE_PORTAL_NETWORK_DASHBOARD_URL \
    EDGE_PORTAL_ENGINEERING_DASHBOARD_URL \
    EDGE_PORTAL_DNS_ACTIVITY_URL \
    EDGE_PORTAL_PIHOLE_URL \
    EDGE_PORTAL_PERSONAL_CLOUD_URL
do
    grep -F "$portal_default=\"\"" "$REPO_DIR/config/edge.conf.example" >/dev/null || {
        echo "FAIL: service portal URL must default to empty: $portal_default" >&2
        exit 1
    }
done

if grep -E 'EDGE_PORTAL_[A-Z_]+_URL="https?://(192\.168\.|100\.)' "$REPO_DIR/config/edge.conf.example" >/dev/null; then
    echo "FAIL: deployment-specific private service portal URL found in public example config" >&2
    exit 1
fi

duplicate_webui_ids="$(
    grep -o 'id="[^"]*"' "$REPO_DIR/router/webui/EdgeGateway.asp" |
        sort |
        uniq -d
)"
if [ -n "$duplicate_webui_ids" ]; then
    echo "FAIL: duplicate HTML id(s) in Edge Gateway WebUI: $duplicate_webui_ids" >&2
    exit 1
fi

for webui_phase3_guard in \
    'window.edgeGatewayStatus' \
    'system: {' \
    'services: {' \
    'tailscale: {' \
    'policy: {' \
    'firewall: {' \
    'lanDnsRedirectPackets' \
    'projectOwnsNetfilter' \
    'edge_svc_pihole' \
    'edge_fw_input_accept' \
    'edgeRunningState' \
    'edgeSchedulerState' \
    'totalKiB < 1048576' \
    'edge_unbound_snapshot'
do
    grep -F "$webui_phase3_guard" \
        "$REPO_DIR/router/scripts/webui-status" \
        "$REPO_DIR/router/webui/EdgeGateway.asp" >/dev/null || {
        echo "FAIL: Edge Gateway WebUI Phase 3 guard missing: $webui_phase3_guard" >&2
        exit 1
    }
done

if grep -F 'window.edgeGatewayStatus' "$REPO_DIR/router/scripts/webui-status" |
    grep -E '100\.[0-9]+\.|192\.168\.' >/dev/null; then
    echo "FAIL: Phase 3 WebUI snapshot contains hard-coded private deployment addresses" >&2
    exit 1
fi

grep -F '"$ADDON_DIR/bin/webui-mount" unmount' "$REPO_DIR/scripts/uninstall.sh" >/dev/null || {
    echo "FAIL: uninstall does not remove Edge Gateway WebUI runtime state" >&2
    exit 1
}

grep -F 'unmount_polish_overlay || return 1' "$REPO_DIR/router/scripts/webui-mount" >/dev/null || {
    echo "FAIL: WebUI unmount does not remove the Polish overlay first" >&2
    exit 1
}

if grep -F '"$service" restart' "$REPO_DIR/router/scripts/services-start" >/dev/null; then
    echo "FAIL: Entware service restart present in boot path" >&2
    exit 1
fi

grep -F 'EDGE_RUN_RC_UNSLUNG="0"' "$REPO_DIR/config/edge.conf.example" >/dev/null || {
    echo "FAIL: rc.unslung must be externally owned by default" >&2
    exit 1
}

for startup_coordination in \
    'amtm_entware_startup_detected()' \
    'wait_for_amtm_entware_startup()' \
    '[ "$EDGE_RUN_RC_UNSLUNG" = "1" ]' \
    'EDGE_ENTWARE_QUIET_SECONDS:=20' \
    'EDGE_SERVICE_START_ATTEMPTS:=6' \
    'process_stays_running()' \
    'remove_stale_process_pidfile()'
do
    grep -F "$startup_coordination" "$REPO_DIR/router/scripts/services-start" >/dev/null || {
        echo "FAIL: Entware startup coordination missing: $startup_coordination" >&2
        exit 1
    }
done

grep -F 'EDGE_TS_NETFILTER_MODE:=off' \
    "$REPO_DIR/router/scripts/services-start" >/dev/null || {
    echo "FAIL: services-start does not default Tailscale netfilter mode to off" >&2
    exit 1
}

grep -F -- '--netfilter-mode="$EDGE_TS_NETFILTER_MODE"' \
    "$REPO_DIR/router/scripts/services-start" >/dev/null || {
    echo "FAIL: services-start does not enforce the configured Tailscale netfilter mode" >&2
    exit 1
}

grep -F -- '--netfilter-mode=off' "$REPO_DIR/README.md" >/dev/null || {
    echo "FAIL: README Tailscale setup does not disable native netfilter management" >&2
    exit 1
}

grep -F 'EDGE_TS_NETFILTER_MODE="off"' \
    "$REPO_DIR/config/edge.conf.example" >/dev/null || {
    echo "FAIL: example config does not document Tailscale netfilter ownership" >&2
    exit 1
}

for tailscale_netfilter_health_guard in \
    'Tailscale netfilter management disabled' \
    'no competing Tailscale netfilter chains' \
    'ts-postrouting'
do
    grep -F "$tailscale_netfilter_health_guard" \
        "$REPO_DIR/scripts/healthcheck.sh" >/dev/null || {
        echo "FAIL: Tailscale netfilter health guard missing: $tailscale_netfilter_health_guard" >&2
        exit 1
    }
done

for tailscale_startup_guard in \
    'swap_is_required()' \
    'wait_for_required_swap()' \
    'start_tailscaled_with_retry()' \
    'wait_for_tailscale_api()' \
    'EDGE_REQUIRE_SWAP:=auto' \
    'EDGE_TS_READY_WAIT_SECONDS:=20' \
    'failed to stabilize tailscaled' \
    'required Tailscale daemon failed to start' \
    'startup_failed=1'
do
    grep -F "$tailscale_startup_guard" "$REPO_DIR/router/scripts/services-start" >/dev/null || {
        echo "FAIL: guarded Tailscale startup missing: $tailscale_startup_guard" >&2
        exit 1
    }
done

for webui_security_health_guard in \
    'EDGE_REQUIRE_WAN_WEBUI_DISABLED:=1' \
    'EDGE_REQUIRE_ACCESS_RESTRICTION:=1' \
    'EDGE_EXPECT_HTTP_AUTOLOGOUT:=' \
    'router WebUI disabled from WAN' \
    'router management access restriction enabled' \
    'router management access restriction rule list present' \
    'WebUI auto logout matches expected policy'
do
    grep -F "$webui_security_health_guard" "$REPO_DIR/scripts/healthcheck.sh" >/dev/null || {
        echo "FAIL: WebUI security drift guard missing: $webui_security_health_guard" >&2
        exit 1
    }
done

for webui_security_config_guard in \
    'EDGE_REQUIRE_WAN_WEBUI_DISABLED="1"' \
    'EDGE_REQUIRE_ACCESS_RESTRICTION="1"' \
    'EDGE_EXPECT_HTTP_AUTOLOGOUT=""'
do
    grep -F "$webui_security_config_guard" "$REPO_DIR/config/edge.conf.example" >/dev/null || {
        echo "FAIL: WebUI security drift config missing: $webui_security_config_guard" >&2
        exit 1
    }
done

for swap_health_guard in \
    'EDGE_REQUIRE_SWAP:=auto' \
    'required swap active' \
    'required swap inactive'
do
    grep -F "$swap_health_guard" "$REPO_DIR/scripts/healthcheck.sh" >/dev/null || {
        echo "FAIL: required-swap health check missing: $swap_health_guard" >&2
        exit 1
    }
done

for startup_failure_guard in \
    'startup_failed=0' \
    'startup_failed=1' \
    'ERROR: required service startup failed'
do
    grep -F "$startup_failure_guard" "$REPO_DIR/router/scripts/services-start" >/dev/null || {
        echo "FAIL: required service failure is not propagated: $startup_failure_guard" >&2
        exit 1
    }
done

for startup_guard in \
    'pidof "$process_name"' \
    '"$service_path" start >>"$service_log" 2>&1' \
    '/tmp/asus-edge-unbound-start.log' \
    '/tmp/asus-edge-syslog-ng-start.log'
do
    grep -F "$startup_guard" "$REPO_DIR/router/scripts/services-start" >/dev/null || {
        echo "FAIL: guarded Entware startup missing: $startup_guard" >&2
        exit 1
    }
done

for direct_unbound_guard in \
    'start_unbound_direct_if_stopped()' \
    'resolve_unbound_config()' \
    '"$EDGE_UNBOUND_BIN" -c "$unbound_config"' \
    'unbound-checkconf "$unbound_config"' \
    'EDGE_UNBOUND_BIN="/opt/sbin/unbound"'
do
    grep -F "$direct_unbound_guard" \
        "$REPO_DIR/router/scripts/services-start" \
        "$REPO_DIR/config/edge.conf.example" >/dev/null || {
        echo "FAIL: direct Unbound recovery missing: $direct_unbound_guard" >&2
        exit 1
    }
done

for loader_guard in \
    'EDGE_ENTWARE_LD_LIBRARY_PATH:=/opt/lib:/opt/usr/lib' \
    'LD_LIBRARY_PATH="$EDGE_ENTWARE_LD_LIBRARY_PATH"' \
    'EDGE_ENTWARE_LD_LIBRARY_PATH="/opt/lib:/opt/usr/lib"'
do
    grep -F "$loader_guard" \
        "$REPO_DIR/router/scripts/services-start" \
        "$REPO_DIR/config/edge.conf.example" >/dev/null || {
        echo "FAIL: scoped Entware loader guard missing: $loader_guard" >&2
        exit 1
    }
done

if grep -F '/opt/etc/init.d/S*unbound' "$REPO_DIR/router/scripts/services-start" >/dev/null; then
    echo "FAIL: Unbound recovery still uses the init wrapper" >&2
    exit 1
fi

if grep -E 'iptables .*-(I|A) (INPUT|FORWARD) -i tailscale\+? -j ACCEPT' "$REPO_DIR/router/scripts/firewall-start" >/dev/null; then
    echo "FAIL: broad Tailscale ACCEPT rule found" >&2
    exit 1
fi

for file in \
    "$REPO_DIR/router/scripts/firewall-start" \
    "$REPO_DIR/router/scripts/services-start" \
    "$REPO_DIR/scripts/install.sh" \
    "$REPO_DIR/scripts/backup.sh" \
    "$REPO_DIR/scripts/restore.sh" \
    "$REPO_DIR/scripts/healthcheck.sh" \
    "$REPO_DIR/scripts/collect-evidence.sh" \
    "$REPO_DIR/scripts/update-tailscale.sh" \
    "$REPO_DIR/scripts/uninstall.sh"
do
    if sed '/^[[:space:]]*#/d' "$file" | grep -F 'command -v' >/dev/null; then
        echo "FAIL: BusyBox-incompatible command discovery in $file" >&2
        exit 1
    fi
done

for file in \
    "$REPO_DIR/router/scripts/services-start" \
    "$REPO_DIR/scripts/healthcheck.sh"
do
    grep -F 'opt_is_ready()' "$file" >/dev/null || {
        echo "FAIL: Entware readiness helper missing in $file" >&2
        exit 1
    }
    grep -F '/opt/bin/opkg' "$file" >/dev/null || {
        echo "FAIL: Entware readiness does not verify opkg in $file" >&2
        exit 1
    }
    if grep -F 'mountpoint -q /opt' "$file" >/dev/null; then
        echo "FAIL: symlink-incompatible /opt mountpoint check in $file" >&2
        exit 1
    fi
done

for file in \
    "$REPO_DIR/scripts/backup.sh" \
    "$REPO_DIR/scripts/restore.sh" \
    "$REPO_DIR/scripts/update-tailscale.sh"
do
    grep -F 'PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"' "$file" >/dev/null || {
        echo "FAIL: deterministic router PATH missing in $file" >&2
        exit 1
    }
done

for file in \
    "$REPO_DIR/scripts/install.sh" \
    "$REPO_DIR/scripts/backup.sh" \
    "$REPO_DIR/scripts/restore.sh" \
    "$REPO_DIR/scripts/update-tailscale.sh" \
    "$REPO_DIR/scripts/uninstall.sh"
do
    if grep -F '$(id -u)' "$file" >/dev/null; then
        echo "FAIL: direct id invocation without BusyBox fallback in $file" >&2
        exit 1
    fi
    grep -F '</proc/self/status' "$file" >/dev/null || {
        echo "FAIL: procfs UID detection missing in $file" >&2
        exit 1
    }
done

for file in \
    "$REPO_DIR/scripts/backup.sh" \
    "$REPO_DIR/scripts/restore.sh" \
    "$REPO_DIR/scripts/collect-evidence.sh"
do
    grep -F '/bin/busybox sha256sum' "$file" >/dev/null || {
        echo "FAIL: BusyBox SHA-256 fallback missing in $file" >&2
        exit 1
    }
done

for file in \
    "$REPO_DIR/scripts/backup.sh" \
    "$REPO_DIR/scripts/restore.sh"
do
    if grep -F 'mktemp ' "$file" >/dev/null; then
        echo "FAIL: unavailable mktemp dependency in $file" >&2
        exit 1
    fi
    grep -F 'secure_temp_dir()' "$file" >/dev/null || {
        echo "FAIL: atomic temporary-directory helper missing in $file" >&2
        exit 1
    }
done

grep -F 'coreutils-sha256sum' "$REPO_DIR/README.md" >/dev/null || {
    echo "FAIL: SHA-256 backup dependency is undocumented" >&2
    exit 1
}

grep -F 'interface=tailscale0' "$REPO_DIR/config/dnsmasq.conf.add.example" >/dev/null || {
    echo "FAIL: dnsmasq example does not include tailscale0" >&2
    exit 1
}

grep -F 'dnsmasq does not include $EDGE_TS_IF' "$REPO_DIR/scripts/healthcheck.sh" >/dev/null || {
    echo "FAIL: healthcheck does not validate the dnsmasq Tailscale listener" >&2
    exit 1
}

grep -F 'EDGE_RUN_LEGACY_HOOKS="0"' "$REPO_DIR/config/edge.conf.example" >/dev/null || {
    echo "FAIL: legacy hooks are not disabled by default" >&2
    exit 1
}


for dns_guard_guard in \
    'router/scripts/dns-guard" "$ADDON_DIR/bin/dns-guard" 0755' \
    'router/scripts/edge-dns-breakglass.sh" "$JFFS_DIR/scripts/edge-dns-breakglass.sh" 0700' \
    'EDGE_DNS_GUARD_WATCHDOG="1"' \
    'configure_dns_guard_watchdog()' \
    'cru a AsusEdgeDNSGuard' \
    'DNS_GUARD="${EDGE_DNS_GUARD:-/jffs/addons/asus-edge/bin/dns-guard}"'
do
    grep -F "$dns_guard_guard" \
        "$REPO_DIR/scripts/install.sh" \
        "$REPO_DIR/config/edge.conf.example" \
        "$REPO_DIR/router/scripts/services-start" \
        "$REPO_DIR/router/scripts/wan-event-handler" >/dev/null || {
        echo "FAIL: DNS Guard integration missing: $dns_guard_guard" >&2
        exit 1
    }
done

if grep -F 'nameserver 127.0.0.1' "$REPO_DIR/router/scripts/wan-event-handler" >/dev/null; then
    echo "FAIL: WAN handler still hard-codes the local resolver instead of DNS Guard" >&2
    exit 1
fi

sh "$REPO_DIR/tests/test-dns-guard.sh"
sh "$REPO_DIR/tests/test-dns-breakglass.sh"
sh "$REPO_DIR/tests/test-wan-event-handler.sh"


grep -F 'EDGE_LAN_DNS_BYPASS_IPS=""' "$REPO_DIR/config/edge.conf.example" >/dev/null || {
    echo "FAIL: LAN DNS bypass configuration guard missing" >&2
    exit 1
}

for lan_dns_bypass_guard in \
    'EDGE_LAN_DNS_BYPASS_IPS:=}"' \
    'invalid LAN DNS bypass IPv4' \
    'LAN DNS bypass UDP return rule failed' \
    'LAN DNS bypass TCP return rule failed'
do
    grep -F "$lan_dns_bypass_guard" "$REPO_DIR/router/scripts/firewall-start" >/dev/null || {
        echo "FAIL: firewall LAN DNS bypass guard missing: $lan_dns_bypass_guard" >&2
        exit 1
    }
done

for lan_dns_bypass_health_guard in \
    'EDGE_LAN_DNS_BYPASS_IPS:=}"' \
    'invalid EDGE_LAN_DNS_BYPASS_IPS IPv4' \
    'bypass_count = split(bypasses' \
    'expected_rules = 4 + (2 * bypass_count)'
do
    grep -F "$lan_dns_bypass_health_guard" "$REPO_DIR/scripts/healthcheck.sh" >/dev/null || {
        echo "FAIL: healthcheck LAN DNS bypass guard missing: $lan_dns_bypass_health_guard" >&2
        exit 1
    }
done

grep -F '${EDGE_RUN_LEGACY_HOOKS:-0}' "$REPO_DIR/scripts/install.sh" >/dev/null || {
    echo "FAIL: installer does not gate preserved legacy hooks" >&2
    exit 1
}

for syslog_config in \
    "$REPO_DIR/config/syslog-ng.conf.example" \
    "$REPO_DIR/config/syslog-ng-collector.conf.example"
do
    grep -F 'ca-file(' "$syslog_config" >/dev/null || {
        echo "FAIL: trusted CA is missing from $syslog_config" >&2
        exit 1
    }
    grep -F 'peer-verify(required-trusted)' "$syslog_config" >/dev/null || {
        echo "FAIL: mTLS peer verification is not required in $syslog_config" >&2
        exit 1
    }
    if grep -F 'peer-verify(optional-untrusted)' "$syslog_config" >/dev/null; then
        echo "FAIL: insecure transitional TLS policy remains in $syslog_config" >&2
        exit 1
    fi
done

for router_identity_option in \
    'key-file("/opt/etc/syslog-ng/tls/router-client.key")' \
    'cert-file("/opt/etc/syslog-ng/tls/router-client.crt")' \
    'disk-buffer(' \
    'reliable(yes)'
do
    grep -F "$router_identity_option" "$REPO_DIR/config/syslog-ng.conf.example" >/dev/null || {
        echo "FAIL: router mTLS/buffer option missing: $router_identity_option" >&2
        exit 1
    }
done

grep -F '"/tmp/syslog.log"' "$REPO_DIR/config/syslog-ng.conf.example" >/dev/null || {
    echo "FAIL: router syslog-ng does not tail the Asuswrt log" >&2
    exit 1
}

# Local archival must not be stopped by backpressure from the remote collector.
# A 2026-10-01 live fault test reproduced that failure when hard flow-control
# was applied to the shared local+remote log path.
if grep -F 'flags(flow-control);' "$REPO_DIR/config/syslog-ng.conf.example" >/dev/null; then
    echo "FAIL: hard syslog-ng flow-control can block the local archive during collector outage" >&2
    exit 1
fi

for syslog_fanout_guard in 'destination(d_local_archive);' 'destination(d_remote_tls);'
do
    grep -F "$syslog_fanout_guard" "$REPO_DIR/config/syslog-ng.conf.example" >/dev/null || {
        echo "FAIL: syslog-ng local/remote fan-out guard missing: $syslog_fanout_guard" >&2
        exit 1
    }
done

if grep -F 'system();' "$REPO_DIR/config/syslog-ng.conf.example" >/dev/null; then
    echo "FAIL: router syslog-ng conflicts with the firmware logging sockets" >&2
    exit 1
fi

if find "$REPO_DIR" -path "$REPO_DIR/.git" -prune -o -type f -name '*.key' -print | grep -q .; then
    echo "FAIL: private-key file found in repository" >&2
    exit 1
fi

RETENTION_SCRIPT="$REPO_DIR/scripts/asus-edge-log-retention.sh"

for retention_guard in \
    'ASUS_EDGE_LOG_ROOT:-/var/log/asus-edge' \
    'ASUS_EDGE_COMPRESS_AFTER_MINUTES:-1440' \
    'ASUS_EDGE_DELETE_AFTER_MINUTES:-43200' \
    '! -name "$TODAY_LOG"' \
    'case "${1:---dry-run}"'
do
    grep -F "$retention_guard" "$RETENTION_SCRIPT" >/dev/null || {
        echo "FAIL: collector retention guard missing: $retention_guard" >&2
        exit 1
    }
done

if grep -F 'rm -rf' "$RETENTION_SCRIPT" >/dev/null; then
    echo "FAIL: broad recursive deletion found in collector retention script" >&2
    exit 1
fi

for retention_doc in \
    "$REPO_DIR/docs/centralized-logging.md" \
    "$REPO_DIR/docs/operations.md"
do
    grep -F 'asus-edge-log-retention.sh' "$retention_doc" >/dev/null || {
        echo "FAIL: collector retention helper undocumented in $retention_doc" >&2
        exit 1
    }
done

for printer_service in lpd u2ec; do
    grep -F "$printer_service" "$REPO_DIR/scripts/check-usb-exposure.sh" >/dev/null || {
        echo "FAIL: USB exposure audit does not inspect $printer_service" >&2
        exit 1
    }
    grep -F "$printer_service" "$REPO_DIR/scripts/healthcheck.sh" >/dev/null || {
        echo "FAIL: healthcheck does not inspect $printer_service" >&2
        exit 1
    }
done

sh "$REPO_DIR/tests/test-usb-exposure.sh"

# Firewall policy rebuilds must be serialized because Merlin may invoke
# firewall-start concurrently from multiple startup/event paths.
for firewall_lock_guard in \
    'EDGE_FIREWALL_LOCK="/tmp/asus-edge-firewall.lock"' \
    'executable_exists flock >/dev/null 2>&1 || die "flock not found; cannot serialize firewall policy rebuild"' \
    'exec 9>"$EDGE_FIREWALL_LOCK"' \
    'flock -x 9'
do
    grep -F "$firewall_lock_guard" \
        "$REPO_DIR/router/scripts/firewall-start" >/dev/null || {
        echo "FAIL: firewall serialization guard missing: $firewall_lock_guard" >&2
        exit 1
    }
done

# WAN-connected handling must allow services-start enough time to recover
# the local Unbound path. This is a maximum wait; the handler exits early
# as soon as DNS becomes ready.
grep -F 'EDGE_WAN_DNS_WAIT_SECONDS="90"' \
    "$REPO_DIR/config/edge.conf.example" >/dev/null || {
    echo "FAIL: example config does not preserve the validated WAN DNS startup wait" >&2
    exit 1
}


GRAFANA_ALERTS="$REPO_DIR/monitoring/grafana/provisioning/alerting/asus-tuf-alerts.yml"
GRAFANA_EMAIL_CONTACT="$REPO_DIR/monitoring/grafana/provisioning/alerting/asus-email-contact.yml"

for grafana_routercloud_guard in \
    'uid: routercloud_backup_bad' \
    'uid: routercloud_backup_stale' \
    'uid: routercloud_maintenance_bad' \
    'uid: routercloud_maintenance_stale' \
    "last_over_time(routercloud_backup_last_run_success[24h])" \
    "time() - last_over_time(routercloud_backup_last_run_timestamp_seconds[24h])" \
    "last_over_time(routercloud_maintenance_last_run_success[30d])" \
    "time() - last_over_time(routercloud_maintenance_last_run_timestamp_seconds[30d])" \
    'params: [28800]' \
    'params: [691200]' \
    'receiver: ASUS Edge Gateway Email'
do
    grep -F "$grafana_routercloud_guard" "$GRAFANA_ALERTS" >/dev/null || {
        echo "FAIL: Grafana RouterCloud alerting guard missing: $grafana_routercloud_guard" >&2
        exit 1
    }
done

for grafana_contact_guard in \
    'name: ASUS Edge Gateway Email' \
    'uid: asus_edge_email' \
    'disableResolveMessage: false'
do
    grep -F "$grafana_contact_guard" "$GRAFANA_EMAIL_CONTACT" >/dev/null || {
        echo "FAIL: Grafana e-mail contact guard missing: $grafana_contact_guard" >&2
        exit 1
    }
done

printf '%s\n' "Static tests passed."
