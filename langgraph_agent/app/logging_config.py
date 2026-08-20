"""
Structured Logging & PII/Secret Sanitization — Phase 6 Hardening.

Provides JSON-formatted structured logging for production with automatic scrubbing
of credentials, API keys, JWT tokens, and passwords.
"""
import os
import re
import json
import logging
import datetime
from typing import Any, Dict

# Regex patterns to scrub key-value credentials and token patterns from raw logs
LOG_SCRUB_PATTERNS = [
    # Key-value assignments like api_key=xyz, password: xyz
    re.compile(r'((?:api[_-]?key|password|passphrase|secret|token|auth(?:orization)?|bearer)\s*[:=]\s*)(["\']?[^"\',\s;]+["\']?)', re.IGNORECASE),
    # Bearer tokens
    re.compile(r'(Bearer\s+)([a-zA-Z0-9_\-\.]+)', re.IGNORECASE),
    # OpenAI/Groq/Generic style sk-... keys
    re.compile(r'\b(sk-[a-zA-Z0-9_-]{10,})\b', re.IGNORECASE),
    # JSON key patterns "password": "value"
    re.compile(r'("?(?:api[_-]?key|password|secret|token|authorization)"?\s*:\s*")([^"]+)(")', re.IGNORECASE),
]


class StructuredJsonFormatter(logging.Formatter):
    """
    Formats log records as structured JSON with automatic sensitive token redaction.
    """
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()

        # Scrub sensitive patterns from message
        for pattern in LOG_SCRUB_PATTERNS:
            if pattern.groups == 2:
                msg = pattern.sub(r'\1[REDACTED_SECRET]', msg)
            elif pattern.groups == 3:
                msg = pattern.sub(r'\1[REDACTED_SECRET]\3', msg)
            else:
                msg = pattern.sub('[REDACTED_SECRET]', msg)

        log_obj: Dict[str, Any] = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": msg,
            "module": record.module,
            "funcName": record.funcName,
            "lineNo": record.lineno,
        }

        # Include request_id or job_name if attached to record
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "job_name"):
            log_obj["job_name"] = record.job_name
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms

        if record.exc_info:
            exc_str = self.formatException(record.exc_info)
            for pattern in LOG_SCRUB_PATTERNS:
                exc_str = pattern.sub('[REDACTED_SECRET]', exc_str)
            log_obj["exception"] = exc_str

        return json.dumps(log_obj, default=str)


def configure_logging():
    """
    Configures application logging based on environment (JSON in production, text in local dev).
    """
    log_format_env = os.getenv("LOG_FORMAT", "text").lower()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    if log_format_env == "json":
        handler.setFormatter(StructuredJsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))

    root_logger.addHandler(handler)
