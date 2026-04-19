---
doc_type: reference
entity: notebooklm-artifact-harvest 下游消费者
status: active
owner: Muqiao
last_verified: 2026-04-19
---

# notebooklm-artifact-harvest

## Identity

| 字段 | 值 |
| --- | --- |
| consumer_id | `notebooklm-artifact-harvest` |
| cron_id | `daily-notebooklm-artifact-harvest` |
| layer | `artifact harvester` |
| suggested schedule | `10:50 Asia/Shanghai` |
| upstream consumer | [[notebooklm-artifact-trigger]] |
| task description | `/root/.ductor/workspace/cron_tasks/daily-notebooklm-artifact-harvest/TASK_DESCRIPTION.md` |
| browser endpoint | `127.0.0.1:9222` |

## Input Contract

| 字段 | 值 |
| --- | --- |
| input_source | `/root/.ductor/workspace/output_to_user/notebooklm_artifact_trigger_latest.json` |
| access_path | NotebookLM CLI + Chrome CDP |
| success_gate | slide deck / video 成功下载，或明确写出 pending / blocker metadata |

## Output Contract

Canonical outputs:

- `/root/.ductor/workspace/output_to_user/notebooklm_artifact_harvest_YYYYMMDD.json`
- `/root/.ductor/workspace/output_to_user/notebooklm_artifact_harvest_latest.json`
- `/root/.ductor/workspace/output_to_user/information_pipeline/artifacts/YYYY-MM-DD/YYYYMMDD-slide-deck-<artifact_id>.pdf`
- `/root/.ductor/workspace/output_to_user/information_pipeline/artifacts/YYYY-MM-DD/YYYYMMDD-video-<artifact_id>.mp4`

Harvest metadata must include at least:

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

Recommended extra fields:

- `status`
- `artifact_dir`
- `trigger_metadata_path`
- `preflight`
- `artifact_results`
- `metadata_paths`

## Failure Behavior

- trigger metadata 缺失时停止并写 `status: blocked` metadata。
- CDP 不可用时停止并写 blocker metadata。
- NotebookLM auth 不可用时停止并写 blocker metadata。
- artifact id 缺失时标记对应 artifact 为 `missing_artifact_id`，不伪造下载成功。
- `artifact wait` 已完成但下载端点仍未就绪时，允许 bounded retry direct download。
- bounded retry 后仍不可下载时，按 `pending` 或 `partial` 写 metadata，不把 trigger 阶段回滚。

## Notes

- harvest 只消费 trigger metadata，不重新触发 artifact 生成。
- 浏览器体系继续复用 `notebooklm-cdp-cli` + server-browser CDP，不引入新的浏览器自动化栈。
- slide deck 建议固定下载为 `pdf`，video 下载为 `mp4`。

## Registry

- 注册表入口：[[../信息源注册表]]
- 总览入口：[[../信息源采集总览]]
