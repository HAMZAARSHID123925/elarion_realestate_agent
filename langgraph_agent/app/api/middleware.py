"""
Security & Abuse Protection Middleware — Phase 6 Hardening.

Provides:
  1. SecurityHeadersMiddleware (nosniff, DENY, Referrer-Policy, HSTS)
  2. RateLimitMiddleware (Client IP/API-Key token bucket rate limiting with 429 response)
  3. PayloadSizeLimitMiddleware (Max request body size enforcement with 413 response)
"""
import os
import time
import logging
from typing import Dict, Tuple, List
from collections import defaultdict

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from dotenv import load_dotenv

from app.api.schemas import ErrorResponse

load_dotenv()

logger = logging.getLogger(__name__)


# ── 1. Security Headers Middleware ────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects OWASP-recommended HTTP security headers on all responses.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HSTS for HTTPS traffic
        if request.url.scheme == "https" or os.getenv("FORCE_HSTS", "false").lower() in ("true", "1", "yes"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


# ── 2. Rate Limiting Middleware ───────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding window rate limiter per client IP / API Key.
    """
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._request_history: Dict[str, List[float]] = defaultdict(list)

    @property
    def current_limit(self) -> int:
        try:
            return int(os.getenv("RATE_LIMIT_PER_MINUTE", str(self.requests_per_minute)))
        except ValueError:
            return self.requests_per_minute

    def _get_client_key(self, request: Request) -> str:
        # Prefer API key or forwarded client IP
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key.strip()}"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting on local health checks and metrics
        if request.url.path in ("/health", "/ready", "/metrics"):
            return await call_next(request)

        # Allow disabling rate limit via env
        if os.getenv("ENABLE_RATE_LIMIT", "true").lower() not in ("true", "1", "yes"):
            return await call_next(request)

        now = time.time()
        client_key = self._get_client_key(request)
        window_start = now - 60.0
        limit = self.current_limit

        # Clean old timestamps
        timestamps = [t for t in self._request_history[client_key] if t > window_start]
        self._request_history[client_key] = timestamps

        if len(timestamps) >= limit:
            logger.warning(f"[RATE LIMIT] Client '{client_key}' exceeded {limit} req/min on {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=ErrorResponse(
                    error="RATE_LIMIT_EXCEEDED",
                    message=f"Too many requests. Rate limit is {limit} requests per minute.",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS
                ).model_dump(),
                headers={"Retry-After": "60"}
            )

        self._request_history[client_key].append(now)
        return await call_next(request)

    def reset(self):
        """Resets rate limit tracker (for testing)."""
        self._request_history.clear()


# ── 3. Payload Size Limit Middleware ──────────────────────────────────────────

class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Rejects request bodies exceeding MAX_PAYLOAD_BYTES (default: 2 MB).
    """
    def __init__(self, app, max_bytes: int = 2 * 1024 * 1024):
        super().__init__(app)
        self.max_bytes = max_bytes

    @property
    def current_max_bytes(self) -> int:
        try:
            return int(os.getenv("MAX_PAYLOAD_BYTES", str(self.max_bytes)))
        except ValueError:
            return self.max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("Content-Length")
        max_bytes = self.current_max_bytes
        if content_length:
            try:
                length = int(content_length)
                if length > max_bytes:
                    logger.warning(f"[PAYLOAD LIMIT] Request to {request.url.path} with size {length} bytes exceeded max {max_bytes} bytes.")
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content=ErrorResponse(
                            error="PAYLOAD_TOO_LARGE",
                            message=f"Request body exceeds the maximum permitted size of {max_bytes // (1024 * 1024)} MB.",
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                        ).model_dump()
                    )
            except ValueError:
                pass

        return await call_next(request)
