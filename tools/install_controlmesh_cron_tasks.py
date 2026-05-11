#!/usr/bin/env python3
"""Install repo-owned cron task contents into a ControlMesh workspace.

This repository is the source-of-truth for information-processing cron task
contracts and helper scripts. Runtime registration still happens through the
ControlMesh cron tools, but this installer syncs the task contents into the
native ``cron_tasks/<name>/`` folders after those jobs are created.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from textwrap import dedent


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/root/.controlmesh/workspace"))
DEFAULT_DEST_BASE = DEFAULT_WORKSPACE_ROOT / "cron_tasks"
SUPPORTED_TASKS = (
    "daily-github-trending-ai-watch",
    "daily-builderpulse-opportunity-radar",
    "ai-builders-digest-5briefs",
)


def github_trending_task_description() -> str:
    return dedent(
        """\
        # Daily GitHub Trending AI Watch

        ## Goal

        Collect the current GitHub Trending daily list, keep a task-local raw snapshot,
        and deliver a concise Chinese report focused on AI, agent, automation, robotics,
        and developer-tool projects.

        ## Assignment

        This is a native ControlMesh cron task installed from the
        `information-processing-system` repository. Use the local wrapper script instead of
        reaching into the repo template by relative-path assumptions.

        Allowed write targets:
        - this task folder
        - `/root/.controlmesh/workspace/output_to_user`

        Execution steps:
        1. Read `daily-github-trending-ai-watch_MEMORY.md`.
        2. Run:
           - `python3 scripts/run_task.py`
        3. Confirm the wrapper wrote:
           - `artifacts/github_trending_latest.json`
           - `artifacts/<timestamp>-github_trending.json`
           - `/root/.controlmesh/workspace/output_to_user/github_trending_ai_watch_latest.json`
        4. Read the latest raw snapshot and build the final Chinese digest.
        5. If the wrapper reports a fetch failure, state that clearly and stop. Do not fake the list.

        Hard rules:
        - Use the actual current daily trending page data from the wrapper output.
        - Keep the report in Chinese.
        - Focus on what the project does and why it matters.
        - Do not dump raw links excessively.

        ## Output

        Return this structure:
        1. `GitHub 今日趋势 Top 8`
        2. `按用户方向最值得看的 4 个`

        For each Top 8 item include:
        - `owner/repo`
        - one-sentence description
        - language | total stars | today's stars

        For each of the 4 selected items include:
        - project name
        - why it matters for AI / agent / automation / robotics / developer tools

        Append a short footer stating:
        - raw snapshot path
        - output json path
        - repo count
        """
    )


def github_trending_wrapper() -> str:
    return dedent(
        """\
        #!/usr/bin/env python3
        from __future__ import annotations

        import json
        import os
        import subprocess
        from datetime import datetime, timezone
        from pathlib import Path


        WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/root/.controlmesh/workspace"))
        REPO_ROOT = WORKSPACE_ROOT / "repos" / "information-processing-system"
        TASK_ROOT = Path(__file__).resolve().parents[1]
        REPO_SCRIPT = (
            REPO_ROOT
            / "cron_tasks"
            / "daily-github-trending-ai-watch"
            / "scripts"
            / "fetch_github_trending.py"
        )
        ARTIFACT_DIR = TASK_ROOT / "artifacts"
        OUTPUT_JSON = WORKSPACE_ROOT / "output_to_user" / "github_trending_ai_watch_latest.json"


        def main() -> int:
            ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
            OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

            completed = subprocess.run(
                ["python3", str(REPO_SCRIPT)],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(completed.stdout)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            dated_path = ARTIFACT_DIR / f"{timestamp}-github_trending.json"
            latest_path = ARTIFACT_DIR / "github_trending_latest.json"
            serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\\n"

            dated_path.write_text(serialized, encoding="utf-8")
            latest_path.write_text(serialized, encoding="utf-8")
            OUTPUT_JSON.write_text(serialized, encoding="utf-8")

            print(
                json.dumps(
                    {
                        "status": "ok",
                        "repo_count": payload.get("count", 0),
                        "artifact_path": str(latest_path),
                        "dated_artifact_path": str(dated_path),
                        "output_json_path": str(OUTPUT_JSON),
                        "source_url": payload.get("url"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def builderpulse_task_description() -> str:
    return dedent(
        """\
        # Daily BuilderPulse Opportunity Radar

        ## Goal

        Generate a standalone Chinese BuilderPulse opportunity-radar brief from the local
        BuilderPulse daily archive through a native ControlMesh cron wrapper.

        ## Assignment

        Allowed write targets:
        - this task folder
        - `/root/.controlmesh/workspace/output_to_user`
        - `/root/.controlmesh/workspace/vendor/BuilderPulse` via `git pull --ff-only` only

        Execution steps:
        1. Read `daily-builderpulse-opportunity-radar_MEMORY.md`.
        2. Run:
           - `python3 scripts/run_task.py`
        3. The wrapper handles:
           - best-effort `git pull --ff-only`
           - calling the repo-owned parser with stable absolute paths
           - writing the canonical markdown and JSON outputs
           - writing a task-local run summary under `artifacts/`
        4. Confirm these files exist:
           - `/root/.controlmesh/workspace/output_to_user/builderpulse_opportunity_radar_latest.md`
           - `/root/.controlmesh/workspace/output_to_user/builderpulse_opportunity_radar_sources_latest.json`
        5. Read the generated markdown and manifest, then return the final report.

        Important:
        - Do not modify the existing digest task.
        - Do not call external messaging tools.
        - If `git pull --ff-only` fails, report that clearly but continue with the latest local snapshot.

        ## Output

        Return the full Chinese radar brief. The markdown must contain a main section
        titled `F. 机会雷达`.

        Then append a short footer stating:
        - markdown saved path
        - source manifest saved path
        - report date
        - selected opportunity count
        - whether `git pull --ff-only` succeeded
        """
    )


def builderpulse_wrapper() -> str:
    return dedent(
        """\
        #!/usr/bin/env python3
        from __future__ import annotations

        import json
        import os
        import subprocess
        from datetime import datetime, timezone
        from pathlib import Path


        WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/root/.controlmesh/workspace"))
        REPO_ROOT = WORKSPACE_ROOT / "repos" / "information-processing-system"
        TASK_ROOT = Path(__file__).resolve().parents[1]
        REPO_SCRIPT = (
            REPO_ROOT
            / "cron_tasks"
            / "daily-builderpulse-opportunity-radar"
            / "scripts"
            / "build_builderpulse_radar.py"
        )
        BUILDERPULSE_REPO_ROOT = WORKSPACE_ROOT / "vendor" / "BuilderPulse"
        ARTIFACT_DIR = TASK_ROOT / "artifacts"
        OUTPUT_MD = WORKSPACE_ROOT / "output_to_user" / "builderpulse_opportunity_radar_latest.md"
        OUTPUT_JSON = (
            WORKSPACE_ROOT / "output_to_user" / "builderpulse_opportunity_radar_sources_latest.json"
        )


        def run_pull() -> dict:
            try:
                completed = subprocess.run(
                    ["git", "-C", str(BUILDERPULSE_REPO_ROOT), "pull", "--ff-only"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return {
                    "ok": True,
                    "stdout": completed.stdout.strip(),
                    "stderr": completed.stderr.strip(),
                }
            except subprocess.CalledProcessError as exc:
                return {
                    "ok": False,
                    "stdout": (exc.stdout or "").strip(),
                    "stderr": (exc.stderr or "").strip(),
                    "returncode": exc.returncode,
                }


        def main() -> int:
            ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
            OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

            pull_result = run_pull()
            completed = subprocess.run(
                [
                    "python3",
                    str(REPO_SCRIPT),
                    "--repo-root",
                    str(BUILDERPULSE_REPO_ROOT),
                    "--md-out",
                    str(OUTPUT_MD),
                    "--json-out",
                    str(OUTPUT_JSON),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            manifest = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            summary = {
                "status": "ok",
                "git_pull": pull_result,
                "report_date": manifest.get("report", {}).get("date"),
                "selected_opportunity_count": manifest.get("selected_opportunity_count"),
                "markdown_path": str(OUTPUT_MD),
                "manifest_path": str(OUTPUT_JSON),
                "parser_stdout_preview": completed.stdout.strip()[:1200],
            }
            summary_path = ARTIFACT_DIR / f"{timestamp}-run_summary.json"
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def builders_digest_task_description() -> str:
    return dedent(
        """\
        # AI Builders Digest 5 Briefs

        ## Goal

        Generate five Chinese AI builders digests and a machine-readable source manifest
        for downstream reuse through a native ControlMesh cron wrapper.

        ## Assignment

        Allowed write targets:
        - this task folder
        - `/root/.controlmesh/workspace/output_to_user`

        Execution steps:
        1. Read `ai-builders-digest-5briefs_MEMORY.md`.
        2. Run:
           - `python3 scripts/run_task.py`
        3. The wrapper handles:
           - fetching the follow-builders bundle
           - saving task-local dated and latest bundle snapshots
           - invoking the repo-owned digest builder with stable absolute paths
        4. Confirm these files exist:
           - `/root/.controlmesh/workspace/output_to_user/ai_builders_digest_latest.md`
           - `/root/.controlmesh/workspace/output_to_user/ai_builders_digest_sources_latest.json`
        5. Read the generated markdown and source manifest, then return the final digest.

        Important:
        - Do not call external messaging tools.
        - Do not try to create NotebookLM notebooks here.
        - This task is the source stage; the NotebookLM tasks are downstream consumers.

        ## Output

        Return the five Chinese digest sections in the final answer, then append a short
        footer stating:
        - source manifest saved path
        - markdown digest saved path
        - total selected source count
        - bundle snapshot path
        """
    )


def builders_digest_wrapper() -> str:
    return dedent(
        """\
        #!/usr/bin/env python3
        from __future__ import annotations

        import json
        import os
        import subprocess
        from datetime import datetime, timezone
        from pathlib import Path


        WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/root/.controlmesh/workspace"))
        REPO_ROOT = WORKSPACE_ROOT / "repos" / "information-processing-system"
        TASK_ROOT = Path(__file__).resolve().parents[1]
        FETCH_SCRIPT = (
            REPO_ROOT
            / "cron_tasks"
            / "ai-builders-digest-5briefs"
            / "scripts"
            / "fetch_follow_builders.py"
        )
        BUILD_SCRIPT = (
            REPO_ROOT
            / "cron_tasks"
            / "ai-builders-digest-5briefs"
            / "scripts"
            / "build_digest_outputs.py"
        )
        ARTIFACT_DIR = TASK_ROOT / "artifacts"
        OUTPUT_MD = WORKSPACE_ROOT / "output_to_user" / "ai_builders_digest_latest.md"
        OUTPUT_JSON = WORKSPACE_ROOT / "output_to_user" / "ai_builders_digest_sources_latest.json"


        def main() -> int:
            ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
            OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

            fetch_completed = subprocess.run(
                ["python3", str(FETCH_SCRIPT)],
                check=True,
                capture_output=True,
                text=True,
            )
            bundle = json.loads(fetch_completed.stdout)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            bundle_path = ARTIFACT_DIR / f"{timestamp}-follow_builders_bundle.json"
            latest_bundle_path = ARTIFACT_DIR / "follow_builders_bundle_latest.json"
            serialized_bundle = json.dumps(bundle, ensure_ascii=False, indent=2) + "\\n"
            bundle_path.write_text(serialized_bundle, encoding="utf-8")
            latest_bundle_path.write_text(serialized_bundle, encoding="utf-8")

            subprocess.run(
                [
                    "python3",
                    str(BUILD_SCRIPT),
                    "--bundle-path",
                    str(bundle_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            manifest = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
            selected_count = manifest.get("selectedSourceCount")
            if not isinstance(selected_count, int):
                selected_sources = manifest.get("selectedSources")
                if isinstance(selected_sources, list):
                    selected_count = len(selected_sources)
                else:
                    selected_count = 0
            summary = {
                "status": "ok",
                "bundle_path": str(bundle_path),
                "latest_bundle_path": str(latest_bundle_path),
                "markdown_path": str(OUTPUT_MD),
                "manifest_path": str(OUTPUT_JSON),
                "selected_source_count": selected_count,
                "feed_stats": bundle.get("stats", {}),
            }
            summary_path = ARTIFACT_DIR / f"{timestamp}-run_summary.json"
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


TASK_SPECS = {
    "daily-github-trending-ai-watch": {
        "memory_name": "daily-github-trending-ai-watch_MEMORY.md",
        "task_description": github_trending_task_description,
        "wrapper": github_trending_wrapper,
    },
    "daily-builderpulse-opportunity-radar": {
        "memory_name": "daily-builderpulse-opportunity-radar_MEMORY.md",
        "task_description": builderpulse_task_description,
        "wrapper": builderpulse_wrapper,
    },
    "ai-builders-digest-5briefs": {
        "memory_name": "ai-builders-digest-5briefs_MEMORY.md",
        "task_description": builders_digest_task_description,
        "wrapper": builders_digest_wrapper,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install repo-owned cron task contents into a ControlMesh workspace."
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=DEFAULT_WORKSPACE_ROOT,
        help="Target ControlMesh workspace root.",
    )
    parser.add_argument(
        "--dest-base",
        type=Path,
        default=None,
        help="Explicit destination cron_tasks directory. Defaults to <workspace-root>/cron_tasks.",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        choices=SUPPORTED_TASKS,
        default=list(SUPPORTED_TASKS),
        help="Task ids to install.",
    )
    return parser.parse_args()


def ensure_native_task_dir(task_dir: Path) -> None:
    if not task_dir.is_dir():
        raise FileNotFoundError(
            f"Native cron task folder does not exist yet: {task_dir}. "
            "Create it first with the official ControlMesh cron_add.py tool."
        )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def install_task(dest_base: Path, task_name: str) -> dict[str, str]:
    spec = TASK_SPECS[task_name]
    task_dir = dest_base / task_name
    ensure_native_task_dir(task_dir)
    write_text(task_dir / "TASK_DESCRIPTION.md", spec["task_description"]())
    write_text(task_dir / "scripts" / "run_task.py", spec["wrapper"]())

    memory_path = task_dir / spec["memory_name"]
    if not memory_path.exists():
        write_text(memory_path, f"# {task_name} Memory\n")

    os.chmod(task_dir / "scripts" / "run_task.py", 0o755)
    return {
        "task_dir": str(task_dir),
        "task_description": str(task_dir / "TASK_DESCRIPTION.md"),
        "wrapper_script": str(task_dir / "scripts" / "run_task.py"),
        "memory_file": str(memory_path),
    }


def main() -> int:
    args = parse_args()
    dest_base = args.dest_base or (args.workspace_root / "cron_tasks")
    result = {
        "repo_root": str(REPO_ROOT),
        "workspace_root": str(args.workspace_root),
        "dest_base": str(dest_base),
        "installed": {},
    }
    for task_name in args.tasks:
        result["installed"][task_name] = install_task(dest_base, task_name)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
