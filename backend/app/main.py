"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import admin, interview_ws, invites, sessions
from app.config import get_settings
from app.db import init_db

# Path to the built frontend (populated by `npm run build`). Optional.
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AI Interviewer", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(admin.router)
    app.include_router(invites.router)
    app.include_router(sessions.router)
    app.include_router(interview_ws.router)

    @app.get("/api/health")
    def health():
        from app.services.llm.factory import active_provider_name

        return {
            "status": "ok",
            "provider": active_provider_name(),
            "gemini": settings.has_gemini,
            "anthropic": settings.has_anthropic,
        }

    # In production, serve the built SPA with a catch-all fallback for client routes.
    if FRONTEND_DIST.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=FRONTEND_DIST / "assets"),
            name="assets",
        )

        @app.get("/{full_path:path}")
        def spa(full_path: str):
            candidate = FRONTEND_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
