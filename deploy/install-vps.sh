#!/usr/bin/env bash
# Install Hermes Garmin morning brief on Ubuntu/Debian VPS.
# Run as root from project root: bash deploy/install-vps.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_USER="${APP_USER:-root}"
VENV="$PROJECT_ROOT/.venv"
PY="$VENV/bin/python"
PORT="${BRIEF_PORT:-8765}"

echo "==> Project: $PROJECT_ROOT"

if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
  echo "WARN: .env not found. Copy from Mac and set BRIEF_PUBLIC_BASE_URL to VPS public URL."
  if [[ -f "$PROJECT_ROOT/.env.example" ]]; then
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "      Created .env from .env.example — edit before first run."
  fi
fi

echo "==> Python venv"
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi
"$PY" -m pip install -U pip wheel
"$PY" -m pip install -e "$PROJECT_ROOT"

echo "==> Directories"
mkdir -p "$PROJECT_ROOT/data/raw" "$PROJECT_ROOT/data/briefs" "$PROJECT_ROOT/web/briefs"

echo "==> systemd: hermes-brief-web"
sed "s|@PROJECT_ROOT@|$PROJECT_ROOT|g; s|@PORT@|$PORT|g" \
  "$PROJECT_ROOT/deploy/hermes-brief-web.service" \
  > /etc/systemd/system/hermes-brief-web.service

systemctl daemon-reload
systemctl enable hermes-brief-web
systemctl restart hermes-brief-web
systemctl --no-pager status hermes-brief-web || true

echo "==> Cron hint (install manually: crontab -e)"
echo "    See: $PROJECT_ROOT/deploy/morning-brief.cron.vps"

echo ""
echo "Done."
echo "  1. Edit $PROJECT_ROOT/.env — set BRIEF_PUBLIC_BASE_URL=http://$(curl -s ifconfig.me 2>/dev/null || echo YOUR_VPS_IP):$PORT"
echo "  2. Garmin login: cd $PROJECT_ROOT && $PY scripts/login.py"
echo "  3. Test: curl -I http://127.0.0.1:$PORT/briefs/"
echo "  4. Open firewall if needed: ufw allow $PORT/tcp"
