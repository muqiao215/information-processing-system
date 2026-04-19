# Information Processing System

Local information processing system extracted from the Ductor workspace.

This repository is the standalone code home for the pipeline that turns
heterogeneous information sources into a canonical `knowledge_pack`, then
drives NotebookLM report generation and artifact lifecycle steps.

## Scope

- Source-oriented contracts and reference docs:
  `docs/信息源处理系统/`
- Canonical knowledge-pack builder and preprocessing:
  `tools/knowledge_pipeline/`
- Cron task contracts and helper scripts used by the pipeline:
  `cron_tasks/`

## Current Pipeline

1. Source collection
   - `ai-builders-digest-5briefs`
   - `daily-builderpulse-opportunity-radar`
   - `daily-arxiv-llm-memory-discovery`
2. Normalization
   - `daily-knowledge-pack-builder`
   - canonical `knowledge_pack`
   - phase-2 preprocessing for X / raw GitHub / arXiv inputs
3. Knowledge digestion
   - `daily-notebooklm-content-gen`
4. Artifact lifecycle
   - `daily-notebooklm-artifact-trigger`
   - `daily-notebooklm-artifact-harvest`

## Notes

- This repo intentionally excludes runtime outputs from `output_to_user/`.
- Browser/runtime-specific login state is not stored here.
- Runtime execution still expects sibling Ductor workspace resources such as
  `output_to_user/`, `vendor/BuilderPulse/`, and `notebooklm-cdp-cli/`.
- The Obsidian/ops-facing reference set is also synced from this repo shape into
  `ops-vault`.
