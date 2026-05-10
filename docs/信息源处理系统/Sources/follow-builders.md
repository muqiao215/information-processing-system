---
doc_type: reference
entity: follow-builders 信息源
status: active
owner: Muqiao
last_verified: 2026-04-19
---

# follow-builders

## Identity

| 字段 | 值 |
| --- | --- |
| source_id | `follow-builders` |
| cron_id | `ai-builders-digest-5briefs` |
| layer | `collector + selector + synthesizer` |
| schedule | `09:40 Asia/Shanghai` |
| skill scope | `shared-global` |
| source_of_truth | `/root/private-sync-bundle/skills-selected/follow-builders` |
| runtime view | `/root/.controlmesh/workspace/skills/follow-builders` |
| task description | `/root/.controlmesh/workspace/cron_tasks/ai-builders-digest-5briefs/TASK_DESCRIPTION.md` |
| collector script | `/root/.controlmesh/workspace/cron_tasks/ai-builders-digest-5briefs/scripts/fetch_follow_builders.py` |

## Source Contract

| 字段 | 值 |
| --- | --- |
| source_of_truth | builders central feed，内部混合 X / Twitter、YouTube podcasts、blogs |
| access_path | 本地脚本 `fetch_follow_builders.py` |
| freshness_policy | 每次运行读取 central feed 当前 bundle |
| selection_policy | 每栏至少选 5 个 substantial items；保留原始 source URL 到 manifest |
| output_contract | A-E 五栏中文 digest + downstream source manifest |

## Output Contract

固定五栏：

1. `A. AI前沿与工具`
2. `B. 创业与战略`
3. `C. 产品与体验`
4. `D. 行业与观点`
5. `E. 技术实践`

Canonical outputs:

- `/root/.controlmesh/workspace/output_to_user/ai_builders_digest_latest.md`
- `/root/.controlmesh/workspace/output_to_user/ai_builders_digest_sources_latest.json`

## Downstream Consumers

- [[../Consumers/notebooklm-report]]
- [[../Consumers/notebooklm-artifact-trigger]]

## Failure Behavior

- feed 加载失败时在报告中明确说明。
- 不直接创建 NotebookLM notebook。
- 不调用外部消息工具，由 workspace cron 负责投递。

## Registry

- 注册表入口：[[../信息源注册表]]
- 总览入口：[[../信息源采集总览]]
