---
name: qiaomu-suno-master
description: |
  Turn a song idea, story, article, theme, or lyrics request into polished Suno-ready lyrics, style tags, and generated music through the local Rust suno CLI. Trigger for 写一首歌, 创作歌曲, 生成音乐, Suno 生成, /suno, /music, or requests to create lyrics and render them through Suno.
---

# Qiaomu Suno Master

Create commercial-grade Suno lyrics, then use the installed `suno` command to generate and optionally download the music.
It also includes a local music genre finder so vague moods can become precise Suno style tags.

## When To Use

Use this skill when the user wants:

- A new song from a theme, article, story, mood, or keywords
- Suno-ready lyrics with sections such as `[Verse]`, `[Chorus]`, and `[Bridge]`
- Music generated through the local Rust `suno` CLI
- A completed song file downloaded locally
- Existing Suno clip IDs exported as audio, video/MTV, timed LRC, SRT, clean SRT, or Markdown lyrics
- Music genre/style recommendations before lyric writing or generation

Do not use this skill for pure music theory, ordinary poetry not intended for Suno, or non-Suno audio editing.

## Inputs To Resolve

Infer these from the user request when possible:

- `title`: short, memorable song title
- `lyrics`: complete Suno-ready lyrics with structural tags
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
6. Save lyrics to a temporary `.txt` file when running the CLI. Prefer a file over shell-quoting long multiline lyrics.
7. Before any CLI generation, download, auth, status, or export step, ensure the Rust CLI exists:

```bash
bash scripts/ensure_suno_cli.sh
```

8. Generate with:

```bash
bash scripts/generate_with_suno.sh --meta-file "$META_FILE" --output-dir "$OUTPUT_DIR"
```

9. Report the saved output directory and any generated clip IDs or file paths shown by the command.

Never save generated songs, subtitles, videos, or exported lyric files inside the skill directory. Use `~/Documents/Suno/<song-title>/` by default.

## CLI Notes

- The upstream CLI is `paperfoot/suno-cli`, installed as the `suno` command.
- If `suno` is missing, run `bash scripts/ensure_suno_cli.sh` before continuing. The script installs from the upstream project, tries Homebrew first, and falls back to Cargo if Homebrew fails.
- Verify with `suno --version` after install.
- For friends who already stay logged into Suno in Chrome, use `scripts/ensure_suno_chrome_session.sh` to connect through Chrome CDP and reuse the existing browser session where possible.
- Run `suno auth --login` if authentication is missing or expired.
- Prefer `bash scripts/generate_with_suno.sh` for generation. It checks for `suno` and bootstraps it when missing. It defaults to `--no-captcha` because the upstream CDP hCaptcha auto-solver can fail with `CDP Runtime.evaluate ws err` even when auth is valid.
- If Suno explicitly requires captcha, provide `--token <hCaptcha-token>` or opt back into the built-in solver with `--captcha`.
- Use `--download <dir>` on `suno generate` when the user wants files saved immediately.
- Use `suno download -o <dir> <id...>` only when the user already has clip IDs or generation was submitted without download.
- Use `scripts/export_suno_assets.py` when the user wants SRT/LRC/timed lyrics, clean MTV subtitles, audio download, or video/MTV download from existing clip IDs.
- Use `scripts/clean_srt_for_mtv.py` to remove Suno structural markers such as `[Verse]` and `[Chorus]` from subtitle files.
- Add `--json` when machine-readable output is needed for follow-up processing.

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

For MTV:

```bash
python3 scripts/export_suno_assets.py <clip-id> --output "$OUTPUT_DIR" --format video,lyrics --clean-srt
```

## Chrome CDP Auth Assist

This skill vendors a lightweight Chrome DevTools Protocol helper from `pasky/chrome-cdp-skill` as `scripts/cdp.mjs`.

Use it only when the user wants to reuse an existing Chrome login or debug Suno browser state. Chrome must have remote debugging enabled. If CDP is unavailable, fall back to `suno auth --login`.

Known issue: the upstream `suno` CLI captcha auto-solver may open a piloted Chrome and fail with `CDP Runtime.evaluate ws err: Connection reset...`. When auth is already OK, retry generation with `--no-captcha`; this is the wrapper default.

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
