#!/usr/bin/env python3
"""Clean Suno SRT files by removing structural markers for MTV subtitles."""

from __future__ import annotations

import re
import sys
from pathlib import Path


TAG_RE = re.compile(r"^\s*\[[^\]]+\]\s*$")


def is_suno_tag(text: str) -> bool:
    return not text.strip() or bool(TAG_RE.match(text.strip()))


def clean_srt(input_file: Path, output_file: Path | None = None) -> bool:
    if not input_file.exists():
        print(f"File not found: {input_file}", file=sys.stderr)
        return False
    if output_file is None:
        output_file = input_file.with_suffix(".clean.srt")

    blocks = input_file.read_text(encoding="utf-8").strip().split("\n\n")
    cleaned_blocks: list[str] = []
    new_index = 1

    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        time_line = lines[1]
        text_lines = [line for line in lines[2:] if not is_suno_tag(line)]
        if not text_lines:
            continue
        cleaned_blocks.append(f"{new_index}\n{time_line}\n" + "\n".join(text_lines))
        new_index += 1

    output_file.write_text("\n\n".join(cleaned_blocks) + "\n", encoding="utf-8")
    print(f"Cleaned SRT saved: {output_file}")
    print(f"Original blocks: {len(blocks)}")
    print(f"Cleaned blocks: {len(cleaned_blocks)}")
    return True


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: clean_srt_for_mtv.py <input.srt> [output.srt]", file=sys.stderr)
        raise SystemExit(2)
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    raise SystemExit(0 if clean_srt(input_file, output_file) else 1)


if __name__ == "__main__":
    main()
