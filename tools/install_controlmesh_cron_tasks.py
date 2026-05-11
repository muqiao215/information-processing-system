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
    "daily-knowledge-pack-builder",
    "daily-notebooklm-content-gen",
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


def knowledge_pack_task_description() -> str:
    return dedent(
        """\
        # Daily Knowledge Pack Builder

        ## Goal

        Build the phase-1 canonical `knowledge_pack` from the current acquisition manifests.

        ## Assignment

        Allowed write targets:
        - this task folder
        - `/root/.controlmesh/workspace/output_to_user`

        Execution steps:
        1. Read `daily-knowledge-pack-builder_MEMORY.md`.
        2. Run:
           - `python3 scripts/run_task.py`
        3. The wrapper handles:
           - checking the three upstream manifest paths
           - invoking the repo-owned canonical builder with stable absolute paths
           - writing a task-local run summary under `artifacts/`
        4. Confirm these files exist:
           - `/root/.controlmesh/workspace/output_to_user/knowledge_pack_latest.json`
           - `/root/.controlmesh/workspace/output_to_user/knowledge_pack_latest.md`
           - `/root/.controlmesh/workspace/output_to_user/information_pipeline/bundles/YYYY-MM-DD/knowledge_pack.json`
           - `/root/.controlmesh/workspace/output_to_user/information_pipeline/bundles/YYYY-MM-DD/knowledge_pack.md`
        5. Parse `knowledge_pack_latest.json` and verify:
           - `item_count` equals `len(items)`
           - `source_counts` is present
           - `preprocessing_summary` is present

        Important:
        - Do not call external messaging tools.
        - Do not create NotebookLM notebooks here.
        - This task should not use Chrome or NotebookLM browser resources.
        - Missing upstream manifests should be reported as warnings unless all sources are missing or empty.

        ## Output

        Return a concise Chinese result:
        - 哪些 upstream manifest 存在 / 缺失
        - `knowledge_pack_latest.json` 是否写入成功
        - `knowledge_pack_latest.md` 是否写入成功
        - 日期化 pipeline 路径是否写入成功
        - `item_count`
        - `source_counts`
        - 如果失败：明确 blocker 和原始错误
        """
    )


