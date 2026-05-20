#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cdp="$script_dir/cdp.mjs"

if [[ ! -x "$cdp" ]]; then
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

if ! pages="$("$cdp" list 2>&1)"; then
  cat >&2 <<EOF
Could not connect to Chrome via CDP.

$pages

Try launching Chrome with remote debugging:
  open -a "Google Chrome" --args --remote-debugging-port=9222

If Chrome is already running, quit it fully first, then relaunch with the command above.
EOF
  exit 1
fi

echo "$pages"

if echo "$pages" | awk '{print $NF}' | grep -Eiq '^https://([^/]+\.)?suno\.com(/|$)'; then
  echo "Found an existing Suno tab in the Chrome CDP session."
  exit 0
fi

echo "No Suno tab found. Opening https://suno.com/create in the CDP-enabled Chrome session..."
"$cdp" open https://suno.com/create
echo "If Suno asks for login, complete it once in Chrome, then rerun generation."
