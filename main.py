"""
main.py

Narada — FastAPI entry point.

In production, serves the React frontend as static files from frontend/dist/.
In development, the React dev server (port 5173) proxies API calls to this server.

Run locally:
    uvicorn main:app --reload

Run production:
    ENVIRONMENT=production FORCE_HTTPS=true uvicorn main:app --host 0.0.0.0 --port 8000
"""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router
from config import configure_logging, get_settings

settings = get_settings()
configure_logging(settings)

logger = logging.getLogger(__name__)

ENVIRONMENT  = os.getenv("ENVIRONMENT", "development")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")
FRONTEND_DIR = Path(__file__).parent / "frontend" / "dist"

# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #

app = FastAPI(
    title="Narada",
    description="Agentic search and structured entity extraction.",
    version="0.1.0",
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url=None,
)

# --------------------------------------------------------------------------- #
# CORS
# --------------------------------------------------------------------------- #

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)

# --------------------------------------------------------------------------- #
# Security headers
# --------------------------------------------------------------------------- #

@app.middleware("http")
async def security_headers(request: Request, call_next):
    if os.getenv("FORCE_HTTPS") == "true":
        proto = request.headers.get("x-forwarded-proto")
        if proto == "http":
            return RedirectResponse(
                str(request.url).replace("http://", "https://", 1),
                status_code=301,
            )

    response = await call_next(request)

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )

    # Prevent browsers from sniffing content types
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Referrer policy -- don't leak URL to third parties
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # HSTS -- tell browsers to always use HTTPS (only set in production)
    if os.getenv("FORCE_HTTPS") == "true":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Remove server header to avoid fingerprinting
    if "server" in response.headers:
        del response.headers["server"]

    return response

# --------------------------------------------------------------------------- #
# API routes
# --------------------------------------------------------------------------- #

app.include_router(router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "environment": ENVIRONMENT,
        "llm_provider": settings.llm_provider,
        "search_provider": settings.search_provider,
    }

# --------------------------------------------------------------------------- #
# Serve React frontend (production only)
# --------------------------------------------------------------------------- #

if FRONTEND_DIR.exists():
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """
        Catch-all route that serves the React app for any non-API path.
        React Router handles client-side routing from there.
        """
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")

    logger.info(f"[Narada] Serving frontend from {FRONTEND_DIR}")
else:
    logger.info("[Narada] Frontend not built — API-only mode. Run: cd frontend && npm run build")