---
doc_type: reference
entity: builderpulse-opportunity-radar 信息源
status: active
owner: Muqiao
last_verified: 2026-04-19
---

# builderpulse-opportunity-radar

## Identity

| 字段 | 值 |
| --- | --- |
| source_id | `builderpulse-opportunity-radar` |
| cron_id | `daily-builderpulse-opportunity-radar` |
| layer | `collector + selector + synthesizer` |
| schedule | `10:10 Asia/Shanghai` |
| upstream repo | `BuilderPulse/BuilderPulse` |
| local repo | `/root/.controlmesh/workspace/vendor/BuilderPulse` |
| task description | `/root/.controlmesh/workspace/cron_tasks/daily-builderpulse-opportunity-radar/TASK_DESCRIPTION.md` |
| parser script | `/root/.controlmesh/workspace/cron_tasks/daily-builderpulse-opportunity-radar/scripts/build_builderpulse_radar.py` |

## Source Contract

| 字段 | 值 |
| --- | --- |
| source_of_truth | `BuilderPulse/BuilderPulse` 每日 markdown archive |
| access_path | `git pull --ff-only` + 本地 parser |
| freshness_policy | 优先 pull 最新仓库；pull 失败时允许使用本地最新 snapshot |
| selection_policy | 提取 headline、2-hour build idea、Top 3 signals、opportunity clusters |
| output_contract | 独立 `F. 机会雷达` 中文报告 + JSON manifest |

## Content Layout

上游仓库内容形态：

- `zh/YYYY/YYYY-MM-DD.md`
- `en/YYYY/YYYY-MM-DD.md`

## Output Contract

Canonical outputs:

- `/root/.controlmesh/workspace/output_to_user/builderpulse_opportunity_radar_latest.md`
- `/root/.controlmesh/workspace/output_to_user/builderpulse_opportunity_radar_sources_latest.json`

报告必须包含：

- 主标题 `F. 机会雷达`
- report date
- selected opportunity count

## Classification

这是独立仓库型信息源，不是 skill。

它不并入 `ai-builders-digest-5briefs` 主 digest，而是保持独立 cron 产出。

## Failure Behavior

- `git pull --ff-only` 失败时说明失败原因。
- pull 失败不直接终止，可继续使用本地最新 snapshot。
- 输出 markdown 和 JSON 都要验证写入。

## Registry

- 注册表入口：[[../信息源注册表]]
- 总览入口：[[../信息源采集总览]]
