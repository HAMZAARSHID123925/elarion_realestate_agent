"""
Sanity test for Gmail IMAP and SMTP authentication with App Password.
"""
import os
import imaplib
import smtplib
from dotenv import load_dotenv

# Load from langgraph_agent/.env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path)

GMAIL_USER = os.getenv("GMAIL_USER", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()

print(f"Testing Gmail credentials for: {GMAIL_USER}")
assert GMAIL_USER, "GMAIL_USER is missing!"
assert GMAIL_APP_PASSWORD, "GMAIL_APP_PASSWORD is missing!"

# 1. Test IMAP (receiving emails)
print("\n[1/2] Connecting to Gmail IMAP (imap.gmail.com:993)...")
try:
    imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    imap.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    status, counts = imap.select("INBOX")
    print(f"  -> SUCCESS! IMAP login authenticated. Total messages in INBOX: {counts[0].decode('utf-8')}")
    imap.logout()
except Exception as e:
    print(f"  -> FAILED IMAP: {e}")
    exit(1)

# 2. Test SMTP (sending replies)
print("\n[2/2] Connecting to Gmail SMTP (smtp.gmail.com:587)...")
try:
    smtp = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()
    smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    print("  -> SUCCESS! SMTP login authenticated. Outbound sending is authorized.")
    smtp.quit()
except Exception as e:
    print(f"  -> FAILED SMTP: {e}")
    exit(1)

print("\nAll Gmail authentication checks passed successfully!")
