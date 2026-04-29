#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[3]


def resolve_workspace_root(start: Path | None = None) -> Path:
    start = (start or REPO_ROOT).resolve()
    if start == REPO_ROOT:
        return start.parent
    if REPO_ROOT in start.parents:
        return REPO_ROOT.parent
    return start


def resolve_notebooklm_command() -> list[str]:
    notebooklm_bin = shutil.which("notebooklm")
    return [notebooklm_bin or "notebooklm"]


WORKSPACE = resolve_workspace_root()
NOTEBOOKLM_COMMAND = resolve_notebooklm_command()
OUTPUT_DIR = WORKSPACE / "output_to_user"
DEFAULT_TRIGGER_METADATA = OUTPUT_DIR / "notebooklm_artifact_trigger_latest.json"
DEFAULT_ARTIFACT_ROOT = OUTPUT_DIR / "information_pipeline" / "artifacts"
HARVEST_LATEST_PATH = OUTPUT_DIR / "notebooklm_artifact_harvest_latest.json"
TZ = ZoneInfo("Asia/Shanghai")


@dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    json_payload: Any | None = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def brief(self) -> dict[str, Any]:
        return {
            "args": self.args,
            "returncode": self.returncode,
            "stdout": self.stdout.strip()[-4000:],
            "stderr": self.stderr.strip()[-4000:],
            "json": self.json_payload,
        }


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)


def parse_json(stdout: str) -> Any | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def run_command(args: list[str], cwd: Path | None = None, timeout: float | None = None) -> CommandResult:
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        stdout = completed.stdout or ""
        result = CommandResult(
            args=args,
            returncode=completed.returncode,
            stdout=stdout,
            stderr=completed.stderr or "",
            json_payload=parse_json(stdout),
        )
        return result
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            args=args,
            returncode=124,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + f"\nTimed out after {timeout}s",
            json_payload=parse_json(exc.stdout or ""),
        )
    except FileNotFoundError as exc:
        missing_target = exc.filename or (str(cwd) if cwd else args[0])
        return CommandResult(
            args=args,
            returncode=127,
            stdout="",
            stderr=f"{exc.strerror}: {missing_target}",
            json_payload=None,
        )


def run_notebooklm(args: list[str], host: str, port: int, timeout: float | None = None) -> CommandResult:
    return run_command(
        [*NOTEBOOKLM_COMMAND, "--host", host, "--port", str(port), *args],
        timeout=timeout,
    )


def date_compact(date_value: str) -> str:
    return date_value.replace("-", "")


def initial_metadata(trigger: dict[str, Any], trigger_path: Path, artifact_root: Path) -> dict[str, Any]:
    date_value = trigger.get("date") or datetime.now(TZ).date().isoformat()
    artifact_dir = artifact_root / date_value
    return {
        "date": date_value,
        "notebook_id": trigger.get("notebook_id"),
        "notebook_title": trigger.get("notebook_title"),
        "report_artifact_id": trigger.get("report_artifact_id"),
        "report_path": trigger.get("report_path"),
        "slide_deck_artifact_id": trigger.get("slide_deck_artifact_id"),
        "video_artifact_id": trigger.get("video_artifact_id"),
        "slide_deck_status": "not_started",
        "video_status": "not_started",
        "downloaded_paths": {},
        "harvested_at": now_iso(),
        "notes": [
            f"Read trigger metadata from {trigger_path}.",
            "Harvest uses the NotebookLM CLI on PATH with Chrome CDP 127.0.0.1:9222.",
        ],
        "status": "not_started",
        "artifact_dir": str(artifact_dir),
        "trigger_metadata_path": str(trigger_path),
        "triggered_at": trigger.get("triggered_at"),
        "preflight": {},
        "artifact_results": {},
    }


def write_harvest_metadata(metadata: dict[str, Any]) -> tuple[Path, Path]:
    dated_path = OUTPUT_DIR / f"notebooklm_artifact_harvest_{date_compact(metadata['date'])}.json"
    metadata["metadata_paths"] = {
        "dated": str(dated_path),
        "latest": str(HARVEST_LATEST_PATH),
    }
    write_json(dated_path, metadata)
    write_json(HARVEST_LATEST_PATH, metadata)
    return dated_path, HARVEST_LATEST_PATH


