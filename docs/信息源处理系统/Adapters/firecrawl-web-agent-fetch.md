---
doc_type: reference
entity: firecrawl web-agent fetch
status: candidate
owner: Muqiao
last_verified: 2026-04-20
---

# firecrawl web-agent fetch

## Identity

| 字段 | 值 |
| --- | --- |
| repo | `firecrawl/web-agent` |
| url | `https://github.com/firecrawl/web-agent` |
| type | `optional acquisition adapter reference` |
| role | 复杂网页 / JS-heavy 页面 / structured research 的可选 adapter 或参考实现 |
| license | `MIT` |

## 正确定位

它不是 active source。

它也不应该直接当默认主链。

在这套系统里，它更适合被定义成：

- acquisition orchestrator 的 optional adapter
- `agent_fetch` 能力的参考实现
- map / crawl / interact / extract 这套统一抽象的借鉴对象

## 为什么不能当默认主线

原因很简单：

1. 默认要求 `FIRECRAWL_API_KEY`
2. 还需要模型 provider key
3. 偏 research-agent loop，不如固定 recipe 可控
4. daily pipeline 更需要可审计、可降级、可复跑

所以它不能替代：

- `follow-builders`
- `BuilderPulse`
- `arxiv-llm-memory-discovery`
- canonical `knowledge_pack`

## 值得吸收的部分

最值得复刻的是这些结构，而不是某个具体 SDK：

1. `search / scrape / interact / map / crawl / extract` 的统一工具抽象
2. recipe 驱动的多步 acquisition
3. 每次 attempt 都有结构化记录
4. structured output，而不是只有 markdown
5. 复杂页面可以交给更强交互能力处理

## 在本机体系中的落点

| Web-agent 思路 | 本机对应层 |
| --- | --- |
| search / map / crawl | acquisition recipe discovery |
| scrape | `jina_reader` / `defuddle` / direct fetch |
| interact | `server-browser` / Chrome CDP / browser handoff |
| structured output | run ledger + promotion candidate + `knowledge_pack` |
| subagents | background tasks / future worker pool |

## 启用策略

默认不开。

只有在这些条件都满足时才值得启用：

- 前面的 no-extra-key adapter 都失败
- 页面确实需要更强交互或结构化提取
- 已显式提供 `FIRECRAWL_API_KEY`
- 成本和不确定性可接受

## 当前结论

如果没有 acquisition orchestrator，接它意义不大。

如果 acquisition orchestrator 已经存在，它才有明确落点：

- 不是“一个更贵的 fallback”
- 而是编排层中的一个 optional adapter

## Related Notes

- [[acquisition-orchestrator]]
- [[qiaomu-anything-to-notebooklm]]
- [[../信息源注册表]]

