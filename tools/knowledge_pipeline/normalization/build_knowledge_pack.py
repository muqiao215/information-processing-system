#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
NORMALIZATION_DIR = Path(__file__).resolve().parent
if str(NORMALIZATION_DIR) not in sys.path:
    sys.path.insert(0, str(NORMALIZATION_DIR))

from preprocess_sources import apply_preprocessing
from tools.knowledge_pipeline.acquisition.models import (
    RunLedger,
    canonicalize_url,
    stable_item_id as acq_stable_item_id,
)


def resolve_workspace_root(repo_root: Path) -> Path:
    if repo_root.parent.name == "repos":
        return repo_root.parent.parent
    return repo_root.parent


WORKSPACE = Path(os.environ.get("WORKSPACE_ROOT", resolve_workspace_root(REPO_ROOT)))
OUTPUT_ROOT = WORKSPACE / "output_to_user"
PIPELINE_ROOT = OUTPUT_ROOT / "information_pipeline" / "bundles"
PREPROCESS_CACHE_ROOT = OUTPUT_ROOT / "information_pipeline" / "preprocessed"
FOLLOW_BUILDERS_MANIFEST = OUTPUT_ROOT / "ai_builders_digest_sources_latest.json"
BUILDERPULSE_MANIFEST = OUTPUT_ROOT / "builderpulse_opportunity_radar_sources_latest.json"
ARXIV_MANIFEST = OUTPUT_ROOT / "arxiv_llm_memory_discovery_latest.json"
SCHEMA_VERSION = "2026-04-19.v2"
DEFAULT_USER_TIMEZONE = os.environ.get("USER_TIMEZONE", "Asia/Shanghai")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a canonical multi-source knowledge_pack for downstream digestion."
    )
    parser.add_argument(
        "--follow-builders",
        type=Path,
        default=FOLLOW_BUILDERS_MANIFEST,
        help="Path to the follow-builders selected sources manifest.",
    )
    parser.add_argument(
        "--builderpulse",
        type=Path,
        default=BUILDERPULSE_MANIFEST,
        help="Path to the BuilderPulse opportunity radar manifest.",
    )
    parser.add_argument(
        "--arxiv",
        type=Path,
        default=ARXIV_MANIFEST,
        help="Path to the arXiv LLM memory discovery manifest.",
    )
    parser.add_argument(
        "--ledgers",
        type=Path,
        default=None,
        help="Path to an acquisition ledger JSON file or directory of ledger JSONs.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=OUTPUT_ROOT,
        help="Root output directory for latest aliases.",
    )
    parser.add_argument(
        "--pipeline-root",
        type=Path,
        default=PIPELINE_ROOT,
        help="Date-partitioned bundle root.",
    )
    parser.add_argument(
        "--preprocess-cache-root",
        type=Path,
        default=PREPROCESS_CACHE_ROOT,
        help="Root directory for NotebookLM-ready local markdown/text cache.",
    )
    parser.add_argument(
        "--no-preprocess",
        action="store_true",
        help="Disable phase-2 local text preprocessing and keep URL-first targets.",
    )
    return parser.parse_args()


def now_local() -> datetime:
    return datetime.now(ZoneInfo(DEFAULT_USER_TIMEZONE))


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.splitlines()]
    collapsed = "\n".join(line for line in lines if line)
    return collapsed.strip()


def clip_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def stable_item_id(
    source_id: str,
    title: str,
    url: str | None,
    canonical_url: str | None = None,
) -> str:
    effective_url = canonical_url or canonicalize_url(url)
    if effective_url:
        seed = f"url:{effective_url}"
    else:
        seed = f"title:{title.strip().lower()}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    prefix = source_id if source_id else "item"
    return f"{prefix}:{digest}"


