"""Configuration loaded from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BRIEF_TYPE = "garmin_morning_recovery"
MORNING_BRIEF_TYPE = "morning_brief"
FINAL_ATTEMPT = 7


@dataclass(frozen=True)
class Config:
    garmin_email: str
    garmin_password: str
    garmin_tokens_path: Path
    data_dir: Path
    user_id: str
    timezone: ZoneInfo
    openrouter_api_key: str
    llm_model: str
    telegram_bot_token: str
    telegram_chat_id: str
    brief_public_base_url: str

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def briefs_dir(self) -> Path:
        return self.data_dir / "briefs"

    @property
    def web_dir(self) -> Path:
        return self.project_root / "web"

    @property
    def web_briefs_dir(self) -> Path:
        return self.web_dir / "briefs"

    @property
    def history_db_path(self) -> Path:
        return self.data_dir / "garmin_history.db"

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def brief_url_for(self, date: str) -> str:
        base = self.brief_public_base_url.rstrip("/")
        return f"{base}/briefs/{date}.html"


def load_config() -> Config:
    project_root = Path(__file__).resolve().parents[2]
    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    if not data_dir.is_absolute():
        data_dir = project_root / data_dir

    tokenstore = os.getenv("GARMINTOKENS", "~/.garminconnect")

    return Config(
        garmin_email=os.getenv("GARMIN_EMAIL", ""),
        garmin_password=os.getenv("GARMIN_PASSWORD", ""),
        garmin_tokens_path=Path(tokenstore).expanduser(),
        data_dir=data_dir,
        user_id=os.getenv("USER_ID", "main_user"),
        timezone=ZoneInfo(os.getenv("TIMEZONE", "Europe/Lisbon")),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "qwen/qwen3.6-35b-a3b"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        brief_public_base_url=os.getenv("BRIEF_PUBLIC_BASE_URL", "http://127.0.0.1:8765"),
    )
