#!/usr/bin/env python3
"""Preflight checks for the qiaomu-suno-master workflow."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
AUTH_EXPIRED_RE = re.compile(r"auth:\s*expired|JWT expired|refresh failed|auth_expired", re.I)


def run(cmd: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "returncode": 127,
            "stdout": "",
            "stderr": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or f"Timed out after {timeout}s",
        }
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    ok: bool,
    detail: str = "",
    hint: str = "",
    required: bool = True,
) -> None:
    checks.append(
        {
            "name": name,
            "ok": ok,
            "required": required,
            "detail": detail,
            "hint": hint,
        }
    )


def check_file(checks: list[dict[str, Any]], name: str, path: Path) -> None:
    add_check(
        checks,
        name,
        path.exists(),
        str(path),
        f"Expected file at {path}",
    )


def check_writable_dir(checks: list[dict[str, Any]], path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=".suno-doctor-", dir=path, delete=True):
            pass
    except Exception as exc:  # pragma: no cover - platform-specific detail
        add_check(
            checks,
            "output_dir_writable",
            False,
            f"{path}: {exc}",
            "Choose another --output-dir or fix directory permissions.",
        )
    else:
        add_check(checks, "output_dir_writable", True, str(path))


def check_node(checks: list[dict[str, Any]]) -> None:
    node = shutil.which("node")
    if not node:
        add_check(
            checks,
            "node",
            False,
            "",
            "Install Node.js 22+ for the Chrome CDP helper.",
        )
        return

    version = run([node, "-p", "process.versions.node"], timeout=5)
    raw = version["stdout"] or version["stderr"]
    try:
        major = int(str(raw).split(".", 1)[0])
    except Exception:
        major = 0
    add_check(
        checks,
        "node",
        major >= 22,
        f"{node} {raw}",
        "Install Node.js 22+ for the Chrome CDP helper.",
    )


def check_websocket(checks: list[dict[str, Any]]) -> None:
    try:
        import websocket  # noqa: F401
    except Exception as exc:
        add_check(
            checks,
            "python_websocket_client",
            False,
            str(exc),
            "Install websocket-client if you want browser-first downloads.",
            required=False,
        )
    else:
        add_check(checks, "python_websocket_client", True, "available", required=False)


def check_suno(checks: list[dict[str, Any]], skip_suno: bool) -> None:
    if skip_suno:
        add_check(checks, "suno_cli", True, "skipped by --skip-suno")
        return

    suno = shutil.which("suno")
    if not suno:
        add_check(
            checks,
            "suno_cli",
            False,
            "",
            "Run: bash scripts/ensure_suno_cli.sh",
        )
        return

    version = run([suno, "--version"], timeout=10)
    version_text = version["stdout"] or version["stderr"] or suno
    add_check(checks, "suno_cli", version["returncode"] == 0, version_text)

    config = run([suno, "config", "check"], timeout=20)
    detail = config["stdout"] or config["stderr"]
    add_check(
        checks,
        "suno_config",
        config["returncode"] == 0,
        detail,
        "Run `suno config check` and fix the reported local configuration issue.",
    )
    auth_ok = config["returncode"] == 0 and (
        "Auth: OK" in detail or not AUTH_EXPIRED_RE.search(detail)
    )
    add_check(
        checks,
        "suno_auth",
        auth_ok,
        detail or "auth did not report an expired token",
        "Run `suno auth --login --quiet` or use the browser fallback lane.",
    )


def check_chrome_session(checks: list[dict[str, Any]], active: bool) -> None:
    session_script = SCRIPT_DIR / "ensure_suno_chrome_session.sh"
    check_file(checks, "chrome_session_helper", session_script)
    if not active or not session_script.exists():
        return

    proc = run(["bash", str(session_script)], timeout=30)
    detail = "\n".join(part for part in (proc["stdout"], proc["stderr"]) if part)
    add_check(
        checks,
        "chrome_suno_session",
        proc["returncode"] == 0,
        detail,
        "Open Chrome with remote debugging, log in to Suno, then rerun.",
        required=False,
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    for name in (
        "generate_with_suno.sh",
        "generate_download_lrc.sh",
        "download_clips.sh",
        "validate_lrc.py",
        "export_suno_assets.py",
        "run_workflow.py",
    ):
        check_file(checks, f"script_{name}", SCRIPT_DIR / name)

    check_node(checks)
    check_websocket(checks)
    check_suno(checks, args.skip_suno)
    check_chrome_session(checks, args.chrome_session)
    check_writable_dir(checks, Path(args.output_dir).expanduser())

    ok = all(check["ok"] or not check["required"] for check in checks)
    return {
        "ok": ok,
        "skill_dir": str(SKILL_DIR),
        "checks": checks,
    }


def print_human(report: dict[str, Any]) -> None:
    print(f"Suno doctor: {'OK' if report['ok'] else 'FAILED'}")
    print(f"Skill: {report['skill_dir']}")
    for check in report["checks"]:
        mark = "OK" if check["ok"] else ("WARN" if not check["required"] else "FAIL")
        print(f"[{mark}] {check['name']}")
        if check["detail"]:
            print(f"  {check['detail']}")
        if not check["ok"] and check["hint"]:
            print(f"  hint: {check['hint']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight qiaomu-suno-master.")
    parser.add_argument(
        "--output-dir",
        default=str(Path.home() / "Documents" / "Suno"),
        help="Directory to check for output writability.",
    )
    parser.add_argument(
        "--chrome-session",
        action="store_true",
        help="Actively check the Chrome/Suno CDP session. This may open a Suno tab.",
    )
    parser.add_argument(
        "--skip-suno",
        action="store_true",
        help="Skip suno CLI checks for dry-run or CI validation.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    report = build_report(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
