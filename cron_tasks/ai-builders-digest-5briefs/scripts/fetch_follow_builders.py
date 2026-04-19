#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen


FEEDS = {
    "x": "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-x.json",
    "podcasts": "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-podcasts.json",
    "blogs": "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-blogs.json",
}


def fetch_json(url: str):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


payload = {
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "feeds": {},
    "stats": {},
}

for key, url in FEEDS.items():
    data = fetch_json(url)
    payload["feeds"][key] = data

payload["stats"] = {
    "x_builders": len(payload["feeds"]["x"].get("x", [])),
    "tweet_count": sum(len(item.get("tweets", [])) for item in payload["feeds"]["x"].get("x", [])),
    "podcast_count": len(payload["feeds"]["podcasts"].get("podcasts", [])),
    "blog_count": len(payload["feeds"]["blogs"].get("blogs", [])),
}

print(json.dumps(payload, ensure_ascii=False, indent=2))
