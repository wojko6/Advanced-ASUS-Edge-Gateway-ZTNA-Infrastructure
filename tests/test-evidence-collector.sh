#!/bin/sh

set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

cat >"$TMP_DIR/iptables" <<'EOF'
#!/bin/sh
echo "Chain EDGE_TEST (1 references)"
echo "num  pkts bytes target prot opt in out source destination"
echo "1 10 640 ACCEPT tcp -- tailscale0 * 100.64.0.10 192.168.50.1 tcp dpt:8443"
EOF

cat >"$TMP_DIR/dig" <<'EOF'
#!/bin/sh
echo ";; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1"
echo ";; flags: qr rd ra ad; QUERY: 1, ANSWER: 1"
echo ";; Query time: 12 msec"
EOF

cat >"$TMP_DIR/healthcheck" <<'EOF'
#!/bin/sh
echo "[OK] mock healthcheck"
EOF

chmod +x "$TMP_DIR/iptables" "$TMP_DIR/dig" "$TMP_DIR/healthcheck"

EVIDENCE_IPTABLES="$TMP_DIR/iptables" \
EVIDENCE_IP6TABLES="$TMP_DIR/iptables" \
EVIDENCE_DIG="$TMP_DIR/dig" \
EVIDENCE_HEALTHCHECK="$TMP_DIR/healthcheck" \
sh "$REPO_DIR/scripts/collect-evidence.sh" "$TMP_DIR/output" >/dev/null

for file in README.md environment.md healthcheck.md firewall-counters.md dns-validation.md; do
    [ -s "$TMP_DIR/output/$file" ] || {
        echo "FAIL: evidence collector did not create $file" >&2
        exit 1
    }
done

if grep -E '100\.64\.0\.10|192\.168\.50\.1' "$TMP_DIR/output/firewall-counters.md" >/dev/null; then
    echo "FAIL: firewall addresses were not redacted" >&2
    exit 1
fi

grep -F '[source-redacted]' "$TMP_DIR/output/firewall-counters.md" >/dev/null
grep -F '[destination-redacted]' "$TMP_DIR/output/firewall-counters.md" >/dev/null
grep -F 'PASS (AD flag present)' "$TMP_DIR/output/dns-validation.md" >/dev/null
grep -F '[OK] mock healthcheck' "$TMP_DIR/output/healthcheck.md" >/dev/null

if [ -f "$TMP_DIR/output/SHA256SUMS" ]; then
    (cd "$TMP_DIR/output" && sha256sum -c SHA256SUMS >/dev/null)
fi

echo "PASS: evidence collector"
