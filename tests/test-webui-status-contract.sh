#!/bin/sh
# Issue #283: Fedora/GitHub-runner-only snapshot contract. No ASUS or network access.
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
COLLECTOR="$ROOT/router/scripts/webui-status"
FIREWALL="$ROOT/router/scripts/firewall-start"
UI="$ROOT/router/webui/EdgeGateway.asp"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
OUT="$TMP/out"
CONF="$TMP/edge.conf"

command -v node >/dev/null 2>&1 || {
    echo "FAIL: node is needed to parse the generated JavaScript" >&2
    exit 1
}

# Compare defaults from the actual source scripts; no independent copied values.
for key in EDGE_INTERCEPT_DNS EDGE_ALLOW_ROUTER_HTTPS EDGE_ALLOW_ROUTER_SSH \
    EDGE_ENFORCE_LAN_DNS EDGE_BLOCK_LAN_DOT EDGE_ENABLE_EXIT_NODE
do
    pattern="$(printf ': "${%s:=' "$key")"
    web_default="$(grep -F "$pattern" "$COLLECTOR" | head -n 1)"
    fw_default="$(grep -F "$pattern" "$FIREWALL" | head -n 1)"
    [ -n "$web_default" ] && [ "$web_default" = "$fw_default" ] || {
        echo "FAIL: WebUI/firewall effective default mismatch: $key" >&2
        exit 1
    }
done
echo "PASS: effective status/firewall defaults match"

run_case() {
    name="$1"
    expected="$2"
    sources="$3"
    extra="$4"
    dns="$5"
    https="$6"
    cat > "$CONF" <<CFG
EDGE_ADMIN_TS_SOURCES='$sources'
EDGE_TS_SOCKET='$TMP/no-router-socket'
$extra
CFG
    # Only local /proc, local commands, and a disposable output path.
    EDGE_CONFIG_FILE="$CONF" EDGE_WEBUI_STATUS_DIR="$OUT" \
        sh "$COLLECTOR" > "$TMP/stdout" 2> "$TMP/stderr" || {
            echo "FAIL: collector did not generate fixture: $name" >&2
            cat "$TMP/stderr" >&2
            exit 1
        }
    [ -s "$OUT/status.js" ] || {
        echo "FAIL: missing generated status.js for $name" >&2
        exit 1
    }
    node --check "$OUT/status.js"
    node - "$OUT/status.js" "$UI" "$expected" "$dns" "$https" <<'NODE'
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const snap = fs.readFileSync(process.argv[2], 'utf8');
const html = fs.readFileSync(process.argv[3], 'utf8');
const expected = Number(process.argv[4]);
const expectedDNS = Number(process.argv[5]);
const expectedHTTPS = Number(process.argv[6]);

const ctx = {window: {}};
vm.runInNewContext(snap, ctx);
const data = ctx.window.edgeGatewayStatus;
assert.equal(data.policy.adminSourceCount, expected);
assert.ok(Number.isInteger(data.policy.adminSourceCount));
assert.equal(data.policy.interceptDns, expectedDNS);
assert.equal(data.policy.routerHttps, expectedHTTPS);
assert.ok(Number.isInteger(data.generatedEpoch) && data.generatedEpoch > 0);
assert.doesNotMatch(snap, /198\.51\.100\.10|203\.0\.113\.20/);

const found = html.match(/<script type="text\/javascript">([\s\S]*?)<\/script>/);
assert.ok(found, 'UI inline script must exist');
const js = found[1].replace(/<%[\s\S]*?%>/g, '0');
new vm.Script(js);

const entries = {};
const sandbox = {
  window: {edgeGatewayStatus: data},
  document: {getElementById: id => (entries[id] ||= {innerHTML: ''})},
  console
};
vm.runInNewContext(js, sandbox);

const now = Math.floor(Date.now() / 1000);
assert.equal(sandbox.edgeSnapshotFreshness({generatedEpoch: now}, now), 'fresh');
assert.equal(sandbox.edgeSnapshotFreshness({generatedEpoch: now - 180}, now), 'fresh');
assert.equal(sandbox.edgeSnapshotFreshness({generatedEpoch: now - 181}, now), 'stale');
assert.equal(sandbox.edgeSnapshotFreshness({generatedEpoch: now + 60}, now), 'unknown');
assert.equal(sandbox.edgeSnapshotFreshness({}, now), 'unknown');
assert.equal(sandbox.edgeSnapshotFreshness({generatedEpoch: -1}, now), 'unknown');

data.generatedEpoch = now - 181;
sandbox.renderGatewaySnapshot();
assert.match(entries.edge_snapshot.innerHTML, /Nieaktualna migawka/);
assert.match(entries.edge_unbound_snapshot.innerHTML, /Stan niepotwierdzony/);

data.generatedEpoch = now;
sandbox.renderGatewaySnapshot();
assert.match(entries.edge_snapshot.innerHTML, /aktualne/);

delete data.generatedEpoch;
sandbox.renderGatewaySnapshot();
assert.match(entries.edge_snapshot.innerHTML, /Nieznana świeżość/);
assert.match(entries.edge_unbound_snapshot.innerHTML, /Stan niepotwierdzony/);
NODE
    echo "PASS: $name (adminSourceCount=$expected, JS valid, freshness guarded)"
}

run_case zero 0 '' '' 1 1
run_case one 1 '198.51.100.10' '' 1 1
run_case multiline 3 '198.51.100.10
203.0.113.20
2001:db8::2' '' 1 1
run_case mixed_whitespace 4 '   198.51.100.10   203.0.113.20
    2001:db8::1	2001:db8::2   ' '' 1 1
run_case explicit_disabled_defaults 2 '198.51.100.10 203.0.113.20' \
'EDGE_INTERCEPT_DNS=0
EDGE_ALLOW_ROUTER_HTTPS=0' 0 0
echo 'ISSUE283_WEBUI_SNAPSHOT_CONTRACT=PASS_5_OF_5'