def knowledge_pack_wrapper() -> str:
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
        BUILD_SCRIPT = (
            REPO_ROOT
            / "tools"
            / "knowledge_pipeline"
            / "normalization"
            / "build_knowledge_pack.py"
        )
        ARTIFACT_DIR = TASK_ROOT / "artifacts"
        OUTPUT_ROOT = WORKSPACE_ROOT / "output_to_user"
        LATEST_JSON = OUTPUT_ROOT / "knowledge_pack_latest.json"
        LATEST_MD = OUTPUT_ROOT / "knowledge_pack_latest.md"

        UPSTREAMS = {
            "follow_builders": OUTPUT_ROOT / "ai_builders_digest_sources_latest.json",
            "builderpulse": OUTPUT_ROOT / "builderpulse_opportunity_radar_sources_latest.json",
            "arxiv": OUTPUT_ROOT / "arxiv_llm_memory_discovery_latest.json",
        }


        def main() -> int:
            ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
            OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

            upstream_status = {
                name: {"path": str(path), "exists": path.exists()}
                for name, path in UPSTREAMS.items()
            }

            completed = subprocess.run(
                ["python3", str(BUILD_SCRIPT)],
                check=True,
                capture_output=True,
                text=True,
                cwd=str(WORKSPACE_ROOT),
            )

            manifest = json.loads(LATEST_JSON.read_text(encoding="utf-8"))
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            summary = {
                "status": "ok",
                "upstreams": upstream_status,
                "knowledge_pack_latest_json": str(LATEST_JSON),
                "knowledge_pack_latest_md": str(LATEST_MD),
                "item_count": manifest.get("item_count"),
                "source_counts": manifest.get("source_counts"),
                "preprocessing_summary": manifest.get("preprocessing_summary"),
                "builder_stdout_preview": completed.stdout.strip()[:1200],
            }
            summary_path = ARTIFACT_DIR / f"{timestamp}-run_summary.json"
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def notebooklm_content_gen_task_description() -> str:
    return dedent(
        """\
        # Daily NotebookLM Report Generation

        ## Goal

        Generate the daily NotebookLM report from the latest canonical `knowledge_pack`
        using the `notebooklm` CLI from `PATH` with the shared Chrome CDP endpoint.

        This task is report-only. A report successfully generated and downloaded to
        `output_to_user` is the success gate. Do not generate video or slide deck here;
        those belong to the downstream artifact trigger task.

        ## Assignment

        This is a native ControlMesh cron task installed from the
        `information-processing-system` repository. Prefer the local wrapper:
        - `python3 scripts/run_task.py`

        Dependencies:
        - `/root/.controlmesh/workspace/output_to_user/knowledge_pack_latest.json`
          from `daily-knowledge-pack-builder`, or the legacy fallback
          `/root/.controlmesh/workspace/output_to_user/ai_builders_digest_sources_latest.json`
        - Chrome CDP at `127.0.0.1:9222`
        - a working NotebookLM login for that browser

        Allowed write targets:
        - this task folder
        - `/root/.controlmesh/workspace/output_to_user`
        - NotebookLM notebooks and report artifacts via the CLI

        Execution steps:
        1. Read `daily-notebooklm-content-gen_MEMORY.md`.
        2. Run:
           - `python3 scripts/run_task.py`
        3. The wrapper handles:
           - browser/CDP and auth preflight
           - canonical knowledge-pack loading with one-shot legacy fallback
           - notebook creation
           - importing local markdown targets first, then URL targets
           - fallback markdown import when partial source import fails
           - report generation and markdown download
           - writing run metadata for downstream consumers
        4. Confirm these files exist:
           - `/root/.controlmesh/workspace/output_to_user/notebooklm_report_YYYYMMDD.md`
           - `/root/.controlmesh/workspace/output_to_user/notebooklm_report_run_YYYYMMDD.json`
           - `/root/.controlmesh/workspace/output_to_user/notebooklm_report_run_latest.json`
        5. If browser/CDP, auth, source import, report generation, or download fails, report the blocker clearly and stop. Do not fake success.

        Important:
        - Use the `notebooklm` CLI from `PATH`.
        - Use `127.0.0.1:9222`; do not probe retired endpoints.
        - Use `generate report --format briefing_doc`.
        - Do not generate `slide-deck` or `video` in this task.
        - Treat the report markdown download as the only success gate.

        ## Output

        Return a concise Chinese result:
        - browser/CDP 是否可用
        - NotebookLM auth 是否可用
        - canonical knowledge_pack 是否存在
        - 是否退回 legacy manifest 兼容模式
        - notebook 是否创建成功
        - report 是否生成并成功落盘
        - 成功写入了哪些文件路径
        - 是否写出 `notebooklm_report_run_latest.json`
        - 如果失败：明确阻塞点
        """
    )


