---
name: qiaomu-suno-master
description: |
  Turn a song idea, story, article, theme, or lyrics request into polished Suno-ready lyrics, style tags, and generated music through the local Rust suno CLI. Trigger for 写一首歌, 创作歌曲, 生成音乐, Suno 生成, /suno, /music, or requests to create lyrics and render them through Suno.
---

# Qiaomu Suno Master

Create commercial-grade Suno lyrics, then use the installed `suno` command to generate and optionally download the music.
It also includes a local music genre finder so vague moods can become precise Suno style tags.

Suno login state is short-lived. Treat Chrome's logged-in Suno web session as
the source of truth, and treat the CLI as the fast path only. If the CLI reports
`auth_expired`, `JWT expired`, `401`, `403`, captcha failures, or cannot find a
browser session, immediately use the Suno web UI fallback instead of retrying the
same CLI request.

## Generation Execution Contract

This skill must prefer a deterministic two-lane generation path over open-ended
exploration:

1. **Make the CLI path work first.**
   - Ensure the installed `suno` CLI exists and run `suno config check`.
   - Refresh auth from the real Chrome Suno session; if refresh fails, run
     `suno auth --login --quiet`.
   - Run `scripts/generate_with_suno.sh` once with the default captcha-backed
     path.
   - Retry CLI at most one more time only for the narrow hCaptcha/CDP-launch
     failure class, using either `--no-captcha` or a user-provided
     `--token "$HCAPTCHA_TOKEN"`.
2. **If CLI generation is blocked, Codex controls the browser.**
   - Use the Codex Browser plugin when available. If it is not exposed in the
     current session, use Chrome/Computer Use against the logged-in Suno page.
   - Open `https://suno.com/create`, fill title, lyrics, styles, model, and
     options from the prepared local files, click Create, wait for the generated
     rows, and capture song IDs/links.
   - Only ask the user to intervene for actions automation cannot legally or
     reliably complete, such as human login, account security checks, or a live
     captcha challenge.
3. **Stop forbidden exploration.**
   - Do not hand-craft Suno generate POST requests, inject copied browser cookies
     into throwaway profiles, replay captured payloads, or repeatedly test
     captcha variants unless the user explicitly asks to debug Suno itself.
   - If the user provides existing Suno song URLs or clip IDs, skip generation
     and continue the stable download, LRC validation, cover-generation, and
     upload path.
   - Never report generation success until real Suno song links or clip IDs have
     been captured.

## When To Use

Use this skill when the user wants:

- A new song from a theme, article, story, mood, or keywords
- Suno-ready lyrics with sections such as `[Verse]`, `[Chorus]`, and `[Bridge]`
- Music generated through the local Rust `suno` CLI, with web UI fallback
- A completed song file downloaded locally
- Existing Suno clip IDs exported as audio, video/MTV, timed LRC, SRT, clean SRT, or Markdown lyrics
- Music genre/style recommendations before lyric writing or generation
- Timestamped `.lrc` lyrics for any song that will be uploaded to a music player or published as a playable web track

Do not use this skill for pure music theory, ordinary poetry not intended for Suno, or non-Suno audio editing.

## Inputs To Resolve

Infer these from the user request when possible:

- `title`: short, memorable song title
- `lyrics`: complete Suno-ready lyrics with structural tags
- `lrc_required`: default yes when generating/downloading music for upload, publishing, or a music-player website
- `style_description`: comma-separated Suno style tags
- `exclude_styles`: comma-separated styles, instruments, or moods to avoid
- `genre_candidates`: optional recommended genres from `scripts/find_music_genres.py`
- `title_options`: three concise title candidates before choosing the final title
- `model`: default `v5.5`
- `vocal`: optional `male` or `female`
- `output_dir`: default to `~/Documents/Suno/<song-title>/` unless the user gives a folder
- `generate`: whether to run Suno immediately; default yes when the user asks to generate music

If the user only asks for lyrics, produce the requested creative output without running `suno`.

## Workflow

