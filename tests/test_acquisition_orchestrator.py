from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.knowledge_pipeline.acquisition import (  # noqa: E402
    AcquisitionTask,
    Orchestrator,
    default_registry,
    select_recipe,
)


class AcquisitionOrchestratorTests(unittest.TestCase):
    def test_recipe_selection_prefers_public_webpage_for_url_tasks(self) -> None:
        task = AcquisitionTask(
            task_id="task-1",
            source_type="webpage",
            task_kind="fetch",
            url="https://example.com/article",
            title="Example Article",
        )

        recipe = select_recipe(task)

        self.assertEqual(recipe.recipe_id, "public_webpage_default")
        self.assertEqual(recipe.step_names_without_disabled(env={}), [
            "jina_reader",
            "defuddle",
            "direct_browser_ua",
            "amp",
            "archive_today",
            "agent_fetch",
        ])

    def test_default_cascade_order_excludes_firecrawl_without_api_key(self) -> None:
        task = AcquisitionTask.from_url("https://example.com/post", task_id="task-2")
        orchestrator = Orchestrator(registry=default_registry(), env={})

        ledger = orchestrator.run(task)

        self.assertEqual([attempt.adapter for attempt in ledger.attempts], [
            "jina_reader",
            "defuddle",
            "direct_browser_ua",
            "amp",
            "archive_today",
            "agent_fetch",
        ])
        self.assertNotIn("firecrawl_web_agent", [attempt.adapter for attempt in ledger.attempts])

    def test_firecrawl_adapter_is_disabled_when_api_key_absent(self) -> None:
        registry = default_registry()
        adapter = registry.adapters["firecrawl_web_agent"]

        self.assertFalse(adapter.is_enabled(env={}))
        self.assertFalse(adapter.is_enabled(env={"FIRECRAWL_API_KEY": ""}))
        self.assertTrue(adapter.is_enabled(env={"FIRECRAWL_API_KEY": "fc-test"}))

    def test_ledger_json_shape_is_suitable_for_later_knowledge_pack_promotion(self) -> None:
        task = AcquisitionTask.from_url(
            "https://example.com/research",
            task_id="task-ledger",
            title="Research Item",
        )
        orchestrator = Orchestrator(registry=default_registry(), env={})

        ledger = orchestrator.run(task)
        payload = ledger.to_dict()
        encoded = json.dumps(payload, sort_keys=True)

        self.assertIn("run_id", payload)
        self.assertEqual(payload["task"]["task_id"], "task-ledger")
        self.assertEqual(payload["recipe_id"], "public_webpage_default")
        self.assertEqual(payload["status"], "attempted")
        self.assertEqual(payload["source_candidates"][0]["url"], "https://example.com/research")
        self.assertEqual(payload["attempts"][0]["adapter"], "jina_reader")
        self.assertEqual(payload["attempts"][0]["status"], "not_executed")
        self.assertEqual(payload["promoted_items"], [])
        self.assertIn("knowledge_pack_candidate", encoded)


if __name__ == "__main__":
    unittest.main()
