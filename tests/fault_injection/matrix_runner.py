"""Fault-matrix runner: fixed-input faults, kill injection, update, stability.

    python3 -m tests.fault_injection.matrix_runner \
        --workspace /tmp/fault_ws --report-dir reports/postfix \
        --phases fixed,kill,update,stability

Phases:
  fixed      clean end-to-end run on the fixed fault batch; per-category verdicts
  kill       checkpoint/timer SIGKILL trials at every pipeline stage + rerun
  update     content-update semantics (fresh vs resumed ledger cache)
  stability  three identical rounds; raw + normalized output diffs
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.fault_injection.fixtures_local import (  # noqa: E402
    MOCK_PORT_DEFAULT,
    UPDATED_BODY_V1,
    UPDATED_BODY_V2,
)
from tests.fault_injection.mock_server import wait_for_server  # noqa: E402
from tests.fault_injection.verify import (  # noqa: E402
    check_invariants,
    diff_json,
    load_pack,
    normalize_pack,
)

DRIVER_TIMEOUT_ACQ = 240
DRIVER_TIMEOUT_PACK = 90


# ---------------------------------------------------------------------------
# infrastructure


class MatrixRunner:
    def __init__(self, workspace: Path, report_dir: Path, port: int) -> None:
        self.workspace = workspace
        self.report_dir = report_dir
        self.port = port
        self.server_proc: subprocess.Popen | None = None
        self.rows_fixed: list[dict[str, Any]] = []
        self.rows_kill: list[dict[str, Any]] = []
        self.rows_update: list[dict[str, Any]] = []
        self.stability: dict[str, Any] = {}
        self.reference_pack: dict[str, Any] | None = None
        self.reference_root: Path | None = None
        self.reference_fetch_total: int | None = None

    # -- infrastructure ----------------------------------------------------

    def ensure_server(self) -> None:
        if wait_for_server(self.port, timeout=1.0):
            return
        epoch_file = self.workspace / "content_epoch"
        epoch_file.parent.mkdir(parents=True, exist_ok=True)
        epoch_file.write_text("1\n", encoding="utf-8")
        log_file = self.workspace / "mock_server.log"
        self.server_proc = subprocess.Popen(
            [
                sys.executable, "-m", "tests.fault_injection.mock_server",
                "--port", str(self.port),
                "--epoch-file", str(epoch_file),
                "--log-file", str(log_file),
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_for_server(self.port, timeout=15.0):
            raise RuntimeError(f"mock origin failed to start on port {self.port}")

    def set_epoch(self, epoch: int) -> None:
        (self.workspace / "content_epoch").write_text(f"{epoch}\n", encoding="utf-8")

    def run_driver(self, stage: str, run_dir: Path, kill: dict | None = None) -> tuple[int, float]:
        cmd = [
            sys.executable, "-m", "tests.fault_injection.driver",
            "--stage", stage,
            "--run-dir", str(run_dir),
            "--port", str(self.port),
        ]
        if kill:
            cmd += ["--kill", json.dumps(kill)]
        env = dict(os.environ)
        env.pop("FIRECRAWL_API_KEY", None)
        env["FAULT_DRIVER_VERBOSE"] = "1"
        started = time.monotonic()
        timeout = DRIVER_TIMEOUT_ACQ if stage == "acquisition" else DRIVER_TIMEOUT_PACK
        try:
            proc = subprocess.run(
                cmd, cwd=REPO_ROOT, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=timeout,
            )
            return proc.returncode, time.monotonic() - started
        except subprocess.TimeoutExpired:
            return -2, time.monotonic() - started

    def fresh_run_dir(self, name: str) -> Path:
        run_dir = self.workspace / name
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def fetch_total(self, run_dir: Path) -> int:
        path = run_dir / "fetch_counts.json"
        if not path.exists():
            return 0
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("total", 0)
        except json.JSONDecodeError:
            return -1

    def close(self) -> None:
        if self.server_proc is not None:
            self.server_proc.terminate()
            try:
                self.server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_proc.kill()

    # -- phase: fixed --------------------------------------------------------

    def phase_fixed(self) -> None:
        run_dir = self.fresh_run_dir("fixed_baseline")
        self.set_epoch(1)
        rc_acq, t_acq = self.run_driver("acquisition", run_dir)
        rc_pack, t_pack = self.run_driver("pack", run_dir)
        self.reference_pack = load_pack(run_dir)
        self.reference_root = run_dir
        self.reference_fetch_total = self.fetch_total(run_dir)

        pack = self.reference_pack
        invariants = check_invariants(run_dir)
        rows = evaluate_fixed_matrix(run_dir, pack, invariants)
        for row in rows:
            row["meta"] = f"acq={t_acq:.1f}s pack={t_pack:.1f}s rc={rc_acq}/{rc_pack}"
        self.rows_fixed = rows

    # -- phase: kill ---------------------------------------------------------

    def phase_kill(self) -> None:
        trials: list[dict[str, Any]] = [
            {"name": "before_task_early", "stage": "acquisition",
             "kill": {"mode": "checkpoint", "name": "before_task", "index": 5}},
            {"name": "before_task_late", "stage": "acquisition",
             "kill": {"mode": "checkpoint", "name": "before_task", "index": 18}},
            {"name": "after_ledger_3", "stage": "acquisition",
             "kill": {"mode": "checkpoint", "name": "after_ledger", "index": 3}},
            {"name": "after_ledger_12", "stage": "acquisition",
             "kill": {"mode": "checkpoint", "name": "after_ledger", "index": 12}},
            {"name": "mid_ledger_write_3", "stage": "acquisition",
             "kill": {"mode": "checkpoint", "name": "mid_ledger_write", "index": 3}},
            {"name": "timer_acq_s1", "stage": "acquisition",
             "kill": {"mode": "timer", "delay": 2.0}},
            {"name": "timer_acq_s2", "stage": "acquisition",
             "kill": {"mode": "timer", "delay": 4.5}},
            {"name": "timer_acq_s3", "stage": "acquisition",
             "kill": {"mode": "timer", "delay": 7.5}},
            {"name": "pack_before_write_2", "stage": "pack",
             "kill": {"mode": "checkpoint", "name": "pack_before_write", "index": 2}},
            {"name": "pack_mid_write_4", "stage": "pack",
             "kill": {"mode": "checkpoint", "name": "pack_mid_write", "index": 4}},
            {"name": "timer_pack_s4", "stage": "pack",
             "kill": {"mode": "timer", "delay": 0.05}},
            {"name": "plant_corrupt_ledger", "stage": "special"},
        ]
        for trial in trials:
            self.rows_kill.append(self.run_kill_trial(trial))

    def run_kill_trial(self, trial: dict[str, Any]) -> dict[str, Any]:
        name = trial["name"]
        stage = trial["stage"]
        run_dir = self.fresh_run_dir(f"kill_{name}")
        row: dict[str, Any] = {
            "trial": name,
            "stage": stage,
            "kill": trial.get("kill"),
            "killed_confirmed": False,
            "recovered": False,
            "violations": [],
            "normalized_diffs": [],
            "notes": [],
        }
        try:
            if stage == "special":
                return self.run_plant_corrupt_trial(run_dir, row)

            if stage == "acquisition":
                rc_kill, _ = self.run_driver("acquisition", run_dir, kill=trial["kill"])
                count_after_kill = self.fetch_total(run_dir)
                rc_rerun, _ = self.run_driver("acquisition", run_dir)
                rc_pack, _ = self.run_driver("pack", run_dir)
                if rc_pack != 0:
                    row["violations"].append(f"pack build failed after recovery (rc={rc_pack})")
            else:
                self.run_driver("acquisition", run_dir)
                rc_kill, _ = self.run_driver("pack", run_dir, kill=trial["kill"])
                count_after_kill = None
                rc_rerun, _ = self.run_driver("pack", run_dir)

            row["killed_confirmed"] = rc_kill == -9
            if rc_kill not in (-9,):
                row["notes"].append(
                    f"kill did not fire (rc={rc_kill}); trial ran as a clean pass"
                )
            row["recovered"] = rc_rerun == 0

            # fetch accounting for acquisition-stage kills
            if stage == "acquisition":
                total = self.fetch_total(run_dir)
                rerun_fetches = total - (count_after_kill or 0)
                row["fetch"] = {
                    "reference_total": self.reference_fetch_total,
                    "after_kill": count_after_kill,
                    "rerun_extra": rerun_fetches,
                }
                if self.reference_fetch_total and rerun_fetches > self.reference_fetch_total:
                    row["violations"].append(
                        f"rerun fetched more than a fresh pass ({rerun_fetches} > {self.reference_fetch_total})"
                    )

            pack = load_pack(run_dir)
            if pack is None:
                row["violations"].append("final pack missing after recovery")
            else:
                if self.reference_pack is not None:
                    left = normalize_pack(pack, run_root=run_dir)
                    right = normalize_pack(self.reference_pack, run_root=self.reference_root)
                    diffs = diff_json(left, right)
                    row["normalized_diffs"] = diffs
                    if diffs:
                        row["violations"].append(
                            f"pack differs from reference after recovery ({len(diffs)} diffs)"
                        )
            invariants = check_invariants(run_dir)
            row["violations"].extend(invariants["violations"])
        except Exception as exc:  # noqa: BLE001 - one broken trial must not kill the matrix
            row["violations"].append(f"trial harness error: {type(exc).__name__}: {exc}")
        return row

    def run_plant_corrupt_trial(self, run_dir: Path, row: dict[str, Any]) -> dict[str, Any]:
        rc_acq, _ = self.run_driver("acquisition", run_dir)
        ledgers_dir = run_dir / "ledgers"
        victim = ledgers_dir / "acq_dup-exact-a.json"
        row["notes"].append(f"planted corrupt JSON into {victim.name}")
        victim.write_text('{"run_id": "run:TRUNCATED', encoding="utf-8")
        rc_pack_before_fix, _ = self.run_driver("pack", run_dir)
        row["pack_with_corrupt_ledger_rc"] = rc_pack_before_fix
        if rc_pack_before_fix != 0:
            row["violations"].append(
                f"pack build crashed on corrupt ledger (rc={rc_pack_before_fix}); "
                "partial success violated"
            )
        rc_acq2, _ = self.run_driver("acquisition", run_dir)
        rc_pack2, _ = self.run_driver("pack", run_dir)
        row["recovered"] = rc_acq2 == 0 and rc_pack2 == 0
        pack = load_pack(run_dir)
        if pack is None:
            row["violations"].append("final pack missing after corrupt-ledger recovery")
        else:
            if self.reference_pack is not None:
                diffs = diff_json(
                    normalize_pack(pack, run_root=run_dir),
                    normalize_pack(self.reference_pack, run_root=self.reference_root),
                )
                row["normalized_diffs"] = diffs
                if diffs:
                    row["violations"].append(f"pack differs from reference ({len(diffs)} diffs)")
        row["violations"].extend(check_invariants(run_dir)["violations"])
        return row

    # -- phase: update -------------------------------------------------------

    def phase_update(self) -> None:
        self.set_epoch(1)
        dir_v1 = self.fresh_run_dir("update_epoch1")
        self.run_driver("acquisition", dir_v1)
        self.run_driver("pack", dir_v1)
        pack_v1 = load_pack(dir_v1)

        self.set_epoch(2)
        dir_v2 = self.fresh_run_dir("update_epoch2_fresh")
        self.run_driver("acquisition", dir_v2)
        self.run_driver("pack", dir_v2)
        pack_v2 = load_pack(dir_v2)

        dir_resume = self.fresh_run_dir("update_epoch2_resumed")
        shutil.copytree(dir_v1 / "ledgers", dir_resume / "ledgers")
        self.run_driver("acquisition", dir_resume)
        self.run_driver("pack", dir_resume)
        pack_resume = load_pack(dir_resume)
        self.set_epoch(1)

        def pricing_item(pack: dict[str, Any] | None) -> dict[str, Any] | None:
            if not pack:
                return None
            for item in pack.get("items", []):
                if item.get("title") == "Frontier Model Pricing Update":
                    return item
            return None

        item_v1, item_v2, item_resume = pricing_item(pack_v1), pricing_item(pack_v2), pricing_item(pack_resume)
        base_row = {
            "title_same": bool(item_v1 and item_v2 and item_v1["title"] == item_v2["title"]),
            "item_id_v1": item_v1 and item_v1["item_id"],
            "item_id_v2": item_v2 and item_v2["item_id"],
            "item_id_resume": item_resume and item_resume["item_id"],
            "content_v1_is_epoch1": bool(item_v1 and "Epoch 1" in item_v1["raw_text"]),
            "content_v2_is_epoch2": bool(item_v2 and "Epoch 2" in item_v2["raw_text"]),
            "resume_content_is_stale_v1": bool(item_resume and "Epoch 1" in item_resume["raw_text"]),
            "v2_item_count": pack_v2 and pack_v2["item_count"],
            "v1_item_count": pack_v1 and pack_v1["item_count"],
        }
        if base_row["item_id_v1"] != base_row["item_id_v2"]:
            base_row["violations"] = ["item_id changed across content update; stable-ID contract broken"]
        else:
            base_row["violations"] = []
        self.rows_update.append({"trial": "content_update_epoch_1_to_2", **base_row})

    # -- phase: stability ------------------------------------------------------

    def phase_stability(self, rounds: int = 3) -> None:
        run_dirs: list[Path] = []
        for index in range(1, rounds + 1):
            run_dir = self.fresh_run_dir(f"stability_round_{index}")
            self.set_epoch(1)
            self.run_driver("acquisition", run_dir)
            self.run_driver("pack", run_dir)
            run_dirs.append(run_dir)

        packs = [load_pack(run_dir) for run_dir in run_dirs]
        raw_pair_diffs = []
        normalized_pair_diffs = []
        for i in range(len(packs) - 1):
            raw = diff_json(packs[i], packs[i + 1])
            raw_pair_diffs.append({
                "pair": f"round_{i + 1}_vs_round_{i + 2}",
                "diff_count": len(raw),
                "paths": sorted({d["path"] for d in raw}),
                "samples": raw[:12],
            })
            norm = diff_json(
                normalize_pack(packs[i], run_root=run_dirs[i]),
                normalize_pack(packs[i + 1], run_root=run_dirs[i + 1]),
            )
            normalized_pair_diffs.append({
                "pair": f"round_{i + 1}_vs_round_{i + 2}",
                "diff_count": len(norm),
                "diffs": norm,
            })

        vs_reference = []
        if self.reference_pack is not None:
            for index, pack in enumerate(packs, start=1):
                norm = diff_json(
                    normalize_pack(pack, run_root=run_dirs[index - 1]),
                    normalize_pack(self.reference_pack, run_root=self.reference_root),
                )
                vs_reference.append({"round": index, "diff_count": len(norm), "diffs": norm})

        violations = [v for run_dir in run_dirs for v in check_invariants(run_dir)["violations"]]
        self.stability = {
            "rounds": [str(r) for r in run_dirs],
            "raw_pair_diffs": raw_pair_diffs,
            "normalized_pair_diffs": normalized_pair_diffs,
            "vs_reference": vs_reference,
            "violations": violations,
        }

    # -- reports ---------------------------------------------------------------

    def write_reports(self) -> None:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        (self.report_dir / "fault_matrix.json").write_text(
            json.dumps(
                {
                    "fixed": self.rows_fixed,
                    "kill": self.rows_kill,
                    "update": self.rows_update,
                },
                ensure_ascii=False, indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        (self.report_dir / "stability.json").write_text(
            json.dumps(self.stability, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.report_dir / "fault_matrix.md").write_text(render_matrix_md(self), encoding="utf-8")
        (self.report_dir / "stability.md").write_text(render_stability_md(self), encoding="utf-8")


# ---------------------------------------------------------------------------
# fixed-matrix evaluation


def evaluate_fixed_matrix(
    run_dir: Path,
    pack: dict[str, Any] | None,
    invariants: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ledgers, corrupt = {}, []
    if (run_dir / "ledgers").exists():
        from tests.fault_injection.verify import load_ledgers

        ledgers, corrupt = load_ledgers(run_dir / "ledgers")
    items_by_title: dict[str, list[dict[str, Any]]] = {}
    if pack:
        for item in pack.get("items", []):
            items_by_title.setdefault(item.get("title", ""), []).append(item)

    def ledger_attempts(task_id: str) -> list[dict[str, Any]]:
        for payload in ledgers.values():
            if payload.get("task", {}).get("task_id") == task_id:
                return payload.get("attempts", [])
        return []

    def ledger_status(task_id: str) -> str:
        for payload in ledgers.values():
            if payload.get("task", {}).get("task_id") == task_id:
                return payload.get("status", "")
        return "missing"

    def add(category: str, expectation: str, observed: str, ok: bool | None) -> None:
        verdict = {True: "PASS", False: "FAIL", None: "DOC"}[ok]
        rows.append({"category": category, "expectation": expectation, "observed": observed, "verdict": verdict})

    dup_items = items_by_title.get("Distributed Trace Sampling at Scale", [])
    add(
        "1_duplicate_article",
        "3 duplicate entries collapse to exactly 1 pack item",
        f"pack items with title: {len(dup_items)}",
        len(dup_items) == 1,
    )

    clash = items_by_title.get("Agent Memory Field Guide", [])
    distinct_ids = len({item.get("item_id") for item in clash}) == len(clash)
    bodies_distinct = len({item.get("raw_text", "")[:60] for item in clash}) == len(clash)
    add(
        "2_same_title_diff_content",
        "2 items share title but stay distinct (different item_id and body)",
        f"items={len(clash)} distinct_ids={distinct_ids} distinct_bodies={bodies_distinct}",
        len(clash) == 2 and distinct_ids and bodies_distinct,
    )

    syndicated = items_by_title.get("Vector DB Cost Playbook", [])
    merged = len(syndicated) == 1
    alias_recorded = merged and any(
        "syndicated/mirror" in str(a) for a in (syndicated[0].get("metadata", {}).get("aliases", []) if syndicated else [])
    )
    add(
        "3_same_content_diff_url",
        "identical body at two URLs merges to 1 item with alias provenance",
        f"items={len(syndicated)} alias_recorded={alias_recorded}",
        merged and alias_recorded,
    )

    updated = items_by_title.get("Frontier Model Pricing Update", [])
    add(
        "4_content_update",
        "epoch-dependent body served; see update phase for ID stability",
        f"items={len(updated)}; full semantics in update phase rows",
        len(updated) == 1,
    )

    for task_id, label in (
        ("acq:http-404", "5a_http_404"),
        ("acq:http-429", "5b_http_429"),
        ("acq:http-500", "5c_http_500"),
    ):
        attempts = ledger_attempts(task_id)
        statuses = sorted({a.get("status") for a in attempts})
        promoted = label_status = ledger_status(task_id)
        no_promo = promoted == "attempted" and not any(a.get("ok") for a in attempts)
        classified = any(str(s).startswith("http_") for s in statuses)
        add(
            label,
            "HTTP error classified per-code, cascade exhausts, nothing promoted",
            f"ledger={promoted} attempt_statuses={statuses}",
            no_promo and classified,
        )

    timeout_attempts = ledger_attempts("acq:timeout-slow")
    timeout_statuses = sorted({a.get("status") for a in timeout_attempts})
    add(
        "6_timeout",
        "attempt marked timeout, cascade exhausts, nothing promoted",
        f"ledger={ledger_status('acq:timeout-slow')} attempt_statuses={timeout_statuses}",
        ledger_status("acq:timeout-slow") == "attempted" and "timeout" in timeout_statuses,
    )

    garbled = items_by_title.get("Misdeclared Charset Memo", [])
    garbled_attempts = ledger_attempts("acq:garbled-bytes")
    garbled_rejected = any(a.get("status") == "rejected" and "mojibake" in a.get("detail", "") for a in garbled_attempts)
    add(
        "7_garbled_bytes",
        "GBK bytes declared utf-8 -> replacement-char wall -> rejected, not promoted",
        f"promoted_items={len(garbled)} rejected_detail={[a.get('detail') for a in garbled_attempts][:2]}",
        not garbled and garbled_rejected,
    )

    truncated = items_by_title.get("Quarterly Infra Report", [])
    add(
        "8_truncated_html",
        "syntactically truncated HTML is accepted as-is (no HTML parser in this layer); "
        "documented risk, content passed through verbatim",
        f"promoted_items={len(truncated)}",
        None if len(truncated) == 1 else False,
    )

    incomplete_attempts = ledger_attempts("acq:incomplete-read")
    incomplete_error = any("IncompleteRead" in a.get("detail", "") for a in incomplete_attempts)
    add(
        "9_incomplete_read",
        "declared Content-Length > body -> IncompleteRead -> error, nothing promoted",
        f"statuses={sorted({a.get('status') for a in incomplete_attempts})} "
        f"incomplete_detected={incomplete_error}",
        incomplete_error and ledger_status("acq:incomplete-read") == "attempted",
    )

    empty_attempts = ledger_attempts("acq:empty-body")
    empty_rejected = any(a.get("status") == "rejected" and "empty" in a.get("detail", "") for a in empty_attempts)
    add(
        "10_empty_body",
        "whitespace-only body rejected by content validation, nothing promoted",
        f"rejected_detail={[a.get('detail') for a in empty_attempts][:2]}",
        empty_rejected and "Whitespace Placeholder Article" not in items_by_title,
    )

    png = items_by_title.get("Binary Payload Served as Article", [])
    png_attempts = ledger_attempts("acq:wrong-mime-png")
    png_rejected = any(
        a.get("status") == "rejected" and ("binary" in a.get("detail", "") or "mojibake" in a.get("detail", ""))
        for a in png_attempts
    )
    add(
        "11_wrong_mime",
        "binary PNG on article URL -> detected as binary/mojibake -> rejected",
        f"promoted_items={len(png)} rejected_detail={[a.get('detail') for a in png_attempts][:2]}",
        not png and png_rejected,
    )

    long_items = items_by_title.get("Extremely Long Queueing Treatise", [])
    long_marked = bool(long_items) and long_items[0].get("raw_text", "").endswith(
        "[acquisition_truncated: content exceeded 200000 char fetch cap]"
    )
    add(
        "12_very_long_body",
        "5MB body truncated at fetch cap, truncation surfaced via end-of-content marker",
        f"promoted={len(long_items)} truncation_marked={long_marked}",
        len(long_items) == 1 and long_marked,
    )

    conflict = [
        item for items in [items_by_title.get(t, []) for t in
                            ("MemoryBench Final Scores", "MemoryBench Results Announced")]
        for item in items
    ]
    conflict_ok = False
    conflict_detail = f"items={len(conflict)}"
    if len(conflict) == 1:
        meta = conflict[0].get("metadata", {})
        raw = conflict[0].get("raw_text", "")
        both_claims = "score of 88" in raw and "score of 93" in raw
        conflict_flag = bool(meta.get("content_conflict"))
        conflict_ok = (
            len(meta.get("observed_sources", [])) >= 2
            and len(meta.get("citations", [])) >= 2
            and both_claims
            and conflict_flag
        )
        conflict_detail += (
            f" observed_sources={meta.get('observed_sources')} "
            f"citations={len(meta.get('citations', []))} both_claims_kept={both_claims} "
            f"conflict_flag={conflict_flag}"
        )
    add(
        "13_conflicting_sources",
        "same canonical URL, contradictory claims -> merged item keeps both citations, "
        "both texts, and raises a conflict flag",
        conflict_detail,
        conflict_ok,
    )

    arxiv = ledger_attempts("acq:arxiv-local")
    github = ledger_attempts("acq:github-local")
    add(
        "14_recipe_coverage_control",
        "control: arXiv and GitHub tasks promoted via their dedicated recipes",
        f"arxiv_first_adapter={arxiv[0].get('adapter') if arxiv else None} "
        f"github_first_adapter={github[0].get('adapter') if github else None}",
        bool(arxiv and arxiv[0].get("ok")) and bool(github and github[0].get("ok")),
    )

    if invariants["violations"]:
        rows.append({
            "category": "15_cross_cutting_invariants",
            "expectation": "pack shape, unique ids, citations, canonical urls, ledger integrity",
            "observed": "; ".join(invariants["violations"])[:400],
            "verdict": "FAIL",
        })
    else:
        rows.append({
            "category": "15_cross_cutting_invariants",
            "expectation": "pack shape, unique ids, citations, canonical urls, ledger integrity",
            "observed": f"item_count={invariants.get('item_count')} corrupt_ledgers={invariants.get('corrupt_ledgers')}",
            "verdict": "PASS",
        })
    return rows


# ---------------------------------------------------------------------------
# report rendering


def render_matrix_md(runner: MatrixRunner) -> str:
    lines = [
        "# Fault Injection Matrix",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Part 1 - Fixed-input fault matrix (no process kill)",
        "",
        "| # | Fault category | Expectation | Observed | Verdict |",
        "| --- | --- | --- | --- | --- |",
    ]
    for index, row in enumerate(runner.rows_fixed, start=1):
        expectation = row["expectation"].replace("|", "\\|")
        observed = row["observed"].replace("|", "\\|")
        lines.append(f"| {index} | {row['category']} | {expectation} | {observed} | {row['verdict']} |")

    lines += [
        "",
        "## Part 2 - Process-kill matrix (SIGKILL at stage, then rerun)",
        "",
        "Every trial: kill the driver subprocess at the marked point, rerun the "
        "killed stage to completion, rebuild the knowledge pack, then compare the "
        "recovered pack against the reference pack with timestamps and run-root "
        "paths normalized. Recovery requires zero normalized diffs and zero "
        "invariant violations.",
        "",
        "| Trial | Stage | Kill point | Killed? | Recovered? | Norm diffs | Violations |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in runner.rows_kill:
        kill = row.get("kill") or "planted corrupt ledger file"
        kill_str = json.dumps(kill, ensure_ascii=False) if isinstance(kill, dict) else str(kill)
        violations = "; ".join(row["violations"])[:220].replace("|", "\\|") or "-"
        lines.append(
            f"| {row['trial']} | {row['stage']} | `{kill_str}` "
            f"| {'yes' if row['killed_confirmed'] else 'no'} "
            f"| {'yes' if row['recovered'] else 'NO'} "
            f"| {len(row['normalized_diffs'])} | {violations} |"
        )

    if runner.rows_update:
        lines += [
            "",
            "## Part 3 - Content update semantics",
            "",
            "| Trial | item_id stable | fresh rerun sees new content | resumed cache sees old content (by design) | violations |",
            "| --- | --- | --- | --- | --- |",
        ]
        for row in runner.rows_update:
            lines.append(
                f"| {row['trial']} | {row['item_id_v1'] == row['item_id_v2']} "
                f"| {row['content_v2_is_epoch2']} | {row['resume_content_is_stale_v1']} "
                f"| {'; '.join(row.get('violations', [])) or '-'} |"
            )
    return "\n".join(lines) + "\n"


def render_stability_md(runner: MatrixRunner) -> str:
    stability = runner.stability
    lines = [
        "# Three-round Determinism Report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "Three fully identical rounds (same fixed batch, same epoch, fresh run dirs).",
        "",
    ]
    violations = stability.get("violations", [])
    lines.append(f"Cross-round invariant violations: **{len(violations)}**")
    for v in violations:
        lines.append(f"- {v}")

    lines += ["", "## Raw diffs between rounds (all of them)", ""]
    for pair in stability.get("raw_pair_diffs", []):
        lines.append(
            f"### {pair['pair']} - {pair['diff_count']} differing JSON paths"
        )
        for path in pair["paths"]:
            lines.append(f"- `{path}`")
        lines.append("")

    lines += ["", "## Normalized diffs (timestamps + run-root paths masked)", ""]
    remaining = 0
    for pair in stability.get("normalized_pair_diffs", []):
        remaining += pair["diff_count"]
        lines.append(f"- {pair['pair']}: {pair['diff_count']} diffs")
        for d in pair["diffs"][:10]:
            lines.append(f"  - `{d['path']}`: {_clip(d['left'])} vs {_clip(d['right'])}")
    if remaining == 0:
        lines.append("- zero remaining diffs: output is deterministic modulo the unstable fields below")

    lines += ["", "## Unstable fields and why they change", ""]
    lines.append(UNSTABLE_FIELD_DOC)
    return "\n".join(lines) + "\n"


def _clip(value: str, limit: int = 60) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."


UNSTABLE_FIELD_DOC = """\
| Field | Where | Why it changes between rounds |
| --- | --- | --- |
| `generated_at` | pack root, `preprocessing_summary`, every item's `freshness`, item `preprocess`, ledger files | wall-clock time of the run that produced the artifact |
| `freshness.generated_at` | per item | inherited from the ledger that promoted the item; under resume, a cached ledger keeps the timestamp of the ORIGINAL run, so this also encodes recovery history (documented, intended) |
| `*_path` absolute prefixes | `fallback_markdown_path`, any local cache paths | each round writes into its own run directory; sub-path layout is identical |
| everything else | - | deterministic: item ids, dedupe/merge results, citations, tags, summaries, attempt classifications are all derived from fixed inputs by stable hashing |"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=MOCK_PORT_DEFAULT)
    parser.add_argument(
        "--phases", type=str, default="fixed,kill,update,stability",
        help="comma-separated subset of: fixed,kill,update,stability",
    )
    args = parser.parse_args()

    runner = MatrixRunner(args.workspace, args.report_dir, args.port)
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]
    args.workspace.mkdir(parents=True, exist_ok=True)
    runner.ensure_server()
    try:
        for phase in phases:
            started = time.monotonic()
            if phase == "fixed":
                runner.phase_fixed()
            elif phase == "kill":
                runner.phase_kill()
            elif phase == "update":
                runner.phase_update()
            elif phase == "stability":
                runner.phase_stability()
            else:
                raise SystemExit(f"unknown phase: {phase}")
            print(f"phase {phase} done in {time.monotonic() - started:.1f}s", file=sys.stderr)
        runner.write_reports()
    finally:
        runner.close()

    failures = []
    for row in runner.rows_fixed:
        if row["verdict"] == "FAIL":
            failures.append(f"fixed/{row['category']}")
    for row in runner.rows_kill:
        if row["violations"] or not row["recovered"]:
            failures.append(f"kill/{row['trial']}")
    for row in runner.rows_update:
        if row.get("violations"):
            failures.append(f"update/{row['trial']}")
    if runner.stability.get("violations"):
        failures.append("stability/violations")
    for pair in runner.stability.get("normalized_pair_diffs", []):
        if pair["diff_count"]:
            failures.append(f"stability/{pair['pair']}")

    if failures:
        print("FAILING ROWS: " + ", ".join(failures), file=sys.stderr)
        return 1
    print("all matrix rows green", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
