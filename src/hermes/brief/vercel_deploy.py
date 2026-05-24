"""Deploy generated HTML to Vercel (optional, after publish_html)."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def deploy_vercel_if_configured(project_root: Path) -> bool:
    """
    Upload web/ to Vercel when VERCEL_TOKEN + project ids are set.
    Returns True if deploy was attempted and succeeded.
    """
    token = os.getenv("VERCEL_TOKEN", "").strip()
    org_id = os.getenv("VERCEL_ORG_ID", "").strip()
    project_id = os.getenv("VERCEL_PROJECT_ID", "").strip()

    if not token:
        return False
    if not org_id or not project_id:
        logger.warning(
            "VERCEL_TOKEN задан, но нет VERCEL_ORG_ID / VERCEL_PROJECT_ID — деплoy пропущен"
        )
        return False

    web_dir = project_root / "web"
    if not web_dir.is_dir():
        logger.error("Каталог web/ не найден: %s", web_dir)
        return False

    env = {
        **os.environ,
        "VERCEL_ORG_ID": org_id,
        "VERCEL_PROJECT_ID": project_id,
    }
    cmd = [
        "npx",
        "--yes",
        "vercel@latest",
        "deploy",
        str(web_dir),
        "--prod",
        "--yes",
        "--token",
        token,
    ]
    logger.info("Vercel deploy: %s", " ".join(cmd[:-1] + ["--token", "***"]))

    try:
        subprocess.run(cmd, cwd=project_root, env=env, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        logger.error("Vercel deploy failed: %s", (exc.stderr or exc.stdout or exc).strip())
        return False
    except FileNotFoundError:
        logger.error("npx не найден — установите Node.js на VPS для Vercel deploy")
        return False

    logger.info("Vercel deploy OK")
    return True
