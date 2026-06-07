# Chrome CDP Auth Assist

This skill includes `scripts/cdp.mjs` from `pasky/chrome-cdp-skill`.

Purpose:

- Reuse a Chrome profile that is already logged into Suno.
- Open or inspect `https://suno.com/create` through Chrome DevTools Protocol.
- Reduce repeated login prompts caused by detached browser sessions.

Limits:

- CDP does not magically bypass authentication.
- Chrome must expose a DevTools endpoint through remote debugging.
- Chrome's native "Allow debugging" confirmation may appear before page-level
  CDP commands can run. Do not rely on `Browser.setPermission` or injected page
  JavaScript to dismiss that native Chrome UI. Keep CDP probes timed and fall
  back cleanly when the user must accept it once.
- The upstream `suno` CLI still owns generation and token refresh.
- If Suno invalidates a session, the user still needs to log in again.
- The upstream hCaptcha auto-solver may fail independently of login state; prefer `--no-captcha` when auth is already valid.

Recommended flow:

1. Run `scripts/ensure_suno_chrome_session.sh --timeout 12`.
2. If it finds a Suno tab, use that logged-in profile.
3. If no CDP endpoint exists and Chrome is not already running, launch Chrome
   with `scripts/launch_suno_cdp_chrome.sh`.
4. If it opens a new Suno tab, ask the user to log in once.
5. Run `suno auth` or `suno generate` again.

Generation recommendation:

```bash
scripts/generate_with_suno.sh ... --no-captcha
```

Use `--captcha` only when you want the upstream solver, or `--token` when you have an hCaptcha token.

Manual setup hints:

```bash
scripts/launch_suno_cdp_chrome.sh
scripts/ensure_suno_chrome_session.sh --launch --timeout 12
```

If Chrome is already running without remote debugging, macOS usually ignores new
`--remote-debugging-port` flags for that app instance. Fully quit Chrome and
relaunch it with `scripts/launch_suno_cdp_chrome.sh`, or use an isolated profile:

```bash
scripts/launch_suno_cdp_chrome.sh --dedicated-profile
```

Environment knobs:

- `SUNO_CDP_TIMEOUT=12`: seconds each CDP probe may wait.
- `SUNO_SKIP_CHROME_SESSION_CHECK=1`: skip the pre-generation CDP probe when it
  is known to trigger an unavoidable native confirmation.
- `SUNO_CDP_PORT=9222`: CDP port for the launcher.

Installed auto-allow helper on this machine:

- Repo: `/Users/joetech/.local/share/chrome-devtools-auto-allow`
- App: `/Users/joetech/.local/share/chrome-devtools-auto-allow/CDP Auto Allow.app`
- Bundle ID: `com.local.CDPAutoAllow`
- LaunchAgent: `~/Library/LaunchAgents/com.local.cdp-auto-allow.plist`
- Log: `/tmp/cdp-auto-allow.debug.log`

If logs contain `不允许辅助访问` or `not allowed assistive access`, enable the
app in `System Settings > Privacy & Security > Accessibility`. The installer
cannot grant this TCC permission programmatically.

Security:

- CDP can inspect and control tabs.
- Use only for local, user-approved Suno browser state.
- Do not export cookies or tokens into shared logs.
