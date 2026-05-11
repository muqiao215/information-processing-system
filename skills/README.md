# Skills

This directory is the project-local skill source-of-truth layer for
`information-processing-system`.

## Source Of Truth Rules

Do not classify a skill by whichever runtime directory happens to contain it.
Classify it by the real upstream owner.

1. Repo-local true source: `information-processing-system/skills/`
2. Shared-global true source: `muqiao-private-sync-bundle/skills-selected/`
3. Runtime views only:
   - `/root/.controlmesh/workspace/skills`
   - `/root/.agents/skills`
   - `/root/.codex/skills`

Runtime/view directories are deployment surfaces, not ownership surfaces.
They must not be treated as canonical edit locations.

## What Belongs Here

Put a skill in this repo only when it is strongly coupled to the information
processing system itself, for example:

- it depends on this repo's cron contracts
- it depends on this repo's `knowledge_pack` schema or normalization logic
- it is maintained as part of this repo's pipeline behavior

Current repo-local owned skills:

- `arxiv-llm-memory-discovery`
- `follow-builders`
- `information-sources`
- `auto-paper-digest`
- `ak-rss-digest`

## What Does Not Belong Here

Do not duplicate a shared skill here just because the project consumes it.
Instead:

1. keep the shared skill in `muqiao-private-sync-bundle/skills-selected/`
2. register the dependency in `skills.registry.json`
3. reference it from docs or cron contracts

Examples of shared-global skills currently used by this pipeline:

- `notebooklm`
- `firecrawl`

## Governance Files

- `skills.registry.json`
  Canonical classification table for information-processing-related skills.
- `../tools/skill_governance/report_information_skill_inventory.py`
  Runtime scanner that reports current locations and source ownership status.