def check_preflight(host: str, port: int) -> tuple[bool, dict[str, Any], list[str]]:
    notes: list[str] = []
    preflight: dict[str, Any] = {}

    ss_bin = shutil.which("ss")
    if ss_bin:
        ss_result = run_command([ss_bin, "-ltn", f"( sport = :{port} )"], timeout=10)
        preflight["socket"] = ss_result.brief()
        if ss_result.ok and f":{port}" in ss_result.stdout:
            notes.append(f"CDP socket listener detected on {host}:{port}.")
        else:
            notes.append(f"CDP socket listener was not detected on {host}:{port}.")
            return False, preflight, notes
    else:
        notes.append("ss command is unavailable; relying on NotebookLM browser status instead.")

    browser = run_notebooklm(["browser", "status", "--json"], host=host, port=port, timeout=60)
    preflight["browser_status"] = browser.brief()
    browser_json = browser.json_payload if isinstance(browser.json_payload, dict) else {}
    if not browser.ok or not browser_json.get("connected"):
        notes.append("NotebookLM browser status is not connected.")
        return False, preflight, notes
    notes.append("NotebookLM browser status is connected.")

    auth = run_notebooklm(["auth", "status", "--json"], host=host, port=port, timeout=60)
    preflight["auth_status"] = auth.brief()
    auth_json = auth.json_payload if isinstance(auth.json_payload, dict) else {}
    if not auth.ok or not auth_json.get("ok"):
        notes.append("NotebookLM auth status is not ok.")
        return False, preflight, notes
    notes.append("NotebookLM auth status is ok.")

    return True, preflight, notes


def output_path_for(kind: str, date_value: str, artifact_id: str, artifact_root: Path) -> Path:
    compact = date_compact(date_value)
    if kind == "slide_deck":
        filename = f"{compact}-slide-deck-{artifact_id}.pdf"
    elif kind == "video":
        filename = f"{compact}-video-{artifact_id}.mp4"
    else:
        filename = f"{compact}-{kind}-{artifact_id}.bin"
    return artifact_root / date_value / filename


def clean_partial(path: Path) -> None:
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def classify_failure(last_error: str | None) -> str:
    if not last_error:
        return "download_failed"
    lowered = last_error.lower()
    if "received html instead of media file" in lowered:
        return "download_failed_html_response"
    if "artifactnotreadyerror" in lowered or "is not ready" in lowered:
        return "not_ready_timeout"
    if "timed out after" in lowered:
        return "wait_timeout"
    return "download_failed"


