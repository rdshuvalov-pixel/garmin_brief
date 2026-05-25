"""Tests for HTTP trigger server."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from hermes.trigger.server import (
    build_brief_command,
    parse_trigger_body,
    read_status,
    spawn_brief_job,
    verify_bearer_auth,
    write_status,
    TriggerStatus,
)


def test_verify_bearer_auth():
    assert verify_bearer_auth("Bearer secret123", "secret123") is True
    assert verify_bearer_auth("Bearer wrong", "secret123") is False
    assert verify_bearer_auth(None, "secret123") is False
    assert verify_bearer_auth("Bearer x", "") is False


def test_parse_trigger_body_defaults():
    assert parse_trigger_body(b"") == {}
    assert parse_trigger_body(b'{"force": false, "attempt": 3}') == {
        "force": False,
        "attempt": 3,
    }


def test_parse_trigger_body_invalid():
    with pytest.raises(json.JSONDecodeError):
        parse_trigger_body(b"not-json")
    with pytest.raises(ValueError):
        parse_trigger_body(b"[]")


def test_build_brief_command(tmp_path: Path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").touch()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "run_morning_brief.py").touch()

    cmd = build_brief_command(tmp_path, force=True, attempt=7, date="2026-05-24")
    assert cmd[-2:] == ["--attempt", "7"]
    assert "--date" in cmd
    assert "--force" in cmd


def test_status_roundtrip(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    status = TriggerStatus(job_id="abc", started_at="2026-05-24T08:00:00Z", exit_code=0)
    write_status(tmp_path, status)
    loaded = read_status(tmp_path)
    assert loaded is not None
    assert loaded["job_id"] == "abc"
    assert loaded["exit_code"] == 0


def test_spawn_brief_job_starts_thread(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").touch()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "run_morning_brief.py").touch()

    with patch("hermes.trigger.server.run_brief_subprocess") as mock_run:
        job_id, cmd = spawn_brief_job(tmp_path, force=True, attempt=7)
        assert len(job_id) == 12
        assert any("run_morning_brief.py" in part for part in cmd)
        mock_run.assert_called_once()
