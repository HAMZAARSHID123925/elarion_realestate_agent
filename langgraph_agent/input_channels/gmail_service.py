"""
Direct Gmail Input Channel for Elarion Real Estate Agent.
Uses IMAP (inbound listener) and SMTP (threaded outbound dispatch) with Gmail App Password.
Supports real-time, multi-turn conversational memory via LangGraph.
"""
import os
import re
import sys
import time
import email
import smtplib
import imaplib
import asyncio
import logging
from email.header import decode_header
from email.utils import parseaddr, formataddr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import deque, defaultdict
from typing import Optional, Dict, Any, Tuple

from dotenv import load_dotenv

# Ensure langgraph_agent root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.pipeline import handle_request
from app.checkpointer import close_checkpointer
from app.core_workflows.maintenance.mcp_client import mcp_client as maintenance_mcp
from app.core_workflows.faq.mcp_client import property_mcp_client as faq_mcp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("GmailChannel")

# --- Configuration ---
GMAIL_USER = os.getenv("GMAIL_USER", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
GMAIL_DISPLAY_NAME = os.getenv("GMAIL_DISPLAY_NAME", "Elarion Real Estate Assistant")
GMAIL_POLL_INTERVAL = float(os.getenv("GMAIL_POLL_INTERVAL", "5.0"))

RATE_LIMIT_MAX_MESSAGES = int(os.getenv("EMAIL_RATE_LIMIT_MAX_MESSAGES", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("EMAIL_RATE_LIMIT_WINDOW_SECONDS", "60"))
_email_timestamps: dict[str, deque] = defaultdict(deque)


def _is_rate_limited(email_address: str) -> bool:
    """Ensures a single sender cannot overwhelm the agent with rapid emails."""
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    timestamps = _email_timestamps[email_address.lower()]

    while timestamps and timestamps[0] < window_start:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT_MAX_MESSAGES:
        return True

    timestamps.append(now)
    return False


def _is_auto_responder(headers: dict) -> bool:
    """Detects automatic out-of-office / bounce / bot emails to prevent infinite loops."""
    h_lower = {k.lower(): str(v).lower() for k, v in headers.items()}
    if "auto-submitted" in h_lower and h_lower["auto-submitted"] != "no":
        return True
    if "x-autoreply" in h_lower and h_lower["x-autoreply"] in ["yes", "true"]:
        return True
    if "precedence" in h_lower and h_lower["precedence"] in ["bulk", "junk", "auto_reply"]:
        return True
    return False


def _clean_email_body(raw_body: str) -> str:
    """Extracts only the newest message from an email thread, stripping quoted history."""
    if not raw_body:
        return ""

    reply_patterns = [
        r"-+\s*Original Message\s*-+",
        r"-+\s*Forwarded message\s*-+",
        r"On\s+.*wrote:",
        r"From:\s+.*",
        r"Sent:\s+.*",
        r"Date:\s+.*",
        r"________________________________",
        r"^>+.*",
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


def _decode_header_str(header_value: Optional[str]) -> str:
    """Safely decodes RFC 2047 encoded email headers (e.g. utf-8 subjects)."""
    if not header_value:
        return ""
    decoded_fragments = []
    for fragment, encoding in decode_header(header_value):
        if isinstance(fragment, bytes):
            try:
                decoded_fragments.append(fragment.decode(encoding or "utf-8", errors="replace"))
            except Exception:
                decoded_fragments.append(fragment.decode("utf-8", errors="replace"))
        else:
            decoded_fragments.append(str(fragment))
    return "".join(decoded_fragments).strip()


def _extract_body_from_email_message(msg: email.message.Message) -> str:
    """Extracts plain text content from MIME multipart or singlepart email."""
    if not msg.is_multipart():
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        return ""

    text_parts = []
    html_parts = []

    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get("Content-Disposition", ""))

        # Skip attachments
        if "attachment" in content_disposition:
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        charset = part.get_content_charset() or "utf-8"
        decoded = payload.decode(charset, errors="replace")

        if content_type == "text/plain":
            text_parts.append(decoded)
        elif content_type == "text/html":
            html_parts.append(decoded)

    if text_parts:
        return "\n".join(text_parts).strip()

    # Fallback: strip basic HTML tags if only HTML is available
    if html_parts:
        raw_html = "\n".join(html_parts)
        text = re.sub(r"<style.*?</style>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    return ""


class GmailAgentService:
    def __init__(self):
        if not GMAIL_USER or not GMAIL_APP_PASSWORD:
            raise ValueError(
                "GMAIL_USER and GMAIL_APP_PASSWORD must be configured in .env!"
            )
        self.user = GMAIL_USER
        self.password = GMAIL_APP_PASSWORD
        self.display_name = GMAIL_DISPLAY_NAME
        self.poll_interval = GMAIL_POLL_INTERVAL
        self._is_running = False
        self._imap: Optional[imaplib.IMAP4_SSL] = None

    def _get_imap_connection(self) -> imaplib.IMAP4_SSL:
        """Establishes or verifies IMAP SSL connection to Gmail."""
        if self._imap is not None:
            try:
                self._imap.noop()
                return self._imap
            except Exception:
                try:
                    self._imap.logout()
                except Exception:
                    pass
                self._imap = None

        logger.info(f"Connecting to Gmail IMAP (imap.gmail.com:993) as {self.user}...")
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(self.user, self.password)
        self._imap = imap
        logger.info("Gmail IMAP connected and authenticated successfully.")
        return self._imap

    def send_reply(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
    ) -> bool:
        """
        Sends outbound reply via Gmail SMTP (smtp.gmail.com:587) with STARTTLS.
        Maintains email client thread continuity via In-Reply-To and References.
        """
        # Format Subject cleanly without stacking "Re: Re: Re:"
        clean_subj = subject.strip()
        if not clean_subj.lower().startswith("re:"):
            formatted_subject = f"Re: {clean_subj}"
        else:
            formatted_subject = clean_subj

        logger.info(f"[Gmail Outbound -> {to_email}] Subject: '{formatted_subject}'")

        msg = MIMEMultipart()
        msg["From"] = formataddr((self.display_name, self.user))
        msg["To"] = to_email
        msg["Subject"] = formatted_subject
        msg["Date"] = email.utils.formatdate(localtime=True)

        # Thread grouping headers for Gmail / Outlook / Apple Mail
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            if references:
                msg["References"] = f"{references} {in_reply_to}"
            else:
                msg["References"] = in_reply_to

        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.user, self.password)
                server.send_message(msg)
            logger.info(f"[Gmail Outbound Dispatched] Successfully sent reply to {to_email}")
            return True
        except Exception as e:
            logger.error(f"[Gmail Outbound Error] Failed to send email to {to_email}: {e}")
            return False

    async def _process_email_message(self, raw_email_bytes: bytes, msg_uid: str) -> None:
        """Parses an incoming raw email, runs LangGraph pipeline, and dispatches reply."""
        msg = email.message_from_bytes(raw_email_bytes)

        # Extract headers
        raw_from = msg.get("From", "")
        sender_name, sender_email = parseaddr(raw_from)
        sender_name = _decode_header_str(sender_name) or sender_email
        subject = _decode_header_str(msg.get("Subject", "Inquiry"))
        message_id = msg.get("Message-ID", "")
        references = msg.get("References", "")
        in_reply_to = msg.get("In-Reply-To", "")

        # Guard: Ignore emails sent by the bot itself
        if sender_email.lower() == self.user.lower():
            logger.debug("Skipping message sent by the agent itself.")
            return

        if not sender_email:
            logger.warning(f"Could not parse valid sender email from '{raw_from}' -- skipping.")
            return

        # Guard: Auto-responders / bot loops
        headers_dict = {k: v for k, v in msg.items()}
        if _is_auto_responder(headers_dict):
            logger.info(f"Ignoring auto-responder from {sender_email}")
            return

        # Guard: Ignore automated system/notification/no-reply senders
        system_patterns = ["noreply", "no-reply", "mailer-daemon", "notifications@", "google.com", "donotreply"]
        if any(pat in sender_email.lower() for pat in system_patterns):
            logger.info(f"Skipping automated notification email from {sender_email}")
            return

        # Guard: Rate limiting
        if _is_rate_limited(sender_email):
            logger.warning(f"Rate limit exceeded for sender: {sender_email} -- skipping.")
            return

        # Extract & clean body
        raw_body = _extract_body_from_email_message(msg)
        clean_body = _clean_email_body(raw_body)
        if not clean_body:
            clean_body = subject  # Fallback to subject if body is blank

        logger.info("=" * 60)
        logger.info(f"📥 [Incoming Gmail Received]")
        logger.info(f"   From: {sender_name} <{sender_email}>")
        logger.info(f"   Subject: '{subject}'")
        logger.info(f"   Message-ID: {message_id}")
        logger.info(f"   Query: {clean_body[:100]}...")
        logger.info("=" * 60)

        channel_metadata = {
            "subject": subject,
            "message_id": message_id,
            "in_reply_to": in_reply_to,
            "references": references,
            "profile_name": sender_name,
            "channel": "email"
        }

        # Run LangGraph pipeline with sender_email as the user_id (persistent checkpointer thread)
        logger.info(f"Executing LangGraph pipeline for user_id='{sender_email}'...")
        start_time = time.time()
        
        # Include subject for initial emails to give full context to triage classifier
        query_text = clean_body
        if subject and not subject.lower().startswith("re:") and not subject.lower().startswith("fwd:"):
            query_text = f"{subject}: {clean_body}"

        try:
            final_response = await handle_request(
                channel="email",
                user_id=sender_email,
                raw_text=query_text,
                channel_metadata=channel_metadata
            )
            elapsed = time.time() - start_time
            logger.info(f"Pipeline finished in {elapsed:.2f}s.")
            logger.info(f"🤖 [Agent Response]:\n{final_response}\n")

            # Dispatch threaded reply back via Gmail SMTP
            self.send_reply(
                to_email=sender_email,
                subject=subject,
                body_text=final_response,
                in_reply_to=message_id,
                references=references
            )
        except Exception as e:
            logger.exception(f"Error processing email through LangGraph pipeline: {e}")
            fallback_msg = (
                "Thank you for contacting Elarion. We received your message and our team "
                "is currently reviewing it. We will get back to you shortly."
            )
            self.send_reply(to_email=sender_email, subject=subject, body_text=fallback_msg, in_reply_to=message_id)

    async def check_inbox_once(self) -> None:
        """Polls Gmail inbox for UNSEEN messages and marks processed ones as read."""
        try:
            imap = self._get_imap_connection()
            status, _ = imap.select("INBOX")
            if status != "OK":
                logger.warning(f"Could not select INBOX: {status}")
                return

            # Search for unread emails
            status, data = imap.search(None, "UNSEEN")
            if status != "OK" or not data or not data[0]:
                return

            email_ids = data[0].split()
            logger.info(f"Found {len(email_ids)} new unread email(s) in INBOX.")

            for e_id in email_ids:
                try:
                    # Fetch RFC822 message content
                    status, msg_data = imap.fetch(e_id, "(RFC822)")
                    if status != "OK" or not msg_data:
                        continue

                    raw_bytes = None
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            raw_bytes = response_part[1]
                            break

                    if raw_bytes:
                        # Mark message as read (\Seen) immediately so concurrent cycles don't duplicate
                        imap.store(e_id, "+FLAGS", "\\Seen")
                        await self._process_email_message(raw_bytes, e_id.decode("utf-8"))
                    else:
                        imap.store(e_id, "+FLAGS", "\\Seen")

                except Exception as ex:
                    logger.exception(f"Failed handling message ID {e_id}: {ex}")
                    # Still mark as seen to avoid infinite crash loops on malformed messages
                    try:
                        imap.store(e_id, "+FLAGS", "\\Seen")
                    except Exception:
                        pass

        except (imaplib.IMAP4.abort, imaplib.IMAP4.error, OSError) as net_err:
            logger.warning(f"IMAP connection dropped ({net_err}). Will reconnect on next cycle.")
            self._imap = None
        except Exception as e:
            logger.exception(f"Unexpected error during inbox check: {e}")

    async def start(self) -> None:
        """Starts the Gmail agent loop, connecting MCP clients and monitoring inbox."""
        logger.info("=" * 70)
        logger.info("🚀 Starting Elarion Real Estate Gmail Agent Channel")
        logger.info(f"   Account: {self.user}")
        logger.info(f"   Poll Interval: {self.poll_interval} seconds")
        logger.info("=" * 70)

        # 1. Connect MCP Clients
        logger.info("Connecting MCP clients (Maintenance + FAQ)...")
        try:
            await maintenance_mcp.connect()
            logger.info("Maintenance MCP client connected.")
        except Exception:
            logger.exception("Failed to connect maintenance MCP client.")

        try:
            await faq_mcp.connect()
            logger.info("FAQ MCP client connected.")
        except Exception:
            logger.exception("Failed to connect FAQ MCP client.")

        self._is_running = True

        # Mark pre-existing unread emails as read so the agent only listens for fresh incoming tenant emails
        try:
            imap = self._get_imap_connection()
            imap.select("INBOX")
            status, data = imap.search(None, "UNSEEN")
            if status == "OK" and data and data[0]:
                old_ids = data[0].split()
                if old_ids:
                    logger.info(f"Marking {len(old_ids)} pre-existing email(s) as read to start fresh...")
                    for old_id in old_ids:
                        imap.store(old_id, "+FLAGS", "\\Seen")
                    logger.info("Inbox cleaned! Agent is now actively listening for fresh tenant emails.")
        except Exception as e:
            logger.warning(f"Could not clear pre-existing unread emails on startup: {e}")

        try:
            while self._is_running:
                await self.check_inbox_once()
                await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            logger.info("Gmail channel received cancellation signal.")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Gracefully disconnects IMAP, MCP clients, and checkpointer."""
        self._is_running = False
        logger.info("Shutting down Gmail Channel...")

        if self._imap:
            try:
                self._imap.close()
                self._imap.logout()
            except Exception:
                pass
            self._imap = None

        try:
            await maintenance_mcp.disconnect()
            logger.info("Maintenance MCP client disconnected.")
        except Exception as e:
            logger.warning(f"Maintenance MCP disconnect error: {e}")

        try:
            await faq_mcp.disconnect()
            logger.info("FAQ MCP client disconnected.")
        except Exception as e:
            logger.warning(f"FAQ MCP disconnect error: {e}")

        try:
            await close_checkpointer()
            logger.info("Database checkpointer closed.")
        except Exception as e:
            logger.warning(f"Checkpointer close error: {e}")

        logger.info("Gmail Agent Channel shutdown complete.")


# Direct instance for import
gmail_service = GmailAgentService()
