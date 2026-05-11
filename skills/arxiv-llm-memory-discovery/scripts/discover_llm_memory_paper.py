#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


ARXIV_API = "https://export.arxiv.org/api/query"
USER_AGENT = "arxiv-llm-memory-discovery/1.0 (daily personal research digest)"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
UTC = timezone.utc


def resolve_workspace_root() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    if repo_root.parent.name == "repos":
        return repo_root.parent.parent
    return repo_root.parent


WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", resolve_workspace_root()))
DEFAULT_MD_OUT = WORKSPACE_ROOT / "output_to_user" / "arxiv_llm_memory_discovery_latest.md"
DEFAULT_JSON_OUT = WORKSPACE_ROOT / "output_to_user" / "arxiv_llm_memory_discovery_latest.json"
DEFAULT_STATE_OUT = WORKSPACE_ROOT / "output_to_user" / "arxiv_llm_memory_discovery_state.json"

QUERIES = [
    'abs:LLM AND abs:memory',
    'abs:"large language model" AND abs:memory',
    'abs:"language model" AND abs:"long-term memory"',
    'abs:"language model" AND abs:"episodic memory"',
    'abs:"language model" AND abs:"semantic memory"',
    'abs:"context window" AND abs:memory',
    'abs:"KV cache" AND abs:memory',
    'abs:"retrieval augmented" AND abs:memory',
]

POSITIVE_PATTERNS = [
    (r"\blarge language model(s)?\b|\bLLM(s)?\b|\blanguage model(s)?\b", 3),
    (r"\blong[- ]term memory\b|\bpersistent memory\b|\bcross[- ]session memory\b", 5),
    (r"\bepisodic memory\b|\bsemantic memory\b|\buser memory\b|\bpersonal memory\b", 5),
    (r"\bconversational memory\b|\bdialogue memory\b|\bchatbot memory\b", 4),
    (r"\bmemory[- ]augmented\b|\bexternal memory\b|\bretrieval memory\b", 4),
    (r"\bretrieval[- ]augmented generation\b|\bRAG\b|\bretrieval augmented\b", 3),
    (r"\bcontext window\b|\bcontext compression\b|\blong context\b", 3),
    (r"\bKV cache\b|\bkey[- ]value cache\b|\bcache compression\b", 4),
    (r"\bagent memory\b|\bLLM agent(s)?\b|\bconversational agent(s)?\b", 3),
]

NEGATIVE_PATTERNS = [
    (r"\bmamba\b|\bstate space model(s)?\b|\bSSM(s)?\b", 6),
    (r"\btime series\b|\bforecasting\b", 5),
    (r"\bmemory[- ]efficient training\b|\bGPU memory\b|\bVRAM\b|\bactivation memory\b", 4),
    (r"\bhuman memory\b|\bworking memory\b|\bneuroscience\b|\bhippocamp", 4),
    (r"\bcomputer vision\b|\bdiffusion model(s)?\b|\bimage generation\b", 3),
]


