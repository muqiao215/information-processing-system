# Task Plan: Acquisition Orchestrator for Information Sources

## Goal

Replicate the useful architecture behind `firecrawl/web-agent` inside the local information processing system, without making Firecrawl a required default dependency.

The target is an acquisition orchestration layer, not a simple fallback:

`source contract -> acquisition recipe -> tool adapters -> run ledger -> structured extraction -> knowledge_pack`

## Constraints

- Keep `knowledge_pack` as the canonical downstream boundary.
- Keep no-extra-API-key paths as the default.
- Treat Firecrawl as an optional adapter, not as the framework.
- Preserve the existing public webpage/X cascade idea: `r.jina.ai -> defuddle.md -> bot UA -> AMP -> archive.today -> agent-fetch`.
- Do not add a new active source unless it emits stable source items.
- Keep NotebookLM-specific behavior downstream of `knowledge_pack`.

## Workstreams

| Workstream | Owner | Status | Write Scope |
| --- | --- | --- | --- |
| Planning files | Main session | complete | `task_plan.md`, `findings.md`, `progress.md` |
| Code skeleton and tests | Background task `7c2f6aa8` + main session | complete | `tools/knowledge_pipeline/acquisition/`, `tests/test_acquisition_orchestrator.py` |
| Docs and registry | Background task `4533ca6c` + main session | complete | `docs/信息源处理系统/Adapters/`, `docs/信息源处理系统/信息源注册表.md`, README docs references |
| Integration review | Main session | complete | Review worker outputs, run tests, fix small integration issues |

## Acceptance Criteria

- A local acquisition orchestrator module exists with explicit concepts for tasks, recipes, adapters, attempts, ledgers, and promoted items.
- Default operation can run without `FIRECRAWL_API_KEY`.
- Firecrawl/Web Agent is documented and modeled only as an optional adapter.
- The orchestrator can emit a JSON ledger and candidate item data that can later be promoted into `knowledge_pack`.
- Tests cover recipe selection, default cascade ordering, optional Firecrawl disabling, and ledger shape.
- Docs explain why this is an adapter/orchestration layer rather than an active source.

## Phases

1. Create persistent plan files. Status: complete.
2. Launch parallel background tasks with disjoint write scopes. Status: complete.
3. Review and integrate task outputs. Status: complete.
4. Run tests. Status: complete.
5. Commit locally if changes are coherent. Status: pending.

## Errors Encountered

| Error | Attempt | Resolution |
| --- | --- | --- |
| `tools/task_tools/CLAUDE/GEMINI/AGENTS.md` path missing | Tried to read placeholder path from Ductor prompt | Use actual `tools/task_tools/AGENTS.md` / `create_task.py` scripts |
