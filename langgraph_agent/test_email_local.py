"""
Local, interactive CLI testing harness for email_server.py (Resend Webhook API).

Usage:
  1. Start email_server.py in Terminal 1:
       python email_server.py
  2. Run this test runner in Terminal 2:
       python test_email_local.py
  3. Select from predefined workflow presets (Maintenance, FAQ, Rent Renewal)
     or enter custom email body text.
"""
import os
import sys
import time
import uuid
import requests
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.getenv("EMAIL_TEST_WEBHOOK_URL", "http://localhost:8004/email/webhook")
TEST_FROM_EMAIL = os.getenv("EMAIL_TEST_FROM_ADDRESS", "usman.hameed1145@gmail.com")
TEST_SUBJECT = "Elarion Tenant Inquiry"


def build_resend_payload(from_email: str, subject: str, body_text: str) -> dict:
    """Constructs authentic Resend inbound webhook JSON payload."""
    msg_id = f"msg_{uuid.uuid4().hex[:16]}"
    return {
        "type": "email.received",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": {
            "id": msg_id,
            "from": [from_email],
            "to": ["support@elarion.com"],
            "subject": subject,
            "text": body_text,
            "headers": {
                "user-agent": "Resend-Inbound-Webhook/1.0",
                "message-id": f"<{msg_id}@mail.gmail.com>",
            }
        }
    }


def send_test_email(from_email: str, subject: str, body_text: str):
    payload = build_resend_payload(from_email, subject, body_text)
    print(f"\n[Sending Email Webhook] From: {from_email} | Subject: '{subject}'")
    print(f"[Body]: \"{body_text}\"")

    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "x-webhook-secret": os.getenv("RESEND_WEBHOOK_SECRET", "elarion_secret_dev")
            },
            timeout=120  # Pipeline can take 30-60s on first run (MCP cold start + Groq LLM + DB)
        )
        if response.status_code == 200:
            print("  -> Webhook accepted (200 OK). Check email_server.py console for outbound response details!")
        else:
            print(f"  -> Webhook returned status {response.status_code}: {response.text}")
    except requests.exceptions.ConnectionError:
        print("  -> Could not reach email_server.py! Make sure it is running (python email_server.py).")
    except Exception as e:
        print(f"  -> Error sending request: {e}")


def main():
    print("=" * 70)
    print("📧 Elarion Email Channel (Resend Webhook API) -- Local Test Harness")
    print(f"Posting to: {WEBHOOK_URL}")
    print(f"Simulated Tenant Sender: {TEST_FROM_EMAIL}")
    print("=" * 70)
    print("\nSelect a Test Scenario:")
    print("  1. [Maintenance] Initial Issue Report ('My kitchen faucet is leaking in Unit 3B')")
    print("  2. [Maintenance] Multi-Turn Answer ('Unit 3B, yes vendor can enter, no pets')")
    print("  3. [FAQ] Policy Inquiry ('What is the pet policy and deposit?')")
    print("  4. [Rent Renewal] Renewal Options ('My lease ends next month. What are my options?')")
    print("  5. Custom Email Body")
    print("  6. Exit\n")

    while True:
        try:
            choice = input("Enter choice (1-6): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if choice == "6" or choice.lower() in ["exit", "quit"]:
            break

        if choice == "1":
            send_test_email(TEST_FROM_EMAIL, "Leaking Faucet in Kitchen", "Hi, my kitchen faucet broke and water is leaking in Unit 3B.")
        elif choice == "2":
            send_test_email(TEST_FROM_EMAIL, "Re: Leaking Faucet in Kitchen", "Unit 3B, yes vendor has permission to enter, and no pets present.")
        elif choice == "3":
            send_test_email(TEST_FROM_EMAIL, "Pet Policy Question", "Hi, what is the pet policy for dogs and what is the deposit amount?")
        elif choice == "4":
            send_test_email(TEST_FROM_EMAIL, "Lease Renewal Question", "Hi, my lease expires next month. What are my renewal rate options?")
        elif choice == "5":
            custom_sender = input(f"Enter Sender Email [Default: {TEST_FROM_EMAIL}]: ").strip() or TEST_FROM_EMAIL
            custom_subject = input("Enter Subject [Default: Inquiry]: ").strip() or "Inquiry"
            custom_body = input("Enter Email Body: ").strip()
            if custom_body:
                send_test_email(custom_sender, custom_subject, custom_body)
        else:
            print("Invalid choice. Please enter 1-6.")

        time.sleep(0.5)


if __name__ == "__main__":
    main()
