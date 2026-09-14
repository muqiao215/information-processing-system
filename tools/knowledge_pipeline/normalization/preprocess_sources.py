#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)
MAX_SOURCE_CHARS = 180_000
DEFAULT_TIMEOUT_SECONDS = 35

try:
    from tools.knowledge_pipeline.fs_utils import atomic_write_text
except ImportError:  # loaded standalone via file path without repo root on sys.path
    import os as _os

    def atomic_write_text(path, data, encoding="utf-8"):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.tmp{_os.getpid()}")
        try:
            with open(tmp, "w", encoding=encoding) as fh:
                fh.write(data)
                fh.flush()
                _os.fsync(fh.fileno())
            _os.replace(tmp, path)
        except BaseException:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise
        return path


@dataclass
class FetchAttempt:
    method: str
    ok: bool
    detail: str = ""


@dataclass
class PreprocessResult:
    status: str
    method: str | None = None
    local_text_path: str | None = None
    source_url: str | None = None
    content_length: int = 0
    attempted_methods: list[FetchAttempt] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_item_metadata(self, generated_at: str) -> dict[str, Any]:
        return {
            "status": self.status,
            "method": self.method,
            "local_text_path": self.local_text_path,
            "source_url": self.source_url,
            "content_length": self.content_length,
            "attempted_methods": [
                {"method": attempt.method, "ok": attempt.ok, "detail": attempt.detail}
                for attempt in self.attempted_methods
            ],
            "notes": self.notes,
            "generated_at": generated_at,
        }


def domain_of(url: str | None) -> str:
    if not url:
        return ""
    return urlparse(url).netloc.lower().removeprefix("www.")


def is_x_url(url: str | None) -> bool:
    domain = domain_of(url)
    return domain in {"x.com", "twitter.com", "mobile.twitter.com"}


def is_raw_github_url(url: str | None) -> bool:
    return domain_of(url) == "raw.githubusercontent.com"


def is_arxiv_url(url: str | None) -> bool:
    return domain_of(url) == "arxiv.org"


def is_pdf_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.path.lower().endswith(".pdf") or "/pdf/" in parsed.path.lower()


def should_preprocess(item: dict[str, Any]) -> tuple[bool, str]:
    url = item.get("url")
    source_type = str(item.get("source_type") or "").lower()
    content_type = str(item.get("content_type") or "").lower()
    import_values = [str(target.get("value") or "") for target in item.get("import_targets", [])]

    if source_type in {"x", "tweet", "twitter"} or is_x_url(url):
        return True, "x_single_link"
    if is_raw_github_url(url) or any(is_raw_github_url(value) for value in import_values):
        return True, "raw_github_text"
    if source_type == "arxiv_paper" or content_type == "paper_url":
        return True, "arxiv_paper"
    if is_pdf_url(url) or any(is_pdf_url(value) for value in import_values):
        return True, "pdf_document"
    return False, "not_targeted"


def clean_for_filename(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower())
    value = re.sub(r"-+", "-", value).strip("-._")
    return value[:72] or "item"


def item_cache_path(cache_dir: Path, item: dict[str, Any]) -> Path:
    seed = f"{item.get('item_id','')}\n{item.get('url','')}\n{item.get('title','')}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    slug = clean_for_filename(str(item.get("title") or item.get("item_id") or "item"))
    return cache_dir / f"{slug}-{digest}.md"


