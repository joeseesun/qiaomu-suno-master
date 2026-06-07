# Manifest Workflow

Use the manifest-first path when a song may be generated, downloaded, validated,
or handed off to publishing. It keeps the creative prompt, Suno clip IDs, files,
and validation status in one durable JSON file.

## Shape

Create one manifest per song:

```json
{
  "schema_version": 1,
  "status": "prepared",
  "title": "Song Title",
  "style_description": "alt-pop, female-vocals, warm-synths, mid-tempo",
  "exclude_styles": "trap, metal, spoken-word",
  "model": "v5.5",
  "vocal": "",
  "lyrics_file": "/absolute/path/lyrics.txt",
  "output_dir": "/absolute/path/output",
  "captcha_solver": true,
  "generation": {
    "json_file": "/absolute/path/output/generate.result.json",
    "clip_ids": [],
    "song_links": [],
    "classified_error": "",
    "returncode": null
  },
  "assets": {
    "audio": [],
    "lrc": [],
    "srt": [],
    "markdown_lyrics": [],
    "video": [],
    "cover": []
  },
  "validation": {
    "lrc": {
      "ok": false,
      "checked_at": "",
      "messages": []
    }
  }
}
```

Do not store account tokens, cookies, hCaptcha tokens, API keys, or passwords in
the manifest. If a token is needed, pass it through the process environment.

## Commands

Prepare from finalized lyrics and style tags:

```bash
python3 scripts/run_workflow.py init \
  --manifest "$OUTPUT_DIR/song.manifest.json" \
  --title "$TITLE" \
  --style "$STYLE_DESCRIPTION" \
  --exclude "$EXCLUDE_STYLES" \
  --lyrics-file "$LYRICS_FILE" \
  --output-dir "$OUTPUT_DIR"
```

For an existing-clip workflow, `--style` and `--lyrics-file` may be omitted if
`--ids` contains the Suno clip IDs or song URLs.

Preflight without opening Chrome:

```bash
python3 scripts/suno_doctor.py --output-dir "$OUTPUT_DIR"
```

Generate, download MP3, fetch LRC, validate LRC, and update the manifest:

```bash
python3 scripts/run_workflow.py generate \
  --manifest "$OUTPUT_DIR/song.manifest.json"
```

Dry-run the generated shell command without calling Suno:

```bash
python3 scripts/run_workflow.py generate \
  --manifest "$OUTPUT_DIR/song.manifest.json" \
  --dry-run
```

Download existing clips:

```bash
python3 scripts/run_workflow.py download \
  --manifest "$OUTPUT_DIR/song.manifest.json" \
  --ids "ID1 ID2"
```

Validate LRC again after Suno finishes aligned lyrics processing:

```bash
python3 scripts/run_workflow.py validate-lrc \
  --manifest "$OUTPUT_DIR/song.manifest.json"
```

Show the current state:

```bash
python3 scripts/run_workflow.py status \
  --manifest "$OUTPUT_DIR/song.manifest.json"
```

## Status Values

- `prepared`: lyrics, style tags, and output paths are ready.
- `ready`: dry-run generated the meta env and command.
- `lrc_ready`: MP3 and timestamped LRC are present and validated.
- `downloaded`: audio downloaded, but validated LRC is not ready.
- `generation_blocked`: auth, captcha, schema, or Suno session issue. Use the
  browser fallback lane.
- `lrc_pending`: Suno has not exposed usable aligned lyrics yet.
- `download_failed`: generation IDs may exist, but audio download failed.
- `failed`: unclassified failure; inspect `workflow.log`.

## Files

The workflow writes these files under `output_dir`:

- `song.manifest.json`: durable song state.
- `suno-meta.env`: generated shell metadata for the existing shell wrappers.
- `generate.result.json`: raw Suno generation JSON with clip IDs.
- `workflow.log`: combined command output for debugging.
