"""Configuration loaded from environment and config.yaml defaults."""

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


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_yaml_defaults() -> dict:
    """Load non-secret defaults from config.yaml (env overrides)."""
    path = _project_root() / "config.yaml"
    if not path.is_file():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _cfg_get(yaml_cfg: dict, *keys: str, default: str = "") -> str:
    node: object = yaml_cfg
    for key in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(key, default)
    return str(node) if node is not None else default


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


def brief_public_base_url_warnings(url: str) -> list[str]:
    """Return human-readable warnings for a misconfigured public brief URL."""
    warnings: list[str] = []
    normalized = url.rstrip("/")

    if "127.0.0.1" in normalized or "localhost" in normalized:
        warnings.append(
            f"BRIEF_PUBLIC_BASE_URL={url} — ссылка в Telegram не откроется с телефона. "
            "Укажи URL Vercel (https://….vercel.app) или публичный IP VPS."
        )

    if ".vercel.ap/" in normalized or normalized.endswith(".vercel.ap"):
        warnings.append(
            f"BRIEF_PUBLIC_BASE_URL={url} — опечатка в домене (.vercel.ap вместо .vercel.app). "
            "Telegram-ссылки не откроются."
        )

    if "vercel.app" in normalized and not normalized.endswith(".vercel.app"):
        if ".vercel.app/" not in normalized:
            warnings.append(
                f"BRIEF_PUBLIC_BASE_URL={url} — проверь домен Vercel, ожидается …vercel.app"
            )

    return warnings


def load_config() -> Config:
    project_root = _project_root()
    yaml_cfg = _load_yaml_defaults()
    data_dir = Path(os.getenv("DATA_DIR", _cfg_get(yaml_cfg, "data_dir", default="./data")))
    if not data_dir.is_absolute():
        data_dir = project_root / data_dir

    tokenstore = os.getenv("GARMINTOKENS", "~/.garminconnect")
    brief_cfg = yaml_cfg.get("brief") if isinstance(yaml_cfg.get("brief"), dict) else {}

    return Config(
        garmin_email=os.getenv("GARMIN_EMAIL", ""),
        garmin_password=os.getenv("GARMIN_PASSWORD", ""),
        garmin_tokens_path=Path(tokenstore).expanduser(),
        data_dir=data_dir,
        user_id=os.getenv("USER_ID", _cfg_get(yaml_cfg, "user_id", default="main_user")),
        timezone=ZoneInfo(
            os.getenv("TIMEZONE", _cfg_get(yaml_cfg, "timezone", default="Europe/Lisbon"))
        ),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        llm_model=os.getenv(
            "LLM_MODEL", _cfg_get(yaml_cfg, "llm_model", default="qwen/qwen3.6-35b-a3b")
        ),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        brief_public_base_url=os.getenv(
            "BRIEF_PUBLIC_BASE_URL",
            str(brief_cfg.get("public_base_url", "http://127.0.0.1:8765")),
        ),
    )
