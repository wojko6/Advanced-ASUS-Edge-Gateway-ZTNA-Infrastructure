# WebUI security-policy drift validation

**Status:** PASS  
**Date:** 2026-09-30  
**Evidence class:** Live functional validation / sanitized  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton

## Purpose

Validate the new healthcheck guards for ASUS WebUI management-plane drift.

The deployment policy under test requires:

- WAN WebUI disabled;
- ASUS access restriction enabled;
- a non-empty access-restriction rule list;
- WebUI auto logout matching the local deployment policy.

For this router, the local policy is:

```text
EDGE_EXPECT_HTTP_AUTOLOGOUT=0
```

## Pre-change live state

Before installing the new healthcheck, the router reported:

```text
http_autologout=0
WAN_WEBUI=0
ACCESS_RESTRICTION=1
HTTPS_PORT=8443
restrict_rulelist=<1>192.168.50.32>3<1>192.168.50.33>3
```

The existing project healthcheck was clean:

```text
Summary: 0 failure(s), 0 warning(s)
```

## Staged validation

The PR healthcheck was staged under `/tmp` before persistent replacement.

Shell syntax validation:

```text
LOCAL_SYNTAX=PASS
```

The staged healthcheck reported all new management-plane checks as healthy:

```text
[OK]   router WebUI disabled from WAN
[OK]   router management access restriction enabled
[OK]   router management access restriction rule list present
[OK]   WebUI auto logout matches expected policy: 0
```

Full staged result:

```text
Summary: 0 failure(s), 0 warning(s)
```

## Persistent deployment

The existing config and live healthcheck were backed up before replacement.

The validated healthcheck was then installed persistently and the local config
was updated with:

```text
EDGE_EXPECT_HTTP_AUTOLOGOUT=0
```

File verification reported:

```text
PERSISTENT_HEALTHCHECK=PASS
```

The final live healthcheck again reported:

```text
[OK]   router WebUI disabled from WAN
[OK]   router management access restriction enabled
[OK]   router management access restriction rule list present
[OK]   WebUI auto logout matches expected policy: 0
```

Final project result:

```text
Summary: 0 failure(s), 0 warning(s)
```

## Result

**PASS.**

The project healthcheck now detects drift in the currently validated ASUS WebUI
security posture while preserving the existing clean health state.

The public example config keeps the auto-logout expectation deployment-specific;
this router explicitly pins the local policy to `0`.
