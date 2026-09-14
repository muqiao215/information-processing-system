# Progress Log: Quality & Reliability Evaluation

## Completed Actions
- Cloned `muqiao215/information-processing-system` to `/home/muqiao/projects/information-processing-system`.
- Constructed fixed evaluation benchmark dataset (`tests/fixtures/evaluation_dataset.py`) containing 10 items spanning GitHub, arXiv, and Web across 5 edge/failure cases.
- Identified 6 root causes / defects in `acquisition` and `normalization`:
  1. Cross-source deduplication failure in `build_knowledge_pack.py`.
  2. Lack of URL canonicalization and alias resolution.
  3. Acceptance and promotion of empty/missing body content in `AcquisitionAdapter`.
  4. Missing specialized recipes and adapters for GitHub and arXiv.
  5. Missing ingestion bridge from `RunLedger` to `build_knowledge_pack.py`.
  6. Lack of batch resumption for interruption recovery.
- Implemented core fixes:
  - `canonicalize_url()` and `stable_item_id()` in `tools/knowledge_pipeline/acquisition/models.py`.
  - `is_valid_content()`, timeout handling, `direct_raw`, and `arxiv_abstract` in `tools/knowledge_pipeline/acquisition/adapters.py`.
  - `raw_github_default` and `arxiv_paper_default` in `tools/knowledge_pipeline/acquisition/recipes.py`.
  - `run_batch()` with checkpoint resumption in `tools/knowledge_pipeline/acquisition/orchestrator.py`.
  - Canonical cross-source deduplication, provenance tracking, and `build_acquisition_items()` in `tools/knowledge_pipeline/normalization/build_knowledge_pack.py`.
- Created comprehensive regression and evaluation test suite (`tests/test_quality_reliability_evaluation.py`).
- Verified all 35 project tests pass with 100% success rate.
- Generated baseline metrics report (`tools/knowledge_pipeline/evaluate_quality_and_reliability.py`).
- Maintained constraints: no new collection sources added, no scheduled tasks/crons created, no digests sent outbound.

## Round 2: Fault Injection (this round)
- Built `tests/fault_injection/`: fixed 22-task fault batch (14 categories), deterministic mock fault origin on 127.0.0.1:8975, killable driver subprocess driving the real `Orchestrator.run_batch` + `build_knowledge_pack.main`, invariant verifier with timestamp/path normalization, and a 4-phase matrix runner.
- Archived the pre-fix evidence: 10 fixed-input rows FAIL (syndication not merged, HTTP codes flattened, garbled/PNG/transport-truncated content promoted, 5MB silently cut, contradictions unflagged) and pack build crashing rc=1 on one corrupt ledger; recovery mechanics themselves already consistent (0 normalized diffs after rerun).
- Fixed 7 production defects: corrupt-ledger tolerance (F1), atomic writes via new `tools/knowledge_pipeline/fs_utils.py` (F2), per-code HTTP attempt statuses (F3), mojibake/binary rejection (F4), transport-truncation detection + cap-truncation marker (F5), same-content-different-URL pass-2 dedupe (F6), `content_conflict` flag (F7). Caught and fixed a precedence bug in F5 itself via matrix row `12_very_long_body`.
- Post-fix matrix all green: fixed 14/14 PASS + 1 documented, 12/12 kill trials recovered with 0 normalized diffs, content update keeps item_id stable, three identical rounds -> 27 raw unstable paths (all timestamps or run-root paths), 0 after normalization, 45/45 pytest.
- Reports: `tests/fault_injection/reports/prefix/` (evidence) and `tests/fault_injection/reports/postfix/` (final) with `fault_matrix.{md,json}` and `stability.{md,json}`.
- Constraints kept: no new collection sources, no new crons, no outbound digests.