def read_url_text(url: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/markdown,text/plain,text/html,application/pdf,*/*",
            "Referer": "https://www.google.com/",
            "X-Forwarded-For": "66.249.66.1",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read(MAX_SOURCE_CHARS + 1)
        charset = response.headers.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")


def fetch_attempt(url: str, method: str) -> tuple[str | None, FetchAttempt]:
    try:
        text = read_url_text(url)
    except HTTPError as exc:
        return None, FetchAttempt(method, False, f"http_{exc.code}")
    except URLError as exc:
        return None, FetchAttempt(method, False, f"url_error:{exc.reason}")
    except TimeoutError:
        return None, FetchAttempt(method, False, "timeout")
    except Exception as exc:  # noqa: BLE001 - keep preprocessing non-fatal.
        return None, FetchAttempt(method, False, f"{type(exc).__name__}:{exc}")

    text = normalize_extracted_text(text)
    if not is_useful_text(text):
        return None, FetchAttempt(method, False, "empty_or_low_signal")
    return text, FetchAttempt(method, True, f"chars={len(text)}")


def normalize_extracted_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.splitlines()]
    collapsed: list[str] = []
    blank = False
    for line in lines:
        if not line.strip():
            if not blank:
                collapsed.append("")
            blank = True
            continue
        collapsed.append(line)
        blank = False
    return "\n".join(collapsed).strip()


def is_useful_text(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 80:
        return False
    lowered = stripped[:1200].lower()
    bad_markers = (
        '{"error"',
        "not an html page",
        "please enable javascript",
        "access denied",
        "just a moment...",
        "captcha",
    )
    return not any(marker in lowered for marker in bad_markers)


def jina_url(url: str) -> str:
    return f"https://r.jina.ai/{url}"


def defuddle_url(url: str) -> str:
    return f"https://defuddle.md/{url}"


def raw_github_blob_url(raw_url: str) -> str | None:
    parsed = urlparse(raw_url)
    if parsed.netloc.lower() != "raw.githubusercontent.com":
        return None
    parts = parsed.path.lstrip("/").split("/", 3)
    if len(parts) < 4:
        return None
    owner, repo, branch, rest = parts
    return f"https://github.com/{owner}/{repo}/blob/{branch}/{rest}"


def arxiv_pdf_url(item: dict[str, Any]) -> str | None:
    for target in item.get("import_targets", []):
        value = str(target.get("value") or "")
        if is_arxiv_url(value) and is_pdf_url(value):
            return value
    url = str(item.get("url") or "")
    if is_arxiv_url(url) and is_pdf_url(url):
        return url
    arxiv_id = item.get("metadata", {}).get("arxiv_id")
    if arxiv_id:
        return f"https://arxiv.org/pdf/{arxiv_id}"
    return None


def arxiv_abs_url(item: dict[str, Any]) -> str | None:
    for target in item.get("import_targets", []):
        value = str(target.get("value") or "")
        if is_arxiv_url(value) and "/abs/" in urlparse(value).path:
            return value
    url = str(item.get("url") or "")
    if is_arxiv_url(url) and "/abs/" in urlparse(url).path:
        return url
    arxiv_id = item.get("metadata", {}).get("arxiv_id")
    if arxiv_id:
        return f"https://arxiv.org/abs/{arxiv_id}"
    return None


def source_candidates(item: dict[str, Any], reason: str) -> list[tuple[str, str]]:
    url = str(item.get("url") or "")
    candidates: list[tuple[str, str]] = []
    if reason == "arxiv_paper":
        pdf_url = arxiv_pdf_url(item)
        abs_url = arxiv_abs_url(item)
        if pdf_url:
            candidates.append(("jina_reader_pdf", jina_url(pdf_url)))
        if abs_url:
            candidates.append(("jina_reader_abs", jina_url(abs_url)))
            candidates.append(("defuddle_abs", defuddle_url(abs_url)))
        return candidates

    if reason == "pdf_document":
        if url:
            candidates.append(("jina_reader_pdf", jina_url(url)))
        return candidates

    if reason == "raw_github_text":
        if url:
            candidates.append(("jina_reader_raw", jina_url(url)))
            candidates.append(("direct_raw", url))
            blob_url = raw_github_blob_url(url)
            if blob_url:
                candidates.append(("defuddle_github_blob", defuddle_url(blob_url)))
        return candidates

    if url:
        candidates.append(("jina_reader", jina_url(url)))
        candidates.append(("defuddle", defuddle_url(url)))
        candidates.append(("direct_browser_ua", url))
    return candidates


def fetch_best_text(item: dict[str, Any], reason: str) -> tuple[str | None, str | None, str | None, list[FetchAttempt]]:
    attempts: list[FetchAttempt] = []
    for method, candidate_url in source_candidates(item, reason):
        text, attempt = fetch_attempt(candidate_url, method)
        attempts.append(attempt)
        if text:
            return text, method, candidate_url, attempts
    return None, None, None, attempts


def manifest_fallback_text(item: dict[str, Any]) -> str:
    parts = []
    if item.get("summary"):
        parts.extend(["## Summary", "", str(item["summary"]).strip(), ""])
    if item.get("raw_text"):
        parts.extend(["## Manifest Raw Text", "", str(item["raw_text"]).strip(), ""])
    if item.get("fallback_content"):
        parts.extend(["## Existing Fallback", "", str(item["fallback_content"]).strip(), ""])
    return "\n".join(parts).strip()


def render_local_markdown(
    item: dict[str, Any],
    source_text: str,
    method: str,
    source_url: str | None,
    generated_at: str,
) -> str:
    title = str(item.get("title") or "Untitled").strip()
    metadata_lines = [
        f"- item_id: {item.get('item_id')}",
        f"- source_id: {item.get('source_id')}",
        f"- source_type: {item.get('source_type')}",
        f"- source_of_truth: {item.get('source_of_truth')}",
        f"- original_url: {item.get('url') or ''}",
        f"- preprocess_method: {method}",
        f"- preprocessed_at: {generated_at}",
    ]
    if source_url:
        metadata_lines.append(f"- fetched_via: {source_url}")
    published_at = item.get("freshness", {}).get("published_at")
    if published_at:
        metadata_lines.append(f"- published_at: {published_at}")
    tags = item.get("tags") or []
    if tags:
        metadata_lines.append(f"- tags: {', '.join(str(tag) for tag in tags)}")

    body = source_text[:MAX_SOURCE_CHARS].strip()
    return "\n".join(
        [
            f"# {title}",
            "",
            "## Source Metadata",
            "",
            *metadata_lines,
            "",
            "## Selected Reason",
            "",
            str(item.get("selected_reason") or "").strip() or "(empty)",
            "",
            "## NotebookLM-Ready Text",
            "",
            body or "(empty)",
            "",
        ]
    )


def localize_item(
    item: dict[str, Any],
    cache_dir: Path,
    generated_at: str,
    timeout_note: str | None = None,
) -> PreprocessResult:
    should, reason = should_preprocess(item)
    if not should:
        return PreprocessResult(status="skipped", method=None, notes=[reason])

    fetched_text, method, fetched_via, attempts = fetch_best_text(item, reason)
    status = "localized"
    notes = [reason]
    if timeout_note:
        notes.append(timeout_note)

    if not fetched_text:
        fallback_text = manifest_fallback_text(item)
        if not is_useful_text(fallback_text):
            return PreprocessResult(
                status="failed",
                method=None,
                source_url=str(item.get("url") or "") or None,
                attempted_methods=attempts,
                notes=notes + ["no_useful_reader_or_manifest_text"],
            )
        fetched_text = fallback_text
        method = "manifest_fallback_markdown"
        fetched_via = str(item.get("url") or "") or None
        status = "fallback_localized"

    output_path = item_cache_path(cache_dir, item)
    markdown = render_local_markdown(item, fetched_text, method or "unknown", fetched_via, generated_at)
    atomic_write_text(output_path, markdown)
    return PreprocessResult(
        status=status,
        method=method,
        local_text_path=str(output_path),
        source_url=fetched_via,
        content_length=len(markdown),
        attempted_methods=attempts,
        notes=notes,
    )


def apply_preprocessing(
    items: list[dict[str, Any]],
    cache_root: Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or datetime.now().astimezone().isoformat()
    cache_root.mkdir(parents=True, exist_ok=True)
    status_counts: dict[str, int] = {}
    method_counts: dict[str, int] = {}
    localized_source_types: dict[str, int] = {}

    for item in items:
        result = localize_item(item, cache_root, generated_at)
        item["preprocess"] = result.as_item_metadata(generated_at)
        item["local_text_path"] = result.local_text_path
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
        if result.method:
            method_counts[result.method] = method_counts.get(result.method, 0) + 1
        if result.local_text_path:
            localized_source_types[str(item.get("source_type") or "unknown")] = (
                localized_source_types.get(str(item.get("source_type") or "unknown"), 0) + 1
            )
            local_target = {"kind": "markdown_file", "value": result.local_text_path}
            existing_targets = [
                target
                for target in item.get("import_targets", [])
                if target.get("value") != result.local_text_path
            ]
            item["import_targets"] = [local_target] + existing_targets
            item["import_policy"] = {
                **item.get("import_policy", {}),
                "preferred": "local_markdown",
                "fallback": "url_then_pack_markdown",
            }

    summary = {
        "status_counts": dict(sorted(status_counts.items())),
        "method_counts": dict(sorted(method_counts.items())),
        "localized_source_types": dict(sorted(localized_source_types.items())),
        "cache_root": str(cache_root),
        "generated_at": generated_at,
        "notes": [
            textwrap.dedent(
                """
                Phase-2 preprocessing keeps original source URLs as source_of_truth,
                but gives NotebookLM local markdown/text import targets first.
                """
            ).strip()
        ],
    }
    return summary
