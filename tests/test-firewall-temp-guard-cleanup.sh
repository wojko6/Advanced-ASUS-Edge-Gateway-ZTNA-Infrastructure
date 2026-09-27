#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

FUNCS="$TMP_DIR/guard-functions.sh"
awk '
    /^remove_temp_ingress_drop_guards\(\)/ { capture=1 }
    /^remove_legacy_tailscale_rules\(\)/ { capture=0 }
    capture { print }
' "$REPO_DIR/router/scripts/firewall-start" >"$FUNCS"

grep -F 'remove_temp_ingress_drop_guards()' "$FUNCS" >/dev/null || {
    echo "FAIL: could not extract guard cleanup helper" >&2
    exit 1
}

STATE="$TMP_DIR/forward.rules"
cat >"$STATE" <<'RULES'
-P FORWARD ACCEPT
-A FORWARD -i tailscale0 -j DROP
-A FORWARD -i tailscale0 -j DROP
-A FORWARD -i br0 -j DROP
-A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT
RULES
export STATE

MOCK="$TMP_DIR/iptables"
cat >"$MOCK" <<'EOF'
#!/bin/sh
set -eu
case "$*" in
    "-t filter -S FORWARD")
        cat "$STATE"
        ;;
    "-t filter -D FORWARD -i tailscale0 -j DROP")
        if ! grep -F -x -e "-A FORWARD -i tailscale0 -j DROP" "$STATE" >/dev/null; then
            exit 1
        fi
        TMP="$STATE.tmp"
        removed=0
        : >"$TMP"
        while IFS= read -r line; do
            if [ "$removed" -eq 0 ] && [ "$line" = "-A FORWARD -i tailscale0 -j DROP" ]; then
                removed=1
                continue
            fi
            printf '%s\n' "$line" >>"$TMP"
        done <"$STATE"
        mv "$TMP" "$STATE"
        ;;
    *)
        echo "unexpected mock iptables call: $*" >&2
        exit 1
        ;;
esac
EOF
chmod +x "$MOCK"

die() {
    echo "FAIL: $*" >&2
    exit 1
}

# shellcheck disable=SC1090
. "$FUNCS"

remove_temp_ingress_drop_guards "$MOCK" FORWARD tailscale0

if grep -F -x -e "-A FORWARD -i tailscale0 -j DROP" "$STATE" >/dev/null; then
    echo "FAIL: stale exact Tailscale guard remains" >&2
    exit 1
fi

grep -F -x -e "-A FORWARD -i br0 -j DROP" "$STATE" >/dev/null || {
    echo "FAIL: unrelated DROP rule was removed" >&2
    exit 1
}

grep -F -x -e "-A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT" "$STATE" >/dev/null || {
    echo "FAIL: established/related rule was altered" >&2
    exit 1
}

echo "PASS: stale temporary Tailscale guards are removed without touching unrelated firewall rules"
