# Information Processing System

Local information processing system extracted from the current workspace.

This repository is the standalone code home for the pipeline that turns
heterogeneous information sources into a canonical `knowledge_pack`, then
drives NotebookLM report generation and artifact lifecycle steps.

The upstream acquisition path is now documented as an explicit local layer:

`source contract -> acquisition recipe -> tool adapters -> run ledger -> structured extraction -> knowledge_pack`

## Scope

- Source-oriented contracts and reference docs:
  `docs/信息源处理系统/`
- Project-owned skill sources and the skill registry:
  `skills/`
- Canonical knowledge-pack builder and preprocessing:
  `tools/knowledge_pipeline/`
- Cron task contracts and helper scripts used by the pipeline:
  `cron_tasks/`

## Current Pipeline

1. Source collection
   - `ai-builders-digest-5briefs`
   - `daily-builderpulse-opportunity-radar`
   - `daily-arxiv-llm-memory-discovery`
2. Acquisition orchestration
   - selects an acquisition recipe per source item or content type
   - runs local-first tool adapters
   - records attempts and outcomes in a run ledger
   - promotes stable structured results into `knowledge_pack`
3. Normalization
   - `daily-knowledge-pack-builder`
   - canonical `knowledge_pack`
   - phase-2 preprocessing for X / raw GitHub / arXiv inputs
4. Knowledge digestion
   - `daily-notebooklm-content-gen`
5. Artifact lifecycle
   - `daily-notebooklm-artifact-trigger`
   - `daily-notebooklm-artifact-harvest`

## Acquisition Layer Rules

- Active sources remain source collectors with stable outputs. The acquisition
  orchestrator is a local layer, not a new content source.
- Skill cleanup follows source-of-truth rules:
  - repo-local true source: `information-processing-system/skills/`
  - shared-global true source: `muqiao-private-sync-bundle/skills-selected/`
  - runtime-only views: `/root/.controlmesh/workspace/skills`, `/root/.agents/skills`,
    `/root/.codex/skills`
- Firecrawl and `firecrawl/web-agent` are optional adapter references only, not
  required default dependencies.
- Default public webpage and X handling uses no-extra-key paths first.
- NotebookLM-specific behavior remains downstream of `knowledge_pack`.

## Notes

- This repo intentionally excludes runtime outputs from `output_to_user/`.
- Browser/runtime-specific login state is not stored here.
- Runtime execution still expects sibling workspace resources such as
  `output_to_user/`, `vendor/BuilderPulse/`, and a `notebooklm` CLI available on `PATH`.
- The Obsidian/ops-facing reference set is also synced from this repo shape into
  `ops-vault`.
- Current skill ownership and classification are tracked in
  `skills/skills.registry.json`.
