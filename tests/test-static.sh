#!/bin/sh

set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"

find "$REPO_DIR/router" "$REPO_DIR/scripts" "$REPO_DIR/tests" -type f \( -name '*.sh' -o -path '*/router/scripts/*' \) | while IFS= read -r file; do
    sh -n "$file"
done

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

for startup_guard in \
    'pidof "$process_name"' \
    '"$service_path" start >"$service_log" 2>&1' \
    '/tmp/asus-edge-unbound-start.log' \
    '/tmp/asus-edge-syslog-ng-start.log'
do
    grep -F "$startup_guard" "$REPO_DIR/router/scripts/services-start" >/dev/null || {
        echo "FAIL: guarded Entware startup missing: $startup_guard" >&2
        exit 1
    }
done

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

"$TEST_DIR/test-firewall-mock.sh"
"$TEST_DIR/test-config-validation.sh"
"$TEST_DIR/test-evidence-collector.sh"
echo "PASS: static test suite"
