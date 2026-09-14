"""Fixed local fault-injection input set.

Every task, route, and content payload here is hard-coded so that URLs,
canonical URLs, item digests, and ledger file names stay byte-identical
across harness invocations. The only runtime variable is the mock server
port, which defaults to a fixed value for the same reason.

Fault categories covered (one or more tasks each):
  1.  duplicate_article          exact duplicate task entries
  2.  same_title_diff_content    identical titles, different bodies, different URLs
  3.  same_content_diff_url      identical bodies, different paths (syndication)
  4.  content_update             same URL, body flips with the content epoch
  5.  http_404 / http_429 / http_500
  6.  timeout                    origin sleeps longer than the fetch timeout
  7.  garbled_bytes              GBK bytes declared as charset=utf-8
  8.  truncated_html             syntactically cut HTML, correct Content-Length
  9.  incomplete_read            declared Content-Length larger than sent body
 10.  empty_body                 200 with whitespace-only body
 11.  wrong_mime                 binary PNG served on an article URL
 12.  very_long_body             5 MB body vs the 200k fetch cap
 13.  conflicting_sources        same canonical URL from two collectors with
                                 contradictory claims
"""
from __future__ import annotations

from typing import Any

MOCK_PORT_DEFAULT = 8975
MOCK_HOST = "127.0.0.1"

FETCH_TIMEOUT_SECONDS = 1.5
TIMEOUT_ROUTE_SLEEP_SECONDS = 3.0
FETCH_CHAR_CAP = 200_000

EPOCH_FILE_NAME = "content_epoch"


def base_url(port: int = MOCK_PORT_DEFAULT) -> str:
    return f"http://{MOCK_HOST}:{port}"


ARTICLE_DUP = (
    "# Distributed Trace Sampling at Scale\n\n"
    "Tail-based sampling keeps only the interesting fraction of traces. "
    "This note describes a deterministic reservoir policy deployed on a "
    "three-region fleet and the gotchas we hit while backfilling."
)

TITLE_CLASH_BODY_V1 = (
    "# Agent Memory Field Guide\n\n"
    "Version one of the field guide: episodic stores, semantic indexes, "
    "and the retention schedules that keep recall honest over long horizons."
)

TITLE_CLASH_BODY_V2 = (
    "# Agent Memory Field Guide\n\n"
    "Version two of the field guide: a totally different article that "
    "deliberately shares its title with version one to prove titles alone "
    "must never merge distinct documents."
)

SYNDICATED_BODY = (
    "# Vector DB Cost Playbook\n\n"
    "Syndicated article: quantify the cost of brute-force recall versus "
    "ANN indexes, then decide when a flat baseline is simply cheaper."
)

UPDATED_BODY_V1 = (
    "# Frontier Model Pricing Update\n\n"
    "Epoch 1 pricing snapshot: flagship context window billed at twelve "
    "dollars per million tokens, cache reads billed at one tenth."
)

UPDATED_BODY_V2 = (
    "# Frontier Model Pricing Update\n\n"
    "Epoch 2 pricing snapshot: flagship context window billed at four "
    "dollars per million tokens after the spring price cut."
)

CONFLICT_BODY_A = (
    "# MemoryBench Final Scores\n\n"
    "Official leaderboard note: the winning agent configuration reached "
    "a verified composite score of 88 on the multi-session track."
)

CONFLICT_BODY_B = (
    "# MemoryBench Results Announced\n\n"
    "Independent coverage claims the winning agent configuration reached "
    "a composite score of 93 on the same multi-session track."
)

ARXIV_ABSTRACT = (
    "Title: Sparse Memory Retrieval for Long-Horizon Agents\n"
    "Authors: Chen, Rao, Ito\n\n"
    "Abstract: We study sparse retrieval over agent episodic memory and "
    "show that block-level sparse indexes beat dense-only recall at a "
    "fraction of the serving cost."
)

GITHUB_README = (
    "# FastAgent Local\n\n"
    "High-throughput agent execution engine. This local fixture stands in "
    "for a raw GitHub README with bullet lists:\n"
    "- deterministic dispatch\n"
    "- durable queues\n"
    "- zero-copy state\n"
)

GARBLED_CHINESE_TEXT = (
    "这篇技术备忘录讨论了分布式追踪采样策略,包括尾部采样、"
    "自适应采样率以及跨区域回填时的常见陷阱与缓解办法。"
    "内容足够长以便通过最低长度阈值检查,同时保持确定性。"
)

TRUNCATED_HTML_BODY = (
    "<!DOCTYPE html><html><head><title>Quarterly Infra Report</title></head>"
    "<body><h1>Quarterly Infra Report</h1><p>Incident count fell by 40% "
    "after the sampling rollout, and p99 ingest lag stayed under budget "
    "for the whole quarter.<p>The next section covers capacity planning "
    "<table><tr><td>region"  # cut mid-tag on purpose
)

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c626001000000ffff03000006000557bfabd40000000049454e44ae426082"
)

