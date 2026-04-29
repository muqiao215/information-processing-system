---
doc_type: reference
entity: qiaomu-anything-to-notebooklm 适配器
status: candidate
owner: Muqiao
last_verified: 2026-04-19
---

# qiaomu-anything-to-notebooklm

## Identity

| 字段 | 值 |
| --- | --- |
| repo | `joeseesun/qiaomu-anything-to-notebooklm` |
| url | `https://github.com/joeseesun/qiaomu-anything-to-notebooklm` |
| type | `adapter repo` |
| role | `preprocessor + knowledge digestion adapter` |
| status | `candidate / borrow-by-parts` |

## 当前定位

这个仓库不是新的“日更信息源”。

它更适合被定位成：

- 多源内容预处理适配器
- NotebookLM 入库前的内容标准化器
- 知识消化链的参考实现

也就是说，它属于 `source collector` 和 `artifact generator` 之间的适配层，
而不是 `Active Sources` 里的 feed / repo archive / academic API。

## 值得借鉴的部分

### 1. 网页获取 cascade

这是当前最值得复用的能力。

建议默认顺序：

1. `r.jina.ai`
2. `defuddle.md`
3. `bot UA` / `X-Forwarded-For` / `Referer` 伪装
4. `AMP`
5. `archive.today`
6. `agent-fetch`

这条链路应作为公开网页与 X/Twitter 单链接深挖的默认能力。

### 2. X/Twitter 单链接拉取

它把 X/Twitter 当作单独 source type 处理，这个方向是对的。

当前建议：

- builder 级 feed 仍由 `follow-builders` 主链负责
- 单条 X/Twitter 深挖时，默认走网页获取 cascade，而不是只依赖 central feed

### 3. 内容转 NotebookLM 的输入路由

它把 URL / PDF / EPUB / Office / 图片 / 音频 / ZIP 统一分流，这个思路适合保留。

但在本环境里，优先复用：

- 可视浏览器
- server-browser / CDP
- 现有 NotebookLM 自动化主线

不建议照搬其 CLI 驱动交互方式。

## 明确不采纳的部分

### 1. 需要额外 API key 的预处理

以下路径默认不作为主线：

- Get笔记 API 转写
- 任何需要额外付费或额外 token 管理的预处理器

原因：

- 增加运维复杂度
- 破坏“默认可用”能力
- 不利于长期收口

### 2. 作为独立 active source

它不应该进入 `Active Sources`。

原因：

- 它不是固定内容源
- 它不提供稳定 daily manifest
- 它更像“内容进入 NotebookLM 之前的变换层”

## 已吸收进本地 knowledge_pack 的部分

2026-04-19 phase-2 preprocessing 已把这里的核心思路落到
`/root/.controlmesh/workspace/tools/knowledge_pipeline/normalization/preprocess_sources.py`。

当前本地实现采用：

1. `r.jina.ai/<original-url>`
2. `defuddle.md/<original-url>`
3. browser-like UA / `Referer` / `X-Forwarded-For` 直取
4. 无法稳定预取时，退回上游 manifest 的 `summary` / `raw_text` / `fallback_content`

落地约定：

- 本地缓存目录：`/root/.controlmesh/workspace/output_to_user/information_pipeline/preprocessed/YYYY-MM-DD/`
- `knowledge_pack` item 记录 `preprocess.status`、`preprocess.method`、`preprocess.local_text_path`
- 成功本地化的 item 会把 `{"kind": "markdown_file", "value": local_path}` 放到 `import_targets` 第一位
- 原始 URL 保留在 `source_of_truth`、`url` 和后续 `import_targets`，作为追溯与兜底，不再作为 NotebookLM 首选入口

已覆盖的高风险类型：

- `x.com` / `twitter.com` 单链接
- `raw.githubusercontent.com` 文本
- `arXiv` PDF / abs 页面

## 当前结论

对本机“信息获取 / 知识消化”体系有帮助，但帮助主要在：

- 默认网页 / X 获取能力
- NotebookLM 入库前预处理
- 公开网页与付费墙页面的多层 fallback

不帮助的点在于：

- 不能替代 `follow-builders`
- 不能替代 `BuilderPulse`
- 不能替代 `arXiv` 类 source

## 建议吸收顺序

1. 先吸收网页 / X 获取 cascade
2. 再吸收 URL / 文件输入分流逻辑
3. 最后再决定是否做成独立本地 skill 或共享脚本

## Related Notes

- [[../信息源注册表]]
- [[../信息源采集总览]]
- [[../Consumers/notebooklm-report]]
