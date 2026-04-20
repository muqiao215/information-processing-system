from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


SCHEMA_VERSION = "2026-04-20.acquisition.v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_digest(*parts: str) -> str:
    seed = "\n".join(parts)
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


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
        generated_task_id = task_id or f"acq:{stable_digest(url, title or '')}"
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
            "title": self.title,
            "domain": self.domain,
            "metadata": self.metadata,
        }


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
        return cls(
            candidate_id=f"candidate:{stable_digest(task.task_id, task.url)}",
            url=task.url,
            source_type=task.source_type,
            title=task.title,
            priority=priority,
            metadata={"task_id": task.task_id},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "url": self.url,
            "source_type": self.source_type,
            "title": self.title,
            "priority": self.priority,
            "metadata": self.metadata,
        }


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
        return cls(
            item_id=f"acquired:{stable_digest(task.task_id, candidate.url, adapter, content[:256])}",
            title=title,
            url=candidate.url,
            source_type=task.source_type,
            adapter=adapter,
            content=content,
            metadata=metadata or {},
        )

    def as_knowledge_pack_candidate(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_type": self.source_type,
            "url": self.url,
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
            "source_type": self.source_type,
            "adapter": self.adapter,
            "content_type": self.content_type,
            "content_length": len(self.content),
            "metadata": self.metadata,
            "knowledge_pack_candidate": self.as_knowledge_pack_candidate(),
        }


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
                "required_fields": ["item_id", "source_type", "url", "title", "raw_text", "metadata"],
            },
            "metadata": self.metadata,
        }
