#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_REPO_ROOT = Path("/root/.ductor/workspace/vendor/BuilderPulse")
DEFAULT_MD_OUT = Path(
    "/root/.ductor/workspace/output_to_user/builderpulse_opportunity_radar_latest.md"
)
DEFAULT_JSON_OUT = Path(
    "/root/.ductor/workspace/output_to_user/builderpulse_opportunity_radar_sources_latest.json"
)
RAW_BASE_URL = "https://raw.githubusercontent.com/BuilderPulse/BuilderPulse/main"
SECTION_ORDER = ["发现机会", "技术选型", "竞争情报", "趋势判断"]
DISPLAY_LIMIT_PER_SECTION = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a standalone BuilderPulse opportunity radar brief."
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
        "--md-out",
        type=Path,
        default=DEFAULT_MD_OUT,
        help="Markdown output path.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=DEFAULT_JSON_OUT,
        help="Machine-readable manifest output path.",
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
    items: list[dict] = []
    for section_name in SECTION_ORDER:
        body = section_body(text, section_name)
        if not body:
            continue
        for match in re.finditer(r"^###\s+(.+?)\n(.*?)(?=^###\s+|\Z)", body, flags=re.MULTILINE | re.DOTALL):
            question = normalize_whitespace(match.group(1))
            block = match.group(2).strip()
            items.append(
                {
                    "section": section_name,
                    "question": question,
                    "signal": extract_labeled_text(block, "🔍 信号"),
                    "key_judgment": extract_labeled_text(block, "关键判断"),
                    "contrarian_view": extract_labeled_text(block, "反向视角"),
                }
            )
    return items


def parse_report(report_path: Path, report_url: str) -> dict:
    text = report_path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    return {
        "source": "builderpulse",
        "repo": "BuilderPulse/BuilderPulse",
        "language": report_path.parts[-3],
        "date": report_path.stem,
        "title": normalize_whitespace(title_match.group(1)) if title_match else report_path.stem,
        "headline": extract_headline(text),
        "build_idea": extract_build_idea(text),
        "report_url": report_url,
        "local_path": str(report_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_signals": extract_top_signals(text),
        "opportunity_sections": extract_opportunity_sections(text),
    }


def read_git_head(repo_root: Path) -> dict | None:
    try:
        sha = subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            text=True,
        ).strip()
        subject = subprocess.check_output(
            ["git", "-C", str(repo_root), "log", "-1", "--pretty=%s"],
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return {"commit": sha, "subject": subject}


def group_sections(items: list[dict]) -> dict[str, list[dict]]:
    grouped = {name: [] for name in SECTION_ORDER}
    for item in items:
        grouped.setdefault(item["section"], []).append(item)
    return grouped


def clip_text(text: str, max_chars: int) -> str:
    text = normalize_whitespace(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def build_manifest(report: dict, git_head: dict | None) -> dict:
    grouped = group_sections(report["opportunity_sections"])
    return {
        "source": "builderpulse",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report": report,
        "git_head": git_head,
        "selected_sections": [
            {
                "section": section,
                "count": len(grouped.get(section, [])),
                "items": grouped.get(section, []),
            }
            for section in SECTION_ORDER
            if grouped.get(section)
        ],
        "selected_opportunity_count": len(report["opportunity_sections"]),
    }


def render_opportunity_item(index: int, item: dict) -> list[str]:
    lines = [f"{index}. {item['question']}"]
    if item["signal"]:
        lines.append(f"   信号：{clip_text(item['signal'], 320)}")
    if item["key_judgment"]:
        lines.append(f"   判断：{clip_text(item['key_judgment'], 260)}")
    if item["contrarian_view"]:
        lines.append(f"   反向视角：{clip_text(item['contrarian_view'], 220)}")
    return lines


def build_markdown(
    report: dict,
    manifest: dict,
    md_out: Path = DEFAULT_MD_OUT,
    json_out: Path = DEFAULT_JSON_OUT,
) -> str:
    grouped = group_sections(report["opportunity_sections"])
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# BuilderPulse Opportunity Radar",
        "",
        f"生成时间：{generated_at}",
        f"报告日期：{report['date']}",
        f"来源仓库：{report['repo']}",
        f"原文链接：{report['report_url']}",
    ]
    if manifest.get("git_head"):
        lines.append(
            f"本地仓库版本：{manifest['git_head']['commit']} {manifest['git_head']['subject']}"
        )
    lines.extend(
        [
            "",
            "## F. 机会雷达",
            "",
            clip_text(report["headline"], 520),
            "",
        ]
    )
    if report["build_idea"]:
        lines.extend(
            [
                "### 今日 2 小时构建",
                "",
                report["build_idea"],
                "",
            ]
        )
    if report["top_signals"]:
        lines.extend(["### 今日 Top 3 信号", ""])
        for index, signal in enumerate(report["top_signals"], start=1):
            lines.append(f"{index}. {clip_text(signal, 360)}")
        lines.append("")
    for section in SECTION_ORDER:
        items = grouped.get(section, [])
        if not items:
            continue
        lines.extend([f"### {section}", ""])
        for index, item in enumerate(items[:DISPLAY_LIMIT_PER_SECTION], start=1):
            lines.extend(render_opportunity_item(index, item))
            lines.append("")
    lines.extend(
        [
            "---",
            "",
            f"markdown saved path: {md_out}",
            f"source manifest saved path: {json_out}",
            f"report date: {report['date']}",
            f"selected opportunity count: {manifest['selected_opportunity_count']}",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    report_path = resolve_report_path(args.repo_root, args.language, args.date)
    relative_path = report_path.relative_to(args.repo_root).as_posix()
    report_url = f"{RAW_BASE_URL}/{relative_path}"
    report = parse_report(report_path, report_url)
    manifest = build_manifest(report, read_git_head(args.repo_root))
    markdown = build_markdown(report, manifest, args.md_out, args.json_out)

    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.write_text(markdown, encoding="utf-8")
    args.json_out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
