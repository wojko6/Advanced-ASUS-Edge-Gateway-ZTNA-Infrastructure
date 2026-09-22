#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

FUNCS="$TMP_DIR/drift-functions.sh"
awk '
    /^direct_parent_tailscale_nat_rule_count\(\)/ { capture=1 }
    /^input_jumps=/ { capture=0 }
    capture { print }
' "$REPO_DIR/scripts/healthcheck.sh" >"$FUNCS"

for function_name in direct_parent_tailscale_nat_rule_count active_jffs_hook_is_unsafe; do
    grep -F "$function_name()" "$FUNCS" >/dev/null || {
        echo "FAIL: could not extract $function_name from healthcheck" >&2
        exit 1
    }
done

MOCK_BIN="$TMP_DIR/bin"
mkdir -p "$MOCK_BIN"

cat >"$MOCK_BIN/iptables" <<'EOF'
#!/bin/sh
case "$*" in
    "-t nat -S PREROUTING")
        case "${FIXTURE:-good}" in
            direct-dns)
                cat <<'RULES'
-P PREROUTING ACCEPT
-A PREROUTING -i tailscale0 -j EDGE_TS_PREROUTING
-A PREROUTING -i tailscale0 -p udp -m udp --dport 53 -j REDIRECT --to-ports 53
-A PREROUTING -i tailscale0 -p tcp -m tcp --dport 53 -j REDIRECT --to-ports 53
RULES
                ;;
            direct-https)
                cat <<'RULES'
-P PREROUTING ACCEPT
-A PREROUTING -i tailscale0 -j EDGE_TS_PREROUTING
-A PREROUTING -i tailscale0 -p tcp -m tcp --dport 8443 -j DNAT --to-destination 192.0.2.1:8443
RULES
                ;;
            *)
                cat <<'RULES'
-P PREROUTING ACCEPT
-A PREROUTING -i tailscale0 -j EDGE_TS_PREROUTING
-A PREROUTING -d 198.51.100.10/32 -j VSERVER
RULES
                ;;
        esac
        ;;
    *)
        exit 1
        ;;
esac
EOF
chmod +x "$MOCK_BIN/iptables"

PATH="$MOCK_BIN:/usr/bin:/bin"
export PATH
EDGE_TS_IF=tailscale0
export EDGE_TS_IF

# shellcheck disable=SC1090
. "$FUNCS"

FIXTURE=good
export FIXTURE
[ "$(direct_parent_tailscale_nat_rule_count)" = "0" ] || {
    echo "FAIL: project-owned parent jump was treated as direct NAT drift" >&2
    exit 1
}

FIXTURE=direct-dns
export FIXTURE
[ "$(direct_parent_tailscale_nat_rule_count)" = "2" ] || {
    echo "FAIL: direct legacy DNS redirects were not detected" >&2
    exit 1
}

FIXTURE=direct-https
export FIXTURE
[ "$(direct_parent_tailscale_nat_rule_count)" = "1" ] || {
    echo "FAIL: direct Tailscale DNAT outside the managed chain was not detected" >&2
    exit 1
}

SAFE_HOOK="$TMP_DIR/safe-hook"
GROUP_WRITABLE_HOOK="$TMP_DIR/group-writable-hook"
WORLD_WRITABLE_HOOK="$TMP_DIR/world-writable-hook"
SYMLINK_HOOK="$TMP_DIR/symlink-hook"

: >"$SAFE_HOOK"
: >"$GROUP_WRITABLE_HOOK"
: >"$WORLD_WRITABLE_HOOK"
chmod 0755 "$SAFE_HOOK"
chmod 0775 "$GROUP_WRITABLE_HOOK"
chmod 0757 "$WORLD_WRITABLE_HOOK"
ln -s "$SAFE_HOOK" "$SYMLINK_HOOK"

if active_jffs_hook_is_unsafe "$SAFE_HOOK"; then
    echo "FAIL: mode 0755 hook was rejected" >&2
    exit 1
fi
active_jffs_hook_is_unsafe "$GROUP_WRITABLE_HOOK" || {
    echo "FAIL: group-writable hook was accepted" >&2
    exit 1
}
active_jffs_hook_is_unsafe "$WORLD_WRITABLE_HOOK" || {
    echo "FAIL: world-writable hook was accepted" >&2
    exit 1
}
active_jffs_hook_is_unsafe "$SYMLINK_HOOK" || {
    echo "FAIL: symlinked active hook was accepted" >&2
    exit 1
}

echo "PASS: healthcheck drift guards detect direct parent NAT rules and unsafe active JFFS hook modes"
