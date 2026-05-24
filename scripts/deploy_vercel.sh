#!/usr/bin/env bash
# Deploy web/ to Vercel (run from VPS after brief generation or manually).
# Requires: Node.js (npx), VERCEL_TOKEN, VERCEL_ORG_ID, VERCEL_PROJECT_ID in .env

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

if [[ -z "${VERCEL_TOKEN:-}" ]]; then
  echo "ERROR: VERCEL_TOKEN not set in .env" >&2
  exit 1
fi
if [[ -z "${VERCEL_ORG_ID:-}" || -z "${VERCEL_PROJECT_ID:-}" ]]; then
  echo "ERROR: VERCEL_ORG_ID and VERCEL_PROJECT_ID required (see docs/deploy-vercel.md)" >&2
  exit 1
fi

export VERCEL_ORG_ID VERCEL_PROJECT_ID

echo "==> Deploying $ROOT/web to Vercel (prod)"
npx --yes vercel@latest deploy web --prod --yes --token "$VERCEL_TOKEN"
echo "==> Done. Check BRIEF_PUBLIC_BASE_URL matches your Vercel URL."
