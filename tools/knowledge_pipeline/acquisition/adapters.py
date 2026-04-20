from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlencode, urlparse, urlunparse

from .models import AcquisitionTask, Attempt, PromotedItem, SourceCandidate


FetchFn = Callable[[str, dict[str, str] | None], str]


def jina_reader_url(url: str) -> str:
    return f"https://r.jina.ai/{url}"


def defuddle_url(url: str) -> str:
    return f"https://defuddle.md/{url}"


def amp_hint_url(url: str) -> str:
    parsed = urlparse(url)
    query = parsed.query
    amp_query = urlencode([("amp", "1")]) if not query else f"{query}&amp=1"
    return urlunparse(parsed._replace(query=amp_query))


def archive_today_url(url: str) -> str:
    return f"https://archive.today/?run=1&url={url}"


@dataclass(frozen=True)
class AcquisitionAdapter:
    name: str
    mode: str
    description: str
    request_builder: Callable[[SourceCandidate], str]
    env_key: str | None = None
    default_headers: dict[str, str] = field(default_factory=dict)

    def is_enabled(self, env: dict[str, str] | None = None) -> bool:
        env = env or {}
        if not self.env_key:
            return True
        return bool(env.get(self.env_key))

    def build_request_url(self, candidate: SourceCandidate) -> str:
        return self.request_builder(candidate)

    def attempt(
        self,
        *,
        task: AcquisitionTask,
        candidate: SourceCandidate,
        env: dict[str, str] | None = None,
        execute: bool = False,
        fetcher: FetchFn | None = None,
    ) -> tuple[Attempt, PromotedItem | None]:
        env = env or {}
        request_url = self.build_request_url(candidate)
        if not self.is_enabled(env):
            attempt = Attempt(
                adapter=self.name,
                status="disabled",
                candidate_id=candidate.candidate_id,
                candidate_url=candidate.url,
                request_url=request_url,
                detail=f"missing_env:{self.env_key}",
                metadata={"mode": self.mode},
            )
            return attempt, None

        if not execute:
            attempt = Attempt(
                adapter=self.name,
                status="not_executed",
                candidate_id=candidate.candidate_id,
                candidate_url=candidate.url,
                request_url=request_url,
                detail="dry_run",
                metadata={"mode": self.mode},
            )
            return attempt, None

        if fetcher is None:
            attempt = Attempt(
                adapter=self.name,
                status="not_implemented",
                candidate_id=candidate.candidate_id,
                candidate_url=candidate.url,
                request_url=request_url,
                detail="no_fetcher_configured",
                metadata={"mode": self.mode},
            )
            return attempt, None

        try:
            content = fetcher(request_url, self.default_headers or None)
        except Exception as exc:  # noqa: BLE001 - surface structured attempt status.
            attempt = Attempt(
                adapter=self.name,
                status="error",
                candidate_id=candidate.candidate_id,
                candidate_url=candidate.url,
                request_url=request_url,
                detail=f"{type(exc).__name__}:{exc}",
                metadata={"mode": self.mode},
            )
            return attempt, None

        promoted = PromotedItem.from_success(
            task=task,
            candidate=candidate,
            adapter=self.name,
            content=content,
            metadata={"request_url": request_url, "mode": self.mode},
        )
        attempt = Attempt(
            adapter=self.name,
            status="success",
            ok=True,
            candidate_id=candidate.candidate_id,
            candidate_url=candidate.url,
            request_url=request_url,
            detail="content_acquired",
            content_length=len(content),
            metadata={"mode": self.mode, "promoted_item_id": promoted.item_id},
        )
        return attempt, promoted


def default_adapters() -> dict[str, AcquisitionAdapter]:
    return {
        "jina_reader": AcquisitionAdapter(
            name="jina_reader",
            mode="reader_proxy",
            description="Primary no-key reader cascade entry using Jina Reader.",
            request_builder=lambda candidate: jina_reader_url(candidate.url),
        ),
        "defuddle": AcquisitionAdapter(
            name="defuddle",
            mode="reader_proxy",
            description="Markdown-focused fallback via defuddle.",
            request_builder=lambda candidate: defuddle_url(candidate.url),
        ),
        "direct_browser_ua": AcquisitionAdapter(
            name="direct_browser_ua",
            mode="direct_fetch",
            description="Direct fetch with browser-like user agent headers.",
            request_builder=lambda candidate: candidate.url,
            default_headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
                )
            },
        ),
        "amp": AcquisitionAdapter(
            name="amp",
            mode="url_variant",
            description="AMP-oriented URL variant for public article pages.",
            request_builder=lambda candidate: amp_hint_url(candidate.url),
        ),
        "archive_today": AcquisitionAdapter(
            name="archive_today",
            mode="archive_proxy",
            description="Archive.today snapshot lookup.",
            request_builder=lambda candidate: archive_today_url(candidate.url),
        ),
        "agent_fetch": AcquisitionAdapter(
            name="agent_fetch",
            mode="interactive_stub",
            description="Local browser or agentic fetch handoff point.",
            request_builder=lambda candidate: candidate.url,
        ),
        "firecrawl_web_agent": AcquisitionAdapter(
            name="firecrawl_web_agent",
            mode="optional_hosted_adapter",
            description="Optional Firecrawl/web-agent adapter, gated on FIRECRAWL_API_KEY.",
            request_builder=lambda candidate: candidate.url,
            env_key="FIRECRAWL_API_KEY",
        ),
    }
