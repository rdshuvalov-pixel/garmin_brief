#!/usr/bin/env python3
"""Entrypoint for morning recovery brief job."""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes.config import FINAL_ATTEMPT, load_config
from hermes.delivery.channels import get_delivery_channel
from hermes.jobs.morning_brief import run_morning_brief


def _parse_date(value: str) -> str:
    datetime.strptime(value, "%Y-%m-%d")
    return value


def main() -> int:
    config = load_config()
    yesterday = (datetime.now(config.timezone).date() - timedelta(days=1)).isoformat()

    parser = argparse.ArgumentParser(description="Generate Garmin morning recovery brief")
    parser.add_argument(
        "--date",
        type=_parse_date,
        help=f"Target date YYYY-MM-DD (default: today, e.g. --date {yesterday} for test)",
    )
    parser.add_argument(
        "--attempt",
        type=int,
        default=1,
        choices=range(1, FINAL_ATTEMPT + 1),
        metavar=f"1-{FINAL_ATTEMPT}",
        help="Poll attempt (7 = final, create Grey if HRV missing)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate brief even if it already exists for this date",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    return run_morning_brief(
        config,
        target_date=args.date,
        attempt=args.attempt,
        force=args.force,
        delivery=get_delivery_channel(),
    )


if __name__ == "__main__":
    sys.exit(main())
