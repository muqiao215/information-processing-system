#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_AI_KEYWORDS = (
    "ai",
    "agent",
    "agents",
    "llm",
    "gpt",
    "openai",
    "anthropic",
    "claude",
    "codex",
    "gemini",
    "copilot",
    "cursor",
    "notebooklm",
    "mcp",
    "rag",
    "chrome",
    "browser",
    "gpu",
    "nvidia",
    "model",
    "inference",
    "developer",
    "devtool",
    "github",
    "hacker news",
)

DEFAULT_ALLOWED_SOURCE_IDS = (
    "hackernews",
)

BLOCKLIST_PATTERNS = (
    "汽车",
    "suv",
    "换电",
    "吹风机",
    "盲订",
    "mpv",
    "电影",
    "综艺",
    "手机话费",
    "老年人",
)


def resolve_workspace_root() -> Path:
    repo_root = Path(__file__).resolve().parents[4]
    if repo_root.parent.name == "repos":
        return repo_root.parent.parent
    return repo_root.parent


WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", resolve_workspace_root()))
DEFAULT_INPUT = WORKSPACE_ROOT / "output_to_user" / "newsnow_latest.json"
DEFAULT_OUTPUT = WORKSPACE_ROOT / "output_to_user" / "newsnow_candidate_pool_latest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a daily-news-summary candidate pool from a previously fetched newsnow manifest."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to the newsnow bridge manifest JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write the filtered candidate pool JSON.",
    )
    parser.add_argument(
        "--per-source-limit",
        type=int,
        default=5,
        help="Max candidates kept per source after filtering.",
    )
    parser.add_argument(
        "--allowed-source-id",
        action="append",
        dest="allowed_source_ids",
        help="Restrict candidate generation to these source IDs. Defaults to hackernews only.",
    )
    return parser.parse_args()


def normalize(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def score_item(source_id: str, item: dict) -> tuple[int, list[str]]:
    title = normalize(item.get("title")).lower()
    signals: list[str] = []
    score = 0

    for keyword in DEFAULT_AI_KEYWORDS:
        if keyword in title:
            score += 2
            signals.append(keyword)

    if source_id in {"github", "hackernews", "producthunt"}:
        score += 2
        signals.append(f"source:{source_id}")

    info = normalize((item.get("extra") or {}).get("info"))
    points_match = re.search(r"(\d+)\s+points", info.lower())
    if points_match:
        points = int(points_match.group(1))
        if points >= 200:
            score += 2
            signals.append("hn:200+")
        elif points >= 80:
            score += 1
            signals.append("hn:80+")

    for blocked in BLOCKLIST_PATTERNS:
        if blocked.lower() in title:
            score -= 3
            signals.append(f"blocked:{blocked}")

    return score, signals


def build_candidate(source_id: str, item: dict, score: int, signals: list[str]) -> dict:
    return {
        "source_id": source_id,
        "title": item.get("title"),
        "url": item.get("url"),
        "published_at": item.get("published_at"),
        "score": score,
        "signals": signals,
        "extra_info": (item.get("extra") or {}).get("info"),
        "selection_note": "Candidate only. Must read full body before using in the final digest.",
    }


def main() -> int:
    args = parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    allowed_source_ids = tuple(args.allowed_source_ids or DEFAULT_ALLOWED_SOURCE_IDS)
    grouped: dict[str, list[dict]] = {}

    for result in payload.get("results", []):
        source_id = result.get("source_id")
        if source_id not in allowed_source_ids:
            continue
        chosen: list[dict] = []
        for item in result.get("items", []):
            score, signals = score_item(source_id, item)
            if score <= 0:
                continue
            chosen.append(build_candidate(source_id, item, score, signals))
        chosen.sort(key=lambda item: (item["score"], normalize(item["title"])), reverse=True)
        grouped[source_id] = chosen[: args.per_source_limit]

    flat_items = [item for items in grouped.values() for item in items]
    output = {
        "source": "newsnow-candidate-pool",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_manifest": str(args.input),
        "candidate_count": len(flat_items),
        "per_source_limit": args.per_source_limit,
        "allowed_source_ids": list(allowed_source_ids),
        "groups": grouped,
        "usage_contract": {
            "purpose": "daily-news-summary candidate discovery only",
            "must_read_full_body": True,
            "must_not_summarize_from_titles_only": True,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
