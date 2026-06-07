---
name: qiaomu-suno-master
description: |
  Turn a song idea, story, article, theme, or lyrics request into polished Suno-ready lyrics, style tags, and generated music through the local Rust suno CLI. Trigger for 写一首歌, 创作歌曲, 生成音乐, Suno 生成, /suno, /music, or requests to create lyrics and render them through Suno.
---

# Qiaomu Suno Master

Create commercial-grade Suno lyrics, then use the selected Suno execution lane
to generate and optionally download the music.
It also includes a local music genre finder so vague moods can become precise Suno style tags.

Suno login state is short-lived. Treat Chrome's logged-in Suno web session as
the source of truth, and treat the CLI as the fast path only. If the CLI reports
`auth_expired`, `JWT expired`, `401`, `403`, captcha failures, or cannot find a
browser session, immediately use the Suno web UI fallback instead of retrying the
same CLI request.

## Style Tag Selection Contract

When the user asks for Suno style tags, genre combinations, genre discovery, or
style sharpening, treat the local genre finder as mandatory evidence, not an
optional helper.

1. Read `references/genre-selection.md` before answering.
2. Run `python3 scripts/find_music_genres.py` from the skill directory. For
   style-only requests or broad briefs, run at least three focused queries that
   sample different axes of the brief: the user's original phrase, one or more
   adjacent genre families, and one or more production/texture/rhythm angles.
   A single query is acceptable only when the user gives a very narrow style and
   asks for minimal output.
3. Build a candidate palette from the database results first. Prefer genre tags
   that appeared in the finder output or are direct, obvious parents/children of
   those results.
4. Compose each Suno style string as 1-3 genre tags plus 2-5 vocal,
   instrument, tempo, production, or mood tags. Do not answer from taste alone,
   and do not dump a long related-genre list into one prompt.
5. For style-only requests, do not write lyrics or run Suno generation unless
   the user explicitly asks. Return useful combinations, the best starters, and
   `exclude_styles` when helpful.
6. If the finder fails or the database is unavailable, say that clearly and
   continue with a best-effort fallback instead of implying the tags were
   database-backed.

## Generation Execution Contract

This skill must prefer a deterministic lane over open-ended exploration.

0. **Honor explicit lane requests as a hard lock.**
   - If the user explicitly asks for Computer Use, the whole generation task
     stays on the Computer Use lane from form submission through visible link
     capture and browser download attempts. Do not switch to CLI, CDP,
     Browser plugin, raw API calls, or captcha-assisted CLI generation to
     "make progress".
   - In a Computer Use-locked task, shell commands may prepare lyrics,
     manifests, inspect files, move browser-downloaded files, resolve captured
     share links, and validate assets. They must not submit Suno generation,
     refresh generation auth, run `suno generate`, or drive CDP/CLI captcha
     helpers.
   - If Computer Use cannot proceed because the user is actively using the same
     browser, the page requires login/security/captcha action, or the desktop UI
     is unavailable, stop at that state and ask for that blocker to be cleared.
     Do not silently fall back to another generation lane.
   - The same lock-in rule applies to any other lane the user explicitly names:
     use that lane end to end, or stop and report the blocker.

1. **Make the CLI path work first.**
   Use this only when the user did not explicitly request another lane.
   - Ensure the installed `suno` CLI exists and run `suno config check`.
   - Refresh auth from the real Chrome Suno session; if refresh fails, run
     `suno auth --login --quiet`.
   - Run `scripts/generate_with_suno.sh` once with the default captcha-backed
     path.
   - Retry CLI at most one more time only for the narrow hCaptcha/CDP-launch
     failure class, using either `--no-captcha` or a user-provided
     `--token "$HCAPTCHA_TOKEN"`.
2. **If CLI generation is blocked, Codex controls the browser.**
   Use this only when the task is not locked to a different lane.
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
     and continue the stable download and LRC validation path.
   - If the user asks to upload or publish to Qiaomu Music, delegate that
     publishing step to `qiaomu-music-publisher`; do not implement Qiaomu Music
     upload inside this skill.
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
Do not use this skill for Qiaomu Music upload execution; use
`qiaomu-music-publisher` after MP3/LRC assets are ready.

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
- `song_manifest`: default to `$OUTPUT_DIR/song.manifest.json`
- `generate`: whether to run Suno immediately; default yes when the user asks to generate music

If the user only asks for lyrics, produce the requested creative output without running `suno`.

## Workflow

1. Analyze the song brief: theme, audience, language, mood, style, vocal, tempo, and any forbidden elements.
2. If style is missing, vague, worth sharpening, or the user specifically asks
   for style/tag recommendations, follow the Style Tag Selection Contract.
