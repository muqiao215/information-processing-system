"""Pipeline driver subprocess for fault-injection runs.

Runs ONE stage of the real pipeline against the local fault origin:

    python3 -m tests.fault_injection.driver \
        --stage acquisition|pack --run-dir DIR [--epoch N] [--kill JSON]

Acquisition stage: builds the fixed task batch, runs the production
Orchestrator.run_batch (with resume) against the mock origin, writing run
ledgers into RUN_DIR/ledgers.

Pack stage: runs the production build_knowledge_pack.main over the ledger
directory, writing the knowledge pack into RUN_DIR (preprocessing disabled:
phase-2 targets x/github/arxiv/pdf URLs and would call external readers).

Kill injection (--kill JSON):
    {"mode": "timer", "delay": 1.4}                      SIGKILL after delay
    {"mode": "checkpoint", "name": "before_task", "index": 5}
    {"mode": "checkpoint", "name": "after_ledger", "index": 3}
    {"mode": "checkpoint", "name": "mid_ledger_write", "index": 3}
    {"mode": "checkpoint", "name": "pack_before_write", "index": 2}
    {"mode": "checkpoint", "name": "pack_mid_write", "index": 4}

Proxy adapter URLs (r.jina.ai / defuddle.md / archive.today / ?amp=1) are
translated back to the mock origin so every adapter in a recipe exercises the
real urllib fetch path against the faulting route.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qsl, parse_qs, urlencode, urlparse, urlunparse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.fault_injection.fixtures_local import (  # noqa: E402
    FETCH_TIMEOUT_SECONDS,
    MOCK_PORT_DEFAULT,
    build_tasks,
)

PROXY_PREFIXES = (
    "https://r.jina.ai/",
    "https://defuddle.md/",
)


def translate_request_url(request_url: str) -> str:
    for prefix in PROXY_PREFIXES:
        if request_url.startswith(prefix):
            return request_url[len(prefix):]
    if request_url.startswith("https://archive.today/"):
        query = parse_qs(urlparse(request_url).query)
        return query.get("url", [request_url])[0]
    parsed = urlparse(request_url)
    if "amp=" in parsed.query:
        pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k != "amp"]
        return urlunparse(parsed._replace(query=urlencode(pairs)))
    return request_url


class FetchCounter:
    def __init__(self, count_file: Path) -> None:
        self.count_file = count_file
        self.lock = threading.Lock()
        self.count = 0
        if count_file.exists():
            try:
                self.count = json.loads(count_file.read_text(encoding="utf-8")).get("total", 0)
            except Exception:
                self.count = 0

    def bump(self) -> None:
        with self.lock:
            self.count += 1
            total = self.count
        tmp = self.count_file.with_suffix(self.count_file.suffix + ".tmp")
        tmp.write_text(json.dumps({"total": total}) + "\n", encoding="utf-8")
        os.replace(tmp, self.count_file)


def sigkill_self() -> None:
    sys.stdout.flush()
    sys.stderr.flush()
    os.kill(os.getpid(), signal.SIGKILL)


class WriteInterceptor:
    """Intercepts durable writes to inject checkpoints.

    Wraps models.atomic_write_text when the production code provides it
    (post-fix), otherwise falls back to pathlib.Path.write_text (pre-fix
    behavior). Kill checkpoints:
      after_ledger:k     die right after the k-th ledger file write lands
      mid_ledger_write:k die right after writing half of the k-th ledger payload
      before_task:k      die before the orchestrator starts task k (see below)
      pack_before_write:i / pack_mid_write:i  same, for knowledge pack files
    """

    def __init__(self, ledger_dir: Path | None, pack_root: Path | None, fault: dict) -> None:
        self.ledger_dir = ledger_dir.resolve() if ledger_dir else None
        self.pack_root = pack_root.resolve() if pack_root else None
        self.fault = fault
        self.ledger_writes = 0
        self.pack_writes = 0
        self.lock = threading.Lock()

    def _classify(self, path: Path) -> str | None:
        path = Path(path).resolve()
        if ".tmp" in path.name:
            return None
        if self.ledger_dir and path.parent == self.ledger_dir and path.suffix == ".json":
            return "ledger"
        if self.pack_root and self.pack_root in path.parents:
            return "pack"
        return None

    def maybe_kill_before(self, kind: str) -> None:
        if self.fault.get("mode") != "checkpoint":
            return
        if self.fault.get("name") == "pack_before_write" and kind == "pack":
            with self.lock:
                self.pack_writes += 1
                hit = self.pack_writes == self.fault.get("index")
            if hit:
                sigkill_self()

    def intercept_payload(self, kind: str, payload: str) -> str:
        """Returns the payload to actually write; kills on mid-write checkpoints."""
        if self.fault.get("mode") != "checkpoint":
            return payload
        if self.fault.get("name") == "pack_mid_write" and kind == "pack":
            with self.lock:
                self.pack_writes += 1
                hit = self.pack_writes == self.fault.get("index")
            if hit:
                threading.Timer(0.0, sigkill_self).start()  # kill after the half write lands
                return payload[: max(1, len(payload) // 2)]
        if self.fault.get("name") == "mid_ledger_write" and kind == "ledger":
            with self.lock:
                self.ledger_writes += 1
                hit = self.ledger_writes == self.fault.get("index")
            if hit:
                threading.Timer(0.0, sigkill_self).start()  # kill after the half write lands
                return payload[: max(1, len(payload) // 2)]
        return payload

    def maybe_kill_after(self, kind: str) -> None:
        if self.fault.get("mode") != "checkpoint":
            return
        if self.fault.get("name") == "after_ledger" and kind == "ledger":
            with self.lock:
                self.ledger_writes += 1
                hit = self.ledger_writes == self.fault.get("index")
            if hit:
                sigkill_self()
        elif self.fault.get("name") == "pack_mid_write" and kind == "pack":
            # kill lands after the intercepted half payload was flushed
            pass


def install_write_patch(interceptor: WriteInterceptor) -> None:
    """Patch the production write seam(s) used by the stages under test."""
    try:
        from tools.knowledge_pipeline import fs_utils

        if hasattr(fs_utils, "atomic_write_text"):
            original = fs_utils.atomic_write_text

            def patched(path, data, *args, **kwargs):
                kind = interceptor._classify(path)
                if kind is None:
                    return original(path, data, *args, **kwargs)
                interceptor.maybe_kill_before(kind)
                data_to_write = interceptor.intercept_payload(kind, data)
                result = original(path, data_to_write, *args, **kwargs)
                if interceptor.fault.get("mode") == "checkpoint" and \
                        interceptor.fault.get("name") == "after_ledger" and kind == "ledger":
                    interceptor.maybe_kill_after(kind)
                return result

            fs_utils.atomic_write_text = patched
            # Patch references already imported into consuming modules.
            for module_name in (
                "tools.knowledge_pipeline.acquisition.orchestrator",
                "tools.knowledge_pipeline.normalization.build_knowledge_pack",
                "tools.knowledge_pipeline.normalization.preprocess_sources",
            ):
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                    if hasattr(module, "atomic_write_text"):
                        module.atomic_write_text = patched
            return
    except ImportError:
        pass

    # Pre-fix fallback: production code writes via pathlib.Path.write_text.
    original_write_text = Path.write_text

    def patched_write_text(path: Path, data: str, *args, **kwargs):
        kind = interceptor._classify(Path(path))
        if kind is None:
            return original_write_text(path, data, *args, **kwargs)
        interceptor.maybe_kill_before(kind)
        data_to_write = interceptor.intercept_payload(kind, data)
        result = original_write_text(path, data_to_write, *args, **kwargs)
        interceptor.maybe_kill_after(kind)
        return result

    Path.write_text = patched_write_text  # type: ignore[method-assign]


class KillBeforeTaskOrchestrator:
    """Mixes the before_task checkpoint into Orchestrator.run."""

    def __init__(self, orchestrator, index: int | None) -> None:
        self._orchestrator = orchestrator
        self._kill_index = index
        self._seen = 0

    def run_batch(self, tasks, **kwargs):
        original_run = self._orchestrator.run

        def run_with_kill(task):
            self._seen += 1
            if self._kill_index is not None and self._seen == self._kill_index:
                sigkill_self()
            return original_run(task)

        self._orchestrator.run = run_with_kill  # type: ignore[method-assign]
        return self._orchestrator.run_batch(tasks, **kwargs)


def run_acquisition(run_dir: Path, port: int, fault: dict) -> int:
    from tools.knowledge_pipeline.acquisition.models import AcquisitionTask
    from tools.knowledge_pipeline.acquisition.adapters import default_http_fetcher
    from tools.knowledge_pipeline.acquisition.orchestrator import Orchestrator

    ledger_dir = run_dir / "ledgers"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    counter = FetchCounter(run_dir / "fetch_counts.json")
    interceptor = WriteInterceptor(ledger_dir=ledger_dir, pack_root=None, fault=fault)
    install_write_patch(interceptor)

    if fault.get("mode") == "timer":
        timer = threading.Timer(float(fault["delay"]), sigkill_self)
        timer.daemon = True
        timer.start()

    def fetch(request_url: str, headers: dict[str, str] | None = None) -> str:
        counter.bump()
        target = translate_request_url(request_url)
        return default_http_fetcher(target, headers, timeout_seconds=FETCH_TIMEOUT_SECONDS)

    raw_tasks = build_tasks(port)
    kill_index = None
    if fault.get("mode") == "checkpoint" and fault.get("name") == "before_task":
        kill_index = int(fault["index"])

    tasks = [
        AcquisitionTask.from_url(
            spec["url"],
            task_id=spec["task_id"],
            title=spec["title"],
            source_type=spec["source_type"],
            source_id=spec["source_id"],
        )
        for spec in raw_tasks
    ]
    orchestrator = KillBeforeTaskOrchestrator(
        Orchestrator(env={}, execute=True, fetcher=fetch),
        kill_index,
    )
    ledgers = orchestrator.run_batch(tasks, ledger_dir=ledger_dir, resume=True)

    if fault.get("mode") == "timer":
        timer.cancel()

    result = {
        "stage": "acquisition",
        "fetch_calls_total": counter.count,
        "ledger_status": {ledger.task.task_id: ledger.status for ledger in ledgers},
    }
    (run_dir / "driver_result_acquisition.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


def run_pack(run_dir: Path, port: int, fault: dict) -> int:
    interceptor = WriteInterceptor(ledger_dir=None, pack_root=run_dir, fault=fault)
    install_write_patch(interceptor)

    if fault.get("mode") == "timer":
        timer = threading.Timer(float(fault["delay"]), sigkill_self)
        timer.daemon = True
        timer.start()

    from tools.knowledge_pipeline.normalization import build_knowledge_pack as bkp

    sys.argv = [
        "build_knowledge_pack",
        "--ledgers", str(run_dir / "ledgers"),
        "--follow-builders", str(run_dir / "missing_follow_builders.json"),
        "--builderpulse", str(run_dir / "missing_builderpulse.json"),
        "--arxiv", str(run_dir / "missing_arxiv.json"),
        "--output-root", str(run_dir),
        "--pipeline-root", str(run_dir / "bundles"),
        "--preprocess-cache-root", str(run_dir / "preprocessed"),
        "--no-preprocess",
    ]
    try:
        bkp.main()
    except SystemExit as exc:  # build_knowledge_pack raises SystemExit(0)
        if exc.code not in (0, None):
            raise
    finally:
        if fault.get("mode") == "timer":
            timer.cancel()

    pack_path = run_dir / "knowledge_pack_latest.json"
    pack = json.loads(pack_path.read_text(encoding="utf-8")) if pack_path.exists() else None
    result = {
        "stage": "pack",
        "pack_item_count": pack.get("item_count") if pack else None,
    }
    (run_dir / "driver_result_pack.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("acquisition", "pack"), required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=MOCK_PORT_DEFAULT)
    parser.add_argument("--kill", type=str, default=None, help="JSON kill injection spec")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    fault = json.loads(args.kill) if args.kill else {"mode": "none"}

    started = time.monotonic()
    if args.stage == "acquisition":
        code = run_acquisition(run_dir, args.port, fault)
    else:
        code = run_pack(run_dir, args.port, fault)
    elapsed = time.monotonic() - started
    if os.environ.get("FAULT_DRIVER_VERBOSE"):
        print(f"stage={args.stage} ok elapsed={elapsed:.2f}s", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