def render_item_fallback(item: dict[str, Any]) -> str:
    lines = [f"## {item['title']}", ""]
    lines.append(f"- source_id: {item['source_id']}")
    lines.append(f"- source_type: {item['source_type']}")
    lines.append(f"- source_of_truth: {item['source_of_truth']}")
    if item.get("url"):
        lines.append(f"- url: {item['url']}")
    if item.get("freshness", {}).get("published_at"):
        lines.append(f"- published_at: {item['freshness']['published_at']}")
    lines.append(f"- selected_reason: {item.get('selected_reason', '')}")
    if item.get("tags"):
        lines.append(f"- tags: {', '.join(item['tags'])}")
    if item.get("local_text_path"):
        lines.append(f"- local_text_path: {item['local_text_path']}")
    if item.get("preprocess"):
        preprocess = item["preprocess"]
        lines.append(f"- preprocess_status: {preprocess.get('status')}")
        if preprocess.get("method"):
            lines.append(f"- preprocess_method: {preprocess.get('method')}")

    # Citations & Provenance traceability
    meta = item.get("metadata", {})
    if meta.get("observed_sources") and len(meta["observed_sources"]) > 1:
        lines.append(f"- observed_sources: {', '.join(meta['observed_sources'])}")
    if meta.get("aliases"):
        lines.append(f"- aliases: {', '.join(meta['aliases'])}")
    if meta.get("acquisition_recipe"):
        lines.append(f"- acquisition_recipe: {meta['acquisition_recipe']}")
    if meta.get("acquisition_adapter"):
        lines.append(f"- acquisition_adapter: {meta['acquisition_adapter']}")
    if meta.get("run_id"):
        lines.append(f"- run_id: {meta['run_id']}")

    lines.extend(["", "### Summary", "", item.get("summary") or "(empty)", ""])
    if item.get("raw_text"):
        lines.extend(["### Raw Text", "", item["raw_text"], ""])
    return "\n".join(lines).strip()


def build_follow_builders_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    generated_at = manifest.get("generatedAt")
    for source in manifest.get("selectedSources", []):
        url = source.get("url")
        canon_url = canonicalize_url(url)
        title = clean_text(source.get("title") or source.get("originalTitle") or url or "Untitled")
        summary = clean_text(source.get("summary"))
        raw_text = clean_text(source.get("originalText"))
        sections = [clean_text(section) for section in source.get("sections", []) if clean_text(section)]
        selected_reason = "Selected for sections: " + ", ".join(sections) if sections else "Selected by follow-builders ranking."
        tags = ["follow-builders", clean_text(source.get("type") or "unknown")]
        tags.extend(sections)
        metadata = {
            "author": source.get("author"),
            "handle": source.get("handle"),
            "origin_source": source.get("source"),
            "sections": sections,
            "publishedAt": source.get("publishedAt"),
            "originalTitle": source.get("originalTitle"),
            "canonical_url": canon_url,
            "observed_sources": ["follow-builders"],
            "aliases": [url] if url and url != canon_url else [],
            "citations": [
                {
                    "source_id": "follow-builders",
                    "title": title,
                    "url": url,
                    "canonical_url": canon_url,
                    "published_at": source.get("publishedAt"),
                }
            ],
        }
        item = {
            "item_id": stable_item_id("follow-builders", title, url, canonical_url=canon_url),
            "source_id": "follow-builders",
            "source_type": clean_text(source.get("type") or "web_item"),
            "source_of_truth": canon_url or url or title,
            "access_path": "cron_tasks/ai-builders-digest-5briefs/scripts/build_digest_outputs.py",
            "url": canon_url or url,
            "title": title,
            "summary": summary or clip_text(raw_text, 320),
            "raw_text": raw_text or summary,
            "selected_reason": selected_reason,
            "tags": sorted({tag for tag in tags if tag}),
            "freshness": {
                "published_at": source.get("publishedAt"),
                "generated_at": generated_at,
            },
            "content_type": "url",
            "import_targets": [{"kind": "url", "value": canon_url or url}] if (canon_url or url) else [],
            "import_policy": {
                "preferred": "url",
                "fallback": "markdown",
            },
            "fallback_content": "",
            "preprocess": {
                "status": "pending",
                "method": None,
                "local_text_path": None,
                "source_url": canon_url or url,
                "content_length": len(raw_text or summary or ""),
                "attempted_methods": [],
                "notes": ["manifest_loaded"],
                "generated_at": generated_at,
            },
            "metadata": metadata,
        }
        item["fallback_content"] = render_item_fallback(item)
        items.append(item)
    return items


