# Findings: Quality & Reliability Evaluation

## Architectural Context

The system separates information acquisition from knowledge digestion:
`source -> acquisition recipe -> adapters -> run ledger -> knowledge_pack -> downstream digestion`

Upstream sources:
- `follow-builders`: Web and X posts
- `builderpulse`: Daily opportunity radar from repo checkout markdown
- `arxiv-llm-memory-discovery`: arXiv paper discovery
- `daily-news-summary-7am`: NewsNow / Hacker News candidate bridge
- `daily-github-trending-ai-watch`: Daily GitHub trending scrape

## Real Issues Discovered & Fixed

1. **Cross-Source Deduplication Bug in `build_knowledge_pack.py`**:
   - *Problem*: `dedupe_items` previously constructed its key as `f"{item['source_id']}::{item.get('url') or item['title']}"`. If two sources (e.g. `follow-builders` and `daily-news-summary`) reported the exact same article or research paper, both remained in the knowledge pack (0% cross-source deduplication).
   - *Fix*: Replaced deduplication key with canonical URL / normalized title. Added deep provenance merging (`observed_sources`, `aliases`, `citations`, `provenance`).

2. **URL Canonicalization & Alias Blindness**:
   - *Problem*: No normalization existed for tracking parameters (`utm_*`, `ref`, `source`), protocol variations (`http` vs `https`), trailing slashes, arXiv variants (`/abs/` vs `/pdf/...pdf`), or GitHub README paths (`raw.githubusercontent.com` vs `github.com/.../blob/...`).
   - *Fix*: Implemented `canonicalize_url()` in `models.py` and utilized it across `AcquisitionTask`, `SourceCandidate`, `PromotedItem`, and `build_knowledge_pack.py`.

3. **Empty Body & Low-Signal Text Promotion in `adapters.py`**:
   - *Problem*: `AcquisitionAdapter.attempt()` marked any non-exception response as `Attempt(status="success", ok=True)` even if `content` was empty string, whitespace, or boilerplate error text (404, Access Denied), and promoted empty `PromotedItem`s.
   - *Fix*: Added `is_valid_content()` with length threshold and error marker detection. Invalid content is marked as `Attempt(status="rejected", ok=False)` so the orchestrator can fall back to alternative adapters, and empty items are never promoted.

4. **Missing Specialized Recipes in `acquisition/recipes.py`**:
   - *Problem*: Only `public_webpage_default` and `generic_default` existed. arXiv and GitHub fell back to generic web scrapers.
   - *Fix*: Added `raw_github_default` (with `direct_raw` adapter) and `arxiv_paper_default` (with `arxiv_abstract` adapter).

5. **Disconnection between Acquisition Ledgers and Knowledge Pack**:
   - *Problem*: `build_knowledge_pack.py` had no mechanism to ingest `RunLedger`s or candidate items directly.
   - *Fix*: Added `build_acquisition_items()` and `--ledgers` argument to `build_knowledge_pack.py`, completing the canonical contract.

6. **Interruption Recovery**:
   - *Problem*: Batches had no checkpointing or resumption mechanism.
   - *Fix*: Added `Orchestrator.run_batch()` with `ledger_dir` and `resume=True`, loading completed ledgers from disk to avoid duplicate network fetches.

## Quantitative Evaluation Baseline

| Metric | Legacy System | Post-Fix Baseline | Improvement / Notes |
| --- | --- | --- | --- |
| **重复率 (Duplication Rate Eliminated)** | 10.0% (1/10 raw items, 25% duplicate capture) | **40.0%** (4/10 raw items, **100% duplicate capture**) | All 4 duplicate URLs, tracking parameter aliases, and cross-source conflicts resolved |
| **来源覆盖 (Source Coverage)** | 100.0% (Generic fallback) | **100.0%** (Dedicated recipes) | 3/3 target domains: GitHub (`raw_github_default`), arXiv (`arxiv_paper_default`), Web (`public_webpage_default`) |
| **有效条目率 (Valid Item Precision)** | 80.0% (1 empty body invalidly promoted) | **100.0%** (0 empty or error items promoted) | Missing body and timeouts cleanly rejected and logged |
| **有效唯一条目产出 (Unique Valid Entities)** | 4 / 6 distinct inputs (66.7%) | **4 / 6** distinct inputs (66.7%) | Exactly 4 clean, unique knowledge pack items from 10 inputs |
| **初次批处理耗时 (Initial Latency)** | ~2.3 ms | **2.3 ms** | Standardized mock cascade |
| **中断恢复重跑耗时 (Resumption Latency)** | ~2.3 ms (re-executed all) | **1.9 ms** (instant cache hit) | 1.2x - 1.5x speedup with zero redundant fetch calls |

---

# Round 2 Findings: Fault Injection Matrix (this round)

## Harness (tests/fault_injection/)

- `fixtures_local.py`: fixed 22-task batch covering all 14 requested fault
  categories (duplicate, same-title-diff-content, same-content-diff-URL,
  content update via epoch file, 404/429/500, timeout, garbled GBK-as-utf8,
  truncated HTML, declared-length truncation, empty body, wrong MIME PNG,
  5MB body, contradictory sources) + arXiv/GitHub recipe controls. Fixed port
  and fixed task IDs keep URLs, digests, and item IDs byte-stable.
- `mock_server.py`: deterministic fault origin on 127.0.0.1:8975; per-request
  route table, sleep route, declared-length padding route, query-keyed
  contradictory-content route.
