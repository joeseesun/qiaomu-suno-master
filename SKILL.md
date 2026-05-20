---
name: qiaomu-suno-master
description: |
  Turn a song idea, story, article, theme, or lyrics request into polished Suno-ready lyrics, style tags, and generated music through the local Rust suno CLI. Trigger for 写一首歌, 创作歌曲, 生成音乐, Suno 生成, /suno, /music, or requests to create lyrics and render them through Suno.
---

# Qiaomu Suno Master

Create commercial-grade Suno lyrics, then use the installed `suno` command to generate and optionally download the music.

## When To Use

Use this skill when the user wants:

- A new song from a theme, article, story, mood, or keywords
- Suno-ready lyrics with sections such as `[Verse]`, `[Chorus]`, and `[Bridge]`
- Music generated through the local Rust `suno` CLI
- A completed song file downloaded locally

Do not use this skill for pure music theory, ordinary poetry not intended for Suno, or non-Suno audio editing.

## Inputs To Resolve

Infer these from the user request when possible:

- `title`: short, memorable song title
- `lyrics`: complete Suno-ready lyrics with structural tags
- `style_description`: comma-separated Suno style tags
- `exclude_styles`: comma-separated styles, instruments, or moods to avoid
- `title_options`: three concise title candidates before choosing the final title
- `model`: default `v5.5`
- `vocal`: optional `male` or `female`
- `output_dir`: default to the current workspace unless the user gives a folder
- `generate`: whether to run Suno immediately; default yes when the user asks to generate music

If the user only asks for lyrics, produce the requested creative output without running `suno`.

## Workflow

1. Analyze the song brief: theme, audience, language, mood, style, vocal, tempo, and any forbidden elements.
2. Read `references/lyric-craft.md` and apply the lyric quality rules.
3. Produce:
   - `title_options`
   - selected `title`
   - `style_description`
   - `exclude_styles`
   - `lyrics`
4. Save lyrics to a temporary `.txt` file when running the CLI. Prefer a file over shell-quoting long multiline lyrics.
5. Generate with:

```bash
suno generate --title "$TITLE" --tags "$STYLE_DESCRIPTION" --exclude "$EXCLUDE_STYLES" --lyrics-file "$LYRICS_FILE" --model v5.5 --wait --download "$OUTPUT_DIR"
```

6. Report the saved output directory and any generated clip IDs or file paths shown by the command.

## CLI Notes

- The upstream CLI is `paperfoot/suno-cli`, installed as the `suno` command.
- If `suno` is missing, use `scripts/ensure_suno_cli.sh` to install it from the upstream project via Homebrew or Cargo.
- Verify with `suno --version` after install.
- For friends who already stay logged into Suno in Chrome, use `scripts/ensure_suno_chrome_session.sh` to connect through Chrome CDP and reuse the existing browser session where possible.
- Run `suno auth --login` if authentication is missing or expired.
- Prefer `scripts/generate_with_suno.sh` for generation. It defaults to `--no-captcha` because the upstream CDP hCaptcha auto-solver can fail with `CDP Runtime.evaluate ws err` even when auth is valid.
- If Suno explicitly requires captcha, provide `--token <hCaptcha-token>` or opt back into the built-in solver with `--captcha`.
- Use `--download <dir>` on `suno generate` when the user wants files saved immediately.
- Use `suno download -o <dir> <id...>` only when the user already has clip IDs or generation was submitted without download.
- Add `--json` when machine-readable output is needed for follow-up processing.

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
