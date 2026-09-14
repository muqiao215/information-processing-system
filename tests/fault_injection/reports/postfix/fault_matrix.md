# Fault Injection Matrix

Generated: 2026-09-15 06:11:51

## Part 1 - Fixed-input fault matrix (no process kill)

| # | Fault category | Expectation | Observed | Verdict |
| --- | --- | --- | --- | --- |
| 1 | 1_duplicate_article | 3 duplicate entries collapse to exactly 1 pack item | pack items with title: 1 | PASS |
| 2 | 2_same_title_diff_content | 2 items share title but stay distinct (different item_id and body) | items=2 distinct_ids=True distinct_bodies=True | PASS |
| 3 | 3_same_content_diff_url | identical body at two URLs merges to 1 item with alias provenance | items=1 alias_recorded=True | PASS |
| 4 | 4_content_update | epoch-dependent body served; see update phase for ID stability | items=1; full semantics in update phase rows | PASS |
| 5 | 5a_http_404 | HTTP error classified per-code, cascade exhausts, nothing promoted | ledger=attempted attempt_statuses=['http_404'] | PASS |
| 6 | 5b_http_429 | HTTP error classified per-code, cascade exhausts, nothing promoted | ledger=attempted attempt_statuses=['http_429'] | PASS |
| 7 | 5c_http_500 | HTTP error classified per-code, cascade exhausts, nothing promoted | ledger=attempted attempt_statuses=['http_500'] | PASS |
| 8 | 6_timeout | attempt marked timeout, cascade exhausts, nothing promoted | ledger=attempted attempt_statuses=['timeout'] | PASS |
| 9 | 7_garbled_bytes | GBK bytes declared utf-8 -> replacement-char wall -> rejected, not promoted | promoted_items=0 rejected_detail=['invalid_content:mojibake_replacement_ratio_0.798', 'invalid_content:mojibake_replacement_ratio_0.798'] | PASS |
| 10 | 8_truncated_html | syntactically truncated HTML is accepted as-is (no HTML parser in this layer); documented risk, content passed through verbatim | promoted_items=1 | DOC |
| 11 | 9_incomplete_read | declared Content-Length > body -> IncompleteRead -> error, nothing promoted | statuses=['error'] incomplete_detected=True | PASS |
| 12 | 10_empty_body | whitespace-only body rejected by content validation, nothing promoted | rejected_detail=['invalid_content:empty_content', 'invalid_content:empty_content'] | PASS |
| 13 | 11_wrong_mime | binary PNG on article URL -> detected as binary/mojibake -> rejected | promoted_items=0 rejected_detail=['invalid_content:mojibake_replacement_ratio_0.125', 'invalid_content:mojibake_replacement_ratio_0.125'] | PASS |
| 14 | 12_very_long_body | 5MB body truncated at fetch cap, truncation surfaced via end-of-content marker | promoted=1 truncation_marked=True | PASS |
| 15 | 13_conflicting_sources | same canonical URL, contradictory claims -> merged item keeps both citations, both texts, and raises a conflict flag | items=1 observed_sources=['follow-builders', 'daily-news-summary'] citations=2 both_claims_kept=True conflict_flag=True | PASS |
| 16 | 14_recipe_coverage_control | control: arXiv and GitHub tasks promoted via their dedicated recipes | arxiv_first_adapter=arxiv_abstract github_first_adapter=direct_raw | PASS |
| 17 | 15_cross_cutting_invariants | pack shape, unique ids, citations, canonical urls, ledger integrity | item_count=10 corrupt_ledgers=[] | PASS |

## Part 2 - Process-kill matrix (SIGKILL at stage, then rerun)

Every trial: kill the driver subprocess at the marked point, rerun the killed stage to completion, rebuild the knowledge pack, then compare the recovered pack against the reference pack with timestamps and run-root paths normalized. Recovery requires zero normalized diffs and zero invariant violations.

| Trial | Stage | Kill point | Killed? | Recovered? | Norm diffs | Violations |
| --- | --- | --- | --- | --- | --- | --- |
| before_task_early | acquisition | `{"mode": "checkpoint", "name": "before_task", "index": 5}` | yes | yes | 0 | - |
| before_task_late | acquisition | `{"mode": "checkpoint", "name": "before_task", "index": 18}` | yes | yes | 0 | - |
| after_ledger_3 | acquisition | `{"mode": "checkpoint", "name": "after_ledger", "index": 3}` | yes | yes | 0 | - |
| after_ledger_12 | acquisition | `{"mode": "checkpoint", "name": "after_ledger", "index": 12}` | yes | yes | 0 | - |
| mid_ledger_write_3 | acquisition | `{"mode": "checkpoint", "name": "mid_ledger_write", "index": 3}` | yes | yes | 0 | - |
| timer_acq_s1 | acquisition | `{"mode": "timer", "delay": 2.0}` | yes | yes | 0 | - |
| timer_acq_s2 | acquisition | `{"mode": "timer", "delay": 4.5}` | yes | yes | 0 | - |
| timer_acq_s3 | acquisition | `{"mode": "timer", "delay": 7.5}` | yes | yes | 0 | - |
| pack_before_write_2 | pack | `{"mode": "checkpoint", "name": "pack_before_write", "index": 2}` | yes | yes | 0 | - |
| pack_mid_write_4 | pack | `{"mode": "checkpoint", "name": "pack_mid_write", "index": 4}` | yes | yes | 0 | - |
| timer_pack_s4 | pack | `{"mode": "timer", "delay": 0.05}` | yes | yes | 0 | - |
| plant_corrupt_ledger | special | `planted corrupt ledger file` | no | yes | 0 | - |

## Part 3 - Content update semantics

| Trial | item_id stable | fresh rerun sees new content | resumed cache sees old content (by design) | violations |
| --- | --- | --- | --- | --- |
| content_update_epoch_1_to_2 | True | True | True | - |
