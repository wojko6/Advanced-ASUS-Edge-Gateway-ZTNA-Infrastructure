#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"

FIREWALL="$REPO_DIR/router/scripts/firewall-start"
EDGE_CONFIG="$REPO_DIR/config/edge.conf.example"
DUFS_CONFIG="$REPO_DIR/config/dufs-personal-cloud.yaml.example"
S66="$REPO_DIR/router/init.d/S66routercloud-ip"
S67="$REPO_DIR/router/init.d/S67routercloud"
POST_MOUNT="$REPO_DIR/router/scripts/routercloud-post-mount"
DNSMASQ="$REPO_DIR/config/dnsmasq.conf.add.example"

for file in "$FIREWALL" "$EDGE_CONFIG" "$DUFS_CONFIG" "$S66" "$S67" "$POST_MOUNT" "$DNSMASQ"; do
    [ -r "$file" ] || {
        echo "FAIL: missing RouterCloud file: $file" >&2
        exit 1
    }
done

for guard in     'EDGE_ROUTERCLOUD_TS_SOURCES:=}"'     'EDGE_ROUTERCLOUD_IP:=}"'     'EDGE_ROUTERCLOUD_PORT:=443}"'     'RouterCloud sources configured without EDGE_ROUTERCLOUD_IP'     'invalid RouterCloud IPv4'     'add_routercloud_input_rules()'     '-d "$EDGE_ROUTERCLOUD_IP/32"'     'RouterCloud HTTPS rule failed'     'add_routercloud_input_rules'
do
    grep -F -- "$guard" "$FIREWALL" >/dev/null || {
        echo "FAIL: RouterCloud firewall guard missing: $guard" >&2
        exit 1
    }
done

for config_guard in     'EDGE_ROUTERCLOUD_TS_SOURCES=""'     'EDGE_ROUTERCLOUD_IP=""'     'EDGE_ROUTERCLOUD_PORT="443"'     'EDGE_ROUTERCLOUD_ROOT="/tmp/mnt/ROUTER_DATA/RouterCloud"'     'EDGE_ROUTER_HTTPS_PORT="8443"'     'EDGE_ROUTER_HTTPS_TARGET_PORT="443"'
do
    grep -F "$config_guard" "$EDGE_CONFIG" >/dev/null || {
        echo "FAIL: RouterCloud example configuration missing: $config_guard" >&2
        exit 1
    }
done

for dufs_guard in     'serve-path: /tmp/mnt/ROUTER_DATA/RouterCloud'     'allow-move: true'     'allow-delete: false'     'allow-symlink: false'     'tls-cert: /opt/etc/routercloud/tls/cloud.home.arpa.crt'     'tls-key: /opt/etc/routercloud/tls/cloud.home.arpa.key'
do
    grep -F "$dufs_guard" "$DUFS_CONFIG" >/dev/null || {
        echo "FAIL: Dufs hardening setting missing: $dufs_guard" >&2
        exit 1
    }
done

grep -F 'REPLACE_WITH_SHA512_CRYPT_HASH' "$DUFS_CONFIG" >/dev/null || {
    echo "FAIL: Dufs example does not force authentication replacement" >&2
    exit 1
}

grep -F 'host-record=cloud.home.arpa,192.168.50.254' "$DNSMASQ" >/dev/null || {
    echo "FAIL: RouterCloud dnsmasq record missing" >&2
    exit 1
}

grep -F 'deferred: RouterCloud storage not ready; post-mount will retry' "$S67" >/dev/null || {
    echo "FAIL: RouterCloud storage-race deferral missing" >&2
    exit 1
}

grep -F 'daemonize' "$S67" >/dev/null || {
    echo "FAIL: RouterCloud daemon detachment dependency missing" >&2
    exit 1
}

grep -F 'RouterCloud startup completed after mount event' "$POST_MOUNT" >/dev/null || {
    echo "FAIL: RouterCloud post-mount recovery logging missing" >&2
    exit 1
}

for management_guard in \
    'EDGE_ROUTER_HTTPS_TARGET_PORT:=443}' \
    'router HTTPS ingress port conflicts with RouterCloud port' \
    '-d "$EDGE_ROUTER_LAN_IP/32" -p tcp --dport "$EDGE_ROUTER_HTTPS_TARGET_PORT"' \
    '--to-destination "$EDGE_ROUTER_LAN_IP:$EDGE_ROUTER_HTTPS_TARGET_PORT"'
do
    grep -F -- "$management_guard" "$FIREWALL" >/dev/null || {
        echo "FAIL: router-management ingress/target split missing: $management_guard" >&2
        exit 1
    }
done

sh -n "$S66"
sh -n "$S67"
sh -n "$POST_MOUNT"

echo "PASS: RouterCloud browser-access static guards"
