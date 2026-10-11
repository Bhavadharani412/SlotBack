# ==============================================================================
# SlotBack — Production Deployment and Verification Script (Windows PowerShell)
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🚀 SlotBack Production Deployment & Release Sequence" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  No .env file found. Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "👉 Please edit .env with your production credentials before continuing." -ForegroundColor Yellow
}

# 2. Install backend dependencies
Write-Host "📦 Installing backend requirements..." -ForegroundColor Green
& .\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt

# 3. Build frontend bundle
Write-Host "🎨 Building frontend production bundle..." -ForegroundColor Green
if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    pnpm --prefix frontend install --frozen-lockfile
    pnpm --prefix frontend build
} elseif (Get-Command npm -ErrorAction SilentlyContinue) {
    npm --prefix frontend install
    npm --prefix frontend run build
} else {
    Write-Host "⚠️  Neither pnpm nor npm found in PATH. Skipping frontend build." -ForegroundColor Yellow
}

# 4. Run database migrations
Write-Host "🗄️  Applying Alembic database schema migrations..." -ForegroundColor Green
& .\.venv\Scripts\alembic.exe upgrade head

# 5. Output ready status
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "✅ SlotBack is production ready!" -ForegroundColor Green
Write-Host "To run the production server:" -ForegroundColor White
Write-Host "  uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 2" -ForegroundColor Yellow
Write-Host ""
Write-Host "Or with Docker Compose:" -ForegroundColor White
Write-Host "  docker compose up -d --build" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
