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
   - `daily-news-summary-7am`
   - `daily-github-trending-ai-watch`
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

## External Upstreams

This repository is the control plane for the information pipeline, not a mirror
of every upstream content source.

- `daily-news-summary-7am`
  Mixed upstream pages, including GitHub releases for `anthropics/claude-code`
  and `openai/codex`, plus public article pages.
- `daily-github-trending-ai-watch`
  Scrapes the live GitHub Trending daily page.
- `ai-builders-digest-5briefs`
  Depends on the public raw feed published by
  `zarazhangrui/follow-builders`.
- `daily-builderpulse-opportunity-radar`
  Parses the external repository checkout at `vendor/BuilderPulse`, whose
  upstream is `BuilderPulse/BuilderPulse`.
- `daily-arxiv-llm-memory-discovery`
  Queries the arXiv API directly.

## Acquisition Layer Rules

- Active sources remain source collectors with stable outputs. The acquisition
  orchestrator is a local layer, not a new content source.
- Skill cleanup follows source-of-truth rules:
  - repo-local true source: `information-processing-system/skills/`
  - shared-global true source: `muqiao-private-sync-bundle/skills-selected/`
  - runtime-only views: `/root/.controlmesh/workspace/skills`, `/root/.agents/skills`,
    `/root/.codex/skills`
- For this repository, information-processing-dedicated skills may be promoted
  to repo-local even if they were previously distributed through the shared
  bundle, because they are not part of the general coding toolbox.
- Firecrawl and `firecrawl/web-agent` are optional adapter references only, not
  required default dependencies.
- Default public webpage and X handling uses no-extra-key paths first.
- NotebookLM-specific behavior remains downstream of `knowledge_pack`.

## Notes

- This repo intentionally excludes runtime outputs from `output_to_user/`.
- Browser/runtime-specific login state is not stored here.
- Runtime execution still expects sibling workspace resources such as
  `output_to_user/`, `vendor/BuilderPulse/`, `vendor/newsnow/`, and a
  `notebooklm` CLI available on `PATH`.
- The Obsidian/ops-facing reference set is also synced from this repo shape into
  `ops-vault`.
- Current skill ownership and classification are tracked in
  `skills/skills.registry.json`.
