#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from html import unescape
from urllib.request import Request, urlopen


URL = "https://github.com/trending?since=daily"


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_number(text: str) -> int:
    text = text.replace(",", "").strip()
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([kK]?)", text)
    if not match:
        return 0
    value = float(match.group(1))
    if match.group(2):
        value *= 1000
    return int(value)


req = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urlopen(req, timeout=30) as resp:
    html = resp.read().decode("utf-8", errors="replace")

articles = re.findall(r"<article class=\"Box-row\".*?</article>", html, re.S)
repos: list[dict[str, object]] = []
for article in articles:
    href_match = re.search(r"<h2[^>]*>.*?<a[^>]*href=\"/([^/]+)/([^\"/]+)\"", article, re.S)
    if not href_match:
        continue
    owner, name = href_match.group(1), href_match.group(2)
    desc_match = re.search(r"<p[^>]*>(.*?)</p>", article, re.S)
    lang_match = re.search(r"programmingLanguage\"[^>]*>(.*?)</span>", article, re.S)
    star_match = re.search(r"href=\"/[^\"]+/stargazers\"[^>]*>(.*?)</a>", article, re.S)
    today_match = re.search(r"([0-9.,kK]+)\s+stars\s+today", article, re.I)
    description = clean(desc_match.group(1) if desc_match else "")
    description = re.sub(r"^Star\s+[A-Za-z0-9_.-]+\s*/\s*[A-Za-z0-9_.-]+\s+", "", description)
    repos.append(
        {
            "owner": owner,
            "name": name,
            "full_name": f"{owner}/{name}",
            "description": description,
            "language": clean(lang_match.group(1) if lang_match else ""),
            "stars": parse_number(clean(star_match.group(1) if star_match else "")),
            "stars_today": parse_number(today_match.group(1) if today_match else ""),
            "url": f"https://github.com/{owner}/{name}",
        }
    )

print(json.dumps({"url": URL, "count": len(repos), "repos": repos}, ensure_ascii=False, indent=2))
