"""Deterministic local mock origin for fault-injection runs.

Run as: python3 -m tests.fault_injection.mock_server --port 8975 --epoch-file PATH

Route behavior comes from fixtures_local.route_table(epoch). The epoch file is
re-read on every request so the harness can flip content epochs between runs
without restarting the server.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.fault_injection.fixtures_local import EPOCH_FILE_NAME, route_table  # noqa: E402

_LOG_LOCK = threading.Lock()
_LOG_PATH: Path | None = None


def log_line(message: str) -> None:
    if _LOG_PATH is None:
        return
    with _LOG_LOCK:
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%H:%M:%S')} {message}\n")


def read_epoch(epoch_file: Path) -> int:
    try:
        return int(epoch_file.read_text(encoding="utf-8").strip() or "1")
    except Exception:
        return 1


class FaultOriginHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "FaultOrigin/1.0"
    epoch_file: Path = Path("/tmp/fault_epoch")
    access_log: Path | None = None

    def log_message(self, fmt: str, *args: Any) -> None:  # silence stderr, use file
        log_line(f"{self.address_string()} {fmt % args}")

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        parsed = urlparse(self.path)
        route = unquote(parsed.path)
        epoch = read_epoch(self.epoch_file)
        table = route_table(epoch)
        spec = table.get(route)
        if spec is None:
            self._respond(404, b"no such fault route", "text/plain; charset=utf-8")
            return

        by_query = spec.get("by_query")
        if by_query:
            query_pairs = dict(parse_qsl(parsed.query, keep_blank_values=True))
            picked = None
            for param, outcomes in by_query.items():
                picked = outcomes.get(query_pairs.get(param))
            if picked is not None:
                spec = picked

        sleep_seconds = spec.get("sleep")
        if sleep_seconds:
            time.sleep(float(sleep_seconds))

        body: bytes = spec.get("raw") or spec.get("body", "").encode("utf-8")
        headers = dict(spec.get("headers", {}))
        status = int(spec.get("status", 200))

        padding = int(spec.get("declared_length_padding", 0))
        if padding:
            # Declare more than we send, then close mid-body -> IncompleteRead.
            self.send_response(status)
            self.send_header("Content-Type", spec.get("content_type", "text/plain"))
            self.send_header("Content-Length", str(len(body) + padding))
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True
            return

        self._respond(status, body, spec.get("content_type", "text/plain"), headers)

    def _respond(
        self,
        status: int,
        body: bytes,
        content_type: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


class FaultOriginServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def wait_for_server(port: int, timeout: float = 10.0) -> bool:
    import urllib.request

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.1)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--epoch-file", type=Path, required=True)
    parser.add_argument("--log-file", type=Path, default=None)
    args = parser.parse_args()

    global _LOG_PATH
    if args.log_file:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        _LOG_PATH = args.log_file
        FaultOriginHandler.access_log = args.log_file

    FaultOriginHandler.epoch_file = args.epoch_file
    args.epoch_file.parent.mkdir(parents=True, exist_ok=True)
    if not args.epoch_file.exists():
        args.epoch_file.write_text("1\n", encoding="utf-8")

    server = FaultOriginServer(("127.0.0.1", args.port), FaultOriginHandler)
    log_line(f"fault origin listening on {args.port} (pid {__import__('os').getpid()})")
    print(json.dumps({"listening": args.port, "epoch_file": str(args.epoch_file)}), flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
