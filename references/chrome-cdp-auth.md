# Chrome CDP Auth Assist

This skill includes `scripts/cdp.mjs` from `pasky/chrome-cdp-skill`.

Purpose:

- Reuse a Chrome profile that is already logged into Suno.
- Open or inspect `https://suno.com/create` through Chrome DevTools Protocol.
- Reduce repeated login prompts caused by detached browser sessions.

Limits:

- CDP does not magically bypass authentication.
- Chrome must expose a DevTools endpoint through remote debugging.
- The upstream `suno` CLI still owns generation and token refresh.
- If Suno invalidates a session, the user still needs to log in again.
- The upstream hCaptcha auto-solver may fail independently of login state; prefer `--no-captcha` when auth is already valid.

Recommended flow:

1. Run `scripts/ensure_suno_chrome_session.sh`.
2. If it finds a Suno tab, use that logged-in profile.
3. If it opens a new Suno tab, ask the user to log in once.
4. Run `suno auth` or `suno generate` again.

Generation recommendation:

```bash
scripts/generate_with_suno.sh ... --no-captcha
```

Use `--captcha` only when you want the upstream solver, or `--token` when you have an hCaptcha token.

Manual setup hints:

```bash
open -a "Google Chrome" --args --remote-debugging-port=9222
```

If Chrome is already running without remote debugging, fully quit Chrome and relaunch it with the flag above, or enable remote debugging in `chrome://inspect/#remote-debugging` when the browser supports it.

Security:

- CDP can inspect and control tabs.
- Use only for local, user-approved Suno browser state.
- Do not export cookies or tokens into shared logs.
