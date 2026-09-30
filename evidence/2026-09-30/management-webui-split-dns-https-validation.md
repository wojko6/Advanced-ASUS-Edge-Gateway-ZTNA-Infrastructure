# Management WebUI split-DNS and HTTPS certificate validation

**Status:** PASS  
**Date:** 2026-09-30  
**Evidence class:** Router-management HTTPS / local DNS / sanitized live validation  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton

## Purpose

Validate a clean HTTPS access path to the router management WebUI without
client-side `/etc/hosts` overrides and without accepting a hostname-mismatch
certificate warning.

The public artifact intentionally redacts the deployment-specific ASUS DDNS
label. The verified hostname is represented below as
`<router-ddns>.asuscomm.com`.

## Initial condition

The local convenience name `router.home.arpa` resolved to the router and the
WebUI returned HTML, but Chromium rejected the page's HTTPS resources with
`ERR_CERT_COMMON_NAME_INVALID`. The page therefore rendered without its normal
CSS/JavaScript dependencies.

Certificate inspection against `router.home.arpa:443` showed that the active
router certificate was issued for the ASUS DDNS hostname only:

```text
subject=CN=<router-ddns>.asuscomm.com
issuer=C=US, O=Let's Encrypt, CN=YE2
X509v3 Subject Alternative Name:
    DNS:<router-ddns>.asuscomm.com
```

`router.home.arpa` was not present in the certificate SAN set.

## Direct hostname/certificate validation

The ASUS DDNS hostname was then forced locally to the router LAN address for a
single `curl` test:

```sh
curl -Iv \
  --resolve <router-ddns>.asuscomm.com:443:192.168.50.1 \
  https://<router-ddns>.asuscomm.com/
```

Observed result:

```text
subjectAltName: "<router-ddns>.asuscomm.com" matches cert's "<router-ddns>.asuscomm.com"
SSL certificate verified via OpenSSL.
HTTP/1.0 200 OK
Server: httpd/3.0
```

The same hostname then loaded the ASUS WebUI correctly in the browser, including
its stylesheet and JavaScript resources.

## Adopted split-DNS configuration

A local Pi-hole DNS record was created so that the validated ASUS DDNS hostname
resolves to the router LAN address:

```text
<router-ddns>.asuscomm.com -> 192.168.50.1
```

The temporary workstation `/etc/hosts` entries used during diagnosis were
removed and the local resolver cache was flushed.

Final workstation validation:

```text
$ getent hosts <router-ddns>.asuscomm.com
192.168.50.1    <router-ddns>.asuscomm.com

$ curl -I https://<router-ddns>.asuscomm.com/
HTTP/1.0 200 OK
Server: httpd/3.0
x-frame-options: SAMEORIGIN
x-xss-protection: 1; mode=block
Content-Type: text/html
Connection: close

$ grep -nE '<router-ddns>|router\.home\.arpa' /etc/hosts || echo "HOSTS_CLEAN"
HOSTS_CLEAN
```

## Accepted management URL design

The accepted local-management pattern is:

```text
<router-ddns>.asuscomm.com
        |
        | local Pi-hole DNS
        v
   192.168.50.1
        |
        | HTTPS with hostname-matching public certificate
        v
     ASUS WebUI
```

`router.home.arpa` is not used as the primary HTTPS WebUI hostname because the
current certificate does not contain that name. A DNS alias alone cannot fix a
TLS hostname mismatch: the browser validates the hostname present in the URL
against the certificate SANs.

The deployment therefore keeps the hostname already covered by the publicly
trusted Let's Encrypt certificate and uses split DNS to route that hostname to
the private LAN address.

## Result

**PASS.**

The final tested state satisfies the intended local-management properties:

- the management hostname resolves to `192.168.50.1` through local DNS;
- the router serves the WebUI successfully over HTTPS;
- the presented certificate matches the hostname used by the client and is
  accepted by the Fedora trust store;
- no persistent `/etc/hosts` override remains on the tested Fedora
  administration workstation;
- the browser WebUI loads normally rather than failing its CSS/JavaScript
  resources on a certificate-name error.

## Claim boundary

This artifact records the observed Fedora-to-router management path on
2026-09-30. It does not by itself prove identical resolver configuration on
every LAN client, future certificate-renewal behavior, or WAN-side management
reachability. WAN exposure and LAN management allowlisting are covered by
separate hardening evidence.

The real ASUS DDNS label, client address and unrelated raw browser/debug output
are intentionally omitted from this public repository artifact.
