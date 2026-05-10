---
doc_type: reference
entity: github-trending-ai-watch 信息源
status: active
owner: Muqiao
last_verified: 2026-04-19
---

# github-trending-ai-watch

## Identity

| 字段 | 值 |
| --- | --- |
| source_id | `github-trending-ai-watch` |
| cron_id | `daily-github-trending-ai-watch` |
| layer | `collector + selector` |
| schedule | `09:30 Asia/Shanghai` |
| task description | `/root/.controlmesh/workspace/information-processing-system/cron_tasks/daily-github-trending-ai-watch/TASK_DESCRIPTION.md` |
| collector script | `/root/.controlmesh/workspace/information-processing-system/cron_tasks/daily-github-trending-ai-watch/scripts/fetch_github_trending.py` |

## Source Contract

| 字段 | 值 |
| --- | --- |
| source_of_truth | GitHub Trending daily page |
| access_path | 本地抓取脚本 `fetch_github_trending.py` |
| freshness_policy | 每次运行读取当前 daily trending |
| selection_policy | 优先 AI、agent、automation、robotics、developer-tool 项目 |
| output_contract | `GitHub 今日趋势 Top 8` + `按用户方向最值得看的 4 个` |

## Output Contract

Top 8 每项包含：

- `owner/repo`
- 一句话描述
- language
- total stars
- today's stars

精选 4 个每项包含：

- project name
- why it matters for AI / agent / automation / robotics / developer tools

## Failure Behavior

- 直接抓取失败时停止并说明。
- 不从 stale memory 生成榜单。
- 不伪造 GitHub Trending 结果。
- 不调用外部消息工具，由 workspace cron 负责投递。

## Registry

- 注册表入口：[[../信息源注册表]]
- 总览入口：[[../信息源采集总览]]
