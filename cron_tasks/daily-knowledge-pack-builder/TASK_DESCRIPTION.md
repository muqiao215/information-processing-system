# Daily Knowledge Pack Builder

## Goal

Build the phase-1 knowledge pack from AI builders digest, BuilderPulse opportunity radar, and arXiv LLM memory discovery manifests.

## Assignment

This repository file is the source-of-truth task contract. When installed into a
native ControlMesh `cron_tasks/<name>/` folder, the runtime task should call its
local wrapper `scripts/run_task.py`, which then invokes the repo-owned canonical
builder using stable absolute workspace paths.

This task is the normalization and phase-2 preprocessing layer between
acquisition cron tasks and downstream knowledge digestion.

It reads existing acquisition manifests, normalizes them into a canonical
`knowledge_pack`, and pre-processes known NotebookLM URL-ingest troublemakers
into local markdown/text before writing dated plus latest outputs.

Allowed write targets:
- `/root/.controlmesh/workspace/output_to_user`

Execution steps:
1. Read this task's memory file.
2. Prefer the installed runtime wrapper:
   - `python3 scripts/run_task.py`
3. If you are running directly from this repository instead of an installed
   ControlMesh cron task folder, confirm the three upstream manifest paths and note which exist:
   - `/root/.controlmesh/workspace/output_to_user/ai_builders_digest_sources_latest.json`
   - `/root/.controlmesh/workspace/output_to_user/builderpulse_opportunity_radar_sources_latest.json`
   - `/root/.controlmesh/workspace/output_to_user/arxiv_llm_memory_discovery_latest.json`
4. Run the canonical builder:
   - `cd /root/.controlmesh/workspace && python3 repos/information-processing-system/tools/knowledge_pipeline/normalization/build_knowledge_pack.py`
5. The builder must:
   - normalize `follow-builders` selected sources
   - normalize `BuilderPulse` opportunity radar selected sections
   - normalize the selected `arxiv-llm-memory-discovery` paper when present
   - pre-process `x.com`, `raw.githubusercontent.com`, and arXiv PDF sources
     into local markdown/text when possible
   - put local `markdown_file` import targets before direct URL targets
   - record each item's `preprocess` metadata and `local_text_path`
   - write fallback markdown containing enough text for NotebookLM when URL import fails
   - continue if one upstream manifest is missing, but fail if all upstream manifests are missing or empty
6. Verify these files exist:
   - `/root/.controlmesh/workspace/output_to_user/knowledge_pack_latest.json`
   - `/root/.controlmesh/workspace/output_to_user/knowledge_pack_latest.md`
   - `/root/.controlmesh/workspace/output_to_user/knowledge_pack_YYYYMMDD.json`
   - `/root/.controlmesh/workspace/output_to_user/knowledge_pack_YYYYMMDD.md`
   - `/root/.controlmesh/workspace/output_to_user/information_pipeline/bundles/YYYY-MM-DD/knowledge_pack.json`
   - `/root/.controlmesh/workspace/output_to_user/information_pipeline/bundles/YYYY-MM-DD/knowledge_pack.md`
   - `/root/.controlmesh/workspace/output_to_user/information_pipeline/preprocessed/YYYY-MM-DD/*.md`
7. Parse `/root/.controlmesh/workspace/output_to_user/knowledge_pack_latest.json` and verify:
   - `item_count` equals `len(items)`
   - every item has `item_id`, `source_id`, `title`, `summary`, `import_targets`,
     `import_policy`, `preprocess`, and `fallback_content`
   - `source_counts` is present
   - `preprocessing_summary` is present
8. Report missing upstream manifests as warnings, not as failure, unless no items were produced.

Important:
- Do not call external messaging tools.
- Do not create NotebookLM notebooks here.
- Do not trigger reports, videos, slide decks, or publishing here.
- This job should not use Chrome or NotebookLM browser resources.
- Phase-2 preprocessing may use public no-key fetch routes such as `r.jina.ai`
  and `defuddle.md`, plus direct browser-like fetch fallback. Do not add paid
  API keys or new authentication requirements for this task.
- `knowledge_pack_latest.json` is now the canonical input for downstream
  `daily-notebooklm-content-gen`.

## Output

Return a concise Chinese result:
- 哪些 upstream manifest 存在 / 缺失
- `knowledge_pack_latest.json` 是否写入成功
- `knowledge_pack_latest.md` 是否写入成功
- 日期化 pipeline 路径是否写入成功
- phase-2 preprocessing 本地化了哪些 source_type
- `item_count`
- `source_counts`
- 如果失败：明确 blocker 和原始错误
