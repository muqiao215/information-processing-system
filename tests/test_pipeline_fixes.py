from __future__ import annotations

import importlib.util
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


class BuilderPulseParsingTests(unittest.TestCase):
    def test_parse_report_supports_english_builderpulse_layout(self) -> None:
        module = load_module(
            "build_builderpulse_radar",
            "cron_tasks/daily-builderpulse-opportunity-radar/scripts/build_builderpulse_radar.py",
        )
        sample_report = """# BuilderPulse Daily — April 19, 2026

## 📝 Liu Xiaopai says

First intro paragraph for the daily headline.

## 🎯 Today's one 2-hour build

**CloudExit** — compare providers and estimate savings.

## Top 3 signals

1. First signal.
2. Second signal.
3. Third signal.

---

## Discovery

### What solo-founder products launched today?

**🔍 Signal**: Launch signal.
**Key Judgment**: Strong wedge.
**Counter-view**: Retention risk.
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            report_path = Path(tmp_dir) / "en" / "2026" / "2026-04-19.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(sample_report, encoding="utf-8")

            report = module.parse_report(report_path, "https://example.com/report")

        self.assertEqual(report["language"], "en")
        self.assertEqual(report["headline"], "First intro paragraph for the daily headline.")
        self.assertEqual(
            report["build_idea"],
            "CloudExit — compare providers and estimate savings.",
        )
        self.assertEqual(len(report["top_signals"]), 3)
        self.assertEqual(len(report["opportunity_sections"]), 1)
        self.assertEqual(
            report["opportunity_sections"][0]["key_judgment"],
            "Strong wedge.",
        )


class PreprocessSourceTests(unittest.TestCase):
    def test_pdf_document_candidates_do_not_fall_back_to_direct_binary_fetch(self) -> None:
        module = load_module(
            "preprocess_sources",
            "tools/knowledge_pipeline/normalization/preprocess_sources.py",
        )
        item = {
            "url": "https://example.com/files/report.pdf",
            "import_targets": [{"kind": "url", "value": "https://example.com/files/report.pdf"}],
            "metadata": {},
        }

        candidates = module.source_candidates(item, "pdf_document")

        self.assertTrue(candidates)
        self.assertNotIn(
            ("direct_browser_ua", "https://example.com/files/report.pdf"),
            candidates,
        )
        self.assertFalse(any(url == "https://example.com/files/report.pdf" for _, url in candidates))


class NotebookLmHarvestTests(unittest.TestCase):
    def test_resolve_workspace_root_falls_back_to_parent_workspace(self) -> None:
        module = load_module(
            "harvest_notebooklm_artifacts",
            "cron_tasks/daily-notebooklm-artifact-harvest/scripts/harvest_notebooklm_artifacts.py",
        )

        repo_root = REPO_ROOT
        workspace_root = module.resolve_workspace_root(repo_root)

        self.assertEqual(workspace_root, REPO_ROOT.parent)

    def test_run_command_returns_structured_result_for_missing_binary(self) -> None:
        module = load_module(
            "harvest_notebooklm_artifacts",
            "cron_tasks/daily-notebooklm-artifact-harvest/scripts/harvest_notebooklm_artifacts.py",
        )

        result = module.run_command(["definitely-missing-command-for-test"])

        self.assertEqual(result.returncode, 127)
        self.assertIn("No such file or directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
