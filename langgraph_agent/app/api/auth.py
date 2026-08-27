"""
API Authentication & Role-Based Access Control (RBAC) — Phase 6 Security.

Supports API-Key authentication via `X-API-Key` or `Authorization: Bearer <key>`.
Provides role-based access dependencies:
  - `admin`: Full administrative access (job triggers, tenant holds, system config)
  - `service`: Automation/integration access (workflow execution, pipeline messages, tickets)
  - `read_only`: Inspection and querying access (tenants, properties, tickets listing)
"""
import os
import logging
from typing import Optional, List, Dict, Set
from dataclasses import dataclass

from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Security scheme extractors
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    key_identifier: str
    role: str  # "admin", "service", "read_only"


def is_auth_enabled() -> bool:
    """
    Returns True if authentication is explicitly enabled or if any API keys are configured.
    """
    if os.getenv("ENABLE_API_AUTH", "").lower() in ("true", "1", "yes"):
        return True
    return bool(
        os.getenv("API_KEYS_ADMIN") or
        os.getenv("API_KEYS_SERVICE") or
        os.getenv("API_KEYS_READONLY") or
        os.getenv("API_KEY")
    )


def _load_configured_keys() -> Dict[str, str]:
    """
    Parses comma-separated keys from environment variables and maps each key to its assigned role.
    """
    key_role_map: Dict[str, str] = {}

    def _register(env_var: str, role: str):
        raw = os.getenv(env_var, "")
        if raw:
            for k in raw.split(","):
                k_clean = k.strip()
                if k_clean:
                    key_role_map[k_clean] = role

    _register("API_KEYS_ADMIN", "admin")
    _register("API_KEYS_SERVICE", "service")
    _register("API_KEYS_READONLY", "read_only")

    # Generic fallback API_KEY defaults to admin
    generic_key = os.getenv("API_KEY", "").strip()
    if generic_key and generic_key not in key_role_map:
        key_role_map[generic_key] = "admin"

    return key_role_map


async def get_current_user(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> AuthenticatedUser:
    """
    Authenticates incoming request via X-API-Key or Bearer token.
    Attempts JWT decoding first; if invalid or missing, falls back to static configured API keys.
    If auth is not enabled, returns a default system user.
    """
    if not is_auth_enabled():
        return AuthenticatedUser(key_identifier="anonymous_dev", role="admin")

    token = None
    if bearer and bearer.credentials:
        token = bearer.credentials.strip()
    elif api_key:
        token = api_key.strip()

    if not token:
        logger.warning(f"Unauthenticated request to {request.url.path} from client {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API authentication credentials. Provide 'X-API-Key' or 'Authorization: Bearer <key>'."
        )

    # 1. Attempt JWT decoding first
    # We must inline the import or ensure auth_service is available, but to avoid circular dependencies
    # we'll import here or at the top. Let's import at the top later.
    from app.services.auth_service import auth_service
    payload = auth_service.verify_access_token(token)
    if payload and "sub" in payload and "role" in payload:
        return AuthenticatedUser(key_identifier=payload["sub"], role=payload["role"])

    # 2. Fall back to static API keys (service to service)
    key_role_map = _load_configured_keys()
    role = key_role_map.get(token)

    if not role:
        logger.warning(f"Invalid API key attempt on {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token or API key."
        )

    masked_key = f"{token[:4]}...{token[-2:]}" if len(token) > 6 else "***"
    return AuthenticatedUser(key_identifier=masked_key, role=role)


async def require_admin(user: AuthenticatedUser = Security(get_current_user)) -> AuthenticatedUser:
    """Requires 'admin' role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: This action requires 'admin' role privileges."
        )
    return user


async def require_service_or_admin(user: AuthenticatedUser = Security(get_current_user)) -> AuthenticatedUser:
    """Requires 'service' or 'admin' role."""
    if user.role not in ("admin", "service"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: This action requires 'service' or 'admin' role privileges."
        )
    return user


async def require_auth(user: AuthenticatedUser = Security(get_current_user)) -> AuthenticatedUser:
    """Requires any authenticated role."""
    return user
