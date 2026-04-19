---
doc_type: reference
entity: daily-news-summary 信息源
status: active
owner: Muqiao
last_verified: 2026-04-19
---

# daily-news-summary

## Identity

| 字段 | 值 |
| --- | --- |
| source_id | `daily-news-summary` |
| cron_id | `daily-news-summary-7am` |
| layer | `collector + synthesizer` |
| schedule | `07:20 Asia/Shanghai` |
| task description | `/root/.ductor/workspace/cron_tasks/daily-news-summary-7am/TASK_DESCRIPTION.md` |

## Source Contract

| 字段 | 值 |
| --- | --- |
| source_of_truth | Claude Code / Codex CLI GitHub releases、橘鸦 AI 早报正文、国际 AI / developer-tool 正文、阮一峰周刊 |
| access_path | GitHub release 页面、网页正文读取、必要时 generic page reader |
| freshness_policy | 每次运行读取当前最新正文或 release body |
| selection_policy | CLI 更新必读 release body；橘鸦取最新全文前三条；国际资讯选 2-3 条；阮一峰检查窗口内新一期 |
| output_contract | 五段式中文晨报 |

## Output Contract

固定五段：

1. `CLI更新`
2. `橘鸦前三条`
3. `国际资讯`
4. `阮一峰`
5. `一句话判断`

## Failure Behavior

- 不允许只看标题或 RSS snippet 硬编正文。
- 正文不可得时明确写 `正文不可得`。
- 内容太薄时明确写 `细节不足`。
- 不调用外部消息工具，由 Ductor cron 负责投递。

## Registry

- 注册表入口：[[../信息源注册表]]
- 总览入口：[[../信息源采集总览]]
