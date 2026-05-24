#!/usr/bin/env python3
"""Validate that downloaded Suno lyrics are real timestamped LRC files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TIMESTAMP_RE = re.compile(r"\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]")
STRUCTURAL_RE = re.compile(r"^\[(verse|chorus|bridge|intro|outro|hook|pre-chorus|post-chorus|refrain|interlude)", re.I)


def validate_lrc(path: Path, min_timed_lines: int) -> tuple[bool, str]:
    if not path.exists():
        return False, f"{path}: file does not exist"
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False, f"{path}: empty file"

    timed_lines = []
    structural_only = 0
    for line in lines:
        if TIMESTAMP_RE.search(line):
            timed_lines.append(line)
        elif STRUCTURAL_RE.search(line):
            structural_only += 1

    if len(timed_lines) < min_timed_lines:
        return False, (
            f"{path}: only {len(timed_lines)} timestamped lines; "
            f"need at least {min_timed_lines}. This looks like plain lyrics, not LRC."
        )

    if structural_only and structural_only >= len(lines) / 2:
        return False, f"{path}: mostly structural markers; likely not usable music-player LRC"

    previous = -1.0
    for line in timed_lines:
        match = TIMESTAMP_RE.search(line)
        if not match:
            continue
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        if seconds > 59:
            return False, f"{path}: invalid seconds in timestamp {match.group(0)}"
        fraction = match.group(3) or "0"
        value = minutes * 60 + seconds + float(f"0.{fraction[:3]}")
        if value + 0.001 < previous:
            return False, f"{path}: timestamps are not monotonic near {match.group(0)}"
        previous = value

    return True, f"{path}: OK ({len(timed_lines)} timestamped lines)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate timestamped LRC files.")
    parser.add_argument("paths", nargs="+", help="LRC files or directories containing .lrc files")
    parser.add_argument("--min-timed-lines", type=int, default=3)
    args = parser.parse_args()

    files: list[Path] = []
    for raw in args.paths:
        path = Path(raw).expanduser()
        if path.is_dir():
            files.extend(sorted(path.glob("*.lrc")))
        else:
            files.append(path)

    if not files:
        print("No .lrc files found", file=sys.stderr)
        return 1

    failed = False
    for path in files:
        ok, message = validate_lrc(path, args.min_timed_lines)
        print(message, file=sys.stderr if not ok else sys.stdout)
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