1. Analyze the song brief: theme, audience, language, mood, style, vocal, tempo, and any forbidden elements.
2. If style is missing, vague, or worth sharpening, read `references/genre-selection.md` and run `python3 scripts/find_music_genres.py "<brief or mood>" --limit 5`.
3. Choose 1-3 fitting genre tags plus a small set of vocal, instrument, tempo, and mood tags. Keep `style_description` focused.
4. Read `references/lyric-craft.md` and apply the lyric quality rules.
5. Produce:
   - `title_options`
   - selected `title`
   - optional `genre_candidates`
   - `style_description`
   - `exclude_styles`
   - `lyrics`
6. Treat Suno-ready lyrics and LRC as separate deliverables:
   - `lyrics` is the creative input sent to Suno and may use `[Verse]`, `[Chorus]`, `[Bridge]`, etc.
   - `.lrc` is the timed output fetched after generation from Suno aligned lyrics.
   - Never upload or publish plain Suno lyrics as music-player synced lyrics.
   - Music-player cover art is a separate generated design asset, not the Suno source cover.
7. Save lyrics to a temporary `.txt` file when running the CLI. Prefer a file over shell-quoting long multiline lyrics.
8. Before any generation or download step, verify that a real Chrome Suno web
   session exists. Run:

```bash
bash scripts/ensure_suno_chrome_session.sh
```

If Suno asks for login, use the Browser/Chrome/Computer Use tools to open
`https://suno.com/create`, let the user or existing profile complete login, then
continue. Do not keep retrying the CLI against an expired JWT.

9. Before any CLI step, ensure the Rust CLI exists:

```bash
bash scripts/ensure_suno_cli.sh
```

Auth is handled automatically by both `generate_with_suno.sh` and
`download_clips.sh` when the CLI accepts Chrome's session. Only call manually for
`export_suno_assets.py`:

```bash
suno auth --refresh --quiet 2>/dev/null || suno auth --login --quiet
```

10. **Generate fast path via CLI** (returns JSON with clip IDs, does NOT download):

```bash
bash scripts/generate_with_suno.sh --meta-file "$META_FILE" --output-dir "$OUTPUT_DIR"
```

Parse the JSON output to extract clip IDs from `data[].id`.

If this command emits `GENERATION_BLOCKED`, or returns JSON with
`"status": "error"`, follow `references/browser-fallback.md` as the Codex
browser-generation lane. Do not attempt raw Suno API calls after a blocked
generation.

11. **Download fast path with browser-first downloader** (separate step with
retry, waits for CDN):

```bash
bash scripts/download_clips.sh --ids "ID1 ID2" --output-dir "$OUTPUT_DIR"
```

For any song that will be uploaded to a music player, a website, or any user-facing
playable catalog, LRC is mandatory. Request and validate LRC at download time:

```bash
bash scripts/download_clips.sh --ids "ID1 ID2" --output-dir "$OUTPUT_DIR" \
  --lyrics --lyrics-format lrc --require-lrc
```

Or pipe directly from generate:

```bash
bash scripts/generate_with_suno.sh --meta-file "$META_FILE" --output-dir "$OUTPUT_DIR" \
  | bash scripts/download_clips.sh --output-dir "$OUTPUT_DIR" \
      --lyrics --lyrics-format lrc --require-lrc
```

If `--require-lrc` fails, do not upload/publish the track yet. Retry aligned
lyrics after Suno finishes processing:

```bash
python3 scripts/export_suno_assets.py ID1 ID2 --format lrc --output "$OUTPUT_DIR"
python3 scripts/validate_lrc.py "$OUTPUT_DIR"
```

`download_clips.sh` features:
- Waits 5s for CDN propagation before first attempt
- Retries up to 3 times with 10s delay between attempts
- Auto-refreshes auth from Chrome
- Uses Chrome/CDP browser download first, then falls back to `suno download`
- Can fetch timestamped `.lrc` lyrics through `suno timed-lyrics`
- `--require-lrc` fails the workflow unless a real timestamped `.lrc` is present
- Accepts IDs via `--ids` flag or piped JSON from generate

12. **LRC gate before upload/publish**:

Before uploading to `music.qiaomu.ai` or any music player, verify the `.lrc`
file exists and contains real `[mm:ss.xx]` timestamps:

```bash
python3 scripts/validate_lrc.py "$OUTPUT_DIR"
```

