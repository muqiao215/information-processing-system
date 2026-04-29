---
doc_type: reference
entity: notebooklm-report 下游消费者
status: active
owner: Muqiao
last_verified: 2026-04-19
---

# notebooklm-report

## Identity

| 字段 | 值 |
| --- | --- |
| consumer_id | `notebooklm-report` |
| cron_id | `daily-notebooklm-content-gen` |
| layer | `artifact generator` |
| schedule | `10:20 Asia/Shanghai` |
| task description | `/root/.controlmesh/workspace/cron_tasks/daily-notebooklm-content-gen/TASK_DESCRIPTION.md` |
| browser endpoint | `127.0.0.1:9222` |

## Input Contract

| 字段 | 值 |
| --- | --- |
| input_source | `/root/.controlmesh/workspace/output_to_user/knowledge_pack_latest.json` |
| legacy fallback | `/root/.controlmesh/workspace/output_to_user/ai_builders_digest_sources_latest.json` |
| upstream source | [[../Adapters/notebooklm-source-pack]] |
| access_path | NotebookLM CLI + Chrome CDP |
| success_gate | report 成功生成并下载到 `output_to_user` |

## Output Contract

Canonical outputs:

- `/root/.controlmesh/workspace/output_to_user/notebooklm_report_YYYYMMDD.md`
- `/root/.controlmesh/workspace/output_to_user/notebooklm_report_run_YYYYMMDD.json`
- `/root/.controlmesh/workspace/output_to_user/notebooklm_report_run_latest.json`

Run metadata must include:

- `date`
- `notebook_id`
- `notebook_title`
- `report_artifact_id`
- `report_path`
- `knowledge_pack_path`
- `legacy_source_manifest_path` when legacy mode is used
- `source_import_summary`
- `fallback_source_path` when used
- `created_at`
- `notes`

## Failure Behavior

- CDP 不可用时停止并报告 blocker。
- NotebookLM auth 不可用时停止并报告 blocker。
- `knowledge_pack_latest.json` 缺失时允许一次性退回 legacy builders manifest，并必须写明 compatibility mode。
- `knowledge_pack_latest.json` 与 legacy manifest 都缺失时停止并报告 blocker。
- URL import 部分失败时，尤其 `x.com` 403，可写 fallback markdown source 并继续生成 report。
- 不生成 slide deck 或 video；这些属于 [[notebooklm-artifact-trigger]]。

## Registry

- 注册表入口：[[../信息源注册表]]
- 总览入口：[[../信息源采集总览]]