def harvest_one(
    *,
    kind: str,
    download_command: str,
    artifact_id: str | None,
    notebook_id: str | None,
    date_value: str,
    artifact_root: Path,
    timeout_seconds: float,
    poll_interval: float,
    download_timeout: float,
    host: str,
    port: int,
    force: bool,
) -> dict[str, Any]:
    if not artifact_id:
        return {
            "status": "missing_artifact_id",
            "downloaded_path": None,
            "attempts": 0,
            "notes": [f"{kind} artifact id is missing from trigger metadata."],
        }
    if not notebook_id:
        return {
            "status": "missing_notebook_id",
            "downloaded_path": None,
            "attempts": 0,
            "notes": ["notebook_id is missing from trigger metadata."],
        }

    output_path = output_path_for(kind, date_value, artifact_id, artifact_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and output_path.stat().st_size > 0 and not force:
        return {
            "status": "already_downloaded",
            "downloaded_path": str(output_path),
            "attempts": 0,
            "notes": [f"Existing non-empty file reused: {output_path}."],
        }

    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    last_get: dict[str, Any] | None = None
    last_wait: dict[str, Any] | None = None
    last_download: dict[str, Any] | None = None
    last_error: str | None = None

    while True:
        attempts += 1
        remaining = max(0.0, deadline - time.monotonic())

        get_result = run_notebooklm(
            ["artifact", "get", artifact_id, "-n", notebook_id, "--json"],
            host=host,
            port=port,
            timeout=60,
        )
        last_get = get_result.brief()

        wait_window = min(max(5.0, poll_interval), max(5.0, remaining))
        wait_result = run_notebooklm(
            [
                "artifact",
                "wait",
                artifact_id,
                "-n",
                notebook_id,
                "--timeout",
                str(int(wait_window)),
                "--json",
            ],
            host=host,
            port=port,
            timeout=wait_window + 45,
        )
        last_wait = wait_result.brief()
        if not wait_result.ok:
            last_error = (wait_result.stderr or wait_result.stdout).strip()[-1000:] or "artifact wait failed"

        partial_path = output_path.with_name(f".{output_path.name}.partial")
        clean_partial(partial_path)
        download_args = ["download", download_command, str(partial_path), "-n", notebook_id, "--artifact-id", artifact_id]
        if kind == "slide_deck":
            download_args.extend(["--format", "pdf"])
        download_args.append("--json")
        download_result = run_notebooklm(
            download_args,
            host=host,
            port=port,
            timeout=download_timeout,
        )
        last_download = download_result.brief()

        if download_result.ok and partial_path.exists() and partial_path.stat().st_size > 0:
            partial_path.replace(output_path)
            return {
                "status": "downloaded",
                "downloaded_path": str(output_path),
                "attempts": attempts,
                "artifact_get": last_get,
                "artifact_wait": last_wait,
                "download": last_download,
                "notes": [f"{kind} downloaded to {output_path}."],
            }

        clean_partial(partial_path)
        last_error = (download_result.stderr or download_result.stdout).strip()[-1000:] or last_error
        if time.monotonic() >= deadline:
            failure_status = classify_failure(last_error)
            return {
                "status": failure_status,
                "downloaded_path": None,
                "attempts": attempts,
                "artifact_get": last_get,
                "artifact_wait": last_wait,
                "download": last_download,
                "last_error": last_error,
                "notes": [
                    f"{kind} was not downloadable within {int(timeout_seconds)} seconds.",
                    f"Final classified status: {failure_status}.",
                ],
            }

        sleep_seconds = min(poll_interval, max(1.0, deadline - time.monotonic()))
        time.sleep(sleep_seconds)


def overall_status(slide_status: str, video_status: str) -> str:
    success_statuses = {"downloaded", "already_downloaded"}
    if slide_status in success_statuses and video_status in success_statuses:
        return "complete"
    if slide_status in success_statuses or video_status in success_statuses:
        return "partial"
    if slide_status.startswith("download_failed") or video_status.startswith("download_failed"):
        return "failed"
    if "missing" in slide_status or "missing" in video_status:
        return "blocked"
    return "pending"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harvest NotebookLM slide deck and video artifacts.")
    parser.add_argument("--trigger-metadata", type=Path, default=DEFAULT_TRIGGER_METADATA)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--slide-timeout", type=float, default=900.0)
    parser.add_argument("--video-timeout", type=float, default=1800.0)
    parser.add_argument("--poll-interval", type=float, default=30.0)
    parser.add_argument("--download-timeout", type=float, default=900.0)
    parser.add_argument("--force", action="store_true", help="Redownload even if target files already exist.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    if not args.trigger_metadata.exists():
        date_value = datetime.now(TZ).date().isoformat()
        metadata = initial_metadata({"date": date_value}, args.trigger_metadata, args.artifact_root)
        metadata["status"] = "blocked"
        metadata["notes"].append(f"Trigger metadata is missing: {args.trigger_metadata}.")
        write_harvest_metadata(metadata)
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return 2

    try:
        trigger = load_json(args.trigger_metadata)
    except Exception as exc:
        date_value = datetime.now(TZ).date().isoformat()
        metadata = initial_metadata({"date": date_value}, args.trigger_metadata, args.artifact_root)
        metadata["status"] = "blocked"
        metadata["notes"].append(f"Could not parse trigger metadata: {exc}.")
        write_harvest_metadata(metadata)
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return 2

    metadata = initial_metadata(trigger, args.trigger_metadata, args.artifact_root)
    preflight_ok, preflight, preflight_notes = check_preflight(args.host, args.port)
    metadata["preflight"] = preflight
    metadata["notes"].extend(preflight_notes)
    if not preflight_ok:
        metadata["status"] = "blocked"
        metadata["slide_deck_status"] = "blocked_preflight"
        metadata["video_status"] = "blocked_preflight"
        write_harvest_metadata(metadata)
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return 2

    slide = harvest_one(
        kind="slide_deck",
        download_command="slide-deck",
        artifact_id=metadata.get("slide_deck_artifact_id"),
        notebook_id=metadata.get("notebook_id"),
        date_value=metadata["date"],
        artifact_root=args.artifact_root,
        timeout_seconds=args.slide_timeout,
        poll_interval=args.poll_interval,
        download_timeout=args.download_timeout,
        host=args.host,
        port=args.port,
        force=args.force,
    )
    metadata["artifact_results"]["slide_deck"] = slide
    metadata["slide_deck_status"] = slide["status"]
    if slide.get("downloaded_path"):
        metadata["downloaded_paths"]["slide_deck"] = slide["downloaded_path"]
    metadata["notes"].extend(slide.get("notes", []))

    video = harvest_one(
        kind="video",
        download_command="video",
        artifact_id=metadata.get("video_artifact_id"),
        notebook_id=metadata.get("notebook_id"),
        date_value=metadata["date"],
        artifact_root=args.artifact_root,
        timeout_seconds=args.video_timeout,
        poll_interval=args.poll_interval,
        download_timeout=args.download_timeout,
        host=args.host,
        port=args.port,
        force=args.force,
    )
    metadata["artifact_results"]["video"] = video
    metadata["video_status"] = video["status"]
    if video.get("downloaded_path"):
        metadata["downloaded_paths"]["video"] = video["downloaded_path"]
    metadata["notes"].extend(video.get("notes", []))

    metadata["status"] = overall_status(metadata["slide_deck_status"], metadata["video_status"])
    metadata["harvested_at"] = now_iso()
    write_harvest_metadata(metadata)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
