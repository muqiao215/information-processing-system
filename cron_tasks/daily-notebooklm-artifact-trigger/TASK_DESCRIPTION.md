# Daily NotebookLM Artifact Trigger

## Goal

Trigger NotebookLM slide deck and video generation from the latest daily report
notebook metadata.

This task only starts optional artifacts. It does not wait for readiness and
does not download the artifacts. For slide deck and video, a successful
generation request that returns an artifact id counts as success.

Artifact readiness waiting and binary download belong to the follow-up
`daily-notebooklm-artifact-harvest` task. Keep this task fast and purely
request-oriented.

## Assignment

This task depends on:
- the report task having written
  `/root/.controlmesh/workspace/output_to_user/notebooklm_report_run_latest.json`
- Chrome CDP being available at `127.0.0.1:9222`
- a working NotebookLM login state for that browser

Allowed write targets:
- `/root/.controlmesh/workspace/output_to_user`
- NotebookLM slide deck and video generation requests via the CLI

Execution steps:
1. Read this task's memory file.
2. Read `/root/.controlmesh/workspace/output_to_user/notebooklm_report_run_latest.json`.
   If missing, stop and report that the report task has not produced notebook metadata yet.
3. Extract at minimum:
   - `date`
   - `notebook_id`
   - `notebook_title`
   - `report_artifact_id`
   - `report_path`
4. Check browser/CDP readiness:
   - `ss -ltn '( sport = :9222 )'`
   - `notebooklm --host 127.0.0.1 --port 9222 browser status --json`
   - `notebooklm --host 127.0.0.1 --port 9222 auth status --json`
5. If CDP or auth is not ready, stop and report the blocker cleanly. Do not fake success.
6. Check whether today's trigger metadata already exists:
   - `/root/.controlmesh/workspace/output_to_user/notebooklm_artifact_trigger_YYYYMMDD.json`
   - If it exists and has both `slide_deck_artifact_id` and `video_artifact_id`
     for the same `notebook_id`, do not create duplicates. Report `already_triggered`.
7. Trigger slide deck generation:
   - `notebooklm --host 127.0.0.1 --port 9222 generate slide-deck -n <notebook_id> --json`
   - Success means the command returns normally with an artifact id or equivalent accepted artifact payload.
   - Do not wait for readiness.
   - Do not download.
8. Trigger video generation:
   - `notebooklm --host 127.0.0.1 --port 9222 generate video -n <notebook_id> --json`
   - Success means the command returns normally with an artifact id or equivalent accepted artifact payload.
   - Do not wait for readiness.
   - Do not download.
9. Write trigger metadata:
   - dated:
     `/root/.controlmesh/workspace/output_to_user/notebooklm_artifact_trigger_YYYYMMDD.json`
   - latest:
     `/root/.controlmesh/workspace/output_to_user/notebooklm_artifact_trigger_latest.json`
10. Report exactly which generation requests were accepted and which artifact ids were returned.
11. Leave the returned artifact ids intact for the downstream harvest task:
   - it will read `notebooklm_artifact_trigger_latest.json`
   - it will wait for readiness and download slide/video into
     `/root/.controlmesh/workspace/output_to_user/information_pipeline/artifacts/YYYY-MM-DD/`

Important:
- Use the `notebooklm` CLI from `PATH`.
- Use the unified server browser endpoint `127.0.0.1:9222`; do not probe the retired `19800` port.
- Use `generate slide-deck`, not the old invalid `generate ppt`.
- Use `generate video` for the video request.
- Do not run `artifact wait`.
- Do not run `download video`.
- Do not run `download slide-deck`.
- Do not absorb harvest logic back into this task; the trigger/harvest split is intentional.
- For this task, `accepted` / artifact id returned = success. Artifact readiness is outside this task.

Trigger metadata JSON should include:
- `date`
- `notebook_id`
- `notebook_title`
- `report_artifact_id`
- `report_path`
- `slide_deck_artifact_id`
- `video_artifact_id`
- `triggered_at`
- `status`
- `notes`

## Output

Return a concise Chinese result:
- report metadata 是否存在
- browser/CDP 是否可用
- NotebookLM auth 是否可用
- notebook id
- slide deck 是否触发成功及 artifact id
- video 是否触发成功及 artifact id
- 成功写入了哪些 metadata 文件
- 如果失败：明确阻塞点和原始命令/错误
