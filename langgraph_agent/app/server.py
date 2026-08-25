"""
Elarion Real Estate Agent Platform — Unified Core API Server (Phases 4, 5 & 6 Hardening).

Hosts all project-wide REST endpoints across all four workflow domains:
  - Health & Readiness (/health, /ready)
  - Metrics (/metrics)
  - Tenants (/api/v1/tenants)
  - Properties (/api/v1/properties)
  - Maintenance Tickets (/api/v1/maintenance)
  - Workflows (/api/v1/workflows)
  - FAQ / Property Search (/api/v1/faq)
  - Master Pipeline (/api/v1/pipeline)
  - Background Jobs & Alerting (/api/v1/jobs)
"""
import os
import sys
import time
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Callable, List

# Ensure parent path is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.checkpointer import close_checkpointer
from app.api.schemas import ErrorResponse
from app.jobs.scheduler import platform_scheduler
from app.logging_config import configure_logging
from app.api.middleware import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    PayloadSizeLimitMiddleware
)

# Import all domain routers
from app.api.routers.health import router as health_router
from app.api.routers.metrics import router as metrics_router, record_http_request
from app.api.routers.tenants import router as tenants_router
from app.api.routers.properties import router as properties_router
from app.api.routers.maintenance import router as maintenance_router
from app.api.routers.workflows import router as workflows_router
from app.api.routers.faq import router as faq_router
from app.api.routers.pipeline import router as pipeline_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.dashboard import router as dashboard_router
from app.api.routers.leases import router as leases_router
from app.api.routers.renewals import router as renewals_router
from app.api.routers.escalations import router as escalations_router
from app.api.routers.documents import router as documents_router
from app.api.routers.auth import router as auth_router

# Configure structured logging
configure_logging()
logger = logging.getLogger("elarion.api")


# ── Lifespan Management ───────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Elarion Real Estate Core API Server (v2.0 - Phase 6 Hardened)...")
    # Start background scheduler if enabled (standalone scheduler recommended for production)
    if os.getenv("ENABLE_BACKGROUND_SCHEDULER", "false").lower() in ("true", "1", "yes"):
        await platform_scheduler.start()
        logger.info("Background job scheduler started in server process.")

    yield

    logger.info("Shutting down Elarion Core API Server and closing checkpointers...")
    if platform_scheduler.is_running():
        await platform_scheduler.stop()
    await close_checkpointer()
    logger.info("Checkpointer and scheduler connections closed cleanly.")


# ── FastAPI App Initialization ────────────────────────────────────────────────

app = FastAPI(
    title="Elarion Real Estate Agent — Core API",
    description=(
        "Unified multi-domain REST API for the Elarion Real Estate Platform. "
        "Provides hardened operational access to Maintenance, Rent Reminders, FAQ/Search, "
        "Lease Expiry/Renewal, Master Pipeline Ingestion, and Background Jobs/Alerting."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ── CORS Middleware Configuration ─────────────────────────────────────────────

def _get_cors_origins() -> List[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:8080")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


allowed_origins = _get_cors_origins()
allow_creds = bool("*" not in allowed_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_creds,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ── Security, Rate Limiting & Payload Size Middlewares ─────────────────────────

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(PayloadSizeLimitMiddleware)


# ── Request Logging & Request ID Middleware ───────────────────────────────────

@app.middleware("http")
async def logging_and_request_id_middleware(request: Request, call_next: Callable):
    request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:8]}"
    start_time = time.perf_counter()

    # Pass request_id in state
    request.state.request_id = request_id

    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        duration_sec = duration_ms / 1000.0

        # Record metric for Prometheus
        record_http_request(request.method, request.url.path, response.status_code, duration_sec)

        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"-> {response.status_code} ({duration_ms:.2f}ms)",
            extra={"request_id": request_id, "duration_ms": duration_ms}
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        duration_sec = duration_ms / 1000.0
        record_http_request(request.method, request.url.path, 500, duration_sec)

        logger.error(
            f"[{request_id}] {request.method} {request.url.path} "
            f"FAILED with unhandled exception: {exc} ({duration_ms:.2f}ms)",
            exc_info=True,
            extra={"request_id": request_id, "duration_ms": duration_ms}
        )
        raise exc


# ── Standardized Exception Handlers ───────────────────────────────────────────

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    err_code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        err_code = "AUTHENTICATION_REQUIRED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        err_code = "FORBIDDEN"

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=err_code,
            message=str(exc.detail),
            status_code=exc.status_code
        ).model_dump(),
        headers=exc.headers
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = "; ".join([f"{e.get('loc', [])}: {e.get('msg', '')}" for e in exc.errors()])
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="VALIDATION_ERROR",
            message=f"Request validation failed: {error_details}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        ).model_dump()
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="INTERNAL_SERVER_ERROR",
            message="An internal server error occurred while processing the request.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ).model_dump()
    )


# ── Mount Domain Routers ──────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(tenants_router)
app.include_router(properties_router)
app.include_router(maintenance_router)
app.include_router(workflows_router)
app.include_router(faq_router)
app.include_router(pipeline_router)
app.include_router(jobs_router)
app.include_router(dashboard_router)
app.include_router(leases_router)
app.include_router(renewals_router)
app.include_router(escalations_router)
app.include_router(documents_router)
app.include_router(auth_router)


# ── CLI Runner ────────────────────────────────────────────────────────────────

def run():
    import uvicorn
    port = int(os.getenv("API_PORT") or os.getenv("PORT") or 8080)
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run("app.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
