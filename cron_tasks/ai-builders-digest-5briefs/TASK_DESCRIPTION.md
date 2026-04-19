# AI Builders Digest 5 Briefs

## Goal

Generate five Chinese AI builders digests and a machine-readable source manifest
for downstream NotebookLM generation, without relying on OpenClaw runtime.

## Assignment

This task does not need browser automation. It should finish the text digests and
write the latest source manifest for the next task.

Allowed write targets:
- `/root/.ductor/workspace/output_to_user`

Execution steps:
1. Read this task's memory file.
2. Run:
   - `python3 scripts/fetch_follow_builders.py > /tmp/follow_builders_bundle.json`
3. Inspect the fetched JSON bundle. If feeds failed to load, report that clearly.
4. Generate five Chinese digests:
   - A = AI前沿与工具
   - B = 创业与战略
   - C = 产品与体验
   - D = 行业与观点
   - E = 技术实践
5. Each digest must select at least 5 substantial items when the feed supports it.
6. For each selected item, keep the original source URL in the machine-readable
   manifest, but do not dump raw links excessively in the human report.
7. Save two files:
   - `/root/.ductor/workspace/output_to_user/ai_builders_digest_latest.md`
   - `/root/.ductor/workspace/output_to_user/ai_builders_digest_sources_latest.json`
8. The JSON manifest must contain the selected items and URLs that the NotebookLM
   task should import later.

Important:
- Do not call any external messaging tool.
- Do not try to create NotebookLM notebooks here.
- This task is the source stage; the NotebookLM task is the artifact stage.

## Output

Return the five Chinese digest sections in the final answer, then append a short
footer stating:
- source manifest saved path
- markdown digest saved path
- total selected source count
