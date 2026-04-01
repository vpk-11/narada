"""
main.py

Narada — FastAPI entry point.

Security hardening:
- CORS locked to ALLOWED_ORIGIN env var in production
- CSP headers block inline scripts, restrict JS execution origins
- HTTPS redirect enforced when FORCE_HTTPS=true
- Request bodies are never logged
- uvicorn access logs exclude headers (where keys live)

Run locally:
    uvicorn main:app --reload

Run production:
    FORCE_HTTPS=true ALLOWED_ORIGIN=https://yourdomain.com uvicorn main:app
"""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse

from api.routes import router
from config import configure_logging, get_settings

settings = get_settings()
configure_logging(settings)

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #

app = FastAPI(
    title="Narada",
    description="Agentic search and structured entity extraction.",
    version="0.1.0",
    # Disable detailed error responses in production to avoid leaking internals
    docs_url="/docs" if os.getenv("ENVIRONMENT", "development") != "production" else None,
    redoc_url=None,
)

# --------------------------------------------------------------------------- #
# CORS — locked in production, open in development
# --------------------------------------------------------------------------- #

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")

if ENVIRONMENT == "production" and ALLOWED_ORIGIN == "*":
    logger.warning(
        "ALLOWED_ORIGIN is '*' in production. "
        "Set ALLOWED_ORIGIN=https://yourdomain.com to lock CORS."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # must allow * so custom x-api-key headers pass through
    allow_credentials=False,  # no cookies used
)

# --------------------------------------------------------------------------- #
# Security headers middleware
# --------------------------------------------------------------------------- #

@app.middleware("http")
async def security_headers(request: Request, call_next):
    """
    Add security headers to every response.

    CSP prevents XSS from stealing sessionStorage contents.
    HSTS enforces HTTPS for a year once set.
    """
    # HTTPS redirect
    if os.getenv("FORCE_HTTPS") == "true":
        if request.headers.get("x-forwarded-proto") == "http":
            https_url = str(request.url).replace("http://", "https://", 1)
            return RedirectResponse(https_url, status_code=301)

    response = await call_next(request)

    # CSP: only load scripts from self and trusted CDNs
    # Blocks inline scripts -- if an attacker injects <script>, it won't run
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://fonts.googleapis.com; "
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
# Routes
# --------------------------------------------------------------------------- #

app.include_router(router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    """Liveness check. Never includes key material."""
    return {
        "status": "ok",
        "environment": ENVIRONMENT,
        "llm_provider": settings.llm_provider,
        "search_provider": settings.search_provider,
    }