"""
WhatsApp Access Token Validator — checks if your current token is still valid.

Usage:
    python scripts/check_token_expiry.py

Calls Meta's Graph API to verify the token and prints the result.
No credit card or production setup required — uses the same temporary
token you generate in Meta's App Dashboard > WhatsApp > API Setup.
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Load .env from the langgraph_agent directory
env_path = os.path.join(os.path.dirname(__file__), "..", "langgraph_agent", ".env")
load_dotenv(env_path)

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v25.0")


def check_token():
    print("=" * 60)
    print("🔑 WhatsApp Access Token Health Check")
    print("=" * 60)

    if not WHATSAPP_ACCESS_TOKEN:
        print("\n❌ WHATSAPP_ACCESS_TOKEN is not set in .env")
        print("   Go to: https://developers.facebook.com/apps/")
        print("   → Your App → WhatsApp → API Setup → Generate Token")
        return False

    if not WHATSAPP_PHONE_NUMBER_ID:
        print("\n❌ WHATSAPP_PHONE_NUMBER_ID is not set in .env")
        return False

    print(f"\n📱 Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
    print(f"🔗 API Version: {WHATSAPP_API_VERSION}")
    print(f"🔐 Token (first 20 chars): {WHATSAPP_ACCESS_TOKEN[:20]}...")

    # Call the Graph API to verify the token
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}"
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}

    print(f"\n⏳ Checking token against Meta Graph API...")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()

        if response.status_code == 200:
            display_name = data.get("verified_name") or data.get("display_phone_number", "Unknown")
            print(f"\n✅ TOKEN IS VALID")
            print(f"   Phone Number: {data.get('display_phone_number', 'N/A')}")
            print(f"   Verified Name: {display_name}")
            print(f"   Quality Rating: {data.get('quality_rating', 'N/A')}")
            print(f"\n   Your WhatsApp channel is ready for testing!")
            return True
        else:
            error = data.get("error", {})
            error_msg = error.get("message", "Unknown error")
            error_code = error.get("code", "N/A")
            error_subcode = error.get("error_subcode", "N/A")

            print(f"\n❌ TOKEN IS EXPIRED OR INVALID")
            print(f"   Error Code: {error_code} (subcode: {error_subcode})")
            print(f"   Message: {error_msg}")
            print(f"\n   🔄 To fix this:")
            print(f"   1. Go to: https://developers.facebook.com/apps/")
            print(f"   2. Select your app → WhatsApp → API Setup")
            print(f"   3. Click 'Generate' under Temporary Access Token")
            print(f"   4. Copy the new token into your .env file:")
            print(f'      WHATSAPP_ACCESS_TOKEN="<new-token>"')
            print(f"   5. Restart whatsapp_server.py")
            return False

    except requests.exceptions.ConnectionError:
        print(f"\n⚠️  Could not reach Meta's API (no internet or API is down)")
        return False
    except Exception as e:
        print(f"\n⚠️  Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = check_token()
    print("\n" + "=" * 60)
    sys.exit(0 if success else 1)
