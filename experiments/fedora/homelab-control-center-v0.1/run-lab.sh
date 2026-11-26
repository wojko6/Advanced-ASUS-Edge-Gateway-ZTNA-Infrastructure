#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ "${1:-}" != "--serve" || $# -ne 1 ]]; then
  printf '%s\n' 'Usage: bash run-lab.sh --serve' 'Scope: user-level, local-only static demo; no sudo, no router, no production APIs.'
  exit 2
fi
if [[ "${EUID}" -eq 0 ]]; then
  echo 'Refusing root execution' >&2
  exit 1
fi
command -v python3 >/dev/null || { echo 'python3 not available' >&2; exit 1; }
printf '%s\n' 'OFFLINE_DEMO=YES' 'EXTERNAL_REQUESTS=NO' 'ASUS_CONTACTED=NO' 'PRODUCTION_CHANGES=NO' 'DEPLOYMENT_GATE=HOLD' 'Open: http://127.0.0.1:8787/' 'Press Ctrl+C to stop.'
exec python3 -m http.server 8787 --bind 127.0.0.1 --directory "$ROOT"
