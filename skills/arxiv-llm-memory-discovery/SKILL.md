---
name: arxiv-llm-memory-discovery
description: >
  每日 arXiv LLM memory 论文发现流水线。用 arXiv API 的 abs: 字段查询摘要关键词，过滤掉
  Mamba、时间序列、显存/内存优化等噪声，只在命中 LLM 长期记忆、跨对话记忆、context
  window / KV cache 管理、RAG 记忆增强、语义/情景记忆等主题时挑出最佳 1 篇并生成
  Telegram 友好的中文推送。
---

# arXiv LLM Memory Discovery

目标：每天只推送 1 篇真正相关的 LLM memory 论文。宁缺毋滥；遇到 arXiv rate limit 时静默跳过，不硬推。

这个 skill 在 `information-processing-system` 中是 repo-local 真源。shared bundle 和
runtime 目录里的副本都应该由这里派生，而不是反过来把 runtime 目录当上游。

## 核心规则

- 查询必须使用 arXiv API，不依赖浏览器。
- 查询必须优先使用 `abs:` 字段前缀，只搜摘要关键词，避免 `all:memory` 带来的噪声。
- 每次最多输出 1 篇论文。
- 如果没有高置信相关论文，输出“今日无高置信命中”，不要凑数。
- 如果 arXiv 返回 `429` 或网络层 rate limit，退出码保持 `0`，输出 `skipped_rate_limited`，不要把每日任务判失败。

## 真正相关的主题

保留论文必须至少命中一个方向：

- LLM 的长期记忆、跨会话记忆、对话记忆、用户偏好记忆。
- 语义记忆、情景记忆、episodic memory、semantic memory。
- Context window 管理、上下文压缩、KV cache 管理、persistent cache、memory compression。
- RAG 风格的记忆增强，包括 memory-augmented retrieval、retrieval memory、external memory。
- Agent memory，例如 tool-using agent / conversational agent 的可检索记忆。

## 噪声过滤

默认过滤：

- Mamba、state space model、SSM 里的 memory。
- 时间序列、控制系统、强化学习环境里的 memory，除非明确与 LLM agent memory 相关。
- GPU/VRAM/显存优化、memory-efficient training、activation memory，除非主题是 KV cache / context memory。
- 人类认知实验、医学记忆、神经科学记忆，除非明确用于 LLM memory 架构。

## 推荐命令

从这个 repo 根目录运行：

```bash
python3 skills/arxiv-llm-memory-discovery/scripts/discover_llm_memory_paper.py
```

默认输出：

- `/root/.controlmesh/workspace/output_to_user/arxiv_llm_memory_discovery_latest.md`
- `/root/.controlmesh/workspace/output_to_user/arxiv_llm_memory_discovery_latest.json`

只看终端结果：

```bash
python3 skills/arxiv-llm-memory-discovery/scripts/discover_llm_memory_paper.py --stdout-only
```

指定回看天数：

```bash
python3 skills/arxiv-llm-memory-discovery/scripts/discover_llm_memory_paper.py --days 7
```

脚本会维护去重状态，默认写入：

- `/root/.controlmesh/workspace/output_to_user/arxiv_llm_memory_discovery_state.json`

已推送过的 arXiv ID 不会重复推送。

## 输出格式

Telegram 推送保持短而完整：

```text
📄 arXiv LLM Memory Daily
日期：YYYY-MM-DD

Title
Authors
arXiv: ID

为什么值得看：
...

相关性判断：
...

链接：
abs: https://arxiv.org/abs/...
pdf: https://arxiv.org/pdf/...
```

如果无命中：

```text
📄 arXiv LLM Memory Daily
日期：YYYY-MM-DD

今日无高置信 LLM memory 论文命中。
```

## 资源

- `scripts/discover_llm_memory_paper.py`：arXiv 查询、去重、过滤、择优、Markdown/JSON 输出脚本。
