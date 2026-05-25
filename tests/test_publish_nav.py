"""Tests for brief archive navigation."""

from pathlib import Path

from hermes.brief.publish import list_brief_dates


def test_list_brief_dates_newest_first(tmp_path: Path):
    briefs = tmp_path / "briefs"
    briefs.mkdir()
    (briefs / "2026-05-22.html").write_text("x")
    (briefs / "2026-05-24.html").write_text("x")
    (briefs / "index.html").write_text("x")

    assert list_brief_dates(briefs) == ["2026-05-24", "2026-05-22"]
