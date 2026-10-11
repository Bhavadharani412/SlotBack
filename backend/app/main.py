import os
from contextlib import asynccontextmanager

import backend.app.models  # noqa: F401
from backend.app.api.v1.endpoints import router as api_v1_router
from backend.app.core.auth import ensure_initial_admin
from backend.app.core.config import settings
from backend.app.db.session import Base, SessionLocal, engine
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce production security invariants
    settings.validate_production_configuration()

    # Ensure database schema exists
    Base.metadata.create_all(bind=engine)

    # Seed initial staff administrator if no users exist
    with SessionLocal() as session:
        ensure_initial_admin(session)

    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="SlotBack appointment recovery API",
    lifespan=lifespan,
    debug=settings.debug,
)

# CORS Middleware with strict origin parsing
configured_origins = [
    origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()
]
# If configured with invalid wildcard or empty, fallback safely to default local origin
safe_origins = (
    [o for o in configured_origins if o != "*"]
    if configured_origins
    else ["http://localhost:5173"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=safe_origins or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Liveness check (process is running)
@app.get("/health", tags=["health"])
@app.get("/health/live", tags=["health"])
def liveness_check() -> dict[str, str]:
    return {"status": "ok", "service": "slotback-api"}


# Readiness check (verifies database connectivity)
@app.get("/health/ready", tags=["health"])
def readiness_check() -> JSONResponse:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ready", "database": "connected"},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "database": f"disconnected: {str(exc)}"},
        )


# Include API v1 Router
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)


# Serve Static Frontend if built
dist_dir = os.environ.get(
    "FRONTEND_DIST_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")),
)
assets_dir = os.path.join(dist_dir, "assets")

if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(request: Request, full_path: str):
    if full_path:
        requested_file = os.path.join(dist_dir, full_path)
        if os.path.isfile(requested_file):
            return FileResponse(requested_file)
    index_path = os.path.join(dist_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "SlotBack API",
        "docs": "/docs",
        "detail": "Frontend dist build not found. Run 'pnpm --prefix frontend build' to compile the React SPA.",
    }
