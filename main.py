"""
main.py

Narada — FastAPI entry point.

Run locally:
    uvicorn main:app --reload
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from config import configure_logging, get_settings

settings = get_settings()
configure_logging(settings)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Narada",
    description=(
        "Narada traverses the web, extracts structured intelligence, "
        "and delivers it as traceable data. "
        "Named after the divine sage who traveled all three worlds "
        "gathering and delivering knowledge."
    ),
    version="0.1.0",
)

# CORS — open for now, lock down to frontend origin in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    """Liveness check. Returns active provider config."""
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.ollama_model if settings.llm_provider == "ollama" else "see config",
        "search_provider": settings.search_provider,
    }