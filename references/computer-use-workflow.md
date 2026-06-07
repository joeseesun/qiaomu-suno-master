# Suno Computer Use Workflow

Use this lane when the CLI submit path hangs, the Codex Browser plugin is not
available, Chrome CDP prompts are unreliable, or the user explicitly asks to use
Computer Use.

Computer Use owns browser clicks and visible-page state. The local manifest
workflow still owns durable files, downloads, LRC validation, and later
publishing handoff.

## Output Directory Policy

Unless the user explicitly gives a folder, always create and use:

```text
~/Documents/Suno/<song-title>/
```

Do not use the current repo/workspace directory as the default output location.
The current working directory is often incidental to the agent session and is
not a music asset library.

## Preparation

1. Finalize `TITLE`, `STYLE_DESCRIPTION`, `EXCLUDE_STYLES`, and `LYRICS_FILE`.
2. If no manifest exists, create it with the default output directory:

```bash
OUTPUT_DIR="$HOME/Documents/Suno/$TITLE"
python3 scripts/run_workflow.py init \
  --manifest "$OUTPUT_DIR/song.manifest.json" \
  --title "$TITLE" \
  --style "$STYLE_DESCRIPTION" \
  --exclude "$EXCLUDE_STYLES" \
  --lyrics-file "$LYRICS_FILE" \
  --output-dir "$OUTPUT_DIR"
```

3. Run the non-destructive preflight:

```bash
python3 scripts/suno_doctor.py --output-dir "$OUTPUT_DIR"
```

## Computer Use Generation

1. Call `get_app_state` for Google Chrome before any Computer Use action.
2. Open `https://suno.com/create`.
3. Confirm the visible account is logged in and has credits. If the page shows a
   login or security challenge, stop at that state and ask the user to complete
   only that action.
4. Select `Advanced` mode.
5. Confirm model `v5.5` unless the user requested another model.
6. Fill the lyrics textarea from `LYRICS_FILE`.
7. Fill styles with:

```text
STYLE_DESCRIPTION, -excluded style one, -excluded style two
```

8. Fill song title with `TITLE`.
9. Click `Create`.
10. Wait until the two newest rows with the title are visible and playable. Do
    not report success before visible rows or links exist.

If Suno generates rows but the CLI wrapper is still waiting for JSON, treat the
web UI as authoritative: stop the stale CLI process, capture the visible rows,
and continue from the share-link path below.

## Link Capture

For each generated row:

1. Click the row's `Share clip` button.
2. Confirm the toast says the song link was copied.
3. Read the clipboard:

```bash
pbpaste
```

Suno may copy a short share URL such as:

```text
https://suno.com/s/<share-id>
```

Resolve each share URL to a real clip ID:

```bash
curl -L -s "$SHARE_URL" \
  | rg -o 'suno.com/song/[A-Za-z0-9_-]+|cdn1\.suno\.ai/[A-Za-z0-9_-]+\.mp3' \
  | head
```

Prefer the UUID from `suno.com/song/<clip-id>`. If only the CDN URL is visible,
use the UUID in `cdn1.suno.ai/<clip-id>.mp3`.

## Download And LRC

Use the manifest-first download path after capturing both clip IDs:

```bash
python3 scripts/run_workflow.py download \
  --manifest "$OUTPUT_DIR/song.manifest.json" \
  --ids "ID1 ID2"
```

This downloads MP3s, fetches timed LRC, validates the LRC files, and updates the
manifest.

If the CLI downloader cannot fetch audio but the rows are visible, use Computer
Use directly:

1. Open the row's `More options` menu.
2. Choose `Download`.
3. Choose `Audio` or `MP3`.
4. Move the browser-downloaded MP3 into `OUTPUT_DIR`.
5. Still run timed lyric export and validation:

```bash
python3 scripts/export_suno_assets.py ID1 ID2 --format lrc --output "$OUTPUT_DIR"
python3 scripts/validate_lrc.py "$OUTPUT_DIR"
```

Do not publish or upload a track to a music player until `validate_lrc.py`
passes with real `[mm:ss.xx]` timestamped lines.

## Completion Report

Report:

- Suno share links and/or canonical `https://suno.com/song/<id>` links
- `OUTPUT_DIR`
- MP3 files
- LRC files
- manifest status and LRC validation result
