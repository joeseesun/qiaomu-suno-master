# Suno Computer Use Workflow

Use this lane when the CLI submit path hangs, the Codex Browser plugin is not
available, Chrome CDP prompts are unreliable, or the user explicitly asks to use
Computer Use.

Computer Use owns browser clicks, visible-page state, generation submission,
link capture, and visible download attempts. The local manifest workflow still
owns durable metadata, file organization, LRC validation, and later publishing
handoff.

This workflow is intentionally boring: once selected, every Suno-facing action
stays in the same visible browser route. Do not "help" by mixing in CDP, CLI, a
browser plugin, or raw requests after the user asked for Computer Use.

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
- Shell commands must not click, submit, generate, refresh Suno auth, solve
  captcha, fetch hidden audio URLs, or download MP3s directly in a locked task.
  The MP3 source must be Chrome's visible Suno UI download.
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

3. Run only the non-destructive local preflight:

```bash
python3 scripts/suno_doctor.py --output-dir "$OUTPUT_DIR"
```

Do not run `ensure_suno_chrome_session.sh`, `launch_suno_cdp_chrome.sh`,
`suno auth`, `run_workflow.py generate`, `run_workflow.py download`,
`generate_with_suno.sh`, `download_clips.sh`, or any CDP helper unless the user
explicitly approves leaving Computer Use.

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

If there is a stale CLI/browser-helper process from an earlier non-locked
attempt, stop it before proceeding. Do not let that process complete the task
for a Computer Use request.

## Link Capture

For each generated row:

1. Click the row's `Share clip` button.
2. If Suno exposes a Share menu, click the copy-link action. If the row's
   `Share clip` button copies directly, confirm the toast says the song link
   was copied.
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

Keep the raw share URLs in the manifest/report even when canonical IDs are not
resolved yet. A copied Suno share link is valid evidence that generation
completed through the UI.

## Download And LRC

When the task is Computer Use-locked, attempt audio download through the Suno web
UI first:

1. In the visible row list, open the target row's `More options` menu.
2. Choose `Download`.
3. Choose `MP3 Audio` when present. If Suno labels the same control as `Audio`
   or `MP3`, choose that visible MP3/audio option.
4. Wait for Chrome's download shelf/popover or `~/Downloads` to show the MP3 as
   complete. Do not use a hidden URL downloader.
5. Repeat for each generated row or for one representative version per style if
   the user's task asks for several styles rather than every generated take.
6. Move the browser-downloaded MP3 into `OUTPUT_DIR`.

Use this organization command shape after Chrome's UI download is complete:

```bash
mkdir -p "$OUTPUT_DIR"
mv -f "$HOME/Downloads/$TITLE.mp3" "$OUTPUT_DIR/$TITLE.mp3"
```

If Chrome creates duplicate names such as `$TITLE (1).mp3`, preserve both files
with clear names such as `$TITLE v2.mp3` instead of overwriting or deleting a
take.

For a multi-song request, use one directory per title:

```text
~/Documents/Suno/<song-title>/<song-title>.mp3
```

Check the final placement with:

```bash
find "$HOME/Documents/Suno" -maxdepth 2 -type f -name '*.mp3' -print | sort
```

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
