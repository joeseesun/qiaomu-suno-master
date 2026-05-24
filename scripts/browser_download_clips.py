#!/usr/bin/env python3
"""Download Suno audio through a CDP-enabled Chrome page.

The regular `suno download` path can hang on some CDN connections even when a
Chrome tab can fetch the same mp3 quickly. This helper asks Chrome to fetch the
audio URL as a blob and save it through the browser download pipeline.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import websocket
except ImportError as exc:  # pragma: no cover - environment dependent
    raise SystemExit("Python package `websocket-client` is required") from exc


DEFAULT_PORTS = (9233, 9222, 9223, 9224, 9225)


@dataclass
class Clip:
    clip_id: str
    title: str | None = None
    audio_url: str | None = None


class CDP:
    def __init__(self, ws_url: str, timeout: int = 20) -> None:
        self._ws = websocket.create_connection(
            ws_url,
            timeout=timeout,
            suppress_origin=True,
        )
        self._next_id = 0

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._next_id += 1
        request_id = self._next_id
        payload: dict[str, Any] = {"id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._ws.send(json.dumps(payload))
        while True:
            response = json.loads(self._ws.recv())
            if response.get("id") != request_id:
                continue
            if "error" in response:
                raise RuntimeError(f"{method}: {response['error']}")
            return response.get("result", {})

    def close(self) -> None:
        self._ws.close()


def load_json_url(url: str, timeout: float = 2.0) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def read_devtools_ports() -> list[int]:
    home = Path.home()
    candidates = [
        home / "Library/Application Support/com.suno-cli.suno-cli/chrome-profile/DevToolsActivePort",
        home / "Library/Application Support/Google/Chrome/DevToolsActivePort",
        home / "Library/Application Support/Chromium/DevToolsActivePort",
        home / "Library/Application Support/BraveSoftware/Brave-Browser/DevToolsActivePort",
        home / ".config/google-chrome/DevToolsActivePort",
        home / ".config/chromium/DevToolsActivePort",
        home / ".config/BraveSoftware/Brave-Browser/DevToolsActivePort",
    ]
    ports: list[int] = []
    for path in candidates:
        try:
            first_line = path.read_text(encoding="utf-8").splitlines()[0]
            ports.append(int(first_line))
        except (OSError, IndexError, ValueError):
            continue
    return ports


def candidate_endpoints() -> list[str]:
    ports: list[int] = []
    for value in (os.environ.get("SUNO_CDP_PORT"), os.environ.get("CDP_PORT")):
        if value:
            try:
                ports.append(int(value))
            except ValueError:
                pass
    ports.extend(read_devtools_ports())
    ports.extend(DEFAULT_PORTS)

    endpoints: list[str] = []
    seen: set[int] = set()
    for port in ports:
        if port in seen:
            continue
        seen.add(port)
        endpoints.append(f"http://127.0.0.1:{port}")
    return endpoints


def resolve_endpoint(explicit: str | None) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    endpoints = [explicit] if explicit else candidate_endpoints()
    errors: list[str] = []
    best: tuple[str, dict[str, Any], list[dict[str, Any]]] | None = None

    for endpoint in endpoints:
        if not endpoint:
            continue
        endpoint = endpoint.rstrip("/")
        try:
            version = load_json_url(f"{endpoint}/json/version")
            targets = load_json_url(f"{endpoint}/json/list")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            errors.append(f"{endpoint}: {exc}")
            continue
        pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
        if not pages:
            errors.append(f"{endpoint}: no debuggable pages")
            continue
        current = (endpoint, version, targets)
        if any("suno.com" in p.get("url", "") for p in pages):
            return current
        best = best or current

    if best:
        return best
    raise SystemExit("Could not find a CDP-enabled Chrome endpoint:\n" + "\n".join(errors))


def load_manifest(path: str | None) -> dict[str, Clip]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    clips = data.get("data", data) if isinstance(data, dict) else data
    by_id: dict[str, Clip] = {}
    if isinstance(clips, list):
        for item in clips:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            by_id[item["id"]] = Clip(
                clip_id=item["id"],
                title=item.get("title"),
                audio_url=item.get("audio_url"),
            )
    return by_id


def safe_filename(value: str) -> str:
    value = re.sub(r"[/:\\]+", "-", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"[\x00-\x1f]+", "", value)
    return value or "Suno clip"


def build_clips(ids: str, manifest: dict[str, Clip]) -> list[Clip]:
    clips: list[Clip] = []
    for clip_id in ids.split():
        known = manifest.get(clip_id)
        clips.append(
            Clip(
                clip_id=clip_id,
                title=known.title if known else None,
                audio_url=(known.audio_url if known else None) or f"https://cdn1.suno.ai/{clip_id}.mp3",
            )
        )
    return clips


def choose_page(targets: list[dict[str, Any]]) -> dict[str, Any]:
    pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    for page in pages:
        if "suno.com" in page.get("url", ""):
            return page
    if not pages:
        raise SystemExit("No debuggable Chrome page found")
    return pages[0]


def expected_path(output_dir: Path, clip: Clip) -> Path:
    title = safe_filename(clip.title or "Suno")
    return output_dir / f"{title}-{clip.clip_id[:8]}.mp3"


def browser_download(page: CDP, output_dir: Path, clip: Clip, timeout: int) -> Path:
    destination = expected_path(output_dir, clip)
    if destination.exists() and destination.stat().st_size > 0:
        print(destination)
        return destination

    try:
        destination.unlink()
    except FileNotFoundError:
        pass

    filename = destination.name
    expression = f"""
    (async () => {{
      const response = await fetch({json.dumps(clip.audio_url)}, {{ mode: 'cors' }});
      if (!response.ok) throw new Error(`fetch failed: ${{response.status}}`);
      const blob = await response.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = {json.dumps(filename)};
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {{
        URL.revokeObjectURL(link.href);
        link.remove();
      }}, 60000);
      return {{ ok: true, size: blob.size, filename: link.download }};
    }})()
    """
    result = page.call(
        "Runtime.evaluate",
        {"expression": expression, "awaitPromise": True, "returnByValue": True},
    )
    if result.get("exceptionDetails"):
        details = result["exceptionDetails"]
        raise RuntimeError(details.get("text") or details.get("exception", {}).get("description"))

    expected_size = result.get("result", {}).get("value", {}).get("size")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if destination.exists():
            size = destination.stat().st_size
            if size > 0 and (not expected_size or size == expected_size):
                print(destination)
                return destination
        time.sleep(0.5)

    raise RuntimeError(f"Timed out waiting for {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", required=True, help="Space-separated Suno clip IDs")
    parser.add_argument("--output-dir", required=True, help="Directory to save MP3 files")
    parser.add_argument("--manifest-json", help="Optional generate JSON with data[].audio_url/title")
    parser.add_argument("--timeout", type=int, default=120, help="Seconds to wait per file")
    parser.add_argument("--cdp-url", help="Explicit CDP HTTP endpoint, e.g. http://127.0.0.1:9233")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    _, version, targets = resolve_endpoint(args.cdp_url)
    browser = CDP(version["webSocketDebuggerUrl"])
    page_target = choose_page(targets)
    page = CDP(page_target["webSocketDebuggerUrl"])

    try:
        browser.call(
            "Browser.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": str(output_dir),
                "eventsEnabled": True,
            },
        )
        page.call("Runtime.enable")
        page.call("Page.enable")
        manifest = load_manifest(args.manifest_json)
        for clip in build_clips(args.ids, manifest):
            browser_download(page, output_dir, clip, args.timeout)
    finally:
        page.close()
        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
