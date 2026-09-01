# Security policy

Do not open a public issue containing router exports, credentials, Tailscale state, private IP inventories, packet captures with sensitive traffic, or exploitable details for an unpatched deployment.

For a suspected credential compromise, revoke the affected Tailscale device/key, remove it from Grants/groups and `EDGE_ADMIN_TS_SOURCES`, rotate router credentials, inspect configuration audit logs, and reapply the firewall from a trusted LAN session.

This is a homelab/portfolio project without a guaranteed security-response SLA. Apply changes only to devices you control, preserve a physical recovery path, and validate against your firmware and Entware target.
