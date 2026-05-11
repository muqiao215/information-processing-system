from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class NewsnowCandidatePoolTests(unittest.TestCase):
    def test_scores_ai_titles_above_zero(self) -> None:
        module = load_module(
            "build_newsnow_candidate_pool",
            "cron_tasks/daily-news-summary-7am/scripts/build_newsnow_candidate_pool.py",
        )

        score, signals = module.score_item(
            "hackernews",
            {"title": "OpenAI Codex and local AI agents", "extra": {"info": "240 points"}},
        )

        self.assertGreater(score, 0)
        self.assertIn("source:hackernews", signals)

    def test_filters_low_signal_consumer_titles(self) -> None:
        module = load_module(
            "build_newsnow_candidate_pool",
            "cron_tasks/daily-news-summary-7am/scripts/build_newsnow_candidate_pool.py",
        )

        score, signals = module.score_item(
            "ithome",
            {"title": "比亚迪推出 SUV 车机屏幕小换大服务", "extra": {}},
        )

        self.assertLessEqual(score, 0)
        self.assertTrue(any(signal.startswith("blocked:") for signal in signals))

    def test_main_writes_candidate_pool(self) -> None:
        module = load_module(
            "build_newsnow_candidate_pool",
            "cron_tasks/daily-news-summary-7am/scripts/build_newsnow_candidate_pool.py",
        )
        manifest = {
            "results": [
                {
                    "source_id": "hackernews",
                    "items": [
                        {
                            "title": "Local AI needs to be the norm",
                            "url": "https://news.ycombinator.com/item?id=1",
                            "published_at": None,
                            "extra": {"info": "588 points"},
                        }
                    ],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            in_path = Path(tmp_dir) / "in.json"
            out_path = Path(tmp_dir) / "out.json"
            in_path.write_text(json.dumps(manifest), encoding="utf-8")
            argv = sys.argv
            sys.argv = [
                "build_newsnow_candidate_pool.py",
                "--input",
                str(in_path),
                "--output",
                str(out_path),
            ]
            try:
                rc = module.main()
            finally:
                sys.argv = argv

            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(payload["candidate_count"], 1)
        self.assertTrue(payload["usage_contract"]["must_read_full_body"])
        self.assertEqual(payload["allowed_source_ids"], ["hackernews"])

    def test_default_allowed_sources_only_keep_hackernews(self) -> None:
        module = load_module(
            "build_newsnow_candidate_pool_default_sources",
            "cron_tasks/daily-news-summary-7am/scripts/build_newsnow_candidate_pool.py",
        )
        manifest = {
            "results": [
                {
                    "source_id": "ithome",
                    "items": [
                        {
                            "title": "OpenAI 发布新模型",
                            "url": "https://example.com/1",
                            "published_at": None,
                            "extra": {},
                        }
                    ],
                },
                {
                    "source_id": "hackernews",
                    "items": [
                        {
                            "title": "Local AI needs to be the norm",
                            "url": "https://example.com/2",
                            "published_at": None,
                            "extra": {"info": "100 points"},
                        }
                    ],
                },
            ]
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            in_path = Path(tmp_dir) / "in.json"
            out_path = Path(tmp_dir) / "out.json"
            in_path.write_text(json.dumps(manifest), encoding="utf-8")
            argv = sys.argv
            sys.argv = [
                "build_newsnow_candidate_pool.py",
                "--input",
                str(in_path),
                "--output",
                str(out_path),
            ]
            try:
                rc = module.main()
            finally:
                sys.argv = argv

            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(list(payload["groups"].keys()), ["hackernews"])


if __name__ == "__main__":
    unittest.main()
