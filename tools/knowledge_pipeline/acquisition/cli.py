from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .models import AcquisitionTask
from .orchestrator import Orchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the local acquisition orchestrator and emit a structured ledger JSON."
    )
    parser.add_argument("--url", required=True, help="Source URL to acquire.")
    parser.add_argument("--task-id", default=None, help="Optional stable task id.")
    parser.add_argument("--title", default=None, help="Optional source title.")
    parser.add_argument("--source-type", default="webpage", help="Logical source type.")
    parser.add_argument("--task-kind", default="fetch", help="Acquisition task kind.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute adapters instead of producing a deterministic dry-run ledger.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the emitted ledger JSON.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    task = AcquisitionTask.from_url(
        args.url,
        task_id=args.task_id,
        title=args.title,
        source_type=args.source_type,
        task_kind=args.task_kind,
    )
    orchestrator = Orchestrator(env=dict(os.environ), execute=args.execute)
    ledger = orchestrator.run(task)
    payload = json.dumps(ledger.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
