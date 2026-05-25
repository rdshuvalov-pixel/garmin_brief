#!/usr/bin/env python3
"""HTTP server: remote trigger for morning brief (Hermes Cloud → VPS)."""

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from hermes.trigger.server import serve  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Garmin brief HTTP trigger")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.getenv("TRIGGER_PORT", "8787")))
    args = parser.parse_args()

    secret = os.getenv("TRIGGER_SECRET", "").strip()
    if not secret:
        print("ERROR: TRIGGER_SECRET not set in .env", file=sys.stderr)
        return 1

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    serve(ROOT, args.host, args.port, secret)
    return 0


if __name__ == "__main__":
    sys.exit(main())
