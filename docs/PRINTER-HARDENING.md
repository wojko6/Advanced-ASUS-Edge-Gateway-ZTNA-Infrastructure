# Network Printer Hardening

## Objective

Reduce the router attack surface without breaking legitimate network printing.

The deployed printer is a standalone LAN device. It does not require the ASUS USB print-server services (`lpd`/`u2ec`) to print from LAN clients.

## Finding

During the router service audit, TCP/515 was listening on the router even though no USB printer was attached. Runtime inspection identified:

- `lpd` listening on the router LAN address on TCP/515;
- `u2ec` running;
- `usb_printer=1` in NVRAM;
- no `/dev/usb/lp*` printer device.

This represented unnecessary service exposure for the deployed topology.

## Controlled remediation

The change was performed in two stages.

1. Stop `lpd` and `u2ec` using native Asuswrt service actions and verify TCP/515 closes without affecting the edge healthcheck.
2. Persist the policy with `usb_printer=0`, commit NVRAM, stop the services, reboot, and validate again.

The previous `usb_printer` value was backed up before the persistent change.

## Reboot validation

After reboot the observed state was:

```text
usb_printer=0
No lpd/u2ec processes
Port 515 CLOSED
[OK]   source-scoped printer policy
Summary: 0 failure(s), 0 warning(s)
```

This confirms that the unnecessary ASUS USB print server remains disabled across reboot while the project's source-scoped printer firewall policy remains healthy.

## Functional validation

The network printer remained reachable directly on the LAN. Its relevant observed services included IPP on TCP/631 and RAW/JetDirect on TCP/9100; TCP/515 on the printer was closed.

A direct RAW test to the printer on TCP/9100 produced a physical print. Linux printing was then configured to use a direct socket connection to the printer on TCP/9100 and successfully produced a CUPS test page.

Windows 11 was also validated using a Standard TCP/IP port with RAW protocol on TCP/9100. A legacy USB queue was removed, printer sharing from Windows was disabled because the printer is independently network reachable, and a Windows test page printed successfully.

## Security result

The final topology does not depend on the router acting as a USB print server. Network clients communicate directly with the printer under the existing source-scoped firewall policy. This removes an unnecessary router listener and two unnecessary print-server processes without loss of required printing functionality.

## Rollback

If USB printer sharing through the ASUS router is intentionally required in the future, restore the backed-up `usb_printer` value and use the native Asuswrt service controls for `lpd` and `u2ec`, followed by a reboot and a new exposure/functional validation.

Do not enable the USB print server merely to support a standalone network printer; these are separate functions.
