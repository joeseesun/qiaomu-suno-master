#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  generate_download_lrc.sh --meta-file FILE --output-dir DIR [options]

Runs the stable end-to-end Suno path:
  generate -> save JSON -> extract clip IDs -> download MP3 -> fetch LRC -> validate LRC

Options:
  --meta-file FILE       Shell-style metadata file for generate_with_suno.sh
  --output-dir DIR       Directory for generated JSON, MP3, and LRC files
  --json-file FILE       Where to save generation JSON (default: OUTPUT_DIR/generate.result.json)
  --lyrics-format FMT    lrc, srt, md, all, both (default: lrc)
  --browser              Allow browser download first (default)
  --no-browser           Skip browser download and use suno download
  --initial-wait N       Seconds before download starts (default: 5)
  --retries N            Download retry attempts (default: 3)
  --delay N              Seconds between download retries (default: 10)
  --require-lrc          Require valid timestamped LRC (default)
  --no-require-lrc       Do not fail if LRC validation fails
  -h, --help             Show this help
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

meta_file=""
output_dir=""
json_file=""
lyrics_format="lrc"
browser=1
initial_wait=5
retries=3
delay=10
require_lrc=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --meta-file)
      meta_file="${2:-}"; shift 2 ;;
    --output-dir)
      output_dir="${2:-}"; shift 2 ;;
    --json-file)
      json_file="${2:-}"; shift 2 ;;
    --lyrics-format)
      lyrics_format="${2:-lrc}"; shift 2 ;;
    --browser)
      browser=1; shift ;;
    --no-browser)
      browser=0; shift ;;
    --initial-wait)
      initial_wait="${2:-5}"; shift 2 ;;
    --retries)
      retries="${2:-3}"; shift 2 ;;
    --delay)
      delay="${2:-10}"; shift 2 ;;
    --require-lrc)
      require_lrc=1; shift ;;
    --no-require-lrc)
      require_lrc=0; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2 ;;
  esac
done

if [[ -z "$meta_file" || -z "$output_dir" ]]; then
  echo "Error: --meta-file and --output-dir are required." >&2
  usage >&2
  exit 2
fi

if [[ ! -f "$meta_file" ]]; then
  echo "Error: metadata file not found: $meta_file" >&2
  exit 66
fi

mkdir -p "$output_dir"
if [[ -z "$json_file" ]]; then
  json_file="$output_dir/generate.result.json"
fi

echo "Generating Suno clips..." >&2
bash "$script_dir/generate_with_suno.sh" --meta-file "$meta_file" --output-dir "$output_dir" > "$json_file"

ids="$(python3 - "$json_file" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

clips = data.get("data", data) if isinstance(data, dict) else data
if not isinstance(clips, list):
    raise SystemExit(1)

ids = [clip.get("id") for clip in clips if isinstance(clip, dict) and clip.get("id")]
print(" ".join(ids))
PY
)"

if [[ -z "$ids" ]]; then
  echo "Error: no clip IDs found in generation JSON: $json_file" >&2
  exit 1
fi

echo "Generated IDs: $ids" >&2

download_args=(
  bash "$script_dir/download_clips.sh"
  --ids "$ids"
  --output-dir "$output_dir"
  --lyrics
  --lyrics-format "$lyrics_format"
  --initial-wait "$initial_wait"
  --retries "$retries"
  --delay "$delay"
)

if [[ "$browser" -eq 1 ]]; then
  download_args+=(--browser)
else
  download_args+=(--no-browser)
fi

if [[ "$require_lrc" -eq 1 ]]; then
  download_args+=(--require-lrc)
fi

"${download_args[@]}"

echo "" >&2
echo "Generation JSON: $json_file" >&2
echo "Completed Suno generate/download/LRC workflow." >&2
