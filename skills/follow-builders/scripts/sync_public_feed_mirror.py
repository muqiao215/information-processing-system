#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


REMOTE_FEEDS = {
    "feed-x.json": "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-x.json",
    "feed-podcasts.json": "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-podcasts.json",
    "feed-blogs.json": "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-blogs.json",
}

SKILL_DIR = Path(__file__).resolve().parents[1]
MIRROR_DIR = SKILL_DIR / "data" / "public-feed-mirror"
MANIFEST_PATH = MIRROR_DIR / "manifest.json"


def fetch_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as resp:
        return resp.read()


def main() -> None:
    MIRROR_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceRepo": "https://github.com/zarazhangrui/follow-builders",
        "files": {},
    }
    for filename, url in REMOTE_FEEDS.items():
        raw = fetch_bytes(url)
        parsed = json.loads(raw.decode("utf-8"))
        target = MIRROR_DIR / filename
        target.write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        list_value = next((value for value in parsed.values() if isinstance(value, list)), [])
        manifest["files"][filename] = {
            "url": url,
            "bytes": len(raw),
            "records": len(list_value),
        }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
