#!/usr/bin/env python3
"""Search the bundled music genre database and emit Suno-ready style hints."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
GENRE_DIR = SKILL_DIR / "references" / "genre-finder"

ZH_KEYWORDS = {
    "深夜": ["night", "ambient", "atmospheric", "dark", "dreamy"],
    "夜晚": ["night", "ambient", "atmospheric"],
    "空灵": ["ethereal", "dreamy", "atmospheric", "reverb"],
    "梦幻": ["dreamy", "ethereal", "psychedelic", "atmospheric"],
    "放松": ["calm", "relaxing", "soothing", "laid-back"],
    "冥想": ["meditative", "ambient", "drone", "minimal"],
    "暗黑": ["dark", "gloomy", "ominous", "dissonant"],
    "压抑": ["dark", "gloomy", "melancholic"],
    "有活力": ["energetic", "fast", "intense", "dance"],
    "激烈": ["aggressive", "intense", "fast", "heavy"],
    "复古": ["retro", "vintage", "1980s", "classic"],
    "怀旧": ["nostalgic", "retro", "classic"],
    "电子": ["electronic", "synth", "digital", "techno"],
    "科技": ["futuristic", "electronic", "digital"],
    "实验": ["experimental", "avant-garde", "unconventional"],
    "前卫": ["avant-garde", "experimental"],
    "世界音乐": ["world", "folk", "african", "latin", "asian", "traditional"],
    "民族": ["folk", "traditional", "world"],
    "冲浪": ["surf", "rock", "reverb", "guitar"],
    "朋克": ["punk", "fast", "raw", "aggressive"],
    "摇滚": ["rock", "guitar", "heavy", "riff"],
    "金属": ["metal", "heavy", "distorted", "aggressive"],
    "爵士": ["jazz", "improvisation", "swing"],
    "民谣": ["folk", "acoustic", "traditional"],
}

SUGGESTED_STYLE_EXTRAS = {
    "ambient": ["atmospheric", "dreamy"],
    "dark": ["moody"],
    "dream": ["ethereal"],
    "punk": ["raw-vocals", "fast-tempo"],
    "rock": ["electric-guitar"],
    "metal": ["distorted-guitars"],
    "folk": ["acoustic-instruments"],
    "world": ["organic-percussion"],
    "dance": ["driving-rhythm"],
    "electronic": ["synth-textures"],
    "jazz": ["improvisational"],
}


def slugify_style(name: str) -> str:
    value = name.lower()
    value = value.replace("&", "and")
    value = re.sub(r"['’]", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value


def text_value(value: Any) -> str:
    return "" if value is None else str(value)


def expand_query(text: str) -> list[str]:
    lowered = text.lower()
    tokens = re.findall(r"[a-z0-9]+", lowered)
    expanded = list(tokens)
    for zh, mapped in ZH_KEYWORDS.items():
        if zh in text:
            expanded.extend(mapped)
    if not expanded and text.strip():
        expanded.append(text.strip().lower())
    return list(dict.fromkeys(expanded))


def load_records() -> list[dict[str, Any]]:
    if not GENRE_DIR.exists():
        raise SystemExit(f"Genre database not found: {GENRE_DIR}")

    records: dict[str, dict[str, Any]] = {}

    index_path = GENRE_DIR / "_index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        for item in index.get("genres", []):
            item = dict(item)
            item.setdefault("level", "main")
            item.setdefault("parent", "")
            records[item["name"].lower()] = item

    for folder in ("main", "detailed"):
        for path in sorted((GENRE_DIR / folder).glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if "sub_genres" in data:
                parent = {
                    "name": data.get("name", path.stem),
                    "description": data.get("description", ""),
                    "url": data.get("url", ""),
                    "level": "main",
                    "parent": "",
                    "children": data.get("sub_genres", []),
                }
                records[parent["name"].lower()] = parent
                for child in data.get("sub_genres", []):
                    records.setdefault(child["name"].lower(), child)
            else:
                data.setdefault("children", data.get("children", []))
                records[data["name"].lower()] = data
                for child in data.get("children", []):
                    records.setdefault(child["name"].lower(), child)

    return list(records.values())


def score_record(record: dict[str, Any], query: str, terms: list[str]) -> int:
    name = text_value(record.get("name")).lower()
    parent = text_value(record.get("parent")).lower()
    description = text_value(record.get("description")).lower()
    haystack = f"{name} {parent} {description}"
    score = 0

    normalized_query = query.lower().strip()
    if normalized_query and normalized_query == name:
        score += 120
    if normalized_query and normalized_query in name:
        score += 70

    for term in terms:
        if not term:
            continue
        if term == name:
            score += 80
        elif term in name:
            score += 35
        if term in parent:
            score += 18
        if term in description:
            score += 10
        if term in haystack:
            score += 2

    level = record.get("level", "")
    if level == "main":
        score += 4
    elif level == "sub":
        score += 8

    return score


def style_extras(record: dict[str, Any]) -> list[str]:
    text = " ".join(
        [
            text_value(record.get("name")),
            text_value(record.get("parent")),
            text_value(record.get("description")),
        ]
    ).lower()
    extras: list[str] = []
    for key, tags in SUGGESTED_STYLE_EXTRAS.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", text):
            extras.extend(tags)
    return list(dict.fromkeys(extras))[:3]


def search(query: str, limit: int) -> list[dict[str, Any]]:
    terms = expand_query(query)
    ranked = []
    for record in load_records():
        score = score_record(record, query, terms)
        if score <= 0:
            continue
        item = dict(record)
        item["score"] = score
        item["suno_tag"] = slugify_style(item["name"])
        item["style_extras"] = style_extras(item)
        ranked.append(item)

    ranked.sort(key=lambda item: (-item["score"], item.get("name", "")))
    return ranked[:limit]


def format_text(results: list[dict[str, Any]], query: str) -> str:
    if not results:
        return f"No genres found for: {query}"

    lines = [f"Genre ideas for: {query}", ""]
    for i, item in enumerate(results, 1):
        extras = ", ".join(item.get("style_extras", []))
        tag_line = item["suno_tag"] if not extras else f"{item['suno_tag']}, {extras}"
        parent = f" / {item['parent']}" if item.get("parent") else ""
        description = item.get("description", "").strip()
        if len(description) > 220:
            description = description[:217].rstrip() + "..."
        lines.extend(
            [
                f"{i}. {item['name']}{parent}",
                f"   Suno tags: {tag_line}",
                f"   {description}",
                f"   {item.get('url', '')}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find music genres and Suno-ready tags from the bundled genre database."
    )
    parser.add_argument("query", nargs="+", help="Genre, mood, scene, or keywords")
    parser.add_argument("--limit", type=int, default=6, help="Maximum recommendations")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    query = " ".join(args.query)
    results = search(query, max(1, args.limit))
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(format_text(results, query))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
