#!/usr/bin/env bash
# Первичная установка на VPS: каталог + git clone + install.
# Запуск на сервере от root:
#   curl -fsSL .../bootstrap-vps.sh | bash
# или после ssh:
#   bash deploy/bootstrap-vps.sh

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/garmin-brief}"
REPO_URL="${REPO_URL:-https://github.com/rdshuvalov-pixel/garmin_brief.git}"
BRANCH="${BRANCH:-main}"
BRIEF_HOST="${BRIEF_HOST:-vercel}"

echo "==> Install dir: $INSTALL_DIR"
echo "==> Repo: $REPO_URL ($BRANCH)"

if ! command -v git >/dev/null 2>&1; then
  echo "==> Installing git"
  apt-get update -qq
  apt-get install -y git
fi

if [[ ! -d "$INSTALL_DIR" ]]; then
  echo "==> Creating $INSTALL_DIR"
  mkdir -p "$INSTALL_DIR"
fi

if [[ ! -d "$INSTALL_DIR/.git" ]]; then
  if [[ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]]; then
    echo "ERROR: $INSTALL_DIR exists and is not empty — remove or pick another INSTALL_DIR" >&2
    exit 1
  fi
  echo "==> git clone"
  git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
else
  echo "==> Already cloned — git pull"
  git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
fi

cd "$INSTALL_DIR"
BRIEF_HOST="$BRIEF_HOST" bash deploy/install-vps.sh

echo ""
echo "Next:"
echo "  1. nano $INSTALL_DIR/.env"
echo "  2. $INSTALL_DIR/.venv/bin/python scripts/login.py"
echo "  3. crontab -e  # paste deploy/morning-brief.cron.vps"
echo "  4. git pull in $INSTALL_DIR for future updates"
