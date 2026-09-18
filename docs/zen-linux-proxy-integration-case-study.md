# Zen Linux Proxy Integration Case Study

## Scope

This case study documents a live validation of Zen's system-proxy integration on a Fedora Linux workstation using GNOME.

The objective was to determine how Zen integrates with the Linux desktop proxy configuration, how its local proxy and PAC services behave during start/stop cycles, whether the proxy is exposed to the LAN, and which DNS path is observed while Zen is active.

This document complements the separate Windows endpoint validation in:

`evidence/ENDPOINT-ZEN-VALIDATION-2026-09-12.md`

Zen remains an optional endpoint-side defense-in-depth layer. It does not replace router-side DNS, firewall, Unbound, Tailscale, or other network controls.

## Test Environment

- Endpoint OS: Fedora Linux
- Desktop environment: GNOME
- Zen executable: `/home/<user>/.local/bin/zen`
- Installation method: standalone/user-local installation outside RPM
- Zen autostart: enabled
- Zen runtime PID during validation: `1797`
- LAN address observed during validation: `WORKSTATION_LAN_IP`
- Router LAN address: `ROUTER_LAN_IP`
- Tailscale interface: `tailscale0`
- Fedora Tailscale address: `FEDORA_TS_IP`
- ASUS TUF-AX5400 Tailscale address: `ROUTER_TS_IP`
- Tailscale DNS address: `100.100.100.100`

The validation was observational and did not require changes to the router configuration.

Deployment-specific LAN/Tailscale addresses and peer names are sanitized in this case study. The well-known Tailscale DNS service address `100.100.100.100` is retained because it is not deployment-specific.

## 1. Zen Installation and Runtime Identification

The shell resolved the Zen executable to:

```text
~/.local/bin/zen
/home/<user>/.local/bin/zen
```

File inspection identified it as a native 64-bit Linux executable:

```text
ELF 64-bit LSB executable, x86-64
```

RPM ownership validation returned:

```text
file /home/<user>/.local/bin/zen is not owned by any package
```

This confirms that the tested Zen installation was not managed by Fedora RPM.

The active process was observed as:

```text
/home/<user>/.local/bin/zen --start --hidden
```

The command-line flags matched the enabled Zen autostart configuration.

## 2. CLI Surface

`zen --help` exposed the following command-line options:

```text
-hidden
    Start the application in hidden mode
-start
    Start the service when DOM is ready
-uninstall-ca
    Uninstall the CA and exit
```

No proxy-port or GNOME integration configuration was exposed through the observed CLI help output.

## 3. Local Listener Behaviour

With Zen active, the process opened multiple dynamically allocated TCP listeners bound to loopback.

One observed state was:

```text
127.0.0.1:46663
127.0.0.1:33255
127.0.0.1:33967
```

After a Zen Stop/Start cycle, a different listener set was observed:

```text
127.0.0.1:37385
127.0.0.1:33249
127.0.0.1:35187
```

A later cycle generated another PAC port:

```text
127.0.0.1:38409
```

Zen's Advanced settings had both Proxy port and PAC port configured as `0`, which the application describes as random port selection.

### Result

Dynamic port allocation was confirmed empirically across service restarts. The Zen process itself remained alive with the same PID while the proxy/network service was stopped and started again.

## 4. GNOME System Proxy Integration

With Zen active:

```bash
gsettings get org.gnome.system.proxy mode
```

returned:

```text
'auto'
```

The GNOME automatic proxy configuration URL was:

```text
http://127.0.0.1:35187/proxy.pac
```

The PAC port matched one of the active Zen loopback listeners.

This establishes the integration path:

```text
GNOME
  |
  v
Automatic proxy configuration
  |
  v
http://127.0.0.1:<dynamic-port>/proxy.pac
  |
  v
Zen local PAC service
```

## 5. Stop Behaviour and Configuration Cleanup