Use the validated `.lrc` file as the track lyrics payload. Do not use the
original `.txt` Suno prompt lyrics unless the destination explicitly asks for
unsynced plain lyrics.

13. **Qiaomu Music cover gate before upload/publish**:

Before uploading to `music.qiaomu.ai`, always generate a fresh square album cover
with `qiaomu-image-generator` from the song title, style, and validated lyrics.
Do not use Suno's `image_url` or original generated cover as the published cover.

Use the `album_cover` template with:

- `style`: `album-mondo-cover` by default, or `negative-space-poster` for sparse/ambient/psychological songs
- `aspect_ratio`: `1:1`
- `description`: one symbolic visual distilled from the lyrics, with Mondo-style limited palette, single focal point, and `no text`
- `filename`: a stable slug ending in `-cover.png`

Minimum generation shape:

```json
{
  "template": "album_cover",
  "cover": {
    "enabled": true,
    "filename": "song-slug-cover.png",
    "style": "album-mondo-cover",
    "aspect_ratio": "1:1",
    "description": "1:1 square album cover, no text. ... distilled lyric imagery ..."
  },
  "defaults": {
    "provider": "jimeng",
    "style": "album-mondo-cover",
    "aspect_ratio": "1:1"
  }
}
```

Generate with:

```bash
python3 ~/.agents/skills/qiaomu-image-generator/scripts/generate.py "$VISUAL_CONFIG" \
  --workers 1 --no-insert --output "$OUTPUT_DIR/cover.result.json"
```

Verify the cover before upload:

```bash
file "$OUTPUT_DIR"/*-cover.png
sips -g pixelWidth -g pixelHeight "$OUTPUT_DIR"/*-cover.png
```

The cover must be square and must be uploaded as the `cover` multipart field
together with the MP3 and validated LRC.

14. **Codex browser generation lane**:

Read `references/browser-fallback.md` and use it when:

- the user explicitly asks for reliable Suno generation
- the CLI auth has expired or is rejected
- captcha automation stalls
- a generated clip is visible in the Suno web list but CLI download fails

This is not a passive handoff. Codex should control the browser:

1. Open `https://suno.com/create` in the logged-in Chrome profile.
2. Switch to Advanced mode and model `v5.5` unless the user requested another model.
3. Fill Lyrics, Styles, and Song Title from the local files/meta.
4. Click `Create`, wait for the two generated rows to appear, and record both
   song links.
5. When rows become playable, click each row's menu/download controls in the web
   UI, or use `download_clips.sh --ids ... --browser` if IDs are visible.

If browser automation cannot complete login, captcha, or Create submission
because the page requires a human security action, pause at that exact browser
state and ask the user to complete only that action. After it is complete, Codex
continues capturing IDs, downloading, validating LRC, generating cover art, and
uploading.

15. **Send to Feishu** (only in bridge context with `chat_id`):

```bash
cd "$OUTPUT_DIR"
lark-cli config bind --source lark-channel --identity bot-only
for f in *.mp3; do
  lark-cli im +messages-send --as bot --chat-id "$CHAT_ID" --file "./$f"
done
```

16. Report the output directory, downloaded file paths, LRC validation status,
generated cover path, published track URL, and/or Suno song links.

Never save generated songs, subtitles, videos, or exported lyric files inside the skill directory. Use `~/Documents/Suno/<song-title>/` by default.

## CLI Notes