def build_builderpulse_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    report = manifest.get("report", {})
    report_url = report.get("report_url")
    canon_report_url = canonicalize_url(report_url)
    report_date = report.get("date")
    report_generated_at = report.get("generated_at")
    items: list[dict[str, Any]] = []
    for section in manifest.get("selected_sections", []):
        section_name = clean_text(section.get("section"))
        for entry in section.get("items", []):
            title = clean_text(entry.get("question") or section_name or "BuilderPulse item")
            signal = clean_text(entry.get("signal"))
            judgment = clean_text(entry.get("key_judgment"))
            contrarian = clean_text(entry.get("contrarian_view"))
            raw_parts = [part for part in [signal, judgment, contrarian] if part]
            raw_text = "\n\n".join(raw_parts)
            summary = judgment or signal or clip_text(raw_text, 280)
            selected_reason = f"Selected from BuilderPulse section: {section_name}"
            tags = ["builderpulse", "opportunity-radar"]
            if section_name:
                tags.append(section_name)
            item = {
                "item_id": stable_item_id("builderpulse-opportunity-radar", title, report_url or title, canonical_url=canon_report_url),
                "source_id": "builderpulse-opportunity-radar",
                "source_type": "repo_archive_markdown",
                "source_of_truth": canon_report_url or report_url or f"BuilderPulse report {report_date}",
                "access_path": "cron_tasks/daily-builderpulse-opportunity-radar/scripts/build_builderpulse_radar.py",
                "url": canon_report_url or report_url,
                "title": title,
                "summary": summary,
                "raw_text": raw_text,
                "selected_reason": selected_reason,
                "tags": sorted({tag for tag in tags if tag}),
                "freshness": {
                    "published_at": report_date,
                    "generated_at": report_generated_at or manifest.get("generated_at"),
                },
                "content_type": "repo_archive_markdown",
                "import_targets": [{"kind": "url", "value": canon_report_url or report_url}] if (canon_report_url or report_url) else [],
                "import_policy": {
                    "preferred": "url",
                    "fallback": "markdown",
                },
                "fallback_content": "",
                "preprocess": {
                    "status": "pending",
                    "method": None,
                    "local_text_path": None,
                    "source_url": canon_report_url or report_url,
                    "content_length": len(raw_text),
                    "attempted_methods": [],
                    "notes": ["manifest_loaded"],
                    "generated_at": report_generated_at or manifest.get("generated_at"),
                },
                "metadata": {
                    "section": section_name,
                    "signal": signal,
                    "key_judgment": judgment,
                    "contrarian_view": contrarian,
                    "report_title": report.get("title"),
                    "report_date": report_date,
                    "local_path": report.get("local_path"),
                    "canonical_url": canon_report_url,
                    "observed_sources": ["builderpulse-opportunity-radar"],
                    "aliases": [report_url] if report_url and report_url != canon_report_url else [],
                    "citations": [
                        {
                            "source_id": "builderpulse-opportunity-radar",
                            "title": title,
                            "url": report_url,
                            "canonical_url": canon_report_url,
                            "published_at": report_date,
                        }
                    ],
                },
            }
            item["fallback_content"] = render_item_fallback(item)
            items.append(item)
    return items