Zen was stopped using the application's Stop control.

After stopping Zen, both listener and active-connection checks returned no Zen TCP sockets:

```bash
ss -lntp | grep '"zen"'
ss -ntp | grep '"zen"'
```

GNOME proxy mode changed from `'auto'` to `'none'`, while:

```bash
gsettings get org.gnome.system.proxy autoconfig-url
```

returned:

```text
''
```

### Result

Zen cleanly removed its active GNOME proxy configuration during the tested Stop operation. No stale PAC URL remained configured.

This is operationally important because a stale localhost PAC reference could otherwise disrupt network connectivity after the local proxy service stops.

## 6. Start → Stop → Start Lifecycle

The complete observed lifecycle was:

```text
ZEN START
   |
   +--> dynamic localhost listeners created
   +--> GNOME proxy mode = auto
   +--> GNOME PAC URL = http://127.0.0.1:<dynamic>/proxy.pac

ZEN STOP
   |
   +--> Zen TCP listeners disappear
   +--> Zen active TCP connections disappear
   +--> GNOME proxy mode = none
   +--> PAC URL cleared

ZEN START
   |
   +--> new dynamic ports allocated
   +--> GNOME proxy mode = auto
   +--> new PAC URL generated
```

A later start produced:

```text
http://127.0.0.1:38409/proxy.pac
```

confirming that the PAC port was not fixed across service restarts.

## 7. PAC Policy Inspection

The generated PAC file was retrieved directly from the GNOME-configured URL.

The primary proxy rule used:

```text
PROXY 127.0.0.1:34569; DIRECT
```

A special local rule was also present:

```text
local.irbis.sh -> PROXY 127.0.0.1:34569
```

Zen additionally generated an exclusion list whose matching destinations returned `DIRECT`.

Observed exclusions included examples from authentication services, password managers, banking and payment services, government services, messaging platforms, cloud/infrastructure services, and development platforms.

Examples observed in the generated PAC included:

```text
auth.openai.com
accounts.google.com
appleid.apple.com
1password.com
bitwarden.com
paypal.com
stripe.com
revolut.com
signal.org
whatsapp.com
github.com
```

### Interpretation

Zen does not implement a simple unconditional "proxy everything" policy. The generated PAC applies selective routing:

```text
excluded destination --> DIRECT

other destination --> PROXY 127.0.0.1:34569
                       |
                       +--> DIRECT fallback
```

The exclusions are a maintained policy list and should not be interpreted as a guarantee that every sensitive destination is excluded.

## 8. Proxy Endpoint Validation

The PAC-selected proxy port was:

```text
127.0.0.1:34569
```

Socket inspection confirmed:

```text
LISTEN ... 127.0.0.1:34569 ... users:(("zen",pid=1797,...))
```

This directly linked the PAC configuration to the running Zen process:

```text
GNOME
  |
  v
proxy.pac
  |
  v
PROXY 127.0.0.1:34569
  |
  v
Zen PID 1797
```

## 9. LAN Exposure Test

Although the Zen proxy was reachable through loopback, an explicit connection attempt was made through the Fedora workstation's LAN address:

```bash
nc -vz -w 2 WORKSTATION_LAN_IP 34569
```

Result:

```text
Ncat: Connection refused.
```

Together with the socket binding to `127.0.0.1:34569`, this confirms that the tested Zen proxy endpoint was not listening on the workstation's LAN address.

### Security Result

PASS for the tested configuration.

The local proxy was bound to loopback and was not exposed as a TCP proxy service to other LAN hosts through `WORKSTATION_LAN_IP`.

## 10. Observed Application-to-Proxy Traffic

While a browser generated traffic, active Zen connections included localhost sessions involving the confirmed proxy endpoint:

```text
127.0.0.1:34569 <-> local client connections
```

At the same time, Zen established external HTTPS connections from the Fedora workstation, including examples such as:

```text
WORKSTATION_LAN_IP:<ephemeral> -> 172.64.155.209:443
WORKSTATION_LAN_IP:<ephemeral> -> 104.18.42.153:443
```

This provides runtime evidence consistent with:

```text
Application
    |
    v
GNOME PAC decision
    |
    v
127.0.0.1:34569
    |
    v
Zen
    |
    v
Remote HTTPS endpoint
```

The socket observations establish proxy participation but do not by themselves identify the application-layer contents of those TLS sessions.

## 11. CLI Applications and GNOME PAC

A direct CLI test using:

```bash
curl -v https://example.com
```

showed a direct connection attempt:

```text
Trying 104.20.23.154:443...
```

No Zen proxy connection was indicated by that test.

### Result

The tested command-line `curl` invocation did not automatically consume the GNOME PAC configuration.

Therefore, GNOME system proxy configuration must not be interpreted as meaning every Linux process is automatically forced through Zen. Application proxy behaviour depends on whether the application consumes the desktop/system proxy configuration.

This is an important limitation when describing Zen as an endpoint-wide filtering layer on Linux.

## 12. Fedora DNS Baseline

`resolvectl status` showed the Wi-Fi interface configured with:

```text
DNS Server: ROUTER_LAN_IP
```

while `tailscale0` exposed:

```text
100.100.100.100
fd7a:115c:a1e0::53
DNS Domain: ~.
```

A direct query:

```bash
resolvectl query example.com
```

returned results through:

```text
-- link: tailscale0
```

This demonstrated that the tested Fedora system's ordinary DNS resolution path was using Tailscale for this query rather than the Wi-Fi interface's router DNS path.

## 13. Live DNS Capture

A live capture was performed with:

```bash
sudo tcpdump -ni any 'port 53'
```

A previously unused test destination, `kernel.org`, was then opened.

The capture showed DNS requests leaving through `tailscale0`, including queries from the Fedora Tailscale address `FEDORA_TS_IP` to:

```text
100.100.100.100:53
ROUTER_TS_IP:53
```

Observed queries included A and AAAA requests for `kernel.org` and `www.kernel.org`.

The returned IPv4 records included:

```text
kernel.org -> 172.105.4.254
```

and:

```text
www.kernel.org
 -> dualstack.m.sni.global.fastly.net
 -> 199.232.17.55
```

## 14. Tailscale Peer Identification

`tailscale status` identified:

```text
FEDORA_TS_IP  fedora
ANDROID_TS_IP    android-client
ROUTER_TS_IP    router
```

The `ROUTER_TS_IP` DNS destination observed in the packet capture therefore corresponded to the ASUS TUF-AX5400 Tailscale peer.

The router was also reported as offering an exit node.

Tailscale displayed:

```text
Some peers are advertising routes but --accept-routes is false
```

No routing configuration was changed as part of this Zen validation.

## 15. DNS and Proxy Separation

The combined observations demonstrate an important architectural distinction.

For the tested browser path:

```text
HTTP/HTTPS application traffic
        |
        v
GNOME PAC
        |
        v
Zen localhost proxy
        |
        v
remote endpoint
```

while observed DNS resolution for the test domain followed:

```text
DNS request
    |
    v
systemd-resolved / system DNS path
    |
    v
tailscale0
    |
    +--> 100.100.100.100
    |
    +--> ROUTER_TS_IP (ASUS TUF-AX5400 peer)
```

No DNS request to `ROUTER_LAN_IP:53` was observed during the captured `kernel.org` test.

This is a bounded observation for the tested configuration and should not be generalized to every application or every Zen operating mode.

## 16. Security Observations

### Positive observations

- Zen proxy listeners were bound to `127.0.0.1`.
- The tested proxy port was not reachable through the workstation LAN address.
- Zen dynamically generated PAC configuration rather than exposing a fixed LAN proxy.
- GNOME proxy state was restored to `none` after Zen Stop.
- The PAC URL was cleared after Zen Stop.
- Sensitive-host exclusions were present in the generated PAC.
- DNS traffic remained observable on the configured system/Tailscale DNS path during the tested browser request.