3. Choose 1-3 fitting genre tags plus a small set of vocal, instrument, tempo, and mood tags. Keep `style_description` focused.
4. For style-only requests, stop after delivering style combinations and any
   useful `exclude_styles`; do not continue to lyrics or generation unless asked.
5. Read `references/lyric-craft.md` and apply the lyric quality rules.
6. Produce:
   - `title_options`
   - selected `title`
   - optional `genre_candidates`
   - `style_description`
   - `exclude_styles`
   - `lyrics`
7. Treat Suno-ready lyrics and LRC as separate deliverables:
   - `lyrics` is the creative input sent to Suno and may use `[Verse]`, `[Chorus]`, `[Bridge]`, etc.
   - `.lrc` is the timed output fetched after generation from Suno aligned lyrics.
   - Never upload or publish plain Suno lyrics as music-player synced lyrics.
   - Music-player cover art is a separate generated design asset, not the Suno source cover.
8. Save lyrics to `$OUTPUT_DIR/lyrics.txt` when generating. Prefer a file over
shell-quoting long multiline lyrics.
   Unless the user explicitly gives a folder, `$OUTPUT_DIR` must be
   `~/Documents/Suno/<song-title>/`. Do not use the current repo/workspace
   directory as the default output location.
9. Use the manifest-first workflow for generation, download, LRC validation,
   and later publishing handoff. Read `references/manifest-workflow.md` when
   creating or updating a song manifest:

```bash
python3 scripts/run_workflow.py init \
  --manifest "$OUTPUT_DIR/song.manifest.json" \
  --title "$TITLE" \
  --style "$STYLE_DESCRIPTION" \
  --exclude "$EXCLUDE_STYLES" \
  --lyrics-file "$LYRICS_FILE" \
  --output-dir "$OUTPUT_DIR"
```

If the user provides existing Suno clip IDs or song URLs, include them with
`--ids` during `init` and skip generation. For this existing-clip path, style
and lyrics file may be omitted.

10. Before any generation or download step, run the non-destructive preflight:

```bash
python3 scripts/suno_doctor.py --output-dir "$OUTPUT_DIR"
```

Before submitting generation, verify that a real Chrome Suno web session exists:

```bash
bash scripts/ensure_suno_chrome_session.sh --timeout 12
```

If no CDP endpoint exists and Chrome is not already running, launch a CDP-enabled
Chrome session:

```bash
bash scripts/launch_suno_cdp_chrome.sh
```

If Chrome is already running without remote debugging, quit it fully before
relaunching with CDP flags, or use `--dedicated-profile` and log into Suno once
there. If Chrome shows a native debugging confirmation, pause for the user to
accept it once. Do not assume page-level CDP injection can dismiss native Chrome
security UI. Do not keep retrying the CLI against an expired JWT.

11. Before any CLI step, ensure the Rust CLI exists:

```bash
bash scripts/ensure_suno_cli.sh
```

Auth is handled automatically by both `generate_with_suno.sh` and
`download_clips.sh` when the CLI accepts Chrome's session. Only call manually for
`export_suno_assets.py`:

```bash
suno auth --refresh --quiet 2>/dev/null || suno auth --login --quiet
```

12. **Generate/download/LRC default path**:

```bash
python3 scripts/run_workflow.py generate \
  --manifest "$OUTPUT_DIR/song.manifest.json"
```

This wrapper writes `suno-meta.env`, preserves `generate.result.json`, extracts
clip IDs, downloads MP3s, fetches LRC, validates LRC, updates
`song.manifest.json`, and writes `workflow.log`.

Use dry-run when preparing or debugging without consuming Suno credits:

```bash
python3 scripts/run_workflow.py generate \
  --manifest "$OUTPUT_DIR/song.manifest.json" \
  --dry-run
```

If the manifest status becomes `generation_blocked`, or the wrapper emits
`GENERATION_BLOCKED`, follow `references/browser-fallback.md` as the Codex
browser-generation lane. Do not attempt raw Suno API calls after a blocked
generation.

13. **Existing-ID download path**:

```bash
python3 scripts/run_workflow.py download \
  --manifest "$OUTPUT_DIR/song.manifest.json" \
  --ids "ID1 ID2"
```

For any song that will be uploaded to a music player, a website, or any
user-facing playable catalog, LRC is mandatory and `run_workflow.py` requires it
by default. If LRC is pending, do not upload/publish the track yet. Retry later:

```bash
python3 scripts/run_workflow.py validate-lrc \
  --manifest "$OUTPUT_DIR/song.manifest.json"
```

