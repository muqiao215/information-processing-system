from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


SCHEMA_VERSION = "2026-04-20.acquisition.v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_digest(*parts: str) -> str:
    seed = "\n".join(parts)
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def canonicalize_url(url: str | None) -> str | None:
    """Normalize and canonicalize URLs for deduplication and provenance tracking.

    Handles:
    - Protocol normalization (default https)
    - Host lowercasing and 'www.' stripping
    - Stripping trailing slashes for non-root paths
    - Removing tracking query parameters (utm_*, ref, source, fbclid, etc.)
    - Normalizing arXiv URLs (/abs/ and /pdf/ variants)
    - Normalizing GitHub raw and blob README URLs
    """
    if not url:
        return None
    url = url.strip()
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url

    scheme = "https" if parsed.scheme.lower() in ("http", "https") else parsed.scheme.lower()
    netloc = parsed.netloc.lower().removeprefix("www.")

    # Canonicalize arXiv
    if netloc == "arxiv.org":
        match = re.search(r"/(?:abs|pdf)/([0-9]+\.[0-9]+(?:v[0-9]+)?)(?:\.pdf)?", parsed.path)
        if match:
            arxiv_id = match.group(1)
            return f"https://arxiv.org/abs/{arxiv_id}"

    # Canonicalize GitHub
    if netloc == "raw.githubusercontent.com":
        parts = parsed.path.strip("/").split("/", 3)
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            if len(parts) == 4 and parts[3].lower() in ("readme.md", "readme"):
                return f"https://github.com/{owner}/{repo}"
    elif netloc == "github.com":
        parts = parsed.path.strip("/").split("/", 4)
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            if len(parts) >= 4 and parts[2] == "blob" and parts[-1].lower() in ("readme.md", "readme"):
                return f"https://github.com/{owner}/{repo}"

    # Filter out tracking query parameters
    tracking_params = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "source",
        "fbclid",
        "gclid",
        "spm",
        "from",
    }
    query_tuples = parse_qsl(parsed.query, keep_blank_values=False)
    filtered_query = [(k, v) for k, v in query_tuples if k.lower() not in tracking_params]
    filtered_query.sort(key=lambda x: x[0])
    query_str = urlencode(filtered_query) if filtered_query else ""

    # Path normalization
    path = re.sub(r"/+", "/", parsed.path)
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    if not path:
        path = "/"

    return urlunparse((scheme, netloc, path, "", query_str, ""))


def stable_item_id(
    source_type: str,
    title: str,
    url: str | None = None,
    canonical_url: str | None = None,
) -> str:
    """Generate a deterministic, source-independent item ID."""
    effective_url = canonical_url or canonicalize_url(url)
    if effective_url:
        seed = f"url:{effective_url}"
    else:
        seed = f"title:{title.strip().lower()}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"item:{digest}"