def notebooklm_content_gen_wrapper() -> str:
    return dedent(
        """\
        #!/usr/bin/env python3
        from __future__ import annotations

        import json
        import os
        import shutil
        import subprocess
        from datetime import datetime
        from pathlib import Path


        WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/root/.controlmesh/workspace"))
        OUTPUT_ROOT = WORKSPACE_ROOT / "output_to_user"
        TASK_ROOT = Path(__file__).resolve().parents[1]
        ARTIFACT_DIR = TASK_ROOT / "artifacts"
        KNOWLEDGE_PACK_PATH = OUTPUT_ROOT / "knowledge_pack_latest.json"
        KNOWLEDGE_PACK_MD = OUTPUT_ROOT / "knowledge_pack_latest.md"
        LEGACY_MANIFEST_PATH = OUTPUT_ROOT / "ai_builders_digest_sources_latest.json"
        NOTEBOOKLM_BIN = shutil.which("notebooklm") or "notebooklm"
        HOST = "127.0.0.1"
        PORT = 9222


        def now_local() -> datetime:
            return datetime.now().astimezone()


        def date_compact(date_value: str) -> str:
            return date_value.replace("-", "")


        def run_command(args: list[str], timeout: float | None = None) -> subprocess.CompletedProcess:
            return subprocess.run(
                args,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )


        def run_notebooklm(args: list[str], timeout: float | None = None) -> subprocess.CompletedProcess:
            return run_command([NOTEBOOKLM_BIN, "--host", HOST, "--port", str(PORT), *args], timeout=timeout)


        def command_result(completed: subprocess.CompletedProcess) -> dict:
            payload = parse_json(completed.stdout)
            return {
                "args": completed.args,
                "returncode": completed.returncode,
                "stdout": (completed.stdout or "").strip()[-4000:],
                "stderr": (completed.stderr or "").strip()[-4000:],
                "json": payload,
            }


        def parse_json(text: str | None) -> dict | list | None:
            raw = (text or "").strip()
            if not raw:
                return None
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None


        def ensure_ok(completed: subprocess.CompletedProcess, context: str) -> dict | list:
            payload = parse_json(completed.stdout)
            if completed.returncode != 0:
                raise RuntimeError(
                    f"{context} failed: returncode={completed.returncode}; stderr={(completed.stderr or '').strip()}"
                )
            if payload is None:
                raise RuntimeError(f"{context} returned non-JSON output")
            return payload


        def load_json(path: Path) -> dict:
            return json.loads(path.read_text(encoding="utf-8"))


        def write_json(path: Path, payload: dict) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")


        def choose_canonical_target(item: dict) -> tuple[str, str] | None:
            for target in item.get("import_targets", []):
                kind = str(target.get("kind") or "")
                value = str(target.get("value") or "")
                if kind == "markdown_file" and value and Path(value).exists():
                    return ("file", value)
            local_text_path = item.get("local_text_path")
            if local_text_path and Path(local_text_path).exists():
                return ("file", str(local_text_path))
            for target in item.get("import_targets", []):
                kind = str(target.get("kind") or "")
                value = str(target.get("value") or "")
                if kind == "url" and value:
                    return ("url", value)
            return None


        def build_legacy_fallback(manifest: dict, destination: Path) -> Path:
            lines = ["# Legacy NotebookLM Source Bundle", ""]
            for source in manifest.get("selectedSources", []):
                title = str(source.get("title") or source.get("originalTitle") or "Untitled").strip()
                url = str(source.get("url") or "").strip()
                summary = str(source.get("summary") or "").strip()
                original_text = str(source.get("originalText") or "").strip()
                lines.append(f"## {title}")
                lines.append("")
                if url:
                    lines.append(f"- url: {url}")
                if summary:
                    lines.extend(["### Summary", "", summary, ""])
                if original_text:
                    lines.extend(["### Raw Text", "", original_text, ""])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("\\n".join(lines).strip() + "\\n", encoding="utf-8")
            return destination


        def preflight() -> dict:
            result = {}
            ss_bin = shutil.which("ss")
            if ss_bin:
                socket_check = run_command([ss_bin, "-ltn", f"( sport = :{PORT} )"], timeout=15)
                result["socket"] = command_result(socket_check)
                if socket_check.returncode != 0 or f":{PORT}" not in (socket_check.stdout or ""):
                    raise RuntimeError(f"Chrome CDP socket {HOST}:{PORT} is not listening")

            browser = run_notebooklm(["browser", "status", "--json"], timeout=60)
            browser_payload = ensure_ok(browser, "browser status")
            result["browser_status"] = command_result(browser)
            if not isinstance(browser_payload, dict) or not browser_payload.get("connected"):
                raise RuntimeError("NotebookLM browser status is not connected")

            auth = run_notebooklm(["auth", "status", "--json"], timeout=60)
            auth_payload = ensure_ok(auth, "auth status")
            result["auth_status"] = command_result(auth)
            if not isinstance(auth_payload, dict) or not auth_payload.get("ok"):
                raise RuntimeError("NotebookLM auth status is not ok")

            return result


        def import_target(notebook_id: str, mode: str, value: str) -> dict:
            if mode == "file":
                completed = run_notebooklm(["source", "add-file", value, "-n", notebook_id, "--wait", "--json"], timeout=300)
            elif mode == "url":
                completed = run_notebooklm(["source", "add-url", value, "-n", notebook_id, "--wait", "--json"], timeout=300)
            else:
                raise ValueError(f"Unsupported import mode: {mode}")
            payload = parse_json(completed.stdout)
            return {
                "ok": completed.returncode == 0,
                "mode": mode,
                "value": value,
                "result": command_result(completed),
                "payload": payload,
            }


        def main() -> int:
            ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
            OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

            created_at = now_local()
            preflight_result = preflight()

            compatibility_mode = False
            legacy_manifest_path = None
            fallback_source_path = None

            if KNOWLEDGE_PACK_PATH.exists():
                source_payload = load_json(KNOWLEDGE_PACK_PATH)
                date_value = str(source_payload.get("date") or created_at.date().isoformat())
                notebook_title = f"NotebookLM Daily Report {date_value}"
                source_entries = []
                seen_targets = set()
                for item in source_payload.get("items", []):
                    selected = choose_canonical_target(item)
                    if not selected:
                        source_entries.append(
                            {
                                "item_id": item.get("item_id"),
                                "title": item.get("title"),
                                "ok": False,
                                "mode": None,
                                "value": None,
                                "reason": "no_import_target",
                            }
                        )
                        continue
                    mode, value = selected
                    dedupe_key = (mode, value)
                    if dedupe_key in seen_targets:
                        continue
                    seen_targets.add(dedupe_key)
                    source_entries.append(
                        {
                            "item_id": item.get("item_id"),
                            "title": item.get("title"),
                            "ok": None,
                            "mode": mode,
                            "value": value,
                        }
                    )
                fallback_candidate = str(
                    source_payload.get("fallback_markdown_path") or KNOWLEDGE_PACK_MD
                )
            elif LEGACY_MANIFEST_PATH.exists():
                compatibility_mode = True
                legacy_manifest_path = str(LEGACY_MANIFEST_PATH)
                source_payload = load_json(LEGACY_MANIFEST_PATH)
                date_value = created_at.date().isoformat()
                notebook_title = f"NotebookLM Legacy Report {date_value}"
                source_entries = []
                fallback_candidate_path = build_legacy_fallback(
                    source_payload,
                    ARTIFACT_DIR / f"{date_compact(date_value)}-legacy-source-bundle.md",
                )
                fallback_candidate = str(fallback_candidate_path)
            else:
                raise RuntimeError(
                    "Neither knowledge_pack_latest.json nor ai_builders_digest_sources_latest.json exists"
                )

            created = ensure_ok(
                run_notebooklm(["notebook", "create", notebook_title, "--json"], timeout=120),
                "notebook create",
            )
            if not isinstance(created, dict) or not created.get("id"):
                raise RuntimeError("Notebook creation did not return a notebook id")
            notebook_id = str(created["id"])

            if compatibility_mode:
                urls_seen = set()
                for index, source in enumerate(source_payload.get("selectedSources", []), start=1):
                    url = str(source.get("url") or "").strip()
                    if not url or url in urls_seen:
                        continue
                    urls_seen.add(url)
                    imported = import_target(notebook_id=notebook_id, mode="url", value=url)
                    source_entries.append(
                        {
                            "item_id": f"legacy:{index}",
                            "title": source.get("title") or source.get("originalTitle"),
                            **imported,
                        }
                    )
            else:
                for entry in source_entries:
                    if entry.get("value") and entry.get("mode") and entry.get("ok") is not False:
                        imported = import_target(
                            notebook_id=notebook_id,
                            mode=str(entry["mode"]),
                            value=str(entry["value"]),
                        )
                        entry.update(imported)

            successful_imports = [entry for entry in source_entries if entry.get("ok")]
            failed_imports = [entry for entry in source_entries if entry.get("ok") is False]

            fallback_path = Path(fallback_candidate)
            if (failed_imports or not successful_imports) and fallback_path.exists():
                fallback_import = import_target(notebook_id=notebook_id, mode="file", value=str(fallback_path))
                if fallback_import.get("ok"):
                    fallback_source_path = str(fallback_path)
                    source_entries.append(
                        {
                            "item_id": "fallback-source",
                            "title": fallback_path.name,
                            **fallback_import,
                        }
                    )
                    successful_imports.append(source_entries[-1])

            if not successful_imports:
                raise RuntimeError("No NotebookLM sources were imported successfully")

            report_generation = ensure_ok(
                run_notebooklm(
                    [
                        "generate",
                        "report",
                        "-n",
                        notebook_id,
                        "--format",
                        "briefing_doc",
                        "--wait",
                        "--json",
                    ],
                    timeout=900,
                ),
                "generate report",
            )
            if not isinstance(report_generation, dict) or not report_generation.get("task_id"):
                raise RuntimeError("Report generation did not return a report artifact id")
            report_artifact_id = str(report_generation["task_id"])

            ensure_ok(
                run_notebooklm(["artifact", "wait", report_artifact_id, "-n", notebook_id, "--json"], timeout=600),
                "artifact wait",
            )

            report_path = OUTPUT_ROOT / f"notebooklm_report_{date_compact(date_value)}.md"
            ensure_ok(
                run_notebooklm(
                    [
                        "download",
                        "report",
                        str(report_path),
                        "-n",
                        notebook_id,
                        "--artifact-id",
                        report_artifact_id,
                        "--json",
                    ],
                    timeout=600,
                ),
                "download report",
            )
            if not report_path.exists() or report_path.stat().st_size == 0:
                raise RuntimeError(f"Report markdown was not written: {report_path}")

            metadata = {
                "date": date_value,
                "notebook_id": notebook_id,
                "notebook_title": notebook_title,
                "report_artifact_id": report_artifact_id,
                "report_path": str(report_path),
                "knowledge_pack_path": str(KNOWLEDGE_PACK_PATH) if KNOWLEDGE_PACK_PATH.exists() else None,
                "legacy_source_manifest_path": legacy_manifest_path,
                "source_import_summary": {
                    "total_attempted": len(source_entries),
                    "successful_count": len([entry for entry in source_entries if entry.get("ok")]),
                    "failed_count": len([entry for entry in source_entries if entry.get("ok") is False]),
                    "entries": source_entries,
                },
                "fallback_source_path": fallback_source_path,
                "created_at": created_at.isoformat(timespec="seconds"),
                "notes": [
                    "NotebookLM report generated through the PATH-installed notebooklm CLI.",
                    f"Compatibility mode used: {compatibility_mode}.",
                ],
                "preflight": preflight_result,
            }

            dated_metadata_path = OUTPUT_ROOT / f"notebooklm_report_run_{date_compact(date_value)}.json"
            latest_metadata_path = OUTPUT_ROOT / "notebooklm_report_run_latest.json"
            write_json(dated_metadata_path, metadata)
            write_json(latest_metadata_path, metadata)

            summary = {
                "status": "ok",
                "date": date_value,
                "compatibility_mode": compatibility_mode,
                "notebook_id": notebook_id,
                "report_artifact_id": report_artifact_id,
                "report_path": str(report_path),
                "dated_metadata_path": str(dated_metadata_path),
                "latest_metadata_path": str(latest_metadata_path),
                "successful_source_count": metadata["source_import_summary"]["successful_count"],
                "failed_source_count": metadata["source_import_summary"]["failed_count"],
                "fallback_source_path": fallback_source_path,
            }
            timestamp = created_at.strftime("%Y%m%dT%H%M%S%z")
            write_json(ARTIFACT_DIR / f"{timestamp}-run_summary.json", summary)
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
    "daily-knowledge-pack-builder": {
        "memory_name": "daily-knowledge-pack-builder_MEMORY.md",
        "task_description": knowledge_pack_task_description,
        "wrapper": knowledge_pack_wrapper,
    },
    "daily-notebooklm-content-gen": {
        "memory_name": "daily-notebooklm-content-gen_MEMORY.md",
        "task_description": notebooklm_content_gen_task_description,
        "wrapper": notebooklm_content_gen_wrapper,
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
