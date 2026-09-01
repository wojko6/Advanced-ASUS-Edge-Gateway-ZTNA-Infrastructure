# Contributing

Keep changes compatible with BusyBox `sh` unless a script explicitly declares another shell. New rules must be least-privilege, idempotent, scoped to project-owned chains, covered by a mock/static test, and documented in the firewall policy and threat model when they alter a trust boundary.

Before a pull request:

```sh
sh tests/test-static.sh
```

Never include secrets, real credentials, private packet captures, Tailscale node state, or router configuration exports.
