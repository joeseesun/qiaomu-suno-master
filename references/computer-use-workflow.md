# Suno Computer Use Workflow

Use this lane when the CLI submit path hangs, the Codex Browser plugin is not
available, Chrome CDP prompts are unreliable, or the user explicitly asks to use
Computer Use.

Computer Use owns browser clicks, visible-page state, generation submission,
link capture, and visible download attempts. The local manifest workflow still
owns durable metadata, file organization, LRC validation, and later publishing
handoff.

## Lane Lock

If the user explicitly asks to use Computer Use, this workflow is a hard lock
for the whole task.

- Do not switch to CLI generation, Chrome CDP, the Codex Browser plugin, raw
  Suno API calls, or captcha-assisted CLI generation after selecting this lane.
- Do not run `suno generate`, `run_workflow.py generate`,
  `generate_with_suno.sh`, or CDP captcha helpers during a Computer Use-locked
  generation task.
- Shell commands are allowed only for local preparation and post-processing:
  reading lyrics/manifests, copying prepared text to the clipboard, moving files
  downloaded by the browser UI, resolving share links after Computer Use copied
  them, exporting timed lyrics for captured IDs, validating LRC, and updating
  the manifest.
- If Chrome is being actively used by the user, Computer Use cannot acquire the
  app, Suno requires login/security/captcha action, or a visible download
  control is unavailable, stop and report that blocker. Do not silently fall
  back to another lane.
- A partially completed non-Computer-Use attempt does not satisfy a
  Computer Use-locked request. Treat it as out of scope, clean up any stale
  background process, and restart the requested item through Computer Use.

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

When the task is Computer Use-locked, attempt audio download through the Suno web
UI first:

1. Open the row's `More options` menu.
2. Choose `Download`.
3. Choose `Audio` or `MP3`.
4. Move the browser-downloaded MP3 into `OUTPUT_DIR`.
5. Repeat for both generated rows.

After the browser UI download attempt, use local tools only for post-processing
captured IDs and downloaded files:

```bash
python3 scripts/export_suno_assets.py ID1 ID2 --format lrc --output "$OUTPUT_DIR"
python3 scripts/validate_lrc.py "$OUTPUT_DIR"
```

If the browser UI cannot expose a download control but the song links or clip
IDs were captured, report the generated links and the download blocker. Do not
switch to CLI download unless the user explicitly approves leaving the Computer
Use lane.

For non-locked browser fallback tasks, the manifest-first download path remains
allowed after capturing both clip IDs:

```bash
python3 scripts/run_workflow.py download \
  --manifest "$OUTPUT_DIR/song.manifest.json" \
  --ids "ID1 ID2"
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
