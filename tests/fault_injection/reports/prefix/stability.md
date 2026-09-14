# Three-round Determinism Report

Generated: 2026-09-15 05:53:14

Three fully identical rounds (same fixed batch, same epoch, fresh run dirs).

Cross-round invariant violations: **6**
- same_content_diff_url: expected 1 pack item(s) titled 'Vector DB Cost Playbook', found 2
- failed fetch was promoted into pack: Declared Longer Than Sent Article
- same_content_diff_url: expected 1 pack item(s) titled 'Vector DB Cost Playbook', found 2
- failed fetch was promoted into pack: Declared Longer Than Sent Article
- same_content_diff_url: expected 1 pack item(s) titled 'Vector DB Cost Playbook', found 2
- failed fetch was promoted into pack: Declared Longer Than Sent Article

## Raw diffs between rounds (all of them)

### round_1_vs_round_2 - 35 differing JSON paths
- `$.fallback_markdown_path`
- `$.generated_at`
- `$.input_manifests.acquisition-orchestrator.path`
- `$.input_manifests.arxiv-llm-memory-discovery.path`
- `$.input_manifests.builderpulse-opportunity-radar.path`
- `$.input_manifests.follow-builders.path`
- `$.items[0].freshness.generated_at`
- `$.items[0].preprocess.generated_at`
- `$.items[10].freshness.generated_at`
- `$.items[10].preprocess.generated_at`
- `$.items[11].freshness.generated_at`
- `$.items[11].preprocess.generated_at`
- `$.items[12].freshness.generated_at`
- `$.items[12].preprocess.generated_at`
- `$.items[13].freshness.generated_at`
- `$.items[13].preprocess.generated_at`
- `$.items[1].freshness.generated_at`
- `$.items[1].preprocess.generated_at`
- `$.items[2].freshness.generated_at`
- `$.items[2].preprocess.generated_at`
- `$.items[3].freshness.generated_at`
- `$.items[3].preprocess.generated_at`
- `$.items[4].freshness.generated_at`
- `$.items[4].preprocess.generated_at`
- `$.items[5].freshness.generated_at`
- `$.items[5].preprocess.generated_at`
- `$.items[6].freshness.generated_at`
- `$.items[6].preprocess.generated_at`
- `$.items[7].freshness.generated_at`
- `$.items[7].preprocess.generated_at`
- `$.items[8].freshness.generated_at`
- `$.items[8].preprocess.generated_at`
- `$.items[9].freshness.generated_at`
- `$.items[9].preprocess.generated_at`
- `$.preprocessing_summary.generated_at`

### round_2_vs_round_3 - 35 differing JSON paths
- `$.fallback_markdown_path`
- `$.generated_at`
- `$.input_manifests.acquisition-orchestrator.path`
- `$.input_manifests.arxiv-llm-memory-discovery.path`
- `$.input_manifests.builderpulse-opportunity-radar.path`
- `$.input_manifests.follow-builders.path`
- `$.items[0].freshness.generated_at`
- `$.items[0].preprocess.generated_at`
- `$.items[10].freshness.generated_at`
- `$.items[10].preprocess.generated_at`
- `$.items[11].freshness.generated_at`
- `$.items[11].preprocess.generated_at`
- `$.items[12].freshness.generated_at`
- `$.items[12].preprocess.generated_at`
- `$.items[13].freshness.generated_at`
- `$.items[13].preprocess.generated_at`
- `$.items[1].freshness.generated_at`
- `$.items[1].preprocess.generated_at`
- `$.items[2].freshness.generated_at`
- `$.items[2].preprocess.generated_at`
- `$.items[3].freshness.generated_at`
- `$.items[3].preprocess.generated_at`
- `$.items[4].freshness.generated_at`
- `$.items[4].preprocess.generated_at`
- `$.items[5].freshness.generated_at`
- `$.items[5].preprocess.generated_at`
- `$.items[6].freshness.generated_at`
- `$.items[6].preprocess.generated_at`
- `$.items[7].freshness.generated_at`
- `$.items[7].preprocess.generated_at`
- `$.items[8].freshness.generated_at`
- `$.items[8].preprocess.generated_at`
- `$.items[9].freshness.generated_at`
- `$.items[9].preprocess.generated_at`
- `$.preprocessing_summary.generated_at`


## Normalized diffs (timestamps + run-root paths masked)

- round_1_vs_round_2: 0 diffs
- round_2_vs_round_3: 0 diffs
- zero remaining diffs: output is deterministic modulo the unstable fields below

## Unstable fields and why they change

| Field | Where | Why it changes between rounds |
| --- | --- | --- |
| `generated_at` | pack root, `preprocessing_summary`, every item's `freshness`, item `preprocess`, ledger files | wall-clock time of the run that produced the artifact |
| `freshness.generated_at` | per item | inherited from the ledger that promoted the item; under resume, a cached ledger keeps the timestamp of the ORIGINAL run, so this also encodes recovery history (documented, intended) |
| `*_path` absolute prefixes | `fallback_markdown_path`, any local cache paths | each round writes into its own run directory; sub-path layout is identical |
| everything else | - | deterministic: item ids, dedupe/merge results, citations, tags, summaries, attempt classifications are all derived from fixed inputs by stable hashing |
