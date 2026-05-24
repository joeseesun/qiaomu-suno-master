#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  download_clips.sh --ids "ID1 ID2 ..." --output-dir DIR [options]
  echo '{"data":[{"id":"..."}]}' | download_clips.sh --output-dir DIR

Download Suno clips by ID. Designed to run AFTER generation completes (CDN
needs a few seconds to propagate). By default it tries Chrome's browser
download pipeline first, then falls back to `suno download`.

Options:
  --ids "ID1 ID2 ..."   Space-separated clip IDs (or pipe JSON from generate)
  --output-dir DIR      Directory to save MP3 files (required)
  --retries N           Max retry attempts (default: 3)
  --delay N             Seconds between retries (default: 10)
  --initial-wait N      Seconds to wait before first attempt (default: 5)
  --browser             Try Chrome/CDP browser download first (default)
  --no-browser          Skip Chrome/CDP and use `suno download` only
  --browser-timeout N   Seconds to wait per browser-downloaded file (default: 120)
  --video               Also download video files
  --lyrics              Also fetch aligned lyrics after audio download
  --lyrics-format FMT   lrc, srt, md, all, both (default: lrc)
  -h, --help            Show this help

Input:
  If --ids is not provided, reads JSON from stdin and extracts data[].id

Output:
  Prints paths of downloaded files. Exit 0 on success, 1 on failure.
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ids=""
output_dir=""
retries=3
delay=10
initial_wait=5
video=0
browser=1
browser_timeout=120
lyrics=0
lyrics_format="lrc"
stdin_json=""
manifest_file=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ids)
      ids="${2:-}"; shift 2 ;;
    --output-dir)
      output_dir="${2:-}"; shift 2 ;;
    --retries)
      retries="${2:-3}"; shift 2 ;;
    --delay)
      delay="${2:-10}"; shift 2 ;;
    --initial-wait)
      initial_wait="${2:-5}"; shift 2 ;;
    --browser)
      browser=1; shift ;;
    --no-browser)
      browser=0; shift ;;
    --browser-timeout)
      browser_timeout="${2:-120}"; shift 2 ;;
    --video)
      video=1; shift ;;
    --lyrics)
      lyrics=1; shift ;;
    --lyrics-format)
      lyrics_format="${2:-lrc}"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2 ;;
  esac
done

# If no IDs provided, try to read from stdin (JSON from generate)
if [[ -z "$ids" ]]; then
  if [[ -t 0 ]]; then
    echo "Error: --ids required or pipe JSON from generate_with_suno.sh" >&2
    exit 2
  fi
  stdin_json="$(cat)"
  manifest_file="$(mktemp -t suno-generate-json.XXXXXX)"
  printf '%s' "$stdin_json" > "$manifest_file"
  ids="$(echo "$stdin_json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
clips = data.get('data', data) if isinstance(data, dict) else data
if isinstance(clips, list):
    print(' '.join(c['id'] for c in clips if 'id' in c))
" 2>/dev/null || true)"
  if [[ -z "$ids" ]]; then
    echo "Error: could not extract clip IDs from stdin JSON" >&2
    echo "Input was: ${stdin_json:0:200}" >&2
    exit 1
  fi
fi

cleanup() {
  if [[ -n "$manifest_file" ]]; then
    rm -f "$manifest_file"
  fi
}
trap cleanup EXIT

if [[ -z "$output_dir" ]]; then
  echo "Error: --output-dir is required" >&2
  exit 2
fi

mkdir -p "$output_dir"

# Wait for CDN propagation
if [[ "$initial_wait" -gt 0 ]]; then
  echo "Waiting ${initial_wait}s for CDN propagation..." >&2
  sleep "$initial_wait"
fi

success=0

if [[ "$browser" -eq 1 ]]; then
  browser_helper="$script_dir/browser_download_clips.py"
  if [[ -f "$browser_helper" ]]; then
    echo "Browser download attempt..." >&2
    browser_args=(python3 "$browser_helper" --ids "$ids" --output-dir "$output_dir" --timeout "$browser_timeout")
    if [[ -n "$manifest_file" ]]; then
      browser_args+=(--manifest-json "$manifest_file")
    fi
    if "${browser_args[@]}"; then
      success=1
    else
      echo "Browser download failed; falling back to suno download." >&2
    fi
  else
    echo "Browser helper not found; falling back to suno download." >&2
  fi
fi

# Download with retry through the upstream CLI when browser download is not available.
for attempt in $(seq 1 "$retries"); do
  if [[ "$success" -eq 1 ]]; then
    break
  fi
  if [[ "$attempt" -eq 1 ]]; then
    # Sync auth only when we actually need the upstream CLI fallback.
    echo "Refreshing Suno auth..." >&2
    if ! suno auth --refresh --quiet 2>/dev/null; then
      suno auth --login --quiet 2>/dev/null || true
    fi
  fi
  echo "Download attempt $attempt/$retries..." >&2
  # shellcheck disable=SC2086
  if suno download -o "$output_dir" $ids 2>&1; then
    success=1
    break
  fi
  if [[ "$attempt" -lt "$retries" ]]; then
    echo "Failed, retrying in ${delay}s..." >&2
    sleep "$delay"
  fi
done

if [[ "$success" -eq 0 ]]; then
  echo "Error: download failed after $retries attempts" >&2
  echo "IDs: $ids" >&2
  echo "You can retry manually: suno download -o \"$output_dir\" $ids" >&2
  exit 1
fi

# Optionally download video
if [[ "$video" -eq 1 ]]; then
  echo "Downloading video files..." >&2
  # shellcheck disable=SC2086
  suno download --video -o "$output_dir" $ids 2>&1 || echo "Video download failed (may not be available yet)" >&2
fi

# Optionally fetch timestamped lyrics through the local suno-api proxy.
# This is intentionally non-fatal: audio download success should remain success
# even if Suno has not generated aligned lyrics yet or the local API is offline.
if [[ "$lyrics" -eq 1 ]]; then
  lyrics_helper="$script_dir/fetch_aligned_lyrics.py"
  if [[ -f "$lyrics_helper" ]]; then
    echo "Fetching aligned lyrics (${lyrics_format})..." >&2
    # shellcheck disable=SC2086
    if ! python3 "$lyrics_helper" $ids --format "$lyrics_format" --output "$output_dir"; then
      echo "Aligned lyrics download failed; retry later with:" >&2
      echo "  python3 \"$lyrics_helper\" $ids --format \"$lyrics_format\" --output \"$output_dir\"" >&2
    fi
  else
    echo "Lyrics helper not found: $lyrics_helper" >&2
  fi
fi

# List downloaded files
echo "" >&2
echo "Downloaded to: $output_dir" >&2
find "$output_dir" -name "*.mp3" -newer "$output_dir" -maxdepth 1 2>/dev/null | sort
