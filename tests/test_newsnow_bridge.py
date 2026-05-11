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


class NewsnowBridgeTests(unittest.TestCase):
    def test_build_source_url_preserves_vendor_http_boundary(self) -> None:
        module = load_module(
            "fetch_newsnow_snapshot",
            "cron_tasks/daily-news-summary-7am/scripts/fetch_newsnow_snapshot.py",
        )

        url = module.build_source_url("http://127.0.0.1:3000/", "ithome")

        self.assertEqual(url, "http://127.0.0.1:3000/api/s?id=ithome&latest=")

    def test_normalize_item_keeps_stable_subset(self) -> None:
        module = load_module(
            "fetch_newsnow_snapshot",
            "cron_tasks/daily-news-summary-7am/scripts/fetch_newsnow_snapshot.py",
        )
        item = {
            "id": "abc",
            "title": "Hello",
            "url": "https://example.com",
            "mobileUrl": "https://m.example.com",
            "pubDate": 123,
            "extra": {"hover": "desc", "date": 456, "info": "meta", "diff": 1},
        }

        normalized = module.normalize_item("ithome", item)

        self.assertEqual(normalized["source_id"], "ithome")
        self.assertEqual(normalized["title"], "Hello")
        self.assertEqual(normalized["extra"]["hover"], "desc")

    def test_main_writes_manifest(self) -> None:
        module = load_module(
            "fetch_newsnow_snapshot",
            "cron_tasks/daily-news-summary-7am/scripts/fetch_newsnow_snapshot.py",
        )

        def fake_fetch_source(base_url: str, source_id: str, limit: int) -> dict:
            return {
                "source_id": source_id,
                "status": "success",
                "updated_time": 123,
                "item_count": 1,
                "items": [{"id": "1", "title": "x", "url": "u", "mobile_url": None, "published_at": None, "extra": {}, "source_id": source_id}],
                "request_url": f"{base_url}/api/s?id={source_id}&latest=",
            }

        original_fetch_source = module.fetch_source
        try:
            module.fetch_source = fake_fetch_source
            with tempfile.TemporaryDirectory() as tmp_dir:
                out = Path(tmp_dir) / "newsnow.json"
                argv = sys.argv
                sys.argv = [
                    "fetch_newsnow_snapshot.py",
                    "--base-url",
                    "http://127.0.0.1:3000",
                    "--source-id",
                    "ithome",
                    "--output",
                    str(out),
                ]
                try:
                    rc = module.main()
                finally:
                    sys.argv = argv

                payload = json.loads(out.read_text(encoding="utf-8"))
        finally:
            module.fetch_source = original_fetch_source

        self.assertEqual(rc, 0)
        self.assertEqual(payload["source"], "newsnow")
        self.assertEqual(payload["source_ids"], ["ithome"])
        self.assertEqual(payload["total_item_count"], 1)

    def test_default_source_ids_are_hackernews_only(self) -> None:
        module = load_module(
            "fetch_newsnow_snapshot_defaults",
            "cron_tasks/daily-news-summary-7am/scripts/fetch_newsnow_snapshot.py",
        )

        self.assertEqual(module.DEFAULT_SOURCE_IDS, ["hackernews"])


if __name__ == "__main__":
    unittest.main()