- The upstream CLI is `paperfoot/suno-cli`, installed as the `suno` command.
- If `suno` is missing, run `bash scripts/ensure_suno_cli.sh` before continuing. The script installs from the upstream project, tries Homebrew first, and falls back to Cargo if Homebrew fails.
- Verify with `suno --version` after install.
- Auth is synced from Chrome's logged-in Suno session (`suno auth --refresh` or `suno auth --login`), but Suno can reject the CLI JWT even when the web UI remains logged in. In that case the web UI is authoritative.
- Prefer `bash scripts/generate_with_suno.sh` for generation only as the fast path. It auto-refreshes auth and defaults to the captcha-backed submit path, but must not be retried repeatedly after auth/captcha rejection.
- CLI retry budget is two total generation attempts: default captcha-backed once, then one targeted retry only for hCaptcha/CDP launch failure with `--no-captcha` or a provided `--token`.
- **IMPORTANT**: Do NOT use `--download` on generate. CDN needs time to propagate. Always use the separate `download_clips.sh` after generation completes.
- Use `scripts/download_clips.sh` for all downloads — it handles retry logic and CDN delay.
- For generated songs that will be uploaded or published, always add `--lyrics --lyrics-format lrc --require-lrc` to `download_clips.sh`.
- For songs uploaded to `music.qiaomu.ai`, always generate a new `qiaomu-image-generator` `album_cover` cover from lyrics and upload it instead of the Suno source cover.
- If clip IDs are visible in the web list, `download_clips.sh --ids "ID1 ID2" --browser` is the preferred download retry because it asks Chrome to fetch the audio through the browser pipeline first.
- Use `scripts/export_suno_assets.py` when the user wants SRT/LRC/timed lyrics, clean MTV subtitles, audio download, or video/MTV download from existing clip IDs.
- Use `scripts/validate_lrc.py "$OUTPUT_DIR"` before any music-player upload. A file with only `[Verse]`/`[Chorus]` markers is plain lyrics, not LRC.
- Use `scripts/clean_srt_for_mtv.py` to remove Suno structural markers such as `[Verse]` and `[Chorus]` from subtitle files.
- If Suno's captcha solver is flaky in a given browser session, fall back to `--no-captcha` only when you have another valid submission path or a manual `--token`.

## Genre Finder

This skill vendors `joeseesun/music-genre-finder` data in `references/genre-finder/`.

Use:

```bash
python3 scripts/find_music_genres.py "深夜 空灵 梦幻" --limit 5
python3 scripts/find_music_genres.py "raw energetic punk" --limit 5
python3 scripts/find_music_genres.py "世界音乐 鼓 长笛" --json
```

For Suno, convert recommendations into concise style tags. Prefer 2-4 genre tags plus vocal, instrument, tempo, and mood tags. Avoid dumping many related subgenres into one prompt.

## Asset Export

For existing clip IDs:

```bash
python3 scripts/export_suno_assets.py <clip-id> --format lyrics --clean-srt
```

Without `--output`, assets are saved under `~/Documents/Suno/<clip-title>/`.

Useful formats:

- `audio`: download MP3/audio
- `video`: download Suno video/MTV asset when available
- `json`: save timed lyrics JSON
- `lrc`: save music-player lyrics
- `srt`: save subtitle file
- `md`: save AI-readable timestamped lyrics Markdown
- `lyrics`: shortcut for `json,lrc,srt,md`
- `all`: shortcut for `audio,video,json,lrc,srt,md`

To retry timed lyrics from existing clip IDs, use the Rust `suno` CLI export path:

```bash
python3 scripts/export_suno_assets.py <clip-id> --format lrc --output "$OUTPUT_DIR"
python3 scripts/export_suno_assets.py <clip-id1> <clip-id2> --format lyrics --output "$OUTPUT_DIR"
```

For MTV:

```bash
python3 scripts/export_suno_assets.py <clip-id> --output "$OUTPUT_DIR" --format video,lyrics --clean-srt
```

## Chrome CDP Auth Assist

This skill vendors a lightweight Chrome DevTools Protocol helper from `pasky/chrome-cdp-skill` as `scripts/cdp.mjs`.

Use it only when the user wants to reuse an existing Chrome login or debug Suno browser state. Chrome must have remote debugging enabled. If CDP is unavailable, fall back to `suno auth --login`.

Known issue: the upstream `suno` CLI captcha auto-solver may open a piloted
Chrome and fail with `CDP Runtime.evaluate ws err: Connection reset...`.
Another common failure is `auth_expired` even after `suno auth --login` succeeds.
When either happens, switch to `references/browser-fallback.md` immediately.

## Output Style

For lyrics-only requests where the user asks to use this creator prompt, output only Markdown code blocks in this order:

```markdown
```lyrics
...
```

```style
style-description-tags
```

```exclude
exclude-style-tags
```

```titles
1. ...
2. ...
3. ...
```
```

For generated music, keep the final response brief:

- mention that generation completed or where it stopped
- include the output folder
- include the next command only if the user needs to authenticate or retry
