---
doc_type: reference
entity: notebooklm-source-pack 适配层
status: active
owner: Muqiao
last_verified: 2026-04-19
---

# notebooklm-source-pack

## Identity

| 字段 | 值 |
| --- | --- |
| adapter_id | `notebooklm-source-pack` |
| type | `adapter` |
| role | source collector 与 digestion consumer 之间的统一 `knowledge_pack` 适配层 |
| cron | `daily-knowledge-pack-builder` |
| schedule | `10:15 Asia/Shanghai` |
| planned output root | `/root/.ductor/workspace/output_to_user/information_pipeline/bundles/` |
| implemented script | `/root/.ductor/workspace/tools/knowledge_pipeline/normalization/build_knowledge_pack.py` |
| preprocessing helper | `/root/.ductor/workspace/tools/knowledge_pipeline/normalization/preprocess_sources.py` |
| schema | `/root/.ductor/workspace/tools/knowledge_pipeline/schemas/knowledge_pack.schema.json` |

## 为什么需要它

当前上游 manifest 结构不统一：

- `follow-builders` 输出 A-E digest source manifest
- `builderpulse-opportunity-radar` 输出 F. 机会雷达 source manifest
- `arxiv-llm-memory-discovery` 输出单篇 discovery JSON

NotebookLM 下游不应该继续直接绑死某一个 manifest。

需要一个中间 adapter：

- 统一多个上游 source output
- 去重
- 标准化字段
- 生成 canonical `knowledge_pack`
- 对不能稳定 URL ingest 的内容先本地化成 markdown/text，再保留 pack 级 fallback markdown

## 输入

- `/root/.ductor/workspace/output_to_user/ai_builders_digest_sources_latest.json`
- `/root/.ductor/workspace/output_to_user/builderpulse_opportunity_radar_sources_latest.json`
- `/root/.ductor/workspace/output_to_user/arxiv_llm_memory_discovery_latest.json`

## 输出

Canonical outputs:

- `/root/.ductor/workspace/output_to_user/knowledge_pack_latest.json`
- `/root/.ductor/workspace/output_to_user/knowledge_pack_latest.md`
- `/root/.ductor/workspace/output_to_user/knowledge_pack_YYYYMMDD.json`
- `/root/.ductor/workspace/output_to_user/knowledge_pack_YYYYMMDD.md`
- `/root/.ductor/workspace/output_to_user/information_pipeline/bundles/YYYY-MM-DD/knowledge_pack.json`
- `/root/.ductor/workspace/output_to_user/information_pipeline/bundles/YYYY-MM-DD/knowledge_pack.md`
- `/root/.ductor/workspace/output_to_user/information_pipeline/preprocessed/YYYY-MM-DD/*.md`

## 标准 item schema

```json
{
  "item_id": "source_id:stable_hash",
  "source_id": "follow-builders",
  "source_type": "tweet",
  "source_of_truth": "original URL or feed",
  "access_path": "fetch script / reader / repo archive",
  "title": "...",
  "url": "...",
  "summary": "...",
  "raw_text": "...",
  "selected_reason": "...",
  "tags": [],
  "freshness": {
    "published_at": "...",
    "generated_at": "..."
  },
  "content_type": "url | markdown | pdf | x_post | repo_archive",
  "local_text_path": "/root/.ductor/workspace/output_to_user/information_pipeline/preprocessed/YYYY-MM-DD/item.md",
  "import_targets": [
    {
      "kind": "markdown_file",
      "value": "/root/.ductor/workspace/output_to_user/information_pipeline/preprocessed/YYYY-MM-DD/item.md"
    },
    {
      "kind": "url",
      "value": "https://..."
    }
  ],
  "import_policy": {
    "preferred": "local_markdown",
    "fallback": "url_then_pack_markdown"
  },
  "preprocess": {
    "status": "localized | fallback_localized | skipped | failed",
    "method": "jina_reader | defuddle | direct_raw | manifest_fallback_markdown",
    "local_text_path": "...",
    "attempted_methods": []
  },
  "fallback_content": "...",
  "metadata": {}
}
```

## Failure Behavior

- 某个上游 manifest 缺失：明确写入 notes，但继续消费其他 manifest。
- 某个 item 无法稳定 URL ingest：优先尝试 `r.jina.ai -> defuddle -> browser-like UA`，成功则写本地 markdown。
- 远端抓取失败但 manifest 里已有足够文本：退回 `summary` / `raw_text` / `fallback_content` 生成 item 级本地 markdown。
- item 级本地化也失败：继续保留原 URL，并由 pack 级 fallback markdown 兜底。
- 所有上游都缺失：停止并报告 blocker。

## Related

- [[../信息获取与知识消化分层]]
- [[../信息流水线重构清单]]
- [[../Consumers/notebooklm-report]]
