#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "skills" / "skills.registry.json"
RUNTIME_ROOTS = [
    REPO_ROOT / "skills",
    Path("/root/private-sync-bundle/skills-selected"),
    Path("/root/.controlmesh/workspace/skills"),
    Path("/root/.agents/skills"),
    Path("/root/.codex/skills"),
]


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def current_locations(skill_name: str) -> list[str]:
    locations: list[str] = []
    for root in RUNTIME_ROOTS:
        candidate = root / skill_name
        if candidate.exists():
            locations.append(str(candidate))
    return locations


def build_rows() -> list[dict]:
    registry = load_registry()
    rows: list[dict] = []
    for skill_name in sorted(registry):
        item = registry[skill_name]
        repo_local = REPO_ROOT / "skills" / skill_name
        shared_source = Path(item["source_of_truth"]) if item.get("scope") == "shared-global" else Path(
            item.get("shared_source", "")
        )
        locations = current_locations(skill_name)
        rows.append(
            {
                "skill_name": skill_name,
                "current_locations": locations,
                "has_repo_local_source": repo_local.exists(),
                "has_shared_source": bool(shared_source) and shared_source.exists(),
                "has_runtime_copy": any(
                    path.startswith("/root/.controlmesh/workspace/skills/")
                    or path.startswith("/root/.agents/skills/")
                    or path.startswith("/root/.codex/skills/")
                    for path in locations
                ),
                "project_dependency": item.get("depends_on_project"),
                "classification": item.get("classification"),
                "action": item.get("action"),
                "risk": item.get("risk"),
            }
        )
    return rows


def render_table(rows: list[dict]) -> str:
    headers = [
        "skill_name",
        "has_repo_local_source",
        "has_shared_source",
        "has_runtime_copy",
        "project_dependency",
        "classification",
        "action",
        "risk",
    ]
    widths = {header: len(header) for header in headers}
    for row in rows:
        for header in headers:
            widths[header] = max(widths[header], len(str(row[header])))
    lines = []
    lines.append(" | ".join(header.ljust(widths[header]) for header in headers))
    lines.append("-+-".join("-" * widths[header] for header in headers))
    for row in rows:
        lines.append(" | ".join(str(row[header]).ljust(widths[header]) for header in headers))
        if row["current_locations"]:
            lines.append(f"  current_locations: {', '.join(row['current_locations'])}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report information-processing skill ownership and runtime copies.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a plain table.")
    args = parser.parse_args()

    rows = build_rows()
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(render_table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
