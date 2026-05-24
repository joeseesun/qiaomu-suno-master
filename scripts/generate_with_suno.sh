#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  generate_with_suno.sh --title TITLE --tags TAGS --lyrics-file FILE [options]
  generate_with_suno.sh --meta-file FILE [options]

Generates music via the Rust `suno` CLI. By default outputs JSON with clip IDs
(no download). Use download_clips.sh separately for reliable downloading.

Options:
  --meta-file FILE       Source a shell-style metadata file with TITLE, STYLE_DESCRIPTION, EXCLUDE_STYLES, and LYRICS_FILE
  --output-dir DIR       Directory for downloaded songs (default: ~/Documents/Suno/<title>)
                         Only used when --download is explicitly passed
  --model MODEL          Suno model (default: v5.5)
  --vocal male|female    Optional vocal gender
  --exclude TAGS         Optional comma-separated styles to avoid
  --token TOKEN          hCaptcha token to pass to suno
  --captcha             Use suno's built-in captcha solver (default)
  --no-captcha          Skip suno's built-in captcha solver
  --download             Also download after generation (NOT recommended; use download_clips.sh instead)

This wrapper calls the installed Rust `suno` CLI.
Output: JSON with clip IDs in data[].id (pipe to download_clips.sh)

If generation fails with auth/captcha errors, do not retry this wrapper in a
loop. Use references/browser-fallback.md from the skill.
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

safe_path_name() {
  local value="$1"
  value="${value//\//-}"
  value="${value//:/-}"
  value="$(printf '%s' "$value" | sed -E 's/[[:space:]]+/ /g; s/^ //; s/ $//')"
  if [[ -z "$value" ]]; then
    value="Untitled Suno Song"
  fi
  printf '%s' "$value"
}

title=""
tags=""
lyrics_file=""
meta_file=""
output_dir=""
model="v5.5"
vocal=""
exclude=""
token=""
download=0
captcha="${SUNO_USE_CAPTCHA_SOLVER:-1}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --meta-file)
      meta_file="${2:-}"; shift 2 ;;
    --title)
      title="${2:-}"; shift 2 ;;
    --tags)
      tags="${2:-}"; shift 2 ;;
    --lyrics-file)
      lyrics_file="${2:-}"; shift 2 ;;
    --output-dir)
      output_dir="${2:-}"; shift 2 ;;
    --model)
      model="${2:-}"; shift 2 ;;
    --vocal)
      vocal="${2:-}"; shift 2 ;;
    --exclude)
      exclude="${2:-}"; shift 2 ;;
    --token)
      token="${2:-}"; shift 2 ;;
    --captcha)
      captcha=1; shift ;;
    --no-captcha)
      captcha=0; shift ;;
    --download)
      download=1; shift ;;
    --no-download)
      download=0; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2 ;;
  esac
done

if [[ -n "$meta_file" ]]; then
  if [[ ! -f "$meta_file" ]]; then
    echo "Metadata file not found: $meta_file" >&2
    exit 66
  fi
  # shellcheck disable=SC1090
  source "$meta_file"
  title="${title:-${TITLE:-}}"
  tags="${tags:-${STYLE_DESCRIPTION:-${TAGS:-}}}"
  exclude="${exclude:-${EXCLUDE_STYLES:-${EXCLUDE:-}}}"
  token="${token:-${HCAPTCHA_TOKEN:-${SUNO_HCAPTCHA_TOKEN:-}}}"
  lyrics_file="${lyrics_file:-${LYRICS_FILE:-}}"
  vocal="${vocal:-${VOCAL:-}}"
  model="${MODEL:-$model}"
  captcha="${SUNO_USE_CAPTCHA_SOLVER:-$captcha}"
fi

if [[ -z "$title" || -z "$tags" || -z "$lyrics_file" ]]; then
  echo "Missing required --title, --tags, or --lyrics-file." >&2
  usage >&2
  exit 2
fi

if [[ -z "$output_dir" ]]; then
  output_dir="$HOME/Documents/Suno/$(safe_path_name "$title")"
fi

if ! command -v suno >/dev/null 2>&1; then
  bash "$script_dir/ensure_suno_cli.sh"
  export PATH="$HOME/.cargo/bin:$PATH"
fi

if ! command -v suno >/dev/null 2>&1; then
  echo "The 'suno' command was not found after bootstrap." >&2
  echo "Manual install options:" >&2
  echo "  brew tap paperfoot/tap && brew install suno" >&2
  echo "  cargo install suno --locked" >&2
  echo "  GitHub Releases: https://github.com/paperfoot/suno-cli/releases" >&2
  exit 127
fi

if [[ ! -f "$lyrics_file" ]]; then
  echo "Lyrics file not found: $lyrics_file" >&2
  exit 66
fi

# Prefer a real logged-in Chrome web session before touching CLI auth. The web
# session is the fallback source of truth when Suno rejects the CLI JWT.
if [[ -x "$script_dir/ensure_suno_chrome_session.sh" ]]; then
  bash "$script_dir/ensure_suno_chrome_session.sh" >/dev/null || true
fi

# Sync auth from Chrome before generating (avoids stale JWT / captcha failures
# when Suno accepts the CLI session).
echo "Refreshing Suno auth from Chrome..." >&2
if ! suno auth --refresh --quiet 2>/dev/null; then
  suno auth --login --quiet
fi

# Build command: always --json for machine-readable output
cmd=(suno generate --title "$title" --tags "$tags" --lyrics-file "$lyrics_file" --model "$model" --wait --json)

if [[ -n "$vocal" ]]; then
  cmd+=(--vocal "$vocal")
fi

if [[ -n "$exclude" ]]; then
  cmd+=(--exclude "$exclude")
fi

if [[ -n "$token" ]]; then
  cmd+=(--token "$token")
elif [[ "$captcha" != "1" ]]; then
  cmd+=(--no-captcha)
fi

if [[ "$download" -eq 1 ]]; then
  mkdir -p "$output_dir"
  cmd+=(--download "$output_dir")
fi

# Output goes to stdout (JSON); status messages go to stderr
echo "Generating: $title" >&2
echo "Output dir: $output_dir" >&2
stderr_file="$(mktemp -t suno-generate-stderr.XXXXXX)"
cleanup() {
  rm -f "$stderr_file"
}
trap cleanup EXIT

set +e
"${cmd[@]}" 2> >(tee "$stderr_file" >&2)
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  exit 0
fi

stderr_text="$(cat "$stderr_file" 2>/dev/null || true)"
if printf '%s' "$stderr_text" | grep -Eiq 'auth_expired|JWT expired|JWT expired or rejected|401|403|captcha|No Suno session found|session.*not found'; then
  cat >&2 <<EOF

Suno CLI generation failed with an auth/captcha/session error.
Do not retry the CLI in a loop. Use the skill's browser fallback:
  references/browser-fallback.md

Recommended next action:
  1. Open https://suno.com/create in the logged-in Chrome profile.
  2. Fill Lyrics, Styles, and Song Title from:
     title: $title
     lyrics: $lyrics_file
  3. Click Create, capture the two song links, then download via the web UI or:
     bash scripts/download_clips.sh --ids "ID1 ID2" --output-dir "$output_dir" --browser
EOF
fi

exit "$status"