14. **Low-level debug commands**:

Keep the separate `generate_with_suno.sh`, `generate_download_lrc.sh`, and
`download_clips.sh` commands for debugging, browser-fallback recovery, or
partial retries. These commands are not allowed during a Computer Use-locked
task unless the user explicitly approves leaving the Computer Use lane.

Generation only, returning JSON with clip IDs:

```bash
bash scripts/generate_with_suno.sh --meta-file "$META_FILE" --output-dir "$OUTPUT_DIR"
```

End-to-end shell wrapper:

```bash
bash scripts/generate_download_lrc.sh --meta-file "$META_FILE" --output-dir "$OUTPUT_DIR"
```

Download fast path with browser-first downloader:

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
- Uses Chrome/CDP browser download first when `websocket-client` is available,
  otherwise skips that attempt and goes straight to `suno download`
- Can fetch timestamped `.lrc` lyrics through `suno timed-lyrics`
- `--require-lrc` fails the workflow unless a real timestamped `.lrc` is present
- Accepts IDs via `--ids` flag or piped JSON from generate

15. **LRC gate before upload/publish**:

Before uploading to `music.qiaomu.ai` or any music player, verify the `.lrc`
file exists and contains real `[mm:ss.xx]` timestamps:

```bash
python3 scripts/validate_lrc.py "$OUTPUT_DIR"
```

Use the validated `.lrc` file as the track lyrics payload. Do not use the
original `.txt` Suno prompt lyrics unless the destination explicitly asks for
unsynced plain lyrics.

16. **Publishing handoff**:

If the destination is Qiaomu Music (`music.qiaomu.ai`,
`qiaomu-music-player-web`, "乔木音乐", "上传到乔木音乐", or "发布到乔木音乐"),
handoff to `qiaomu-music-publisher` after MP3 and timestamped LRC are ready:

```bash
python3 ~/.agents/skills/qiaomu-music-publisher/scripts/publish_suno_to_qiaomu_music.py \
  --ids "ID1 ID2" \
  --output-dir "$OUTPUT_DIR"
```

`qiaomu-music-publisher` owns site-specific login, cover handling, multipart
upload, and publication status. Keep this Suno skill focused on creation,
download, and LRC validation. Use `song.manifest.json` as the source of truth
for IDs, asset paths, and LRC status even if the publisher still takes explicit
CLI arguments.

17. **Generic music-player cover gate before upload/publish**:

For non-Qiaomu music-player uploads, generate a fresh square album cover with
`qiaomu-image-generator` from the song title, style, and validated lyrics unless
the destination explicitly wants the Suno source cover.

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

18. **Codex browser generation lane**:

Read `references/browser-fallback.md` and use it when:

- the user explicitly asks for reliable Suno generation
- the CLI auth has expired or is rejected
- captcha automation stalls
- a generated clip is visible in the Suno web list but CLI download fails
- the user explicitly asks to use Computer Use

If the user explicitly asks for Computer Use, the Computer Use lane lock applies
to generation and browser download attempts. Do not use CLI/CDP generation or
CLI/browser download helpers unless the user explicitly approves leaving that
lane.

This is not a passive handoff. Codex should control the browser:

1. Open `https://suno.com/create` in the logged-in Chrome profile.
2. Switch to Advanced mode and model `v5.5` unless the user requested another model.
3. Fill Lyrics, Styles, and Song Title from the local files/meta.
4. Click `Create`, wait for the two generated rows to appear, and record both
   song links.
5. When rows become playable, click each row's menu/download controls in the web
   UI. For non-locked browser fallback only, `download_clips.sh --ids ... --browser`
   is allowed if IDs are visible.

If browser automation cannot complete login, captcha, or Create submission
because the page requires a human security action, pause at that exact browser
state and ask the user to complete only that action. After it is complete, Codex
continues capturing IDs, downloading, validating LRC, and handing off any
site-specific publishing step to the appropriate publisher skill.

For direct Computer Use generation and download, read
`references/computer-use-workflow.md`. This lane should open Suno Create,
submit through the visible web UI, copy share links from the generated rows,
resolve share links to clip IDs, download audio through the visible Suno web UI
when possible, then use local post-processing only for file organization,
timed-lyrics export, LRC validation, and manifest updates. Do not run
`run_workflow.py generate`, `run_workflow.py download`, `suno generate`, or
CDP/captcha helpers in a Computer Use-locked task unless the user explicitly
approves switching lanes.

19. **Send to Feishu** (only in bridge context with `chat_id`):

