# Local Caddy HTTPS frontend for Grafana

The validated Fedora reference deployment keeps Grafana bound to
`127.0.0.1:3000` and places Caddy in front of it on loopback-only HTTPS:

```text
Browser
  -> https://grafana.home.arpa/
  -> 127.0.0.1:443 Caddy
  -> 127.0.0.1:3000 Grafana
```

This is a local convenience/security layer, not LAN or WAN publication.

## Local name

Add the local-only name to `/etc/hosts`:

```text
127.0.0.1 grafana.home.arpa
```

## Caddy configuration

Install the repository `Caddyfile` as `/etc/caddy/Caddyfile`, validate it,
then enable the packaged service.

The configuration intentionally uses:

- `bind 127.0.0.1` so port 443 is loopback-only;
- `tls internal` so Caddy issues the local certificate from its own CA;
- `auto_https disable_redirects` so the deployment does not need an HTTP
  listener on port 80;
- `reverse_proxy 127.0.0.1:3000` so Grafana itself stays local-only.

Expected listeners:

```text
127.0.0.1:443   Caddy
127.0.0.1:3000  Grafana
```

Do not accept `0.0.0.0:443` or `[::]:443` as equivalent for this baseline.

## Trusting the local Caddy CA on Fedora

The packaged Caddy service runs as user `caddy`. During the live test it could
not automatically call sudo to install its internal root certificate. That
failure did not prevent Caddy from serving HTTPS; it only meant that the local
CA still needed to be trusted by the workstation.

Locate the generated public root certificate:

```bash
ROOT_CERT="$(sudo find /var/lib/caddy \
  -path '*/pki/authorities/local/root.crt' \
  -print -quit)"
test -n "$ROOT_CERT"
```

Install only the public root certificate into Fedora's system trust store:

```bash
sudo install -m 0644 \
  "$ROOT_CERT" \
  /etc/pki/ca-trust/source/anchors/caddy-local-root.crt
sudo update-ca-trust
```

The private CA key remains in Caddy's protected runtime storage and must never
be copied into this repository.

## Brave / Chromium NSS trust

On the tested Fedora/Brave profile, system trust alone did not clear the browser
warning. The same public CA was therefore added to the user's NSS database:

```bash
sudo dnf install -y nss-tools
mkdir -p ~/.pki/nssdb

if [ ! -f ~/.pki/nssdb/cert9.db ]; then
    certutil -N -d sql:$HOME/.pki/nssdb --empty-password
fi

certutil -D \
  -d sql:$HOME/.pki/nssdb \
  -n "Caddy Local Authority" 2>/dev/null || true

certutil -A \
  -d sql:$HOME/.pki/nssdb \
  -n "Caddy Local Authority" \
  -t "C,," \
  -i /etc/pki/ca-trust/source/anchors/caddy-local-root.crt
```

Restart the browser completely after changing NSS trust.

## Validation

The live deployment returned an HTTP/2 redirect from the HTTPS frontend to
Grafana's login path:

```text
HTTP/2 302
location: /login
via: 1.1 Caddy
```

The browser subsequently loaded `https://grafana.home.arpa/login` without the
certificate warning after NSS trust was installed.

This validation is intentionally local. It does not authorize exposure of Caddy
or Grafana to LAN, Tailscale or the public Internet.
