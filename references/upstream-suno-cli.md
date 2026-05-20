# Upstream Suno CLI

This skill uses the upstream `paperfoot/suno-cli` project.

- Repository: `https://github.com/paperfoot/suno-cli`
- Installed executable: `suno`
- Crate: `suno`
- Current command family: `generate`, `describe`, `lyrics`, `download`, `auth`, `credits`, `models`, `update`

## Install

Homebrew:

```bash
brew tap paperfoot/tap
brew install suno
```

Cargo:

```bash
cargo install suno --locked
```

Prebuilt binaries:

```text
https://github.com/paperfoot/suno-cli/releases
```

Bootstrap from this skill:

```bash
scripts/ensure_suno_cli.sh
```

Disable auto-install:

```bash
SUNO_CLI_AUTO_INSTALL=0 scripts/generate_with_suno.sh ...
```

## Important Flags

```bash
suno generate \
  --title "$TITLE" \
  --tags "$STYLE_DESCRIPTION" \
  --exclude "$EXCLUDE_STYLES" \
  --lyrics-file "$LYRICS_FILE" \
  --vocal male \
  --weirdness 40 \
  --style-influence 65 \
  --wait \
  --download "$OUTPUT_DIR" \
  --no-captcha
```

Use `suno auth --login` for browser-cookie authentication.

Use `suno update --check` and `suno update` when Suno changes APIs or the installed CLI falls behind.

## Asset Commands

Download audio:

```bash
suno download -o "$OUTPUT_DIR" "$CLIP_ID"
```

Download Suno video/MTV asset when available:

```bash
suno download --video -o "$OUTPUT_DIR" "$CLIP_ID"
```

Get word-level timed lyrics:

```bash
suno timed-lyrics --json "$CLIP_ID"
suno timed-lyrics --lrc "$CLIP_ID"
```

Skill wrapper for all assets:

```bash
scripts/export_suno_assets.py "$CLIP_ID" --format all --clean-srt
```

Without an explicit `--output`, wrapper scripts save generated and exported files under `~/Documents/Suno/<song-title>/`.

## Captcha/CDP Notes

Observed behavior on Chrome 148:

- `suno auth` can refresh JWT successfully from Chrome cookies.
- `suno generate` may still launch its built-in hCaptcha CDP solver.
- The solver can fail with `CDP Runtime.evaluate ws err: Connection reset...`.
- Direct generation with `--no-captcha` can submit successfully when the account/session does not require captcha.

Therefore `scripts/generate_with_suno.sh` defaults to `--no-captcha`.

Override choices:

```bash
# Use upstream built-in solver
SUNO_USE_CAPTCHA_SOLVER=1 scripts/generate_with_suno.sh ...

# Or pass it explicitly
scripts/generate_with_suno.sh ... --captcha

# Or provide a solved token
scripts/generate_with_suno.sh ... --token "$HCAPTCHA_TOKEN"
```

## Chrome CDP Login Reuse

The skill also vendors `pasky/chrome-cdp-skill` as `scripts/cdp.mjs` so an agent can inspect or reuse an already logged-in Chrome session.

Why this helps:

- `suno` may open or inspect Chrome to refresh browser cookies/JWT.
- A persistent Chrome session with remote debugging can avoid separate throwaway browser sessions.
- It lets the agent check whether `https://suno.com/create` is already logged in before asking the user to log in again.

Prerequisites:

- Chrome or Chromium with remote debugging enabled.
- Node.js 22+ for the CDP helper.
- On Chrome, open `chrome://inspect/#remote-debugging` and enable remote debugging if available.

Helper:

```bash
scripts/ensure_suno_chrome_session.sh
```

Manual CDP commands:

```bash
scripts/cdp.mjs list
scripts/cdp.mjs open https://suno.com/create
scripts/cdp.mjs snap <target-prefix>
```

Security note: CDP controls the browser session. Use it only on the user's local machine and only for the Suno session task.
