#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ "${1:-}" != "--serve-readonly" || $# -ne 1 ]]; then
  printf '%s\n' 'Usage: bash tools/run-live-lab.sh --serve-readonly' 'Only a local manual V0.2 read-only VictoriaMetrics aggregate tile, no new services.'
  exit 2
fi
if (( EUID == 0 )); then echo "Refusing root" >&2; exit 1; fi
exec python3 -B "$ROOT/tools/v02_local_server.py" --serve-readonly