def build_arxiv_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    selected = manifest.get("selected")
    if not selected:
        return []
    title = clean_text(selected.get("title") or "arXiv memory paper")
    abs_url = selected.get("abs_url")
    pdf_url = selected.get("pdf_url")
    canon_url = canonicalize_url(abs_url or pdf_url)
    reasons = [clean_text(reason) for reason in selected.get("reasons", []) if clean_text(reason)]
    summary = clean_text(selected.get("summary"))
    tags = ["arxiv", "llm-memory"]
    tags.extend(clean_text(category) for category in selected.get("categories", []) if clean_text(category))
    import_targets = []
    if canon_url:
        import_targets.append({"kind": "url", "value": canon_url})
    if pdf_url and pdf_url != canon_url:
        import_targets.append({"kind": "url", "value": pdf_url})
    if abs_url and abs_url != canon_url:
        import_targets.append({"kind": "url", "value": abs_url})
    item = {
        "item_id": stable_item_id("arxiv-llm-memory-discovery", title, abs_url or pdf_url, canonical_url=canon_url),
        "source_id": "arxiv-llm-memory-discovery",
        "source_type": "arxiv_paper",
        "source_of_truth": canon_url or abs_url or pdf_url or title,
        "access_path": "skills/arxiv-llm-memory-discovery/scripts/discover_llm_memory_paper.py",
        "url": canon_url or abs_url or pdf_url,
        "title": title,
        "summary": summary,
        "raw_text": summary,
        "selected_reason": "; ".join(reasons) if reasons else "Selected by arXiv memory discovery scoring.",
        "tags": sorted({tag for tag in tags if tag}),
        "freshness": {
            "published_at": selected.get("published"),
            "generated_at": manifest.get("generated_at"),
        },
        "content_type": "paper_url",
        "import_targets": import_targets,
        "import_policy": {
            "preferred": "pdf_url" if pdf_url else "abs_url",
            "fallback": "markdown",
        },
        "fallback_content": "",
        "preprocess": {
            "status": "pending",
            "method": None,
            "local_text_path": None,
            "source_url": canon_url or abs_url or pdf_url,
            "content_length": len(summary or ""),
            "attempted_methods": [],
            "notes": ["manifest_loaded"],
            "generated_at": manifest.get("generated_at"),
        },
        "metadata": {
            "arxiv_id": selected.get("arxiv_id"),
            "authors": selected.get("authors", []),
            "categories": selected.get("categories", []),
            "score": selected.get("score"),
            "reasons": reasons,
            "penalties": selected.get("penalties", []),
            "canonical_url": canon_url,
            "observed_sources": ["arxiv-llm-memory-discovery"],
            "aliases": [u for u in [abs_url, pdf_url] if u and u != canon_url],
            "citations": [
                {
                    "source_id": "arxiv-llm-memory-discovery",
                    "title": title,
                    "url": abs_url or pdf_url,
                    "canonical_url": canon_url,
                    "published_at": selected.get("published"),
                }
            ],
        },
    }
    item["fallback_content"] = render_item_fallback(item)
    return [item]


