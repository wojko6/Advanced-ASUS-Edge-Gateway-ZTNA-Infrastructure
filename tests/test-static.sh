#!/bin/sh

set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"

find "$REPO_DIR/router" "$REPO_DIR/scripts" "$REPO_DIR/tests" -type f \( -name '*.sh' -o -path '*/router/scripts/*' \) | while IFS= read -r file; do
    sh -n "$file"
done

grep -F 'Installed Advanced ASUS Edge Gateway v2.1.1' "$REPO_DIR/scripts/install.sh" >/dev/null || {
    echo "FAIL: installer version does not match release v2.1.1" >&2
    exit 1
}

[ "$(cat "$REPO_DIR/VERSION")" = "2.1.1" ] || {
    echo "FAIL: VERSION does not match release v2.1.1" >&2
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
    '/jffs/configs/dnsmasq.conf.add "$WORK_DIR/jffs/configs/"'
do
    grep -F "$backup_path" "$REPO_DIR/scripts/backup.sh" >/dev/null || {
        echo "FAIL: backup does not preserve $backup_path" >&2
        exit 1
    }
done

if grep -F 'opkg update && opkg upgrade tailscale' "$REPO_DIR/router/scripts/services-start" >/dev/null; then
    echo "FAIL: package upgrade present in boot path" >&2
    exit 1
fi

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

for service_guard in \
    'ExecStart=/usr/local/sbin/asus-edge-log-retention --apply' \
    'ProtectSystem=strict' \
    'ProtectHome=true' \
    'ReadWritePaths=/var/log/asus-edge'
do
    grep -F "$service_guard" "$REPO_DIR/config/systemd/asus-edge-log-retention.service" >/dev/null || {
        echo "FAIL: retention service hardening missing: $service_guard" >&2
        exit 1
    }
done

for timer_guard in \
    'OnCalendar=*-*-* 03:20:00' \
    'Persistent=true' \
    'RandomizedDelaySec=10m'
do
    grep -F "$timer_guard" "$REPO_DIR/config/systemd/asus-edge-log-retention.timer" >/dev/null || {
        echo "FAIL: retention timer guard missing: $timer_guard" >&2
        exit 1
    }
done

"$TEST_DIR/test-log-retention.sh"
"$TEST_DIR/test-firewall-mock.sh"
"$TEST_DIR/test-config-validation.sh"
"$TEST_DIR/test-evidence-collector.sh"
python3 "$TEST_DIR/test-recovery.py"
echo "PASS: static test suite"
