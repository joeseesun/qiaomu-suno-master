# Suno Codex Browser Generation

Use this path whenever the CLI cannot generate reliably after the allowed CLI
repair attempts. Suno's web session often remains valid after the CLI JWT is
rejected, so the browser UI is the authoritative generation lane.

## Trigger Conditions

Switch to browser fallback immediately if any of these appear:

- `auth_expired`
- `JWT expired`
- `JWT expired or rejected by Suno`
- `401` or `403`
- `schema_drift`
- `token_validation_failed`
- `"status": "error"` in CLI JSON output
- `No Suno session found`
- captcha never loads or never completes
- generated songs are visible on suno.com but CLI download fails

Before switching here, make one real CLI repair pass: verify `suno config check`,
sync auth from Chrome with `suno auth --refresh` or `suno auth --login --quiet`,
then run the wrapper. A second CLI attempt is allowed only for a narrow
hCaptcha/CDP launch failure, using `--no-captcha` or a user-provided token.

Do not keep retrying `suno generate` after these errors unless the user provides
a new token or explicitly asks to debug the CLI. Do not explore raw Suno
generation endpoints, copied cookies, throwaway Chrome profiles, or captured web
payloads during ordinary song generation work.

## Browser Control Policy

This is an agent-controlled browser lane, not a user handoff:

- Prefer the Codex Browser plugin when available.
- If the Browser plugin is not exposed, use Chrome or Computer Use to operate
  the logged-in Suno page.
- Codex must fill the form, click Create, monitor generation, extract IDs/links,
  and continue download/publish work.
- Ask the user to act only when the page requires a human security step that the
  agent cannot complete, such as login confirmation, account challenge, or a
  live captcha.
- **Existing-ID path**: if the request already includes Suno IDs or song URLs,
  skip generation entirely and only perform export/download/publish steps.

## Generation Procedure

1. Open `https://suno.com/create` using the Codex Browser plugin if available;
   otherwise use Chrome/Computer Use.
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

If any step is blocked by login, captcha, or UI controls that require a human
security action, stop at that browser state and ask the user to complete only
that step. Then continue this procedure. Keep these details available:

- the exact prepared title
- the style string
- the lyrics file path
- the output directory

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
- Never claim generation success from a CLI JSON error, a visible form, or a
  partially filled browser page. Success requires captured Suno song links or
  clip IDs.
