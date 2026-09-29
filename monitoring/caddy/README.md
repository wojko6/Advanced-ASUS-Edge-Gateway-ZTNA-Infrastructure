# Local Caddy HTTPS frontends for Grafana and Pi-hole

The validated Fedora reference deployment keeps Grafana bound to
`127.0.0.1:3000` and places Caddy in front of it on loopback-only HTTPS. The
same Caddy instance also provides a local HTTPS operator name for the Pi-hole
WebUI while leaving Pi-hole on its existing LAN HTTP listener.

```text
Browser
  -> https://grafana.home.arpa/
  -> 127.0.0.1:443 Caddy
  -> 127.0.0.1:3000 Grafana

Browser
  -> https://pihole.home.arpa/
  -> 127.0.0.1:443 Caddy
  -> http://192.168.50.253:8080 Pi-hole
```

These are local convenience/security frontends on the Fedora operator host.
They do not publish Caddy itself to LAN, Tailscale or WAN.

## Local names

Add the local-only names to `/etc/hosts`:

```text
127.0.0.1 grafana.home.arpa
127.0.0.1 pihole.home.arpa
```

## Caddy configuration

Install the repository `Caddyfile` as `/etc/caddy/Caddyfile`, validate it,
then reload or enable the packaged service.

The configuration intentionally uses:

- `bind 127.0.0.1` so port 443 is loopback-only;
- `tls internal` so Caddy issues local certificates from its own CA;
- `auto_https disable_redirects` so the deployment does not need an HTTP
  listener on port 80;
- `reverse_proxy 127.0.0.1:3000` for Grafana;
- `reverse_proxy 192.168.50.253:8080` for the existing Pi-hole WebUI;
- an explicit root-path redirect from `https://pihole.home.arpa/` to
  `/admin/login`, because the Pi-hole backend returns HTTP 403 for `/`
  instead of redirecting itself.

Expected local frontend listener:

```text
127.0.0.1:443   Caddy
```

Grafana remains loopback-only on `127.0.0.1:3000`. Pi-hole remains on its
existing router-side/LAN listener; Caddy does not change that backend exposure.

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

The Grafana frontend returned an HTTP/2 redirect to Grafana's login path:

```text
HTTP/2 302
location: /login
via: 1.1 Caddy
```

The Pi-hole backend was first validated directly with HTTP 200 at
`/admin/login`. A Host-header test using `pihole.home.arpa` also returned
HTTP 200. The Caddy configuration then validated successfully, was reloaded,
and the local HTTPS operator URL worked at:

```text
https://pihole.home.arpa/
```

with Caddy redirecting the root path to `/admin/login`.

This validation is intentionally local. It does not authorize exposure of Caddy
or Grafana to LAN, Tailscale or the public Internet, and it does not broaden the
existing Pi-hole backend listener.
