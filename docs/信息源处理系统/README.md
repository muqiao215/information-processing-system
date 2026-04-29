---
doc_type: reference
entity: 信息源采集目录
status: active
owner: Muqiao
last_verified: 2026-04-20
---

# 信息源采集

## 目录定位

这个目录记录 workspace / Hermes / 本地脚本体系里所有“信息源采集”相关资产。

这里不记录模型额度、服务健康检查、账号池同步这类运维遥测，除非它们本身成为内容源。

## 当前标准文件

- [[信息源注册表]]：当前所有采集源、访问路径、输出契约和失败行为的台账。
- [[信息源采集总览]]：对现有任务的解释性归类，说明哪些是 skill、哪些是仓库、哪些是下游生成链。
- [[信息源契约模板]]：新增信息源或改造旧任务时应填写的标准字段。
- [[信息获取与知识消化分层]]：APD 风格重构后的两层架构口径，区分信息获取层和知识消化层。
- [[信息流水线重构清单]]：后续改 cron / 脚本时按此清单落地。
- [[Adapters/acquisition-orchestrator]]：source collector 与 `knowledge_pack` 之间的采集编排层定义。
- [[Adapters/firecrawl-web-agent-fetch]]：可选 Firecrawl / web-agent 参考适配器，不是 active source。

## 单源卡片

### Sources

- [[Sources/daily-news-summary]]
- [[Sources/github-trending-ai-watch]]
- [[Sources/follow-builders]]
- [[Sources/builderpulse-opportunity-radar]]
- [[Sources/arxiv-llm-memory-discovery]]

### Consumers

- [[Consumers/notebooklm-report]]
- [[Consumers/notebooklm-artifact-trigger]]

### Adapters

- [[Adapters/qiaomu-anything-to-notebooklm]]
- [[Adapters/notebooklm-source-pack]]
- [[Adapters/acquisition-orchestrator]]
- [[Adapters/firecrawl-web-agent-fetch]]

### Pipelines

- [[Pipelines/auto-paper-digest-engine]]

## 分层口径

后续采用两大层：

- 信息获取层：负责 source collection / acquisition orchestration / selection / bundle。
- 知识消化层：负责 NotebookLM ingest / report / artifact / publishing。

细分层级如下：

| 层级 | 所属大层 | 含义 | 例子 |
| --- | --- | --- | --- |
| source collector | 信息获取层 | 直接接触上游信息源，拉取原始条目或正文 | `follow-builders`, `BuilderPulse`, arXiv API |
| acquisition orchestrator | 信息获取层 | 按 source type / item type 选择 recipe，驱动 adapter，写 run ledger，并决定哪些结果可以提升为标准 item | public web / X 单链接获取编排层 |
| acquisition adapter | 信息获取层 | 被 orchestrator 调用的具体工具接口或抓取实现 | `r.jina.ai`, `defuddle`, browser-like fetch, browser/CDP, optional Firecrawl |
| selector / ranker | 信息获取层 | 从原始条目里过滤、打分、选题 | `arxiv-llm-memory-discovery`, GitHub Trending Top 8 |
| import bundle | 信息获取层到知识消化层的边界 | 把多源结果和 acquisition 成功产物标准化成 NotebookLM 可消费的 canonical `knowledge_pack` | `daily-knowledge-pack-builder` |
| artifact generator | 知识消化层 | 基于已选内容生成 NotebookLM 报告、视频、幻灯片等产物 | NotebookLM cron |
| publishing layer | 知识消化层 | 把 report / video / slides 发布到 portal、HF、平台 | APD `publisher.py` / `portal` 参考 |
| ops telemetry | 不属于内容层 | 配额、健康检查、账号池等状态监控 | quota / health check cron |

## Acquisition 编排口径

公开网页与 X/Twitter 单链接不再只被描述成固定 fallback chain。

现在的标准口径是：

- source collector 只负责交出原始 URL、条目文本或候选对象。
- acquisition orchestrator 根据 source type 选择 recipe。
- recipe 定义适配器顺序、停止条件、是否允许付费 / 额外 key 路径。
- adapter 执行具体抓取动作，并把每次尝试写入 ledger。
- 只有成功获取到可追溯结构化内容的结果，才会被提升进 `knowledge_pack`。

默认 recipe 仍然坚持 no-extra-key 路径优先：

1. `r.jina.ai`
2. `defuddle.md`
3. browser-like UA / 直取
4. AMP
5. `archive.today`
6. browser / agent fetch
7. optional Firecrawl adapter when explicitly enabled

这表示 Firecrawl 不是默认主线，而是编排层中的一个可选 adapter。

## 核心规则

1. `source_of_truth` 和 `access_path` 必须分开写。
2. GitHub 仓库、GitHub release、RSS feed、arXiv API、Jina Reader 都不是同一层概念。
3. 新信息源必须有稳定输出，至少是 Markdown 或 JSON manifest。
4. 下游生成链不能冒充原始信息源。
5. 每个采集源都要写清楚失败行为：停止、降级、跳过，还是使用本地缓存。
6. 公开网页与 X/Twitter 单链接默认具备 acquisition recipe，不再只写成硬编码 fallback；ledger 必须能说明尝试过哪些 adapter。
7. NotebookLM 任务只消费标准 import bundle，不再直接承担多源兼容和选题逻辑。
8. `output_to_user/*latest*` 只作为兼容入口；长期资产应进入日期化 pipeline 目录与 ledger。
9. Firecrawl / web-agent 只能作为可选 adapter 或参考实现，不能在文档上冒充 active source。
