#!/usr/bin/env python3
"""
Suno Aligned Lyrics Fetcher - 获取精准同步歌词

通过本地 suno-api 代理获取带时间戳的同步歌词，生成 LRC/SRT/MD 格式文件。
无需手动管理 JWT Token，由本地服务器自动处理鉴权。

Usage:
    python fetch_aligned_lyrics.py <song_id>
    python fetch_aligned_lyrics.py <song_id1> <song_id2>
    python fetch_aligned_lyrics.py <song_id> --format lrc
    python fetch_aligned_lyrics.py <song_id> --format srt
    python fetch_aligned_lyrics.py <song_id> --format md
    python fetch_aligned_lyrics.py <song_id> --format all   # 默认：lrc + srt + md
    python fetch_aligned_lyrics.py <song_id> --output ~/Music/lyrics
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 配置
SUNO_API_BASE = os.environ.get("SUNO_API_URL", "http://localhost:3000")
DEFAULT_OUTPUT_DIR = Path(os.environ.get("SUNO_MUSIC_DIR", str(Path.home() / "Music" / "Suno")))


def fetch_aligned_lyrics(song_id: str) -> Optional[Dict]:
    """通过本地 suno-api 代理获取带时间戳的同步歌词"""
    url = f"{SUNO_API_BASE}/api/get_aligned_lyrics?song_id={song_id}"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"⚠️  No aligned lyrics found for {song_id}", file=sys.stderr)
        else:
            error_body = e.read().decode("utf-8")
            print(f"❌ HTTP {e.code}: {error_body}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ Error fetching aligned lyrics: {e}", file=sys.stderr)
        return None


def fetch_song_metadata(song_id: str) -> Optional[Dict]:
    """通过本地 /api/get 获取歌曲元数据（标题、纯文本歌词等）"""
    url = f"{SUNO_API_BASE}/api/get?ids={song_id}"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            # /api/get 返回列表
            if isinstance(data, list) and data:
                return data[0]
            return data
    except Exception as e:
        print(f"⚠️  Could not fetch song metadata: {e}", file=sys.stderr)
        return None


def parse_aligned_lyrics(data) -> Tuple[List[Dict], Optional[float]]:
    """解析 aligned_lyrics 数据，返回 (lines, duration)。

    本地 suno-api 返回词级别的 list：
    [{"word": "花非花，\n", "start_s": 1.2, "end_s": 2.3}, ...]
    每个 word 可能包含换行符和 Suno 结构标签（[Intro], [Verse 1] 等）。
    注意：结构标签可能被拆分到多个相邻 word item，需先合并再过滤。
    """
    import re

    # 兼容 list（本地 API）和 dict（旧格式）
    if isinstance(data, list):
        word_items = data
    elif isinstance(data, dict):
        word_items = data.get("aligned_lyrics", [])
        if not word_items and "data" in data:
            word_items = data["data"].get("aligned_lyrics", [])
    else:
        return [], None

    if not word_items:
        return [], None

    # 提取时长（dict 格式才有）
    duration = None
    if isinstance(data, dict):
        for key in ("duration_s", "duration"):
            val = data.get(key)
            if isinstance(val, (int, float)) and val > 0:
                duration = float(val)
                break

    # Step 1: 合并所有词，建立字符级时间戳映射
    # 结构标签可能被拆分到多个 word item（如 "[Verse" 在一个，" 1]" 在下一个），
    # 合并后再做正则才能正确匹配完整的 [...] 标签。
    joined = ""
    char_ts: List[Tuple[float, float]] = []  # 每个字符对应的 (start_s, end_s)
    for item in word_items:
        raw = item.get("word", "") or item.get("text", "")
        s = float(item.get("start_s") or 0)
        e = float(item.get("end_s") or 0)
        joined += raw
        char_ts.extend([(s, e)] * len(raw))

    # Step 2: 标记所有结构标签字符位置（合并后正则能匹配跨 item 的标签）
    tag_positions: set = set()
    for m in re.finditer(r'\[[^\]]*\]', joined):
        tag_positions.update(range(m.start(), m.end()))

    # Step 3: 逐字符扫描，按 \n 分行，跳过标签字符
    lines = []
    current_chars: List[str] = []
    current_start: Optional[float] = None
    current_end: Optional[float] = None

    for i, ch in enumerate(joined):
        if i in tag_positions:
            continue  # 跳过结构标签字符

        if ch == "\n":
            text = "".join(current_chars).strip()
            if text and current_start is not None and current_end is not None:
                lines.append({"text": text, "start_s": current_start, "end_s": current_end})
            current_chars = []
            current_start = None
            current_end = None
        else:
            ts = char_ts[i]
            if not current_chars:
                current_start = ts[0]
            current_end = ts[1]
            current_chars.append(ch)

    # 处理最后一行（没有尾随换行符时）
    text = "".join(current_chars).strip()
    if text and current_start is not None and current_end is not None:
        lines.append({"text": text, "start_s": current_start, "end_s": current_end})

    return lines, duration


def fmt_lrc_time(seconds: float) -> str:
    """[mm:ss.xx]"""
    m = int(seconds // 60)
    s = int(seconds % 60)
    h = int((seconds % 1) * 100)
    return f"[{m:02d}:{s:02d}.{h:02d}]"


def fmt_srt_time(seconds: float) -> str:
    """hh:mm:ss,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_md_time(seconds: float) -> str:
    """[mm:ss] 简洁格式，方便 AI 读取"""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"[{m:02d}:{s:02d}]"


