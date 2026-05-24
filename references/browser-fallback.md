# Suno Browser Fallback

Use this path whenever the CLI cannot generate or download reliably. Suno's web
session often remains valid after the CLI JWT is rejected, so the browser UI is
the authoritative fallback.

## Trigger Conditions

Switch to browser fallback immediately if any of these appear:

- `auth_expired`
- `JWT expired`
- `JWT expired or rejected by Suno`
- `401` or `403`
- `No Suno session found`
- captcha never loads or never completes
- generated songs are visible on suno.com but CLI download fails

Do not keep retrying `suno generate` after these errors unless the user provides
a new token or explicitly asks to debug the CLI.

## Generation Procedure

1. Open `https://suno.com/create` in Chrome using the available Browser, Chrome,
   or Computer Use tool.
2. Confirm the left sidebar shows the logged-in Suno account and plan, not
   `Log in` or `Join Suno`.
3. Select Advanced mode.
4. Confirm model `v5.5` unless the user requested another model.
5. Fill the Lyrics textarea from `LYRICS_FILE`.
6. Fill Styles with:

```text
STYLE_DESCRIPTION, -excluded style one, -excluded style two
```

7. Expand More Options and fill Song Title with `TITLE`.
8. Click `Create`.
9. Wait until two new rows with the title appear in the workspace list.
10. Record both `https://suno.com/song/<id>` links from the rows.

## Download Procedure

Prefer this order:

1. If song links or clip IDs are visible, run:

```bash
bash scripts/download_clips.sh --ids "ID1 ID2" --output-dir "$OUTPUT_DIR" --browser
```

2. If the script cannot connect to CDP but the Suno rows are visible, use the web
   UI controls directly:
   - open the row's More options menu
   - choose Download
   - choose Audio / MP3 when offered
   - save or move the browser-downloaded file to `OUTPUT_DIR`

3. If neither path downloads, leave the Suno song links in the final response
   and state that browser download controls were unavailable.

## Agent Behavior

- Keep local lyric/meta files even when using the browser UI.
- Report both generated versions because Suno usually creates two clips per
  `Create` click.
- If the user asked for "generate music", web UI submission counts as successful
  generation once the new song rows and links appear.
- If MP3 files were not downloaded, say that clearly and include the song links.
