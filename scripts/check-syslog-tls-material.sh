#!/bin/sh
# Read-only TLS material preflight for optional syslog-ng mTLS.

set -eu

KEY="${EDGE_SYSLOG_TLS_KEY:-/opt/etc/syslog-ng/tls/router-client.key}"
CERT="${EDGE_SYSLOG_TLS_CERT:-/opt/etc/syslog-ng/tls/router-client.crt}"
CA="${EDGE_SYSLOG_TLS_CA:-/opt/etc/syslog-ng/ca.d/asus-edge-ca.crt}"
MIN_SECONDS="${EDGE_SYSLOG_CERT_MIN_SECONDS:-604800}"
PEER_CERT="${EDGE_SYSLOG_PEER_CERT:-}"
PEER_NAME="${EDGE_SYSLOG_PEER_NAME:-}"

case "$MIN_SECONDS" in ''|*[!0-9]*) echo "ERROR: EDGE_SYSLOG_CERT_MIN_SECONDS must be a non-negative integer" >&2; exit 2 ;; esac

for path in "$KEY" "$CERT" "$CA"; do
    [ -f "$path" ] || { echo "ERROR: missing TLS file: $path" >&2; exit 1; }
    [ ! -L "$path" ] || { echo "ERROR: refusing symlink TLS file: $path" >&2; exit 1; }
done

key_mode="$(stat -c %a "$KEY" 2>/dev/null)" || {
    echo "ERROR: cannot read private-key mode" >&2
    exit 1
}
case "$key_mode" in 400|600) ;; *) echo "ERROR: private key mode must be 0400 or 0600, got $key_mode" >&2; exit 1 ;; esac

key_uid="$(stat -c %u "$KEY" 2>/dev/null)" || {
    echo "ERROR: cannot read private-key owner" >&2
    exit 1
}
[ "$key_uid" = "0" ] || {
    echo "ERROR: private key must be owned by root (uid 0), got uid $key_uid" >&2
    exit 1
}

openssl x509 -in "$CERT" -noout -checkend "$MIN_SECONDS" >/dev/null || {
    echo "ERROR: client certificate expires too soon or is invalid" >&2
    exit 1
}
openssl verify -CAfile "$CA" "$CERT" >/dev/null || {
    echo "ERROR: client certificate does not validate against configured CA" >&2
    exit 1
}

if [ -n "$PEER_CERT" ] || [ -n "$PEER_NAME" ]; then
    [ -n "$PEER_CERT" ] && [ -n "$PEER_NAME" ] || {
        echo "ERROR: peer certificate and peer name must be provided together" >&2
        exit 2
    }
    [ -f "$PEER_CERT" ] && [ ! -L "$PEER_CERT" ] || {
        echo "ERROR: invalid peer certificate path" >&2
        exit 1
    }
    openssl verify -CAfile "$CA" "$PEER_CERT" >/dev/null || {
        echo "ERROR: peer certificate does not validate against configured CA" >&2
        exit 1
    }
    openssl x509 -in "$PEER_CERT" -noout -checkhost "$PEER_NAME" >/dev/null || {
        echo "ERROR: peer certificate SAN/name mismatch: $PEER_NAME" >&2
        exit 1
    }
fi

echo "PASS: syslog-ng TLS material preflight"
