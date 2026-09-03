# 📬 Elarion AI Property Management System
## Free Direct Gmail Channel Integration & Operations Guide

**Account:** `apiusage92@gmail.com`  
**Protocol:** IMAP (`imap.gmail.com:993` SSL) + SMTP (`smtp.gmail.com:587` STARTTLS)  
**Authentication:** Google App Password (`mrdtthfhlpvkvejj`)  
**Cost:** **100% Free (No custom domain or third-party paid service required)**  
**Status:** Tested & Operational  

---

## 1. Overview & Architecture

Previously, testing the email channel relied either on simulated webhook CLI tools (`test_email_local.py`) or third-party webhook relays (Resend) which require a custom domain.

With this integration, the agent directly connects to your Gmail account:
1. **Inbound Listener (IMAP):** Watches for unread incoming tenant emails.
2. **Conversation Threading & Cleaning:** Automatically strips email history blocks (`On ... wrote:`, quotes) so only the tenant's new message is sent to the LLM.
3. **Multi-Turn Memory (LangGraph Checkpointer):** Maps the conversation thread to `email:<sender_email>`, preserving slot filling (e.g. Unit number, permission to enter, pets) across multiple email replies.
4. **Outbound Dispatcher (SMTP):** Sends replies directly from `apiusage92@gmail.com` with `In-Reply-To` and `References` headers matching the tenant's email `Message-ID`. The tenant's email client keeps the entire conversation in a single thread.
5. **Deduplication & Safety:**
   - Automatically marks incoming emails as `\Seen` so no message is answered twice.
   - Ignores self-sent emails from `apiusage92@gmail.com` to prevent infinite bot loops.
   - Built-in rate limiting (max 10 emails/min per sender) and auto-responder detection.

---

## 2. File Structure

```
langgraph_agent/
├── .env                              # Stores GMAIL_USER, GMAIL_APP_PASSWORD, GMAIL_POLL_INTERVAL
├── gmail_server.py                   # Main launcher script (python gmail_server.py)
├── test_gmail_channel.py             # CLI test runner to send test emails to the agent
├── tests/
│   └── test_gmail_auth.py            # Sanity test for IMAP/SMTP authentication
└── input_channels/
    └── gmail_service.py              # Core service handling IMAP polling, email cleaning & SMTP reply
```

---

## 3. Configuration in `.env`

The following environment variables are configured in `langgraph_agent/.env`:

```env
# --- Free Direct Gmail Channel Configuration (IMAP / SMTP) ---
GMAIL_USER="apiusage92@gmail.com"
GMAIL_APP_PASSWORD="mrdtthfhlpvkvejj"
GMAIL_POLL_INTERVAL="5"
GMAIL_DISPLAY_NAME="Elarion Real Estate Assistant"
```

---

## 4. How to Run and Test

### Step 1: Sanity Check Credentials
Run the authentication test script:
```powershell
cd d:\ELARION\elarion_realestate_agent\langgraph_agent
python tests/test_gmail_auth.py
```
**Expected Output:**
```
Testing Gmail credentials for: apiusage92@gmail.com
[1/2] Connecting to Gmail IMAP (imap.gmail.com:993)...
  -> SUCCESS! IMAP login authenticated. Total messages in INBOX: 50
[2/2] Connecting to Gmail SMTP (smtp.gmail.com:587)...
  -> SUCCESS! SMTP login authenticated. Outbound sending is authorized.
All Gmail authentication checks passed successfully!
```

---

### Step 2: Start the Gmail Agent Server
In your terminal, launch the agent:
```powershell
cd d:\ELARION\elarion_realestate_agent\langgraph_agent
python gmail_server.py
```
**Expected Terminal Output:**
```
======================================================================
🚀 Starting Elarion Real Estate Gmail Agent Channel
   Account: apiusage92@gmail.com
   Poll Interval: 5.0 seconds
======================================================================
Connecting MCP clients (Maintenance + FAQ)...
Maintenance MCP client connected.
FAQ MCP client connected.
```
Leave this process running.

---

### Step 3: Test From Any Real Email Account

You can now test from **your phone or computer** using any personal email (Gmail, Outlook, Yahoo, etc.):

#### Turn 1: Initial Inquiry
1. Open your personal email (e.g. `yourname@gmail.com`).
2. Compose a new email:
   - **To:** `apiusage92@gmail.com`
   - **Subject:** `Leaking kitchen pipe`
   - **Body:** `Hi, water is leaking under my kitchen sink in Unit 2B.`
3. Click **Send**.
4. **What happens in the agent terminal:**
   - Within 5 seconds, the agent picks up the email:
     ```
     📥 [Incoming Gmail Received]
        From: Your Name <yourname@gmail.com>
        Subject: 'Leaking kitchen pipe'
        Query: Hi, water is leaking under my kitchen sink in Unit 2B....
     Executing LangGraph pipeline for user_id='yourname@gmail.com'...
     [Gmail Outbound Dispatched] Successfully sent reply to yourname@gmail.com
     ```
5. **What happens in your inbox:**
   - Within seconds, you receive a reply from `Elarion Real Estate Assistant <apiusage92@gmail.com>`:
     > *"I'm sorry to hear about the leak in Unit 2B. To coordinate repair, does our maintenance team have permission to enter if you're not home, and do you have any pets on the premises?"*

#### Turn 2: Multi-Turn Continuation
1. In your personal email, hit **Reply** (do not change the subject):
   - **Body:** `Yes, permission is granted and there are no pets.`
2. Click **Send**.
3. **What happens:**
   - The agent strips the previous quoted message block automatically.
   - It retrieves the ongoing conversation thread from the database checkpointer.
   - It matches the unit number and permissions, completes the maintenance ticket, and replies back.
   - In your inbox, the reply appears right inside the **same conversation thread**!

---

### Step 4: Testing via the CLI Test Utility (Optional)
If you do not want to use an email client, run:
```powershell
cd d:\ELARION\elarion_realestate_agent\langgraph_agent
python test_gmail_channel.py
```
This tool lets you select pre-built scenarios (Maintenance, FAQ, Lease Renewal) or custom inquiries, enter your personal email address as the simulated tenant, and automatically dispatches the email to `apiusage92@gmail.com`.

---

## 5. Best Practices & Production Safeguards

1. **Email Header Decoding:** Handled via `email.header.decode_header` to prevent unicode crashes when users send emoji or international characters.
2. **Quote Stripping:** RegEx patterns strip standard email client quote artifacts (`On ... wrote:`, `From:`, `> ...`) to keep LLM context clean and token costs low.
3. **Loop Prevention:** Checks if `sender_email == GMAIL_USER`. If equal, the message is ignored to prevent infinite mail loops.
4. **Resilient Connection Handling:** If the network drops or Gmail closes the IMAP socket, the service catches the exception and reconnects automatically on the next cycle without crashing.
5. **Clean Thread Identifiers:** Sets both `In-Reply-To` and `References` headers on all replies.
