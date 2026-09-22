#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
SCRIPT="$ROOT_DIR/scripts/check-syslog-tls-material.sh"
TMPROOT="$(mktemp -d)"
trap 'rm -rf "$TMPROOT"' EXIT HUP INT TERM

openssl req -x509 -newkey rsa:2048 -nodes -days 2     -subj '/CN=fixture-ca'     -keyout "$TMPROOT/ca.key" -out "$TMPROOT/ca.crt" >/dev/null 2>&1

openssl req -newkey rsa:2048 -nodes     -subj '/CN=router-client'     -keyout "$TMPROOT/client.key" -out "$TMPROOT/client.csr" >/dev/null 2>&1
openssl x509 -req -days 1 -in "$TMPROOT/client.csr"     -CA "$TMPROOT/ca.crt" -CAkey "$TMPROOT/ca.key" -CAcreateserial     -out "$TMPROOT/client.crt" >/dev/null 2>&1

cat >"$TMPROOT/peer.ext" <<'EOF'
subjectAltName=DNS:collector.example.invalid
EOF
openssl req -newkey rsa:2048 -nodes     -subj '/CN=collector.example.invalid'     -keyout "$TMPROOT/peer.key" -out "$TMPROOT/peer.csr" >/dev/null 2>&1
openssl x509 -req -days 1 -in "$TMPROOT/peer.csr"     -CA "$TMPROOT/ca.crt" -CAkey "$TMPROOT/ca.key" -CAcreateserial     -extfile "$TMPROOT/peer.ext" -out "$TMPROOT/peer.crt" >/dev/null 2>&1

chmod 0600 "$TMPROOT/client.key"

EDGE_SYSLOG_TLS_KEY="$TMPROOT/client.key" EDGE_SYSLOG_TLS_CERT="$TMPROOT/client.crt" EDGE_SYSLOG_TLS_CA="$TMPROOT/ca.crt" EDGE_SYSLOG_CERT_MIN_SECONDS=60 EDGE_SYSLOG_PEER_CERT="$TMPROOT/peer.crt" EDGE_SYSLOG_PEER_NAME="collector.example.invalid" sh "$SCRIPT" >/dev/null

echo "PASS: valid key ownership/mode, certificate chain, expiry and peer SAN"

chmod 0644 "$TMPROOT/client.key"
if EDGE_SYSLOG_TLS_KEY="$TMPROOT/client.key"    EDGE_SYSLOG_TLS_CERT="$TMPROOT/client.crt"    EDGE_SYSLOG_TLS_CA="$TMPROOT/ca.crt"    EDGE_SYSLOG_CERT_MIN_SECONDS=60    sh "$SCRIPT" >/dev/null 2>&1
then
    echo "FAIL: insecure private-key mode accepted" >&2
    exit 1
fi
chmod 0600 "$TMPROOT/client.key"
echo "PASS: insecure private-key mode rejected"

if EDGE_SYSLOG_TLS_KEY="$TMPROOT/client.key"    EDGE_SYSLOG_TLS_CERT="$TMPROOT/client.crt"    EDGE_SYSLOG_TLS_CA="$TMPROOT/ca.crt"    EDGE_SYSLOG_CERT_MIN_SECONDS=60    EDGE_SYSLOG_PEER_CERT="$TMPROOT/peer.crt"    EDGE_SYSLOG_PEER_NAME="wrong.example.invalid"    sh "$SCRIPT" >/dev/null 2>&1
then
    echo "FAIL: peer SAN mismatch accepted" >&2
    exit 1
fi
echo "PASS: peer SAN mismatch rejected"
