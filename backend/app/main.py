import os
from contextlib import asynccontextmanager

import backend.app.models  # noqa: F401
from backend.app.api.v1.endpoints import router as api_v1_router
from backend.app.core.config import settings
from backend.app.db.session import Base, engine
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema exists on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="SlotBack appointment recovery API",
    lifespan=lifespan,
)

# CORS Middleware
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "slotback-api"}


# Include API v1 Router
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)


# Serve Static Frontend if built
dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
assets_dir = os.path.join(dist_dir, "assets")

if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(request: Request, full_path: str):
    index_path = os.path.join(dist_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "SlotBack API",
        "docs": "/docs",
        "detail": "Frontend dist build not found. Run 'npx pnpm build' inside frontend directory.",
    }
