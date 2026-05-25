#!/usr/bin/env python3
"""Rebuild HTML for all saved morning briefs (updates nav + archive)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes.brief.publish import publish_html
from hermes.config import load_config
from hermes.storage.json_store import load_morning_brief


def main() -> int:
    config = load_config()
    briefs_dir = config.briefs_dir
    if not briefs_dir.is_dir():
        print("No briefs directory", file=sys.stderr)
        return 1

    dates = sorted(
        p.stem.replace("morning_", "")
        for p in briefs_dir.glob("morning_*.json")
    )
    if not dates:
        print("No morning brief JSON files found")
        return 0

    for date in dates:
        record = load_morning_brief(config, date)
        if record is None:
            continue
        path = publish_html(config, record)
        print(path)

    print(f"Republished {len(dates)} brief(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