```bash
cd "$OUTPUT_DIR"
lark-cli config bind --source lark-channel --identity bot-only
for f in *.mp3; do
  lark-cli im +messages-send --as bot --chat-id "$CHAT_ID" --file "./$f"
done
```

20. Report the output directory, manifest path, downloaded file paths, LRC
validation status, generated cover path, published track URL, and/or Suno song
links.

Never save generated songs, subtitles, videos, or exported lyric files inside the skill directory or incidental current repo. Use `~/Documents/Suno/<song-title>/` by default.

## CLI Notes

- The upstream CLI is `paperfoot/suno-cli`, installed as the `suno` command.
- If `suno` is missing, run `bash scripts/ensure_suno_cli.sh` before continuing. The script installs from the upstream project, tries Homebrew first, and falls back to Cargo if Homebrew fails.
- Verify with `suno --version` after install.
- Prefer `python3 scripts/run_workflow.py generate --manifest "$OUTPUT_DIR/song.manifest.json"` for ordinary generation tasks. It wraps generation, download, LRC validation, asset discovery, and status tracking.
- Run `python3 scripts/suno_doctor.py --output-dir "$OUTPUT_DIR"` before generation to check local prerequisites without spending credits.
- Auth is synced from Chrome's logged-in Suno session (`suno auth --refresh` or `suno auth --login`), but Suno can reject the CLI JWT even when the web UI remains logged in. In that case the web UI is authoritative.
- Prefer `bash scripts/generate_with_suno.sh` for generation only as the fast path. It auto-refreshes auth and defaults to the captcha-backed submit path, but must not be retried repeatedly after auth/captcha rejection.
- CLI retry budget is two total generation attempts: default captcha-backed once, then one targeted retry only for hCaptcha/CDP launch failure with `--no-captcha` or a provided `--token`.
- Latest verified path on 2026-05-25: `suno 0.5.7` default captcha-backed
  generation solved hCaptcha, submitted v5.5, returned two complete IDs, then
  `download_clips.sh --require-lrc` downloaded MP3 and validated LRC. Do not add
  `--no-captcha` by default.
- **IMPORTANT**: Do NOT use `--download` on generate. CDN needs time to propagate. Always use the separate `download_clips.sh` after generation completes.
- Use `scripts/download_clips.sh` for ordinary CLI/non-locked browser fallback
  downloads — it handles retry logic and CDN delay. In Computer Use-locked
  tasks, attempt browser UI downloads first and do not switch to CLI download
  without explicit user approval.
- For generated songs that will be uploaded or published through the
  ordinary CLI/non-locked fallback path, always add
  `--lyrics --lyrics-format lrc --require-lrc` to `download_clips.sh`.
- For songs uploaded to Qiaomu Music, invoke `qiaomu-music-publisher` after MP3
  and LRC are ready. Site-specific login/upload logic belongs there.
- If clip IDs are visible in the web list during a non-locked fallback task,
  `download_clips.sh --ids "ID1 ID2" --browser` is the preferred download retry
  because it asks Chrome to fetch the audio through the browser pipeline first.
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

For Suno, convert recommendations into concise style tags. Prefer 1-3 genre tags plus vocal, instrument, tempo, and mood tags. Avoid dumping many related subgenres into one prompt.
For style-only or broad recommendation requests, run multiple focused finder
queries and synthesize from the returned palette before answering.

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

Use it only when the user wants to reuse an existing Chrome login or debug Suno browser state. Chrome must have remote debugging enabled. If CDP is unavailable, fall back to `suno auth --login` or the browser-generation lane. Keep all CDP checks bounded with `--timeout`; a native Chrome debugging confirmation can otherwise stall automation before page scripts run.

To start a CDP-enabled Chrome session:

```bash
bash scripts/launch_suno_cdp_chrome.sh
```

Useful environment knobs:

- `SUNO_CDP_TIMEOUT=12` bounds the pre-generation CDP probe.
- `SUNO_SKIP_CHROME_SESSION_CHECK=1` skips the pre-generation CDP probe when it
  is known to trigger a native Chrome confirmation.
- `SUNO_CDP_PORT=9222` controls the Chrome remote debugging port.

This machine has `liaocaoxuezhe/chrome-devtools-auto-allow` installed at
`/Users/joetech/.local/share/chrome-devtools-auto-allow`. Its LaunchAgent is
`com.local.cdp-auto-allow`, app path is
`/Users/joetech/.local/share/chrome-devtools-auto-allow/CDP Auto Allow.app`, and
logs are written to `/tmp/cdp-auto-allow.debug.log`. If the log says
`不允许辅助访问`, the user must enable the app in macOS Accessibility settings.

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