LONG_PARAGRAPH = (
    "Deterministic filler paragraph for the very-long-body fault category. "
    "It talks about queueing theory, backpressure, and fair scheduling so "
    "that the text stays plausible while remaining perfectly repeatable. "
)


def long_body() -> str:
    return "\n\n".join(
        f"{LONG_PARAGRAPH} (segment {i})" for i in range(12_500)
    )


def garbled_gbk_bytes() -> bytes:
    return GARBLED_CHINESE_TEXT.encode("gbk")


def route_table(epoch: int) -> dict[str, dict[str, Any]]:
    """Route path -> response spec. Deterministic given the content epoch."""
    conflict_a_spec = {"status": 200, "body": CONFLICT_BODY_A, "content_type": "text/html; charset=utf-8"}
    conflict_b_spec = {"status": 200, "body": CONFLICT_BODY_B, "content_type": "text/html; charset=utf-8"}
    return {
        "/dup/article-a": {"status": 200, "body": ARTICLE_DUP, "content_type": "text/html; charset=utf-8"},
        "/title-clash/v1": {"status": 200, "body": TITLE_CLASH_BODY_V1, "content_type": "text/html; charset=utf-8"},
        "/title-clash/v2": {"status": 200, "body": TITLE_CLASH_BODY_V2, "content_type": "text/html; charset=utf-8"},
        "/syndicated/original": {"status": 200, "body": SYNDICATED_BODY, "content_type": "text/html; charset=utf-8"},
        "/syndicated/mirror": {"status": 200, "body": SYNDICATED_BODY, "content_type": "text/html; charset=utf-8"},
        "/updated/article": {
            "status": 200,
            "body": UPDATED_BODY_V1 if epoch < 2 else UPDATED_BODY_V2,
            "content_type": "text/html; charset=utf-8",
        },
        "/status/404": {"status": 404, "body": "404 not found page", "content_type": "text/plain; charset=utf-8"},
        "/status/429": {"status": 429, "body": "rate limited, slow down", "content_type": "text/plain; charset=utf-8", "headers": {"Retry-After": "1"}},
        "/status/500": {"status": 500, "body": "internal server error while rendering", "content_type": "text/plain; charset=utf-8"},
        "/timeout/slow": {"status": 200, "body": "too late", "content_type": "text/plain; charset=utf-8", "sleep": TIMEOUT_ROUTE_SLEEP_SECONDS},
        "/garbled/misdeclared": {
            "status": 200,
            "raw": garbled_gbk_bytes(),
            "content_type": "text/html; charset=utf-8",
        },
        "/truncated/cut-mid-tag": {"status": 200, "body": TRUNCATED_HTML_BODY, "content_type": "text/html; charset=utf-8"},
        "/truncated/incomplete-read": {
            "status": 200,
            "body": TRUNCATED_HTML_BODY,
            "content_type": "text/html; charset=utf-8",
            "declared_length_padding": 4096,
        },
        "/empty/body": {"status": 200, "body": "   \n\t  \n", "content_type": "text/html; charset=utf-8"},
        "/mime/png-as-article": {"status": 200, "raw": PNG_1PX, "content_type": "image/png"},
        "/long/article": {"status": 200, "body": long_body(), "content_type": "text/plain; charset=utf-8"},
        # Same canonical path; the two collectors see contradictory bodies
        # selected by the tracking query they appended.
        "/conflict/claim-a": {
            "status": 200,
            "by_query": {
                "ref": {
                    "newsletter": conflict_a_spec,
                    "hacker-news": conflict_b_spec,
                }
            },
            "body": CONFLICT_BODY_A,
            "content_type": "text/html; charset=utf-8",
        },
        "/arxiv/abs/2603.11111": {"status": 200, "body": ARXIV_ABSTRACT, "content_type": "text/html; charset=utf-8"},
        "/gh/raw/fastagent.md": {"status": 200, "body": GITHUB_README, "content_type": "text/plain; charset=utf-8"},
        "/health": {"status": 200, "body": "ok", "content_type": "text/plain; charset=utf-8"},
    }


