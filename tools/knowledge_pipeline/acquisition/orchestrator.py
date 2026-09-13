from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .adapters import FetchFn
from .models import AcquisitionTask, PromotedItem, RunLedger, SourceCandidate, stable_digest
from .recipes import Registry, default_registry


class Orchestrator:
    def __init__(
        self,
        *,
        registry: Registry | None = None,
        env: dict[str, str] | None = None,
        execute: bool = False,
        fetcher: FetchFn | None = None,
    ) -> None:
        self.registry = registry or default_registry()
        self.env = dict(os.environ if env is None else env)
        self.execute = execute
        self.fetcher = fetcher

    def source_candidates_for(self, task: AcquisitionTask) -> list[SourceCandidate]:
        if task.url:
            return [SourceCandidate.from_task(task)]
        return []

    def run(self, task: AcquisitionTask) -> RunLedger:
        recipe = self.registry.recipe_for_task(task)
        candidates = self.source_candidates_for(task)
        attempts = []
        promoted_items: list[PromotedItem] = []

        for candidate in candidates:
            for step in recipe.steps:
                if not step.is_enabled(self.env):
                    continue
                adapter = self.registry.adapters[step.adapter_name]
                attempt, promoted = adapter.attempt(
                    task=task,
                    candidate=candidate,
                    env=self.env,
                    execute=self.execute,
                    fetcher=self.fetcher,
                )
                attempts.append(attempt)
                if promoted is not None:
                    promoted_items.append(promoted)
                    if step.stop_on_success:
                        break

        if promoted_items:
            status = "promoted"
        elif attempts:
            status = "attempted"
        else:
            status = "no_candidates"

        return RunLedger(
            run_id=f"run:{stable_digest(task.task_id, recipe.recipe_id, task.url or '')}",
            task=task,
            recipe_id=recipe.recipe_id,
            source_candidates=candidates,
            attempts=attempts,
            promoted_items=promoted_items,
            status=status,
            metadata={
                "execute": self.execute,
                "adapter_count": len(self.registry.adapters),
                "effective_steps": recipe.step_names_without_disabled(self.env),
            },
        )

    def run_batch(
        self,
        tasks: list[AcquisitionTask],
        *,
        ledger_dir: Path | None = None,
        resume: bool = True,
    ) -> list[RunLedger]:
        """Execute a batch of acquisition tasks with interruption resumption."""
        ledgers: list[RunLedger] = []
        if ledger_dir is not None:
            ledger_dir = Path(ledger_dir)
            ledger_dir.mkdir(parents=True, exist_ok=True)

        for task in tasks:
            ledger_file = None
            if ledger_dir is not None:
                safe_id = re.sub(r"[^a-zA-Z0-9._-]+", "_", task.task_id)
                ledger_file = ledger_dir / f"{safe_id}.json"

            if resume and ledger_file is not None and ledger_file.exists():
                try:
                    payload = json.loads(ledger_file.read_text(encoding="utf-8"))
                    cached_ledger = RunLedger.from_dict(payload)
                    if cached_ledger.status == "promoted":
                        ledgers.append(cached_ledger)
                        continue
                except Exception:
                    pass

            ledger = self.run(task)
            ledgers.append(ledger)

            if ledger_file is not None:
                payload_str = json.dumps(ledger.to_dict(), ensure_ascii=False, indent=2)
                ledger_file.write_text(payload_str + "\n", encoding="utf-8")

        return ledgers
