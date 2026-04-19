# Daily BuilderPulse Opportunity Radar

## Goal

Generate a standalone BuilderPulse opportunity radar brief from the local BuilderPulse daily archive.

## Assignment

This task should produce one standalone Chinese opportunity-radar brief from
`BuilderPulse/BuilderPulse` without changing the existing `ai-builders-digest-5briefs`
task.

Allowed write targets:
- `/root/.ductor/workspace/output_to_user`
- `/root/.ductor/workspace/vendor/BuilderPulse` via `git pull --ff-only` only

Execution steps:
1. Read this task's memory file.
2. Refresh the local BuilderPulse source:
   - `git -C /root/.ductor/workspace/vendor/BuilderPulse pull --ff-only`
3. If the pull fails, report the failure clearly, but continue using the latest
   local snapshot instead of failing the whole run.
4. Run:
   - `python3 scripts/build_builderpulse_radar.py`
5. The script must:
   - parse the latest available Chinese BuilderPulse daily markdown
   - extract headline, today's 2-hour build idea, Top 3 signals, and the four
     opportunity clusters
   - write a human-readable markdown report
   - write a machine-readable JSON manifest for downstream reuse
6. Save two files:
   - `/root/.ductor/workspace/output_to_user/builderpulse_opportunity_radar_latest.md`
   - `/root/.ductor/workspace/output_to_user/builderpulse_opportunity_radar_sources_latest.json`
7. Verify both files were written and the JSON manifest parses cleanly.

Important:
- Do not modify the existing `ai-builders-digest-5briefs` task.
- Do not call external messaging tools.
- This is a standalone BuilderPulse radar task, not a replacement for the main
  follow-builders digest.

## Output

Return the full Chinese radar brief in the final answer. The markdown must
contain a main section titled `F. 机会雷达`.

Then append a short footer stating:
- markdown saved path
- source manifest saved path
- report date
- selected opportunity count
