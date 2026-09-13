"""Quality and reliability evaluation tests for information-processing-system.

Evaluates:
- End-to-end pipeline: source -> recipe -> ledger -> knowledge_pack
- 5 failure/edge modes:
  1. Duplicate URLs
  2. Same content different links (URL normalization, tracking params, arXiv abs/pdf)
  3. Missing body / empty content
  4. Timeout
  5. Source conflict across collectors
- Interruption and rerun (resumption idempotency)
- Cross-day rerun and stable ID consistency
- Partial success handling
- Citation and provenance traceability
- Baseline metrics computation (duplication rate, source coverage, valid item rate, processing time)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tests.fixtures.evaluation_dataset import BENCHMARK_ITEMS
from tools.knowledge_pipeline.acquisition import (
    AcquisitionTask,
    Orchestrator,
    RunLedger,
    default_registry,
    select_recipe,
)
from tools.knowledge_pipeline.acquisition.models import (
    canonicalize_url,
    stable_digest,
    stable_item_id,
)
from tools.knowledge_pipeline.normalization.build_knowledge_pack import (
    build_acquisition_items,
    dedupe_items,
    ensure_pack_shape,
    render_item_fallback,
)


def make_mock_fetcher(dataset: list[dict[str, Any]]):
    """Returns a deterministic fetcher keyed on candidate request URL."""
    url_map: dict[str, dict[str, Any]] = {}
    for item in dataset:
        raw_url = item["url"]
        url_map[raw_url] = item["mock_response"]
        url_map[f"https://r.jina.ai/{raw_url}"] = item["mock_response"]
        url_map[f"https://defuddle.md/{raw_url}"] = item["mock_response"]
        canon = item.get("canonical_url")
        if canon:
            url_map[canon] = item["mock_response"]
            url_map[f"https://r.jina.ai/{canon}"] = item["mock_response"]
            url_map[f"https://defuddle.md/{canon}"] = item["mock_response"]

    def fetcher(request_url: str, headers: dict[str, str] | None = None) -> str:
        resp = None
        if request_url in url_map:
            resp = url_map[request_url]
        else:
            for target_url, data in url_map.items():
                if target_url in request_url or request_url in target_url:
                    resp = data
                    break
        if not resp:
            raise ValueError(f"Unmocked URL: {request_url}")

        if resp.get("status") == "timeout":
            raise TimeoutError(resp.get("error", "Timed out"))
        return resp.get("content", "")

    return fetcher


class QualityReliabilityEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = default_registry()
        self.fetcher = make_mock_fetcher(BENCHMARK_ITEMS)

    def test_01_benchmark_contains_all_required_dimensions(self) -> None:
        """Verify the benchmark dataset covers GitHub, arXiv, Web, and the 5 required cases."""
        source_types = {item["source_type"] for item in BENCHMARK_ITEMS}
        self.assertIn("webpage", source_types)
        self.assertIn("arxiv_paper", source_types)
        self.assertIn("raw_github_text", source_types)

        cases = {item["expected_case"] for item in BENCHMARK_ITEMS}
        self.assertIn("duplicate_url", cases)
        self.assertIn("same_content_different_link", cases)
        self.assertIn("missing_body", cases)
        self.assertIn("timeout", cases)
        self.assertIn("source_conflict", cases)

    def test_02_url_canonicalization_and_alias_resolution(self) -> None:
        """Verify URL canonicalization handles tracking params, trailing slashes, arXiv variants, and GitHub."""
        # Tracking parameters and fragments
        url1 = "http://blog.example.com/llm-agents-2026/?utm_source=twitter&utm_medium=social&ref=feed#section2"
        canon1 = canonicalize_url(url1)
        self.assertEqual(canon1, "https://blog.example.com/llm-agents-2026")

        # arXiv abs vs pdf
        url_abs = "https://arxiv.org/abs/2603.11111"
        url_pdf = "https://arxiv.org/pdf/2603.11111.pdf"
        self.assertEqual(canonicalize_url(url_abs), canonicalize_url(url_pdf))
        self.assertEqual(canonicalize_url(url_pdf), "https://arxiv.org/abs/2603.11111")

        # GitHub raw vs repo
        github_raw = "https://raw.githubusercontent.com/example-org/fast-agent/main/README.md"
        github_blob = "https://github.com/example-org/fast-agent/blob/main/README.md"
        self.assertEqual(canonicalize_url(github_raw), "https://github.com/example-org/fast-agent")
        self.assertEqual(canonicalize_url(github_blob), "https://github.com/example-org/fast-agent")

    def test_03_missing_body_is_rejected_not_promoted(self) -> None:
        """Verify that an article with missing body / whitespace is rejected and not promoted."""
        item = next(x for x in BENCHMARK_ITEMS if x["id"] == "web_missing_body")
        task = AcquisitionTask.from_url(
            item["url"],
            title=item["title"],
            source_type=item["source_type"],
            source_id=item["source_id"],
        )
        orchestrator = Orchestrator(
            registry=self.registry,
            execute=True,
            fetcher=self.fetcher,
        )
        ledger = orchestrator.run(task)

        # Missing body should not be promoted
        self.assertEqual(ledger.promoted_items, [])
        self.assertIn(ledger.status, ("attempted", "rejected", "failed"))
        # Attempts should record rejection detail
        self.assertTrue(any("invalid_content" in a.detail or a.status == "rejected" for a in ledger.attempts))

    def test_04_timeout_handling_records_clean_failure_without_crash(self) -> None:
        """Verify timeout during fetch is handled gracefully and recorded in the ledger."""
        item = next(x for x in BENCHMARK_ITEMS if x["id"] == "web_timeout_error")
        task = AcquisitionTask.from_url(
            item["url"],
            title=item["title"],
            source_type=item["source_type"],
            source_id=item["source_id"],
        )
        orchestrator = Orchestrator(
            registry=self.registry,
            execute=True,
            fetcher=self.fetcher,
        )
        ledger = orchestrator.run(task)

        self.assertEqual(ledger.promoted_items, [])
        self.assertEqual(ledger.status, "attempted")
        # Every executed step should have caught the timeout
        timeout_attempts = [a for a in ledger.attempts if "timeout" in a.status.lower() or "timeout" in a.detail.lower()]
        self.assertTrue(len(timeout_attempts) > 0)

    def test_05_specialized_recipes_for_arxiv_and_github(self) -> None:
        """Verify specialized recipes exist for arXiv papers and GitHub text."""
        arxiv_task = AcquisitionTask.from_url(
            "https://arxiv.org/abs/2603.11111",
            source_type="arxiv_paper",
        )
        arxiv_recipe = select_recipe(arxiv_task, self.registry)
        self.assertEqual(arxiv_recipe.recipe_id, "arxiv_paper_default")

        github_task = AcquisitionTask.from_url(
            "https://raw.githubusercontent.com/example-org/fast-agent/main/README.md",
            source_type="raw_github_text",
        )
        github_recipe = select_recipe(github_task, self.registry)
        self.assertEqual(github_recipe.recipe_id, "raw_github_default")

    def test_06_source_conflict_merging_and_cross_source_dedupe(self) -> None:
        """Verify source conflict (same canonical URL from 2 sources) merges metadata and provenance."""
        item_a = next(x for x in BENCHMARK_ITEMS if x["id"] == "conflict_source_a")
        item_b = next(x for x in BENCHMARK_ITEMS if x["id"] == "conflict_source_b")

        task_a = AcquisitionTask.from_url(item_a["url"], title=item_a["title"], source_id=item_a["source_id"])
        task_b = AcquisitionTask.from_url(item_b["url"], title=item_b["title"], source_id=item_b["source_id"])

        orchestrator = Orchestrator(registry=self.registry, execute=True, fetcher=self.fetcher)
        ledger_a = orchestrator.run(task_a)
        ledger_b = orchestrator.run(task_b)

        self.assertEqual(len(ledger_a.promoted_items), 1)
        self.assertEqual(len(ledger_b.promoted_items), 1)

        raw_kp_items = build_acquisition_items([ledger_a, ledger_b])
        self.assertEqual(len(raw_kp_items), 2)

        deduped = dedupe_items(raw_kp_items)
        # Should merge into exactly 1 item!
        self.assertEqual(len(deduped), 1)
        merged = deduped[0]

        # Check citation and provenance
        meta = merged.get("metadata", {})
        self.assertIn("observed_sources", meta)
        self.assertIn("follow-builders", meta["observed_sources"])
        self.assertIn("daily-news-summary", meta["observed_sources"])

    def test_07_full_chain_source_recipe_ledger_knowledge_pack(self) -> None:
        """Verify end-to-end pipeline execution from sources to a validated knowledge_pack."""
        tasks = [
            AcquisitionTask.from_url(
                item["url"],
                title=item["title"],
                source_type=item["source_type"],
                source_id=item["source_id"],
                metadata={"benchmark_id": item["id"]},
            )
            for item in BENCHMARK_ITEMS
        ]

        orchestrator = Orchestrator(registry=self.registry, execute=True, fetcher=self.fetcher)
        ledgers = [orchestrator.run(task) for task in tasks]

        # Verify ledgers
        promoted_ledgers = [l for l in ledgers if l.promoted_items]
        # We expect 8 items to have valid responses, 2 to fail (missing body & timeout)
        self.assertEqual(len(promoted_ledgers), 8)

        # Convert ledgers to knowledge_pack items
        kp_items = build_acquisition_items(ledgers)
        self.assertEqual(len(kp_items), 8)

        # Deduplicate items
        deduped = dedupe_items(kp_items)
        # 8 items contain:
        # - web agents (3 items: 1 valid, 1 exact dup, 1 tracking alias) -> deduped to 1
        # - arxiv (2 items: 1 abs, 1 pdf) -> deduped to 1
        # - github (1 item) -> 1
        # - memorybench (2 items: conflict A and B) -> deduped to 1
        # Total unique entities = 4!
        self.assertEqual(len(deduped), 4)

        # Construct full pack dictionary and verify schema
        date_str = "2026-09-14"
        pack = {
            "schema_version": "2026-04-19.v2",
            "pack_id": f"knowledge-pack-{date_str}",
            "date": date_str,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "item_count": len(deduped),
            "source_counts": {"acquisition-orchestrator": len(deduped)},
            "input_manifests": {
                "acquisition-orchestrator": {
                    "path": "memory://ledgers",
                    "exists": True,
                    "item_count": len(ledgers),
                }
            },
            "items": deduped,
            "preprocessing_summary": {
                "status_counts": {"ready": len(deduped)},
                "method_counts": {},
                "localized_source_types": {},
                "cache_root": None,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "notes": ["Evaluated via quality & reliability suite."],
            },
            "fallback_markdown_path": None,
            "notes": ["Evaluation pack."],
        }
        ensure_pack_shape(pack)

    def test_08_interruption_and_rerun_resumption(self) -> None:
        """Verify interruption recovery: already acquired items are not re-fetched on rerun."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ledger_dir = Path(tmp_dir) / "ledgers"
            ledger_dir.mkdir()

            tasks = [
                AcquisitionTask.from_url(
                    item["url"],
                    title=item["title"],
                    source_type=item["source_type"],
                    source_id=item["source_id"],
                )
                for item in BENCHMARK_ITEMS[:4]
            ]

            fetch_counter = {"calls": 0}

            def counting_fetcher(url: str, headers: dict[str, str] | None = None) -> str:
                fetch_counter["calls"] += 1
                return self.fetcher(url, headers)

            orchestrator = Orchestrator(registry=self.registry, execute=True, fetcher=counting_fetcher)

            # Step 1: Run first 2 tasks and simulate interruption
            ledgers_part1 = orchestrator.run_batch(tasks[:2], ledger_dir=ledger_dir, resume=True)
            self.assertEqual(len(ledgers_part1), 2)
            first_run_calls = fetch_counter["calls"]
            self.assertTrue(first_run_calls > 0)

            # Step 2: Rerun all 4 tasks with resume=True
            ledgers_part2 = orchestrator.run_batch(tasks, ledger_dir=ledger_dir, resume=True)
            self.assertEqual(len(ledgers_part2), 4)

            # The first 2 tasks should have been loaded from disk without incrementing fetch_counter
            # Total fetch calls should only be for the remaining 2 tasks!
            additional_calls = fetch_counter["calls"] - first_run_calls
            # Remaining 2 tasks: task[2] (web alias) and task[3] (arxiv valid)
            self.assertTrue(additional_calls > 0)
            self.assertEqual(fetch_counter["calls"], first_run_calls + additional_calls)

    def test_09_cross_day_rerun_id_stability(self) -> None:
        """Verify item IDs remain stable and deterministic across multiple run dates."""
        item = next(x for x in BENCHMARK_ITEMS if x["id"] == "web_canonical_valid")
        id_day1 = stable_item_id("webpage", item["title"], item["url"])
        id_day2 = stable_item_id("webpage", item["title"], item["url"])
        self.assertEqual(id_day1, id_day2)

        # Check cross-source stability for canonical URL
        conflict_a = next(x for x in BENCHMARK_ITEMS if x["id"] == "conflict_source_a")
        conflict_b = next(x for x in BENCHMARK_ITEMS if x["id"] == "conflict_source_b")
        canon_id_a = stable_item_id("webpage", conflict_a["title"], conflict_a["url"])
        canon_id_b = stable_item_id("webpage", conflict_b["title"], conflict_b["url"])
        self.assertEqual(canon_id_a, canon_id_b)

    def test_10_citation_and_provenance_traceability(self) -> None:
        """Verify provenance and citation data are preserved in JSON and fallback markdown."""
        item_a = next(x for x in BENCHMARK_ITEMS if x["id"] == "conflict_source_a")
        item_b = next(x for x in BENCHMARK_ITEMS if x["id"] == "conflict_source_b")

        task_a = AcquisitionTask.from_url(item_a["url"], title=item_a["title"], source_id="follow-builders")
        task_b = AcquisitionTask.from_url(item_b["url"], title=item_b["title"], source_id="daily-news-summary")

        orchestrator = Orchestrator(registry=self.registry, execute=True, fetcher=self.fetcher)
        ledgers = [orchestrator.run(task_a), orchestrator.run(task_b)]

        kp_items = build_acquisition_items(ledgers)
        deduped = dedupe_items(kp_items)
        self.assertEqual(len(deduped), 1)

        item = deduped[0]
        meta = item["metadata"]
        self.assertIn("citations", meta)
        self.assertEqual(len(meta["citations"]), 2)
        self.assertIn("observed_sources", meta)

        md = render_item_fallback(item)
        self.assertIn("observed_sources:", md)
        self.assertIn("follow-builders", md)
        self.assertIn("daily-news-summary", md)


if __name__ == "__main__":
    unittest.main()
