"""FastAPI application for DevKit for OpenCode."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import analyze, audit, config, history, migrate, recommendations, score
from devkit import __version__

app = FastAPI(
    title="DevKit for OpenCode",
    description="Analyze and optimize OpenCode configurations",
    version=__version__,
)

# CORS for dev mode (Vite dev server on :5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(analyze.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(score.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(migrate.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")


@app.get("/api/health", tags=["health"])
async def health_check():
    """API health check."""
    return {
        "status": "ok",
        "version": __version__,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }


# Serve static files in production (built React app)
static_dir = Path(__file__).parent.parent / "web" / "dist"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