def build_acquisition_items(ledgers: list[dict[str, Any] | RunLedger]) -> list[dict[str, Any]]:
    """Convert acquisition run ledgers and promoted items into knowledge_pack candidates."""
    items: list[dict[str, Any]] = []
    for ledger_entry in ledgers:
        if isinstance(ledger_entry, dict):
            ledger_data = ledger_entry
            promoted_list = ledger_data.get("promoted_items", [])
            recipe_id = ledger_data.get("recipe_id", "unknown_recipe")
            run_id = ledger_data.get("run_id", "unknown_run")
            task_data = ledger_data.get("task", {})
            generated_at = ledger_data.get("generated_at")
        else:
            ledger_data = ledger_entry.to_dict()
            promoted_list = [p.to_dict() for p in ledger_entry.promoted_items]
            recipe_id = ledger_entry.recipe_id
            run_id = ledger_entry.run_id
            task_data = ledger_entry.task.to_dict()
            generated_at = ledger_entry.generated_at

        for promoted in promoted_list:
            candidate = promoted.get("knowledge_pack_candidate") or promoted
            url = candidate.get("url")
            canon_url = candidate.get("canonical_url") or canonicalize_url(url)
            title = clean_text(candidate.get("title") or url or "Acquired item")
            raw_text = clean_text(candidate.get("raw_text") or candidate.get("content") or "")
            summary = clean_text(candidate.get("summary") or clip_text(raw_text, 320))
            source_type = clean_text(candidate.get("source_type") or "webpage")
            source_id = (
                task_data.get("source_id")
                or candidate.get("metadata", {}).get("source_id")
                or "acquisition-orchestrator"
            )
            adapter = candidate.get("metadata", {}).get("acquisition_adapter") or promoted.get("adapter", "unknown")

            item_id = stable_item_id(source_type, title, url, canonical_url=canon_url)
            tags = ["acquisition", source_type]
            if canon_url:
                tags.append(clean_text(urlparse(canon_url).netloc.removeprefix("www.")))

            aliases = [url] if url and url != canon_url else []
            metadata = {
                **candidate.get("metadata", {}),
                "acquisition_recipe": recipe_id,
                "acquisition_adapter": adapter,
                "run_id": run_id,
                "canonical_url": canon_url,
                "observed_sources": [source_id],
                "aliases": aliases,
                "citations": [
                    {
                        "source_id": source_id,
                        "title": title,
                        "url": url,
                        "canonical_url": canon_url,
                        "run_id": run_id,
                    }
                ],
            }

            item = {
                "item_id": item_id,
                "source_id": source_id,
                "source_type": source_type,
                "source_of_truth": canon_url or url or title,
                "access_path": "tools/knowledge_pipeline/acquisition/orchestrator.py",
                "url": canon_url or url,
                "title": title,
                "summary": summary,
                "raw_text": raw_text,
                "selected_reason": f"Acquired via recipe: {recipe_id} using adapter: {adapter}",
                "tags": sorted({tag for tag in tags if tag}),
                "freshness": {
                    "published_at": None,
                    "generated_at": generated_at,
                },
                "content_type": "markdown",
                "import_targets": [{"kind": "url", "value": canon_url or url}] if (canon_url or url) else [],
                "import_policy": {
                    "preferred": "local_markdown",
                    "fallback": "url_then_pack_markdown",
                },
                "fallback_content": "",
                "preprocess": {
                    "status": "ready",
                    "method": "acquisition_adapter",
                    "local_text_path": None,
                    "source_url": canon_url or url,
                    "content_length": len(raw_text),
                    "attempted_methods": [{"method": adapter, "ok": True, "detail": "acquired"}],
                    "notes": ["promoted_from_acquisition_ledger"],
                    "generated_at": generated_at,
                },
                "metadata": metadata,
            }
            item["fallback_content"] = render_item_fallback(item)
            items.append(item)
    return items


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate items across sources using canonical URLs or normalized titles."""
    deduped: dict[str, dict[str, Any]] = {}
    for item in items:
        url = item.get("url")
        canon_url = canonicalize_url(url)
        if canon_url:
            key = f"url::{canon_url}"
        elif item.get("title"):
            key = f"title::{clean_text(item['title']).lower()}"
        else:
            key = f"id::{item.get('item_id')}"

        if key not in deduped:
            meta = item.setdefault("metadata", {})
            meta.setdefault("observed_sources", [item["source_id"]])
            meta.setdefault("aliases", [])
            meta.setdefault("citations", [
                {
                    "source_id": item["source_id"],
                    "title": item["title"],
                    "url": url,
                    "canonical_url": canon_url,
                    "published_at": item.get("freshness", {}).get("published_at"),
                }
            ])
            deduped[key] = item
            continue

        existing = deduped[key]
        existing_meta = existing.setdefault("metadata", {})
        item_meta = item.get("metadata", {})

        # Merge tags
        existing["tags"] = sorted(set(existing.get("tags", [])) | set(item.get("tags", [])))

        # Merge selected reasons
        if item.get("selected_reason") and item["selected_reason"] not in existing.get("selected_reason", ""):
            existing["selected_reason"] = f"{existing.get('selected_reason', '')} | {item['selected_reason']}".strip(" |")

        # Merge raw text
        if item.get("raw_text") and item["raw_text"] not in existing.get("raw_text", ""):
            existing["raw_text"] = clean_text(existing.get("raw_text", "") + "\n\n" + item["raw_text"])

        # Pick longer / more informative summary
        if item.get("summary") and len(item["summary"]) > len(existing.get("summary", "")):
            existing["summary"] = item["summary"]

        # Track observed sources
        observed = existing_meta.setdefault("observed_sources", [existing["source_id"]])
        if item["source_id"] not in observed:
            observed.append(item["source_id"])

        # Track aliases
        aliases = existing_meta.setdefault("aliases", [])
        if url and url != existing.get("url") and url not in aliases:
            aliases.append(url)
        for a in item_meta.get("aliases", []):
            if a != existing.get("url") and a not in aliases:
                aliases.append(a)

        # Track citations
        citations = existing_meta.setdefault("citations", [])
        citation_entry = {
            "source_id": item["source_id"],
            "title": item["title"],
            "url": url,
            "canonical_url": canon_url,
            "published_at": item.get("freshness", {}).get("published_at"),
        }
        if citation_entry not in citations:
            citations.append(citation_entry)

        # Merge provenance
        if "provenance" in item_meta:
            prov_list = existing_meta.setdefault("provenance", [])
            if item_meta["provenance"] not in prov_list:
                prov_list.append(item_meta["provenance"])

        existing["fallback_content"] = render_item_fallback(existing)
    return list(deduped.values())


def build_fallback_markdown(pack: dict[str, Any]) -> str:
    lines = [
        "# Knowledge Pack",
        "",
        f"pack_id: {pack['pack_id']}",
        f"date: {pack['date']}",
        f"generated_at: {pack['generated_at']}",
        f"item_count: {pack['item_count']}",
        "",
    ]
    for item in pack["items"]:
        lines.append(item["fallback_content"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def ensure_pack_shape(pack: dict[str, Any]) -> None:
    required_top = {
        "schema_version",
        "pack_id",
        "date",
        "generated_at",
        "item_count",
        "items",
        "input_manifests",
        "preprocessing_summary",
        "notes",
    }
    missing = sorted(required_top - set(pack))
    if missing:
        raise ValueError(f"knowledge_pack missing top-level keys: {missing}")
    for index, item in enumerate(pack["items"], start=1):
        for key in (
            "item_id",
            "source_id",
            "source_type",
            "source_of_truth",
            "access_path",
            "title",
            "summary",
            "raw_text",
            "selected_reason",
            "tags",
            "freshness",
            "content_type",
            "import_targets",
            "import_policy",
            "fallback_content",
            "preprocess",
            "metadata",
        ):
            if key not in item:
                raise ValueError(f"knowledge_pack item #{index} missing key: {key}")


def manifest_status(path: Path | str, payload: dict[str, Any] | None, notes: list[str]) -> dict[str, Any]:
    p = Path(path) if isinstance(path, (str, Path)) else None
    exists = p.exists() if p else True
    entry: dict[str, Any] = {"path": str(path), "exists": exists, "notes": notes}
    if not payload:
        return entry
    if "status" in payload:
        entry["status"] = payload.get("status")
    if "selection_status" in payload:
        entry["selection_status"] = payload.get("selection_status")
    if "selectedSources" in payload:
        entry["item_count"] = len(payload.get("selectedSources", []))
    elif "selected_sections" in payload:
        entry["item_count"] = sum(len(section.get("items", [])) for section in payload.get("selected_sections", []))
    elif payload.get("selected"):
        entry["item_count"] = 1
    elif "item_count" in payload:
        entry["item_count"] = payload["item_count"]
    return entry


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    now = now_local()
    date_str = now.strftime("%Y-%m-%d")
    date_compact = now.strftime("%Y%m%d")

    follow_payload = load_json(args.follow_builders)
    builderpulse_payload = load_json(args.builderpulse)
    arxiv_payload = load_json(args.arxiv)

    notes: list[str] = []
    fb_notes: list[str] = []
    bp_notes: list[str] = []
    ax_notes: list[str] = []
    ledger_notes: list[str] = []
    items: list[dict[str, Any]] = []

    if follow_payload:
        items.extend(build_follow_builders_items(follow_payload))
    else:
        fb_notes.append("follow-builders manifest missing")

    if builderpulse_payload:
        items.extend(build_builderpulse_items(builderpulse_payload))
    else:
        bp_notes.append("builderpulse manifest missing")

    if arxiv_payload:
        if arxiv_payload.get("selected"):
            items.extend(build_arxiv_items(arxiv_payload))
        else:
            ax_notes.append("arxiv manifest present but no selected paper")
    else:
        ax_notes.append("arxiv manifest missing")

    loaded_ledgers: list[dict[str, Any]] = []
    if args.ledgers:
        if args.ledgers.is_file():
            payload = load_json(args.ledgers)
            if payload:
                loaded_ledgers.append(payload)
        elif args.ledgers.is_dir():
            for f in sorted(args.ledgers.glob("*.json")):
                payload = load_json(f)
                if payload:
                    loaded_ledgers.append(payload)
        if loaded_ledgers:
            items.extend(build_acquisition_items(loaded_ledgers))
        else:
            ledger_notes.append(f"No valid ledgers found in {args.ledgers}")

    items = dedupe_items(items)
    if not items:
        raise SystemExit("No knowledge items available; all input manifests missing or empty.")

    preprocess_summary: dict[str, Any]
    if args.no_preprocess:
        generated_at = now.isoformat()
        preprocess_summary = {
            "status_counts": {"disabled": len(items)},
            "method_counts": {},
            "localized_source_types": {},
            "cache_root": None,
            "generated_at": generated_at,
            "notes": ["Phase-2 preprocessing disabled by --no-preprocess."],
        }
        for item in items:
            item["preprocess"] = {
                "status": "disabled",
                "method": None,
                "local_text_path": None,
                "source_url": item.get("url"),
                "content_length": 0,
                "attempted_methods": [],
                "notes": ["disabled_by_cli"],
                "generated_at": generated_at,
            }
            item["local_text_path"] = None
    else:
        preprocess_day_dir = args.preprocess_cache_root / date_str
        preprocess_summary = apply_preprocessing(items, preprocess_day_dir, generated_at=now.isoformat())

    for item in items:
        item["fallback_content"] = render_item_fallback(item)

    source_counts = Counter(item["source_id"] for item in items)
    input_manifests = {
        "follow-builders": manifest_status(args.follow_builders, follow_payload, fb_notes),
        "builderpulse-opportunity-radar": manifest_status(args.builderpulse, builderpulse_payload, bp_notes),
        "arxiv-llm-memory-discovery": manifest_status(args.arxiv, arxiv_payload, ax_notes),
    }
    if args.ledgers:
        input_manifests["acquisition-orchestrator"] = manifest_status(
            args.ledgers,
            {"status": "loaded", "item_count": len(loaded_ledgers)},
            ledger_notes,
        )

    pack: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "pack_id": f"knowledge-pack-{date_str}",
        "date": date_str,
        "run_date": date_str,
        "data_date": date_str,
        "timezone": DEFAULT_USER_TIMEZONE,
        "artifact_date_basis": "data_date",
        "generated_at": now.isoformat(),
        "item_count": len(items),
        "source_counts": dict(source_counts),
        "input_manifests": input_manifests,
        "items": items,
        "preprocessing_summary": preprocess_summary,
        "fallback_markdown_path": None,
        "notes": notes,
    }
    fallback_markdown = build_fallback_markdown(pack)

    latest_json = args.output_root / "knowledge_pack_latest.json"
    dated_json = args.output_root / f"knowledge_pack_{date_compact}.json"
    latest_md = args.output_root / "knowledge_pack_latest.md"
    dated_md = args.output_root / f"knowledge_pack_{date_compact}.md"
    pipeline_day_dir = args.pipeline_root / date_str
    pipeline_json = pipeline_day_dir / "knowledge_pack.json"
    pipeline_md = pipeline_day_dir / "knowledge_pack.md"

    pack["fallback_markdown_path"] = str(pipeline_md)
    ensure_pack_shape(pack)

    write_json(latest_json, pack)
    write_json(dated_json, pack)
    write_json(pipeline_json, pack)
    write_text(latest_md, fallback_markdown)
    write_text(dated_md, fallback_markdown)
    write_text(pipeline_md, fallback_markdown)

    print(json.dumps(
        {
            "knowledge_pack_latest": str(latest_json),
            "knowledge_pack_dated": str(dated_json),
            "knowledge_pack_pipeline": str(pipeline_json),
            "knowledge_pack_markdown_latest": str(latest_md),
            "knowledge_pack_markdown_dated": str(dated_md),
            "knowledge_pack_markdown_pipeline": str(pipeline_md),
            "item_count": pack["item_count"],
            "source_counts": pack["source_counts"],
            "preprocessing_summary": pack["preprocessing_summary"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
