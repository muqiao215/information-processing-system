---
doc_type: reference
entity: auto-paper-digest pipeline engine
status: candidate
owner: Muqiao
last_verified: 2026-04-19
---

# auto-paper-digest-engine

## Identity

| 字段 | 值 |
| --- | --- |
| repo | `muqiao215/auto-paper-digest` |
| visibility | private |
| type | independent repo / pipeline engine |
| role | APD 风格的论文到 NotebookLM / artifact / publishing 流水线参考实现 |
| local status | 当前未克隆到 `/root/.ductor/workspace/vendor/auto-paper-digest` |
| skill wrapper | `/root/.ductor/workspace/skills/auto-paper-digest` |

## 定位

`auto-paper-digest` 不是普通 skill，也不是当前信息源之一。

它应被定位为：

- pipeline engine 参考实现
- source object 状态机参考
- NotebookLM artifact orchestration 参考
- publishing layer 参考

当前本地不应把它整仓并入 `skills-selected`，而应把它的实现结构借鉴到本机信息流水线。

## 可借鉴模块

| APD 模块 | 可借鉴点 | 本地对应方向 |
| --- | --- | --- |
| `apd/db.py` | SQLite 状态机、阶段状态、错误记录 | 后续 `information_pipeline` ledger |
| `apd/config.py` | 统一 data 目录、PDF/video/slides/digest 分区 | `output_to_user/information_pipeline/*` |
| `apd/hf_fetcher.py` | source-specific fetcher 与对象 upsert | source collector 脚本标准化 |
| `apd/pdf_downloader.py` | 下载、校验、缓存、幂等 | arXiv / PDF 类 source 标准化 |
| `apd/nblm_bot.py` | NotebookLM artifact 阶段意识 | 只借鉴阶段拆分，不复制 browser bot |
| `apd/publisher.py` | HuggingFace publishing 层 | 后续 portal / dataset 发布层 |
| `portal/` | artifact 展示面 | 后续 digest archive portal |

## 当前不采纳

- 不复制 APD 的 Playwright NotebookLM 自动化。
- 不复用 APD 的本地 profile 作为身份源。
- 不把 HF papers 当成主信息源。
- 不默认接 Douyin publishing。
- 不把 portal 先接到主链。

## 推荐落地路径

### Phase 1: 信息获取层标准化

将现有 source cron 输出收敛为统一 `source item`：

- `source_id`
- `source_of_truth`
- `access_path`
- `source_url`
- `title`
- `published_at`
- `raw_text_path`
- `selected`
- `score`
- `failure_behavior`

### Phase 2: NotebookLM import bundle

新增中间层，统一消费多个 source output，产出：

- `knowledge_pack_YYYYMMDD.json`
- `knowledge_pack_latest.json`
- `knowledge_pack_YYYYMMDD.md`

### Phase 3: artifact ledger

把 `notebooklm_report_run_latest.json` 与 `notebooklm_artifact_trigger_latest.json` 扩展成统一 ledger：

- report artifact
- slide artifact
- video artifact
- source import summary
- fallback source path
- async pending status

### Phase 4: publishing layer

借鉴 APD 的 `publisher.py` 与 `portal/`，但作为独立任务读取 ledger，不反向污染信息获取层。

## Related

- [[../信息获取与知识消化分层]]
- [[../Consumers/notebooklm-report]]
- [[../Consumers/notebooklm-artifact-trigger]]
- [[../Adapters/qiaomu-anything-to-notebooklm]]
