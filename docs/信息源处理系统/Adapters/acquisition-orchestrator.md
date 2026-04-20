---
doc_type: reference
entity: acquisition orchestrator
status: active
owner: Muqiao
last_verified: 2026-04-20
---

# acquisition orchestrator

## Identity

| 字段 | 值 |
| --- | --- |
| type | `local orchestration layer` |
| role | `source collector` 与 `knowledge_pack` 之间的采集编排层 |
| implemented code | `/root/.ductor/workspace/information-processing-system/tools/knowledge_pipeline/acquisition/` |
| cli entry | `python3 -m tools.knowledge_pipeline.acquisition --url <URL>` |
| status | `active / skeleton landed` |

## 为什么需要单独一层

如果只是把网页抓取写成一个更长的 fallback chain，它依然只是“更长的单函数”。

我们真正要复刻的是一种 acquisition architecture：

`source contract -> acquisition recipe -> adapter set -> run ledger -> promotion candidate -> knowledge_pack`

这层要解决的是：

1. 哪种内容该走哪条 recipe
2. recipe 里哪些 adapter 默认启用
3. 每次尝试为什么成功或失败
4. 哪些结果有资格提升成标准 candidate
5. 哪些能力必须继续留在 `knowledge_pack` / NotebookLM 下游

## 当前骨架

当前已落地的核心对象：

- `AcquisitionTask`
- `SourceCandidate`
- `Attempt`
- `PromotedItem`
- `RunLedger`
- `AcquisitionRecipe`
- `Registry`
- `Orchestrator`

## 默认 adapter 集

默认顺序是：

1. `jina_reader`
2. `defuddle`
3. `direct_browser_ua`
4. `amp`
5. `archive_today`
6. `agent_fetch`
7. `firecrawl_web_agent` 仅在显式提供 `FIRECRAWL_API_KEY` 时启用

这意味着：

- 默认仍然坚持 no-extra-key
- Firecrawl 不是默认路径
- acquisition 层是“编排 + ledger”，而不是“新加一个抓取器”

## CLI

干跑并打印 ledger：

```bash
cd /root/.ductor/workspace/information-processing-system
python3 -m tools.knowledge_pipeline.acquisition \
  --url https://example.com/article \
  --title "Example Article"
```

把 ledger 写到文件：

```bash
cd /root/.ductor/workspace/information-processing-system
python3 -m tools.knowledge_pipeline.acquisition \
  --url https://example.com/article \
  --output /tmp/acquisition-ledger.json
```

## 和现有系统的边界

- source collector：继续负责稳定源的拉取和筛选
- acquisition orchestrator：负责单链接 / 候选对象的抓取编排
- `knowledge_pack`：负责标准化成统一导入包
- NotebookLM：只消费 `knowledge_pack`，不回头承担网页采集兼容

## 下一步

1. 给不同 item type 补专门 recipe：
   - `x_single_link`
   - `raw_github_text`
   - `arxiv_paper`
   - `js_heavy_page`
2. 让 `agent_fetch` 真正接本机 `server-browser / CDP`
3. 把 run ledger 写入日期化 pipeline 目录
4. 定义 promotion gate，让 acquisition candidate 稳定进入 `knowledge_pack`

## Related Notes

- [[../信息源注册表]]
- [[../信息源契约模板]]
- [[notebooklm-source-pack]]
- [[firecrawl-web-agent-fetch]]

