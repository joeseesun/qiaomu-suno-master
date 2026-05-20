# qiaomu-suno-master

> 把一句想法变成 Suno 可唱歌词、风格提示词，并直接生成下载歌曲。
> Turn a rough song idea into Suno-ready lyrics, style prompts, and downloaded music.

![GitHub License](https://img.shields.io/github/license/joeseesun/qiaomu-suno-master)
![GitHub last commit](https://img.shields.io/github/last-commit/joeseesun/qiaomu-suno-master)

**[中文](#中文) | [English](#english)**

---

<a name="中文"></a>
## 中文

你想让 AI 写歌，最麻烦的通常不是一句歌词，而是整套可用于 Suno 的结构：Hook、段落标记、风格标签、排除风格、登录态、下载路径。

`qiaomu-suno-master` 把这些揉成一个 Agent Skill：先按专业歌曲结构写歌词，再调用本地 Rust `suno` CLI 生成并下载音乐。

### 你会得到什么

- Suno-ready 歌词：`[Verse]`、`[Chorus]`、`[Bridge]`、`[Hook]` 等结构完整
- Style Description：例如 `punk-rock, male-vocals, distorted-guitars, fast-tempo`
- Exclude Styles：避免不想要的风格，例如 `auto-tune, trap, overly-polished`
- 三个歌名候选
- 可选：直接生成并下载 MP3
- 从已有 Suno Clip ID 导出 MP3、视频/MTV、LRC、SRT、干净字幕、Markdown 歌词
- Chrome CDP 辅助：复用已登录 Chrome/Suno 会话

### 安装

```bash
npx skills add joeseesun/qiaomu-suno-master
```

验证：

```bash
ls ~/.agents/skills/qiaomu-suno-master
```

### 前置条件

- [ ] 已安装 Rust `suno` CLI，或允许 skill 自动安装

  ```bash
  cargo install suno --locked
  suno --version
  ```

- [ ] 已登录 Suno

  ```bash
  suno auth --login
  suno auth
  ```

- [ ] 如果要复用 Chrome 登录态，Chrome 已开启远程调试

  打开：

  ```text
  chrome://inspect/#remote-debugging
  ```

  勾选 `Allow remote debugging for this browser instance`。

### 自然语言用法

```text
用 qiaomu-suno-master 写一首朋克歌，主题是把音量打满
```

```text
把这篇文章改成一首中文民谣，并生成 Suno 歌曲
```

```text
生成一首世界音乐，女声男声合唱，鼓和长笛，下载到当前项目
```

### CLI 生成

Skill 内置封装脚本：

```bash
~/.agents/skills/qiaomu-suno-master/scripts/generate_with_suno.sh \
  --title "把音量打满" \
  --tags "punk-rock, male-vocals, distorted-guitars, fast-tempo" \
  --exclude "auto-tune, trap, overly-polished" \
  --lyrics-file ./lyrics.txt
```

默认输出到：

```text
~/Documents/Suno/<歌曲名>/
```

默认会加 `--no-captcha`，因为上游 `suno` CLI 的 hCaptcha CDP auto-solver 在某些 Chrome 会话下可能报：

```text
CDP Runtime.evaluate ws err: Connection reset...
```

如果你确实需要使用上游 captcha solver：

```bash
~/.agents/skills/qiaomu-suno-master/scripts/generate_with_suno.sh ... --captcha
```

或传入 token：

```bash
~/.agents/skills/qiaomu-suno-master/scripts/generate_with_suno.sh ... --token "$HCAPTCHA_TOKEN"
```

### 导出 SRT/LRC/MTV 素材

如果你已经有 Suno clip ID，可以直接导出字幕和素材：

```bash
~/.agents/skills/qiaomu-suno-master/scripts/export_suno_assets.py \
  <clip-id> \
  --format lyrics \
  --clean-srt
```

导出音频 + 视频/MTV + 全部歌词格式：

```bash
~/.agents/skills/qiaomu-suno-master/scripts/export_suno_assets.py \
  <clip-id> \
  --format all \
  --clean-srt
```

默认会按歌曲标题创建目录：

```text
~/Documents/Suno/<歌曲名>/
```

格式说明：

- `audio`：下载音频
- `video`：下载 Suno 视频/MTV 文件（如果该 clip 可用）
- `json`：保存 timed lyrics 原始 JSON
- `lrc`：音乐播放器歌词
- `srt`：字幕文件
- `md`：带时间戳 Markdown 歌词，方便 AI/剪辑流程读取
- `lyrics`：等于 `json,lrc,srt,md`
- `all`：等于 `audio,video,json,lrc,srt,md`

清理已有 SRT：

```bash
~/.agents/skills/qiaomu-suno-master/scripts/clean_srt_for_mtv.py input.srt
```

### Troubleshooting

| 问题 | 解决 |
|---|---|
| `suno: command not found` | 运行 `cargo install suno --locked`，或执行 `scripts/ensure_suno_cli.sh` |
| `JWT expired` | 运行 `suno auth` 或 `suno auth --login` |
| `CDP Runtime.evaluate ws err` | 用默认封装脚本重试，或显式加 `--no-captcha` |
| Chrome 反复弹调试确认 | 复用同一个 Suno 标签页，避免反复新开 tab；Chrome CDP 权限很高，这是安全确认 |
| 找不到 Suno 标签页 | 运行 `scripts/ensure_suno_chrome_session.sh` |
| 需要 SRT/MTV | 用 `scripts/export_suno_assets.py <clip-id> --format all --clean-srt` |

### 致谢

- [`paperfoot/suno-cli`](https://github.com/paperfoot/suno-cli)：本 skill 使用的 Rust Suno CLI
- [`pasky/chrome-cdp-skill`](https://github.com/pasky/chrome-cdp-skill)：本 skill vendored 的轻量 CDP helper
- [`joeseesun/suno-music-creator`](https://github.com/joeseesun/suno-music-creator)：歌词创作提示词来源之一

### 风险和限制

- 生成音乐会消耗 Suno 账号额度。
- Chrome CDP 可以控制本地浏览器标签页，只在可信本机环境使用。
- Suno API 和网页流程可能变化；如失败，先运行 `suno update --check` 和 `suno update`。
- 视频/MTV 下载取决于 Suno 是否为该 clip 提供 video asset。

---

<a name="english"></a>
## English

`qiaomu-suno-master` is an Agent Skill for turning a song brief into Suno-ready lyrics, style prompts, exclude tags, and generated audio through the local Rust `suno` CLI.

### Install

```bash
npx skills add joeseesun/qiaomu-suno-master
```

### Requirements

- [ ] Install the upstream `suno` CLI:

  ```bash
  cargo install suno --locked
  suno --version
  ```

- [ ] Authenticate Suno:

  ```bash
  suno auth --login
  suno auth
  ```

- [ ] Optional Chrome CDP login reuse:

  Open `chrome://inspect/#remote-debugging` and enable `Allow remote debugging for this browser instance`.

### Example Prompts

```text
Use qiaomu-suno-master to write a punk song about turning the volume all the way up.
```

```text
Turn this article into a Chinese folk song and generate it with Suno.
```

```text
Generate a world music track with duet vocals, hand drums, flute, and cinematic energy.
```

### CLI Wrapper

```bash
~/.agents/skills/qiaomu-suno-master/scripts/generate_with_suno.sh \
  --title "Turn It Up" \
  --tags "punk-rock, male-vocals, distorted-guitars, fast-tempo" \
  --exclude "auto-tune, trap, overly-polished" \
  --lyrics-file ./lyrics.txt
```

The wrapper defaults to `--no-captcha` because the upstream CDP hCaptcha solver can be flaky in some Chrome sessions.

Default output:

```text
~/Documents/Suno/<song-title>/
```

### Export Assets

```bash
~/.agents/skills/qiaomu-suno-master/scripts/export_suno_assets.py \
  <clip-id> \
  --format all \
  --clean-srt
```

This can export audio, video/MTV assets, timed lyrics JSON, LRC, SRT, clean SRT, and Markdown lyrics.
Without `--output`, exported files are saved to `~/Documents/Suno/<clip-title>/`.

### Credits

- [`paperfoot/suno-cli`](https://github.com/paperfoot/suno-cli)
- [`pasky/chrome-cdp-skill`](https://github.com/pasky/chrome-cdp-skill)
- [`joeseesun/suno-music-creator`](https://github.com/joeseesun/suno-music-creator)
