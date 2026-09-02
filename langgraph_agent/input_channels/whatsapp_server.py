import os
import hmac
import hashlib
import logging
import time
from collections import deque, defaultdict
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse

from app.pipeline import handle_request
from app.checkpointer import close_checkpointer
from app.core_workflows.maintenance.mcp_client import mcp_client as maintenance_mcp
from app.core_workflows.faq.mcp_client import property_mcp_client as faq_mcp
from app.core_workflows.rent_reminder.scheduler import rent_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _validate_whatsapp_token_sync() -> None:
    """Calls Meta's Graph API at startup to check if the access token is valid.
    Logs a clear, actionable warning if the token has expired (they rotate
    every 24h during testing) so the developer knows immediately instead of
    only finding out when a reply fails to send later."""
    if not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        logger.warning(
            "⚠️  WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID not set -- "
            "WhatsApp reply delivery will be skipped. Set them in .env."
        )
        return
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}"
    try:
        resp = requests.get(url, headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            display = data.get("display_phone_number", "N/A")
            logger.info(f"✅ WhatsApp access token is VALID (phone: {display})")
        else:
            error_msg = resp.json().get("error", {}).get("message", resp.text[:200])
            logger.warning(
                f"❌ WhatsApp access token is EXPIRED or INVALID — {error_msg}\n"
                f"   → Go to https://developers.facebook.com/apps/ → your app → WhatsApp → API Setup\n"
                f"   → Click 'Generate' under Temporary Access Token, paste it into .env, and restart."
            )
    except Exception as e:
        logger.warning(f"⚠️  Could not validate WhatsApp token (network issue?): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Both maintenance and FAQ flows call out to their MCP servers (ticket
    # creation, property lookup) -- terminal.py connects these explicitly
    # before its loop starts, but neither vapi_server.py nor this file did
    # until now, which is why maintenance requests were failing with
    # "MCP Client not connected" here. Connecting once at process startup
    # (not per-request) matches how terminal.py does it.
    logger.info("Connecting MCP clients (maintenance + FAQ)...")

    try:
        await maintenance_mcp.connect()
        logger.info("Maintenance MCP client connected.")
    except Exception:
        logger.exception("Failed to connect maintenance MCP client -- full traceback above.")

    try:
        await faq_mcp.connect()
        logger.info("FAQ MCP client connected.")
    except Exception:
        logger.exception("Failed to connect FAQ MCP client -- full traceback above.")

    # Validate WhatsApp access token early so expired tokens are caught
    # at startup rather than on the first failed reply send.
    _validate_whatsapp_token_sync()

    logger.info("Starting automated morning rent reminder scheduler...")
    try:
        rent_scheduler.start()
        logger.info("Automated morning rent scheduler running.")
    except Exception as e:
        logger.error(f"Failed to start rent scheduler: {e}")

    yield

    logger.info("Shutting down -- stopping rent scheduler, disconnecting MCP clients and checkpointer...")
    await rent_scheduler.stop()
    await maintenance_mcp.disconnect()
    await faq_mcp.disconnect()
    await close_checkpointer()


app = FastAPI(title="ELARION WhatsApp Agent API (Meta Cloud API)", lifespan=lifespan)

# --- Meta WhatsApp Cloud API config ------------------------------------
# All of these come from Meta for Developers > your App > WhatsApp > API Setup.
# For testing, Meta gives you a free test phone number, a temporary access
# token (24h, regenerate as needed while testing), and lets you add up to 5
# recipient test numbers -- no business verification or payment required
# until you're ready to move past testing.
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET")
# You choose this string yourself and enter the same value in the Meta App
# Dashboard's webhook config -- it's just a shared secret for the one-time
# verification handshake, not the same as the App Secret used for signing.
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v25.0")

# VALIDATE_META_SIGNATURE defaults to "true" -- production-safe by default.
# Only ever set "false" for a throwaway local debugging session.
VALIDATE_META_SIGNATURE = os.getenv("VALIDATE_META_SIGNATURE", "true").lower() == "true"

GRAPH_API_URL = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"

# --- 4.4 Per-phone-number rate limiting -------------------------------
# Simple in-memory sliding-window limiter: caps how many inbound messages a
# single phone number can push into the AI pipeline per minute. This is a
# process-local dict (fine for a single-instance deployment; if this is ever
# horizontally scaled behind a load balancer, move this to Redis so all
# instances share one counter). Protects against a looping/broken tenant
# device or a bad actor who has the webhook URL and a valid signature.
RATE_LIMIT_MAX_MESSAGES = int(os.getenv("WHATSAPP_RATE_LIMIT_MAX_MESSAGES", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("WHATSAPP_RATE_LIMIT_WINDOW_SECONDS", "60"))
_message_timestamps: dict[str, deque] = defaultdict(deque)


def _is_rate_limited(phone_number: str) -> bool:
    """True if this phone number has already hit the per-window message cap."""
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    timestamps = _message_timestamps[phone_number]

    while timestamps and timestamps[0] < window_start:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT_MAX_MESSAGES:
        return True

    timestamps.append(now)
    return False


# --- 4.3 Alerting when a WhatsApp reply fails to send -------------------
# Before this, a failed send to Meta's Graph API was only logged -- the
# tenant was left with no reply and nobody on the team knew. This posts to a
# Slack incoming webhook (or logs a CRITICAL line as a fallback if no
# webhook is configured) so a human actually finds out.
TEAM_ALERT_WEBHOOK_URL = os.getenv("TEAM_ALERT_WEBHOOK_URL")


def _alert_team(message: str) -> None:
    if not TEAM_ALERT_WEBHOOK_URL:
        logger.critical(f"[TEAM ALERT -- no TEAM_ALERT_WEBHOOK_URL configured] {message}")
        return
    try:
        requests.post(TEAM_ALERT_WEBHOOK_URL, json={"text": message}, timeout=5)
    except Exception as e:
        # Alerting must never itself crash message processing.
        logger.error(f"Failed to post team alert to TEAM_ALERT_WEBHOOK_URL: {e}")


def _verify_meta_signature(raw_body: bytes, signature_header: str) -> None:
    """Rejects any POST that didn't actually come from Meta.

    Meta signs the raw request body with your App Secret (HMAC-SHA256) and
    sends it as "X-Hub-Signature-256: sha256=<hex>". This must be checked
    against the *raw* bytes, before any JSON parsing -- key ordering in a
    re-serialized JSON body would break the comparison. Skipping this check
    means anyone who finds your webhook URL can post fake messages straight
    into your orchestrator/maintenance/faq graphs as if they were real
    tenant input.
    """
    if not VALIDATE_META_SIGNATURE:
        logger.warning("Meta signature validation is DISABLED -- do not run this in production.")
        return

    if not WHATSAPP_APP_SECRET:
        raise RuntimeError("WHATSAPP_APP_SECRET is not set -- cannot validate webhook signatures.")

    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Missing or malformed X-Hub-Signature-256 header")

    expected_signature = signature_header.removeprefix("sha256=")
    computed_signature = hmac.new(
        WHATSAPP_APP_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, computed_signature):
        logger.error("Meta signature validation failed for inbound webhook request")
        raise HTTPException(status_code=403, detail="Invalid signature")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/whatsapp/webhook")
async def verify_webhook(request: Request):
    """
    Meta calls this once (GET, not POST) when you register/save the webhook
    URL in the App Dashboard, to prove you control the endpoint. It sends
    hub.mode, hub.verify_token, and hub.challenge as query params -- if the
    token matches WHATSAPP_VERIFY_TOKEN, echo hub.challenge back as plain
    text. This has nothing to do with actual message traffic; it only runs
    once per webhook URL you configure.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verification succeeded")
        return PlainTextResponse(content=challenge or "", status_code=200)

    logger.warning("Webhook verification failed -- token mismatch or missing params")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Meta calls this on every inbound event -- messages, but also delivery/
    read status updates, which arrive on the same endpoint and must be
    ignored rather than treated as tenant input. Shape (trimmed):

      {
        "entry": [{
          "changes": [{
            "value": {
              "messages": [{"from": "923...", "id": "wamid...", "text": {"body": "..."}}],
              "statuses": [...]   -- present instead of "messages" for delivery receipts
            }
          }]
        }]
      }

    We ack Meta immediately (200, empty body) and process the pipeline call
    + reply-send in the background -- Meta expects a fast response or it
    will retry, which would otherwise duplicate-process the same message.
    """
    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    _verify_meta_signature(raw_body, signature_header)

    payload = await request.json()

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])

            for message in messages:
                if message.get("type") != "text":
                    logger.info(f"Ignoring non-text message type: {message.get('type')}")
                    continue

                from_number = message.get("from", "")
                body_text = message.get("text", {}).get("body", "").strip()
                message_id = message.get("id")

                contacts = value.get("contacts", [])
                profile_name = contacts[0].get("profile", {}).get("name") if contacts else None

                if not from_number or not body_text:
                    logger.warning(f"Ignoring malformed message payload: {message}")
                    continue

                if _is_rate_limited(from_number):
                    logger.warning(
                        f"Rate limit exceeded for {from_number} "
                        f"({RATE_LIMIT_MAX_MESSAGES} msgs / {RATE_LIMIT_WINDOW_SECONDS}s) -- dropping message."
                    )
                    continue

                logger.info(f"Inbound WhatsApp message from {from_number} (id={message_id}): {body_text!r}")

                background_tasks.add_task(
                    _process_and_reply,
                    from_number=from_number,
                    body_text=body_text,
                    message_id=message_id,
                    profile_name=profile_name,
                )
            # "statuses" entries (sent/delivered/read receipts) are silently
            # skipped -- not tenant input, nothing to process.

    return JSONResponse(content={"status": "received"}, status_code=200)


async def _process_and_reply(from_number: str, body_text: str, message_id: str, profile_name: str):
    try:
        final_response = await handle_request(
            channel="whatsapp",
            user_id=from_number,
            raw_text=body_text,
            channel_metadata={
                "message_id": message_id,
                "profile_name": profile_name,
            },
        )
    except Exception as e:
        logger.error(f"Error processing WhatsApp message from {from_number}: {e}")
        final_response = "Sorry, I ran into an error processing that. Please try again shortly."

    # Printed (not just logged) so it's visible immediately in the console
    # running whatsapp_server.py -- useful for local testing.
    print(f"[WhatsApp -> {from_number}] {final_response}")

    _send_whatsapp_message(to=from_number, body=final_response)


def _send_whatsapp_message(to: str, body: str) -> None:
    if not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        logger.warning(
            f"WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID not set -- "
            f"skipping actual send to {to}. Reply was still generated "
            f"correctly (see the [WhatsApp -> ...] line above); this only "
            f"affects delivering it back over the Graph API."
        )
        return

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }

    try:
        response = requests.post(GRAPH_API_URL, headers=headers, json=payload, timeout=10)
        if response.status_code >= 400:
            logger.error(f"Failed to send WhatsApp reply to {to}: {response.status_code} {response.text}")
            _alert_team(
                f"WhatsApp reply FAILED to send to {to} "
                f"(HTTP {response.status_code}): {response.text[:300]}"
            )
        else:
            logger.info(f"Sent WhatsApp reply to {to}")
    except Exception as e:
        logger.error(f"Failed to send WhatsApp reply to {to}: {e}")
        _alert_team(f"WhatsApp reply FAILED to send to {to} (exception): {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
