from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from .models import AcquisitionTask, Attempt, PromotedItem, SourceCandidate, canonicalize_url


FetchFn = Callable[[str, dict[str, str] | None], str]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)


def is_valid_content(content: str | None, min_chars: int = 40) -> tuple[bool, str]:
    """Validate acquired content against missing body and low signal markers."""
    if content is None:
        return False, "null_content"
    stripped = content.strip()
    if not stripped:
        return False, "empty_content"
    if len(stripped) < min_chars:
        return False, f"low_signal_chars_{len(stripped)}"

    lowered = stripped[:1000].lower()
    error_markers = (
        "404 not found",
        "page not found",
        "access denied",
        "please enable javascript",
        "just a moment...",
        "captcha",
        '{"error":',
    )
    for marker in error_markers:
        if marker in lowered and len(stripped) < 250:
            return False, f"error_marker:{marker}"

    return True, "ok"


def default_http_fetcher(
    url: str,
    headers: dict[str, str] | None = None,
    timeout_seconds: int = 30,
) -> str:
    """Built-in HTTP fetcher with timeout and browser UA."""
    req_headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept": "*/*"}
    if headers:
        req_headers.update(headers)
    req = Request(url, headers=req_headers)
    with urlopen(req, timeout=timeout_seconds) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read(200_000).decode(charset, errors="replace")


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


def arxiv_abs_url(url: str) -> str:
    canon = canonicalize_url(url)
    if canon and "arxiv.org" in canon:
        return canon
    return url


@dataclass(frozen=True)
class AcquisitionAdapter:
    name: str
    mode: str
    description: str
    request_builder: Callable[[SourceCandidate], str]
    env_key: str | None = None
    default_headers: dict[str, str] = field(default_factory=dict)
    min_content_chars: int = 40

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

        active_fetcher = fetcher or default_http_fetcher

        try:
            content = active_fetcher(request_url, self.default_headers or None)
        except (TimeoutError, TimeoutAsyncError if "TimeoutAsyncError" in globals() else TimeoutError) as exc:
            attempt = Attempt(
                adapter=self.name,
                status="timeout",
                candidate_id=candidate.candidate_id,
                candidate_url=candidate.url,
                request_url=request_url,
                detail=f"TimeoutError:{exc}",
                metadata={"mode": self.mode},
            )
            return attempt, None
        except Exception as exc:  # noqa: BLE001 - surface structured attempt status.
            exc_str = str(exc).lower()
            is_timeout = "timeout" in exc_str or "timed out" in exc_str
            status = "timeout" if is_timeout else "error"
            attempt = Attempt(
                adapter=self.name,
                status=status,
                candidate_id=candidate.candidate_id,
                candidate_url=candidate.url,
                request_url=request_url,
                detail=f"{type(exc).__name__}:{exc}",
                metadata={"mode": self.mode},
            )
            return attempt, None

        # Content validation: reject missing body or low-signal error text
        valid, reason = is_valid_content(content, min_chars=self.min_content_chars)
        if not valid:
            attempt = Attempt(
                adapter=self.name,
                status="rejected",
                candidate_id=candidate.candidate_id,
                candidate_url=candidate.url,
                request_url=request_url,
                detail=f"invalid_content:{reason}",
                content_length=len(content or ""),
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
            default_headers={"User-Agent": DEFAULT_USER_AGENT},
        ),
        "direct_raw": AcquisitionAdapter(
            name="direct_raw",
            mode="direct_fetch",
            description="Direct raw fetch for GitHub READMEs and text endpoints.",
            request_builder=lambda candidate: candidate.url,
            default_headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "text/plain,text/markdown,*/*",
            },
        ),
        "arxiv_abstract": AcquisitionAdapter(
            name="arxiv_abstract",
            mode="reader_proxy",
            description="Direct fetch for arXiv abstract pages.",
            request_builder=lambda candidate: arxiv_abs_url(candidate.url),
            default_headers={"User-Agent": DEFAULT_USER_AGENT},
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
