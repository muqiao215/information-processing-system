"""Fixed evaluation dataset for quality and reliability assessment.

Contains 10 fixed items spanning GitHub, arXiv, and Web inputs,
exercising 5 failure/edge cases:
1. Duplicate URLs (exact duplicate input items)
2. Same content different links (URL normalization, tracking params, scheme, arXiv abs vs pdf)
3. Missing body / empty content / low-signal text
4. Timeout during acquisition/fetch
5. Source conflict (same article/URL from multiple collectors with differing metadata)
"""
from __future__ import annotations

from typing import Any


BENCHMARK_ITEMS: list[dict[str, Any]] = [
    # 1. Valid Webpage item
    {
        "id": "web_canonical_valid",
        "url": "https://blog.example.com/llm-agents-2026",
        "canonical_url": "https://blog.example.com/llm-agents-2026",
        "title": "State of LLM Agent Architectures in 2026",
        "source_type": "webpage",
        "source_id": "follow-builders",
        "summary": "An overview of production agent patterns including memory layers and tool orchestrators.",
        "tags": ["agents", "llm", "architecture"],
        "mock_response": {
            "status": 200,
            "content": "# State of LLM Agent Architectures in 2026\n\nProduction agents require persistent state, structured ledgers, and deterministic tool dispatching. This article reviews modern patterns.",
        },
        "expected_case": "valid",
    },
    # 2. Duplicate URL (exact duplicate of item 1)
    {
        "id": "web_exact_duplicate",
        "url": "https://blog.example.com/llm-agents-2026",
        "canonical_url": "https://blog.example.com/llm-agents-2026",
        "title": "State of LLM Agent Architectures in 2026",
        "source_type": "webpage",
        "source_id": "follow-builders",
        "summary": "Duplicate submission of the overview article.",
        "tags": ["agents"],
        "mock_response": {
            "status": 200,
            "content": "# State of LLM Agent Architectures in 2026\n\nProduction agents require persistent state, structured ledgers, and deterministic tool dispatching. This article reviews modern patterns.",
        },
        "expected_case": "duplicate_url",
    },
    # 3. Same content, different link (http, tracking parameters, trailing slash)
    {
        "id": "web_alias_tracking_params",
        "url": "http://blog.example.com/llm-agents-2026/?utm_source=twitter&utm_medium=social&ref=feed#section2",
        "canonical_url": "https://blog.example.com/llm-agents-2026",
        "title": "State of LLM Agent Architectures in 2026",
        "source_type": "webpage",
        "source_id": "follow-builders",
        "summary": "Link with tracking parameters pointing to the same article.",
        "tags": ["agents", "newsletter"],
        "mock_response": {
            "status": 200,
            "content": "# State of LLM Agent Architectures in 2026\n\nProduction agents require persistent state, structured ledgers, and deterministic tool dispatching. This article reviews modern patterns.",
        },
        "expected_case": "same_content_different_link",
    },
    # 4. Valid arXiv Paper (Abstract page)
    {
        "id": "arxiv_abstract_valid",
        "url": "https://arxiv.org/abs/2603.11111",
        "canonical_url": "https://arxiv.org/abs/2603.11111",
        "title": "Long-Term Working Memory in Autonomous Agents",
        "source_type": "arxiv_paper",
        "source_id": "arxiv-llm-memory-discovery",
        "summary": "Presents a dual-tier working memory model for LLM agents operating over multi-week task horizons.",
        "tags": ["arxiv", "llm-memory", "cs.AI"],
        "metadata": {
            "arxiv_id": "2603.11111",
            "authors": ["Alice Chen", "Bob Wang"],
            "score": 92.5,
        },
        "mock_response": {
            "status": 200,
            "content": "Title: Long-Term Working Memory in Autonomous Agents\nAuthors: Alice Chen, Bob Wang\n\nAbstract: We propose an episodic working memory mechanism that stores structured execution traces and retrieves them during planning.",
        },
        "expected_case": "valid",
    },
    # 5. Same arXiv Paper, different link (PDF URL variant)
    {
        "id": "arxiv_pdf_alias",
        "url": "https://arxiv.org/pdf/2603.11111.pdf",
        "canonical_url": "https://arxiv.org/abs/2603.11111",
        "title": "Long-Term Working Memory in Autonomous Agents",
        "source_type": "arxiv_paper",
        "source_id": "arxiv-llm-memory-discovery",
        "summary": "PDF URL variant of paper 2603.11111.",
        "tags": ["arxiv", "llm-memory"],
        "metadata": {
            "arxiv_id": "2603.11111",
        },
        "mock_response": {
            "status": 200,
            "content": "Title: Long-Term Working Memory in Autonomous Agents\nAuthors: Alice Chen, Bob Wang\n\nAbstract: We propose an episodic working memory mechanism that stores structured execution traces and retrieves them during planning.",
        },
        "expected_case": "same_content_different_link",
    },
    # 6. Valid GitHub Repository Raw Text
    {
        "id": "github_raw_valid",
        "url": "https://raw.githubusercontent.com/example-org/fast-agent/main/README.md",
        "canonical_url": "https://github.com/example-org/fast-agent",
        "title": "FastAgent: High-Throughput Agent Execution Engine",
        "source_type": "raw_github_text",
        "source_id": "daily-github-trending-ai-watch",
        "summary": "A lightweight Rust runtime for running autonomous agent workflows with sub-millisecond dispatch.",
        "tags": ["github", "trending", "rust", "agents"],
        "mock_response": {
            "status": 200,
            "content": "# FastAgent\n\nHigh-throughput autonomous agent execution engine written in Rust.\nFeatures:\n- Sub-millisecond dispatch\n- Durable task queues\n- Zero-copy state serialization",
        },
        "expected_case": "valid",
    },
    # 7. Missing body / empty content
    {
        "id": "web_missing_body",
        "url": "https://example.org/articles/empty-placeholder",
        "canonical_url": "https://example.org/articles/empty-placeholder",
        "title": "Empty Placeholder Article",
        "source_type": "webpage",
        "source_id": "follow-builders",
        "summary": "Article with missing body.",
        "tags": ["draft"],
        "mock_response": {
            "status": 200,
            "content": "   \n\t  \n  ",  # empty/whitespace only
        },
        "expected_case": "missing_body",
    },
    # 8. Timeout
    {
        "id": "web_timeout_error",
        "url": "https://timeout.blackhole.example.net/slow-endpoint",
        "canonical_url": "https://timeout.blackhole.example.net/slow-endpoint",
        "title": "Slow Endpoint That Hangs",
        "source_type": "webpage",
        "source_id": "daily-news-summary",
        "summary": "Source endpoint that always times out.",
        "tags": ["news"],
        "mock_response": {
            "status": "timeout",
            "error": "Connection timed out after 30 seconds",
        },
        "expected_case": "timeout",
    },
    # 9. Source conflict Item A (Observed via follow-builders)
    {
        "id": "conflict_source_a",
        "url": "https://research.example.com/evals/memorybench-2026",
        "canonical_url": "https://research.example.com/evals/memorybench-2026",
        "title": "MemoryBench 2026: Evaluating Multi-Session Agent Memory",
        "source_type": "webpage",
        "source_id": "follow-builders",
        "summary": "A standardized benchmark for multi-session agent recall and reasoning over extended memory stores.",
        "tags": ["evals", "benchmarks", "memory"],
        "freshness": {
            "published_at": "2026-09-13T10:00:00Z",
            "generated_at": "2026-09-14T01:00:00Z",
        },
        "mock_response": {
            "status": 200,
            "content": "# MemoryBench 2026\n\nMemoryBench evaluates agent long-term memory across 100 multi-turn scenarios.",
        },
        "expected_case": "source_conflict",
    },
    # 10. Source conflict Item B (Observed via daily-news-summary with different title & tags)
    {
        "id": "conflict_source_b",
        "url": "https://research.example.com/evals/memorybench-2026?ref=hacker-news",
        "canonical_url": "https://research.example.com/evals/memorybench-2026",
        "title": "MemoryBench Released: Comprehensive LLM Memory Benchmark",
        "source_type": "webpage",
        "source_id": "daily-news-summary",
        "summary": "MemoryBench released by research team, providing standardized test suites for memory agents.",
        "tags": ["hacker-news", "llm-memory", "release"],
        "freshness": {
            "published_at": "2026-09-13T11:30:00Z",
            "generated_at": "2026-09-14T01:15:00Z",
        },
        "mock_response": {
            "status": 200,
            "content": "# MemoryBench 2026\n\nMemoryBench evaluates agent long-term memory across 100 multi-turn scenarios.",
        },
        "expected_case": "source_conflict",
    },
]
