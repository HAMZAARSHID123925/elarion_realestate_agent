import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# Security configuration — require JWT_SECRET_KEY in production, with safe ephemeral fallback in development
_env_secret = os.getenv("JWT_SECRET_KEY")
if not _env_secret:
    if os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod"):
        raise RuntimeError("CRITICAL SECURITY ERROR: JWT_SECRET_KEY environment variable is missing in production environment!")
    logger.warning("WARNING: JWT_SECRET_KEY not set in environment. Generating an ephemeral secret key for this process session. Set JWT_SECRET_KEY in .env for persistent token verification.")
    SECRET_KEY = secrets.token_hex(32)
else:
    SECRET_KEY = _env_secret

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

class AuthService:
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except ValueError:
            return False

    def get_password_hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_access_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None

auth_service = AuthService()