### Residual considerations

- Zen is a high-trust endpoint component capable of HTTPS interception.
- PAC exclusions are list-based and cannot guarantee coverage of every sensitive destination.
- Applications that ignore GNOME system proxy settings may bypass Zen.
- Dynamic local ports make static port-based monitoring less useful.
- DNS behaviour may differ depending on application-specific DNS implementations such as DoH.
- This validation does not constitute a source-code security audit of Zen.
- This validation does not establish long-term telemetry behaviour or update-channel integrity.

## 17. Validation Summary

| Area | Result | Evidence |
| --- | --- | --- |
| Fedora native executable | CONFIRMED | ELF x86-64 |
| RPM ownership | NONE | User-local standalone installation |
| Autostart | CONFIRMED | `--start --hidden` |
| Dynamic proxy/PAC ports | CONFIRMED | Different ports after restart |
| Loopback binding | PASS | `127.0.0.1` listeners |
| GNOME proxy integration | CONFIRMED | `mode='auto'` |
| PAC integration | CONFIRMED | localhost `proxy.pac` |
| PAC → Zen proxy mapping | CONFIRMED | `127.0.0.1:34569`, PID 1797 |
| Stop cleanup | PASS | mode `none`, empty PAC URL |
| Restart behaviour | PASS | new dynamic PAC port |
| LAN proxy exposure | NOT OBSERVED | LAN connection refused |
| Selective PAC exclusions | CONFIRMED | `DIRECT` exclusion list |
| Browser proxy participation | CONFIRMED | localhost + Zen external sockets |
| CLI curl automatic proxying | NOT OBSERVED | direct HTTPS connection |
| Fedora DNS via Tailscale | CONFIRMED | `resolvectl` + `tcpdump` |
| ASUS Tailscale DNS path | OBSERVED | `ROUTER_TS_IP` identified as router |
| Router configuration changes | NONE | observational endpoint validation |

## 18. Conclusion

The Fedora validation demonstrated that Zen integrates with GNOME by dynamically deploying a localhost PAC service and switching the GNOME proxy mode to automatic configuration.

The PAC file directs eligible traffic to a dynamically allocated Zen proxy bound to loopback while explicitly bypassing selected sensitive destinations.

The tested Start/Stop lifecycle behaved cleanly: stopping Zen removed its listeners, disabled the GNOME proxy mode, and cleared the PAC URL. Restarting Zen generated new dynamic service ports without requiring the main Zen process to be recreated.

The tested proxy endpoint was not exposed through the Fedora workstation's LAN address.

The validation also demonstrated an important Linux limitation: GNOME proxy configuration does not guarantee interception of every process. The tested CLI `curl` invocation connected directly rather than automatically using the GNOME PAC configuration.

During the live browser DNS test, DNS traffic remained on the Fedora system/Tailscale DNS path. Queries were observed through `tailscale0`, including communication with Tailscale DNS and the ASUS TUF-AX5400 Tailscale peer.

The resulting architecture is therefore best described as:

```text
                     Fedora endpoint
                           |
              +------------+------------+
              |                         |
              | HTTP/HTTPS              | DNS
              v                         v
          GNOME PAC               systemd-resolved
              |                         |
              v                         v
       Zen localhost proxy          tailscale0
              |                         |
              v                   +-----+------+
       remote HTTPS               |            |
                                  v            v
                           Tailscale DNS    ASUS router
```

Zen remains an optional endpoint-side defense-in-depth component and does not replace the router-side security architecture.

## Related Evidence

- `evidence/ENDPOINT-ZEN-VALIDATION-2026-09-12.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/endpoint-filtering-validation.md`
- `docs/webrtc-exit-node-validation.md`