def build_tasks(port: int = MOCK_PORT_DEFAULT) -> list[dict[str, Any]]:
    """The fixed acquisition batch. task_id / title / source_id are all fixed."""
    root = base_url(port)
    return [
        {
            "task_id": "acq:dup-exact-a",
            "url": f"{root}/dup/article-a",
            "title": "Distributed Trace Sampling at Scale",
            "source_type": "webpage",
            "source_id": "follow-builders",
        },
        {
            "task_id": "acq:dup-exact-b",
            "url": f"{root}/dup/article-a",
            "title": "Distributed Trace Sampling at Scale",
            "source_type": "webpage",
            "source_id": "follow-builders",
        },
        {
            "task_id": "acq:dup-alias-utm",
            "url": f"{root}/dup/article-a?utm_source=twitter&utm_medium=social&ref=feed",
            "title": "Distributed Trace Sampling at Scale",
            "source_type": "webpage",
            "source_id": "daily-news-summary",
        },
        {
            "task_id": "acq:title-clash-v1",
            "url": f"{root}/title-clash/v1",
            "title": "Agent Memory Field Guide",
            "source_type": "webpage",
            "source_id": "follow-builders",
        },
        {
            "task_id": "acq:title-clash-v2",
            "url": f"{root}/title-clash/v2",
            "title": "Agent Memory Field Guide",
            "source_type": "webpage",
            "source_id": "daily-news-summary",
        },
        {
            "task_id": "acq:syndicated-original",
            "url": f"{root}/syndicated/original",
            "title": "Vector DB Cost Playbook",
            "source_type": "webpage",
            "source_id": "follow-builders",
        },
        {
            "task_id": "acq:syndicated-mirror",
            "url": f"{root}/syndicated/mirror",
            "title": "Vector DB Cost Playbook",
            "source_type": "webpage",
            "source_id": "daily-news-summary",
        },
        {
            "task_id": "acq:updated-article",
            "url": f"{root}/updated/article",
            "title": "Frontier Model Pricing Update",
            "source_type": "webpage",
            "source_id": "follow-builders",
        },
        {
            "task_id": "acq:http-404",
            "url": f"{root}/status/404",
            "title": "Missing Article on Status Route",
            "source_type": "webpage",
            "source_id": "daily-news-summary",
        },
        {
            "task_id": "acq:http-429",
            "url": f"{root}/status/429",
            "title": "Rate Limited Article Fetch",
            "source_type": "webpage",
            "source_id": "daily-news-summary",
        },
        {
            "task_id": "acq:http-500",
            "url": f"{root}/status/500",
            "title": "Server Error Article Fetch",
            "source_type": "webpage",
            "source_id": "daily-news-summary",
        },
        {
            "task_id": "acq:timeout-slow",
            "url": f"{root}/timeout/slow",
            "title": "Hanging Endpoint Article",
            "source_type": "webpage",
            "source_id": "daily-news-summary",
        },
        {
            "task_id": "acq:garbled-bytes",
            "url": f"{root}/garbled/misdeclared",
            "title": "Misdeclared Charset Memo",
            "source_type": "webpage",
            "source_id": "follow-builders",
        },
        {
            "task_id": "acq:truncated-html",
            "url": f"{root}/truncated/cut-mid-tag",
            "title": "Quarterly Infra Report",
            "source_type": "webpage",
            "source_id": "follow-builders",
        },
        {
            "task_id": "acq:incomplete-read",
            "url": f"{root}/truncated/incomplete-read",
            "title": "Declared Longer Than Sent Article",
            "source_type": "webpage",
            "source_id": "follow-builders",
        },
        {
            "task_id": "acq:empty-body",
            "url": f"{root}/empty/body",
            "title": "Whitespace Placeholder Article",
            "source_type": "webpage",
            "source_id": "daily-news-summary",
        },
        {
            "task_id": "acq:wrong-mime-png",
            "url": f"{root}/mime/png-as-article",
            "title": "Binary Payload Served as Article",
            "source_type": "webpage",
            "source_id": "follow-builders",
        },
        {
            "task_id": "acq:long-body",
            "url": f"{root}/long/article",
            "title": "Extremely Long Queueing Treatise",
            "source_type": "webpage",
            "source_id": "follow-builders",
        },
        {
            "task_id": "acq:conflict-source-a",
            "url": f"{root}/conflict/claim-a?ref=newsletter",
            "title": "MemoryBench Final Scores",
            "source_type": "webpage",
            "source_id": "follow-builders",
        },
        {
            "task_id": "acq:conflict-source-b",
            "url": f"{root}/conflict/claim-a?ref=hacker-news",
            "title": "MemoryBench Results Announced",
            "source_type": "webpage",
            "source_id": "daily-news-summary",
        },
        {
            "task_id": "acq:arxiv-local",
            "url": f"{root}/arxiv/abs/2603.11111",
            "title": "Sparse Memory Retrieval for Long-Horizon Agents",
            "source_type": "arxiv_paper",
            "source_id": "arxiv-llm-memory-discovery",
        },
        {
            "task_id": "acq:github-local",
            "url": f"{root}/gh/raw/fastagent.md",
            "title": "FastAgent Local README",
            "source_type": "raw_github_text",
            "source_id": "daily-github-trending-ai-watch",
        },
    ]


# Which task groups should collapse into a single knowledge pack item
# after a correct dedupe pass. Used by the matrix evaluator.
EXPECTED_MERGE_GROUPS = {
    "duplicate_article": ["acq:dup-exact-a", "acq:dup-exact-b", "acq:dup-alias-utm"],
    "same_title_diff_content": ["acq:title-clash-v1", "acq:title-clash-v2"],  # must stay separate
    "same_content_diff_url": ["acq:syndicated-original", "acq:syndicated-mirror"],
    "conflicting_sources": ["acq:conflict-source-a", "acq:conflict-source-b"],
}

EXPECTED_NO_PROMOTION = [
    "acq:http-404",
    "acq:http-429",
    "acq:http-500",
    "acq:timeout-slow",
    "acq:empty-body",
    "acq:incomplete-read",
]

EPOCH_DEPENDENT_TITLE = "Frontier Model Pricing Update"
