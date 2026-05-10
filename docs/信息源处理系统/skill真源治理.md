---
doc_type: reference
entity: 信息处理 skill 真源治理
status: active
owner: Muqiao
last_verified: 2026-05-11
---

# Skill 真源治理

这份规则只覆盖 `information-processing-system` 这条线。

目标不是“清目录”，而是建立一套稳定的 source-of-truth 判断方法：

`真源识别 -> 归属判定 -> 迁移/保留 -> runtime 清理 -> commit/push -> grep 验证`

## 三层模型

1. repo-local 真源
   - 路径：`information-processing-system/skills/`
   - 只放项目强依赖 skill
2. shared-global 真源
   - 路径：`muqiao-private-sync-bundle/skills-selected/`
   - 放跨项目复用的通用 skill
3. runtime/view 层
   - 路径：
     - `/root/.controlmesh/workspace/skills`
     - `/root/.agents/skills`
     - `/root/.codex/skills`
   - 这些都只是运行态视图，不是上游

## 核心规则

1. skill 清理不以当前目录存在为准，而以事实来源为准。
2. runtime/view 目录不能直接作为上游修改、提交或推送。
3. 项目强依赖 skill 必须进入 repo-local 真源，不应继续只挂在 shared bundle。
4. 跨项目通用 skill 必须保留在 shared-global 真源，不在项目 repo 中重复造第二个真源。
5. 项目 repo 可以登记 shared skill 依赖，但不应把“依赖”误写成“所有权”。
6. 每次迁移都必须同时处理：
   - 新真源落位
   - 旧真源删除或降级为依赖登记
   - runtime 残留清理
   - git commit/push
   - grep 或 inventory 验证

## 当前信息处理范围的第一批分类

- `repo-local`
  - `arxiv-llm-memory-discovery`
- `shared-global`
  - `follow-builders`
  - `information-sources`
  - `auto-paper-digest`
  - `notebooklm`
  - `firecrawl`

完整机器可读注册表见：

- `skills/skills.registry.json`

运行态审计命令：

```bash
python3 tools/skill_governance/report_information_skill_inventory.py
```

## 决策树

看到一个 skill，按下面顺序判断：

1. 它是否依赖本 repo 的 cron、schema、脚本、知识包格式？
   - 是：`repo-local`
   - 否：继续
2. 它是否是跨项目通用能力？
   - 是：`shared-global`
   - 否：继续
3. 它是否只存在于 runtime/view 层？
   - 是：`runtime-orphan`
   - 否：`manual-review`
