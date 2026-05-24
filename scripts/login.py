#!/usr/bin/env python3
"""First-time Garmin Connect login with MFA."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes.config import load_config
from hermes.garmin.auth import login_interactive


def main() -> int:
    return login_interactive(load_config())


if __name__ == "__main__":
    sys.exit(main())
