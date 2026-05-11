from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    module_dir = str(module_path.parent)
    inserted = False
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
        inserted = True
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and sys.path and sys.path[0] == module_dir:
            sys.path.pop(0)


class BuildDigestOutputsCliTests(unittest.TestCase):
    def test_load_bundle_accepts_explicit_path(self) -> None:
        module = load_module(
            "build_digest_outputs",
            "cron_tasks/ai-builders-digest-5briefs/scripts/build_digest_outputs.py",
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            bundle_path = Path(tmp_dir) / "bundle.json"
            bundle_path.write_text('{"generatedAt":"2026-05-11T00:00:00Z"}', encoding="utf-8")

            bundle = module.load_bundle(bundle_path)

        self.assertEqual(bundle["generatedAt"], "2026-05-11T00:00:00Z")


class ArxivCompatibilityTests(unittest.TestCase):
    def test_utc_alias_is_timezone_utc(self) -> None:
        module = load_module(
            "discover_llm_memory_paper",
            "skills/arxiv-llm-memory-discovery/scripts/discover_llm_memory_paper.py",
        )

        self.assertEqual(module.UTC.utcoffset(None), module.timezone.utc.utcoffset(None))


class WorkspaceResolutionTests(unittest.TestCase):
    def test_build_knowledge_pack_supports_repo_under_repos_dir(self) -> None:
        module = load_module(
            "build_knowledge_pack",
            "tools/knowledge_pipeline/normalization/build_knowledge_pack.py",
        )
        repo_root = Path("/srv/workspace/repos/information-processing-system")

        workspace = module.resolve_workspace_root(repo_root)

        self.assertEqual(workspace, Path("/srv/workspace"))


if __name__ == "__main__":
    unittest.main()