- `driver.py`: runs ONE real pipeline stage (production
  `Orchestrator.run_batch` / `build_knowledge_pack.main`) as a killable
  subprocess; translates reader-proxy URLs back to the mock origin; SIGKILL
  injection at checkpoints (before task k, after ledger k, mid-ledger-write k,
  pack file write i, mid-pack-write i) plus seeded random-timer kills;
  per-process fetch counting for resume-efficiency analysis.
- `verify.py`: invariant checks (pack shape, unique item IDs, citations,
  canonical URLs, merge-group expectations, corrupt-ledger detection),
  timestamp/path normalization, and JSON path diffing.
- `matrix_runner.py`: phases `fixed` / `kill` / `update` / `stability`;
  writes `fault_matrix.{json,md}` + `stability.{json,md}` under `reports/`.

## Real Defects Found & Fixed (this round)

1. **F1 - One corrupt ledger bricked the whole knowledge pack build**
   (`build_knowledge_pack.py`). A SIGKILL during ledger writing left a torn
   JSON file; the next pack build crashed with `JSONDecodeError` (pre-fix
   trial `plant_corrupt_ledger`: rc=1). Fix: `load_ledger_payloads()` skips
   unreadable/corrupt ledger files and records a "partial success" note.
2. **F2 - Non-atomic writes produced torn artifacts** (orchestrator,
   build_knowledge_pack, preprocess_sources). Fix: shared
   `tools/knowledge_pipeline/fs_utils.atomic_write_text` (tmp file + fsync +
   `os.replace` + dir fsync) used for ledgers, all 6 pack files, and the
   phase-2 cache. Kill-mid-write now leaves either the old file or the new
   file, never a torn one.
3. **F3 - HTTP status codes flattened to "error"** (adapters.py). 404/429/500
   were indistinguishable in ledgers. Fix: `HTTPError` caught separately ->
   attempt status `http_<code>`; the fault matrix can now tell rate limiting
   from missing pages.
4. **F4 - Mojibake and binary garbage were promoted** (adapters.py). GBK
   bytes declared utf-8 (replacement-char ratio 0.798) and a PNG served on an
   article URL both entered the knowledge pack as "content". Fix:
   `is_valid_content` rejects >2% U+FFFD or >5% C0 control chars
   (`mojibake_replacement_ratio_*` / `binary_control_char_ratio_*`).
5. **F5 - Transport truncation was silent, cap truncation was invisible**
   (adapters.py). `read(200_000)` clamps to the amount argument, so a
   declared-Content-Length shortfall never raises (the IncompleteRead path in
   urllib only fires on `read(None)`); a 5MB body was silently cut at 200k
   with no marker. Fix: declared-length shortfall raises `IncompleteRead`;
   cap overflow appends an explicit
   `[acquisition_truncated: content exceeded 200000 char fetch cap]` marker.
   Note: the first version of this fix misclassified cap-truncation of large
   declared bodies as transport truncation; the fault matrix row
   `12_very_long_body` caught it and the precedence was corrected.
6. **F6 - Same content at different URLs was never merged** (build_knowledge_pack).
   Syndicated copies/mirrors stayed as duplicate items. Fix: pass-2 dedupe
   `merge_identical_content()` merges identical normalized title + identical
   raw_text at different canonical URLs, keeping alias/citation/observed-
   source provenance and `merged_same_content` flag. Same title with
   different body never merges (verified by `2_same_title_diff_content`).
7. **F7 - Contradictory sources merged silently** (build_knowledge_pack).
   Two collectors reporting different claims for one canonical URL were
   concatenated with no trace. Fix: pass-1 URL merge sets
   `metadata.content_conflict=true` and `render_item_fallback` surfaces it;
   both citations and both claims are preserved.

## Verification Results (post-fix)

- Fixed-input matrix: 14/14 PASS + 1 documented acceptance (truncated HTML
  passes through verbatim; this layer has no HTML parser). Pack contains
  exactly 10 unique items from 22 tasks; zero corrupt ledgers.
- Kill matrix (12 trials): before-task k, after-ledger k, mid-ledger-write,
  random-timer (3 seeds), pack-write checkpoints, planted corrupt ledger.
  All: process killed (rc=-9), rerun to completion, recovered pack identical
  to reference under timestamp/path normalization (0 diffs, 0 violations).
- Resume efficiency: reference full pass = 62 fetches; every rerun fetched
  only tasks without a promoted ledger (e.g. after_ledger_3 -> 59 extra,
  before_task_late -> 53 extra; never more than a fresh pass).
- Content update: epoch 1 -> 2 keeps item_id `webpage:2c0fae3371a6c7a4`
  stable; fresh rerun sees new body; resumed ledger cache keeps the old body
  (documented same-day staleness of `resume=True`).
- Three identical rounds: 27 raw JSON paths differ per pair, ALL of them
  timestamps or run-root-relative absolute paths; normalized diff = 0 for
  both pairs and against the reference run.
- Regression: 45/45 pytest green (29 pre-existing + 16 new in
  `tests/test_fault_injection_matrix.py`).

## Unstable Fields (explained)

| Field | Reason |
| --- | --- |
| `generated_at` (pack root, `preprocessing_summary`, item `freshness`, item `preprocess`, ledger files) | wall-clock time of the producing run |
| `freshness.generated_at` under resume | inherited from the ledger that promoted the item; cached ledgers keep the original run's timestamp (encodes recovery history, intended) |
| `fallback_markdown_path`, `input_manifests.*.path` | absolute paths containing the run/output root; sub-layout identical across rounds |
| everything else (item IDs, dedupe/merge results, citations, tags, summaries, attempt statuses, source counts) | deterministic: derived from fixed inputs by stable hashing |
