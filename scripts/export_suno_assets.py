#!/usr/bin/env python3
"""Export Suno lyrics/subtitles/video assets using the Rust `suno` CLI."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


TAG_RE = re.compile(r"^\s*\[[^\]]+\]\s*$")
DEFAULT_ROOT = Path.home() / "Documents" / "Suno"


def run(cmd: list[str], quiet: bool = False) -> subprocess.CompletedProcess[str]:
    if not quiet:
        print("$ " + " ".join(cmd), file=sys.stderr)
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def safe_name(value: str) -> str:
    cleaned = "".join(c for c in value if c.isalnum() or c in " -_").strip()
    return cleaned or "suno-asset"


def song_dir_name(value: str) -> str:
    cleaned = value.replace("/", "-").replace(":", "-")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "Untitled Suno Song"


def srt_time(seconds: float) -> str:
    ms_total = max(0, int(round(seconds * 1000)))
    h, rem = divmod(ms_total, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def lrc_time(seconds: float) -> str:
    cs_total = max(0, int(round(seconds * 100)))
    m, rem = divmod(cs_total, 6000)
    s, cs = divmod(rem, 100)
    return f"[{m:02d}:{s:02d}.{cs:02d}]"


def md_time(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    m, s = divmod(total, 60)
    return f"{m:02d}:{s:02d}"


def is_tag(text: str) -> bool:
    return not text.strip() or bool(TAG_RE.match(text))


def extract_title(info: dict[str, Any], clip_id: str) -> str:
    data = info.get("data", info)
    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, dict):
        return str(data.get("title") or data.get("name") or clip_id[:8])
    return clip_id[:8]


def parse_words(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", payload)
    if isinstance(data, dict):
        for key in ("aligned_lyrics", "lyrics", "words", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    if isinstance(data, list):
        return data
    return []


def word_text(item: dict[str, Any]) -> str:
    return str(item.get("word") or item.get("text") or item.get("lyric") or "")


def word_start(item: dict[str, Any]) -> float:
    value = item.get("start_s", item.get("start", item.get("startTime", 0)))
    try:
        return float(value)
    except Exception:
        return 0.0


def word_end(item: dict[str, Any]) -> float:
    value = item.get("end_s", item.get("end", item.get("endTime", word_start(item))))
    try:
        return float(value)
    except Exception:
        return word_start(item)


def words_to_lines(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    joined = ""
    char_ts: list[tuple[float, float]] = []
    for item in words:
        raw = word_text(item)
        start = word_start(item)
        end = word_end(item)
        joined += raw
        char_ts.extend([(start, end)] * len(raw))

    tag_positions: set[int] = set()
    for match in re.finditer(r"\[[^\]]*\]", joined):
        tag_positions.update(range(match.start(), match.end()))

    lines: list[dict[str, Any]] = []
    chars: list[str] = []
    start_s: float | None = None
    end_s: float | None = None

    def flush() -> None:
        nonlocal chars, start_s, end_s
        text = "".join(chars).strip()
        if text and start_s is not None and end_s is not None and not is_tag(text):
            lines.append({"text": text, "start_s": start_s, "end_s": end_s})
        chars = []
        start_s = None
        end_s = None

    for i, ch in enumerate(joined):
        if i in tag_positions:
            continue
        if ch == "\n":
            flush()
            continue
        if not chars:
            start_s = char_ts[i][0] if i < len(char_ts) else 0.0
        end_s = char_ts[i][1] if i < len(char_ts) else (start_s or 0.0)
        chars.append(ch)
    flush()
    return lines


def generate_lrc(lines: list[dict[str, Any]], title: str) -> str:
    output = [f"[ti:{title}]", "[by:Suno AI]", ""]
    output.extend(f"{lrc_time(line['start_s'])}{line['text']}" for line in lines)
    return "\n".join(output) + "\n"


def generate_srt(lines: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for index, line in enumerate(lines, 1):
        chunks.append(str(index))
        chunks.append(f"{srt_time(line['start_s'])} --> {srt_time(line['end_s'])}")
        chunks.append(str(line["text"]))
        chunks.append("")
    return "\n".join(chunks)


def generate_md(lines: list[dict[str, Any]], title: str, clip_id: str) -> str:
    output = [
        f"# {title}",
        "",
        f"**Clip ID**: `{clip_id}`",
        "",
        "| Start | End | Lyric |",
        "|---|---|---|",
    ]
    for line in lines:
        text = str(line["text"]).replace("|", "\\|")
        output.append(f"| {md_time(line['start_s'])} | {md_time(line['end_s'])} | {text} |")
    output.append("")
    output.append("## Plain Lyrics")
    output.append("")
    output.extend(str(line["text"]) for line in lines)
    return "\n".join(output) + "\n"


def clean_srt(input_path: Path, output_path: Path) -> None:
    blocks = input_path.read_text(encoding="utf-8").strip().split("\n\n")
    cleaned: list[str] = []
    index = 1
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        time_line = lines[1]
        text_lines = [line for line in lines[2:] if not is_tag(line)]
        if not text_lines:
            continue
        cleaned.append(f"{index}\n{time_line}\n" + "\n".join(text_lines))
        index += 1
    output_path.write_text("\n\n".join(cleaned) + "\n", encoding="utf-8")


def export_one(clip_id: str, output_dir: Path | None, formats: set[str], clean: bool) -> list[Path]:
    info_proc = run(["suno", "info", "--json", clip_id], quiet=True)
    info: dict[str, Any] = {}
    if info_proc.returncode == 0:
        try:
            info = json.loads(info_proc.stdout)
        except json.JSONDecodeError:
            info = {}
    title = extract_title(info, clip_id)
    if output_dir is None:
        output_dir = DEFAULT_ROOT / song_dir_name(title)
    output_dir.mkdir(parents=True, exist_ok=True)

    base = safe_name(f"{title}-{clip_id[:8]}")

    saved: list[Path] = []

    if "audio" in formats:
        proc = run(["suno", "download", "-o", str(output_dir), clip_id])
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, file=sys.stderr, end="")

    if "video" in formats:
        proc = run(["suno", "download", "--video", "-o", str(output_dir), clip_id])
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, file=sys.stderr, end="")

    if formats.intersection({"json", "lrc", "srt", "md"}):
        proc = run(["suno", "timed-lyrics", "--json", clip_id])
        if proc.returncode != 0:
            print(proc.stdout, end="")
            print(proc.stderr, file=sys.stderr, end="")
            raise SystemExit(proc.returncode)
        payload = json.loads(proc.stdout)
        json_path = output_dir / f"{base}.timed-lyrics.json"
        if "json" in formats:
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            saved.append(json_path)

        lines = words_to_lines(parse_words(payload))
        if not lines:
            print(f"No timestamped lyric lines found for {clip_id}", file=sys.stderr)
        else:
            if "lrc" in formats:
                path = output_dir / f"{base}.lrc"
                path.write_text(generate_lrc(lines, title), encoding="utf-8")
                saved.append(path)
            if "srt" in formats:
                path = output_dir / f"{base}.srt"
                path.write_text(generate_srt(lines), encoding="utf-8")
                saved.append(path)
                if clean:
                    clean_path = output_dir / f"{base}.clean.srt"
                    clean_srt(path, clean_path)
                    saved.append(clean_path)
            if "md" in formats:
                path = output_dir / f"{base}.lyrics.md"
                path.write_text(generate_md(lines, title, clip_id), encoding="utf-8")
                saved.append(path)

    for path in saved:
        print(f"Saved: {path}")
    return saved


def expand_formats(values: list[str]) -> set[str]:
    result: set[str] = set()
    for value in values:
        for part in value.split(","):
            part = part.strip().lower()
            if part == "all":
                result.update({"audio", "video", "json", "lrc", "srt", "md"})
            elif part == "lyrics":
                result.update({"json", "lrc", "srt", "md"})
            elif part:
                result.add(part)
    allowed = {"audio", "video", "json", "lrc", "srt", "md"}
    unknown = result - allowed
    if unknown:
        raise SystemExit(f"Unknown format(s): {', '.join(sorted(unknown))}")
    return result or {"audio", "json", "lrc", "srt", "md"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Suno audio/video/timed lyric assets")
    parser.add_argument("clip_ids", nargs="+", help="Suno clip IDs")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output directory (default: ~/Documents/Suno/<clip-title>)",
    )
    parser.add_argument(
        "--format",
        "-f",
        action="append",
        default=[],
        help="audio, video, json, lrc, srt, md, lyrics, all. Can be comma-separated.",
    )
    parser.add_argument("--clean-srt", action="store_true", help="Also create .clean.srt for MTV subtitles")
    args = parser.parse_args()

    formats = expand_formats(args.format)
    for clip_id in args.clip_ids:
        export_one(clip_id, args.output, formats, args.clean_srt)


if __name__ == "__main__":
    main()
