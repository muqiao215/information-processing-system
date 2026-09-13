# Task Plan: Quality & Reliability Evaluation of Information Processing System

## Goal

Perform a comprehensive quality and reliability evaluation on `muqiao215/information-processing-system`.
Verify the end-to-end pipeline:
`source -> recipe -> ledger -> knowledge_pack`
using a fixed evaluation dataset containing GitHub, arXiv, and Web inputs covering 5 failure/edge cases:
1. Duplicate URLs
2. Same content with different links (canonical URL / aliases)
3. Missing body / empty content
4. Timeout
5. Source conflict

Test interruption recovery and cross-day re-runs, checking stable IDs, partial success handling, and citation/provenance traceability. Establish baseline metrics (duplication rate, source coverage, valid item rate, processing time) and fix real issues discovered.

## Constraints

- Do NOT add new collection sources.
- Do NOT create new scheduled tasks/crons.
- Do NOT send digests/summaries outbound.
- Adhere to SpecMesh and planning-with-files conventions.

## Phases

| Phase | Description | Status | Next Step |
| --- | --- | --- | --- |
| 1 | Benchmark Dataset Design & Exploration | complete | Completed fixed 10-item dataset |
| 2 | Pipeline Audit & Failure Mode Verification | complete | Completed failure mode verification |
| 3 | Baseline Metrics Measurement | complete | Baseline computed |
| 4 | Root Cause Fixes & Pipeline Hardening | complete | Deduplication, recipes, validation, and ledger bridge fixed |
| 5 | Post-fix Verification & Baseline Documentation | complete | Verified 35/35 pytest passes, evaluation script passes |

## Next Step

Present evaluation report, baseline metrics, and fixed architectural issues to the user.

## Decisions Made

| Decision | Rationale | Impact |
| --- | --- | --- |
| Use isolated test fixtures under `tests/fixtures/` and dedicated test suites under `tests/` | Allows deterministic, reproducible evaluation without mutating production workspace | Clean automated regression testing and clear baseline measurement |
| Integrate acquisition ledgers directly into `build_knowledge_pack.py` | Complete the `source -> recipe -> ledger -> knowledge_pack` pipeline contract documented in architecture docs | Fulfills end-to-end integration without adding new collection sources |
| Canonicalize URLs and unify item deduplication across source boundaries | `dedupe_items` previously keyed on `source_id::url`, failing cross-source deduplication and alias merging | Eliminates 100% of redundant inputs and resolves source conflict bugs |
| Implement content validation in `AcquisitionAdapter` | Previously empty or whitespace-only bodies were marked as successful and promoted | Prevents corrupted / empty items from entering knowledge packs |
| Add checkpoint-based resumption in `Orchestrator.run_batch` | Enables interruption recovery without re-fetching or duplicating items | Increases rerun efficiency with zero duplicate effort |

## Errors Encountered

| Error | Attempt | Resolution |
| --- | --- | --- |
| Missing `canonicalize_url` import during initial test run | 1 | Implemented `canonicalize_url` in `models.py` and exported cleanly |
| `AcquisitionAdapter` promoting empty bodies | 1 | Added `is_valid_content` filter in `adapters.py` to reject whitespace/empty/error text |
