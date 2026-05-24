"""SQLite storage for metric history (rolling baselines)."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from hermes.models.metrics import RawMetrics

logger = logging.getLogger(__name__)


@contextmanager
def get_conn(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_conn(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                date TEXT PRIMARY KEY,
                hrv_ms REAL,
                resting_hr_bpm REAL,
                respiratory_rate REAL,
                temp_deviation_c REAL,
                spo2_avg_pct REAL,
                spo2_min_pct REAL,
                total_sleep_seconds INTEGER,
                deep_sleep_seconds INTEGER,
                rem_sleep_seconds INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
    logger.debug("Metrics DB initialised at %s", db_path)


def save_metrics(metrics: RawMetrics, db_path: Path) -> None:
    init_db(db_path)
    with get_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO metrics (
                date, hrv_ms, resting_hr_bpm, respiratory_rate,
                temp_deviation_c, spo2_avg_pct, spo2_min_pct,
                total_sleep_seconds, deep_sleep_seconds, rem_sleep_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                hrv_ms = excluded.hrv_ms,
                resting_hr_bpm = excluded.resting_hr_bpm,
                respiratory_rate = excluded.respiratory_rate,
                temp_deviation_c = excluded.temp_deviation_c,
                spo2_avg_pct = excluded.spo2_avg_pct,
                spo2_min_pct = excluded.spo2_min_pct,
                total_sleep_seconds = excluded.total_sleep_seconds,
                deep_sleep_seconds = excluded.deep_sleep_seconds,
                rem_sleep_seconds = excluded.rem_sleep_seconds,
                created_at = datetime('now')
            """,
            (
                metrics.date.isoformat(),
                metrics.hrv_ms,
                metrics.resting_hr_bpm,
                metrics.respiratory_rate,
                metrics.temp_deviation_c,
                metrics.spo2_avg_pct,
                metrics.spo2_min_pct,
                metrics.total_sleep_seconds,
                metrics.deep_sleep_seconds,
                metrics.rem_sleep_seconds,
            ),
        )


def load_history(
    db_path: Path,
    days: int = 30,
    end_date: Optional[date] = None,
) -> list[RawMetrics]:
    if not db_path.exists():
        return []
    if end_date is None:
        end_date = date.today()

    start_date = end_date - timedelta(days=days)
    cutoff = (end_date - timedelta(days=1)).isoformat()
    start_str = start_date.isoformat()

    with get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM metrics
            WHERE date >= ? AND date <= ?
            ORDER BY date ASC
            """,
            (start_str, cutoff),
        ).fetchall()

    result: list[RawMetrics] = []
    for row in rows:
        m = RawMetrics(date=date.fromisoformat(row["date"]))
        m.hrv_ms = row["hrv_ms"]
        m.resting_hr_bpm = row["resting_hr_bpm"]
        m.respiratory_rate = row["respiratory_rate"]
        m.temp_deviation_c = row["temp_deviation_c"]
        m.spo2_avg_pct = row["spo2_avg_pct"]
        m.spo2_min_pct = row["spo2_min_pct"]
        m.total_sleep_seconds = row["total_sleep_seconds"]
        m.deep_sleep_seconds = row["deep_sleep_seconds"]
        m.rem_sleep_seconds = row["rem_sleep_seconds"]
        result.append(m)
    return result
