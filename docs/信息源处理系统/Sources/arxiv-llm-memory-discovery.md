---
doc_type: reference
entity: arxiv-llm-memory-discovery 信息源
status: active
owner: Muqiao
last_verified: 2026-04-19
---

# arxiv-llm-memory-discovery

## Identity

| 字段 | 值 |
| --- | --- |
| source_id | `arxiv-llm-memory-discovery` |
| cron_id | `daily-arxiv-llm-memory-discovery` |
| layer | `collector + selector` |
| schedule | `09:00 Asia/Shanghai` |
| skill | `/root/.ductor/workspace/skills/arxiv-llm-memory-discovery` |
| Hermes live copy | `/root/.ductor/workspace/vendor/hermes-agent/.hermes-home/skills/research/arxiv-llm-memory-discovery` |
| private sync | `/root/private-sync-bundle/skills-selected/arxiv-llm-memory-discovery` |
| task description | `/root/.ductor/workspace/cron_tasks/daily-arxiv-llm-memory-discovery/TASK_DESCRIPTION.md` |
| discovery script | `/root/.ductor/workspace/skills/arxiv-llm-memory-discovery/scripts/discover_llm_memory_paper.py` |

## Source Contract

| 字段 | 值 |
| --- | --- |
| source_of_truth | arXiv API |
| access_path | skill script `discover_llm_memory_paper.py` |
| freshness_policy | 每日 live 查询 arXiv API |
| query_policy | 使用 `abs:` scoped queries only |
| selection_policy | 只选 LLM memory / long-term memory / context / KV cache / RAG memory / semantic or episodic memory 方向 |
| output_contract | 每天最多 1 篇 Telegram-friendly 论文推送 |

## Explicit Noise Filters

必须排除：

- Mamba / state-space
- time-series memory
- memory-efficient training
- GPU memory optimization
- 与 LLM 跨对话记忆、context 管理、RAG 记忆增强无关的泛化 memory 论文

## Output Contract

Canonical outputs:

- `/root/.ductor/workspace/output_to_user/arxiv_llm_memory_discovery_latest.md`
- `/root/.ductor/workspace/output_to_user/arxiv_llm_memory_discovery_latest.json`
- `/root/.ductor/workspace/output_to_user/arxiv_llm_memory_discovery_state.json`

## Failure Behavior

- 没有高置信论文时输出“今日无高置信命中”类消息。
- arXiv rate limit 时 graceful skip，不把任务判成硬失败。
- 不允许一天推多篇；宁缺毋滥。

## Registry

- 注册表入口：[[../信息源注册表]]
- 总览入口：[[../信息源采集总览]]
