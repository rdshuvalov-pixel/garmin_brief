"""JSON file storage for raw data and briefs."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from hermes.config import BRIEF_TYPE, MORNING_BRIEF_TYPE, Config

logger = logging.getLogger(__name__)


def ensure_data_dirs(config: Config) -> None:
    config.raw_dir.mkdir(parents=True, exist_ok=True)
    config.briefs_dir.mkdir(parents=True, exist_ok=True)
    config.web_briefs_dir.mkdir(parents=True, exist_ok=True)


def brief_path(config: Config, date: str) -> Path:
    return config.briefs_dir / f"garmin_morning_{date}.json"


def morning_brief_path(config: Config, date: str) -> Path:
    return config.briefs_dir / f"morning_{date}.json"


def raw_path(config: Config, date: str) -> Path:
    return config.raw_dir / f"garmin_{date}.json"


def exists_brief(config: Config, user_id: str, date: str, brief_type: str = BRIEF_TYPE) -> bool:
    for path_fn in (morning_brief_path, brief_path):
        path = path_fn(config, date)
        if not path.exists():
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if (
                record.get("user_id", user_id) == user_id
                and record.get("date") == date
                and record.get("status") == "created"
                and record.get("type") in (brief_type, MORNING_BRIEF_TYPE, BRIEF_TYPE)
            ):
                return True
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read brief file %s: %s", path, exc)
    return False


def save_raw(config: Config, date: str, payload: dict[str, Any]) -> Path:
    ensure_data_dirs(config)
    path = raw_path(config, date)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved raw data to %s", path)
    return path


def save_brief(
    config: Config,
    *,
    user_id: str,
    date: str,
    metrics: dict[str, Any],
    brief_text: str,
    brief_type: str = BRIEF_TYPE,
    timezone: ZoneInfo | None = None,
) -> Path:
    ensure_data_dirs(config)
    tz = timezone or ZoneInfo("UTC")
    now = datetime.now(tz).isoformat()

    record = {
        "date": date,
        "type": brief_type,
        "user_id": user_id,
        "source": "garmin_connect",
        "metrics": metrics,
        "brief_text": brief_text,
        "created_at": now,
        "status": "created",
    }

    path = brief_path(config, date)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved brief to %s", path)
    return path


def save_morning_brief(config: Config, record: dict[str, Any]) -> Path:
    ensure_data_dirs(config)
    date = record["date"]
    path = morning_brief_path(config, date)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    _update_briefs_index(config, date)
    logger.info("Saved morning brief to %s", path)
    return path


def _update_briefs_index(config: Config, date: str) -> None:
    index_path = config.briefs_dir / "index.json"
    dates: list[str] = []
    if index_path.exists():
        try:
            dates = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            dates = []
    if date not in dates:
        dates.append(date)
    dates.sort(reverse=True)
    index_path.write_text(json.dumps(dates, ensure_ascii=False, indent=2), encoding="utf-8")


def load_morning_brief(config: Config, date: str) -> dict[str, Any] | None:
    path = morning_brief_path(config, date)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_brief(config: Config, date: str) -> dict[str, Any] | None:
    return load_morning_brief(config, date) or (
        json.loads(brief_path(config, date).read_text(encoding="utf-8"))
        if brief_path(config, date).exists()
        else None
    )
