#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[4].parent
DEFAULT_REPO_ROOT = WORKSPACE_ROOT / "vendor" / "BuilderPulse"
RAW_BASE_URL = "https://raw.githubusercontent.com/BuilderPulse/BuilderPulse/main"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a structured opportunity radar bundle from BuilderPulse daily markdown."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Local BuilderPulse repo root.",
    )
    parser.add_argument(
        "--language",
        choices=("zh", "en"),
        default="zh",
        help="Report language to parse.",
    )
    parser.add_argument(
        "--date",
        help="Target date in YYYY-MM-DD. Defaults to latest available report.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Optional file path to save the JSON bundle.",
    )
    return parser.parse_args()


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"(?m)^\s*---\s*$", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def find_latest_report(repo_root: Path, language: str) -> Path:
    report_dir = repo_root / language
    reports = sorted(report_dir.glob("*/*.md"))
    if not reports:
        raise FileNotFoundError(f"no BuilderPulse reports found under {report_dir}")
    return reports[-1]


def resolve_report_path(repo_root: Path, language: str, report_date: str | None) -> Path:
    if report_date:
        year = report_date[:4]
        report_path = repo_root / language / year / f"{report_date}.md"
        if not report_path.exists():
            raise FileNotFoundError(f"missing report: {report_path}")
        return report_path
    return find_latest_report(repo_root, language)


def section_body(text: str, heading: str) -> str:
    pattern = rf"^##\s+{re.escape(heading)}\n(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_headline(text: str) -> str:
    match = re.search(r"^\*\*(?:今日|Today):\s*(.+?)\*\*$", text, flags=re.MULTILINE)
    if match:
        return normalize_whitespace(match.group(1))
    intro = section_body(text, "📝 刘小排说")
    first_paragraph = intro.split("\n\n", 1)[0] if intro else ""
    return normalize_whitespace(first_paragraph)


def extract_build_idea(text: str) -> str:
    body = section_body(text, "🎯 今日 2 小时构建")
    match = re.search(r"^\*\*(.+?)\*\*\s+—\s+(.+)$", body, flags=re.MULTILINE)
    if not match:
        return ""
    name = normalize_whitespace(match.group(1))
    desc = normalize_whitespace(match.group(2))
    return f"{name} — {desc}"


def extract_top_signals(text: str) -> list[str]:
    body = section_body(text, "今日 Top 3 信号")
    body = body.split("\n---", 1)[0]
    signals: list[str] = []
    for match in re.finditer(r"^\d+\.\s+(.+?)(?=^\d+\.|\Z)", body, flags=re.MULTILINE | re.DOTALL):
        signal = normalize_whitespace(match.group(1))
        if signal:
            signals.append(signal)
    return signals


def extract_labeled_text(block: str, label: str) -> str:
    match = re.search(
        rf"\*\*{re.escape(label)}\*\*：\s*(.+?)(?=\n\*\*[^*]+?\*\*：|\Z)",
        block,
        flags=re.DOTALL,
    )
    return normalize_whitespace(match.group(1)) if match else ""


def extract_opportunity_sections(text: str) -> list[dict]:
    top_sections = ["发现机会", "技术选型", "竞争情报", "趋势判断"]
    items: list[dict] = []
    for section_name in top_sections:
        body = section_body(text, section_name)
        if not body:
            continue
        for match in re.finditer(r"^###\s+(.+?)\n(.*?)(?=^###\s+|\Z)", body, flags=re.MULTILINE | re.DOTALL):
            question = normalize_whitespace(match.group(1))
            block = match.group(2).strip()
            item = {
                "section": section_name,
                "question": question,
                "signal": extract_labeled_text(block, "🔍 信号"),
                "关键判断": extract_labeled_text(block, "关键判断"),
                "反向视角": extract_labeled_text(block, "反向视角"),
            }
            items.append(item)
    return items


def parse_report(report_path: Path, report_url: str) -> dict:
    text = report_path.read_text(encoding="utf-8")
    date = report_path.stem
    language = report_path.parts[-3]
    title_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    return {
        "source": "builderpulse",
        "repo": "BuilderPulse/BuilderPulse",
        "language": language,
        "date": date,
        "title": normalize_whitespace(title_match.group(1)) if title_match else report_path.stem,
        "headline": extract_headline(text),
        "build_idea": extract_build_idea(text),
        "report_url": report_url,
        "local_path": str(report_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_signals": extract_top_signals(text),
        "opportunity_sections": extract_opportunity_sections(text),
    }


def main() -> int:
    args = parse_args()
    report_path = resolve_report_path(args.repo_root, args.language, args.date)
    relative_path = report_path.relative_to(args.repo_root).as_posix()
    report_url = f"{RAW_BASE_URL}/{relative_path}"
    payload = parse_report(report_path, report_url)
    output = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
