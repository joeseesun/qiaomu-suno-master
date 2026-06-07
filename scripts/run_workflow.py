#!/usr/bin/env python3
"""Manifest-first wrapper around the qiaomu-suno-master shell scripts."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = Path.home() / "Documents" / "Suno"
SCHEMA_VERSION = 1
BLOCKED_RE = re.compile(
    r"auth_expired|JWT expired|JWT expired or rejected|401|403|captcha|hCaptcha|"
    r"token_validation_failed|schema_drift|Suno.s request schema has changed|"
    r"No Suno session found|session.*not found|GENERATION_BLOCKED",
    re.I,
)
LRC_PENDING_RE = re.compile(
    r"No timestamped lyric lines|valid timestamped LRC is required|only \d+ timestamped lines",
    re.I,
)
SONG_URL_RE = re.compile(r"https?://suno\.com/song/([A-Za-z0-9_-]+)")


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_path_name(value: str) -> str:
    cleaned = value.replace("/", "-").replace(":", "-")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "Untitled Suno Song"


def abs_path(value: str | Path) -> str:
    return str(Path(value).expanduser().resolve())


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    if not isinstance(manifest, dict):
        raise SystemExit(f"Manifest must be a JSON object: {path}")
    return manifest


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest["updated_at"] = now_iso()
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")


def append_history(manifest: dict[str, Any], event: str, detail: str = "") -> None:
    manifest.setdefault("history", []).append(
        {
            "at": now_iso(),
            "event": event,
            "detail": detail,
        }
    )


def normalize_ids(raw: str) -> list[str]:
    ids: list[str] = []
    for match in SONG_URL_RE.finditer(raw):
        ids.append(match.group(1))
    cleaned = SONG_URL_RE.sub(" ", raw)
    for part in re.split(r"[\s,]+", cleaned):
        part = part.strip()
        if part:
            ids.append(part)
    seen: set[str] = set()
    unique: list[str] = []
    for clip_id in ids:
        if clip_id not in seen:
            seen.add(clip_id)
            unique.append(clip_id)
    return unique


def create_manifest(args: argparse.Namespace) -> dict[str, Any]:
    title = args.title.strip()
    if not title:
        raise SystemExit("--title cannot be empty")
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else DEFAULT_ROOT / safe_path_name(title)
    ids = normalize_ids(args.ids or "")
    style = args.style.strip()
    if not style and not ids:
        raise SystemExit("--style is required unless --ids is provided for an existing-clip workflow")
    lyrics_file = ""
    if args.lyrics_file:
        path = Path(args.lyrics_file).expanduser()
        if not path.exists():
            raise SystemExit(f"Lyrics file not found: {path}")
        lyrics_file = abs_path(path)
    elif not ids:
        raise SystemExit("--lyrics-file is required unless --ids is provided for an existing-clip workflow")

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "prepared",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "title": title,
        "style_description": style,
        "exclude_styles": args.exclude.strip(),
        "model": args.model,
        "vocal": args.vocal,
        "lyrics_file": lyrics_file,
        "output_dir": abs_path(output_dir),
        "captcha_solver": args.captcha_solver,
        "generation": {
            "json_file": "",
            "clip_ids": ids,
            "song_links": [],
            "classified_error": "",
            "returncode": None,
        },
        "assets": empty_assets(),
        "validation": {
            "lrc": {
                "ok": False,
                "checked_at": "",
                "messages": [],
            }
        },
        "history": [
            {
                "at": now_iso(),
                "event": "manifest_created",
                "detail": "Created by run_workflow.py init.",
            }
        ],
    }


def empty_assets() -> dict[str, Any]:
    return {
        "audio": [],
        "lrc": [],
        "srt": [],
        "markdown_lyrics": [],
        "video": [],
        "cover": [],
    }


def validate_required_fields(manifest: dict[str, Any], for_generation: bool) -> None:
    required = ["title", "output_dir"]
    if for_generation:
        required.extend(["style_description", "lyrics_file", "model"])
    missing = [key for key in required if not str(manifest.get(key, "")).strip()]
    if missing:
        raise SystemExit(f"Manifest is missing required fields: {', '.join(missing)}")
    lyrics_value = str(manifest.get("lyrics_file", "")).strip()
    if not lyrics_value:
        return
    lyrics_file = Path(lyrics_value).expanduser()
    if not lyrics_file.exists():
        raise SystemExit(f"Lyrics file not found: {lyrics_file}")


def write_meta_env(manifest: dict[str, Any]) -> Path:
    output_dir = Path(str(manifest["output_dir"])).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    meta_file = output_dir / "suno-meta.env"
    values = {
        "TITLE": manifest.get("title", ""),
        "STYLE_DESCRIPTION": manifest.get("style_description", ""),
        "EXCLUDE_STYLES": manifest.get("exclude_styles", ""),
        "LYRICS_FILE": manifest.get("lyrics_file", ""),
        "MODEL": manifest.get("model", "v5.5"),
        "VOCAL": manifest.get("vocal", ""),
        "SUNO_USE_CAPTCHA_SOLVER": "1" if manifest.get("captcha_solver", True) else "0",
    }
    lines = [
        "# Generated by qiaomu-suno-master/scripts/run_workflow.py",
        "# Do not store secrets here. Pass HCAPTCHA_TOKEN via the environment if needed.",
    ]
    lines.extend(f"{key}={shlex.quote(str(value))}" for key, value in values.items())
    meta_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return meta_file


def parse_generation_json(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    clips = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(clips, list):
        return []
    ids: list[str] = []
    for clip in clips:
        if isinstance(clip, dict) and clip.get("id"):
            ids.append(str(clip["id"]))
    return ids


def find_assets(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.expanduser()
    assets = empty_assets()
    if not output_dir.exists():
        return assets
    assets["audio"] = sorted(str(path) for path in output_dir.glob("*.mp3"))
    assets["lrc"] = sorted(str(path) for path in output_dir.glob("*.lrc"))
    assets["srt"] = sorted(str(path) for path in output_dir.glob("*.srt"))
    assets["markdown_lyrics"] = sorted(str(path) for path in output_dir.glob("*.lyrics.md"))
    video_exts = ("*.mp4", "*.mov", "*.webm", "*.m4v")
    assets["video"] = sorted(str(path) for pattern in video_exts for path in output_dir.glob(pattern))
    cover_exts = ("*.png", "*.jpg", "*.jpeg", "*.webp")
    assets["cover"] = sorted(
        str(path)
        for pattern in cover_exts
        for path in output_dir.glob(pattern)
        if "cover" in path.stem.lower()
    )
    return assets


def classify_failure(text: str) -> str:
    if BLOCKED_RE.search(text):
        return "generation_blocked"
    if LRC_PENDING_RE.search(text):
        return "lrc_pending"
    if re.search(r"download failed|Error: download failed", text, re.I):
        return "download_failed"
    return "failed"


def run_and_tee(cmd: list[str], log_path: Path) -> tuple[int, str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    combined: list[str] = []
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n$ {' '.join(shlex.quote(part) for part in cmd)}\n")
        proc = subprocess.Popen(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            combined.append(line)
            print(line, end="")
            log.write(line)
        returncode = proc.wait()
        log.write(f"[exit {returncode}]\n")
    return returncode, "".join(combined)


def update_lrc_validation(manifest: dict[str, Any]) -> bool:
    output_dir = Path(str(manifest["output_dir"])).expanduser()
    validator = SCRIPT_DIR / "validate_lrc.py"
    proc = subprocess.run(
        ["python3", str(validator), str(output_dir)],
        text=True,
        capture_output=True,
        check=False,
    )
    messages = [line for line in (proc.stdout + proc.stderr).splitlines() if line.strip()]
    ok = proc.returncode == 0
    manifest.setdefault("validation", {})["lrc"] = {
        "ok": ok,
        "checked_at": now_iso(),
        "messages": messages,
    }
    return ok


def command_init(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).expanduser()
    if manifest_path.exists() and not args.overwrite:
        raise SystemExit(f"Manifest already exists: {manifest_path} (use --overwrite)")
    manifest = create_manifest(args)
    save_manifest(manifest_path, manifest)
    print(str(manifest_path))
    return 0


def command_generate(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).expanduser()
    manifest = load_manifest(manifest_path)
    validate_required_fields(manifest, for_generation=True)
    output_dir = Path(str(manifest["output_dir"])).expanduser()
    meta_file = write_meta_env(manifest)
    json_file = Path(args.json_file).expanduser() if args.json_file else output_dir / "generate.result.json"
    log_file = output_dir / "workflow.log"

    cmd = [
        "bash",
        str(SCRIPT_DIR / "generate_download_lrc.sh"),
        "--meta-file",
        str(meta_file),
        "--output-dir",
        str(output_dir),
        "--json-file",
        str(json_file),
        "--lyrics-format",
        args.lyrics_format,
        "--initial-wait",
        str(args.initial_wait),
        "--retries",
        str(args.retries),
        "--delay",
        str(args.delay),
    ]
    cmd.append("--no-browser" if args.no_browser else "--browser")
    cmd.append("--no-require-lrc" if args.no_require_lrc else "--require-lrc")

    manifest.setdefault("workflow", {})["meta_file"] = str(meta_file)
    manifest["generation"]["json_file"] = str(json_file)

    if args.dry_run:
        manifest["status"] = "ready"
        append_history(manifest, "generate_dry_run", "Prepared meta env without calling Suno.")
        save_manifest(manifest_path, manifest)
        print(" ".join(shlex.quote(part) for part in cmd))
        return 0

    returncode, output = run_and_tee(cmd, log_file)
    ids = parse_generation_json(json_file)
    if ids:
        manifest["generation"]["clip_ids"] = ids
        manifest["generation"]["song_links"] = [f"https://suno.com/song/{clip_id}" for clip_id in ids]
    manifest["generation"]["returncode"] = returncode
    manifest["assets"] = find_assets(output_dir)

    lrc_ok = update_lrc_validation(manifest)
    if returncode == 0:
        manifest["generation"]["classified_error"] = ""
        manifest["status"] = "lrc_ready" if lrc_ok else "downloaded"
        append_history(manifest, "generate_completed", f"Clip IDs: {' '.join(ids)}")
    else:
        classified = classify_failure(output)
        manifest["generation"]["classified_error"] = classified
        manifest["status"] = classified
        append_history(manifest, "generate_failed", classified)
    save_manifest(manifest_path, manifest)
    return returncode


def command_download(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).expanduser()
    manifest = load_manifest(manifest_path)
    validate_required_fields(manifest, for_generation=False)
    output_dir = Path(str(manifest["output_dir"])).expanduser()
    ids = normalize_ids(args.ids or " ".join(manifest.get("generation", {}).get("clip_ids", [])))
    if not ids:
        raise SystemExit("No clip IDs found. Pass --ids or generate first.")

    log_file = output_dir / "workflow.log"
    cmd = [
        "bash",
        str(SCRIPT_DIR / "download_clips.sh"),
        "--ids",
        " ".join(ids),
        "--output-dir",
        str(output_dir),
        "--lyrics",
        "--lyrics-format",
        args.lyrics_format,
        "--initial-wait",
        str(args.initial_wait),
        "--retries",
        str(args.retries),
        "--delay",
        str(args.delay),
    ]
    cmd.append("--no-browser" if args.no_browser else "--browser")
    if not args.no_require_lrc:
        cmd.append("--require-lrc")

    if args.dry_run:
        print(" ".join(shlex.quote(part) for part in cmd))
        return 0

    returncode, output = run_and_tee(cmd, log_file)
    manifest.setdefault("generation", {})["clip_ids"] = ids
    manifest["generation"]["song_links"] = [f"https://suno.com/song/{clip_id}" for clip_id in ids]
    manifest["assets"] = find_assets(output_dir)
    lrc_ok = update_lrc_validation(manifest)
    if returncode == 0:
        manifest["status"] = "lrc_ready" if lrc_ok else "downloaded"
        manifest["generation"]["classified_error"] = ""
        append_history(manifest, "download_completed", f"Clip IDs: {' '.join(ids)}")
    else:
        classified = classify_failure(output)
        manifest["status"] = classified
        manifest["generation"]["classified_error"] = classified
        append_history(manifest, "download_failed", classified)
    save_manifest(manifest_path, manifest)
    return returncode


def command_validate_lrc(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).expanduser()
    manifest = load_manifest(manifest_path)
    ok = update_lrc_validation(manifest)
    manifest["assets"] = find_assets(Path(str(manifest["output_dir"])).expanduser())
    if ok:
        manifest["status"] = "lrc_ready"
    append_history(manifest, "lrc_validated", "ok" if ok else "failed")
    save_manifest(manifest_path, manifest)
    for message in manifest["validation"]["lrc"]["messages"]:
        print(message)
    return 0 if ok else 1


def command_status(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest).expanduser())
    generation = manifest.get("generation", {})
    validation = manifest.get("validation", {}).get("lrc", {})
    print(f"Status: {manifest.get('status', 'unknown')}")
    print(f"Title: {manifest.get('title', '')}")
    print(f"Output: {manifest.get('output_dir', '')}")
    print(f"Clip IDs: {' '.join(generation.get('clip_ids', []))}")
    print(f"LRC: {'OK' if validation.get('ok') else 'not ready'}")
    if generation.get("classified_error"):
        print(f"Error class: {generation['classified_error']}")
    return 0


def add_common_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--lyrics-format", default="lrc", help="lrc, srt, md, all, both")
    parser.add_argument("--initial-wait", type=int, default=5)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--delay", type=int, default=10)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-require-lrc", action="store_true")
    parser.add_argument("--dry-run", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run qiaomu-suno-master with a song manifest.")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a song manifest from prepared lyrics and tags.")
    init.add_argument("--manifest", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--style", default="")
    init.add_argument("--lyrics-file", default="")
    init.add_argument("--exclude", default="")
    init.add_argument("--model", default="v5.5")
    init.add_argument("--vocal", default="")
    init.add_argument("--output-dir", default="")
    init.add_argument("--ids", default="", help="Optional existing clip IDs or Suno song URLs.")
    init.add_argument("--no-captcha-solver", dest="captcha_solver", action="store_false")
    init.set_defaults(captcha_solver=True, func=command_init)
    init.add_argument("--overwrite", action="store_true")

    generate = sub.add_parser("generate", help="Generate, download, fetch LRC, and update manifest.")
    generate.add_argument("--manifest", required=True)
    generate.add_argument("--json-file", default="")
    add_common_run_args(generate)
    generate.set_defaults(func=command_generate)

    download = sub.add_parser("download", help="Download existing clip IDs and update manifest.")
    download.add_argument("--manifest", required=True)
    download.add_argument("--ids", default="")
    add_common_run_args(download)
    download.set_defaults(func=command_download)

    validate = sub.add_parser("validate-lrc", help="Validate LRC files and update manifest.")
    validate.add_argument("--manifest", required=True)
    validate.set_defaults(func=command_validate_lrc)

    status = sub.add_parser("status", help="Print a short manifest summary.")
    status.add_argument("--manifest", required=True)
    status.set_defaults(func=command_status)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
