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

## Round 2 (this round): Fault Injection Matrix

Extended the evaluation to full fault injection with 14 fault categories and
SIGKILL injection at every pipeline stage. Fixed batch of local test inputs +
local mock fault-origin server + driver subprocess harness + matrix runner.

| Phase | Description | Status | Next Step |
| --- | --- | --- | --- |
| 1 | Benchmark Dataset Design & Exploration (round 1) | complete | - |
| 2 | Pipeline Audit & Failure Mode Verification (round 1) | complete | - |
| 3 | Baseline Metrics Measurement (round 1) | complete | - |
| 4 | Root Cause Fixes & Pipeline Hardening (round 1) | complete | - |
| 5 | Post-fix Verification & Baseline Documentation (round 1) | complete | - |
| 6 | Fault-injection harness (fixtures, mock origin, driver, verifier, matrix runner) | complete | `tests/fault_injection/` |
| 7 | Pre-fix matrix run (evidence archive) | complete | `tests/fault_injection/reports/prefix/` |
| 8 | Fixes F1-F7 + regression (45/45 pytest) | complete | see findings.md |
| 9 | Post-fix matrix (fixed / kill / update / stability) all green | complete | `tests/fault_injection/reports/postfix/` |

## Constraints

- Do NOT add new collection sources.
- Do NOT create new scheduled tasks/crons.
- Do NOT send digests/summaries outbound.
- Adhere to SpecMesh and planning-with-files conventions.

## Next Step

Present the fault-injection matrix report and stability report to the user.

## Decisions Made

| Decision | Rationale | Impact |
| --- | --- | --- |
| Use isolated test fixtures under `tests/fixtures/` and dedicated test suites under `tests/` | Allows deterministic, reproducible evaluation without mutating production workspace | Clean automated regression testing and clear baseline measurement |
| Integrate acquisition ledgers directly into `build_knowledge_pack.py` | Complete the `source -> recipe -> ledger -> knowledge_pack` pipeline contract documented in architecture docs | Fulfills end-to-end integration without adding new collection sources |
| Canonicalize URLs and unify item deduplication across source boundaries | `dedupe_items` previously keyed on `source_id::url`, failing cross-source deduplication and alias merging | Eliminates 100% of redundant inputs and resolves source conflict bugs |
| Implement content validation in `AcquisitionAdapter` | Previously empty or whitespace-only bodies were marked as successful and promoted | Prevents corrupted / empty items from entering knowledge packs |
| Add checkpoint-based resumption in `Orchestrator.run_batch` | Enables interruption recovery without re-fetching or duplicating items | Increases rerun efficiency with zero duplicate effort |
| Round 2: fixed port (8975) mock origin + fixed task batch | Port/URL changes would change canonical URLs, digests, and item IDs | Byte-identical outputs across rounds make the 3-round diff meaningful |
| Round 2: kill injection wraps the production write seam (`atomic_write_text`), not a copy of the pipeline | The driver must exercise the real production code paths | Kill trials prove properties of the shipped code, not of a test double |
| Round 2: syndication merge requires title AND body identity | Same-title-different-content must never merge; body identity is the safe discriminator | Pass-2 dedupe merges mirrors only, keeps distinct articles separate |
| Round 2: keep same-URL-different-title merge (URL-primary key) | Established round-1 contract (`test_06`) merges conflicting sources on one canonical URL | Contradictions now flagged via `content_conflict` instead of being split apart |

## Errors Encountered

| Error | Attempt | Resolution |
| --- | --- | --- |
| Missing `canonicalize_url` import during initial test run (round 1) | 1 | Implemented `canonicalize_url` in `models.py` and exported cleanly |
| `AcquisitionAdapter` promoting empty bodies (round 1) | 1 | Added `is_valid_content` filter in `adapters.py` |
| Harness `pkill -f` pattern matched its own shell and killed the matrix run | 1 | Use a non-self-matching pattern (`fault_injection[.]mock_server`) |
| `IncompleteRead(partial=<int>)` crashes `__repr__` (`len()` of int) | 1 | Pass the actually-read bytes (`partial=raw`) per stdlib contract |
| Fix F5 initially misclassified cap-truncated 5MB responses (Content-Length > cap) as transport truncation | 1 | Check the cap-overflow case FIRST, then the declared-length shortfall; caught by fault matrix row `12_very_long_body` and fixed |
