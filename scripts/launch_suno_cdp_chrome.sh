#!/usr/bin/env bash
set -euo pipefail

port="${SUNO_CDP_PORT:-9222}"
url="${SUNO_CDP_START_URL:-https://suno.com/create}"
dedicated_profile=0

usage() {
  cat <<'EOF'
Usage: launch_suno_cdp_chrome.sh [options]

Options:
  --port N              CDP port (default: SUNO_CDP_PORT or 9222).
  --url URL             First page to open (default: https://suno.com/create).
  --dedicated-profile   Use a separate temporary Chrome profile.
  -h, --help            Show this help.

Default mode reuses the normal Chrome profile, so it can reuse an existing Suno
login, but Chrome must not already be running. Dedicated profile mode avoids
touching the normal profile, but you will need to log into Suno in that profile.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      port="${2:-9222}"; shift 2 ;;
    --url)
      url="${2:-https://suno.com/create}"; shift 2 ;;
    --dedicated-profile)
      dedicated_profile=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2 ;;
  esac
done

chrome_app="Google Chrome"
args=(
  --remote-debugging-port="$port"
  --no-first-run
  --no-default-browser-check
  --disable-features=ChromePasswordManager,PasswordManagerOnboarding,AutofillAddressSavePrompt
  "$url"
)

if [[ "$dedicated_profile" -eq 1 ]]; then
  profile_dir="${SUNO_CDP_PROFILE_DIR:-$HOME/.cache/qiaomu-suno-master/chrome-cdp-profile}"
  mkdir -p "$profile_dir"
  args=(--user-data-dir="$profile_dir" "${args[@]}")
  open -na "$chrome_app" --args "${args[@]}"
  echo "Launched dedicated Chrome CDP profile on port $port: $profile_dir"
  exit 0
fi

if pgrep -x "Google Chrome" >/dev/null 2>&1; then
  cat >&2 <<EOF
Chrome is already running. macOS will ignore new --remote-debugging-port flags
for the existing app instance.

Quit Chrome fully, then run:
  bash "$0" --port "$port" --url "$url"

Or use an isolated profile:
  bash "$0" --dedicated-profile --port "$port" --url "$url"
EOF
  exit 1
fi

open -a "$chrome_app" --args "${args[@]}"
echo "Launched Chrome CDP on port $port with the normal Chrome profile."
