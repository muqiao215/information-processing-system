# Progress: Acquisition Orchestrator

## 2026-04-20

- Created persistent planning files for the acquisition orchestrator work.
- Confirmed `firecrawl/web-agent` should be replicated as architecture, not configured as a simple fallback.
- Planned parallel background tasks with disjoint write scopes:
  - code/tests for acquisition orchestrator
  - docs/registry for adapter positioning
- Launched background task `7c2f6aa8` for acquisition core code/tests.
- Launched background task `4533ca6c` for acquisition docs/registry.
- Updated the documentation set to place an acquisition orchestrator layer between source collectors and `knowledge_pack`, with Firecrawl/web-agent documented as an optional adapter only.
- Added a pre-knowledge-pack acquisition orchestrator package with deterministic recipe/adapters/ledger output, a dry-run CLI, and focused acquisition tests.
- Verified with `python3 -m unittest tests/test_pipeline_fixes.py tests/test_acquisition_orchestrator.py`.
- Verified CLI dry-run with `python3 -m tools.knowledge_pipeline.acquisition --url https://example.com/article --title 'Example Article' --output /tmp/ips-acquisition-ledger.json`.
