#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


REMOTE_FEEDS = {
    "x": "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-x.json",
    "podcasts": "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-podcasts.json",
    "blogs": "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-blogs.json",
}

REPO_ROOT = Path(__file__).resolve().parents[3]
MIRROR_DIR = REPO_ROOT / "skills" / "follow-builders" / "data" / "public-feed-mirror"
MIRROR_FEEDS = {
    "x": MIRROR_DIR / "feed-x.json",
    "podcasts": MIRROR_DIR / "feed-podcasts.json",
    "blogs": MIRROR_DIR / "feed-blogs.json",
}


def fetch_json(url: str):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_local_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_feed(mode: str, key: str):
    local_path = MIRROR_FEEDS[key]
    if mode == "remote":
        return fetch_json(REMOTE_FEEDS[key]), "remote"
    if mode == "local":
        return load_local_json(local_path), "local"
    if local_path.exists():
        return load_local_json(local_path), "local"
    return fetch_json(REMOTE_FEEDS[key]), "remote-fallback"


payload = {
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "feedMode": os.environ.get("FOLLOW_BUILDERS_FEED_MODE", "prefer-local"),
    "feedSources": {},
    "feeds": {},
    "stats": {},
}

for key in REMOTE_FEEDS:
    data, source = resolve_feed(payload["feedMode"], key)
    payload["feeds"][key] = data
    payload["feedSources"][key] = {
        "mode": source,
        "path": str(MIRROR_FEEDS[key]) if source == "local" else None,
        "url": REMOTE_FEEDS[key],
    }

payload["stats"] = {
    "x_builders": len(payload["feeds"]["x"].get("x", [])),
    "tweet_count": sum(len(item.get("tweets", [])) for item in payload["feeds"]["x"].get("x", [])),
    "podcast_count": len(payload["feeds"]["podcasts"].get("podcasts", [])),
    "blog_count": len(payload["feeds"]["blogs"].get("blogs", [])),
}

print(json.dumps(payload, ensure_ascii=False, indent=2))
