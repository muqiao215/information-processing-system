#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_SOURCE_IDS = [
    "hackernews",
]
USER_AGENT = "information-processing-system/newsnow-bridge/1.0"


def resolve_workspace_root() -> Path:
    repo_root = Path(__file__).resolve().parents[4]
    if repo_root.parent.name == "repos":
        return repo_root.parent.parent
    return repo_root.parent


WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", resolve_workspace_root()))
DEFAULT_OUTPUT = WORKSPACE_ROOT / "output_to_user" / "newsnow_latest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch a thin vendor-boundary-preserving snapshot from a running newsnow instance."
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("NEWSNOW_BASE_URL", "http://127.0.0.1:3000"),
        help="Base URL for the newsnow deployment.",
    )
    parser.add_argument(
        "--source-id",
        action="append",
        dest="source_ids",
        help="Source ID to fetch. Repeatable. Defaults to a curated starter set.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max items to keep per source after fetch.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write the bridge manifest JSON.",
    )
    return parser.parse_args()


def fetch_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_source_url(base_url: str, source_id: str) -> str:
    query = urlencode({"id": source_id, "latest": ""})
    return f"{base_url.rstrip('/')}/api/s?{query}"


def normalize_item(source_id: str, item: dict) -> dict:
    extra = item.get("extra") or {}
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "url": item.get("url"),
        "mobile_url": item.get("mobileUrl"),
        "published_at": item.get("pubDate"),
        "extra": {
            "hover": extra.get("hover"),
            "date": extra.get("date"),
            "info": extra.get("info"),
            "diff": extra.get("diff"),
        },
        "source_id": source_id,
    }


def fetch_source(base_url: str, source_id: str, limit: int) -> dict:
    url = build_source_url(base_url, source_id)
    payload = fetch_json(url)
    items = payload.get("items") or []
    return {
        "source_id": source_id,
        "status": payload.get("status"),
        "updated_time": payload.get("updatedTime"),
        "item_count": min(len(items), limit),
        "items": [normalize_item(source_id, item) for item in items[:limit]],
        "request_url": url,
    }


def main() -> int:
    args = parse_args()
    source_ids = args.source_ids or DEFAULT_SOURCE_IDS
    generated_at = datetime.now(timezone.utc).isoformat()
    results = [fetch_source(args.base_url, source_id, args.limit) for source_id in source_ids]
    payload = {
        "source": "newsnow",
        "bridge_version": "2026-05-11.v1",
        "generated_at": generated_at,
        "base_url": args.base_url.rstrip("/"),
        "source_ids": source_ids,
        "source_count": len(results),
        "total_item_count": sum(result["item_count"] for result in results),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
