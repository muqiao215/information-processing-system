# Daily NotebookLM Report Generation

## Goal

Generate the daily NotebookLM report from the latest canonical `knowledge_pack`
using the `notebooklm` CLI with the shared Chrome CDP endpoint.

This task is report-only. A report successfully generated and downloaded to
`output_to_user` is the success gate. Do not generate video or slide deck here;
those are handled by the separate `daily-notebooklm-artifact-trigger` cron.

## Assignment

This task depends on:
- `daily-knowledge-pack-builder` or equivalent pack builder having produced
  `/root/.controlmesh/workspace/output_to_user/knowledge_pack_latest.json`
- Chrome CDP being available at `127.0.0.1:9222`
- a working NotebookLM login state for that browser

Allowed write targets:
- `/root/.controlmesh/workspace/output_to_user`
- NotebookLM notebooks and report artifact via the CLI

Execution steps:
1. Read this task's memory file.
2. Check browser/CDP readiness:
   - `ss -ltn '( sport = :9222 )'`
   - `notebooklm --host 127.0.0.1 --port 9222 browser status --json`
   - `notebooklm --host 127.0.0.1 --port 9222 auth status --json`
3. If CDP or auth is not ready, stop and report the blocker cleanly. Do not fake success.
4. Prefer reading `/root/.controlmesh/workspace/output_to_user/knowledge_pack_latest.json`.
   - This is the canonical multi-source pack for NotebookLM digestion.
   - If it is missing, fall back once to
     `/root/.controlmesh/workspace/output_to_user/ai_builders_digest_sources_latest.json`
     in legacy-compat mode and clearly note that the run did not use the canonical pack.
   - If neither exists, report the blocker and stop.
5. Create one notebook for today's selected knowledge set.
6. Import sources from the canonical pack.
   - For `knowledge_pack`, read each item's `import_targets`.
   - Prefer local `markdown_file` targets first when present.
   - If no local file target exists for an item, fall back to URL targets.
   - If URL import is partially skipped, especially `x.com` returning
     `http_403`, do not fail the run immediately.
   - Use each item's `preprocess.status` and `local_text_path` as the first
     signal of whether the source was already localized by the pack builder.
   - Use the pack's fallback markdown when available:
     `/root/.controlmesh/workspace/output_to_user/knowledge_pack_latest.md`
     or the dated fallback path recorded in `fallback_markdown_path`.
   - Import that fallback markdown as a NotebookLM source so the report can still be generated.
   - In legacy mode, keep the existing digest-manifest fallback behavior.
7. Generate and download the primary report:
   - `generate report --format briefing_doc`
   - wait for the report until ready using a reasonable bounded timeout
   - download it to `/root/.controlmesh/workspace/output_to_user/notebooklm_report_YYYYMMDD.md`
8. Write a run metadata file for the follow-up artifact trigger task:
   - dated:
     `/root/.controlmesh/workspace/output_to_user/notebooklm_report_run_YYYYMMDD.json`
   - latest:
     `/root/.controlmesh/workspace/output_to_user/notebooklm_report_run_latest.json`
9. Report exactly what was generated and what paths were written.

Important:
- Use the `notebooklm` CLI from `PATH`.
- Use the unified server browser endpoint `127.0.0.1:9222`; do not probe the retired `19800` port.
- Use `generate report`, not the old invalid `generate summary`.
- Do not generate `slide-deck` or `video` in this task.
- Treat report download as the only success gate for this daily task.
- Date semantics are explicit:
  - `run_date`: the local calendar date in `Asia/Shanghai` when this wrapper runs
  - `data_date`: the knowledge-pack date being reported
  - `report_date`: same as `data_date` for this task
  - artifact filenames are keyed by `data_date`, not UTC wall-clock date
- Chrome/CDP access must be protected by the file lock
  `~/.controlmesh/locks/notebooklm_chrome.lock`. Scheduler dependencies are
  hints only; process-level locking is mandatory.

Run metadata JSON should include:
- `date`
- `report_date`
- `data_date`
- `run_date`
- `timezone`
- `artifact_date_basis`
- `notebook_id`
- `notebook_title`
- `report_artifact_id`
- `report_path`
- `knowledge_pack_path`
- `legacy_source_manifest_path` if legacy mode was used
- `source_import_summary`
- `fallback_source_path` if used
- `created_at`
- `notes`

## Output

Return a concise Chinese result:
- browser/CDP 是否可用
- NotebookLM auth 是否可用
- knowledge_pack 是否存在
- 是否退回 legacy manifest 兼容模式
- notebook 是否创建成功
- report 是否生成并成功落盘
- 成功写入了哪些文件路径
- 是否写出 `notebooklm_report_run_latest.json`
- 如果失败：明确阻塞点
