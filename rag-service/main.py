"""
NyayaSetu RAG Service — FastAPI application entry point.

Start with:
    uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from utils.config import settings
from utils.logger import get_logger, setup_logging

# ── Logging ──────────────────────────────────────────────────────
setup_logging(level="DEBUG" if settings.ENVIRONMENT == "development" else "INFO")
logger = get_logger(__name__)


# ── Lifespan (startup / shutdown) ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager — runs on startup and shutdown."""
    logger.info("=" * 60)
    logger.info("  %s  v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("  Environment : %s", settings.ENVIRONMENT)
    logger.info("  Server      : http://%s:%s", settings.HOST, settings.PORT)
    logger.info("  Docs        : http://%s:%s/docs", settings.HOST, settings.PORT)
    logger.info("=" * 60)
    yield
    logger.info("%s shutting down.", settings.APP_NAME)


# ── FastAPI application ─────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered Retrieval-Augmented Generation service "
        "for Indian legal knowledge"
    ),
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server (frontend)
        "http://localhost:3000",  # Express backend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint — confirms the service is running."""
    return {
        "message": "NyayaSetu RAG Service is running",
        "docs": "/docs",
    }
