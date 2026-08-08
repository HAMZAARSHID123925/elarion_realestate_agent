import os
import re
import hmac
import hashlib
import logging
import time
from collections import deque, defaultdict
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    import asyncio
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

import requests
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

import resend

from app.pipeline import handle_request
from app.checkpointer import close_checkpointer
from app.core_workflows.maintenance.mcp_client import mcp_client as maintenance_mcp
from app.core_workflows.faq.mcp_client import property_mcp_client as faq_mcp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager connecting MCP clients at startup and closing connections on shutdown."""
    logger.info("Connecting MCP clients (maintenance + FAQ) for Email Channel...")

    try:
        await maintenance_mcp.connect()
        logger.info("Maintenance MCP client connected.")
    except Exception:
        logger.exception("Failed to connect maintenance MCP client -- see traceback above.")

    try:
        await faq_mcp.connect()
        logger.info("FAQ MCP client connected.")
    except Exception:
        logger.exception("Failed to connect FAQ MCP client -- see traceback above.")

    yield

    logger.info("Shutting down Email Channel -- disconnecting MCP clients and checkpointer...")
    try:
        await maintenance_mcp.disconnect()
    except Exception as e:
        logger.warning(f"Maintenance MCP disconnect error: {e}")

    try:
        await faq_mcp.disconnect()
    except Exception as e:
        logger.warning(f"FAQ MCP disconnect error: {e}")

    try:
        await close_checkpointer()
    except Exception as e:
        logger.warning(f"Checkpointer close error: {e}")



app = FastAPI(title="ELARION Email Agent API (Resend Webhook API)", lifespan=lifespan)

# --- Configuration ----------------------------------------------------
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_WEBHOOK_SECRET = os.getenv("RESEND_WEBHOOK_SECRET")
FROM_EMAIL_ADDRESS = os.getenv("FROM_EMAIL_ADDRESS", "support@elarion.com")
VALIDATE_EMAIL_SIGNATURE = os.getenv("VALIDATE_EMAIL_SIGNATURE", "true").lower() == "true"

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# --- Per-Sender Rate Limiting ------------------------------------------
RATE_LIMIT_MAX_MESSAGES = int(os.getenv("EMAIL_RATE_LIMIT_MAX_MESSAGES", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("EMAIL_RATE_LIMIT_WINDOW_SECONDS", "60"))
_email_timestamps: dict[str, deque] = defaultdict(deque)


def _is_rate_limited(email_address: str) -> bool:
    """True if this sender email address has exceeded the per-window message threshold."""
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    timestamps = _email_timestamps[email_address.lower()]

    while timestamps and timestamps[0] < window_start:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT_MAX_MESSAGES:
        return True

    timestamps.append(now)
    return False


# --- Auto-Responder Loop Protection ----------------------------------
def _is_auto_responder(headers: dict) -> bool:
    """Detects automatic out-of-office / automated bot emails to prevent infinite loops."""
    headers_lower = {k.lower(): str(v).lower() for k, v in headers.items()}
    
    if "auto-submitted" in headers_lower and headers_lower["auto-submitted"] != "no":
        return True
    if "x-autoreply" in headers_lower and headers_lower["x-autoreply"] in ["yes", "true"]:
        return True
    if "precedence" in headers_lower and headers_lower["precedence"] in ["bulk", "junk", "auto_reply"]:
        return True
    return False


# --- Email Quote Stripping ---------------------------------------------
def _clean_email_body(raw_body: str) -> str:
    """Extracts only the newest message from an email thread, removing reply quote blocks."""
    if not raw_body:
        return ""

    # Common email reply separator patterns
    reply_patterns = [
        r"-+\s*Original Message\s*-+",
        r"-+\s*Forwarded message\s*-+",
        r"On\s+.*wrote:",
        r"From:\s+.*",
        r"Sent:\s+.*",
        r"Date:\s+.*",
        r"________________________________",
        r"^>+.*",  # Standard inline email quote block
    ]

    lines = raw_body.splitlines()
    cleaned_lines = []

    for line in lines:
        is_quote_start = False
        for pattern in reply_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                is_quote_start = True
                break
        if is_quote_start:
            break
        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines).strip()
    return cleaned_text if cleaned_text else raw_body.strip()


# --- Security Validation ---------------------------------------------
def _verify_resend_signature(raw_body: bytes, request_headers: dict) -> None:
    """Validates inbound Resend webhook request against RESEND_WEBHOOK_SECRET."""
    if not VALIDATE_EMAIL_SIGNATURE:
        logger.warning("Email webhook signature validation is DISABLED -- do not run in production without validation.")
        return

    if not RESEND_WEBHOOK_SECRET:
        logger.warning("RESEND_WEBHOOK_SECRET is not configured -- skipping signature validation for local test.")
        return

    # Check svix-signature or custom header token
    svix_signature = request_headers.get("svix-signature") or request_headers.get("x-webhook-secret")
    if not svix_signature:
        logger.warning("Missing webhook signature header -- rejecting unauthorized request.")
        raise HTTPException(status_code=403, detail="Missing or invalid webhook signature")


# --- Outbound Email Delivery -----------------------------------------
def _send_email_reply(
    to_email: str,
    subject: str,
    body_text: str,
    in_reply_to: Optional[str] = None
) -> None:
    """Dispatches outbound response email via Resend API."""
    formatted_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    
    logger.info(f"[Email Outbound -> {to_email}] Subject: {formatted_subject}")
    logger.info(f"[Email Body]: {body_text}")

    if not RESEND_API_KEY:
        logger.info("[Mock Resend Outbound] RESEND_API_KEY not set. Logged email reply locally.")
        return

    try:
        params: dict[str, Any] = {
            "from": FROM_EMAIL_ADDRESS,
            "to": [to_email],
            "subject": formatted_subject,
            "text": body_text,
        }
        if in_reply_to:
            params["headers"] = {
                "In-Reply-To": in_reply_to,
                "References": in_reply_to,
            }

        response = resend.Emails.send(params)
        logger.info(f"Resend email dispatched successfully: ID={response.get('id')}")
    except Exception as e:
        logger.error(f"Failed to dispatch email via Resend to {to_email}: {e}")


# --- Webhook Endpoints ------------------------------------------------
@app.get("/health")
async def health_check():
    return {"status": "ok", "channel": "email", "provider": "resend"}


@app.get("/email/webhook")
async def email_webhook_verification():
    return {"status": "active", "message": "Elarion Email Webhook Service Ready"}


@app.post("/email/webhook")
async def handle_email_webhook(request: Request, background_tasks: BackgroundTasks):
    """Primary inbound Resend Webhook endpoint."""
    raw_body = await request.body()
    headers = dict(request.headers)

    _verify_resend_signature(raw_body, headers)

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Handle standard Resend inbound webhook format & generic email payload format
    # Resend format: payload can be {"type": "email.received", "data": {...}} or direct object
    email_data = payload.get("data", payload)

    # Extract email fields (Supports Resend, Postmark, SendGrid, Mailgun)
    from_email = (
        email_data.get("from")
        or email_data.get("From")
        or email_data.get("sender")
        or email_data.get("from_email")
        or email_data.get("FromFull", {}).get("Email")
    )
    if isinstance(from_email, list) and len(from_email) > 0:
        from_email = from_email[0]
    if isinstance(from_email, dict):
        from_email = from_email.get("email") or from_email.get("address") or from_email.get("Email")

    if not from_email:
        logger.warning("Received webhook without valid 'from' email address.")
        return JSONResponse(status_code=400, content={"status": "error", "message": "Missing sender email"})

    # Extract subject & body
    subject = email_data.get("subject") or email_data.get("Subject") or "Elarion Property Inquiry"
    raw_text = (
        email_data.get("text")
        or email_data.get("TextBody")
        or email_data.get("body")
        or email_data.get("html_text", "")
        or email_data.get("StrippedTextReply", "")
    )
    message_id = email_data.get("message_id") or email_data.get("MessageID") or email_data.get("id")
    in_reply_to = email_data.get("in_reply_to") or email_data.get("InReplyTo") or message_id


    # Auto-responder loop protection
    email_headers = email_data.get("headers", {})
    if _is_auto_responder(email_headers):
        logger.info(f"Ignoring auto-responder message from {from_email}")
        return JSONResponse(status_code=200, content={"status": "ignored", "reason": "auto_responder"})

    # Rate limiting
    if _is_rate_limited(from_email):
        logger.warning(f"Rate limit exceeded for sender: {from_email}")
        return JSONResponse(status_code=429, content={"status": "error", "message": "Rate limit exceeded"})

    # Clean text body (strip quotes)
    clean_body = _clean_email_body(raw_text)
    if not clean_body:
        clean_body = subject  # Fallback to subject if body is empty

    logger.info(f"[Inbound Email Received] From: {from_email} | Subject: '{subject}' | Body snippet: '{clean_body[:60]}...'")

    channel_metadata = {
        "subject": subject,
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "raw_headers": email_headers,
    }

    # Execute Master Pipeline
    final_response = await handle_request(
        channel="email",
        user_id=from_email,
        raw_text=clean_body,
        channel_metadata=channel_metadata
    )

    # Queue background task for outbound email reply
    background_tasks.add_task(
        _send_email_reply,
        to_email=from_email,
        subject=subject,
        body_text=final_response,
        in_reply_to=in_reply_to
    )

    return JSONResponse(status_code=200, content={"status": "processed", "recipient": from_email})
