#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  download_clips.sh --ids "ID1 ID2 ..." --output-dir DIR [options]
  echo '{"data":[{"id":"..."}]}' | download_clips.sh --output-dir DIR

Download Suno clips by ID with retry logic. Designed to run AFTER generation
completes (CDN needs a few seconds to propagate).

Options:
  --ids "ID1 ID2 ..."   Space-separated clip IDs (or pipe JSON from generate)
  --output-dir DIR      Directory to save MP3 files (required)
  --retries N           Max retry attempts (default: 3)
  --delay N             Seconds between retries (default: 10)
  --initial-wait N      Seconds to wait before first attempt (default: 5)
  --video               Also download video files
  -h, --help            Show this help

Input:
  If --ids is not provided, reads JSON from stdin and extracts data[].id

Output:
  Prints paths of downloaded files. Exit 0 on success, 1 on failure.
EOF
}

ids=""
output_dir=""
retries=3
delay=10
initial_wait=5
video=0

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
    --video)
      video=1; shift ;;
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

if [[ -z "$output_dir" ]]; then
  echo "Error: --output-dir is required" >&2
  exit 2
fi

mkdir -p "$output_dir"

# Sync auth from Chrome (fast, ensures valid JWT)
echo "Refreshing Suno auth..." >&2
if ! suno auth --refresh --quiet 2>/dev/null; then
  suno auth --login --quiet 2>/dev/null || true
fi

# Wait for CDN propagation
if [[ "$initial_wait" -gt 0 ]]; then
  echo "Waiting ${initial_wait}s for CDN propagation..." >&2
  sleep "$initial_wait"
fi

# Download with retry
success=0
for attempt in $(seq 1 "$retries"); do
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

# List downloaded files
echo "" >&2
echo "Downloaded to: $output_dir" >&2
find "$output_dir" -name "*.mp3" -newer "$output_dir" -maxdepth 1 2>/dev/null | sort
