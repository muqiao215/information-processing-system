---
doc_type: reference
entity: notebooklm-artifact-trigger 下游消费者
status: active
owner: Muqiao
last_verified: 2026-04-19
---

# notebooklm-artifact-trigger

## Identity

| 字段 | 值 |
| --- | --- |
| consumer_id | `notebooklm-artifact-trigger` |
| cron_id | `daily-notebooklm-artifact-trigger` |
| layer | `artifact generator` |
| schedule | `10:35 Asia/Shanghai` |
| upstream consumer | [[notebooklm-report]] |
| downstream consumer | [[notebooklm-artifact-harvest]] |
| browser endpoint | `127.0.0.1:9222` |

## Input Contract

| 字段 | 值 |
| --- | --- |
| input_source | `/root/.controlmesh/workspace/output_to_user/notebooklm_report_run_latest.json` |
| access_path | NotebookLM CLI + Chrome CDP |
| success_gate | generation request accepted and artifact id returned |

## Output Contract

输出语义：

- slide deck generation request metadata
- video generation request metadata
- async pending 状态 when artifact is not ready
- harvest follow-up 所需 artifact ids

Canonical outputs:

- `/root/.controlmesh/workspace/output_to_user/notebooklm_artifact_trigger_YYYYMMDD.json`
- `/root/.controlmesh/workspace/output_to_user/notebooklm_artifact_trigger_latest.json`

Downstream handoff:

- `daily-notebooklm-artifact-harvest` 读取 latest trigger metadata。
- harvest 负责等待 readiness 与下载，不回流到 trigger。
- artifact 文件落点是 `/root/.controlmesh/workspace/output_to_user/information_pipeline/artifacts/YYYY-MM-DD/`。

## Failure Behavior

- 不把 slide / video 未就绪视为 report 主任务失败。
- 请求被接受但 artifact 未生成完成时，按 `async_pending` 记录。
- 只有生成请求被接受并返回 artifact id 才算成功。
- 不在本任务里执行 `artifact wait`、`download slide-deck` 或 `download video`。

## Registry

- 注册表入口：[[../信息源注册表]]
- 总览入口：[[../信息源采集总览]]
