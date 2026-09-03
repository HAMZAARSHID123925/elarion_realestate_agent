"""
CLI Test Utility for Elarion Gmail Channel.
Can send simulated tenant emails to apiusage92@gmail.com to trigger the agent,
or verify end-to-end processing.
"""
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GMAIL_USER = os.getenv("GMAIL_USER", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
TEST_RECIPIENT = GMAIL_USER  # Sends to the agent inbox


def send_tenant_email(from_addr: str, subject: str, body: str, reply_to_msg_id: str = None):
    print(f"\n[Sending Test Email to Agent]")
    print(f"  From:    {from_addr}")
    print(f"  To:      {TEST_RECIPIENT}")
    print(f"  Subject: {subject}")
    print(f"  Body:    \"{body}\"")

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = TEST_RECIPIENT
    msg["Subject"] = subject
    if reply_to_msg_id:
        msg["In-Reply-To"] = reply_to_msg_id
        msg["References"] = reply_to_msg_id

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print("  -> Sent successfully! Check your running `python gmail_server.py` console.")
    except Exception as e:
        print(f"  -> Failed to send: {e}")


def main():
    print("=" * 70)
    print("📧 Elarion Gmail Channel -- Test Dispatcher")
    print(f"Agent Inbox Target: {TEST_RECIPIENT}")
    print("=" * 70)
    print("\nSelect a Test Scenario:")
    print("  1. [Maintenance] Report leaking faucet ('My kitchen faucet is leaking in Unit 4B')")
    print("  2. [FAQ] Inquire about pet policy ('What is the pet policy and deposit fee?')")
    print("  3. [Rent Renewal] Inquire about lease renewal ('When does my lease expire and can I renew?')")
    print("  4. Custom Email Inquiry")
    print("  5. Exit\n")

    while True:
        try:
            choice = input("Enter choice (1-5): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if choice == "5" or choice.lower() in ["exit", "quit"]:
            break

        # Note: In Gmail, sending from self to self works, but the agent skips emails
        # where sender == GMAIL_USER to avoid infinite bot-to-bot loops.
        # So we prompt for a simulated external sender address or custom address.
        sender_email = input(f"Enter your personal/sender email address [e.g. tenant@gmail.com]: ").strip()
        if not sender_email:
            print("Sender email cannot be empty! (Must be different from agent email to avoid self-loop).")
            continue

        if sender_email.lower() == GMAIL_USER.lower():
            print(f"Warning: The agent ignores emails sent by itself ({GMAIL_USER}) to avoid infinite loops.")
            print("Please enter a different email address (e.g. your personal email).")
            continue

        if choice == "1":
            send_tenant_email(sender_email, "Leaking faucet in kitchen", "Hi, my kitchen faucet is leaking badly in Unit 4B. Water is spilling.")
        elif choice == "2":
            send_tenant_email(sender_email, "Pet Policy Inquiry", "Hi, I am thinking of getting a cat. What is the pet policy and deposit?")
        elif choice == "3":
            send_tenant_email(sender_email, "Lease Renewal Question", "Hi, I would like to know if I can renew my lease for another year.")
        elif choice == "4":
            subj = input("Subject: ").strip() or "General Inquiry"
            body = input("Body: ").strip()
            if body:
                send_tenant_email(sender_email, subj, body)
        else:
            print("Invalid choice. Please select 1-5.")


if __name__ == "__main__":
    main()
