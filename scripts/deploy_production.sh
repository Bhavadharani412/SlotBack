#!/usr/bin/env bash
# ==============================================================================
# SlotBack — Production Deployment and Verification Script (Linux/Cloud)
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo "🚀 SlotBack Production Deployment & Release Sequence"
echo "=========================================================="

# 1. Check for .env file
if [ ! -f ".env" ]; then
  echo "⚠️  No .env file found. Copying .env.example to .env..."
  cp .env.example .env
  echo "👉 Please edit .env with your production credentials before continuing."
fi

# 2. Install backend dependencies
echo "📦 Installing backend requirements..."
pip install --no-cache-dir -r requirements.txt

# 3. Build frontend bundle
echo "🎨 Building frontend production bundle..."
if command -v pnpm &> /dev/null; then
  pnpm --prefix frontend install --frozen-lockfile
  pnpm --prefix frontend build
elif command -v npm &> /dev/null; then
  npm --prefix frontend install
  npm --prefix frontend run build
else
  echo "⚠️  Neither pnpm nor npm found. Skipping frontend build step."
fi

# 4. Run database migrations
echo "🗄️  Applying Alembic database schema migrations..."
alembic upgrade head

# 5. Output ready status
echo "=========================================================="
echo "✅ SlotBack is production ready!"
echo "To run the production server:"
echo "  uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips='*'"
echo ""
echo "Or with Docker Compose:"
echo "  docker compose up -d --build"
echo "=========================================================="