@dataclass(frozen=True)
class AcquisitionTask:
    task_id: str
    source_type: str
    task_kind: str
    url: str | None = None
    title: str | None = None
    source_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        task_id: str | None = None,
        title: str | None = None,
        source_type: str = "webpage",
        task_kind: str = "fetch",
        source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "AcquisitionTask":
        canon = canonicalize_url(url)
        generated_task_id = task_id or f"acq:{stable_digest(canon or url, title or '')}"
        return cls(
            task_id=generated_task_id,
            source_type=source_type,
            task_kind=task_kind,
            url=url,
            title=title,
            source_id=source_id,
            metadata=metadata or {},
        )

    @property
    def canonical_url(self) -> str | None:
        return canonicalize_url(self.url)

    @property
    def domain(self) -> str:
        if not self.url:
            return ""
        return urlparse(self.url).netloc.lower().removeprefix("www.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "task_kind": self.task_kind,
            "url": self.url,
            "canonical_url": self.canonical_url,
            "title": self.title,
            "domain": self.domain,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AcquisitionTask":
        return cls(
            task_id=data["task_id"],
            source_type=data.get("source_type", "webpage"),
            task_kind=data.get("task_kind", "fetch"),
            url=data.get("url"),
            title=data.get("title"),
            source_id=data.get("source_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass(frozen=True)
class SourceCandidate:
    candidate_id: str
    url: str
    source_type: str
    title: str | None = None
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_task(cls, task: AcquisitionTask, *, priority: int = 0) -> "SourceCandidate":
        if not task.url:
            raise ValueError("AcquisitionTask.url is required for URL source candidates")
        canon = task.canonical_url or task.url
        return cls(
            candidate_id=f"candidate:{stable_digest(task.task_id, canon)}",
            url=task.url,
            source_type=task.source_type,
            title=task.title,
            priority=priority,
            metadata={"task_id": task.task_id, "canonical_url": canon},
        )

    @property
    def canonical_url(self) -> str | None:
        return canonicalize_url(self.url)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "url": self.url,
            "canonical_url": self.canonical_url,
            "source_type": self.source_type,
            "title": self.title,
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceCandidate":
        return cls(
            candidate_id=data["candidate_id"],
            url=data["url"],
            source_type=data.get("source_type", "webpage"),
            title=data.get("title"),
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass(frozen=True)
class Attempt:
    adapter: str
    status: str
    ok: bool = False
    candidate_id: str | None = None
    candidate_url: str | None = None
    request_url: str | None = None
    detail: str = ""
    content_length: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "status": self.status,
            "ok": self.ok,
            "candidate_id": self.candidate_id,
            "candidate_url": self.candidate_url,
            "request_url": self.request_url,
            "detail": self.detail,
            "content_length": self.content_length,
            "metadata": self.metadata,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Attempt":
        return cls(
            adapter=data["adapter"],
            status=data["status"],
            ok=data.get("ok", False),
            candidate_id=data.get("candidate_id"),
            candidate_url=data.get("candidate_url"),
            request_url=data.get("request_url"),
            detail=data.get("detail", ""),
            content_length=data.get("content_length", 0),
            metadata=data.get("metadata", {}),
            started_at=data.get("started_at", utc_now_iso()),
            finished_at=data.get("finished_at", utc_now_iso()),
        )


@dataclass(frozen=True)
class PromotedItem:
    item_id: str
    title: str
    url: str
    source_type: str
    adapter: str
    content: str
    content_type: str = "markdown"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_success(
        cls,
        *,
        task: AcquisitionTask,
        candidate: SourceCandidate,
        adapter: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> "PromotedItem":
        title = task.title or candidate.title or candidate.url
        canon = candidate.canonical_url or candidate.url
        meta = dict(metadata or {})
        meta["canonical_url"] = canon
        meta["source_id"] = task.source_id or "acquisition-orchestrator"
        return cls(
            item_id=f"acquired:{stable_digest(task.task_id, canon, adapter, content[:256])}",
            title=title,
            url=candidate.url,
            source_type=task.source_type,
            adapter=adapter,
            content=content,
            metadata=meta,
        )

    @property
    def canonical_url(self) -> str | None:
        return canonicalize_url(self.url)

    def as_knowledge_pack_candidate(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_type": self.source_type,
            "url": self.url,
            "canonical_url": self.canonical_url,
            "title": self.title,
            "raw_text": self.content,
            "local_text_path": None,
            "metadata": {
                **self.metadata,
                "acquisition_adapter": self.adapter,
                "content_type": self.content_type,
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "url": self.url,
            "canonical_url": self.canonical_url,
            "source_type": self.source_type,
            "adapter": self.adapter,
            "content_type": self.content_type,
            "content_length": len(self.content),
            "metadata": self.metadata,
            "knowledge_pack_candidate": self.as_knowledge_pack_candidate(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromotedItem":
        return cls(
            item_id=data["item_id"],
            title=data["title"],
            url=data["url"],
            source_type=data.get("source_type", "webpage"),
            adapter=data.get("adapter", "unknown"),
            content=data.get("content", ""),
            content_type=data.get("content_type", "markdown"),
            metadata=data.get("metadata", {}),
        )


@dataclass(frozen=True)
class RunLedger:
    run_id: str
    task: AcquisitionTask
    recipe_id: str
    source_candidates: list[SourceCandidate]
    attempts: list[Attempt]
    promoted_items: list[PromotedItem]
    status: str
    generated_at: str = field(default_factory=utc_now_iso)
    schema_version: str = SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "status": self.status,
            "recipe_id": self.recipe_id,
            "task": self.task.to_dict(),
            "source_candidates": [candidate.to_dict() for candidate in self.source_candidates],
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "promoted_items": [item.to_dict() for item in self.promoted_items],
            "promotion_contract": {
                "boundary": "before_knowledge_pack",
                "item_key": "knowledge_pack_candidate",
                "required_fields": [
                    "item_id",
                    "source_type",
                    "url",
                    "title",
                    "raw_text",
                    "metadata",
                ],
            },
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunLedger":
        task = AcquisitionTask.from_dict(data["task"])
        candidates = [SourceCandidate.from_dict(c) for c in data.get("source_candidates", [])]
        attempts = [Attempt.from_dict(a) for a in data.get("attempts", [])]
        promoted = [PromotedItem.from_dict(p) for p in data.get("promoted_items", [])]
        return cls(
            run_id=data["run_id"],
            task=task,
            recipe_id=data["recipe_id"],
            source_candidates=candidates,
            attempts=attempts,
            promoted_items=promoted,
            status=data["status"],
            generated_at=data.get("generated_at", utc_now_iso()),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            metadata=data.get("metadata", {}),
        )