@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    summary: str
    published: str
    updated: str
    categories: list[str]
    abs_url: str
    pdf_url: str
    score: int = 0
    reasons: list[str] | None = None
    penalties: list[str] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find one high-signal arXiv paper on LLM memory.")
    parser.add_argument("--days", type=int, default=7, help="Lookback window by published date.")
    parser.add_argument("--max-results", type=int, default=12, help="Max results per query.")
    parser.add_argument("--sleep", type=float, default=3.1, help="Delay between arXiv API calls.")
    parser.add_argument("--min-score", type=int, default=7, help="Minimum score required to push.")
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--state-out", type=Path, default=DEFAULT_STATE_OUT)
    parser.add_argument("--stdout-only", action="store_true", help="Do not write output files.")
    return parser.parse_args()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def request_arxiv(query: str, max_results: int) -> bytes:
    params = {
        "search_query": query,
        "start": "0",
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def text_of(parent: ET.Element, path: str) -> str:
    found = parent.find(path, NS)
    return normalize(found.text if found is not None else "")


def parse_feed(xml_bytes: bytes) -> list[Paper]:
    root = ET.fromstring(xml_bytes)
    papers: list[Paper] = []
    for entry in root.findall("a:entry", NS):
        raw_id = text_of(entry, "a:id").split("/abs/")[-1]
        title = text_of(entry, "a:title")
        summary = text_of(entry, "a:summary")
        authors = [text_of(a, "a:name") for a in entry.findall("a:author", NS)]
        categories = [c.get("term", "") for c in entry.findall("a:category", NS)]
        published = text_of(entry, "a:published")
        updated = text_of(entry, "a:updated")
        pdf_url = f"https://arxiv.org/pdf/{raw_id}"
        for link in entry.findall("a:link", NS):
            if link.get("title") == "pdf" and link.get("href"):
                pdf_url = link.get("href", pdf_url)
        papers.append(
            Paper(
                arxiv_id=raw_id,
                title=title,
                authors=[a for a in authors if a],
                summary=summary,
                published=published[:10],
                updated=updated[:10],
                categories=[c for c in categories if c],
                abs_url=f"https://arxiv.org/abs/{raw_id}",
                pdf_url=pdf_url,
            )
        )
    return papers


def within_days(paper: Paper, days: int, today: datetime) -> bool:
    if not paper.published:
        return True
    try:
        published = datetime.fromisoformat(paper.published).replace(tzinfo=UTC)
    except ValueError:
        return True
    return published >= today - timedelta(days=days)


def score_paper(paper: Paper) -> Paper:
    haystack = f"{paper.title}\n{paper.summary}".lower()
    score = 0
    reasons: list[str] = []
    penalties: list[str] = []
    for pattern, weight in POSITIVE_PATTERNS:
        if re.search(pattern, haystack, flags=re.IGNORECASE):
            score += weight
            reasons.append(pattern)
    for pattern, weight in NEGATIVE_PATTERNS:
        if re.search(pattern, haystack, flags=re.IGNORECASE):
            score -= weight
            penalties.append(pattern)
    if any(cat in {"cs.CL", "cs.AI", "cs.LG"} for cat in paper.categories):
        score += 1
        reasons.append("cs.CL/cs.AI/cs.LG")
    paper.score = score
    paper.reasons = reasons
    paper.penalties = penalties
    return paper


def discover(max_results: int, days: int, sleep_seconds: float) -> tuple[str, list[Paper]]:
    seen: dict[str, Paper] = {}
    today = datetime.now(UTC)
    for index, query in enumerate(QUERIES):
        try:
            papers = parse_feed(request_arxiv(query, max_results))
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                return "skipped_rate_limited", []
            raise
        except urllib.error.URLError as exc:
            if "429" in str(exc):
                return "skipped_rate_limited", []
            raise
        for paper in papers:
            if within_days(paper, days, today):
                seen.setdefault(paper.arxiv_id, paper)
        if index != len(QUERIES) - 1:
            time.sleep(sleep_seconds)
    scored = [score_paper(paper) for paper in seen.values()]
    scored.sort(key=lambda p: (p.score, p.published, p.updated), reverse=True)
    return "ok", scored


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"sent_ids": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"sent_ids": []}
    if not isinstance(data, dict) or not isinstance(data.get("sent_ids"), list):
        return {"sent_ids": []}
    return data


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def select_paper(candidates: list[Paper], min_score: int, sent_ids: set[str]) -> tuple[Paper | None, str]:
    for paper in candidates:
        if paper.score < min_score:
            continue
        if paper.arxiv_id in sent_ids:
            continue
        return paper, "selected"
    if any(p.score >= min_score and p.arxiv_id in sent_ids for p in candidates):
        return None, "no_new_high_confidence"
    return None, "no_high_confidence"


def render_markdown(status: str, selected: Paper | None, candidates: list[Paper], selection_status: str) -> str:
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    lines = ["📄 arXiv LLM Memory Daily", f"日期：{date}", ""]
    if status == "skipped_rate_limited":
        lines.append("arXiv API 当前命中 rate limit，本轮静默跳过。")
    elif selection_status == "no_new_high_confidence":
        lines.append("今日无新的高置信 LLM memory 论文命中；候选高分论文此前已推送过。")
    elif selected is None:
        lines.append("今日无高置信 LLM memory 论文命中。")
        if candidates:
            best = candidates[0]
            lines.append("")
            lines.append(f"最接近候选：{best.title}（score={best.score}，未过阈值）")
    else:
        lines.extend(
            [
                selected.title,
                f"Authors：{', '.join(selected.authors[:6])}",
                f"arXiv：{selected.arxiv_id}",
                f"Published：{selected.published}",
                "",
                "为什么值得看：",
                selected.summary,
                "",
                "相关性判断：",
                f"score={selected.score}；命中 LLM memory / context / RAG 相关信号：{len(selected.reasons or [])}；噪声惩罚：{len(selected.penalties or [])}。",
                "",
                "链接：",
                f"abs: {selected.abs_url}",
                f"pdf: {selected.pdf_url}",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    status, candidates = discover(args.max_results, args.days, args.sleep)
    state = load_state(args.state_out)
    sent_ids = set(str(item) for item in state.get("sent_ids", []))
    selected, selection_status = (
        select_paper(candidates, args.min_score, sent_ids) if status == "ok" else (None, status)
    )
    markdown = render_markdown(status, selected, candidates, selection_status)
    payload = {
        "status": status,
        "selection_status": selection_status,
        "generated_at": datetime.now(UTC).isoformat(),
        "selected": asdict(selected) if selected else None,
        "candidate_count": len(candidates),
        "candidates": [asdict(p) for p in candidates[:10]],
        "queries": QUERIES,
        "min_score": args.min_score,
    }
    if not args.stdout_only:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(markdown, encoding="utf-8")
        args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if selected:
            sent = list(dict.fromkeys([selected.arxiv_id, *state.get("sent_ids", [])]))[:200]
            state["sent_ids"] = sent
            state["updated_at"] = datetime.now(UTC).isoformat()
            save_state(args.state_out, state)
    print(markdown)
    if status == "skipped_rate_limited":
        print("status=skipped_rate_limited", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
