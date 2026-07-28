"""
Local, terminal-style testing loop for whatsapp_server.py (Meta Cloud API
version) -- the WhatsApp equivalent of app/terminal.py, going through the
real HTTP webhook instead of calling invoke_pipeline() directly.

Usage:
  1. Start whatsapp_server.py in one terminal:
       python whatsapp_server.py
  2. Run this script in another terminal:
       python test_whatsapp_local.py
  3. Type messages like you did with terminal.py. Each one is wrapped in a
     Meta-shaped webhook payload and POSTed with a correctly-computed
     X-Hub-Signature-256 header (using the real WHATSAPP_APP_SECRET from
     .env), so signature validation passes exactly as it would for a real
     Meta request.
  4. Watch the whatsapp_server.py console -- the "[WhatsApp -> ...]" line
     shows the reply as soon as the pipeline finishes. If WHATSAPP_ACCESS_TOKEN
     / WHATSAPP_PHONE_NUMBER_ID point at your real Meta test number and
     WHATSAPP_TEST_FROM_NUMBER is a number you've added as a test recipient,
     the reply also arrives on that WhatsApp for real.

This does NOT test whether Meta can reach you over the public internet, or
the one-time GET webhook verification handshake -- that needs ngrok + the
Meta App Dashboard. Run that at least once before considering this channel
done, and again before moving off the free test number.
"""
import os
import hmac
import hashlib
import json
import time
import uuid
import requests
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.getenv("WHATSAPP_TEST_WEBHOOK_URL", "http://localhost:8003/whatsapp/webhook")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET")
TEST_FROM_NUMBER = os.getenv("WHATSAPP_TEST_FROM_NUMBER", "923001234567")  # no "whatsapp:" prefix, no "+"


def build_meta_payload(body_text: str) -> dict:
    """Mimics the shape Meta actually sends for an inbound text message."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "TEST_WABA_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "15551234567",
                        "phone_number_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID", "TEST_PHONE_NUMBER_ID"),
                    },
                    "contacts": [{"profile": {"name": "Local Test User"}, "wa_id": TEST_FROM_NUMBER}],
                    "messages": [{
                        "from": TEST_FROM_NUMBER,
                        "id": f"wamid.TEST{uuid.uuid4().hex}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": body_text},
                        "type": "text",
                    }],
                },
                "field": "messages",
            }],
        }],
    }


def sign_payload(raw_body: bytes) -> str:
    if not WHATSAPP_APP_SECRET:
        raise RuntimeError(
            "WHATSAPP_APP_SECRET not set in .env -- required even for local "
            "testing, since the webhook validates every request against it."
        )
    computed = hmac.new(WHATSAPP_APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={computed}"


def main():
    print("Elarion WhatsApp (Meta Cloud API) -- local webhook test loop")
    print(f"Posting to: {WEBHOOK_URL}")
    print(f"Simulated sender: {TEST_FROM_NUMBER}")
    print("Type 'exit' or 'quit' to stop.\n")
    print("Note: replies print in the whatsapp_server.py console, not here --")
    print("this script only simulates the inbound Meta webhook call.\n")

    while True:
        try:
            user_input = input("You: ")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if user_input.strip().lower() in ["exit", "quit"]:
            break
        if not user_input.strip():
            continue

        try:
            payload = build_meta_payload(user_input)
            # Signature is computed over the exact raw bytes we send -- must
            # use the same serialization requests will actually transmit.
            raw_body = json.dumps(payload).encode("utf-8")
            signature = sign_payload(raw_body)

            response = requests.post(
                WEBHOOK_URL,
                data=raw_body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": signature,
                },
                timeout=10,
            )
            if response.status_code == 200:
                print("  -> webhook accepted (200). Check the server console for the reply.")
            else:
                print(f"  -> webhook returned {response.status_code}: {response.text}")
        except requests.exceptions.ConnectionError:
            print("  -> could not reach whatsapp_server.py. Is it running (python whatsapp_server.py)?")
        except Exception as e:
            print(f"  -> error: {e}")

        time.sleep(0.3)


if __name__ == "__main__":
    main()