def generate_lrc(lines: List[Dict], title: str = "") -> str:
    parts = []
    if title:
        parts.append(f"[ti:{title}]")
    parts.append("[by:Suno AI]")
    parts.append("")
    for line in lines:
        parts.append(f"{fmt_lrc_time(line['start_s'])}{line['text']}")
    return "\n".join(parts)


def generate_srt(lines: List[Dict]) -> str:
    parts = []
    for i, line in enumerate(lines, 1):
        parts.append(str(i))
        parts.append(f"{fmt_srt_time(line['start_s'])} --> {fmt_srt_time(line['end_s'])}")
        parts.append(line["text"])
        parts.append("")
    return "\n".join(parts)


def generate_md(lines: List[Dict], title: str = "", song_id: str = "") -> str:
    """生成 Markdown 格式带时间戳歌词，方便 AI 读取"""
    parts = []
    if title:
        parts.append(f"# {title}")
        parts.append("")
    if song_id:
        parts.append(f"**Song ID**: `{song_id}`")
        parts.append("")
    parts.append("## 带时间戳歌词")
    parts.append("")
    parts.append("| 时间 | 结束 | 歌词 |")
    parts.append("|------|------|------|")
    for line in lines:
        start = fmt_md_time(line["start_s"])
        end = fmt_md_time(line["end_s"])
        text = line["text"].replace("|", "\\|")
        parts.append(f"| {start} | {end} | {text} |")
    parts.append("")
    parts.append("## 纯文本歌词（无时间戳）")
    parts.append("")
    for line in lines:
        parts.append(line["text"])
    return "\n".join(parts)


def save_lyrics(song_id: str, lines: List[Dict], output_dir: Path,
                format_type: str = "all", title: str = "", name: str = "") -> List[str]:
    """保存歌词文件，返回保存的文件路径列表"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 优先使用显式传入的 name（对应 MP3 文件名词干），其次从 title 生成
    if name:
        base_name = name
    else:
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
        base_name = safe_title if safe_title else song_id[:8]

    saved = []

    if format_type in ("lrc", "all", "both"):
        path = output_dir / f"{base_name}.lrc"
        path.write_text(generate_lrc(lines, title=title), encoding="utf-8")
        saved.append(str(path))
        print(f"✅ LRC saved: {path}")

    if format_type in ("srt", "all", "both"):
        path = output_dir / f"{base_name}.srt"
        path.write_text(generate_srt(lines), encoding="utf-8")
        saved.append(str(path))
        print(f"✅ SRT saved: {path}")

    if format_type in ("md", "all"):
        path = output_dir / f"{base_name}.lyrics.md"
        path.write_text(generate_md(lines, title=title, song_id=song_id), encoding="utf-8")
        saved.append(str(path))
        print(f"✅ MD  saved: {path}")

    return saved


def process_song(song_id: str, output_dir: Path, format_type: str = "all", name: str = "") -> bool:
    print(f"\n🎵 Processing song: {song_id}")

    # 1. 获取精准时间戳歌词
    print("📡 Fetching aligned lyrics via local API...")
    lyrics_data = fetch_aligned_lyrics(song_id)

    if not lyrics_data:
        # 降级：通过本地 /api/get 获取纯文本歌词
        print("⚠️  No aligned lyrics, falling back to plain lyrics...")
        meta = fetch_song_metadata(song_id)
        if meta:
            title = meta.get("title", song_id[:8])
            prompt = meta.get("metadata", {}).get("prompt", "") or meta.get("lyric", "")
            if prompt:
                base = name if name else "".join(c for c in title if c.isalnum() or c in " -_").strip()
                txt_path = output_dir / f"{base}.txt"
                txt_path.write_text(prompt, encoding="utf-8")
                print(f"📝 Plain lyrics saved: {txt_path}")
                return True
        print("❌ No lyrics found", file=sys.stderr)
        return False

    # 2. 解析
    lines, duration = parse_aligned_lyrics(lyrics_data)
    if not lines:
        print("⚠️  No valid lyrics lines found", file=sys.stderr)
        return False

    print(f"✅ Found {len(lines)} lines with timestamps")
    if duration:
        print(f"⏱️  Duration: {duration:.2f}s")

    # 3. 获取歌曲标题（用于 MD header，不影响文件名）
    meta = fetch_song_metadata(song_id)
    title = meta.get("title", song_id[:8]) if meta else song_id[:8]

    # 4. 保存（name 优先用于文件名）
    saved = save_lyrics(song_id, lines, output_dir, format_type, title, name=name)
    return len(saved) > 0


def main():
    parser = argparse.ArgumentParser(description="Fetch aligned lyrics from Suno (via local API proxy)")
    parser.add_argument("song_ids", nargs="+", help="Song ID(s)")
    parser.add_argument(
        "--format", "-f",
        choices=["lrc", "srt", "md", "all", "both"],
        default="all",
        help="Output format: lrc / srt / md / all (default: all = lrc+srt+md)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--name", "-n",
        default="",
        help="Base filename (without extension), overrides title-derived name. Used to match MP3 filename."
    )

    args = parser.parse_args()

    success = 0
    for song_id in args.song_ids:
        if process_song(song_id, args.output, args.format, name=args.name):
            success += 1

    print(f"\n{'='*50}")
    print(f"✅ Processed {success}/{len(args.song_ids)} song(s)")
    print(f"📁 Output: {args.output}")


if __name__ == "__main__":
    main()
