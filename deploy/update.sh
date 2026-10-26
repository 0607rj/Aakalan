#!/usr/bin/env bash
# Install or update Aakalan on the Ubuntu server (docs/DEPLOY.md): pull the code, install the
# backend, migrate, load the seed data, build the website, restart the services.
# Run from anywhere as the user that owns the checkout: bash deploy/update.sh
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")/.."

git pull --ff-only
api_url=$(grep -E '^NEXT_PUBLIC_API_URL=' .env | cut -d= -f2-)
mkdir -p data

cd backend
uv sync --frozen --no-dev
uv run --no-sync alembic upgrade head
uv run --no-sync python -m app.cli seed
cd ../frontend
npm ci
NEXT_PUBLIC_API_URL="$api_url" NEXT_TELEMETRY_DISABLED=1 npm run build
cp -r .next/static .next/standalone/.next/
cp -r public .next/standalone/
cd ..

sudo systemctl restart aakalan-api aakalan-worker aakalan-web
echo "Aakalan updated."
