"""HTTP trigger for remote brief runs (Hermes Cloud → VPS)."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_STATUS_FILE = "trigger_status.json"


@dataclass
class TriggerStatus:
    job_id: str
    started_at: str
    finished_at: str | None = None
    exit_code: int | None = None
    command: list[str] | None = None
    error: str | None = None


def verify_bearer_auth(header: str | None, secret: str) -> bool:
    if not secret:
        return False
    if not header or not header.startswith("Bearer "):
        return False
    token = header[7:].strip()
    return token == secret


def parse_trigger_body(raw: bytes) -> dict[str, Any]:
    if not raw.strip():
        return {}
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")
    return data


def build_brief_command(
    project_root: Path,
    *,
    force: bool = True,
    attempt: int = 7,
    date: str | None = None,
) -> list[str]:
    py = project_root / ".venv" / "bin" / "python"
    script = project_root / "scripts" / "run_morning_brief.py"
    cmd = [str(py), str(script)]
    if date:
        cmd.extend(["--date", date])
    if force:
        cmd.append("--force")
    cmd.extend(["--attempt", str(attempt)])
    return cmd


def _status_path(project_root: Path) -> Path:
    data_dir = os.getenv("DATA_DIR", "./data")
    base = Path(data_dir)
    if not base.is_absolute():
        base = project_root / base
    return base / _STATUS_FILE


def read_status(project_root: Path) -> dict[str, Any] | None:
    path = _status_path(project_root)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_status(project_root: Path, status: TriggerStatus) -> None:
    path = _status_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(status), ensure_ascii=False, indent=2), encoding="utf-8")


def _append_trigger_log(project_root: Path, line: str) -> None:
    data_dir = _status_path(project_root).parent
    log_path = data_dir / "trigger.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def run_brief_subprocess(project_root: Path, cmd: list[str], job_id: str) -> None:
    started = datetime.now(timezone.utc).isoformat()
    status = TriggerStatus(job_id=job_id, started_at=started, command=cmd)
    write_status(project_root, status)
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        status.exit_code = result.returncode
        if result.returncode != 0:
            status.error = (result.stderr or result.stdout or "unknown error")[:500]
    except OSError as exc:
        status.exit_code = 1
        status.error = str(exc)
    status.finished_at = datetime.now(timezone.utc).isoformat()
    write_status(project_root, status)


def spawn_brief_job(
    project_root: Path,
    *,
    force: bool = True,
    attempt: int = 7,
    date: str | None = None,
) -> tuple[str, list[str]]:
    job_id = uuid.uuid4().hex[:12]
    cmd = build_brief_command(project_root, force=force, attempt=attempt, date=date)
    thread = threading.Thread(
        target=run_brief_subprocess,
        args=(project_root, cmd, job_id),
        daemon=True,
    )
    thread.start()
    return job_id, cmd


class TriggerHTTPHandler(BaseHTTPRequestHandler):
    project_root: Path
    secret: str

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s - %s", self.address_string(), format % args)

    def _json_response(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _unauthorized(self) -> None:
        self._json_response(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})

    def _check_auth(self) -> bool:
        if verify_bearer_auth(self.headers.get("Authorization"), self.secret):
            return True
        self._unauthorized()
        return False

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._json_response(HTTPStatus.OK, {"ok": True})
            return
        if path == "/status":
            if not self._check_auth():
                return
            self._json_response(HTTPStatus.OK, {"status": read_status(self.project_root)})
            return
        self._json_response(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/trigger":
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if not self._check_auth():
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            body = parse_trigger_body(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        force = bool(body.get("force", True))
        attempt = int(body.get("attempt", 7))
        date = body.get("date")
        if date is not None and not isinstance(date, str):
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "date must be a string"})
            return

        job_id, cmd = spawn_brief_job(
            self.project_root,
            force=force,
            attempt=attempt,
            date=date,
        )
        _append_trigger_log(
            self.project_root,
            f"{datetime.now(timezone.utc).isoformat()} POST /trigger from {self.client_address[0]} job={job_id}",
        )
        self._json_response(
            HTTPStatus.ACCEPTED,
            {"accepted": True, "job_id": job_id, "command": cmd},
        )


def make_handler(project_root: Path, secret: str) -> type[TriggerHTTPHandler]:
    class Handler(TriggerHTTPHandler):
        pass

    Handler.project_root = project_root
    Handler.secret = secret
    return Handler


def serve(project_root: Path, host: str, port: int, secret: str) -> None:
    handler = make_handler(project_root, secret)
    server = ThreadingHTTPServer((host, port), handler)
    logger.info("Trigger server listening on http://%s:%s", host, port)
    server.serve_forever()
