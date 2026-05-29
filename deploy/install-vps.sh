#!/usr/bin/env bash
# Install garmin-brief on Ubuntu/Debian VPS.
# BRIEF_HOST=vercel  — генерация на VPS, HTML на Vercel (без systemd web)
# BRIEF_HOST=local   — systemd serve_brief.py на порту 8765 (default)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$PROJECT_ROOT/.venv"
PY="$VENV/bin/python"
PORT="${BRIEF_PORT:-8765}"

if [[ -z "${BRIEF_HOST:-}" ]]; then
  if [[ -f "$PROJECT_ROOT/.env" ]] && grep -qE '^VERCEL_TOKEN=.+' "$PROJECT_ROOT/.env" 2>/dev/null; then
    BRIEF_HOST=vercel
  else
    BRIEF_HOST=local
  fi
fi

echo "==> Project: $PROJECT_ROOT"
echo "==> BRIEF_HOST: $BRIEF_HOST"

if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
  echo "WARN: .env not found."
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

TRIGGER_PORT="${TRIGGER_PORT:-8787}"
if [[ -f "$PROJECT_ROOT/.env" ]] && grep -qE '^TRIGGER_SECRET=.+' "$PROJECT_ROOT/.env" 2>/dev/null; then
  echo "==> systemd: hermes-brief-trigger (port $TRIGGER_PORT)"
  sed "s|@PROJECT_ROOT@|$PROJECT_ROOT|g; s|@TRIGGER_PORT@|$TRIGGER_PORT|g" \
    "$PROJECT_ROOT/deploy/hermes-brief-trigger.service" \
    > /etc/systemd/system/hermes-brief-trigger.service
  systemctl daemon-reload
  systemctl enable hermes-brief-trigger
  systemctl restart hermes-brief-trigger
  systemctl --no-pager status hermes-brief-trigger || true
else
  echo "==> Trigger server skipped (set TRIGGER_SECRET in .env to enable)"
fi

if [[ "$BRIEF_HOST" == "vercel" ]]; then
  echo "==> Vercel mode — skipping systemd web server"
  echo "    HTML: docs/deploy-vercel.md"
  if ! command -v npx >/dev/null 2>&1; then
    echo "WARN: npx not found — install Node.js for auto Vercel deploy"
  fi
else
  echo "==> systemd: hermes-brief-web"
  sed "s|@PROJECT_ROOT@|$PROJECT_ROOT|g; s|@PORT@|$PORT|g" \
    "$PROJECT_ROOT/deploy/hermes-brief-web.service" \
    > /etc/systemd/system/hermes-brief-web.service

  systemctl daemon-reload
  systemctl enable hermes-brief-web
  systemctl restart hermes-brief-web
  systemctl --no-pager status hermes-brief-web || true
fi

echo ""
echo "Done."
if [[ "$BRIEF_HOST" == "vercel" ]]; then
  echo "  1. Edit .env — BRIEF_PUBLIC_BASE_URL=https://YOUR.vercel.app"
  echo "  2. Set VERCEL_TOKEN, VERCEL_ORG_ID, VERCEL_PROJECT_ID"
  echo "  3. Garmin login: cd $PROJECT_ROOT && $PY scripts/login.py"
  echo "  4. Test deploy: bash $PROJECT_ROOT/scripts/deploy_vercel.sh"
  echo "  5. Test trigger: curl -H \"Authorization: Bearer \$TRIGGER_SECRET\" http://127.0.0.1:$TRIGGER_PORT/health"
else
  echo "  1. Edit .env — BRIEF_PUBLIC_BASE_URL=http://$(curl -s ifconfig.me 2>/dev/null || echo VPS_IP):$PORT"
  echo "  2. Garmin login: cd $PROJECT_ROOT && $PY scripts/login.py"
  echo "  3. Test: curl -I http://127.0.0.1:$PORT/briefs/"
fi
