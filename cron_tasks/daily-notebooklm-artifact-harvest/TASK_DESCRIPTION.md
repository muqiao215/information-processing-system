# Daily NotebookLM Artifact Harvest

## Goal

Wait for the NotebookLM slide deck and video artifacts triggered by
`daily-notebooklm-artifact-trigger`, download them into the dated information
pipeline artifact folder, and write harvest metadata.

This task is the second phase of the NotebookLM optional artifact lifecycle. It
does not create notebooks, import sources, generate reports, or trigger new
slide/video generation requests.

## Assignment

This task depends on:

- the artifact trigger task having written
  `/root/.ductor/workspace/output_to_user/notebooklm_artifact_trigger_latest.json`
- Chrome CDP being available at `127.0.0.1:9222`
- a working NotebookLM login state for that browser

Allowed write targets:

- `/root/.ductor/workspace/cron_tasks/daily-notebooklm-artifact-harvest/`
- `/root/.ductor/workspace/output_to_user/notebooklm_artifact_harvest_YYYYMMDD.json`
- `/root/.ductor/workspace/output_to_user/notebooklm_artifact_harvest_latest.json`
- `/root/.ductor/workspace/output_to_user/information_pipeline/artifacts/YYYY-MM-DD/`

Execution steps:

1. Read this task's memory file if present.
2. Read the whole `TASK_DESCRIPTION.md`.
3. Run the harvest helper:

   ```bash
   cd /root/.ductor/workspace
   python3 cron_tasks/daily-notebooklm-artifact-harvest/scripts/harvest_notebooklm_artifacts.py
   ```

4. The helper must read:

   ```text
   /root/.ductor/workspace/output_to_user/notebooklm_artifact_trigger_latest.json
   ```

5. Extract at minimum:

   - `date`
   - `notebook_id`
   - `notebook_title`
   - `report_artifact_id`
   - `report_path`
   - `slide_deck_artifact_id`
   - `video_artifact_id`

6. Check browser/CDP readiness before waiting or downloading:

   - `ss -ltn '( sport = :9222 )'`
   - `cd /root/.ductor/workspace/notebooklm-cdp-cli && uv run notebooklm --host 127.0.0.1 --port 9222 browser status --json`
   - `cd /root/.ductor/workspace/notebooklm-cdp-cli && uv run notebooklm --host 127.0.0.1 --port 9222 auth status --json`

7. If CDP or auth is not ready, stop after writing harvest metadata with
   `status: blocked`. Do not fake success.
8. Wait for the slide deck artifact and download it to:

   ```text
   /root/.ductor/workspace/output_to_user/information_pipeline/artifacts/YYYY-MM-DD/YYYYMMDD-slide-deck-<artifact_id>.pdf
   ```

   Use:

   ```bash
   cd /root/.ductor/workspace/notebooklm-cdp-cli
   uv run notebooklm --host 127.0.0.1 --port 9222 artifact wait <slide_deck_artifact_id> -n <notebook_id> --json
   uv run notebooklm --host 127.0.0.1 --port 9222 download slide-deck <output.pdf> -n <notebook_id> --artifact-id <slide_deck_artifact_id> --format pdf --json
   ```

9. Wait for the video artifact and download it to:

   ```text
   /root/.ductor/workspace/output_to_user/information_pipeline/artifacts/YYYY-MM-DD/YYYYMMDD-video-<artifact_id>.mp4
   ```

   Use:

   ```bash
   cd /root/.ductor/workspace/notebooklm-cdp-cli
   uv run notebooklm --host 127.0.0.1 --port 9222 artifact wait <video_artifact_id> -n <notebook_id> --json
   uv run notebooklm --host 127.0.0.1 --port 9222 download video <output.mp4> -n <notebook_id> --artifact-id <video_artifact_id> --json
   ```

10. The helper is allowed to retry direct download after bounded waits because
    NotebookLM can expose an artifact before the binary download endpoint is
    ready.
11. Preserve idempotency:

    - If a target artifact file already exists and is non-empty, reuse it and
      mark that artifact as `already_downloaded`.
    - Do not trigger duplicate slide or video generation from this task.
    - Use `--force` only for manual recovery when a known bad file must be
      replaced.

12. Write harvest metadata:

    - dated:
      `/root/.ductor/workspace/output_to_user/notebooklm_artifact_harvest_YYYYMMDD.json`
    - latest:
      `/root/.ductor/workspace/output_to_user/notebooklm_artifact_harvest_latest.json`

13. Update `daily-notebooklm-artifact-harvest_MEMORY.md` with the current
    date/time and what happened.

Important:

- Use `/root/.ductor/workspace/notebooklm-cdp-cli`, never `/root/.conductor/...`.
- Use the unified server browser endpoint `127.0.0.1:9222`; do not probe the retired `19800` port.
- Use existing NotebookLM CLI commands only. Do not introduce another browser automation stack.
- Use `download slide-deck`, not `download ppt`.
- Use `download video` for the video artifact.
- Do not generate or regenerate report, slide deck, or video in this task.
- Treat missing trigger metadata, missing artifact ids, missing CDP, or broken auth as blockers.
- Treat artifact wait/download timeout as `pending` or `partial`, not as success.

Harvest metadata JSON must include at least:

- `date`
- `notebook_id`
- `notebook_title`
- `report_artifact_id`
- `report_path`
- `slide_deck_artifact_id`
- `video_artifact_id`
- `slide_deck_status`
- `video_status`
- `downloaded_paths`
- `harvested_at`
- `notes`

Additional fields such as `status`, `artifact_dir`, `preflight`,
`artifact_results`, and `metadata_paths` are allowed and recommended.

## Output

Return a concise Chinese result:

- trigger metadata 是否存在
- browser/CDP 是否可用
- NotebookLM auth 是否可用
- notebook id
- slide deck wait/download 状态和文件路径
- video wait/download 状态和文件路径
- 成功写入了哪些 harvest metadata 文件
- 如果失败或 pending：明确阻塞点、artifact id、原始命令/错误摘要

## Suggested Cron Registration

This folder is prepared for later registration by the main agent.

Recommended registration:

- schedule: `50 10 * * *` (`10:50 Asia/Shanghai`)
- provider: `codex`
- model: `gpt-5.4`
- reasoning effort: `high`
- dependency: `chrome_browser`
- order: after `daily-notebooklm-artifact-trigger` at `10:35 Asia/Shanghai`

Rationale: slide deck and video generation are asynchronous. A 10-15 minute gap
keeps the trigger task fast while giving NotebookLM time to make artifacts
downloadable. If video routinely remains pending, move harvest later or add a
second late retry job instead of making the trigger task block.
