"""Regression tests derived from the fault-injection matrix.

Fast in-process tests pin the fixed behaviors (mojibake/binary rejection,
HTTP status classification, atomic writes, transport truncation detection,
same-content dedupe, conflict flagging, corrupt-ledger tolerance) plus one
end-to-end SIGKILL-and-recover trial through the real driver subprocess.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tests.fault_injection.fixtures_local import MOCK_PORT_DEFAULT
from tests.fault_injection.mock_server import wait_for_server
from tests.fault_injection.verify import check_invariants, diff_json, load_pack, normalize_pack
from tools.knowledge_pipeline.acquisition.adapters import AcquisitionAdapter, is_valid_content
from tools.knowledge_pipeline.acquisition.models import AcquisitionTask, SourceCandidate
from tools.knowledge_pipeline.fs_utils import atomic_write_text
from tools.knowledge_pipeline.normalization.build_knowledge_pack import (
    build_acquisition_items,
    dedupe_items,
    load_ledger_payloads,
)


# ---------------------------------------------------------------------------
# content validation (乱码 / 错误 MIME / 空正文)


def test_is_valid_content_rejects_mojibake_wall():
    garbled = "原文" * 3 + "\ufffd" * 200  # >2% replacement chars
    ok, reason = is_valid_content(garbled, min_chars=40)
    assert not ok
    assert "mojibake" in reason


def test_is_valid_content_rejects_binary_payload():
    png = bytes(range(256)).decode("utf-8", errors="replace") * 2
    ok, reason = is_valid_content(png, min_chars=40)
    assert not ok
    assert "mojibake" in reason or "binary" in reason


def test_is_valid_content_still_accepts_normal_text():
    ok, reason = is_valid_content("正常中文与 English mixed content " * 5, min_chars=40)
    assert ok, reason


def test_is_valid_content_rejects_empty_and_whitespace():
    assert not is_valid_content("", min_chars=40)[0]
    assert not is_valid_content("   \n\t ", min_chars=40)[0]


# ---------------------------------------------------------------------------
# HTTP status classification


def _adapter_attempt_raising(exc: Exception) -> tuple[str, str]:
    adapter = AcquisitionAdapter(
        name="probe", mode="direct_fetch", description="",
        request_builder=lambda candidate: candidate.url,
    )
    task = AcquisitionTask.from_url("http://example.com/x", task_id="acq:probe")
    candidate = SourceCandidate.from_task(task)
    attempt, promoted = adapter.attempt(
        task=task, candidate=candidate, env={}, execute=True,
        fetcher=lambda url, headers=None: (_ for _ in ()).throw(exc),
    )
    assert promoted is None
    return attempt.status, attempt.detail


def test_http_404_classified():
    status, detail = _adapter_attempt_raising(HTTPError("u", 404, "Not Found", hdrs=None, fp=None))
    assert status == "http_404", detail


def test_http_429_classified():
    status, _ = _adapter_attempt_raising(HTTPError("u", 429, "Too Many Requests", hdrs=None, fp=None))
    assert status == "http_429"


def test_http_500_classified():
    status, _ = _adapter_attempt_raising(HTTPError("u", 500, "Internal Server Error", hdrs=None, fp=None))
    assert status == "http_500"


def test_timeout_still_classified():
    status, _ = _adapter_attempt_raising(TimeoutError("timed out"))
    assert status == "timeout"


# ---------------------------------------------------------------------------
# atomic writes (kill safety)


def test_atomic_write_replaces_target_atomically(tmp_path: Path):
    target = tmp_path / "ledger.json"
    target.write_text("v1", encoding="utf-8")
    atomic_write_text(target, "v2" * 10000)
    assert target.read_text(encoding="utf-8") == "v2" * 10000
    assert not list(tmp_path.glob("*.tmp*"))


def test_atomic_write_failure_keeps_old_target(tmp_path: Path, monkeypatch):
    target = tmp_path / "ledger.json"
    target.write_text("v1", encoding="utf-8")

    import tools.knowledge_pipeline.fs_utils as fs_utils

    def broken_replace(src, dst):
        raise OSError("simulated crash before rename")

    monkeypatch.setattr(fs_utils.os, "replace", broken_replace)
    with pytest.raises(OSError):
        atomic_write_text(target, "v2")
    assert target.read_text(encoding="utf-8") == "v1"
    monkeypatch.undo()


# ---------------------------------------------------------------------------
# dedupe: same content different URL / conflicting sources


def _pack_item(title: str, url: str, raw: str, source_id: str) -> dict:
    from tools.knowledge_pipeline.normalization.build_knowledge_pack import render_item_fallback, stable_item_id

    item = {
        "item_id": stable_item_id(source_id, title, url),
        "source_id": source_id,
        "source_type": "webpage",
        "source_of_truth": url,
        "access_path": "test",
        "url": url,
        "title": title,
        "summary": raw[:80],
        "raw_text": raw,
        "selected_reason": "test",
        "tags": [],
        "freshness": {"published_at": None, "generated_at": None},
        "content_type": "markdown",
        "import_targets": [],
        "import_policy": {"preferred": "url"},
        "fallback_content": "",
        "preprocess": {},
        "metadata": {},
    }
    item["fallback_content"] = render_item_fallback(item)
    return item


BODY = "Syndicated article body " * 10


def test_same_content_different_url_merges_with_alias():
    a = _pack_item("Same Title", "https://a.example.com/post", BODY, "src-a")
    b = _pack_item("Same Title", "https://b.example.com/mirror", BODY, "src-b")
    deduped = dedupe_items([a, b])
    assert len(deduped) == 1
    meta = deduped[0]["metadata"]
    assert any("b.example.com/mirror" in str(alias) for alias in meta["aliases"])
    assert sorted(meta["observed_sources"]) == ["src-a", "src-b"]
    assert len(meta["citations"]) == 2


def test_same_title_different_content_not_merged():
    a = _pack_item("Same Title", "https://a.example.com/1", "Body one " * 10, "src-a")
    b = _pack_item("Same Title", "https://b.example.com/2", "Body two " * 10, "src-b")
    assert len(dedupe_items([a, b])) == 2


def test_conflicting_sources_keeps_both_and_flags():
    a = _pack_item("T1", "https://x.example.com/claim?ref=newsletter", "score of 88 " * 5, "src-a")
    b = _pack_item("T2", "https://x.example.com/claim?ref=hackernews", "score of 93 " * 5, "src-b")
    deduped = dedupe_items([a, b])
    assert len(deduped) == 1  # same canonical URL after tracking-param strip
    meta = deduped[0]["metadata"]
    raw = deduped[0]["raw_text"]
    assert "score of 88" in raw and "score of 93" in raw
    assert meta.get("content_conflict") is True
    assert len(meta["citations"]) == 2


# ---------------------------------------------------------------------------
# corrupt ledger tolerance (partial success / recovery)


def _promoted_ledger_payload(task_id: str) -> dict:
    from tools.knowledge_pipeline.acquisition.models import (
        AcquisitionTask, Attempt, PromotedItem, RunLedger, SourceCandidate,
    )

    task = AcquisitionTask.from_url("http://example.com/x", task_id=task_id, title="T")
    candidate = SourceCandidate.from_task(task)
    promoted = PromotedItem.from_success(
        task=task, candidate=candidate, adapter="direct", content="content " * 20,
    )
    ledger = RunLedger(
        run_id=f"run:{task_id}", task=task, recipe_id="public_webpage_default",
        source_candidates=[candidate],
        attempts=[Attempt(adapter="direct", status="success", ok=True)],
        promoted_items=[promoted], status="promoted",
    )
    return ledger.to_dict()


def test_load_ledger_payloads_skips_corrupt_and_reports(tmp_path: Path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_promoted_ledger_payload("acq:good")), encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text('{"run_id": "run:TRUNC', encoding="utf-8")
    payloads, skipped = load_ledger_payloads([good, bad])
    assert len(payloads) == 1
    assert skipped and "bad.json" in skipped[0]


def test_build_acquisition_items_ignores_empty_ledger_list():
    assert build_acquisition_items([]) == []


# ---------------------------------------------------------------------------
# end-to-end: SIGKILL mid-acquisition, rerun, recover


@pytest.fixture(scope="module")
def fault_origin():
    if not wait_for_server(MOCK_PORT_DEFAULT, timeout=1.0):
        epoch_file = Path(tempfile.gettempdir()) / "pytest_fault_epoch"
        proc = subprocess.Popen(
            [sys.executable, "-m", "tests.fault_injection.mock_server",
             "--port", str(MOCK_PORT_DEFAULT),
             "--epoch-file", str(epoch_file)],
            cwd=REPO_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        assert wait_for_server(MOCK_PORT_DEFAULT, timeout=15.0)
        yield
        proc.terminate()
        proc.wait(timeout=5)
    else:
        yield


def _run_driver(stage: str, run_dir: Path, kill: str | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "tests.fault_injection.driver",
           "--stage", stage, "--run-dir", str(run_dir), "--port", str(MOCK_PORT_DEFAULT)]
    if kill:
        cmd += ["--kill", kill]
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=240)


def test_end_to_end_sigkill_recovery_matches_reference(fault_origin, tmp_path: Path):
    reference = tmp_path / "reference"
    proc = _run_driver("acquisition", reference)
    assert proc.returncode == 0, proc.stderr[-2000:]
    packed_ref = _run_driver("pack", reference)
    assert packed_ref.returncode == 0, packed_ref.stderr[-2000:]
    reference_pack = load_pack(reference)
    assert reference_pack is not None

    run_dir = tmp_path / "killed"
    proc = _run_driver("acquisition", run_dir,
                       kill='{"mode": "checkpoint", "name": "after_ledger", "index": 3}')
    assert proc.returncode == -9, f"expected SIGKILL confirmation, stderr: {proc.stderr[-1000:]}"
    rerun = _run_driver("acquisition", run_dir)
    assert rerun.returncode == 0, rerun.stderr[-2000:]
    packed = _run_driver("pack", run_dir)
    assert packed.returncode == 0, packed.stderr[-2000:]

    recovered = load_pack(run_dir)
    assert recovered is not None
    diffs = diff_json(
        normalize_pack(recovered, run_root=run_dir),
        normalize_pack(reference_pack, run_root=reference),
    )
    assert diffs == [], json.dumps(diffs, ensure_ascii=False)[:2000]

    invariants = check_invariants(run_dir)
    assert invariants["violations"] == [], invariants["violations"]
    assert invariants["corrupt_ledgers"] == []
