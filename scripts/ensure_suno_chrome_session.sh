#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cdp="$script_dir/cdp.mjs"
timeout_seconds="${SUNO_CDP_TIMEOUT:-12}"
launch=0
open_suno=1

usage() {
  cat <<'EOF'
Usage: ensure_suno_chrome_session.sh [options]

Options:
  --launch        Launch Chrome with CDP flags first when no endpoint is found.
  --no-open      Only inspect the CDP session; do not open suno.com/create.
  --timeout N    Seconds to wait for each CDP operation (default: SUNO_CDP_TIMEOUT or 12).
  -h, --help     Show this help.

This helper must never hang generation. If Chrome shows a native "Allow
debugging" confirmation or CDP is unavailable, it returns non-zero quickly so the
caller can use the Suno web UI fallback.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --launch)
      launch=1; shift ;;
    --no-open)
      open_suno=0; shift ;;
    --timeout)
      timeout_seconds="${2:-12}"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2 ;;
  esac
done

run_with_timeout() {
  local seconds="$1"
  shift
  python3 - "$seconds" "$@" <<'PY'
import subprocess
import sys

timeout = float(sys.argv[1])
cmd = sys.argv[2:]
try:
    proc = subprocess.run(cmd, timeout=timeout)
except subprocess.TimeoutExpired:
    print(f"Timed out after {timeout:g}s: {' '.join(cmd)}", file=sys.stderr)
    raise SystemExit(124)
raise SystemExit(proc.returncode)
PY
}

if [[ ! -f "$cdp" ]]; then
  echo "Missing CDP helper: $cdp" >&2
  exit 66
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required for Chrome CDP helper." >&2
  exit 127
fi

node_major="$(node -p 'Number(process.versions.node.split(".")[0])')"
if [[ "$node_major" -lt 22 ]]; then
  echo "Node.js 22+ is required for the CDP helper. Current: $(node --version)" >&2
  exit 127
fi

if ! pages="$(run_with_timeout "$timeout_seconds" node "$cdp" list 2>&1)"; then
  if [[ "$launch" -eq 1 && -x "$script_dir/launch_suno_cdp_chrome.sh" ]]; then
    echo "No responsive Chrome CDP endpoint found. Launching Chrome with CDP flags..." >&2
    bash "$script_dir/launch_suno_cdp_chrome.sh" --url https://suno.com/create >&2 || true
    sleep 2
    pages="$(run_with_timeout "$timeout_seconds" node "$cdp" list 2>&1)" || true
  fi
fi

if [[ -z "${pages:-}" || "$pages" == *"No DevToolsActivePort found"* || "$pages" == *"Timeout"* || "$pages" == *"Timed out"* ]]; then
  cat >&2 <<EOF
Could not connect to Chrome via CDP.

${pages:-CDP helper timed out after ${timeout_seconds}s.}

Try launching Chrome with remote debugging:
  bash "$script_dir/launch_suno_cdp_chrome.sh"

If Chrome is already running, quit it fully first, then relaunch with the command above.
EOF
  exit 1
fi

echo "$pages"

if echo "$pages" | awk '{print $NF}' | grep -Eiq '^https://([^/]+\.)?suno\.com(/|$)'; then
  echo "Found an existing Suno tab in the Chrome CDP session."
  exit 0
fi

if [[ "$open_suno" -eq 0 ]]; then
  echo "No Suno tab found in the Chrome CDP session."
  exit 1
fi

echo "No Suno tab found. Opening https://suno.com/create in the CDP-enabled Chrome session..."
run_with_timeout "$timeout_seconds" node "$cdp" open https://suno.com/create
echo "If Suno asks for login, complete it once in Chrome, then rerun generation."
