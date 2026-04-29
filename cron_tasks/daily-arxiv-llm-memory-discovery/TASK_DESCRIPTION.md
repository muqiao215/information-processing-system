# Daily arXiv LLM Memory Discovery

## Goal

Find one high-signal arXiv paper about LLM memory and push a concise Telegram-friendly summary.

## Assignment

This task should run the local `arxiv-llm-memory-discovery` skill and produce one
daily Telegram-friendly push message.

Allowed write targets:
- `/root/.controlmesh/workspace/output_to_user`

Execution steps:
1. Read this task's memory file.
2. Run the skill script:
   - `python3 /root/.controlmesh/workspace/skills/arxiv-llm-memory-discovery/scripts/discover_llm_memory_paper.py`
3. The script is responsible for:
   - querying arXiv with `abs:`-scoped queries only
   - filtering out Mamba / state-space / time-series / memory-efficient-training noise
   - keeping only papers about LLM memory, long-term memory, context window or KV cache management, RAG-style memory augmentation, or semantic / episodic memory for language agents
   - selecting at most one paper
   - degrading gracefully on arXiv rate limits by printing a skip message instead of failing
4. Verify the output files exist:
   - `/root/.controlmesh/workspace/output_to_user/arxiv_llm_memory_discovery_latest.md`
   - `/root/.controlmesh/workspace/output_to_user/arxiv_llm_memory_discovery_latest.json`
   - `/root/.controlmesh/workspace/output_to_user/arxiv_llm_memory_discovery_state.json`
5. Parse the JSON file to confirm it is valid JSON.

Important:
- Do not push more than one paper.
- If no paper meets the score threshold, return the generated “今日无高置信命中” message as-is.
- If arXiv rate limits the request, treat the run as a graceful skip, not an error.

## Output

Return the exact daily push message in the final answer, then append a short footer stating:
- markdown saved path
- json saved path
- status
