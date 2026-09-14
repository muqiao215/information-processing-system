"""Invariant checks, unstable-field normalization, and JSON diffing.

`normalize_pack` masks fields that legitimately change between runs
(timestamps, run-directory-relative absolute paths). Everything else that
differs between two runs of identical inputs is a determinism bug and shows
up in `diff_json`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

UNSTABLE_KEY_MARKERS = (
    "generated_at",
    "generatedAt",
    "preprocessed_at",
)


def _looks_like_iso_timestamp(value: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value))


def _mask_unstable(value: Any, run_root: Path | None) -> Any:
    """Recursive normalize that also masks by KEY name (walks with keys)."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            normalized_item = _mask_unstable(item, run_root)
            if isinstance(normalized_item, str) and any(
                marker in key for marker in UNSTABLE_KEY_MARKERS
            ):
                out[key] = "<timestamp>"
            else:
                out[key] = normalized_item
        return out
    if isinstance(value, list):
        return [_mask_unstable(v, run_root) for v in value]
    if isinstance(value, str):
        if _looks_like_iso_timestamp(value):
            return "<timestamp>"
        if run_root is not None:
            try:
                rel = Path(value).relative_to(run_root)
                return str(Path("<run_root>") / rel)
            except (ValueError, OSError):
                pass
    return value


def normalize_pack(pack: dict[str, Any], run_root: Path | None = None) -> dict[str, Any]:
    return _mask_unstable(pack, run_root)


def diff_json(a: Any, b: Any, path: str = "$") -> list[dict[str, str]]:
    """Return a list of differing leaf paths between two JSON structures."""
    diffs: list[dict[str, str]] = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a:
                diffs.append({"path": f"{path}.{key}", "left": "<missing>", "right": _short(b[key])})
            elif key not in b:
                diffs.append({"path": f"{path}.{key}", "left": _short(a[key]), "right": "<missing>"})
            else:
                diffs.extend(diff_json(a[key], b[key], f"{path}.{key}"))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append({"path": f"{path}[len]", "left": str(len(a)), "right": str(len(b))})
        for index, (item_a, item_b) in enumerate(zip(a, b)):
            diffs.extend(diff_json(item_a, item_b, f"{path}[{index}]"))
    elif a != b:
        diffs.append({"path": path, "left": _short(a), "right": _short(b)})
    return diffs


def _short(value: Any, limit: int = 90) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return text if len(text) <= limit else text[: limit - 3] + "..."


def load_pack(run_dir: Path) -> dict[str, Any] | None:
    pack_path = run_dir / "knowledge_pack_latest.json"
    if not pack_path.exists():
        return None
    try:
        return json.loads(pack_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_ledgers(ledger_dir: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Returns ({ledger_file_name: payload}, [corrupt file names])."""
    ledgers: dict[str, dict[str, Any]] = {}
    corrupt: list[str] = []
    for path in sorted(ledger_dir.glob("*.json")):
        try:
            ledgers[path.name] = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            corrupt.append(path.name)
    return ledgers, corrupt


def ensure_pack_shape(pack: dict[str, Any]) -> list[str]:
    """Standalone mirror of build_knowledge_pack.ensure_pack_shape -> error list."""
    required_top = {
        "schema_version", "pack_id", "date", "generated_at", "item_count",
        "items", "input_manifests", "preprocessing_summary", "notes",
    }
    errors = []
    missing = sorted(required_top - set(pack))
    if missing:
        errors.append(f"pack missing top-level keys: {missing}")
    required_item = (
        "item_id", "source_id", "source_type", "source_of_truth", "access_path",
        "title", "summary", "raw_text", "selected_reason", "tags", "freshness",
        "content_type", "import_targets", "import_policy", "fallback_content",
        "preprocess", "metadata",
    )
    for index, item in enumerate(pack.get("items", []), start=1):
        for key in required_item:
            if key not in item:
                errors.append(f"item #{index} missing key: {key}")
    return errors


def check_invariants(
    run_dir: Path,
    *,
    allow_corrupt_ledgers: bool = False,
) -> dict[str, Any]:
    """Core post-recovery invariants for one completed run directory."""
    report: dict[str, Any] = {"violations": [], "notes": []}
    pack = load_pack(run_dir)
    if pack is None:
        report["violations"].append("knowledge_pack_latest.json missing or unparseable")
        return report

    report["violations"].extend(ensure_pack_shape(pack))

    items = pack.get("items", [])
    ids = [item.get("item_id") for item in items]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        report["violations"].append(f"duplicate item_ids in pack: {dupes}")
    report["item_count"] = len(items)
    report["item_ids"] = ids

    for item in items:
        meta = item.get("metadata", {})
        citations = meta.get("citations", [])
        if not citations:
            report["violations"].append(f"item {item.get('item_id')} has no citations")
        if not item.get("source_of_truth"):
            report["violations"].append(f"item {item.get('item_id')} has empty source_of_truth")
        if meta.get("canonical_url") is None and item.get("source_type") != "repo_archive_markdown":
            report["violations"].append(f"item {item.get('item_id')} has null canonical_url")

    ledgers, corrupt = load_ledgers(run_dir / "ledgers")
    report["ledger_count"] = len(ledgers)
    report["corrupt_ledgers"] = corrupt
    if corrupt and not allow_corrupt_ledgers:
        report["violations"].append(f"corrupt ledger files remain: {corrupt}")
    if len(ledgers) + len(corrupt) != 22:
        report["notes"].append(
            f"expected 22 ledger files, found {len(ledgers)} valid + {len(corrupt)} corrupt"
        )

    by_title: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_title.setdefault(item.get("title", ""), []).append(item)

    def expect_count(title: str, count: int, label: str) -> None:
        found = len(by_title.get(title, []))
        if found != count:
            report["violations"].append(
                f"{label}: expected {count} pack item(s) titled '{title}', found {found}"
            )

    expect_count("Distributed Trace Sampling at Scale", 1, "duplicate_article")
    expect_count("Agent Memory Field Guide", 2, "same_title_diff_content")
    expect_count("Vector DB Cost Playbook", 1, "same_content_diff_url")

    clash = by_title.get("Agent Memory Field Guide", [])
    if len(clash) == 2 and clash[0].get("item_id") == clash[1].get("item_id"):
        report["violations"].append("same_title_diff_content items share an item_id")

    conflict_items = [
        item for item in items
        if item.get("title") in ("MemoryBench Final Scores", "MemoryBench Results Announced")
    ]
    if len(conflict_items) == 1:
        meta = conflict_items[0].get("metadata", {})
        if len(meta.get("observed_sources", [])) < 2:
            report["violations"].append("conflicting_sources item did not record both sources")
        if len(meta.get("citations", [])) < 2:
            report["violations"].append("conflicting_sources item did not keep both citations")
    elif len(conflict_items) > 1:
        report["violations"].append(
            f"conflicting_sources not merged: {len(conflict_items)} items"
        )

    promoted_titles = {item.get("title") for item in items}
    for bad in (
        "Missing Article on Status Route",
        "Rate Limited Article Fetch",
        "Server Error Article Fetch",
        "Hanging Endpoint Article",
        "Whitespace Placeholder Article",
        "Declared Longer Than Sent Article",
    ):
        if bad in promoted_titles:
            report["violations"].append(f"failed fetch was promoted into pack: {bad}")

    return report
