#!/usr/bin/env python3
"""Rebuild HTML page from saved morning brief JSON."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes.brief.publish import publish_html
from hermes.config import load_config
from hermes.storage.json_store import load_morning_brief


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish HTML from morning brief JSON")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    config = load_config()
    record = load_morning_brief(config, args.date)
    if record is None:
        print(f"No morning brief for {args.date}", file=sys.stderr)
        return 1

    path = publish_html(config, record)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
