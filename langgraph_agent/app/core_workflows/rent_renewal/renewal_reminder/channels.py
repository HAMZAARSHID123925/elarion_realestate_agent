"""
Renewal Reminder Channel Dispatcher — Phase 2, Workflow #4.

Dispatches messages across Email, WhatsApp, and Mock channels.
Handles authentication, API payload assembly, and graceful fallbacks.
"""
import os
import logging
import httpx
from typing import Dict, Any, Optional

from app.core_workflows.rent_renewal.renewal_reminder.config import get_from_email_address

logger = logging.getLogger(__name__)

# Environment variables
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v25.0")


async def dispatch_reminder(
    recipient: str,
    subject: str,
    body: str,
    channel: str = "email",
) -> Dict[str, Any]:
    """
    Dispatches a reminder message to the recipient over the chosen channel.

    Args:
        recipient: Email address or phone number.
        subject: Message subject.
        body: Plaintext body content.
        channel: 'email' | 'whatsapp' | 'mock'

    Returns:
        Dict with keys:
            success (bool),
            status (str: SENT | DELIVERED | MOCKED | FAILED),
            channel (str),
            recipient (str),
            message_id (str, optional),
            error (str, optional)
    """
    channel_norm = channel.strip().lower()

    if channel_norm == "email":
        return await _dispatch_email(recipient, subject, body)
    elif channel_norm == "whatsapp":
        return await _dispatch_whatsapp(recipient, body)
    else:
        return _dispatch_mock(recipient, subject, body, channel=channel_norm)


async def _dispatch_email(recipient: str, subject: str, body: str) -> Dict[str, Any]:
    """Dispatches via Resend API or logs locally if unconfigured."""
    from_address = get_from_email_address()

    if not RESEND_API_KEY:
        logger.info(
            "[Mock Email Outbound] RESEND_API_KEY not set. Sent renewal reminder to %s. Subject: %s",
            recipient,
            subject,
        )
        return {
            "success": True,
            "status": "MOCKED",
            "channel": "email",
            "recipient": recipient,
            "message_id": f"mock-email-{os.urandom(4).hex()}",
        }

    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": from_address,
            "to": [recipient],
            "subject": subject,
            "text": body,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code in (200, 201):
                data = response.json()
                msg_id = data.get("id", "")
                logger.info("Resend email sent successfully to %s: id=%s", recipient, msg_id)
                return {
                    "success": True,
                    "status": "SENT",
                    "channel": "email",
                    "recipient": recipient,
                    "message_id": msg_id,
                }
            else:
                err_msg = f"Resend API error HTTP {response.status_code}: {response.text}"
                logger.error(err_msg)
                return {
                    "success": False,
                    "status": "FAILED",
                    "channel": "email",
                    "recipient": recipient,
                    "error": err_msg,
                }
    except Exception as e:
        logger.error("Exception sending email via Resend: %s", e, exc_info=True)
        return {
            "success": False,
            "status": "FAILED",
            "channel": "email",
            "recipient": recipient,
            "error": str(e),
        }


async def _dispatch_whatsapp(recipient: str, body: str) -> Dict[str, Any]:
    """Dispatches via Meta WhatsApp Cloud API or logs locally if unconfigured."""
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.info(
            "[Mock WhatsApp Outbound] WhatsApp credentials not set. Sent renewal reminder to %s.",
            recipient,
        )
        return {
            "success": True,
            "status": "MOCKED",
            "channel": "whatsapp",
            "recipient": recipient,
            "message_id": f"mock-wa-{os.urandom(4).hex()}",
        }

    try:
        url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        # Format phone number: remove non-digits/spaces/dashes
        clean_number = "".join(ch for ch in recipient if ch.isdigit() or ch == "+")
        if clean_number.startswith("+"):
            clean_number = clean_number[1:]

        payload = {
            "messaging_product": "whatsapp",
            "to": clean_number,
            "type": "text",
            "text": {"body": body},
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code in (200, 201):
                data = response.json()
                messages = data.get("messages", [])
                msg_id = messages[0].get("id") if messages else "wa-sent"
                logger.info("WhatsApp reminder sent successfully to %s: id=%s", recipient, msg_id)
                return {
                    "success": True,
                    "status": "SENT",
                    "channel": "whatsapp",
                    "recipient": recipient,
                    "message_id": msg_id,
                }
            else:
                err_msg = f"Meta WhatsApp API error HTTP {response.status_code}: {response.text}"
                logger.error(err_msg)
                return {
                    "success": False,
                    "status": "FAILED",
                    "channel": "whatsapp",
                    "recipient": recipient,
                    "error": err_msg,
                }
    except Exception as e:
        logger.error("Exception sending WhatsApp message: %s", e, exc_info=True)
        return {
            "success": False,
            "status": "FAILED",
            "channel": "whatsapp",
            "recipient": recipient,
            "error": str(e),
        }


def _dispatch_mock(recipient: str, subject: str, body: str, channel: str = "mock") -> Dict[str, Any]:
    """Logs mock message dispatch locally."""
    logger.info("[Mock Channel %s] Sent to: %s | Subject: %s", channel, recipient, subject)
    return {
        "success": True,
        "status": "MOCKED",
        "channel": channel,
        "recipient": recipient,
        "message_id": f"mock-{channel}-{os.urandom(4).hex()}",
    }
